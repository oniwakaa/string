"""
Intent Classifier Module

This module provides a model-driven intent classification system for routing
user prompts to appropriate agents. It replaces the hardcoded keyword-based
routing with a more flexible and accurate ML-based approach using Gemma3n.

Integration Point: This classifier is called from orchestrator.py in the
_decompose_prompt() method, replacing the keyword matching logic.
"""

import json
import logging
import os
import time
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from abc import ABC, abstractmethod

import yaml
import numpy as np

# Configure logging
logger = logging.getLogger(__name__)


@dataclass
class IntentClassification:
    """
    Represents the result of intent classification.
    
    Attributes:
        primary_intent: The main detected intent
        confidence: Confidence score for the primary intent (0.0-1.0)
        secondary_intents: List of secondary intents with their scores
        workflow: Suggested workflow based on intent combinations
        context_modifiers: Detected context that affects routing
        metadata: Additional classification metadata
    """
    primary_intent: str
    confidence: float
    secondary_intents: List[Tuple[str, float]]
    workflow: Optional[str] = None
    context_modifiers: List[str] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.context_modifiers is None:
            self.context_modifiers = []
        if self.metadata is None:
            self.metadata = {}
        
        # Ensure confidence is in valid range
        self.confidence = max(0.0, min(1.0, self.confidence))
    
    def meets_threshold(self, threshold: float = 0.7) -> bool:
        """Check if the classification meets the confidence threshold."""
        return self.confidence >= threshold
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "primary_intent": self.primary_intent,
            "confidence": self.confidence,
            "secondary_intents": self.secondary_intents,
            "workflow": self.workflow,
            "context_modifiers": self.context_modifiers,
            "metadata": self.metadata
        }


class BaseIntentClassifier(ABC):
    """
    Abstract base class for intent classifiers.
    
    This defines the interface that all intent classifiers must implement,
    allowing for different implementations (keyword-based, model-based, etc.).
    """
    
    def __init__(self, registry_path: str = None):
        """
        Initialize the classifier with intent registry.
        
        Args:
            registry_path: Path to the agent intent registry YAML file
        """
        self.registry = self._load_registry(registry_path)
        self.intents = self.registry.get('intents', {})
        self.workflows = self.registry.get('workflows', {})
        self.context_modifiers = self.registry.get('context_modifiers', {})
        
    def _load_registry(self, registry_path: str = None) -> Dict[str, Any]:
        """Load the intent registry from YAML file."""
        if registry_path is None:
            # Default path relative to project root
            registry_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                'config', 'agent_intent_registry.yaml'
            )
        
        try:
            with open(registry_path, 'r') as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.error(f"Failed to load intent registry: {e}")
            # Return minimal registry if loading fails
            return {"intents": {}, "workflows": {}, "context_modifiers": {}}
    
    @abstractmethod
    def classify(self, prompt: str, context: Dict[str, Any] = None) -> IntentClassification:
        """
        Classify the intent of a user prompt.
        
        Args:
            prompt: The user's input prompt
            context: Optional context dictionary with additional information
            
        Returns:
            IntentClassification object with classification results
        """
        pass
    
    def get_agent_for_intent(self, intent: str) -> Optional[str]:
        """
        Get the primary agent for a given intent.
        
        Args:
            intent: The classified intent
            
        Returns:
            Agent role/name or None if intent not found
        """
        intent_config = self.intents.get(intent, {})
        return intent_config.get('primary_agent')
    
    def get_workflow_for_intents(self, primary: str, secondary: List[str]) -> Optional[Dict[str, Any]]:
        """
        Determine if a workflow should be triggered based on intent combinations.
        
        Args:
            primary: Primary intent
            secondary: List of secondary intents
            
        Returns:
            Workflow configuration or None
        """
        for workflow_name, workflow_config in self.workflows.items():
            trigger_intents = workflow_config.get('trigger_intents', [])
            if primary in trigger_intents:
                # Check if any secondary keywords match
                secondary_keywords = workflow_config.get('secondary_keywords', [])
                if secondary_keywords:
                    # This would need the original prompt to check keywords
                    # For now, return the workflow config
                    return workflow_config
        return None


class GemmaIntentClassifier(BaseIntentClassifier):
    """
    Model-driven intent classifier using Gemma3n model.
    
    This classifier uses the Gemma3n model to understand the semantic meaning
    of prompts and classify them into appropriate intents with confidence scores.
    """
    
    def __init__(self, registry_path: str = None, model_name: str = "gemma-3n-E4B-it"):
        """
        Initialize the Gemma-based intent classifier.
        
        Args:
            registry_path: Path to the agent intent registry
            model_name: Name of the model to use for classification
        """
        super().__init__(registry_path)
        self.model_name = model_name
        self.model = None
        self._classification_prompt_template = None
        self._setup_classification_prompt()
        
    def _setup_classification_prompt(self):
        """
        Set up enhanced classification prompt template for Gemma.
        
        Testing Results (Prompt Refinement Analysis):
        - Current minimal: 27.3% accuracy (3/11 test cases)
        - Enhanced definitions: 72.7% accuracy (8/11) - CHOSEN
        - Keyword focused: 45.5% accuracy (5/11)
        - Action focused: 54.5% accuracy (6/11)
        
        Enhanced definitions fixed all 3 known failure cases:
        - Web research vs code editing distinction
        - Tool execution vs code analysis distinction  
        - Codebase queries vs quality analysis distinction
        
        Improvement: +45.5% accuracy, 2.3x faster (0.59s vs 1.38s)
        """
        # Build simple intent list for fallback
        intent_list = []
        for intent_name, intent_config in self.intents.items():
            if not intent_config.get('is_fallback', False):
                intent_list.append(intent_name)
        
        # Enhanced definitions prompt with improved clarifications based on failure analysis
        self._classification_prompt_template = """Classify user request into ONE intent:

web_research: Get info from external websites/sources (NOT create internal docs)
codebase_query: Understand existing code logic (NOT quality evaluation)  
code_generation: Create new code from scratch (NOT modify existing)
code_editing: Change/modify/fix code files (NOT just identify issues)
code_analysis: Evaluate code quality/structure (NOT understand logic)
documentation: Create internal docs/comments (NOT fetch external docs)
tool_execution: Run/execute/perform actions that produce output (NOT passive review)

Request: {prompt}

Intent:"""
        
        self._intent_options = ", ".join(intent_list)
    
    def _load_model(self):
        """Lazy load the Gemma model."""
        if self.model is None:
            try:
                # Import model manager
                import sys
                src_path = os.path.join(os.path.dirname(__file__), '..')
                if src_path not in sys.path:
                    sys.path.insert(0, src_path)
                from models.manager import model_manager
                
                logger.info(f"Loading {self.model_name} for intent classification...")
                self.model = model_manager.get_model(self.model_name)
                if not self.model:
                    raise RuntimeError(f"Failed to load model: {self.model_name}")
                logger.info("Model loaded successfully for intent classification")
                
            except Exception as e:
                logger.error(f"Failed to load model for classification: {e}")
                raise
    
    def classify(self, prompt: str, context: Dict[str, Any] = None) -> IntentClassification:
        """
        Classify the intent using Gemma3n model.
        
        Args:
            prompt: The user's input prompt
            context: Optional context dictionary
            
        Returns:
            IntentClassification object with results
        """
        start_time = time.time()
        
        try:
            # Ensure model is loaded
            self._load_model()
            
            # Prepare the minimal classification prompt
            classification_prompt = self._classification_prompt_template.format(
                prompt=prompt, 
                intent_list=self._intent_options
            )
            
            # Add minimal context if available (no verbose JSON)
            if context and len(str(context)) < 100:
                context_info = f"\nContext: {context}"
                classification_prompt += context_info
            
            # Generate classification using Gemma (optimized for minimal prompts)
            response = self.model(
                classification_prompt,
                max_tokens=20,  # Minimal tokens for simple classification
                temperature=0.1,  # Low temperature for consistent classification
                top_p=0.9,
                stop=["User:", "Intent:", "Categories:", "\n\n"]
            )
            
            # Extract and parse the simple response (no JSON expected)
            classification_text = response['choices'][0]['text'].strip()
            
            # Extract intent directly from minimal response
            predicted_intent = self._extract_intent_minimal(classification_text)
            
            # Set base confidence based on exact match
            confidence = 0.9 if predicted_intent != 'general_query' else 0.3
            primary_intent = predicted_intent
            
            # Apply confidence validation for known confusion patterns
            primary_intent, confidence = self._validate_classification(prompt, primary_intent, confidence)
            
            # Ensure primary intent is valid
            if primary_intent not in self.intents:
                logger.warning(f"Unknown intent '{primary_intent}', falling back to general_query")
                primary_intent = 'general_query'
                confidence *= 0.5  # Reduce confidence for fallback
            
            # Minimal response - no secondary intents or complex workflows
            secondary_intents = []
            workflow = None
            context_modifiers = []
            
            # Build metadata
            metadata = {
                'classification_time': time.time() - start_time,
                'model_used': self.model_name,
                'prompt_type': 'minimal_structured',
                'raw_response': classification_text[:100]  # Store truncated raw response
            }
            
            return IntentClassification(
                primary_intent=primary_intent,
                confidence=confidence,
                secondary_intents=secondary_intents,
                workflow=workflow,
                context_modifiers=context_modifiers,
                metadata=metadata
            )
            
        except Exception as e:
            logger.error(f"Intent classification failed: {e}")
            # Return fallback classification
            return IntentClassification(
                primary_intent='general_query',
                confidence=0.3,
                secondary_intents=[],
                metadata={
                    'error': str(e),
                    'classification_time': time.time() - start_time
                }
            )
    
    def _extract_intent_minimal(self, text: str) -> str:
        """
        Extract intent from minimal model response.
        
        Args:
            text: The model's simple response text
            
        Returns:
            Intent name or 'general_query' as fallback
        """
        text_lower = text.lower().strip()
        
        # Direct intent matching (exact name)
        for intent_name in self._intent_options.split(", "):
            if intent_name.lower() in text_lower:
                return intent_name
        
        # Partial matching with underscores replaced
        for intent_name in self._intent_options.split(", "):
            intent_words = intent_name.replace("_", " ").lower()
            if intent_words in text_lower:
                return intent_name
        
        # Look for key terms
        if any(term in text_lower for term in ["scrape", "fetch", "web", "website", "url"]):
            return "web_research"
        elif any(term in text_lower for term in ["find", "search", "where", "locate", "show"]):
            return "codebase_query"
        elif any(term in text_lower for term in ["create", "generate", "build", "implement", "write"]):
            return "code_generation"
        elif any(term in text_lower for term in ["edit", "fix", "modify", "update", "change", "refactor"]):
            return "code_editing"
        elif any(term in text_lower for term in ["analyze", "review", "check", "audit", "quality"]):
            return "code_analysis"
        elif any(term in text_lower for term in ["document", "explain", "describe", "usage"]):
            return "documentation"
        
        return "general_query"
    
    def _validate_classification(self, prompt: str, predicted_intent: str, confidence: float) -> tuple[str, float]:
        """
        Validate classification against known confusion patterns and apply fallback logic.
        
        Based on routing failure analysis, this method checks for common misclassifications
        and adjusts the result when confidence is high but the classification seems wrong.
        
        Args:
            prompt: Original user prompt
            predicted_intent: The initially predicted intent
            confidence: Initial confidence score
            
        Returns:
            Tuple of (validated_intent, adjusted_confidence)
        """
        prompt_lower = prompt.lower()
        
        # High confidence validation rules based on failure analysis
        if confidence > 0.85:
            
            # Rule 1: web_research vs documentation confusion
            if predicted_intent == "documentation" and any(indicator in prompt_lower for indicator in ["website", "external", "fetch", "get from", "scrape"]):
                logger.info(f"🔍 High-confidence validation: '{predicted_intent}' → 'web_research' (external source indicators found)")
                return "web_research", confidence * 0.9  # Slight confidence reduction for correction
            
            # Rule 2: code_analysis vs tool_execution confusion  
            if predicted_intent == "code_analysis" and any(action in prompt_lower for action in ["run", "execute", "perform", "test with", "execute tests"]):
                logger.info(f"🔍 High-confidence validation: '{predicted_intent}' → 'tool_execution' (action verbs found)")
                return "tool_execution", confidence * 0.9
            
            # Rule 3: code_analysis vs code_editing confusion
            if predicted_intent == "code_analysis" and any(action in prompt_lower for action in ["fix", "modify", "change", "update", "resolve"]):
                logger.info(f"🔍 High-confidence validation: '{predicted_intent}' → 'code_editing' (modification verbs found)")
                return "code_editing", confidence * 0.9
        
        # Ambiguity detection for low/medium confidence
        elif confidence < 0.7:
            
            # Check for ambiguous multi-step prompts
            if "and" in prompt_lower:
                actions = prompt_lower.split("and")
                if len(actions) >= 2:
                    # Multiple actions detected - might need clarification
                    logger.info(f"⚠️ Ambiguous multi-step prompt detected: '{prompt[:50]}...'")
                    # For now, keep original classification but flag for potential user clarification
        
        # Intent-specific validation rules
        
        # Web research should have external indicators
        if predicted_intent == "web_research" and not any(indicator in prompt_lower for indicator in ["website", "web", "external", "url", "http", "fetch", "scrape", "get from"]):
            logger.warning(f"⚠️ web_research classified but no external indicators found")
            confidence *= 0.8  # Reduce confidence
        
        # Tool execution should have action verbs
        if predicted_intent == "tool_execution" and not any(action in prompt_lower for action in ["run", "execute", "test", "perform", "command"]):
            logger.warning(f"⚠️ tool_execution classified but no action verbs found")  
            confidence *= 0.8
        
        # Code editing should have modification indicators
        if predicted_intent == "code_editing" and not any(mod in prompt_lower for mod in ["fix", "modify", "change", "update", "edit", "refactor", "improve"]):
            logger.warning(f"⚠️ code_editing classified but no modification indicators found")
            confidence *= 0.8
        
        return predicted_intent, confidence
    
    def _extract_classification_fallback(self, text: str) -> Dict[str, Any]:
        """
        Fallback method to extract classification from non-JSON response.
        
        Args:
            text: The model's response text
            
        Returns:
            Dictionary with extracted classification data
        """
        import re
        
        classification = {
            'primary_intent': 'general_query',
            'confidence': 0.5,
            'secondary_intents': [],
            'context_modifiers': [],
            'reasoning': text[:200]
        }
        
        # Try to extract intent names
        intent_pattern = r'(?:primary_intent|intent)["\s:]+(\w+)'
        intent_match = re.search(intent_pattern, text, re.IGNORECASE)
        if intent_match:
            potential_intent = intent_match.group(1).lower()
            if potential_intent in self.intents:
                classification['primary_intent'] = potential_intent
                classification['confidence'] = 0.7
        
        # Try to extract confidence
        confidence_pattern = r'(?:confidence)["\s:]+([0-9.]+)'
        confidence_match = re.search(confidence_pattern, text, re.IGNORECASE)
        if confidence_match:
            try:
                classification['confidence'] = float(confidence_match.group(1))
            except ValueError:
                pass
        
        return classification




# Factory function for creating classifiers
def create_intent_classifier(
    classifier_type: str = "gemma",
    registry_path: str = None
) -> BaseIntentClassifier:
    """
    Create an intent classifier instance.
    
    Args:
        classifier_type: Type of classifier (only "gemma" supported)
        registry_path: Path to intent registry
        
    Returns:
        Intent classifier instance
    """
    if classifier_type == "gemma":
        return GemmaIntentClassifier(registry_path)
    else:
        raise ValueError(f"Only 'gemma' classifier type is supported, got: {classifier_type}")


# Module-level instance for easy access
_default_classifier = None


def get_default_classifier() -> BaseIntentClassifier:
    """Get or create the default intent classifier."""
    global _default_classifier
    if _default_classifier is None:
        _default_classifier = create_intent_classifier("gemma")
    return _default_classifier