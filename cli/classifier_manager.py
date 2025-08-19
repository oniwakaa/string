"""
CLI Classifier Manager - PID-based lifecycle management for isolated Gemma service.
"""

import os
import time
import signal
import subprocess
import psutil
from pathlib import Path
from typing import Optional, Dict, Any
import httpx
from rich.console import Console
from rich.table import Table

console = Console()

def _get_string_home() -> Path:
    """Resolve STRING_HOME path cross-platform."""
    if "STRING_HOME" in os.environ:
        return Path(os.environ["STRING_HOME"]).expanduser().resolve()
    if os.name == "nt":
        base = Path(os.environ.get("USERPROFILE", str(Path.home())))
        return (base / ".string").resolve()
    return (Path.home() / ".string").resolve()

class ClassifierManager:
    """Manages the isolated Gemma classifier service lifecycle."""
    
    def __init__(self):
        self.string_home = _get_string_home()
        self.pid_file = self.string_home / "storage" / ".pids" / "classifier.pid"
        self.log_file = self.string_home / "storage" / "logs" / "classifier.log"
        self.host = os.environ.get("SERVICEHOST_CLASSIFIER", "127.0.0.1")
        self.port = int(os.environ.get("SERVICEPORT_CLASSIFIER", "8001"))
        self.base_url = f"http://{self.host}:{self.port}"
        
        # Ensure directories exist
        self.pid_file.parent.mkdir(parents=True, exist_ok=True)
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
    
    def get_pid(self) -> Optional[int]:
        """Get PID from PID file if it exists and process is running."""
        if not self.pid_file.exists():
            return None
        
        try:
            with open(self.pid_file, 'r') as f:
                pid = int(f.read().strip())
            
            # Check if process is actually running
            if psutil.pid_exists(pid):
                process = psutil.Process(pid)
                # Verify it's our classifier service
                cmdline = " ".join(process.cmdline())
                if "rungemma_classifier_service" in cmdline:
                    return pid
                    
            # Stale PID file
            self.pid_file.unlink()
            return None
            
        except (ValueError, OSError, psutil.NoSuchProcess):
            # Invalid PID file or process no longer exists
            if self.pid_file.exists():
                self.pid_file.unlink()
            return None
    
    def is_port_occupied(self) -> bool:
        """Check if the classifier port is occupied."""
        try:
            for conn in psutil.net_connections():
                if (conn.laddr.ip == self.host and 
                    conn.laddr.port == self.port and 
                    conn.status == psutil.CONN_LISTEN):
                    return True
            return False
        except Exception:
            return False
    
    def is_running(self) -> bool:
        """Check if classifier service is running and healthy."""
        pid = self.get_pid()
        if not pid:
            return False
        
        # Quick port check
        if not self.is_port_occupied():
            return False
        
        # Health check
        try:
            with httpx.Client(timeout=2.0) as client:
                response = client.get(f"{self.base_url}/health")
                return response.status_code == 200
        except Exception:
            return False
    
    def get_status(self) -> Dict[str, Any]:
        """Get detailed status of classifier service."""
        pid = self.get_pid()
        port_occupied = self.is_port_occupied()
        
        status = {
            "running": False,
            "pid": pid,
            "port": self.port,
            "host": self.host,
            "port_occupied": port_occupied,
            "single_instance": False,
            "health": None,
            "error": None
        }
        
        if pid:
            try:
                process = psutil.Process(pid)
                status["single_instance"] = True
                
                # Get health info
                if port_occupied:
                    try:
                        with httpx.Client(timeout=3.0) as client:
                            response = client.get(f"{self.base_url}/health")
                            if response.status_code == 200:
                                status["health"] = response.json()
                                status["running"] = True
                            else:
                                status["error"] = f"Health check failed: {response.status_code}"
                    except Exception as e:
                        status["error"] = f"Health check error: {str(e)}"
                else:
                    status["error"] = "Process running but port not bound"
                    
            except psutil.NoSuchProcess:
                status["error"] = "PID exists but process not found"
        elif port_occupied:
            status["error"] = "Port occupied by unknown process"
        
        return status
    
    def start(self) -> bool:
        """Start the classifier service."""
        # Check if already running
        if self.is_running():
            console.print("✅ Classifier service already running", style="green")
            return True
        
        # Check for stale processes
        existing_pid = self.get_pid()
        if existing_pid:
            console.print(f"⚠️  Found stale PID {existing_pid}, cleaning up...", style="yellow")
            self.stop(force=True)
            time.sleep(1)
        
        # Check port availability
        if self.is_port_occupied():
            console.print(f"❌ Port {self.port} already occupied", style="red")
            console.print(f"💡 Try setting different port: export SERVICEPORT_CLASSIFIER=8002")
            return False
        
        # Start the service
        console.print(f"🚀 Starting classifier service on {self.host}:{self.port}...", style="blue")
        
        try:
            # Get project root and python executable
            project_root = Path(__file__).parent.parent
            python_exe = os.environ.get("PYTHON", "python")
            
            # Set environment variables
            env = os.environ.copy()
            env["SERVICEHOST_CLASSIFIER"] = self.host
            env["SERVICEPORT_CLASSIFIER"] = str(self.port)
            
            # Start subprocess
            process = subprocess.Popen(
                [python_exe, str(project_root / "rungemma_classifier_service.py")],
                env=env,
                cwd=str(project_root),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                start_new_session=True
            )
            
            # Wait for startup
            console.print("⏳ Waiting for service to start...", style="blue")
            
            for i in range(30):  # 30 second timeout
                time.sleep(1)
                if self.is_running():
                    console.print("✅ Classifier service started successfully", style="green")
                    return True
                
                # Check if process died
                if process.poll() is not None:
                    stdout, stderr = process.communicate()
                    console.print("❌ Service failed to start", style="red")
                    if stderr:
                        console.print(f"Error: {stderr.decode()}", style="red")
                    return False
            
            # Timeout
            console.print("❌ Service startup timeout", style="red")
            return False
            
        except Exception as e:
            console.print(f"❌ Failed to start service: {e}", style="red")
            return False
    
    def stop(self, force: bool = False) -> bool:
        """Stop the classifier service."""
        pid = self.get_pid()
        
        if not pid:
            console.print("ℹ️  Classifier service not running", style="blue")
            return True
        
        try:
            process = psutil.Process(pid)
            console.print(f"🛑 Stopping classifier service (PID: {pid})...", style="blue")
            
            if force:
                process.kill()
            else:
                process.terminate()
            
            # Wait for graceful shutdown
            for i in range(10):
                time.sleep(0.5)
                if not psutil.pid_exists(pid):
                    break
            else:
                # Force kill if still running
                if psutil.pid_exists(pid):
                    console.print("⚡ Force killing service...", style="yellow")
                    process.kill()
            
            # Clean up PID file
            if self.pid_file.exists():
                self.pid_file.unlink()
            
            console.print("✅ Classifier service stopped", style="green")
            return True
            
        except (psutil.NoSuchProcess, OSError):
            # Process already dead, clean up PID file
            if self.pid_file.exists():
                self.pid_file.unlink()
            console.print("✅ Classifier service stopped (was already dead)", style="green")
            return True
        except Exception as e:
            console.print(f"❌ Error stopping service: {e}", style="red")
            return False
    
    def restart(self) -> bool:
        """Restart the classifier service."""
        console.print("🔄 Restarting classifier service...", style="blue")
        self.stop()
        time.sleep(2)
        return self.start()
    
    def show_status(self):
        """Display detailed status information."""
        status = self.get_status()
        
        table = Table(title="Gemma Classifier Service Status")
        table.add_column("Property", style="cyan")
        table.add_column("Value", style="white")
        
        # Basic info
        table.add_row("Running", "✅ Yes" if status["running"] else "❌ No")
        table.add_row("Host", status["host"])
        table.add_row("Port", str(status["port"]))
        table.add_row("PID", str(status["pid"]) if status["pid"] else "None")
        table.add_row("Single Instance", "✅ Yes" if status["single_instance"] else "❌ No")
        
        # Health info
        if status["health"]:
            health = status["health"]
            table.add_row("Model", health.get("model", "Unknown"))
            table.add_row("Context Size", str(health.get("n_ctx", "Unknown")))
            table.add_row("Memory (MB)", f"{health.get('memory_mb', 0):.1f}")
        
        # Error info
        if status["error"]:
            table.add_row("Error", status["error"])
        
        console.print(table)
        
        # Show recent logs
        if self.log_file.exists():
            console.print("\n📋 Recent logs:", style="blue")
            try:
                with open(self.log_file, 'r') as f:
                    lines = f.readlines()
                    for line in lines[-5:]:  # Last 5 lines
                        console.print(f"  {line.strip()}", style="dim")
            except Exception:
                console.print("  Could not read log file", style="red")
    
    def test_classify(self, text: str = "Create a new Python file") -> bool:
        """Test classification endpoint."""
        if not self.is_running():
            console.print("❌ Classifier service not running", style="red")
            return False
        
        try:
            with httpx.Client(timeout=5.0) as client:
                response = client.post(
                    f"{self.base_url}/classify",
                    json={"text": text}
                )
                
                if response.status_code == 200:
                    result = response.json()
                    console.print(f"✅ Classification successful:", style="green")
                    console.print(f"  Text: {text}")
                    console.print(f"  Intent: {result['intent']}")
                    console.print(f"  Confidence: {result['confidence']:.2f}")
                    return True
                else:
                    console.print(f"❌ Classification failed: {response.status_code}", style="red")
                    return False
                    
        except Exception as e:
            console.print(f"❌ Classification test error: {e}", style="red")
            return False