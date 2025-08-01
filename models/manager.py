"""
ModelManager - Centralized model lifecycle management for AI Coding Assistant

This module provides a singleton ModelManager that handles loading, unloading,
and resource management for all AI models used in the multi-agent system.
"""

import json
import os
import time
import threading
import psutil
from typing import Dict, Any, Optional, Union
from pathlib import Path
import logging

# Import model loaders
try:
    from llama_cpp import Llama
except ImportError:
    Llama = None

logger = logging.getLogger(__name__)

class ModelManager:
    """
    Centralized model manager with automatic lifecycle management, 
    memory monitoring, and lazy loading capabilities.
    """
    
    def __init__(self, config_path: str = "models/config.json"):
        self.config_path = config_path
        self.config = self._load_config()
        self.loaded_models: Dict[str, Any] = {}
        self.model_metadata: Dict[str, Dict] = {}
        self.last_used: Dict[str, float] = {}
        self._lock = threading.RLock()
        self._memory_monitor_active = False
        self._start_memory_monitor()
        
        logger.info("ModelManager initialized successfully")
        
        # Preload critical models if configured
        if self.config.get("performance", {}).get("preload_critical"):
            self._preload_critical_models()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load model configuration from JSON file."""
        try:
            with open(self.config_path, 'r') as f:
                config = json.load(f)
            logger.info(f"Loaded model configuration from {self.config_path}")
            return config
        except FileNotFoundError:
            logger.error(f"Configuration file not found: {self.config_path}")
            return {"models": {}, "agent_mapping": {}, "memory_limits": {}}
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in configuration file: {e}")
            return {"models": {}, "agent_mapping": {}, "memory_limits": {}}
    
    def _preload_critical_models(self):
        """Preload models marked as critical."""
        critical_models = self.config.get("performance", {}).get("preload_critical", [])
        for model_name in critical_models:
            try:
                self.get_model(model_name)
                logger.info(f"Preloaded critical model: {model_name}")
            except Exception as e:
                logger.warning(f"Failed to preload critical model {model_name}: {e}")
    
    def _start_memory_monitor(self):
        """Start the memory monitoring thread."""
        if not self._memory_monitor_active and self.config.get("memory_limits", {}).get("auto_eviction", False):
            self._memory_monitor_active = True
            monitor_thread = threading.Thread(target=self._memory_monitor_loop, daemon=True)
            monitor_thread.start()
            logger.info("Memory monitor started")
    
    def _memory_monitor_loop(self):
        """Background thread for memory monitoring and auto-eviction."""
        interval = self.config.get("memory_limits", {}).get("memory_check_interval", 30)
        idle_timeout = self.config.get("memory_limits", {}).get("idle_timeout_minutes", 10) * 60
        
        while self._memory_monitor_active:
            try:
                # Check memory usage
                memory_usage = psutil.virtual_memory().percent / 100.0 * psutil.virtual_memory().total / (1024**3)  # GB
                max_memory = self.config.get("memory_limits", {}).get("max_total_memory_gb", 6.0)
                
                with self._lock:
                    current_time = time.time()
                    
                    # Auto-evict idle models if memory is high
                    if memory_usage > max_memory * 0.8:  # 80% threshold
                        idle_models = [
                            name for name, last_used in self.last_used.items()
                            if current_time - last_used > idle_timeout
                        ]
                        
                        # Sort by priority (unload low priority first) and idle time
                        idle_models.sort(key=lambda x: (
                            self.config["models"].get(x, {}).get("priority", "medium") == "low",
                            current_time - self.last_used[x]
                        ), reverse=True)
                        
                        for model_name in idle_models[:2]:  # Unload up to 2 models at a time
                            self.unload_model(model_name)
                            logger.info(f"Auto-evicted idle model: {model_name}")
                
                time.sleep(interval)
                
            except Exception as e:
                logger.error(f"Error in memory monitor: {e}")
                time.sleep(interval)
    
    def get_model(self, model_name: str) -> Any:
        """
        Get a model instance, loading it if necessary.
        
        Args:
            model_name: Name of the model from configuration
            
        Returns:
            Loaded model instance
            
        Raises:
            ValueError: If model not found in configuration
            RuntimeError: If model fails to load
        """
        if model_name not in self.config["models"]:
            raise ValueError(f"Model '{model_name}' not found in configuration")
        
        with self._lock:
            # Return cached model if already loaded
            if model_name in self.loaded_models:
                self.last_used[model_name] = time.time()
                return self.loaded_models[model_name]
            
            # Load the model
            model_config = self.config["models"][model_name]
            model = self._load_model(model_name, model_config)
            
            # Cache the model and update metadata
            self.loaded_models[model_name] = model
            self.last_used[model_name] = time.time()
            self.model_metadata[model_name] = {
                "loaded_at": time.time(),
                "loader": model_config.get("loader", "unknown"),
                "purpose": model_config.get("purpose", "general")
            }
            
            logger.info(f"Successfully loaded model: {model_name}")
            return model
    
    def _load_model(self, model_name: str, model_config: Dict[str, Any]) -> Any:
        """
        Load a model based on its configuration.
        
        Args:
            model_name: Name of the model
            model_config: Model configuration dictionary
            
        Returns:
            Loaded model instance
            
        Raises:
            RuntimeError: If model fails to load
        """
        loader = model_config.get("loader", "gguf")
        model_path = model_config["path"]
        config = model_config.get("config", {})
        
        # Ensure model file exists
        if not os.path.exists(model_path):
            raise RuntimeError(f"Model file not found: {model_path}")
        
        try:
            if loader == "gguf":
                if Llama is None:
                    raise RuntimeError("llama-cpp-python not available for GGUF models")
                
                # Extract llama-cpp specific parameters
                llama_config = {
                    "model_path": model_path,
                    "n_ctx": config.get("n_ctx", 16384),
                    "n_gpu_layers": config.get("n_gpu_layers", -1),
                    "verbose": False
                }
                
                return Llama(**llama_config)
                
            elif loader == "huggingface":
                # Placeholder for HuggingFace model loading
                raise NotImplementedError("HuggingFace loader not yet implemented")
                
            elif loader == "openai":
                # Placeholder for OpenAI API integration
                raise NotImplementedError("OpenAI loader not yet implemented")
                
            else:
                raise ValueError(f"Unknown loader type: {loader}")
                
        except Exception as e:
            logger.error(f"Failed to load model {model_name}: {e}")
            raise RuntimeError(f"Model loading failed: {e}")
    
    def unload_model(self, model_name: str) -> bool:
        """
        Unload a model from memory.
        
        Args:
            model_name: Name of the model to unload
            
        Returns:
            True if model was unloaded, False if not loaded
        """
        with self._lock:
            if model_name not in self.loaded_models:
                return False
            
            try:
                # Clean up model resources
                model = self.loaded_models[model_name]
                if hasattr(model, 'close'):
                    model.close()
                
                # Remove from caches
                del self.loaded_models[model_name]
                del self.last_used[model_name]
                if model_name in self.model_metadata:
                    del self.model_metadata[model_name]
                
                logger.info(f"Unloaded model: {model_name}")
                return True
                
            except Exception as e:
                logger.error(f"Error unloading model {model_name}: {e}")
                return False
    
    def get_model_for_agent(self, agent_name: str) -> Any:
        """
        Get the appropriate model for a specific agent.
        
        Args:
            agent_name: Name of the agent
            
        Returns:
            Model instance for the agent
        """
        agent_mapping = self.config.get("agent_mapping", {})
        model_name = agent_mapping.get(agent_name)
        
        if not model_name:
            # Fallback to a default model if no specific mapping
            default_models = list(self.config.get("models", {}).keys())
            if default_models:
                model_name = default_models[0]
                logger.warning(f"No model mapping for agent {agent_name}, using default: {model_name}")
            else:
                raise ValueError(f"No models available for agent: {agent_name}")
        
        return self.get_model(model_name)
    
    def get_loaded_models(self) -> Dict[str, Dict]:
        """Get information about currently loaded models."""
        with self._lock:
            return {
                name: {
                    **self.model_metadata.get(name, {}),
                    "last_used": self.last_used.get(name, 0)
                }
                for name in self.loaded_models.keys()
            }
    
    def get_memory_usage(self) -> Dict[str, float]:
        """Get current memory usage statistics."""
        memory = psutil.virtual_memory()
        return {
            "total_gb": memory.total / (1024**3),
            "used_gb": memory.used / (1024**3),
            "available_gb": memory.available / (1024**3),
            "percent": memory.percent
        }
    
    def shutdown(self):
        """Shutdown the model manager and clean up resources."""
        logger.info("Shutting down ModelManager...")
        self._memory_monitor_active = False
        
        with self._lock:
            for model_name in list(self.loaded_models.keys()):
                self.unload_model(model_name)
        
        logger.info("ModelManager shutdown complete")


def initialize_model_manager(config_path: str = "models/config.json") -> ModelManager:
    """Initialize and return a ModelManager instance."""
    return ModelManager(config_path=config_path)


# Create singleton instance
model_manager = initialize_model_manager()