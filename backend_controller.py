#!/usr/bin/env python3
"""
Cross-Platform Backend Controller for AI Coding Assistant

This module provides unified process control for the backend service
across macOS, Windows, and Linux platforms. Handles start/stop/status/restart
operations with OS-specific optimizations.
"""

import os
import sys
import json
import time
import signal
import socket
import psutil
import logging
import platform
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime


@dataclass
class BackendStatus:
    """Status information for the backend service."""
    is_running: bool
    pid: Optional[int] = None
    port: Optional[int] = None
    host: Optional[str] = None
    uptime_seconds: Optional[float] = None
    memory_mb: Optional[float] = None
    cpu_percent: Optional[float] = None
    api_health: Optional[str] = None
    last_error: Optional[str] = None


class BackendController:
    """Cross-platform backend service controller."""
    
    def __init__(self, project_root: Optional[Path] = None):
        """
        Initialize the backend controller.
        
        Args:
            project_root: Path to project root (auto-detected if None)
        """
        self.project_root = Path(project_root) if project_root else Path.cwd()
        self.pid_file = self.project_root / ".backend.pid"
        self.log_file = self.project_root / "logs" / "backend.log"
        self.config_file = self.project_root / "config.yaml"
        self.service_script = self.project_root / "run_gguf_service.py"
        
        # Ensure logs directory exists
        self.log_file.parent.mkdir(exist_ok=True)
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(self.log_file),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
        # Platform detection
        self.platform = platform.system().lower()
        self.is_windows = self.platform == "windows"
        self.is_macos = self.platform == "darwin"
        self.is_linux = self.platform == "linux"
        
        self.logger.info(f"Backend controller initialized for {self.platform}")
    
    def start(self, 
              host: str = "127.0.0.1", 
              port: int = 8000, 
              background: bool = True,
              verbose: bool = False) -> Dict[str, Any]:
        """
        Start the backend service.
        
        Args:
            host: Host to bind to
            port: Port to bind to
            background: Run in background (daemon mode)
            verbose: Enable verbose logging
            
        Returns:
            Dict with start operation results
        """
        self.logger.info(f"Starting backend service on {host}:{port}")
        
        # Check if already running
        status = self.get_status()
        if status.is_running:
            return {
                "success": False,
                "message": f"Backend already running (PID: {status.pid})",
                "pid": status.pid,
                "port": status.port
            }
        
        # Check if port is available
        if not self._is_port_available(host, port):
            return {
                "success": False,
                "message": f"Port {port} is already in use",
                "host": host,
                "port": port
            }
        
        # Validate environment
        validation_result = self._validate_environment()
        if not validation_result["success"]:
            return validation_result
        
        try:
            # Prepare environment
            env = os.environ.copy()
            env.update({
                "SERVICE_HOST": host,
                "SERVICE_PORT": str(port),
                "PYTHONPATH": str(self.project_root)
            })
            
            if verbose:
                env["LOG_LEVEL"] = "DEBUG"
            
            # Platform-specific start command
            if background:
                if self.is_windows:
                    # Windows background process
                    cmd = [
                        sys.executable, str(self.service_script)
                    ]
                    process = subprocess.Popen(
                        cmd,
                        env=env,
                        cwd=str(self.project_root),
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        creationflags=subprocess.CREATE_NEW_CONSOLE if hasattr(subprocess, 'CREATE_NEW_CONSOLE') else 0
                    )
                else:
                    # Unix-like background process
                    cmd = [
                        sys.executable, str(self.service_script)
                    ]
                    process = subprocess.Popen(
                        cmd,
                        env=env,
                        cwd=str(self.project_root),
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        preexec_fn=os.setsid if hasattr(os, 'setsid') else None
                    )
            else:
                # Foreground process
                cmd = [sys.executable, str(self.service_script)]
                process = subprocess.Popen(
                    cmd,
                    env=env,
                    cwd=str(self.project_root)
                )
            
            # Store PID
            self._write_pid_file(process.pid, host, port)
            
            # Wait a moment for startup
            time.sleep(2)
            
            # Verify startup
            if process.poll() is None:  # Still running
                startup_status = self._wait_for_startup(host, port, timeout=30)
                if startup_status["success"]:
                    self.logger.info(f"Backend started successfully (PID: {process.pid})")
                    return {
                        "success": True,
                        "message": "Backend started successfully",
                        "pid": process.pid,
                        "host": host,
                        "port": port,
                        "api_health": startup_status.get("api_health")
                    }
                else:
                    self.logger.error("Backend startup verification failed")
                    return {
                        "success": False,
                        "message": "Backend started but health check failed",
                        "pid": process.pid,
                        "details": startup_status
                    }
            else:
                # Process died during startup
                return_code = process.poll()
                self.logger.error(f"Backend process died during startup (exit code: {return_code})")
                self._cleanup_pid_file()
                return {
                    "success": False,
                    "message": f"Backend process died during startup (exit code: {return_code})",
                    "exit_code": return_code
                }
                
        except Exception as e:
            self.logger.error(f"Failed to start backend: {e}")
            return {
                "success": False,
                "message": f"Failed to start backend: {str(e)}",
                "error": str(e)
            }
    
    def stop(self, force: bool = False, timeout: int = 10) -> Dict[str, Any]:
        """
        Stop the backend service.
        
        Args:
            force: Use SIGKILL instead of SIGTERM
            timeout: Seconds to wait before force killing
            
        Returns:
            Dict with stop operation results
        """
        self.logger.info("Stopping backend service")
        
        status = self.get_status()
        if not status.is_running:
            self._cleanup_pid_file()
            return {
                "success": True,
                "message": "Backend was not running"
            }
        
        try:
            process = psutil.Process(status.pid)
            
            if force or self.is_windows:
                # Force kill (Windows doesn't handle SIGTERM well)
                if self.is_windows:
                    process.terminate()
                else:
                    process.kill()
                self.logger.info(f"Force killed backend process (PID: {status.pid})")
            else:
                # Graceful shutdown
                process.terminate()
                
                # Wait for graceful shutdown
                try:
                    process.wait(timeout=timeout)
                    self.logger.info(f"Backend stopped gracefully (PID: {status.pid})")
                except psutil.TimeoutExpired:
                    self.logger.warning(f"Graceful shutdown timed out, force killing (PID: {status.pid})")
                    process.kill()
                    process.wait(timeout=5)
            
            self._cleanup_pid_file()
            
            return {
                "success": True,
                "message": f"Backend stopped successfully (PID: {status.pid})",
                "pid": status.pid
            }
            
        except psutil.NoSuchProcess:
            self._cleanup_pid_file()
            return {
                "success": True,
                "message": "Backend process was already terminated"
            }
        except Exception as e:
            self.logger.error(f"Failed to stop backend: {e}")
            return {
                "success": False,
                "message": f"Failed to stop backend: {str(e)}",
                "error": str(e)
            }
    
    def restart(self, **kwargs) -> Dict[str, Any]:
        """
        Restart the backend service.
        
        Args:
            **kwargs: Arguments passed to start()
            
        Returns:
            Dict with restart operation results
        """
        self.logger.info("Restarting backend service")
        
        # Stop first
        stop_result = self.stop()
        if not stop_result["success"]:
            return {
                "success": False,
                "message": f"Failed to stop during restart: {stop_result['message']}",
                "stop_result": stop_result
            }
        
        # Wait a moment
        time.sleep(1)
        
        # Start again
        start_result = self.start(**kwargs)
        return {
            "success": start_result["success"],
            "message": f"Restart {'successful' if start_result['success'] else 'failed'}",
            "stop_result": stop_result,
            "start_result": start_result
        }
    
    def get_status(self) -> BackendStatus:
        """
        Get current backend status.
        
        Returns:
            BackendStatus object with current state
        """
        try:
            # Check PID file
            if not self.pid_file.exists():
                return BackendStatus(is_running=False)
            
            pid_data = self._read_pid_file()
            if not pid_data:
                return BackendStatus(is_running=False)
            
            pid = pid_data.get("pid")
            host = pid_data.get("host", "127.0.0.1")
            port = pid_data.get("port", 8000)
            start_time = pid_data.get("start_time")
            
            # Check if process exists
            try:
                process = psutil.Process(pid)
                if not process.is_running():
                    self._cleanup_pid_file()
                    return BackendStatus(is_running=False)
            except psutil.NoSuchProcess:
                self._cleanup_pid_file()
                return BackendStatus(is_running=False)
            
            # Calculate uptime
            uptime_seconds = None
            if start_time:
                uptime_seconds = time.time() - start_time
            
            # Get resource usage
            memory_mb = process.memory_info().rss / 1024 / 1024
            cpu_percent = process.cpu_percent()
            
            # Check API health
            api_health = self._check_api_health(host, port)
            
            return BackendStatus(
                is_running=True,
                pid=pid,
                port=port,
                host=host,
                uptime_seconds=uptime_seconds,
                memory_mb=memory_mb,
                cpu_percent=cpu_percent,
                api_health=api_health
            )
            
        except Exception as e:
            self.logger.error(f"Error getting status: {e}")
            return BackendStatus(
                is_running=False,
                last_error=str(e)
            )
    
    def get_logs(self, lines: int = 50) -> List[str]:
        """
        Get recent log lines.
        
        Args:
            lines: Number of recent lines to return
            
        Returns:
            List of log lines
        """
        try:
            if not self.log_file.exists():
                return ["No log file found"]
            
            with open(self.log_file, 'r') as f:
                all_lines = f.readlines()
                return [line.rstrip() for line in all_lines[-lines:]]
        except Exception as e:
            return [f"Error reading logs: {e}"]
    
    def _validate_environment(self) -> Dict[str, Any]:
        """Validate that the environment is ready for backend startup."""
        issues = []
        
        # Check Python version
        if sys.version_info < (3, 8):
            issues.append(f"Python 3.8+ required, found {sys.version}")
        
        # Check if service script exists
        if not self.service_script.exists():
            issues.append(f"Service script not found: {self.service_script}")
        
        # Check config file
        if not self.config_file.exists():
            issues.append(f"Config file not found: {self.config_file}")
        
        # Check required directories
        required_dirs = ["models", "config", "src"]
        for dir_name in required_dirs:
            dir_path = self.project_root / dir_name
            if not dir_path.exists():
                issues.append(f"Required directory missing: {dir_name}")
        
        if issues:
            return {
                "success": False,
                "message": "Environment validation failed",
                "issues": issues
            }
        
        return {"success": True, "message": "Environment validation passed"}
    
    def _is_port_available(self, host: str, port: int) -> bool:
        """Check if a port is available for binding."""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.bind((host, port))
                return True
        except OSError:
            return False
    
    def _wait_for_startup(self, host: str, port: int, timeout: int = 30) -> Dict[str, Any]:
        """Wait for the backend to become available."""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                api_health = self._check_api_health(host, port)
                if api_health == "healthy":
                    return {
                        "success": True,
                        "api_health": api_health,
                        "startup_time": time.time() - start_time
                    }
            except:
                pass
            
            time.sleep(1)
        
        return {
            "success": False,
            "message": f"Backend did not become available within {timeout} seconds"
        }
    
    def _check_api_health(self, host: str, port: int) -> str:
        """Check if the API is responding."""
        try:
            import requests
            response = requests.get(f"http://{host}:{port}/health", timeout=5)
            if response.status_code == 200:
                data = response.json()
                return data.get("status", "unknown")
            else:
                return f"http_error_{response.status_code}"
        except Exception as e:
            return f"connection_error: {str(e)}"
    
    def _write_pid_file(self, pid: int, host: str, port: int) -> None:
        """Write PID file with service information."""
        pid_data = {
            "pid": pid,
            "host": host,
            "port": port,
            "start_time": time.time(),
            "platform": self.platform
        }
        
        with open(self.pid_file, 'w') as f:
            json.dump(pid_data, f, indent=2)
    
    def _read_pid_file(self) -> Optional[Dict[str, Any]]:
        """Read PID file data."""
        try:
            with open(self.pid_file, 'r') as f:
                return json.load(f)
        except Exception:
            return None
    
    def _cleanup_pid_file(self) -> None:
        """Remove PID file."""
        try:
            if self.pid_file.exists():
                self.pid_file.unlink()
        except Exception:
            pass


def main():
    """CLI interface for the backend controller."""
    import argparse
    
    parser = argparse.ArgumentParser(description="AI Coding Assistant Backend Controller")
    parser.add_argument("command", choices=["start", "stop", "restart", "status", "logs"], 
                       help="Command to execute")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind to")
    parser.add_argument("--force", action="store_true", help="Force kill processes")
    parser.add_argument("--foreground", action="store_true", help="Run in foreground")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    parser.add_argument("--lines", type=int, default=50, help="Number of log lines to show")
    
    args = parser.parse_args()
    
    controller = BackendController()
    
    if args.command == "start":
        result = controller.start(
            host=args.host,
            port=args.port,
            background=not args.foreground,
            verbose=args.verbose
        )
        print(json.dumps(result, indent=2))
        sys.exit(0 if result["success"] else 1)
    
    elif args.command == "stop":
        result = controller.stop(force=args.force)
        print(json.dumps(result, indent=2))
        sys.exit(0 if result["success"] else 1)
    
    elif args.command == "restart":
        result = controller.restart(
            host=args.host,
            port=args.port,
            background=not args.foreground,
            verbose=args.verbose
        )
        print(json.dumps(result, indent=2))
        sys.exit(0 if result["success"] else 1)
    
    elif args.command == "status":
        status = controller.get_status()
        status_dict = {
            "is_running": status.is_running,
            "pid": status.pid,
            "host": status.host,
            "port": status.port,
            "uptime_seconds": status.uptime_seconds,
            "memory_mb": status.memory_mb,
            "cpu_percent": status.cpu_percent,
            "api_health": status.api_health,
            "last_error": status.last_error
        }
        print(json.dumps(status_dict, indent=2))
        sys.exit(0 if status.is_running else 1)
    
    elif args.command == "logs":
        logs = controller.get_logs(lines=args.lines)
        for line in logs:
            print(line)
        sys.exit(0)


if __name__ == "__main__":
    main()