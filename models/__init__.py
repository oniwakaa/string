"""
Models package for AI Coding Assistant

This package provides model management capabilities for the multi-agent system.
"""

from .manager import model_manager, ModelManager
from .integration import get_agent_model, get_model_manager

__all__ = ["model_manager", "ModelManager", "get_agent_model", "get_model_manager"]