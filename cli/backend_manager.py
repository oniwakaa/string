#!/usr/bin/env python3
"""
Backend Service Manager

Manages the FastAPI backend service lifecycle, ensuring it's running when needed
and providing health check and auto-start functionality.
"""

import asyncio
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional, Tuple, Dict, Any
import psutil
import httpx
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, TaskID
from rich.panel import Panel
from rich.text import Text

from .runtime_home import get_string_home

console = Console()

class BackendManager:
    """Manages the FastAPI backend service lifecycle."""
    
    def __init__(self):
        self.default_port = 8000
        self.host = "127.0.0.1"
        self.backend_url = f"http://{self.host}:{self.default_port}"
        self.health_endpoint = f"{self.backend_url}/health"
        # Identifier for module-based process launch (python -m ...)
        self.process_identifier = "string_ai_coding_assistant.backend.service"
        self.pid_file = get_string_home() / "storage" / ".backend.pid"
        self.log_file = get_string_home() / "storage" / "backend.log"
        self.pipx_python = self._get_pipx_python()
        
    def is_backend_running(self) -> Tuple[bool, Optional[int]]:
        """
        Check if the backend service is running.
        
        Returns:
            Tuple[bool, Optional[int]]: (is_running, pid)
        """
        # First check if PID file exists and process is alive
        if self.pid_file.exists():
            try:
                with open(self.pid_file, 'r') as f:
                    pid = int(f.read().strip())
                
                if psutil.pid_exists(pid):
                    proc = psutil.Process(pid)
                    # Check if it's actually our backend process
                    if self.process_identifier in ' '.join(proc.cmdline()):
                        return True, pid
                else:
                    # PID file exists but process is dead, clean up
                    self.pid_file.unlink()
            except (ValueError, FileNotFoundError, psutil.Error):
                if self.pid_file.exists():
                    self.pid_file.unlink()
        
        # Check by port if PID check failed
        try:
            for proc in psutil.process_iter(['pid', 'cmdline']):
                cmdline = proc.info.get('cmdline', [])
                if cmdline and self.process_identifier in ' '.join(cmdline):
                    # Found the process, update PID file
                    with open(self.pid_file, 'w') as f:
                        f.write(str(proc.info['pid']))
                    return True, proc.info['pid']
        except (psutil.Error, PermissionError):
            pass
            
        return False, None
    
    def _get_pipx_python(self) -> str:
        """Get the Python interpreter from pipx venv."""
        package_name = "string-ai-coding-assistant"
        pipx_venv_path = Path.home() / ".local" / "pipx" / "venvs" / package_name
        
        # Try different possible Python executable paths
        possible_paths = [
            pipx_venv_path / "bin" / "python",  # Unix-like
            pipx_venv_path / "Scripts" / "python.exe",  # Windows
        ]
        
        for python_path in possible_paths:
            if python_path.exists():
                return str(python_path)
        
        # Fallback to current Python if pipx venv not found
        console.print("⚠️  pipx venv not found, using current Python interpreter")
        return sys.executable
    
    async def health_check(self, timeout: float = 5.0) -> bool:
        """
        Check if the backend service is healthy via HTTP.
        
        Args:
            timeout (float): Timeout for the health check request
            
        Returns:
            bool: True if backend is healthy
        """
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.get(self.health_endpoint)
                return response.status_code == 200
        except (httpx.RequestError, httpx.TimeoutException):
            return False
    
    def start_backend(self, detached: bool = True) -> Tuple[bool, Optional[int]]:
        """
        Start the backend service with robust process management and logging.
        
        Args:
            detached (bool): Whether to run in detached mode
            
        Returns:
            Tuple[bool, Optional[int]]: (success, pid)
        """
        # Use the packaged script entry point instead of module path
        script_name = "run_gguf_service"
        
        # Ensure storage directory exists
        self.pid_file.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            # Check if port is available
            port_to_use = self._find_available_port()
            if port_to_use != self.default_port:
                console.print(f"⚠️  Port {self.default_port} busy, using {port_to_use}")
                self.backend_url = f"http://{self.host}:{port_to_use}"
                self.health_endpoint = f"{self.backend_url}/health"
            
            # Prepare environment with STRING_HOME and proper paths
            env = os.environ.copy()
            env['STRING_HOME'] = str(get_string_home())
            # Backend ConfigLoader expects SERVICE_HOST / SERVICE_PORT
            env['SERVICE_PORT'] = str(port_to_use)
            env['SERVICE_HOST'] = self.host
            
            # Enable dynamic initialization and error recovery
            env['STRING_DYNAMIC_INIT'] = '1'
            env['STRING_FORCE_SEQUENTIAL_INIT'] = '1'
            
            # Log details
            console.print(f"🏠 STRING_HOME: {env['STRING_HOME']}")
            console.print(f"🌍 Backend URL: {self.backend_url}")
            console.print(f"🐍 Using Python: {self.pipx_python}")
            
            if detached:
                # Rotate log file if it's getting large (> 10MB)
                self._rotate_log_if_needed()
                
                # Start in detached mode with output to log file
                with open(self.log_file, 'a') as log_f:  # Append mode for rotation
                    # Write startup header
                    import datetime
                    timestamp = datetime.datetime.now().isoformat()
                    log_f.write(f"\n{'='*60}\n")
                    log_f.write(f"Backend startup at {timestamp}\n")
                    log_f.write(f"Command: {script_name} (via pipx script)\n")
                    log_f.write(f"URL: {self.backend_url}\n")
                    log_f.write(f"PID will be saved to: {self.pid_file}\n")
                    log_f.write(f"{'='*60}\n")
                    log_f.flush()
                    
                    # Use the packaged script from pipx venv
                    script_path = Path(self.pipx_python).parent / script_name
                    
                    # Use start_new_session for process group management (cross-platform)
                    proc = subprocess.Popen(
                        [str(script_path)],
                        env=env,
                        stdout=log_f,
                        stderr=subprocess.STDOUT,
                        start_new_session=True
                    )
                
                # Wait a moment to ensure process started
                time.sleep(0.5)
                
                # Check if process is still running
                try:
                    proc.poll()
                    if proc.returncode is not None:
                        # Process died immediately
                        console.print("❌ Backend process died immediately after startup")
                        self._show_recent_logs(lines=20)
                        return False, None
                except:
                    pass
                
                # Save PID
                with open(self.pid_file, 'w') as f:
                    f.write(str(proc.pid))
                
                return True, proc.pid
            else:
                # Start in foreground mode
                script_path = Path(self.pipx_python).parent / script_name
                proc = subprocess.Popen(
                    [str(script_path)],
                    env=env
                )
                return True, proc.pid
                
        except Exception as e:
            console.print(f"❌ Failed to start backend service: {e}")
            # Show recent logs if available
            self._show_recent_logs(lines=30)
            
            # Enhanced error diagnostics
            console.print(Panel(
                "[red]Startup Failure Diagnostics[/red]\\n\\n"
                "💡 [cyan]Common causes and solutions:[/cyan]\\n"
                "• Missing models: run setup_cli.py --with-models\\n"
                "• MemOS not installed: pip install the memos package\\n"
                "• Build issues: reinstall llama-cpp-python with platform flags\\n"
                "• Port conflicts: backend will auto-select available port\\n"
                "• Permission issues: check STRING_HOME directory permissions\\n"
                "• Memory constraints: ensure sufficient RAM for model loading",
                title="🔧 Troubleshooting",
                border_style="red"
            ))
            return False, None
    
    def _rotate_log_if_needed(self, max_size_mb: int = 10):
        """
        Rotate log file if it exceeds the maximum size.
        
        Args:
            max_size_mb: Maximum log file size in MB before rotation
        """
        try:
            if self.log_file.exists():
                size_mb = self.log_file.stat().st_size / (1024 * 1024)
                if size_mb > max_size_mb:
                    # Keep last 3 rotations
                    for i in range(2, 0, -1):
                        old_log = self.log_file.with_suffix(f'.{i}.log')
                        new_log = self.log_file.with_suffix(f'.{i+1}.log')
                        if old_log.exists():
                            if new_log.exists():
                                new_log.unlink()
                            old_log.rename(new_log)
                    
                    # Move current log to .1
                    backup_log = self.log_file.with_suffix('.1.log')
                    if backup_log.exists():
                        backup_log.unlink()
                    self.log_file.rename(backup_log)
                    
                    console.print(f"🔄 [dim]Rotated backend log (was {size_mb:.1f}MB)[/dim]")
        except Exception as e:
            # Log rotation failure shouldn't stop startup
            console.print(f"⚠️  [dim]Log rotation failed: {e}[/dim]")
    
    def get_log_tail_stream(self, lines: int = 50):
        """
        Generator that yields recent log lines for live monitoring.
        
        Args:
            lines: Number of recent lines to yield
            
        Yields:
            str: Log lines
        """
        if self.log_file.exists():
            try:
                with open(self.log_file, 'r') as f:
                    log_lines = f.readlines()
                    recent_lines = log_lines[-lines:] if len(log_lines) > lines else log_lines
                    for line in recent_lines:
                        yield line.rstrip()
            except Exception as e:
                yield f"Error reading log: {e}"
        else:
            yield "Log file does not exist"
    
    async def ensure_backend_running(self, cancellable: bool = True) -> bool:
        """
        Ensure the backend service is running and healthy with Rich progress indicator.
        Uses health polling with exponential backoff instead of fixed timeouts.
        
        Args:
            cancellable (bool): Allow user to cancel with Ctrl+C
            
        Returns:
            bool: True if backend is running and healthy, False if failed or cancelled
        """
        # Check if already running and healthy
        is_running, pid = self.is_backend_running()
        if is_running and await self.health_check():
            return True
        
        # If running but not healthy, try to restart
        if is_running:
            console.print("⚠️  Backend running but unhealthy, restarting...")
            self.stop_backend(pid)
            time.sleep(2)
        
        # Start the backend process
        console.print("🚀 Starting backend service...")
        success, pid = self.start_backend()
        
        if not success:
            return False
        
        # Wait for backend to become healthy with Rich progress
        return await self._wait_for_backend_health(pid, cancellable)
    
    def stop_backend(self, pid: Optional[int] = None) -> bool:
        """
        Stop the backend service.
        
        Args:
            pid (Optional[int]): Specific PID to stop, or None to find it
            
        Returns:
            bool: True if successfully stopped
        """
        if pid is None:
            is_running, pid = self.is_backend_running()
            if not is_running:
                return True
        
        try:
            if pid:
                proc = psutil.Process(pid)
                proc.terminate()
                
                # Wait for graceful termination
                try:
                    proc.wait(timeout=10)
                except psutil.TimeoutExpired:
                    # Force kill if necessary
                    proc.kill()
                    proc.wait(timeout=5)
            
            # Clean up PID file
            if self.pid_file.exists():
                self.pid_file.unlink()
                
            return True
            
        except (psutil.Error, ProcessLookupError):
            # Process already dead, clean up PID file
            if self.pid_file.exists():
                self.pid_file.unlink()
            return True
        except Exception as e:
            console.print(f"⚠️  Error stopping backend: {e}")
            return False
    
    def get_backend_status(self) -> dict:
        """
        Get comprehensive backend status information.
        
        Returns:
            dict: Status information
        """
        is_running, pid = self.is_backend_running()
        
        status = {
            'running': is_running,
            'pid': pid,
            'healthy': False,
            'url': self.backend_url,
            'log_file': str(self.log_file) if self.log_file.exists() else None
        }
        
        if is_running:
            try:
                status['healthy'] = asyncio.run(self.health_check())
            except Exception:
                status['healthy'] = False
        
        return status
    
    def _find_available_port(self, start_port: int = None) -> int:
        """Find an available port starting from the default or specified port"""
        import socket
        
        port = start_port or self.default_port
        max_attempts = 10
        
        for attempt in range(max_attempts):
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                    sock.bind((self.host, port))
                    return port
            except OSError:
                port += 1
                continue
        
        # If we can't find a port, use the default and let the service handle it
        return self.default_port
    
    async def _wait_for_backend_health(self, pid: Optional[int], cancellable: bool = True) -> bool:
        """
        Wait for backend to become healthy with Rich progress and exponential backoff.
        
        Args:
            pid: Backend process PID
            cancellable: Allow Ctrl+C cancellation
            
        Returns:
            bool: True if healthy, False if failed or cancelled
        """
        start_time = time.time()
        attempts = 0
        base_wait = 0.5  # Start with 500ms
        max_single_wait = 15.0  # Cap individual waits at 15s
        log_show_interval = 30.0  # Show logs every 30s
        last_log_show = 0
        
        with Progress(
            SpinnerColumn(),
            TextColumn("{task.description}"),
            console=console,
            transient=False
        ) as progress:
            task = progress.add_task("[cyan]Starting backend...[/cyan]", total=None)
            
            try:
                while True:
                    attempts += 1
                    elapsed = time.time() - start_time
                    
                    # Update progress description with current phase info and failure detection
                    try:
                        health_data = await self._get_detailed_health()
                        if health_data:
                            phase_info = self._get_startup_phase_info(health_data)
                            
                            # Check for immediate failure conditions
                            if phase_info.get('should_fail_fast', False):
                                progress.update(task, description=f"[red]{phase_info['description']}[/red]")
                                actionable_error = phase_info.get('actionable_error')
                                if actionable_error:
                                    # Show actionable error information
                                    console.print(f"\n❌ [red]Backend startup failed:[/red] {actionable_error['title']}")
                                    console.print(f"📋 [yellow]Error details:[/yellow] {actionable_error['message']}")
                                    console.print("\n💡 [cyan]Recommended solutions:[/cyan]")
                                    for i, solution in enumerate(actionable_error['solutions'], 1):
                                        console.print(f"   {i}. {solution}")
                                    console.print("\n📄 [dim]Recent backend logs:[/dim]")
                                    self._show_recent_logs(lines=15)
                                return False
                            
                            # Normal phase update
                            progress.update(task, description=f"[cyan]{phase_info['description']}[/cyan] [dim]({elapsed:.1f}s, attempt {attempts})[/dim]")
                        else:
                            progress.update(task, description=f"[yellow]Bootstrapping process...[/yellow] [dim]({elapsed:.1f}s, attempt {attempts})[/dim]")
                    except:
                        # Fallback if health check fails
                        progress.update(task, description=f"[yellow]Waiting for server response...[/yellow] [dim]({elapsed:.1f}s, attempt {attempts})[/dim]")
                    
                    # Check health
                    if await self.health_check():
                        progress.update(task, description="[green]✅ Backend service is healthy![/green]")
                        console.print(f"\n✅ [green]Backend started successfully[/green] (PID: {pid}, {elapsed:.1f}s)")
                        return True
                    
                    # Show logs periodically for long waits
                    if elapsed - last_log_show >= log_show_interval:
                        last_log_show = elapsed
                        progress.update(task, description=f"[dim]Backend still initializing... showing recent logs[/dim]")
                        await asyncio.sleep(0.1)  # Brief pause for display
                        self._show_recent_logs(lines=10)
                    
                    # Calculate exponential backoff wait time
                    wait_time = min(base_wait * (1.2 ** (attempts - 1)), max_single_wait)
                    await asyncio.sleep(wait_time)
                    
            except KeyboardInterrupt:
                if cancellable:
                    progress.update(task, description="[red]❌ Startup cancelled by user[/red]")
                    console.print("\n🛑 [yellow]Backend startup cancelled. Showing recent logs:[/yellow]")
                    self._show_recent_logs(lines=15)
                    return False
                else:
                    raise
                    
        return False
    
    async def _get_detailed_health(self) -> Optional[Dict[str, Any]]:
        """
        Get detailed health information including startup phases.
        
        Returns:
            Optional[Dict]: Health data or None if unavailable
        """
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                response = await client.get(self.health_endpoint)
                if response.status_code == 200:
                    return response.json()
                return None
        except:
            return None
    
    def _get_startup_phase_info(self, health_data: Dict[str, Any]) -> Dict[str, str]:
        """
        Extract startup phase information from health data and detect failure conditions.
        
        Args:
            health_data: Health response data
            
        Returns:
            Dict with phase description, status, and failure detection
        """
        # Default fallback
        phase_info = {
            "description": "Initializing service...",
            "status": "starting",
            "should_fail_fast": False,
            "actionable_error": None
        }
        
        try:
            service = health_data.get('service', {})
            model = health_data.get('model', {})
            memos = health_data.get('memos', {})
            
            # Check for definitive failures that should stop polling
            if service.get('error') or health_data.get('status') == 'unhealthy':
                error_msg = service.get('error', 'Unknown service error')
                failed_phase = service.get('failed_phase', 'unknown')
                
                # Categorize errors for actionable feedback
                actionable_error = self._categorize_startup_error(error_msg, failed_phase)
                if actionable_error:
                    phase_info.update({
                        "description": f"❌ {actionable_error['title']}",
                        "status": "failed",
                        "should_fail_fast": True,
                        "actionable_error": actionable_error
                    })
                    return phase_info
            
            if not service.get('initialized', False):
                # Try to get init coordinator phase info if available
                if 'init_phase' in service:
                    current_phase = service['init_phase']
                    phase_duration = service.get('phase_duration_seconds', 0)
                    
                    phase_descriptions = {
                        'idle': '⏳ Service initialization starting',
                        'gguf_model_loading': '🧠 Loading GGUF model (Metal/GPU initialization)',
                        'embedding_model_loading': '🔢 Loading embedding model',
                        'memos_initialization': '💾 Initializing MemOS memory system',
                        'codebase_loading': '📁 Loading codebase context',
                        'service_ready': '✅ Service initialization complete',
                        'error': '❌ Initialization failed'
                    }
                    
                    base_description = phase_descriptions.get(current_phase, f"Phase: {current_phase}")
                    
                    # Add duration info for long-running phases
                    if phase_duration and phase_duration > 30:
                        if current_phase == 'gguf_model_loading':
                            base_description += f" (Metal init: {phase_duration:.0f}s - this is normal for Apple Silicon)"
                        else:
                            base_description += f" ({phase_duration:.0f}s)"
                    
                    phase_info['description'] = base_description
                    
                    # Detect if a phase is stuck (running too long without progress)
                    if phase_duration and phase_duration > 300:  # 5 minutes
                        if current_phase == 'gguf_model_loading':
                            phase_info['description'] += " [yellow](taking longer than expected)[/yellow]"
                        else:
                            phase_info.update({
                                "description": f"⚠️ {current_phase} appears stuck ({phase_duration:.0f}s)",
                                "status": "stuck",
                                "should_fail_fast": False  # Don't fail fast, but warn
                            })
                            
                elif service.get('error'):
                    error_msg = service.get('error', 'Unknown error')
                    actionable_error = self._categorize_startup_error(error_msg, 'service_init')
                    if actionable_error:
                        phase_info.update({
                            "description": f"❌ {actionable_error['title']}",
                            "status": "failed",
                            "should_fail_fast": True,
                            "actionable_error": actionable_error
                        })
                    else:
                        phase_info['description'] = f"❌ Service error: {error_msg[:50]}..."
                        phase_info['status'] = 'error'
                else:
                    # Infer phase from available information
                    if not model.get('loaded', False):
                        phase_info['description'] = '🧠 Loading model (Metal/GPU initialization)'
                    elif memos.get('status') == 'not_initialized':
                        phase_info['description'] = '💾 Initializing memory system'
                    else:
                        phase_info['description'] = '🔧 Finalizing service initialization'
            else:
                phase_info['description'] = '✅ Service ready'
                phase_info['status'] = 'ready'
                
        except Exception:
            # Keep default fallback
            pass
        
        return phase_info
    
    def _categorize_startup_error(self, error_msg: str, phase: str) -> Optional[Dict[str, Any]]:
        """
        Categorize startup errors into actionable categories.
        
        Args:
            error_msg: Error message from backend
            phase: Phase where error occurred
            
        Returns:
            Optional[Dict]: Actionable error information or None
        """
        error_lower = error_msg.lower()
        
        # Model loading failures
        if 'model' in error_lower and ('not found' in error_lower or 'missing' in error_lower):
            return {
                'category': 'missing_models',
                'title': 'Models not installed',
                'message': error_msg,
                'solutions': [
                    'Run: python setup_cli.py --with-models',
                    'Ensure models are in STRING_HOME/models directory',
                    'Check that model files downloaded successfully'
                ]
            }
        
        # MemOS initialization failures  
        if 'memos' in error_lower or 'memory' in error_lower:
            return {
                'category': 'memos_failure',
                'title': 'MemOS initialization failed',
                'message': error_msg,
                'solutions': [
                    'Install MemOS: pip install -e ./MemOS',
                    'Check Qdrant vector database connectivity',
                    'Verify embedding model availability'
                ]
            }
        
        # GPU/Metal failures
        if any(gpu_term in error_lower for gpu_term in ['metal', 'gpu', 'cuda', 'memory']):
            if 'out of memory' in error_lower or 'insufficient' in error_lower:
                return {
                    'category': 'gpu_memory',
                    'title': 'GPU memory exhausted',
                    'message': error_msg,
                    'solutions': [
                        'Close other GPU-intensive applications',
                        'Restart your system to clear GPU memory',
                        'Use CPU-only mode: set STRING_FORCE_CPU=1'
                    ]
                }
        
        # Permission/filesystem failures
        if 'permission' in error_lower or 'access' in error_lower:
            return {
                'category': 'permissions',
                'title': 'File permission error',
                'message': error_msg,
                'solutions': [
                    'Check STRING_HOME directory permissions',
                    'Ensure write access to log and storage directories',
                    'Run with appropriate user permissions'
                ]
            }
        
        # Port/network failures
        if 'port' in error_lower or 'address' in error_lower or 'bind' in error_lower:
            return {
                'category': 'network',
                'title': 'Network binding failed',
                'message': error_msg,
                'solutions': [
                    'Backend will auto-select available port',
                    'Check for conflicting services on port 8000',
                    'Restart if port conflicts persist'
                ]
            }
        
        return None
    
    def _show_recent_logs(self, lines: int = 20) -> None:
        """Show recent backend log entries for debugging."""
        if self.log_file.exists():
            try:
                with open(self.log_file, 'r') as f:
                    log_lines = f.readlines()
                    recent_lines = log_lines[-lines:] if len(log_lines) > lines else log_lines
                    
                if recent_lines:
                    # Use Rich panel for better formatting
                    log_content = ''.join(recent_lines).rstrip()
                    console.print(Panel(
                        log_content,
                        title=f"📝 Last {len(recent_lines)} lines from backend log",
                        border_style="dim",
                        expand=False
                    ))
                else:
                    console.print("⚠️  Backend log file is empty")
                    
            except Exception as e:
                console.print(f"⚠️  Could not read backend log: {e}")
        else:
            console.print("⚠️  Backend log file does not exist")


# Global backend manager instance
_backend_manager: Optional[BackendManager] = None

def get_backend_manager() -> BackendManager:
    """Get the global backend manager instance."""
    global _backend_manager
    if _backend_manager is None:
        _backend_manager = BackendManager()
    return _backend_manager