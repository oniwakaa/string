"""
Global GPU Lock Module

Provides a shared threading lock to prevent concurrent GPU operations
across all models (intent classifier, embeddings, GGUF main model).
"""

import threading
import logging

logger = logging.getLogger(__name__)

# Global GPU lock to prevent concurrent model operations
_gpu_lock = threading.Lock()

def get_gpu_lock():
    """Get the global GPU lock for coordinating model operations."""
    return _gpu_lock

def with_gpu_lock(func):
    """Decorator to automatically wrap function calls with GPU lock."""
    def wrapper(*args, **kwargs):
        with _gpu_lock:
            logger.debug("🔒 Acquired GPU lock for model operation")
            try:
                result = func(*args, **kwargs)
                logger.debug("🔓 Released GPU lock after model operation")
                return result
            except Exception as e:
                logger.debug("🔓 Released GPU lock after error")
                raise
    return wrapper