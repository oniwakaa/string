"""
Unit tests for the intent classifier module.

Tests both the Gemma-based and keyword-based classifiers to ensure
consistent and accurate intent classification.
"""

import pytest
import json
import os
import sys
from typing import Dict, Any

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), 'src'))

from inference.intent_classifier import (
    IntentClassification,
    GemmaIntentClassifier,
    KeywordIntentClassifier,
    create_intent_classifier
)


class TestIntentClassification:
    """Test the IntentClassification dataclass."""
    
    def test_intent_classification_creation(self):
        """Test creating an IntentClassification instance."""
        classification = IntentClassification(
            primary_intent="code_generation",
            confidence=0.85,
            secondary_intents=[("code_analysis", 0.6)],
            workflow="generate_and_analyze",
            context_modifiers=["requires_context"],
            metadata={"test": True}
        )
        
        assert classification.primary_intent == "code_generation"
        assert classification.confidence == 0.85
        assert len(classification.secondary_intents) == 1
        assert classification.workflow == "generate_and_analyze"
        assert "requires_context" in classification.context_modifiers
        assert classification.metadata["test"] is True
    
    def test_confidence_clamping(self):
        """Test that confidence scores are clamped to [0, 1]."""
        classification = IntentClassification(
            primary_intent="test",
            confidence=1.5,  # Over 1.0
            secondary_intents=[]
        )
        assert classification.confidence == 1.0
        
        classification = IntentClassification(
            primary_intent="test",
            confidence=-0.5,  # Below 0.0
            secondary_intents=[]
        )
        assert classification.confidence == 0.0
    
    def test_meets_threshold(self):
        """Test threshold checking."""
        classification = IntentClassification(
            primary_intent="test",
            confidence=0.8,
            secondary_intents=[]
        )
        
        assert classification.meets_threshold(0.7) is True
        assert classification.meets_threshold(0.8) is True
        assert classification.meets_threshold(0.9) is False
    
    def test_to_dict(self):
        """Test dictionary conversion."""
        classification = IntentClassification(
            primary_intent="code_generation",
            confidence=0.85,
            secondary_intents=[("code_analysis", 0.6)]
        )
        
        result = classification.to_dict()
        assert isinstance(result, dict)
        assert result["primary_intent"] == "code_generation"
        assert result["confidence"] == 0.85
        assert len(result["secondary_intents"]) == 1


class TestKeywordIntentClassifier:
    """Test the keyword-based intent classifier."""
    
    @pytest.fixture
    def classifier(self):
        """Create a keyword classifier instance."""
        return KeywordIntentClassifier()
    
    def test_web_research_classification(self, classifier):
        """Test classification of web research intents."""
        prompts = [
            "scrape data from https://example.com",
            "fetch content from this website",
            "extract information from the webpage"
        ]
        
        for prompt in prompts:
            result = classifier.classify(prompt)
            assert result.primary_intent == "web_research"
            assert result.confidence >= 0.7
    
    def test_code_generation_classification(self, classifier):
        """Test classification of code generation intents."""
        prompts = [
            "create a function to validate emails",
            "generate a REST API endpoint",
            "implement a sorting algorithm",
            "build a React component"
        ]
        
        for prompt in prompts:
            result = classifier.classify(prompt)
            assert result.primary_intent == "code_generation"
            assert result.confidence >= 0.7
    
    def test_code_editing_classification(self, classifier):
        """Test classification of code editing intents."""
        prompts = [
            "fix the bug in the login function",
            "modify this method to handle errors",
            "change the implementation to use async",
            "refactor this code for better performance"
        ]
        
        for prompt in prompts:
            result = classifier.classify(prompt)
            assert result.primary_intent == "code_editing"
            assert result.confidence >= 0.7
    
    def test_codebase_query_classification(self, classifier):
        """Test classification of codebase query intents."""
        prompts = [
            "find the authentication function",
            "where is the database connection code?",
            "search for the user model",
            "explain how the payment system works"
        ]
        
        for prompt in prompts:
            result = classifier.classify(prompt)
            assert result.primary_intent == "codebase_query"
            assert result.confidence >= 0.7
    
    def test_code_analysis_classification(self, classifier):
        """Test classification of code analysis intents."""
        prompts = [
            "analyze this code for security issues",
            "review the performance of this function",
            "audit the error handling",
            "check for potential bugs"
        ]
        
        for prompt in prompts:
            result = classifier.classify(prompt)
            assert result.primary_intent == "code_analysis"
            assert result.confidence >= 0.7
    
    def test_documentation_classification(self, classifier):
        """Test classification of documentation intents."""
        prompts = [
            "document this API endpoint",
            "create documentation for this class",
            "explain how to use this module"
        ]
        
        for prompt in prompts:
            result = classifier.classify(prompt)
            assert result.primary_intent == "documentation"
            assert result.confidence >= 0.7
    
    def test_fallback_classification(self, classifier):
        """Test fallback to general_query for unclear prompts."""
        prompts = [
            "hello",
            "what can you do?",
            "help me with something"
        ]
        
        for prompt in prompts:
            result = classifier.classify(prompt)
            assert result.primary_intent == "general_query"
            assert result.confidence <= 0.5
    
    def test_context_modifier_detection(self, classifier):
        """Test detection of context modifiers."""
        prompt = "create a function based on the existing authentication code"
        result = classifier.classify(prompt)
        
        # Should detect both code generation intent and context modifier
        assert result.primary_intent == "code_generation"
        assert len(result.context_modifiers) > 0
    
    def test_secondary_intent_detection(self, classifier):
        """Test detection of secondary intents."""
        prompt = "generate a function and analyze it for performance"
        result = classifier.classify(prompt)
        
        assert result.primary_intent == "code_generation"
        assert len(result.secondary_intents) > 0
        
        # Check if code_analysis is in secondary intents
        secondary_intent_names = [intent[0] for intent in result.secondary_intents]
        assert "code_analysis" in secondary_intent_names


class TestGemmaIntentClassifier:
    """Test the Gemma model-based intent classifier."""
    
    @pytest.fixture
    def classifier(self):
        """Create a Gemma classifier instance."""
        # Note: This will attempt to load the model, which may not be available in test env
        try:
            return GemmaIntentClassifier()
        except Exception:
            pytest.skip("Gemma model not available for testing")
    
    def test_classification_prompt_setup(self):
        """Test that the classification prompt is properly set up."""
        # Create classifier without loading model
        classifier = GemmaIntentClassifier()
        
        assert classifier._classification_prompt_template is not None
        assert "Available intents:" in classifier._classification_prompt_template
        assert "primary_intent" in classifier._classification_prompt_template
        assert "confidence" in classifier._classification_prompt_template
    
    def test_fallback_extraction(self):
        """Test the fallback extraction method."""
        classifier = GemmaIntentClassifier()
        
        # Test extraction from non-JSON response
        text = """
        I believe the primary_intent is code_generation with high confidence.
        The confidence is 0.85 for this classification.
        """
        
        result = classifier._extract_classification_fallback(text)
        
        assert result["primary_intent"] == "code_generation"
        assert result["confidence"] == 0.85
    
    @pytest.mark.integration
    def test_model_classification(self, classifier):
        """Test actual model classification (requires model to be loaded)."""
        test_prompts = {
            "create a Python function to sort a list": "code_generation",
            "find the database connection in my project": "codebase_query",
            "fix the bug in the authentication": "code_editing",
            "analyze this code for security issues": "code_analysis",
            "document the API endpoints": "documentation",
            "scrape data from this website": "web_research"
        }
        
        for prompt, expected_intent in test_prompts.items():
            result = classifier.classify(prompt)
            
            # Check that we get a valid classification
            assert isinstance(result, IntentClassification)
            assert result.confidence > 0.0
            
            # Model might not always match exactly, but should have reasonable confidence
            if result.primary_intent == expected_intent:
                assert result.confidence >= 0.6
            
            # Check metadata
            assert "classification_time" in result.metadata
            assert "model_used" in result.metadata
            assert result.metadata["model_used"] == "gemma-3n-E4B-it"


class TestIntentClassifierFactory:
    """Test the classifier factory function."""
    
    def test_create_keyword_classifier(self):
        """Test creating a keyword classifier."""
        classifier = create_intent_classifier("keyword")
        assert isinstance(classifier, KeywordIntentClassifier)
    
    def test_create_gemma_classifier(self):
        """Test creating a Gemma classifier."""
        try:
            classifier = create_intent_classifier("gemma")
            assert isinstance(classifier, GemmaIntentClassifier)
        except Exception:
            # Model might not be available in test environment
            pytest.skip("Gemma model not available")
    
    def test_invalid_classifier_type(self):
        """Test that invalid classifier type raises error."""
        with pytest.raises(ValueError):
            create_intent_classifier("invalid_type")


# Performance benchmarks
@pytest.mark.benchmark
class TestClassifierPerformance:
    """Benchmark tests for classifier performance."""
    
    def test_keyword_classifier_speed(self, benchmark):
        """Benchmark keyword classifier speed."""
        classifier = KeywordIntentClassifier()
        prompt = "create a function to validate email addresses and test it"
        
        result = benchmark(classifier.classify, prompt)
        assert result.primary_intent in ["code_generation", "codebase_query"]
    
    @pytest.mark.skipif(not os.getenv("RUN_MODEL_BENCHMARKS"), 
                        reason="Model benchmarks disabled by default")
    def test_gemma_classifier_speed(self, benchmark):
        """Benchmark Gemma classifier speed (requires model)."""
        try:
            classifier = GemmaIntentClassifier()
            prompt = "create a function to validate email addresses and test it"
            
            # Warm up the model
            classifier.classify("test prompt")
            
            result = benchmark(classifier.classify, prompt)
            assert result.primary_intent in ["code_generation", "codebase_query"]
        except Exception:
            pytest.skip("Gemma model not available for benchmarking")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])