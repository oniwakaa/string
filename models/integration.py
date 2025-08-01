"""
Integration helpers for ModelManager

This module provides simple helper functions to integrate the ModelManager
with existing agent code and MemOS components.
"""

import logging
from typing import Any, Optional, Dict
from .manager import model_manager

logger = logging.getLogger(__name__)

def get_model_manager():
    """
    Get the singleton ModelManager instance.
    
    Returns:
        ModelManager: The singleton model manager
    """
    return model_manager

def get_agent_model(agent_name: str) -> Any:
    """
    Get the appropriate model for a specific agent.
    
    Args:
        agent_name: Name of the agent (e.g., 'CodebaseExpertAgent')
        
    Returns:
        Model instance configured for the agent
        
    Example:
        model = get_agent_model('CodebaseExpertAgent')
        response = model.create_completion(prompt="...", max_tokens=512)
    """
    try:
        return model_manager.get_model_for_agent(agent_name)
    except Exception as e:
        logger.error(f"Failed to get model for agent {agent_name}: {e}")
        raise

def get_llm_for_memos(model_name: Optional[str] = None, **kwargs) -> Any:
    """
    Get a model specifically configured for MemOS integration.
    
    Args:
        model_name: Optional specific model name. If None, uses default embedding model.
        **kwargs: Additional configuration parameters
        
    Returns:
        Model instance suitable for MemOS
        
    Example:
        extractor_llm = get_llm_for_memos()
    """
    try:
        if model_name is None:
            # Default to embedding model for MemOS
            model_name = "Qwen3-Embedding-0.6B-GGUF"
        
        model = model_manager.get_model(model_name)
        
        # Apply any additional configuration
        if hasattr(model, 'update_config') and kwargs:
            model.update_config(**kwargs)
            
        return model
        
    except Exception as e:
        logger.error(f"Failed to get MemOS model {model_name}: {e}")
        raise

def create_model_adapter(agent_name: str) -> 'ModelAdapter':
    """
    Create a model adapter for drop-in replacement during migration.
    
    Args:
        agent_name: Name of the agent
        
    Returns:
        ModelAdapter: Wrapper that provides backward compatibility
    """
    return ModelAdapter(agent_name)

class ModelAdapter:
    """
    Adapter class that provides backward compatibility for existing agent code.
    This allows gradual migration from direct model loading to ModelManager.
    """
    
    def __init__(self, agent_name: str):
        self.agent_name = agent_name
        self._model = None
        self._model_loaded = False
    
    @property
    def model(self) -> Any:
        """Lazy load and return the model."""
        if not self._model_loaded:
            self._model = get_agent_model(self.agent_name)
            self._model_loaded = True
        return self._model
    
    def create_completion(self, prompt: str, **kwargs) -> Dict:
        """
        Create a completion using the managed model.
        
        Args:
            prompt: Input prompt
            **kwargs: Additional parameters
            
        Returns:
            Completion response
        """
        try:
            # Get model configuration from ModelManager
            model_config = model_manager.config["models"]
            agent_mapping = model_manager.config.get("agent_mapping", {})
            model_name = agent_mapping.get(self.agent_name)
            
            if model_name and model_name in model_config:
                config = model_config[model_name].get("config", {})
                
                # Merge default config with provided kwargs
                completion_kwargs = {
                    "max_tokens": config.get("max_tokens", 512),
                    "temperature": config.get("temperature", 0.7),
                    **kwargs
                }
            else:
                completion_kwargs = kwargs
            
            return self.model.create_completion(prompt, **completion_kwargs)
            
        except Exception as e:
            logger.error(f"Completion failed for agent {self.agent_name}: {e}")
            raise
    
    def embed(self, text: str) -> list:
        """
        Generate embeddings using the managed model.
        
        Args:
            text: Text to embed
            
        Returns:
            List of embedding values
        """
        try:
            if hasattr(self.model, 'embed'):
                return self.model.embed(text)
            else:
                raise NotImplementedError("Model does not support embeddings")
        except Exception as e:
            logger.error(f"Embedding failed for agent {self.agent_name}: {e}")
            raise
    
    def close(self):
        """Clean up resources (handled by ModelManager)."""
        # ModelManager handles cleanup automatically
        pass

def get_model_status() -> Dict[str, Any]:
    """
    Get status information about all models.
    
    Returns:
        Dictionary with model status information
    """
    try:
        return {
            "loaded_models": model_manager.get_loaded_models(),
            "memory_usage": model_manager.get_memory_usage(),
            "total_models_available": len(model_manager.config.get("models", {})),
            "agent_mappings": model_manager.config.get("agent_mapping", {})
        }
    except Exception as e:
        logger.error(f"Failed to get model status: {e}")
        return {"error": str(e)}

def preload_agent_models(agent_names: list) -> Dict[str, bool]:
    """
    Preload models for specific agents.
    
    Args:
        agent_names: List of agent names
        
    Returns:
        Dictionary mapping agent names to success status
    """
    results = {}
    for agent_name in agent_names:
        try:
            get_agent_model(agent_name)
            results[agent_name] = True
            logger.info(f"Preloaded model for agent: {agent_name}")
        except Exception as e:
            results[agent_name] = False
            logger.error(f"Failed to preload model for agent {agent_name}: {e}")
    
    return results

def unload_agent_model(agent_name: str) -> bool:
    """
    Unload the model for a specific agent.
    
    Args:
        agent_name: Name of the agent
        
    Returns:
        True if model was unloaded successfully
    """
    try:
        agent_mapping = model_manager.config.get("agent_mapping", {})
        model_name = agent_mapping.get(agent_name)
        
        if model_name:
            return model_manager.unload_model(model_name)
        else:
            logger.warning(f"No model mapping found for agent: {agent_name}")
            return False
            
    except Exception as e:
        logger.error(f"Failed to unload model for agent {agent_name}: {e}")
        return False

# Legacy compatibility functions
def load_model(model_name: str) -> Any:
    """Legacy function for backward compatibility."""
    logger.warning("load_model() is deprecated. Use get_agent_model() or get_model_manager().get_model()")
    return model_manager.get_model(model_name)

def get_model(model_name: str) -> Any:
    """Legacy function for backward compatibility."""
    logger.warning("get_model() is deprecated. Use get_agent_model() or get_model_manager().get_model()")
    return model_manager.get_model(model_name)