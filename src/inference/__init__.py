"""
Inference module for AI model-based operations.

This module contains model-driven components for the AI coding assistant,
including intent classification and other inference tasks.
"""

from .intent_classifier import (
    IntentClassification,
    BaseIntentClassifier,
    GemmaIntentClassifier,
    create_intent_classifier,
    get_default_classifier
)

__all__ = [
    'IntentClassification',
    'BaseIntentClassifier',
    'GemmaIntentClassifier',
    'create_intent_classifier',
    'get_default_classifier'
]