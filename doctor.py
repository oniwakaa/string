#!/usr/bin/env python3
"""
AI Coding Assistant - System Doctor

This tool performs comprehensive system diagnostics to ensure all components
are properly configured and compatible across different operating systems.
"""

import os
import sys
import json
import time
import psutil
import socket
import platform
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime


@dataclass
class DiagnosticResult:
    """Result of a diagnostic check."""
    name: str
    status: str  # "pass", "fail", "warning", "info"
    message: str
    details: Optional[Dict[str, Any]] = None
    fix_suggestion: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class SystemDoctor:
    """Comprehensive system diagnostics for the AI Coding Assistant."""
    
    def __init__(self, project_root: Optional[Path] = None, verbose: bool = False):
        """
        Initialize the system doctor.
        
        Args:
            project_root: Path to project root (auto-detected if None)
            verbose: Enable verbose output
        """
        self.project_root = Path(project_root) if project_root else Path.cwd()
        self.verbose = verbose
        self.results: List[DiagnosticResult] = []
        
        # Platform detection
        self.platform = platform.system().lower()
        self.is_windows = self.platform == "windows"
        self.is_macos = self.platform == "darwin"
        self.is_linux = self.platform == "linux"
        self.architecture = platform.machine()
        
        # Expected file paths
        self.config_file = self.project_root / "config.yaml"
        self.service_script = self.project_root / "run_gguf_service.py"
        self.backend_controller = self.project_root / "backend_controller.py"
        self.models_dir = self.project_root / "models"
        self.smollm_dir = self.project_root / "smollm-quantized"
        
    def run_full_diagnosis(self) -> Dict[str, Any]:
        """
        Run complete system diagnosis.
        
        Returns:
            Dict with comprehensive diagnostic results
        """
        start_time = time.time()
        self.results = []
        
        print("🔬 AI Coding Assistant - System Doctor")
        print("=====================================")
        print(f"Platform: {platform.platform()}")
        print(f"Architecture: {self.architecture}")
        print(f"Project Root: {self.project_root}")
        print("")
        
        # Run all diagnostic checks
        self._check_system_info()
        self._check_python_environment()
        self._check_project_structure()
        self._check_dependencies()
        self._check_models()
        self._check_configuration()
        self._check_backend_health()
        self._check_network_connectivity()
        self._check_system_resources()
        self._check_gpu_acceleration()
        self._check_external_services()
        
        # Summarize results
        summary = self._generate_summary()
        diagnosis_time = time.time() - start_time
        
        return {
            "platform": {
                "system": self.platform,
                "architecture": self.architecture,
                "version": platform.version(),
                "machine": platform.machine()
            },
            "diagnosis_time_seconds": round(diagnosis_time, 2),
            "summary": summary,
            "results": [result.to_dict() for result in self.results],
            "timestamp": datetime.now().isoformat()
        }
    
    def _add_result(self, name: str, status: str, message: str, 
                   details: Optional[Dict[str, Any]] = None,
                   fix_suggestion: Optional[str] = None) -> None:
        """Add a diagnostic result."""
        result = DiagnosticResult(
            name=name,
            status=status,
            message=message,
            details=details,
            fix_suggestion=fix_suggestion
        )
        self.results.append(result)
        
        # Print result if verbose
        if self.verbose:
            status_icon = {
                "pass": "✅",
                "fail": "❌", 
                "warning": "⚠️",
                "info": "ℹ️"
            }.get(status, "?")
            print(f"{status_icon} {name}: {message}")
    
    def _check_system_info(self) -> None:
        """Check basic system information."""
        try:
            # OS Version
            os_version = platform.version()
            self._add_result(
                "Operating System",
                "info",
                f"{platform.system()} {platform.release()}",
                {"version": os_version, "architecture": self.architecture}
            )
            
            # CPU Information
            cpu_count = psutil.cpu_count(logical=True)
            cpu_freq = psutil.cpu_freq()
            self._add_result(
                "CPU Information",
                "info",
                f"{cpu_count} cores at {cpu_freq.current:.0f}MHz" if cpu_freq else f"{cpu_count} cores",
                {"physical_cores": psutil.cpu_count(logical=False),
                 "logical_cores": cpu_count,
                 "frequency": cpu_freq._asdict() if cpu_freq else None}
            )
            
            # Memory Information
            memory = psutil.virtual_memory()
            memory_gb = memory.total / (1024**3)
            self._add_result(
                "System Memory",
                "pass" if memory_gb >= 8 else "warning",
                f"{memory_gb:.1f} GB total, {memory.percent}% used",
                {"total_gb": memory_gb, "used_percent": memory.percent},
                "Consider 16GB+ RAM for optimal performance" if memory_gb < 16 else None
            )
            
        except Exception as e:
            self._add_result("System Information", "fail", f"Error gathering system info: {e}")
    
    def _check_python_environment(self) -> None:
        """Check Python installation and environment."""
        try:
            # Python version
            python_version = platform.python_version()
            python_major, python_minor = sys.version_info[:2]
            
            if python_major >= 3 and python_minor >= 11:
                status = "pass"
                message = f"Python {python_version}"
            elif python_major >= 3 and python_minor >= 8:
                status = "warning"
                message = f"Python {python_version} (3.11+ recommended)"
            else:
                status = "fail"
                message = f"Python {python_version} (3.11+ required)"
            
            self._add_result(
                "Python Version",
                status,
                message,
                {"version": python_version, "executable": sys.executable},
                "Install Python 3.11+ for best compatibility" if status != "pass" else None
            )
            
            # Virtual environment
            in_venv = hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix)
            if in_venv:
                self._add_result("Virtual Environment", "pass", "Active virtual environment detected")
            else:
                self._add_result(
                    "Virtual Environment", 
                    "warning", 
                    "No virtual environment detected",
                    fix_suggestion="Use Poetry or create a virtual environment to isolate dependencies"
                )
            
            # Poetry
            try:
                poetry_result = subprocess.run(["poetry", "--version"], 
                                             capture_output=True, text=True, timeout=5)
                if poetry_result.returncode == 0:
                    poetry_version = poetry_result.stdout.strip()
                    self._add_result("Poetry", "pass", poetry_version)
                else:
                    self._add_result("Poetry", "fail", "Poetry not working properly")
            except (subprocess.TimeoutExpired, FileNotFoundError):
                self._add_result(
                    "Poetry", 
                    "fail", 
                    "Poetry not found",
                    fix_suggestion="Install Poetry: curl -sSL https://install.python-poetry.org | python3 -"
                )
                
        except Exception as e:
            self._add_result("Python Environment", "fail", f"Error checking Python: {e}")
    
    def _check_project_structure(self) -> None:
        """Check project file structure."""
        required_files = [
            ("config.yaml", self.config_file),
            ("run_gguf_service.py", self.service_script),
            ("backend_controller.py", self.backend_controller)
        ]
        
        required_dirs = [
            ("models", self.models_dir),
            ("config", self.project_root / "config"),
            ("src", self.project_root / "src")
        ]
        
        # Check files
        for name, path in required_files:
            if path.exists():
                self._add_result(f"File: {name}", "pass", f"Found at {path}")
            else:
                self._add_result(
                    f"File: {name}", 
                    "fail", 
                    f"Missing: {path}",
                    fix_suggestion=f"Ensure {name} exists in project root"
                )
        
        # Check directories
        for name, path in required_dirs:
            if path.exists() and path.is_dir():
                file_count = len(list(path.rglob("*")))
                self._add_result(f"Directory: {name}", "pass", f"Found with {file_count} files")
            else:
                self._add_result(
                    f"Directory: {name}", 
                    "fail", 
                    f"Missing: {path}",
                    fix_suggestion=f"Create directory: mkdir -p {path}"
                )
    
    def _check_dependencies(self) -> None:
        """Check Python package dependencies."""
        try:
            # Check if in Poetry environment
            poetry_env_info = subprocess.run(
                ["poetry", "env", "info", "--json"], 
                capture_output=True, text=True, timeout=10
            )
            
            if poetry_env_info.returncode == 0:
                env_info = json.loads(poetry_env_info.stdout)
                python_path = env_info.get("Executable", "unknown")
                self._add_result("Poetry Environment", "pass", f"Active: {python_path}")
            else:
                self._add_result("Poetry Environment", "warning", "Poetry environment not active")
            
            # Check key dependencies
            key_packages = [
                "fastapi", "uvicorn", "llama-cpp-python", "qdrant-client", 
                "sentence-transformers", "psutil", "pydantic"
            ]
            
            missing_packages = []
            for package in key_packages:
                try:
                    __import__(package.replace("-", "_"))
                    self._add_result(f"Package: {package}", "pass", "Installed")
                except ImportError:
                    missing_packages.append(package)
                    self._add_result(f"Package: {package}", "fail", "Missing")
            
            if missing_packages:
                self._add_result(
                    "Dependencies",
                    "fail",
                    f"Missing packages: {', '.join(missing_packages)}",
                    fix_suggestion="Run: poetry install"
                )
            else:
                self._add_result("Dependencies", "pass", "All key packages installed")
                
        except Exception as e:
            self._add_result("Dependencies", "fail", f"Error checking dependencies: {e}")
    
    def _check_models(self) -> None:
        """Check model files and directories."""
        expected_models = [
            ("SmolLM3-3B", self.smollm_dir / "smollm-q4_K_M.gguf"),
            ("Gemma", self.models_dir / "gemma" / "gemma-3n-e4b-it_q4_k_m.gguf"),
            ("Qwen", self.models_dir / "qwen" / "qwen3-1.7b-q4_k_m.gguf"),
            ("WebSailor", self.models_dir / "websailor" / "WebSailor-3B.Q4_K_M.gguf")
        ]
        
        total_size_gb = 0
        found_models = 0
        
        for model_name, model_path in expected_models:
            if model_path.exists():
                size_gb = model_path.stat().st_size / (1024**3)
                total_size_gb += size_gb
                found_models += 1
                self._add_result(
                    f"Model: {model_name}", 
                    "pass", 
                    f"Found ({size_gb:.1f} GB)",
                    {"path": str(model_path), "size_gb": size_gb}
                )
            else:
                self._add_result(
                    f"Model: {model_name}", 
                    "warning", 
                    "Missing",
                    {"expected_path": str(model_path)},
                    f"Download model to {model_path}"
                )
        
        # Summary
        self._add_result(
            "Models Summary",
            "pass" if found_models >= 2 else "warning",
            f"{found_models}/4 models found ({total_size_gb:.1f} GB total)",
            {"models_found": found_models, "total_size_gb": total_size_gb}
        )
    
    def _check_configuration(self) -> None:
        """Check configuration files."""
        try:
            if self.config_file.exists():
                import yaml
                with open(self.config_file, 'r') as f:
                    config = yaml.safe_load(f)
                
                # Check key configuration sections
                required_sections = ["service", "model", "memos"]
                missing_sections = [section for section in required_sections if section not in config]
                
                if missing_sections:
                    self._add_result(
                        "Configuration",
                        "warning",
                        f"Missing sections: {', '.join(missing_sections)}",
                        fix_suggestion="Add missing sections to config.yaml"
                    )
                else:
                    # Check API configuration
                    api_config = config.get("service", {}).get("api", {})
                    host = api_config.get("host", "0.0.0.0")
                    port = api_config.get("port", 8000)
                    
                    self._add_result(
                        "Configuration",
                        "pass",
                        f"Valid config (API: {host}:{port})",
                        {"host": host, "port": port, "sections": list(config.keys())}
                    )
            else:
                self._add_result(
                    "Configuration",
                    "fail",
                    "config.yaml missing",
                    fix_suggestion="Create config.yaml from template"
                )
                
        except Exception as e:
            self._add_result("Configuration", "fail", f"Error reading config: {e}")
    
    def _check_backend_health(self) -> None:
        """Check if backend service is running and healthy."""
        try:
            # Check if PID file exists
            pid_file = self.project_root / ".backend.pid"
            if pid_file.exists():
                with open(pid_file, 'r') as f:
                    pid_data = json.load(f)
                
                pid = pid_data.get("pid")
                host = pid_data.get("host", "127.0.0.1")
                port = pid_data.get("port", 8000)
                
                # Check if process is running
                try:
                    process = psutil.Process(pid)
                    if process.is_running():
                        # Try to connect to API
                        try:
                            import requests
                            response = requests.get(f"http://{host}:{port}/health", timeout=5)
                            if response.status_code == 200:
                                health_data = response.json()
                                self._add_result(
                                    "Backend Service",
                                    "pass",
                                    f"Running and healthy (PID: {pid})",
                                    {"pid": pid, "host": host, "port": port, "health": health_data}
                                )
                            else:
                                self._add_result(
                                    "Backend Service",
                                    "warning",
                                    f"Running but not healthy (HTTP {response.status_code})",
                                    {"pid": pid, "host": host, "port": port}
                                )
                        except requests.RequestException as e:
                            self._add_result(
                                "Backend Service",
                                "warning",
                                f"Process running but API not responding: {e}",
                                {"pid": pid}
                            )
                    else:
                        self._add_result("Backend Service", "fail", "Process not running")
                except psutil.NoSuchProcess:
                    self._add_result("Backend Service", "fail", "PID file exists but process not found")
            else:
                self._add_result(
                    "Backend Service",
                    "info",
                    "Not running",
                    fix_suggestion="Start with: python backend_controller.py start"
                )
                
        except Exception as e:
            self._add_result("Backend Service", "fail", f"Error checking backend: {e}")
    
    def _check_network_connectivity(self) -> None:
        """Check network connectivity and port availability."""
        # Check if default port is available
        host = "127.0.0.1"
        port = 8000
        
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(1)
                result = sock.connect_ex((host, port))
                if result == 0:
                    self._add_result("Port 8000", "warning", "Port in use (service may be running)")
                else:
                    self._add_result("Port 8000", "pass", "Available for use")
        except Exception as e:
            self._add_result("Port 8000", "fail", f"Error checking port: {e}")
        
        # Check internet connectivity for model downloads
        try:
            import requests
            response = requests.get("https://huggingface.co", timeout=5)
            if response.status_code == 200:
                self._add_result("Internet Connectivity", "pass", "Can reach HuggingFace")
            else:
                self._add_result("Internet Connectivity", "warning", f"HuggingFace returned {response.status_code}")
        except requests.RequestException:
            self._add_result(
                "Internet Connectivity",
                "warning",
                "Cannot reach HuggingFace",
                fix_suggestion="Check internet connection for model downloads"
            )
    
    def _check_system_resources(self) -> None:
        """Check system resource availability."""
        # Memory check
        memory = psutil.virtual_memory()
        available_gb = memory.available / (1024**3)
        
        if available_gb >= 4:
            status = "pass"
            message = f"{available_gb:.1f} GB available"
        elif available_gb >= 2:
            status = "warning"
            message = f"{available_gb:.1f} GB available (may be tight)"
        else:
            status = "fail"
            message = f"{available_gb:.1f} GB available (insufficient)"
        
        self._add_result(
            "Available Memory",
            status,
            message,
            {"available_gb": available_gb},
            "Close other applications to free memory" if status != "pass" else None
        )
        
        # Disk space check
        disk_usage = psutil.disk_usage(str(self.project_root))
        free_gb = disk_usage.free / (1024**3)
        
        if free_gb >= 10:
            status = "pass"
            message = f"{free_gb:.1f} GB free"
        elif free_gb >= 5:
            status = "warning"
            message = f"{free_gb:.1f} GB free (may need more for models)"
        else:
            status = "fail"
            message = f"{free_gb:.1f} GB free (insufficient)"
        
        self._add_result(
            "Disk Space",
            status,
            message,
            {"free_gb": free_gb},
            "Free up disk space for model files" if status != "pass" else None
        )
    
    def _check_gpu_acceleration(self) -> None:
        """Check GPU acceleration availability."""
        gpu_info = []
        
        try:
            # Check NVIDIA GPU
            nvidia_result = subprocess.run(
                ["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader,nounits"],
                capture_output=True, text=True, timeout=5
            )
            if nvidia_result.returncode == 0:
                for line in nvidia_result.stdout.strip().split('\n'):
                    if line.strip():
                        name, memory = line.split(',')
                        gpu_info.append(f"NVIDIA {name.strip()} ({memory.strip()}MB)")
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
        
        # Check for Metal (macOS)
        if self.is_macos and self.architecture == "arm64":
            gpu_info.append("Apple Silicon GPU (Metal)")
        
        # Check for AMD GPU (basic detection)
        try:
            if self.is_linux:
                lspci_result = subprocess.run(
                    ["lspci"], capture_output=True, text=True, timeout=5
                )
                if "AMD" in lspci_result.stdout and "VGA" in lspci_result.stdout:
                    gpu_info.append("AMD GPU detected")
        except:
            pass
        
        if gpu_info:
            self._add_result(
                "GPU Acceleration",
                "pass",
                f"Available: {', '.join(gpu_info)}",
                {"gpus": gpu_info}
            )
        else:
            self._add_result(
                "GPU Acceleration",
                "info",
                "None detected (CPU inference will be used)",
                fix_suggestion="Install GPU drivers for better performance"
            )
    
    def _check_external_services(self) -> None:
        """Check external service dependencies."""
        # Check Ollama
        try:
            ollama_result = subprocess.run(
                ["ollama", "list"], capture_output=True, text=True, timeout=10
            )
            if ollama_result.returncode == 0:
                models = [line.split()[0] for line in ollama_result.stdout.strip().split('\n')[1:] if line.strip()]
                self._add_result(
                    "Ollama Service",
                    "pass",
                    f"Running with {len(models)} models",
                    {"models": models}
                )
            else:
                self._add_result("Ollama Service", "warning", "Installed but not responding")
        except FileNotFoundError:
            self._add_result(
                "Ollama Service",
                "warning",
                "Not installed",
                fix_suggestion="Install Ollama for web research: curl -fsSL https://ollama.ai/install.sh | sh"
            )
        except subprocess.TimeoutExpired:
            self._add_result("Ollama Service", "warning", "Timeout waiting for response")
    
    def _generate_summary(self) -> Dict[str, Any]:
        """Generate diagnostic summary."""
        status_counts = {"pass": 0, "fail": 0, "warning": 0, "info": 0}
        critical_failures = []
        warnings = []
        
        for result in self.results:
            status_counts[result.status] += 1
            if result.status == "fail":
                critical_failures.append(result.name)
            elif result.status == "warning":
                warnings.append(result.name)
        
        # Determine overall health
        if critical_failures:
            overall_status = "critical"
            overall_message = f"{len(critical_failures)} critical issues found"
        elif warnings:
            overall_status = "warning"
            overall_message = f"{len(warnings)} warnings found"
        else:
            overall_status = "healthy"
            overall_message = "All checks passed"
        
        return {
            "overall_status": overall_status,
            "overall_message": overall_message,
            "status_counts": status_counts,
            "critical_failures": critical_failures,
            "warnings": warnings,
            "total_checks": len(self.results)
        }


def main():
    """CLI interface for the system doctor."""
    import argparse
    
    parser = argparse.ArgumentParser(description="AI Coding Assistant System Doctor")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose output")
    parser.add_argument("--json", action="store_true", help="Output results as JSON")
    parser.add_argument("--output", "-o", help="Save results to file")
    parser.add_argument("--project-root", help="Path to project root directory")
    
    args = parser.parse_args()
    
    # Initialize doctor
    project_root = Path(args.project_root) if args.project_root else None
    doctor = SystemDoctor(project_root=project_root, verbose=args.verbose)
    
    # Run diagnosis
    results = doctor.run_full_diagnosis()
    
    if args.json:
        # JSON output
        output = json.dumps(results, indent=2)
        print(output)
    else:
        # Human-readable output
        summary = results["summary"]
        print(f"\n🏥 Diagnosis Complete ({results['diagnosis_time_seconds']}s)")
        print("=" * 40)
        print(f"Overall Status: {summary['overall_status'].upper()}")
        print(f"Message: {summary['overall_message']}")
        print(f"Total Checks: {summary['total_checks']}")
        print(f"✅ Pass: {summary['status_counts']['pass']}")
        print(f"⚠️  Warning: {summary['status_counts']['warning']}")
        print(f"❌ Fail: {summary['status_counts']['fail']}")
        print(f"ℹ️  Info: {summary['status_counts']['info']}")
        
        if summary['critical_failures']:
            print(f"\n❌ Critical Issues:")
            for failure in summary['critical_failures']:
                print(f"  - {failure}")
        
        if summary['warnings']:
            print(f"\n⚠️  Warnings:")
            for warning in summary['warnings']:
                print(f"  - {warning}")
        
        if not args.verbose:
            print(f"\nRun with --verbose to see detailed results")
    
    # Save to file if requested
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"Results saved to {args.output}")
    
    # Exit with appropriate code
    if results["summary"]["overall_status"] == "critical":
        sys.exit(1)
    elif results["summary"]["overall_status"] == "warning":
        sys.exit(2)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()