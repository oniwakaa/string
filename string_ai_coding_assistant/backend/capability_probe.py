# Generated for robust cross-platform model initialization
"""
Dynamic Capability Probing for Cross-Platform Model Initialization

Detects system capabilities and derives safe defaults for GGUF model loading
to prevent GPU memory exhaustion and ensure sequential initialization.
"""

import logging
import os
import platform
import psutil
import subprocess
import sys
from dataclasses import dataclass
from typing import Dict, Any, Optional, Tuple
import json

logger = logging.getLogger(__name__)


@dataclass
class SystemCapabilities:
    """System capability information for dynamic configuration."""
    
    # Platform info
    platform: str
    arch: str
    python_version: str
    
    # Hardware specs
    total_memory_gb: float
    cpu_cores: int
    
    # GPU info
    has_metal: bool = False
    has_cuda: bool = False
    has_opencl: bool = False
    metal_device_name: Optional[str] = None
    cuda_device_count: int = 0
    
    # Derived safe limits
    recommended_n_gpu_layers: int = 0
    recommended_n_batch: int = 512
    recommended_n_parallel: int = 1
    recommended_max_gpu_memory_mb: int = 2048
    recommended_n_ctx: int = 8192
    recommended_startup_n_ctx: int = 4096
    
    # Feature flags
    force_sequential_init: bool = True
    enable_metal_optimization: bool = False
    metal_batch_limit: int = 64
    
    def to_config_overrides(self) -> Dict[str, Any]:
        """Convert capabilities to config override format."""
        return {
            "model": {
                "gpu_memory": {
                    "n_gpu_layers": self.recommended_n_gpu_layers,
                    "max_gpu_memory_mb": self.recommended_max_gpu_memory_mb,
                    "enable_metal_optimization": self.enable_metal_optimization,
                    "metal_batch_limit": self.metal_batch_limit,
                },
                "generation": {
                    "n_ctx": self.recommended_n_ctx,
                    "n_batch": self.recommended_n_batch,
                },
                "context": {
                    "startup_n_ctx": self.recommended_startup_n_ctx,
                    "runtime_n_ctx": self.recommended_n_ctx,
                    "context_scaling_enabled": True,
                },
                "loading": {
                    "sequential_loading": self.force_sequential_init,
                }
            },
            "_capability_probe": {
                "probed_at": "runtime",
                "platform": self.platform,
                "arch": self.arch,
                "total_memory_gb": self.total_memory_gb,
                "cpu_cores": self.cpu_cores,
                "has_metal": self.has_metal,
                "has_cuda": self.has_cuda,
                "metal_device_name": self.metal_device_name,
                "cuda_device_count": self.cuda_device_count,
            }
        }


class CapabilityProbe:
    """Cross-platform capability detection for robust model initialization."""
    
    def __init__(self):
        self.logger = logger
        
    def probe_system_capabilities(self, conservative: bool = True) -> SystemCapabilities:
        """
        Probe system capabilities and derive safe model initialization parameters.
        
        Args:
            conservative: Use conservative settings to avoid memory issues
            
        Returns:
            SystemCapabilities with recommended settings
        """
        caps = SystemCapabilities(
            platform=platform.system(),
            arch=platform.machine(),
            python_version=f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            total_memory_gb=psutil.virtual_memory().total / (1024**3),
            cpu_cores=psutil.cpu_count(logical=False) or 1,
        )
        
        # Detect GPU capabilities
        self._detect_gpu_capabilities(caps)
        
        # Derive safe limits based on platform and memory
        self._derive_safe_limits(caps, conservative=conservative)
        
        logger.info(f"System capabilities probed: {caps.platform} {caps.arch}, "
                   f"{caps.total_memory_gb:.1f}GB RAM, {caps.cpu_cores} cores")
        
        if caps.has_metal:
            logger.info(f"Metal detected: {caps.metal_device_name}, "
                       f"GPU layers: {caps.recommended_n_gpu_layers}")
        elif caps.has_cuda:
            logger.info(f"CUDA detected: {caps.cuda_device_count} devices, "
                       f"GPU layers: {caps.recommended_n_gpu_layers}")
        else:
            logger.info("GPU acceleration not detected, using CPU-only")
            
        return caps
    
    def _detect_gpu_capabilities(self, caps: SystemCapabilities) -> None:
        """Detect available GPU acceleration options."""
        
        # Check for Apple Metal (macOS)
        if caps.platform == "Darwin":
            try:
                # Use system_profiler to get GPU info
                result = subprocess.run([
                    'system_profiler', 'SPDisplaysDataType', '-json'
                ], capture_output=True, text=True, timeout=10)
                
                if result.returncode == 0:
                    displays = json.loads(result.stdout)
                    for item in displays.get('SPDisplaysDataType', []):
                        if 'sppci_model' in item:
                            model = item['sppci_model']
                            if 'Apple' in model and any(chip in model for chip in ['M1', 'M2', 'M3', 'M4']):
                                caps.has_metal = True
                                caps.metal_device_name = model
                                break
            except Exception as e:
                logger.debug(f"Could not detect Metal GPU: {e}")
                # Fallback check
                if caps.arch in ['arm64', 'aarch64']:
                    caps.has_metal = True
                    caps.metal_device_name = "Apple Silicon (detected)"
        
        # Check for CUDA (Linux/Windows)
        if caps.platform in ["Linux", "Windows"]:
            try:
                result = subprocess.run([
                    'nvidia-smi', '--query-gpu=count', '--format=csv,noheader,nounits'
                ], capture_output=True, text=True, timeout=5)
                
                if result.returncode == 0:
                    caps.has_cuda = True
                    caps.cuda_device_count = len(result.stdout.strip().split('\n'))
            except (subprocess.TimeoutExpired, FileNotFoundError):
                logger.debug("CUDA not detected or nvidia-smi not available")
        
        # Check for OpenCL as fallback
        try:
            result = subprocess.run([
                sys.executable, '-c', 
                'import pyopencl as cl; print(len(cl.get_platforms()))'
            ], capture_output=True, text=True, timeout=5)
            
            if result.returncode == 0 and int(result.stdout.strip()) > 0:
                caps.has_opencl = True
        except Exception:
            logger.debug("OpenCL not available")
    
    def _derive_safe_limits(self, caps: SystemCapabilities, conservative: bool) -> None:
        """Derive safe model loading parameters based on detected capabilities."""
        
        # Base memory allocation (conservative approach)
        available_memory_gb = caps.total_memory_gb
        
        # Reserve memory for OS and other processes
        if available_memory_gb <= 8:
            usable_memory_gb = available_memory_gb * 0.6  # 60% of total
        elif available_memory_gb <= 16:
            usable_memory_gb = available_memory_gb * 0.7  # 70% of total
        else:
            usable_memory_gb = available_memory_gb * 0.8  # 80% of total
        
        # Apple Silicon M-series specific tuning
        if caps.has_metal and caps.metal_device_name:
            if "M4" in caps.metal_device_name:
                # M4 has better memory management but still unified
                if available_memory_gb >= 16:
                    caps.recommended_n_gpu_layers = 28 if not conservative else 20
                    caps.recommended_max_gpu_memory_mb = int(usable_memory_gb * 1024 * 0.4)  # 40% for GPU
                else:
                    caps.recommended_n_gpu_layers = 15 if not conservative else 10
                    caps.recommended_max_gpu_memory_mb = int(usable_memory_gb * 1024 * 0.3)  # 30% for GPU
            elif any(chip in caps.metal_device_name for chip in ["M3", "M2", "M1"]):
                # Older M-series, more conservative
                caps.recommended_n_gpu_layers = 15 if not conservative else 10
                caps.recommended_max_gpu_memory_mb = int(usable_memory_gb * 1024 * 0.3)
            
            caps.enable_metal_optimization = True
            caps.metal_batch_limit = 128 if not conservative else 64
            caps.recommended_n_batch = 256 if not conservative else 128
            
        # NVIDIA CUDA tuning
        elif caps.has_cuda and caps.cuda_device_count > 0:
            # More aggressive GPU usage for dedicated VRAM
            caps.recommended_n_gpu_layers = 35 if not conservative else 25
            caps.recommended_max_gpu_memory_mb = 6144  # 6GB for GPU
            caps.recommended_n_batch = 512 if not conservative else 256
            caps.recommended_n_parallel = min(caps.cuda_device_count, 2)
            
        # CPU-only fallback
        else:
            caps.recommended_n_gpu_layers = 0
            caps.recommended_max_gpu_memory_mb = 0
            caps.recommended_n_batch = 256 if not conservative else 128
            caps.recommended_n_parallel = min(caps.cpu_cores // 2, 4)
        
        # Context window sizing based on available memory
        if usable_memory_gb >= 12:
            caps.recommended_n_ctx = 16384 if not conservative else 8192
            caps.recommended_startup_n_ctx = 8192 if not conservative else 4096
        elif usable_memory_gb >= 8:
            caps.recommended_n_ctx = 8192
            caps.recommended_startup_n_ctx = 4096
        else:
            caps.recommended_n_ctx = 4096
            caps.recommended_startup_n_ctx = 2048
        
        # Force sequential loading for unified memory systems
        caps.force_sequential_init = caps.has_metal or conservative
        
        logger.info(f"Derived limits: GPU layers={caps.recommended_n_gpu_layers}, "
                   f"batch={caps.recommended_n_batch}, ctx={caps.recommended_n_ctx}, "
                   f"sequential={caps.force_sequential_init}")


def get_dynamic_config_overrides(conservative: bool = None) -> Dict[str, Any]:
    """
    Get dynamic configuration overrides based on system capabilities.
    
    Args:
        conservative: Use conservative settings. None = auto-detect based on env
        
    Returns:
        Configuration overrides dictionary
    """
    if conservative is None:
        # Auto-detect based on environment variables
        conservative = os.getenv('STRING_FORCE_CONSERVATIVE', 'false').lower() in ('true', '1', 'yes')
    
    # Check if dynamic probing is enabled
    if os.getenv('STRING_DYNAMIC_INIT', '1').lower() not in ('true', '1', 'yes'):
        logger.info("Dynamic capability probing disabled by STRING_DYNAMIC_INIT")
        return {}
    
    probe = CapabilityProbe()
    capabilities = probe.probe_system_capabilities(conservative=conservative)
    
    overrides = capabilities.to_config_overrides()
    logger.info("Dynamic configuration overrides applied based on system capabilities")
    
    return overrides


def merge_config_with_capabilities(base_config: Dict[str, Any], 
                                 conservative: bool = None) -> Dict[str, Any]:
    """
    Merge base configuration with dynamic capability overrides.
    
    Args:
        base_config: Base configuration dictionary
        conservative: Use conservative settings
        
    Returns:
        Merged configuration with capability overrides
    """
    overrides = get_dynamic_config_overrides(conservative=conservative)
    
    if not overrides:
        return base_config
    
    # Deep merge overrides into base config
    merged_config = _deep_merge_dict(base_config.copy(), overrides)
    
    logger.info("Configuration merged with dynamic capability overrides")
    return merged_config


def _deep_merge_dict(base: Dict[str, Any], overrides: Dict[str, Any]) -> Dict[str, Any]:
    """Deep merge two dictionaries, with overrides taking precedence."""
    for key, value in overrides.items():
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            base[key] = _deep_merge_dict(base[key], value)
        else:
            base[key] = value
    return base


# Export main interface
__all__ = ['SystemCapabilities', 'CapabilityProbe', 'get_dynamic_config_overrides', 
           'merge_config_with_capabilities']