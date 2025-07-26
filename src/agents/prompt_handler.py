"""
Enhanced Prompt Handler for Ambiguous Terminal Requests

This module provides sophisticated prompt analysis and disambiguation
for the Enhanced Tool Executor Agent, handling complex scenarios like:
- Compound requests ("search for TODOs and clean unused files")
- Context-dependent actions ("clean up the project")
- Partial commands ("start the server... you know which one")
- Ambiguous references ("fix the build issues")

Key Features:
- Multi-intent detection and decomposition
- Context awareness and inference
- Command completion and suggestion
- Risk assessment for ambiguous operations
- Integration with confirmation system

Author: Claude Code Assistant
Date: 2025-01-26
"""

import json
import logging
import re
from typing import Dict, Any, List, Tuple, Optional
from dataclasses import dataclass, asdict
from enum import Enum

from .confirmation_system import RiskLevel


class RequestType(Enum):
    """Types of user requests."""
    SIMPLE_COMMAND = "simple_command"         # "list files"
    COMPOUND_REQUEST = "compound_request"     # "search and delete"
    CONTEXTUAL_REQUEST = "contextual_request" # "clean up"
    PARTIAL_COMMAND = "partial_command"       # "start the..."
    AMBIGUOUS_REQUEST = "ambiguous_request"   # "fix issues"


class DisambiguationStrategy(Enum):
    """Strategies for handling ambiguous requests."""
    AUTO_INFER = "auto_infer"           # Try to infer intent
    REQUEST_CLARIFICATION = "clarify"   # Ask user for clarification
    SUGGEST_OPTIONS = "suggest"         # Provide multiple options
    SAFE_DEFAULT = "safe_default"       # Choose safest interpretation


@dataclass
class IntentDecomposition:
    """Result of breaking down a complex request into atomic intents."""
    original_request: str
    atomic_intents: List[str]
    intent_dependencies: Dict[str, List[str]]  # Which intents depend on others
    risk_assessment: Dict[str, str]  # Risk level for each intent
    execution_order: List[str]
    warnings: List[str]


@dataclass
class ContextInference:
    """Result of inferring context from ambiguous requests."""
    inferred_context: Dict[str, Any]
    confidence_score: float
    context_sources: List[str]  # What clues led to this inference
    alternatives: List[Dict[str, Any]]  # Alternative interpretations
    needs_clarification: bool


@dataclass
class CommandSuggestion:
    """A suggested command completion or interpretation."""
    suggested_command: str
    confidence: float
    rationale: str
    risk_level: RiskLevel
    requires_confirmation: bool
    metadata: Dict[str, Any] = None


class EnhancedPromptHandler:
    """
    Enhanced prompt handler for complex terminal request analysis.
    
    This handler provides sophisticated analysis of user requests,
    including disambiguation, context inference, and intent decomposition.
    """
    
    def __init__(self, model=None, project_context: Dict[str, Any] = None):
        """
        Initialize the enhanced prompt handler.
        
        Args:
            model: Language model for advanced analysis
            project_context: Context about the current project
        """
        self.model = model
        self.project_context = project_context or {}
        
        # Patterns for different request types
        self.compound_patterns = [
            r'\band\b', r'\bthen\b', r'\bafter\b', r'\bnext\b', r'\balso\b'
        ]
        
        self.contextual_keywords = {
            'cleanup': ['clean', 'cleanup', 'remove unused', 'delete temp'],
            'build': ['build', 'compile', 'make', 'package'],
            'test': ['test', 'check', 'verify', 'validate'],
            'server': ['start', 'serve', 'run server', 'launch'],
            'git': ['commit', 'push', 'pull', 'merge', 'branch']
        }
        
        self.risk_indicators = {
            'high_risk': ['delete', 'remove', 'rm', 'clean', 'wipe', 'destroy'],
            'medium_risk': ['modify', 'change', 'update', 'replace', 'move'],
            'low_risk': ['list', 'show', 'display', 'find', 'search', 'view']
        }
        
        self.logger = logging.getLogger(f'{self.__class__.__name__}')
        self.logger.setLevel(logging.INFO)
    
    def analyze_request(self, request: str) -> Dict[str, Any]:
        """
        Analyze a user request and determine handling strategy.
        
        Args:
            request: The user's natural language request
            
        Returns:
            Analysis result with request type, strategy, and recommendations
        """
        analysis = {
            'original_request': request,
            'request_type': self._classify_request_type(request),
            'complexity_score': self._assess_complexity(request),
            'disambiguation_strategy': None,
            'recommendations': [],
            'warnings': [],
            'metadata': {}
        }
        
        # Determine appropriate handling strategy
        request_type = analysis['request_type']
        
        if request_type == RequestType.SIMPLE_COMMAND:
            analysis['disambiguation_strategy'] = DisambiguationStrategy.AUTO_INFER
            analysis['recommendations'] = [self._handle_simple_command(request)]
            
        elif request_type == RequestType.COMPOUND_REQUEST:
            analysis['disambiguation_strategy'] = DisambiguationStrategy.SUGGEST_OPTIONS
            decomposition = self._decompose_compound_request(request)
            analysis['intent_decomposition'] = asdict(decomposition)
            analysis['recommendations'] = self._generate_compound_recommendations(decomposition)
            
        elif request_type == RequestType.CONTEXTUAL_REQUEST:
            analysis['disambiguation_strategy'] = DisambiguationStrategy.AUTO_INFER
            inference = self._infer_context(request)
            analysis['context_inference'] = asdict(inference)
            
            if inference.needs_clarification:
                analysis['disambiguation_strategy'] = DisambiguationStrategy.REQUEST_CLARIFICATION
                analysis['recommendations'] = self._generate_clarification_prompts(inference)
            else:
                analysis['recommendations'] = self._generate_contextual_recommendations(inference)
                
        elif request_type == RequestType.PARTIAL_COMMAND:
            analysis['disambiguation_strategy'] = DisambiguationStrategy.SUGGEST_OPTIONS
            suggestions = self._complete_partial_command(request)
            analysis['command_suggestions'] = [asdict(s) for s in suggestions]
            analysis['recommendations'] = suggestions
            
        elif request_type == RequestType.AMBIGUOUS_REQUEST:
            analysis['disambiguation_strategy'] = DisambiguationStrategy.REQUEST_CLARIFICATION
            clarifications = self._generate_ambiguity_clarifications(request)
            analysis['clarification_options'] = clarifications
            analysis['recommendations'] = clarifications
        
        # Add safety warnings
        analysis['warnings'].extend(self._assess_safety_risks(request))
        
        self.logger.info(f"Request analyzed: {request_type.value} - {analysis['disambiguation_strategy'].value}")
        
        return analysis
    
    def _classify_request_type(self, request: str) -> RequestType:
        """Classify the type of user request."""
        request_lower = request.lower().strip()
        
        # Check for compound requests (multiple actions)
        if any(re.search(pattern, request_lower) for pattern in self.compound_patterns):
            return RequestType.COMPOUND_REQUEST
        
        # Check for partial/incomplete commands
        if request_lower.endswith('...') or 'you know' in request_lower or 'the usual' in request_lower:
            return RequestType.PARTIAL_COMMAND
        
        # Check for contextual requests (vague but contextually meaningful)
        contextual_terms = ['clean up', 'fix', 'setup', 'prepare', 'organize']
        if any(term in request_lower for term in contextual_terms):
            return RequestType.CONTEXTUAL_REQUEST
        
        # Check for ambiguous requests (too vague to interpret)
        if len(request_lower.split()) <= 2 and not any(keyword in request_lower for keywords in self.contextual_keywords.values() for keyword in keywords):
            return RequestType.AMBIGUOUS_REQUEST
        
        # Default to simple command
        return RequestType.SIMPLE_COMMAND
    
    def _assess_complexity(self, request: str) -> float:
        """Assess the complexity of a request (0.0 to 1.0)."""
        complexity_factors = 0.0
        
        # Length factor
        word_count = len(request.split())
        if word_count > 10:
            complexity_factors += 0.3
        elif word_count > 5:
            complexity_factors += 0.1
        
        # Compound structure
        if any(re.search(pattern, request.lower()) for pattern in self.compound_patterns):
            complexity_factors += 0.4
        
        # Ambiguous references
        ambiguous_words = ['it', 'this', 'that', 'them', 'those', 'the usual']
        ambiguous_count = sum(1 for word in ambiguous_words if word in request.lower())
        complexity_factors += min(ambiguous_count * 0.1, 0.3)
        
        return min(complexity_factors, 1.0)
    
    def _handle_simple_command(self, request: str) -> CommandSuggestion:
        """Handle a simple, straightforward command request."""
        # Simple command mapping
        command_mappings = {
            'list files': 'ls -la',
            'show files': 'ls -la',
            'current directory': 'pwd',
            'git status': 'git status',
            'check status': 'git status --porcelain',
            'show branches': 'git branch -a',
            'list processes': 'ps aux'
        }
        
        request_lower = request.lower().strip()
        
        # Direct mapping
        if request_lower in command_mappings:
            command = command_mappings[request_lower]
            return CommandSuggestion(
                suggested_command=command,
                confidence=0.9,
                rationale=f"Direct mapping for '{request}'",
                risk_level=RiskLevel.LOW,
                requires_confirmation=False
            )
        
        # Pattern-based inference
        if 'list' in request_lower or 'show' in request_lower:
            return CommandSuggestion(
                suggested_command='ls -la',
                confidence=0.7,
                rationale="Inferred list/show command",
                risk_level=RiskLevel.MINIMAL,
                requires_confirmation=False
            )
        
        # Fallback
        return CommandSuggestion(
            suggested_command=f"# Unable to interpret: {request}",
            confidence=0.3,
            rationale="Could not interpret simple command",
            risk_level=RiskLevel.LOW,
            requires_confirmation=True
        )
    
    def _decompose_compound_request(self, request: str) -> IntentDecomposition:
        """Decompose a compound request into atomic intents."""
        # Split by compound indicators
        parts = re.split(r'\\b(and|then|after|next|also)\\b', request, flags=re.IGNORECASE)
        
        # Filter out connecting words and clean up parts
        atomic_intents = []
        for part in parts:
            part = part.strip()
            if part and part.lower() not in ['and', 'then', 'after', 'next', 'also']:
                atomic_intents.append(part)
        
        # Assess risk for each intent
        risk_assessment = {}
        for intent in atomic_intents:
            risk_assessment[intent] = self._assess_intent_risk(intent)
        
        # Determine execution order (simple sequential for now)
        execution_order = atomic_intents.copy()
        
        # Check for dependencies
        intent_dependencies = {}
        for i, intent in enumerate(atomic_intents):
            if i > 0:
                # Simple assumption: each intent depends on the previous one
                intent_dependencies[intent] = [atomic_intents[i-1]]
            else:
                intent_dependencies[intent] = []
        
        warnings = []
        if len(atomic_intents) > 3:
            warnings.append("Complex compound request with multiple steps")
        
        high_risk_intents = [intent for intent, risk in risk_assessment.items() if risk in ['high', 'maximum']]
        if high_risk_intents:
            warnings.append(f"High-risk operations detected: {', '.join(high_risk_intents)}")
        
        return IntentDecomposition(
            original_request=request,
            atomic_intents=atomic_intents,
            intent_dependencies=intent_dependencies,
            risk_assessment=risk_assessment,
            execution_order=execution_order,
            warnings=warnings
        )
    
    def _assess_intent_risk(self, intent: str) -> str:
        """Assess the risk level of a single intent."""
        intent_lower = intent.lower()
        
        for risk_level, indicators in self.risk_indicators.items():
            if any(indicator in intent_lower for indicator in indicators):
                return risk_level.replace('_risk', '')
        
        return 'low'
    
    def _infer_context(self, request: str) -> ContextInference:
        """Infer context from a contextual request."""
        request_lower = request.lower()
        inferred_context = {}
        context_sources = []
        confidence_score = 0.0
        alternatives = []
        
        # Check against contextual keywords
        for context_type, keywords in self.contextual_keywords.items():
            for keyword in keywords:
                if keyword in request_lower:
                    inferred_context[context_type] = True
                    context_sources.append(f"Keyword '{keyword}' suggests {context_type}")
                    confidence_score += 0.2
        
        # Project context inference
        if self.project_context:
            # Check for project-specific files or patterns
            if 'package.json' in str(self.project_context):
                if 'build' in request_lower or 'start' in request_lower:
                    inferred_context['node_project'] = True
                    context_sources.append("Detected Node.js project context")
                    confidence_score += 0.3
            
            if 'requirements.txt' in str(self.project_context) or 'setup.py' in str(self.project_context):
                if 'run' in request_lower or 'start' in request_lower:
                    inferred_context['python_project'] = True
                    context_sources.append("Detected Python project context")
                    confidence_score += 0.3
        
        # Generate alternatives
        if 'clean' in request_lower:
            alternatives = [
                {'action': 'clean_build', 'command': 'rm -rf build/ dist/', 'risk': 'medium'},
                {'action': 'clean_cache', 'command': 'rm -rf __pycache__/', 'risk': 'low'},
                {'action': 'clean_node_modules', 'command': 'rm -rf node_modules/', 'risk': 'medium'}
            ]
        
        # Determine if clarification is needed
        needs_clarification = confidence_score < 0.5 or len(alternatives) > 1
        
        return ContextInference(
            inferred_context=inferred_context,
            confidence_score=min(confidence_score, 1.0),
            context_sources=context_sources,
            alternatives=alternatives,
            needs_clarification=needs_clarification
        )
    
    def _complete_partial_command(self, request: str) -> List[CommandSuggestion]:
        """Complete a partial command based on context and common patterns."""
        request_lower = request.lower().strip()
        suggestions = []
        
        # Common partial command completions
        partial_completions = {
            'start the': [
                ('start the development server', 'npm start', RiskLevel.LOW),
                ('start the Flask server', 'python app.py', RiskLevel.LOW),
                ('start the database', 'systemctl start postgresql', RiskLevel.MEDIUM)
            ],
            'run the': [
                ('run the tests', 'npm test', RiskLevel.LOW),
                ('run the application', 'python main.py', RiskLevel.LOW),
                ('run the build', 'npm run build', RiskLevel.LOW)
            ],
            'show me': [
                ('show me the files', 'ls -la', RiskLevel.MINIMAL),
                ('show me the status', 'git status', RiskLevel.MINIMAL),
                ('show me the logs', 'tail -f app.log', RiskLevel.MINIMAL)
            ]
        }
        
        # Find matching partial patterns
        for partial_pattern, completions in partial_completions.items():
            if partial_pattern in request_lower:
                for description, command, risk_level in completions:
                    suggestions.append(CommandSuggestion(
                        suggested_command=command,
                        confidence=0.8,
                        rationale=f"Completion for '{partial_pattern}': {description}",
                        risk_level=risk_level,
                        requires_confirmation=risk_level in [RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.MAXIMUM]
                    ))
        
        # If no direct matches, provide generic suggestions
        if not suggestions:
            suggestions = [
                CommandSuggestion(
                    suggested_command='ls -la',
                    confidence=0.4,
                    rationale="Generic suggestion: list files",
                    risk_level=RiskLevel.MINIMAL,
                    requires_confirmation=False
                ),
                CommandSuggestion(
                    suggested_command='git status',
                    confidence=0.4,
                    rationale="Generic suggestion: check git status",
                    risk_level=RiskLevel.MINIMAL,
                    requires_confirmation=False
                )
            ]
        
        return suggestions[:5]  # Limit to top 5 suggestions
    
    def _generate_compound_recommendations(self, decomposition: IntentDecomposition) -> List[Dict[str, Any]]:
        """Generate recommendations for compound requests."""
        recommendations = []
        
        for intent in decomposition.execution_order:
            risk_level = decomposition.risk_assessment.get(intent, 'low')
            
            recommendations.append({
                'step': len(recommendations) + 1,
                'intent': intent,
                'risk_level': risk_level,
                'requires_confirmation': risk_level in ['high', 'maximum'],
                'dependencies': decomposition.intent_dependencies.get(intent, [])
            })
        
        return recommendations
    
    def _generate_contextual_recommendations(self, inference: ContextInference) -> List[CommandSuggestion]:
        """Generate recommendations based on context inference."""
        suggestions = []
        
        # Generate suggestions based on inferred context
        for context_type in inference.inferred_context:
            if context_type == 'cleanup':
                suggestions.append(CommandSuggestion(
                    suggested_command='find . -name "*.pyc" -delete',
                    confidence=inference.confidence_score,
                    rationale="Clean up Python cache files",
                    risk_level=RiskLevel.MEDIUM,
                    requires_confirmation=True
                ))
            
            elif context_type == 'build':
                suggestions.append(CommandSuggestion(
                    suggested_command='npm run build',
                    confidence=inference.confidence_score,
                    rationale="Build the project",
                    risk_level=RiskLevel.LOW,
                    requires_confirmation=False
                ))
        
        # Add alternatives as additional suggestions
        for alt in inference.alternatives:
            risk_level = RiskLevel(alt['risk'].lower()) if alt['risk'].lower() in [r.value for r in RiskLevel] else RiskLevel.MEDIUM
            suggestions.append(CommandSuggestion(
                suggested_command=alt['command'],
                confidence=0.6,
                rationale=f"Alternative interpretation: {alt['action']}",
                risk_level=risk_level,
                requires_confirmation=risk_level in [RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.MAXIMUM]
            ))
        
        return suggestions
    
    def _generate_clarification_prompts(self, inference: ContextInference) -> List[Dict[str, Any]]:
        """Generate clarification prompts for ambiguous requests."""
        prompts = []
        
        if inference.alternatives:
            prompt = {
                'type': 'multiple_choice',
                'message': 'Your request could mean several things. Please choose:',
                'options': []
            }
            
            for i, alt in enumerate(inference.alternatives):
                prompt['options'].append({
                    'index': i + 1,
                    'description': alt['action'],
                    'command': alt['command'],
                    'risk_level': alt['risk']
                })
            
            prompts.append(prompt)
        
        else:
            prompts.append({
                'type': 'open_clarification',
                'message': 'Could you please be more specific about what you want to do?',
                'suggestions': [
                    'What files or directories should be affected?',
                    'What is the expected outcome?',
                    'Are there any safety considerations?'
                ]
            })
        
        return prompts
    
    def _generate_ambiguity_clarifications(self, request: str) -> List[Dict[str, Any]]:
        """Generate clarification options for ambiguous requests."""
        return [{
            'type': 'disambiguation',
            'message': f"The request '{request}' is too ambiguous. Please provide more details:",
            'clarification_questions': [
                'What specific action do you want to perform?',
                'Which files or directories are involved?',
                'What is the expected result?'
            ],
            'example_alternatives': [
                'list all Python files',
                'delete temporary files', 
                'start the development server',
                'run the test suite'
            ]
        }]
    
    def _assess_safety_risks(self, request: str) -> List[str]:
        """Assess potential safety risks in the request."""
        warnings = []
        request_lower = request.lower()
        
        # Check for destructive operations
        destructive_keywords = ['delete', 'remove', 'rm', 'clean', 'wipe', 'destroy', 'kill']
        if any(keyword in request_lower for keyword in destructive_keywords):
            warnings.append("Request contains potentially destructive operations")
        
        # Check for system-level operations
        system_keywords = ['sudo', 'admin', 'root', 'system', 'service']
        if any(keyword in request_lower for keyword in system_keywords):
            warnings.append("Request may require system-level privileges")
        
        # Check for broad scope operations
        broad_scope_keywords = ['all', 'everything', 'entire', 'whole']
        if any(keyword in request_lower for keyword in broad_scope_keywords):
            warnings.append("Request has broad scope - consider limiting to specific targets")
        
        return warnings


# Convenience function
def create_prompt_handler(model=None, project_context: Dict[str, Any] = None) -> EnhancedPromptHandler:
    """Create an enhanced prompt handler."""
    return EnhancedPromptHandler(model=model, project_context=project_context)


# Testing function
def test_prompt_handler():
    """Test the enhanced prompt handler."""
    handler = create_prompt_handler()
    
    test_requests = [
        "list files",                                      # Simple
        "search for TODOs and clean unused files",         # Compound
        "clean up the project",                           # Contextual
        "start the server... you know which one",        # Partial
        "fix it",                                         # Ambiguous
    ]
    
    print("🔍 Enhanced Prompt Handler Test")
    print("=" * 50)
    
    for request in test_requests:
        print(f"\\nAnalyzing: '{request}'")
        analysis = handler.analyze_request(request)
        print(f"Type: {analysis['request_type'].value}")
        print(f"Strategy: {analysis['disambiguation_strategy'].value}")
        print(f"Complexity: {analysis['complexity_score']:.2f}")
        if analysis['warnings']:
            print(f"Warnings: {', '.join(analysis['warnings'])}")


if __name__ == "__main__":
    test_prompt_handler()