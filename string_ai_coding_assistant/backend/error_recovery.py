# Generated for robust error handling and recovery
"""
Error Recovery and Model Normalization for GGUF Service

Provides robust error handling, model key normalization, and automatic
recovery strategies for common initialization failures.
"""

import logging
import os
import platform
import psutil
import re
import time
from dataclasses import dataclass
from typing import Dict, Any, Optional, List, Tuple, Union
import subprocess

logger = logging.getLogger(__name__)


@dataclass
class RecoveryAction:
    """Represents a recovery action that can be taken for an error."""
    name: str
    description: str
    priority: int  # Lower = higher priority
    can_retry: bool = True
    requires_restart: bool = False
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class ErrorContext:
    """Context information for an error during initialization."""
    error_type: str
    error_message: str
    phase: str
    system_info: Dict[str, Any]
    config_snapshot: Dict[str, Any]
    suggested_actions: List[RecoveryAction]


class ModelKeyNormalizer:
    """Centralized model key normalization for consistent model loading."""
    
    ALIAS_MAP = {
        # SmolLM variants
        "SmolLM3": "SmolLM3-3B-Q4_K_M",
        "SmolLM3-3B": "SmolLM3-3B-Q4_K_M", 
        "smollm": "SmolLM3-3B-Q4_K_M",
        "smollm3": "SmolLM3-3B-Q4_K_M",
        
        # Gemma variants
        "Gemma": "gemma-3n-E4B-it-Q5_K_S",
        "gemma": "gemma-3n-E4B-it-Q5_K_S",
        "Gemma-3n-E4B-it": "gemma-3n-E4B-it-Q5_K_S",
        "gemma-3n-E4B-it": "gemma-3n-E4B-it-Q5_K_S",
        
        # Qwen variants
        "Qwen": "Qwen3-1.7B-Q5_K_M",
        "qwen": "Qwen3-1.7B-Q5_K_M",
        "Qwen3": "Qwen3-1.7B-Q5_K_M",
        "Qwen3-1.7B": "Qwen3-1.7B-Q5_K_M",
    }
    
    @classmethod
    def normalize_model_key(cls, requested_key: str, available_models: Dict[str, Any]) -> str:
        """
        Normalize a requested model key to a valid configuration key.
        
        Args:
            requested_key: The model key requested
            available_models: Available models in configuration
            
        Returns:
            Normalized model key
            
        Raises:
            ValueError: If no valid mapping can be found
        """
        if not requested_key:
            raise ValueError("Model key cannot be empty")
        
        # Direct match
        if requested_key in available_models:
            return requested_key
        
        # Alias mapping
        if requested_key in cls.ALIAS_MAP:
            canonical = cls.ALIAS_MAP[requested_key]
            if canonical in available_models:
                return canonical
        
        # Case-insensitive matching
        lower_requested = requested_key.lower()
        for model_key in available_models:
            if model_key.lower() == lower_requested:
                return model_key
        
        # Partial prefix matching
        for model_key in available_models:
            if model_key.lower().startswith(lower_requested):
                return model_key
        
        # Base name extraction (before first dash)
        base_name = requested_key.split('-')[0]
        for model_key in available_models:
            if model_key.startswith(base_name):
                return model_key
        
        # No match found
        available_list = list(available_models.keys())
        raise ValueError(
            f"Model '{requested_key}' not found in configuration. "
            f"Available models: {', '.join(available_list) if available_list else 'none'}. "
            f"Ensure models are installed under STRING_HOME/models or run setup with --with-models."
        )


class ErrorRecoveryManager:
    """Manages error recovery strategies for robust initialization."""
    
    def __init__(self):
        self.recovery_history: List[Dict[str, Any]] = []
        self.max_recovery_attempts = 3
        self.system_info = self._gather_system_info()
        
    def _gather_system_info(self) -> Dict[str, Any]:
        """Gather system information for error diagnosis."""
        try:
            return {
                "platform": platform.system(),
                "arch": platform.machine(),
                "python_version": platform.python_version(),
                "total_memory_gb": psutil.virtual_memory().total / (1024**3),
                "available_memory_gb": psutil.virtual_memory().available / (1024**3),
                "cpu_cores": psutil.cpu_count(logical=False) or 1,
                "has_metal": self._detect_metal(),
                "has_cuda": self._detect_cuda(),
            }
        except Exception as e:
            logger.warning(f"Could not gather system info: {e}")
            return {"error": str(e)}
    
    def _detect_metal(self) -> bool:
        """Detect if Metal GPU acceleration is available."""
        if platform.system() != "Darwin":
            return False
        try:
            result = subprocess.run(['system_profiler', 'SPDisplaysDataType'], 
                                  capture_output=True, text=True, timeout=5)
            return 'Apple' in result.stdout and any(chip in result.stdout for chip in ['M1', 'M2', 'M3', 'M4'])
        except:
            return platform.machine() in ['arm64', 'aarch64']
    
    def _detect_cuda(self) -> bool:
        """Detect if CUDA is available."""
        try:
            result = subprocess.run(['nvidia-smi'], capture_output=True, timeout=5)
            return result.returncode == 0
        except:
            return False
    
    def analyze_error(self, error: Exception, phase: str, 
                     config: Dict[str, Any]) -> ErrorContext:
        """
        Analyze an error and provide recovery suggestions.
        
        Args:
            error: The exception that occurred
            phase: The initialization phase where error occurred
            config: Configuration snapshot when error occurred
            
        Returns:
            ErrorContext with analysis and suggested actions
        """
        error_type = type(error).__name__
        error_message = str(error)
        
        # Determine recovery actions based on error patterns
        actions = self._determine_recovery_actions(error_type, error_message, phase)
        
        return ErrorContext(
            error_type=error_type,
            error_message=error_message,
            phase=phase,
            system_info=self.system_info,
            config_snapshot=config.copy(),
            suggested_actions=actions
        )
    
    def _determine_recovery_actions(self, error_type: str, error_message: str, 
                                  phase: str) -> List[RecoveryAction]:
        """Determine appropriate recovery actions for an error."""
        actions = []
        
        # GPU Memory Exhaustion (Apple Metal)
        if ("kIOGPUCommandBufferCallbackErrorOutOfMemory" in error_message or
            "Metal Performance Shaders" in error_message or
            "Insufficient Memory" in error_message):
            
            actions.extend([
                RecoveryAction(
                    name="reduce_gpu_layers",
                    description="Reduce n_gpu_layers to prevent GPU memory exhaustion",
                    priority=1,
                    metadata={"new_n_gpu_layers": 10}
                ),
                RecoveryAction(
                    name="reduce_batch_size", 
                    description="Reduce n_batch to lower memory pressure",
                    priority=2,
                    metadata={"new_n_batch": 64}
                ),
                RecoveryAction(
                    name="fallback_cpu",
                    description="Fallback to CPU-only inference",
                    priority=3,
                    metadata={"new_n_gpu_layers": 0}
                )
            ])
        
        # Model Loading Failures
        elif error_type in ["RuntimeError", "FileNotFoundError"] and phase == "gguf_model_loading":
            if "Model file not found" in error_message or "not found" in error_message:
                actions.append(RecoveryAction(
                    name="check_model_installation",
                    description="Verify model files are installed under STRING_HOME/models",
                    priority=1,
                    can_retry=False
                ))
            
            if "ModelManager" in error_message:
                actions.append(RecoveryAction(
                    name="fallback_direct_loading",
                    description="Fallback to direct llama-cpp loading",
                    priority=2
                ))
        
        # Context Length Issues
        elif ("llama_decode returned -3" in error_message or
              "context" in error_message.lower()):
            
            actions.extend([
                RecoveryAction(
                    name="reduce_context_length",
                    description="Reduce n_ctx to fit model constraints",
                    priority=1,
                    metadata={"new_n_ctx": 4096}
                ),
                RecoveryAction(
                    name="reduce_parallelism",
                    description="Disable parallel processing",
                    priority=2,
                    metadata={"new_n_parallel": 1}
                )
            ])
        
        # MemOS Import/Initialization Failures
        elif (error_type == "RuntimeError" and 
              ("MemOS" in error_message or "memos" in error_message.lower())):
            
            actions.append(RecoveryAction(
                name="disable_memos",
                description="Continue without MemOS memory features",
                priority=1,
                metadata={"disable_memos": True}
            ))
        
        # General fallback actions
        if not actions:
            actions.extend([
                RecoveryAction(
                    name="conservative_config",
                    description="Apply conservative settings for stability",
                    priority=1
                ),
                RecoveryAction(
                    name="restart_service",
                    description="Restart service with clean state",
                    priority=10,
                    requires_restart=True
                )
            ])
        
        return sorted(actions, key=lambda a: a.priority)
    
    def apply_recovery_action(self, action: RecoveryAction, 
                            current_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply a recovery action to the configuration.
        
        Args:
            action: Recovery action to apply
            current_config: Current configuration
            
        Returns:
            Modified configuration
        """
        logger.info(f"Applying recovery action: {action.name} - {action.description}")
        
        config = current_config.copy()
        metadata = action.metadata or {}
        
        if action.name == "reduce_gpu_layers":
            new_layers = metadata.get("new_n_gpu_layers", 10)
            self._set_config_value(config, ["model", "gpu_memory", "n_gpu_layers"], new_layers)
        
        elif action.name == "reduce_batch_size":
            new_batch = metadata.get("new_n_batch", 64)
            self._set_config_value(config, ["model", "generation", "n_batch"], new_batch)
        
        elif action.name == "fallback_cpu":
            self._set_config_value(config, ["model", "gpu_memory", "n_gpu_layers"], 0)
            self._set_config_value(config, ["model", "gpu_memory", "max_gpu_memory_mb"], 0)
        
        elif action.name == "reduce_context_length":
            new_ctx = metadata.get("new_n_ctx", 4096)
            self._set_config_value(config, ["model", "generation", "n_ctx"], new_ctx)
            self._set_config_value(config, ["model", "context", "startup_n_ctx"], new_ctx // 2)
        
        elif action.name == "reduce_parallelism":
            new_parallel = metadata.get("new_n_parallel", 1)
            self._set_config_value(config, ["model", "generation", "n_parallel"], new_parallel)
        
        elif action.name == "conservative_config":
            # Apply multiple conservative settings
            self._set_config_value(config, ["model", "gpu_memory", "n_gpu_layers"], 5)
            self._set_config_value(config, ["model", "generation", "n_batch"], 32)
            self._set_config_value(config, ["model", "generation", "n_ctx"], 2048)
            self._set_config_value(config, ["model", "context", "startup_n_ctx"], 1024)
        
        elif action.name == "disable_memos":
            # Mark MemOS as disabled for this session
            config["_recovery_flags"] = config.get("_recovery_flags", {})
            config["_recovery_flags"]["disable_memos"] = True
        
        # Record recovery action
        self.recovery_history.append({
            "timestamp": time.time(),
            "action": action.name,
            "description": action.description,
            "config_changes": metadata
        })
        
        return config
    
    def _set_config_value(self, config: Dict[str, Any], path: List[str], value: Any):
        """Set a nested configuration value."""
        current = config
        for key in path[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        current[path[-1]] = value
    
    def get_recovery_guidance(self, error_context: ErrorContext) -> str:
        """
        Generate human-readable guidance for recovering from an error.
        
        Args:
            error_context: Context of the error
            
        Returns:
            Formatted guidance string
        """
        guidance = [
            f"❌ Error during {error_context.phase}: {error_context.error_type}",
            f"   Message: {error_context.error_message}",
            "",
            "🔧 Suggested recovery actions:"
        ]
        
        for i, action in enumerate(error_context.suggested_actions[:3], 1):
            guidance.append(f"   {i}. {action.description}")
            if action.metadata:
                details = ", ".join(f"{k}={v}" for k, v in action.metadata.items())
                guidance.append(f"      ({details})")
        
        # System-specific guidance
        if error_context.system_info.get("has_metal") and "Memory" in error_context.error_message:
            guidance.extend([
                "",
                "💡 Apple Silicon specific guidance:",
                "   • Unified memory requires conservative GPU layer limits",
                "   • Try setting n_gpu_layers between 5-15 for stable operation",
                "   • Reduce batch size (n_batch=64) for lower memory pressure"
            ])
        
        return "\n".join(guidance)


# Global recovery manager instance
_recovery_manager: Optional[ErrorRecoveryManager] = None


def get_recovery_manager() -> ErrorRecoveryManager:
    """Get the global error recovery manager instance."""
    global _recovery_manager
    if _recovery_manager is None:
        _recovery_manager = ErrorRecoveryManager()
    return _recovery_manager


def normalize_model_key(key: str, available_models: Dict[str, Any]) -> str:
    """Normalize a model key using the global normalizer."""
    return ModelKeyNormalizer.normalize_model_key(key, available_models)


# Export main interface
__all__ = ['ErrorContext', 'RecoveryAction', 'ErrorRecoveryManager', 
           'ModelKeyNormalizer', 'get_recovery_manager', 'normalize_model_key']