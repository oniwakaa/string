"""
Production-ready Model Registry with Serial Loading and Single-Flight Protection

This module provides async-enabled model loading with strict serialization during
startup and single-flight protection during runtime to prevent concurrent model
loading that exhausts GPU memory.
"""

import asyncio
import logging
import os
import time
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum
from collections import defaultdict

from .manager import model_manager, ModelManager

logger = logging.getLogger(__name__)


class ModelStatus(Enum):
    PENDING = "pending"
    LOADING = "loading" 
    READY = "ready"
    FAILED = "failed"


@dataclass
class ModelInfo:
    name: str
    status: ModelStatus
    load_time_ms: Optional[float] = None
    error: Optional[str] = None
    instance: Optional[Any] = None


class ModelRegistry:
    """
    Production model registry with async single-flight loading and startup coordination.
    
    Wraps the existing ModelManager to add:
    - Serial preloading during startup
    - Single-flight protection for concurrent requests
    - Async-compatible API
    - Observability and health reporting
    
    ModelManager remains the single source of truth for loading logic and caching.
    """
    
    def __init__(self, model_manager: ModelManager):
        self._model_manager = model_manager
        self._models: Dict[str, ModelInfo] = {}
        self._loading_locks: Dict[str, asyncio.Lock] = {}
        self._decode_semaphores: Dict[str, asyncio.Semaphore] = defaultdict(lambda: asyncio.Semaphore(1))
        self._global_lock = asyncio.Lock()
        self._startup_complete = False
        self._startup_start_time: Optional[float] = None
        self._startup_end_time: Optional[float] = None
        
        logger.info("ModelRegistry initialized with decode concurrency protection")
        
    async def preload_models_serial(self, model_names: List[str], critical_only: bool = False) -> Dict[str, bool]:
        """
        Preload models serially during startup to prevent GPU memory conflicts.
        
        Args:
            model_names: List of resolved model names from ModelManager config
            critical_only: If True, fail fast on any model failure
            
        Returns:
            Dict mapping model names to success status
        """
        logger.info(f"🚀 Starting serial model preload: {model_names}")
        self._startup_start_time = time.time()
        results = {}
        
        for model_name in model_names:
            try:
                logger.info(f"📥 Loading model {model_name}...")
                start_time = time.time()
                
                # Use single-flight loading
                model_instance = await self._load_model_single_flight(model_name)
                
                load_time_ms = (time.time() - start_time) * 1000
                
                self._models[model_name] = ModelInfo(
                    name=model_name,
                    status=ModelStatus.READY,
                    load_time_ms=load_time_ms,
                    instance=model_instance
                )
                
                results[model_name] = True
                logger.info(f"✅ Model {model_name} loaded in {load_time_ms:.1f}ms")
                
            except Exception as e:
                error_msg = str(e)
                self._models[model_name] = ModelInfo(
                    name=model_name,
                    status=ModelStatus.FAILED,
                    error=error_msg
                )
                results[model_name] = False
                logger.error(f"❌ Model {model_name} failed to load: {error_msg}")
                
                if critical_only:
                    logger.error("Critical model failed - aborting startup")
                    break
        
        self._startup_end_time = time.time()
        startup_duration = self._startup_end_time - self._startup_start_time
        self._startup_complete = True
        
        success_count = sum(results.values())
        total_count = len(model_names)
        logger.info(f"🏁 Model preload complete: {success_count}/{total_count} in {startup_duration:.2f}s")
        
        return results
    
    async def get_model(self, model_name: str) -> Any:
        """
        Get a model instance with single-flight loading protection.
        
        Args:
            model_name: Resolved model name from ModelManager config
            
        Returns:
            Model instance
            
        Raises:
            RuntimeError: If model fails to load
        """
        # Fast path for ready models
        if model_name in self._models and self._models[model_name].status == ModelStatus.READY:
            return self._models[model_name].instance
        
        # Handle failed models
        if model_name in self._models and self._models[model_name].status == ModelStatus.FAILED:
            error_msg = self._models[model_name].error or "Unknown error"
            raise RuntimeError(f"Model {model_name} previously failed to load: {error_msg}")
        
        # Load the model with single-flight protection
        return await self._load_model_single_flight(model_name)
    
    async def get_model_with_decode_lock(self, model_name: str):
        """
        Get model and its decode semaphore to prevent concurrent decode calls.
        
        Usage:
            model, semaphore = await registry.get_model_with_decode_lock("SmolLM3-3B")
            async with semaphore:
                result = model(...)  # Only one decode at a time per model
        
        Returns:
            tuple: (model_instance, decode_semaphore)
        """
        model = await self.get_model(model_name)
        semaphore = self._decode_semaphores[model_name]
        return model, semaphore
    
    async def _load_model_single_flight(self, model_name: str) -> Any:
        """Load model with single-flight protection - only one load per model name."""
        async with self._global_lock:
            # Get or create lock for this model
            if model_name not in self._loading_locks:
                self._loading_locks[model_name] = asyncio.Lock()
        
        # Single-flight loading per model
        async with self._loading_locks[model_name]:
            # Check if another coroutine already loaded it
            if model_name in self._models and self._models[model_name].status == ModelStatus.READY:
                return self._models[model_name].instance
            
            # Mark as loading
            self._models[model_name] = ModelInfo(
                name=model_name,
                status=ModelStatus.LOADING
            )
            
            try:
                # Call the underlying model manager in thread executor to avoid blocking
                loop = asyncio.get_event_loop()
                model_instance = await loop.run_in_executor(
                    None, 
                    self._model_manager.get_model, 
                    model_name
                )
                
                # Update status
                self._models[model_name] = ModelInfo(
                    name=model_name,
                    status=ModelStatus.READY,
                    instance=model_instance
                )
                
                return model_instance
                
            except Exception as e:
                # Mark as failed
                self._models[model_name] = ModelInfo(
                    name=model_name,
                    status=ModelStatus.FAILED,
                    error=str(e)
                )
                raise
    
    def is_ready(self, model_name: str) -> bool:
        """Check if a model is ready for use."""
        return (model_name in self._models and 
                self._models[model_name].status == ModelStatus.READY)
    
    def list_ready(self) -> List[str]:
        """List all ready model names."""
        return [name for name, info in self._models.items() 
                if info.status == ModelStatus.READY]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get registry statistics for observability."""
        stats = {
            "startup_complete": self._startup_complete,
            "total_models": len(self._models),
            "ready_models": len(self.list_ready()),
            "failed_models": len([m for m in self._models.values() if m.status == ModelStatus.FAILED]),
            "models": {}
        }
        
        if self._startup_start_time and self._startup_end_time:
            stats["startup_duration_ms"] = (self._startup_end_time - self._startup_start_time) * 1000
        
        for name, info in self._models.items():
            stats["models"][name] = {
                "status": info.status.value,
                "load_time_ms": info.load_time_ms,
                "error": info.error
            }
        
        return stats


# Global registry instance
_registry: Optional[ModelRegistry] = None


def get_model_registry() -> ModelRegistry:
    """Get or create the global model registry."""
    global _registry
    if _registry is None:
        _registry = ModelRegistry(model_manager)
    return _registry


def get_preload_config() -> Dict[str, List[str]]:
    """
    Get model preload configuration from models.json with env var overrides.
    
    Returns:
        Dict with 'critical' and 'additional' model lists
    """
    # Get available models from ModelManager config
    available_models = model_manager.config.get("models", {})
    
    # Default critical models (first available from priority list)
    default_critical = []
    priority_models = ["SmolLM3-3B-Q4_K_M", "SmolLM3", "gemma-3n-E4B-it-Q5_K_S"]
    for candidate in priority_models:
        if candidate in available_models:
            default_critical.append(candidate)
            break
    
    # Environment overrides
    critical_env = os.getenv('CRITICAL_MODELS', '')
    additional_env = os.getenv('PRELOAD_MODELS', '')
    
    critical_models = critical_env.split(',') if critical_env else default_critical
    
    # Additional models: all available except critical
    if additional_env:
        additional_models = additional_env.split(',')
    else:
        # Default: preload up to 2 additional models beyond critical
        all_available = list(available_models.keys())
        additional_models = [m for m in all_available if m not in critical_models][:2]
    
    # Filter and clean
    critical_models = [m.strip() for m in critical_models if m.strip() and m.strip() in available_models]
    additional_models = [m.strip() for m in additional_models if m.strip() and m.strip() in available_models and m.strip() not in critical_models]
    
    return {
        "critical": critical_models,
        "additional": additional_models
    }