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
from typing import Dict, Any, Optional, Union, Tuple
from pathlib import Path
from collections import defaultdict
import logging

# Import model loaders
try:
    from llama_cpp import Llama
except ImportError:
    Llama = None

logger = logging.getLogger(__name__)

def _get_string_home() -> Path:
    """Resolve STRING_HOME path cross-platform."""
    # Env override
    if "STRING_HOME" in os.environ:
        return Path(os.environ["STRING_HOME"]).expanduser().resolve()
    # Windows vs *nix defaults
    if os.name == "nt":
        base = Path(os.environ.get("USERPROFILE", str(Path.home())))
        return (base / ".string").resolve()
    return (Path.home() / ".string").resolve()


def _manifest_to_internal_config(manifest: Dict[str, Any], string_home: Path) -> Dict[str, Any]:
    """Convert STRING_HOME/config/models.json manifest to ModelManager internal config structure."""
    internal: Dict[str, Any] = {
        "models": {},
        "agent_mapping": {},
        "memory_limits": {},
        "performance": {},
    }

    models_dir = string_home / "models"
    for item in manifest.get("models", []):
        name = item.get("name")
        filename = item.get("filename")
        local_dir = item.get("local_dir")
        if not all([name, filename, local_dir]):
            continue
        model_path = (models_dir / local_dir / filename).as_posix()
        # Special configuration for classifier models
        if name == "Gemma-3-270m-it-classifier":
            gpu_layers = int(os.getenv("STRING_CLASSIFIER_ON_GPU", "0"))
        else:
            gpu_layers = -1  # Default GPU acceleration for main models
            
        entry = {
            "loader": "gguf",
            "path": model_path,
            "config": {
                "n_ctx": 16384,
                "n_gpu_layers": gpu_layers,
            },
            "priority": "high" if "SmolLM3-3B" in name else "medium",
            "purpose": "classifier" if name == "Gemma-3-270m-it-classifier" else "general",
        }
        # Full name key
        internal["models"][name] = entry
        # Base alias (strip trailing quantization suffix after first dash)
        base_alias = name.split("-")[0]
        if base_alias and base_alias not in internal["models"]:
            internal["models"][base_alias] = entry

    return internal


class ModelManager:
    """
    Centralized model manager with automatic lifecycle management, 
    memory monitoring, and lazy loading capabilities.
    """
    
    def __init__(self, config_path: Optional[str] = None):
        self.string_home: Path = _get_string_home()
        self.config_path = config_path  # May be None -> use manifest
        self.config = self._load_config()
        self.loaded_models: Dict[str, Any] = {}
        self.model_metadata: Dict[str, Dict] = {}
        self.last_used: Dict[str, float] = {}
        self._lock = threading.RLock()
        self._decode_locks: Dict[str, threading.RLock] = defaultdict(threading.RLock)
        self._memory_monitor_active = False
        self._start_memory_monitor()
        
        logger.info("ModelManager initialized successfully")
        
        # Preload critical models if configured
        if self.config.get("performance", {}).get("preload_critical"):
            self._preload_critical_models()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load model configuration from STRING_HOME manifest or explicit path."""
        # Prefer explicit path when given
        if self.config_path:
            try:
                with open(self.config_path, 'r') as f:
                    config = json.load(f)
                logger.info(f"Loaded model configuration from {self.config_path}")
                return config
            except FileNotFoundError:
                logger.error(f"Configuration file not found: {self.config_path}")
                # Fall through to STRING_HOME manifest
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON in configuration file: {e}")
                # Fall through to STRING_HOME manifest

        # Load STRING_HOME manifest
        manifest_path = self.string_home / "config" / "models.json"
        try:
            with open(manifest_path, 'r') as f:
                manifest = json.load(f)
            internal = _manifest_to_internal_config(manifest, self.string_home)
            logger.info(f"Loaded model configuration from {manifest_path}")
            return internal
        except FileNotFoundError:
            logger.error(
                f"Model manifest not found: {manifest_path}. Ensure models are installed under ${self.string_home}/models "
                "and manifest exists at ${STRING_HOME}/config/models.json (run: python setup_cli.py --with-models)."
            )
            return {"models": {}, "agent_mapping": {}, "memory_limits": {}}
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in model manifest {manifest_path}: {e}")
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
    
    def _normalize_model_key(self, requested: str) -> str:
        """Normalize incoming model names to manifest-valid keys.
        Accepted canonical keys include:
          - SmolLM3-3B-Q4_K_M
          - Gemma-3n-E4B-it-Q5_K_S
          - Qwen3-1.7B-Q5_K_M
        Fallbacks: map base aliases like 'SmolLM3-3B' -> 'SmolLM3-3B-Q4_K_M' if present.
        """
        models = self.config.get("models", {})
        if requested in models:
            return requested
        alias_map = {
            "SmolLM3-3B": "SmolLM3-3B-Q4_K_M",
            "Gemma-3n-E4B-it": "gemma-3n-E4B-it-Q5_K_S",
            "gemma-3n-E4B-it": "gemma-3n-E4B-it-Q5_K_S",  # Case variant
            "Qwen3-1.7B": "Qwen3-1.7B-Q5_K_M",
            "gemma-3-270m-it": "Gemma-3-270m-it-classifier",  # Classifier alias
        }
        if requested in alias_map and alias_map[requested] in models:
            return alias_map[requested]
        # Try base alias prefix
        base_alias = requested.split("-")[0]
        candidates = [k for k in models.keys() if k.startswith(base_alias)]
        if candidates:
            return candidates[0]
        # No mapping
        available = ", ".join(models.keys()) or "<none>"
        raise ValueError(
            f"Model '{requested}' not found in configuration. Available: {available}. "
            f"Ensure {(_get_string_home() / 'config' / 'models.json').as_posix()} contains a valid entry, "
            "or run: python setup_cli.py --with-models"
        )

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
        if model_name not in self.config.get("models", {}):
            model_name = self._normalize_model_key(model_name)
        
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
    
    def get_model_with_decode_lock(self, model_name: str):
        """
        Get model and its decode lock for sync operations to prevent concurrent decode calls.
        
        Usage:
            model, decode_lock = model_manager.get_model_with_decode_lock("SmolLM3-3B")
            with decode_lock:
                result = model(...)  # Only one decode at a time per model
        
        Returns:
            tuple: (model_instance, decode_lock)
        """
        model = self.get_model(model_name)
        decode_lock = self._decode_locks[model_name]
        return model, decode_lock
    
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
            raise RuntimeError(
                f"Model file not found: {model_path}. Ensure models are installed under "
                f"{(self.string_home / 'models').as_posix()} (run: python setup_cli.py --with-models)."
            )
        
        try:
            if loader == "gguf":
                if Llama is None:
                    raise RuntimeError("llama-cpp-python not available for GGUF models")
                
                # Extract llama-cpp specific parameters
                llama_config = {
                    "model_path": model_path,
                    "n_ctx": min(config.get("n_ctx", 16384), 16384),  # Restore original context size
                    "n_batch": min(config.get("n_batch", 512), 512),   # Larger batch for better GPU utilization
                    "n_threads": min(config.get("n_threads", 8), 8),
                    "n_gpu_layers": config.get("n_gpu_layers", 20),    # Conservative GPU layers for Apple Silicon
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

    def get_model_info(self, model_name: str) -> Dict[str, Any]:
        """
        Get information about a specific model (loaded or configured).
        
        Args:
            model_name: Name of the model to get info for
            
        Returns:
            Dict containing model information including loader type, path, etc.
            
        Raises:
            ValueError: If model not found in configuration
        """
        # Normalize model name
        if model_name not in self.config.get("models", {}):
            model_name = self._normalize_model_key(model_name)
        
        if model_name not in self.config.get("models", {}):
            raise ValueError(f"Model '{model_name}' not found in configuration")
        
        model_config = self.config["models"][model_name]
        
        # Base info from configuration
        info = {
            "name": model_name,
            "loader": model_config.get("loader", "unknown"),
            "path": model_config.get("path", ""),
            "purpose": model_config.get("purpose", "general"),
            "is_loaded": model_name in self.loaded_models
        }
        
        # Add runtime metadata if loaded
        if model_name in self.model_metadata:
            metadata = self.model_metadata[model_name]
            info.update({
                "loaded_at": metadata.get("loaded_at", 0),
                "last_used": self.last_used.get(model_name, 0)
            })
        
        return info

    def get_memory_stats(self) -> Dict[str, Any]:
        """Compatibility shim used by health/status callers.
        Returns lightweight statistics about loaded models.
        """
        with self._lock:
            return {
                "currently_loaded": len(self.loaded_models),
                "loaded_model_names": list(self.loaded_models.keys()),
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


def initialize_model_manager(config_path: Optional[str] = None) -> ModelManager:
    """Initialize and return a ModelManager instance (STRING_HOME-aware by default)."""
    return ModelManager(config_path=config_path)


# Create singleton instance
model_manager = initialize_model_manager()