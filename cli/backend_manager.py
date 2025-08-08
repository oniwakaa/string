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
from typing import Optional, Tuple
import psutil
import httpx
from rich.console import Console

from .runtime_home import get_string_home

console = Console()

class BackendManager:
    """Manages the FastAPI backend service lifecycle."""
    
    def __init__(self):
        self.default_port = 8000
        self.host = "127.0.0.1"
        self.backend_url = f"http://{self.host}:{self.default_port}"
        self.health_endpoint = f"{self.backend_url}/health"
        self.service_module = "run_gguf_service"
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
                    if self.service_module in ' '.join(proc.cmdline()):
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
                if cmdline and self.service_module in ' '.join(cmdline):
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
        Start the backend service.
        
        Args:
            detached (bool): Whether to run in detached mode
            
        Returns:
            Tuple[bool, Optional[int]]: (success, pid)
        """
        # Find the service script - check multiple possible locations
        possible_locations = [
            # Current project directory
            Path.cwd() / f"{self.service_module}.py",
            # Parent directories (up to 3 levels)
            Path.cwd().parent / f"{self.service_module}.py",
            Path.cwd().parent.parent / f"{self.service_module}.py",
            # Package installation directory
            Path(__file__).parent.parent / f"{self.service_module}.py",
        ]
        
        service_script = None
        for location in possible_locations:
            if location.exists():
                service_script = location
                break
        
        if service_script is None:
            console.print(f"❌ Backend service script not found in any of these locations:")
            for location in possible_locations:
                console.print(f"   {location}")
            return False, None
        
        console.print(f"📁 Using service script: {service_script}")
        current_dir = service_script.parent
        
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
            env['PYTHONPATH'] = str(current_dir)
            env['STRING_HOME'] = str(get_string_home())
            env['PORT'] = str(port_to_use)
            env['HOST'] = self.host
            
            # Ensure we're in the correct working directory for the service
            console.print(f"📋 Working directory: {current_dir}")
            console.print(f"🏠 STRING_HOME: {env['STRING_HOME']}")
            console.print(f"🌍 Backend URL: {self.backend_url}")
            console.print(f"🐍 Using Python: {self.pipx_python}")
            
            if detached:
                # Start in detached mode with output to log file
                with open(self.log_file, 'w') as log_f:
                    proc = subprocess.Popen(
                        [self.pipx_python, str(service_script)],
                        cwd=str(current_dir),
                        env=env,
                        stdout=log_f,
                        stderr=subprocess.STDOUT,
                        start_new_session=True
                    )
                
                # Save PID
                with open(self.pid_file, 'w') as f:
                    f.write(str(proc.pid))
                
                return True, proc.pid
            else:
                # Start in foreground mode
                proc = subprocess.Popen(
                    [self.pipx_python, str(service_script)],
                    cwd=str(current_dir),
                    env=env
                )
                return True, proc.pid
                
        except Exception as e:
            console.print(f"❌ Failed to start backend service: {e}")
            return False, None
    
    async def ensure_backend_running(self, max_wait: float = 30.0) -> bool:
        """
        Ensure the backend service is running and healthy.
        
        Args:
            max_wait (float): Maximum time to wait for backend to become healthy
            
        Returns:
            bool: True if backend is running and healthy
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
        
        # Start the backend
        console.print("🚀 Starting backend service...")
        success, pid = self.start_backend()
        
        if not success:
            return False
        
        # Wait for backend to become healthy with exponential backoff
        start_time = time.time()
        attempts = 0
        base_wait = 0.5  # Start with 500ms
        max_single_wait = 3.0  # Cap individual waits at 3s
        
        while time.time() - start_time < max_wait:
            attempts += 1
            
            # Check health
            if await self.health_check():
                console.print(f"✅ Backend service is running and healthy (PID: {pid})")
                return True
            
            # Calculate exponential backoff wait time
            wait_time = min(base_wait * (1.5 ** (attempts - 1)), max_single_wait)
            
            # Show progress periodically
            elapsed = time.time() - start_time
            if attempts == 1 or attempts % 3 == 0:
                console.print(f"🔄 Waiting for backend health... ({elapsed:.1f}s, attempt {attempts})")
            
            await asyncio.sleep(wait_time)
        
        console.print("❌ Backend service failed to become healthy within timeout")
        # Show recent log entries for debugging
        self._show_recent_logs()
        return False
    
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
    
    def _show_recent_logs(self, lines: int = 20) -> None:
        """Show recent backend log entries for debugging."""
        if self.log_file.exists():
            try:
                with open(self.log_file, 'r') as f:
                    log_lines = f.readlines()
                    recent_lines = log_lines[-lines:] if len(log_lines) > lines else log_lines
                    
                if recent_lines:
                    console.print(f"\n📝 Last {len(recent_lines)} lines from backend log:")
                    console.print("-" * 60)
                    for line in recent_lines:
                        console.print(line.rstrip())
                    console.print("-" * 60)
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