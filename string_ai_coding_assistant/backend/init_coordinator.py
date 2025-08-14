# Generated for robust sequential initialization
"""
Initialization Coordinator for Sequential Model Loading

Enforces strict sequentialization of heavy operations during service startup
to prevent GPU memory conflicts and concurrent model loading issues.
"""

import asyncio
import logging
import threading
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass
from enum import Enum
from typing import Dict, Any, Optional, Callable, Awaitable, List
import os

logger = logging.getLogger(__name__)


class InitPhase(Enum):
    """Initialization phases that must be executed sequentially."""
    IDLE = "idle"
    GGUF_MODEL_LOADING = "gguf_model_loading"
    EMBEDDING_MODEL_LOADING = "embedding_model_loading"
    MEMOS_INITIALIZATION = "memos_initialization"
    CODEBASE_LOADING = "codebase_loading"
    SERVICE_READY = "service_ready"
    ERROR = "error"


@dataclass
class InitPhaseResult:
    """Result of an initialization phase."""
    success: bool
    phase: InitPhase
    duration_seconds: float
    error_message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class InitializationCoordinator:
    """
    Coordinates sequential initialization of heavy operations to prevent
    GPU memory conflicts and ensure robust startup across platforms.
    """
    
    def __init__(self):
        self.current_phase: InitPhase = InitPhase.IDLE
        self._lock = threading.RLock()
        self._phase_results: List[InitPhaseResult] = []
        self._force_sequential = self._check_force_sequential()
        self._startup_start_time: Optional[float] = None
        self._phase_start_time: Optional[float] = None
        
        logger.info(f"InitializationCoordinator initialized (force_sequential={self._force_sequential})")
    
    def _check_force_sequential(self) -> bool:
        """Check if sequential initialization is forced by environment or platform."""
        # Environment override
        if os.getenv('STRING_FORCE_SEQUENTIAL_INIT', 'false').lower() in ('true', '1', 'yes'):
            return True
            
        # Auto-detect platform needs
        import platform
        system = platform.system()
        arch = platform.machine()
        
        # Apple Silicon always needs sequential due to unified memory
        if system == "Darwin" and arch in ['arm64', 'aarch64']:
            return True
            
        # Low memory systems
        import psutil
        total_memory_gb = psutil.virtual_memory().total / (1024**3)
        if total_memory_gb < 12:  # Less than 12GB RAM
            return True
            
        return False
    
    @asynccontextmanager
    async def phase_context(self, phase: InitPhase, 
                           description: Optional[str] = None):
        """
        Context manager for executing an initialization phase with proper
        sequencing, timing, and error handling.
        """
        phase_desc = description or f"Phase {phase.value}"
        
        # Wait for previous phases if sequential
        if self._force_sequential:
            # Acquire lock for sequential execution
            with self._lock:
                # Only wait if we're not in an idle/ready state (i.e., previous phase is still running)
                if self.current_phase not in [InitPhase.IDLE, InitPhase.SERVICE_READY]:
                    await self._wait_for_phase_completion()
                
                # Set current phase
                self.current_phase = phase
                self._phase_start_time = time.time()
                
                if self._startup_start_time is None:
                    self._startup_start_time = self._phase_start_time
                
                logger.info(f"🚀 Starting {phase_desc}")
                
                try:
                    yield
                    
                    # Phase completed successfully
                    duration = time.time() - self._phase_start_time
                    result = InitPhaseResult(
                        success=True,
                        phase=phase,
                        duration_seconds=duration
                    )
                    self._phase_results.append(result)
                    
                    # Transition to IDLE to allow next phase
                    self.current_phase = InitPhase.IDLE
                    
                    logger.info(f"✅ Completed {phase_desc} in {duration:.2f}s")
                    
                except Exception as e:
                    # Phase failed
                    duration = time.time() - self._phase_start_time
                    result = InitPhaseResult(
                        success=False,
                        phase=phase,
                        duration_seconds=duration,
                        error_message=str(e)
                    )
                    self._phase_results.append(result)
                    self.current_phase = InitPhase.ERROR
                    
                    logger.error(f"❌ Failed {phase_desc} after {duration:.2f}s: {e}")
                    raise
                
                finally:
                    self._phase_start_time = None
        else:
            # Non-sequential execution (still tracked but no locking)
            self.current_phase = phase
            self._phase_start_time = time.time()
            
            if self._startup_start_time is None:
                self._startup_start_time = self._phase_start_time
            
            logger.info(f"🚀 Starting {phase_desc}")
            
            try:
                yield
                
                # Phase completed successfully
                duration = time.time() - self._phase_start_time
                result = InitPhaseResult(
                    success=True,
                    phase=phase,
                    duration_seconds=duration
                )
                self._phase_results.append(result)
                
                # Transition to IDLE to allow next phase
                self.current_phase = InitPhase.IDLE
                
                logger.info(f"✅ Completed {phase_desc} in {duration:.2f}s")
                
            except Exception as e:
                # Phase failed
                duration = time.time() - self._phase_start_time
                result = InitPhaseResult(
                    success=False,
                    phase=phase,
                    duration_seconds=duration,
                    error_message=str(e)
                )
                self._phase_results.append(result)
                self.current_phase = InitPhase.ERROR
                
                logger.error(f"❌ Failed {phase_desc} after {duration:.2f}s: {e}")
                raise
            
            finally:
                self._phase_start_time = None
    
    
    async def _wait_for_phase_completion(self, max_wait: float = 300.0):
        """Wait for the current phase to complete before proceeding."""
        start_wait = time.time()
        phase_to_wait_for = self.current_phase
        
        while (self.current_phase == phase_to_wait_for 
               and self.current_phase not in [InitPhase.IDLE, InitPhase.SERVICE_READY, InitPhase.ERROR] 
               and time.time() - start_wait < max_wait):
            await asyncio.sleep(0.1)
        
        if time.time() - start_wait >= max_wait and self.current_phase == phase_to_wait_for:
            raise TimeoutError(f"Timeout waiting for phase {phase_to_wait_for} to complete")
    
    async def execute_gguf_model_loading(self, load_func: Callable[[], Awaitable[Any]]) -> Any:
        """Execute GGUF model loading phase with proper sequencing."""
        async with self.phase_context(InitPhase.GGUF_MODEL_LOADING, "GGUF Model Loading"):
            return await load_func()
    
    async def execute_embedding_model_loading(self, load_func: Callable[[], Awaitable[Any]]) -> Any:
        """Execute embedding model loading phase with proper sequencing."""
        async with self.phase_context(InitPhase.EMBEDDING_MODEL_LOADING, "Embedding Model Loading"):
            return await load_func()
    
    async def execute_memos_initialization(self, init_func: Callable[[], Awaitable[Any]]) -> Any:
        """Execute MemOS initialization phase with proper sequencing."""
        async with self.phase_context(InitPhase.MEMOS_INITIALIZATION, "MemOS Initialization"):
            return await init_func()
    
    async def execute_codebase_loading(self, load_func: Callable[[], Awaitable[Any]]) -> Any:
        """Execute codebase loading phase with proper sequencing."""
        async with self.phase_context(InitPhase.CODEBASE_LOADING, "Codebase Loading"):
            return await load_func()
    
    def mark_service_ready(self):
        """Mark the service as fully initialized and ready."""
        with self._lock:
            self.current_phase = InitPhase.SERVICE_READY
            
            if self._startup_start_time:
                total_duration = time.time() - self._startup_start_time
                logger.info(f"🎉 Service initialization completed in {total_duration:.2f}s")
                
                # Log phase summary
                for result in self._phase_results:
                    status = "✅" if result.success else "❌"
                    logger.info(f"  {status} {result.phase.value}: {result.duration_seconds:.2f}s")
    
    def get_initialization_status(self) -> Dict[str, Any]:
        """Get detailed initialization status."""
        with self._lock:
            total_duration = None
            if self._startup_start_time:
                if self.current_phase == InitPhase.SERVICE_READY:
                    # Find the last successful phase
                    last_result = next((r for r in reversed(self._phase_results) if r.success), None)
                    if last_result:
                        total_duration = sum(r.duration_seconds for r in self._phase_results if r.success)
                else:
                    total_duration = time.time() - self._startup_start_time
            
            return {
                "current_phase": self.current_phase.value,
                "force_sequential": self._force_sequential,
                "total_duration_seconds": total_duration,
                "phase_results": [
                    {
                        "phase": r.phase.value,
                        "success": r.success,
                        "duration_seconds": r.duration_seconds,
                        "error_message": r.error_message,
                        "metadata": r.metadata or {}
                    }
                    for r in self._phase_results
                ],
                "is_ready": self.current_phase == InitPhase.SERVICE_READY,
                "has_error": self.current_phase == InitPhase.ERROR
            }
    
    def get_current_phase_info(self) -> Dict[str, Any]:
        """Get information about the current phase."""
        with self._lock:
            phase_duration = None
            if self._phase_start_time:
                phase_duration = time.time() - self._phase_start_time
            
            return {
                "phase": self.current_phase.value,
                "phase_duration_seconds": phase_duration,
                "is_sequential": self._force_sequential
            }
    
    def reset(self):
        """Reset the coordinator for a new initialization cycle."""
        with self._lock:
            self.current_phase = InitPhase.IDLE
            self._phase_results.clear()
            self._startup_start_time = None
            self._phase_start_time = None
            logger.info("InitializationCoordinator reset")


# Global coordinator instance
_coordinator: Optional[InitializationCoordinator] = None


def get_init_coordinator() -> InitializationCoordinator:
    """Get the global initialization coordinator instance."""
    global _coordinator
    if _coordinator is None:
        _coordinator = InitializationCoordinator()
    return _coordinator


def reset_init_coordinator():
    """Reset the global initialization coordinator."""
    global _coordinator
    if _coordinator:
        _coordinator.reset()
    else:
        _coordinator = InitializationCoordinator()


# Export main interface
__all__ = ['InitPhase', 'InitPhaseResult', 'InitializationCoordinator', 
           'get_init_coordinator', 'reset_init_coordinator']