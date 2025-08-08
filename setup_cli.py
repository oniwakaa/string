#!/usr/bin/env python3
"""
Comprehensive Installation Script for String AI Coding Assistant

This script provides a fully automated installation flow that:
- Sets up user-scoped runtime home (STRING_HOME)
- Installs string-cli globally using pipx with proper PATH configuration
- Builds llama-cpp-python with correct backend per OS (Metal/CUDA/OpenBLAS)
- Downloads models via authenticated Hugging Face CLI to STRING_HOME
- Creates runtime configurations and initializes storage directories

Usage:
    python setup_cli.py                    # Basic installation
    python setup_cli.py --with-models      # Include model downloads
    python setup_cli.py --enable-cuda      # Enable CUDA on Linux/Windows
    python setup_cli.py --enable-blas      # Enable OpenBLAS on Linux
    python setup_cli.py --string-home PATH # Override STRING_HOME path
"""

import sys
import subprocess
import os
import platform
import json
import shutil
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import argparse
import urllib.request
import tempfile

# Constants
PACKAGE_NAME = "string-ai-coding-assistant"
CLI_NAME = "string-cli"

class SetupError(Exception):
    """Custom exception for setup failures"""
    pass

class ComprehensiveSetup:
    """Comprehensive setup orchestrator with STRING_HOME support and automatic Python 3.11 provisioning"""
    
    def __init__(self, enable_cuda: bool = False, enable_blas: bool = False, 
                 with_models: bool = False, string_home: Optional[str] = None,
                 reinstall_metal: bool = False, python_311: bool = False, auto_provision: bool = True):
        self.enable_cuda = enable_cuda
        self.enable_blas = enable_blas
        self.with_models = with_models
        self.reinstall_metal = reinstall_metal
        self.python_311 = python_311
        self.auto_provision = auto_provision
        self.system = platform.system().lower()
        self.arch = platform.machine().lower()
        self.is_windows = self.system == "windows"
        self.is_macos = self.system == "darwin"
        self.is_linux = self.system == "linux"
        self.is_apple_silicon = self.is_macos and self.arch in ["arm64", "aarch64"]
        
        # Set project root
        self.project_root = Path(__file__).parent.resolve()
        
        # Set STRING_HOME
        self.string_home = self._get_string_home(string_home)
        
        # Initialize with system Python first, will be updated later if needed
        self.python_cmd = self._find_python_windows() if self.is_windows else sys.executable
        
        print(f"🖥️  Platform: {platform.system()} {platform.release()} ({self.arch})")
        print(f"🏠 STRING_HOME: {self.string_home}")
        print(f"📁 Project root: {self.project_root}")
        
        # Now ensure Python 3.11 is available (after all other attributes are set)
        self._setup_python_interpreter()
        
        print(f"🐍 Python: {self.python_cmd}")
    
    def _get_string_home(self, override_path: Optional[str] = None) -> Path:
        """Get STRING_HOME directory path with platform defaults"""
        if override_path:
            return Path(override_path).resolve()
        
        # Check environment override
        if "STRING_HOME" in os.environ:
            return Path(os.environ["STRING_HOME"]).resolve()
        
        # Platform-specific defaults
        if self.is_windows:
            home_base = Path(os.environ.get("USERPROFILE", Path.home()))
            return home_base / ".string"
        else:
            # macOS and Linux
            return Path.home() / ".string"
    
    def _find_python_311(self) -> str:
        """Find Python 3.11 interpreter across platforms"""
        if self.is_windows:
            # Try Windows Python Launcher first
            for cmd in ["py -3.11", "python3.11", "python"]:
                try:
                    result = subprocess.run(cmd.split(), capture_output=True, text=True, timeout=10)
                    if result.returncode == 0 and "3.11" in result.stdout:
                        return cmd
                except (FileNotFoundError, subprocess.TimeoutExpired):
                    continue
        else:
            # Unix-like systems
            for cmd in ["/opt/homebrew/bin/python3.11", "python3.11", "/usr/local/bin/python3.11", "python3"]:
                try:
                    result = subprocess.run([cmd, "--version"], capture_output=True, text=True, timeout=10)
                    if result.returncode == 0 and "3.11" in result.stdout:
                        return cmd
                except (FileNotFoundError, subprocess.TimeoutExpired):
                    continue
        
        # Fallback to system Python if 3.11 not found
        print("⚠️  Python 3.11 not found, using system Python")
        return sys.executable
    
    def _find_python_windows(self) -> str:
        """Find appropriate Python command on Windows"""
        for cmd in ["py", "python", "python3", sys.executable]:
            try:
                result = subprocess.run([cmd, "--version"], capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    return cmd
            except (FileNotFoundError, subprocess.TimeoutExpired):
                continue
        return sys.executable
    
    def _setup_python_interpreter(self) -> None:
        """Set up the Python interpreter after object initialization"""
        if self.python_311 or self.auto_provision:
            python311_path = self.ensure_python311()
            if python311_path:
                self.python_cmd = python311_path
                self.python_311 = True  # Mark as using 3.11
                print(f"✅ Using Python 3.11: {python311_path}")
            else:
                print("⚠️  Falling back to system Python")
    
    def detect_os_and_arch(self) -> Tuple[str, str, str]:
        """Detect OS, architecture, and distribution details"""
        system = platform.system().lower()
        arch = platform.machine().lower()
        
        # Detailed OS detection
        if system == "linux":
            try:
                # Try to detect distribution
                with open('/etc/os-release', 'r') as f:
                    os_release = f.read().lower()
                if 'ubuntu' in os_release or 'debian' in os_release:
                    distro = 'debian-based'
                elif 'centos' in os_release or 'rhel' in os_release or 'fedora' in os_release:
                    distro = 'rpm-based'
                else:
                    distro = 'linux-generic'
            except:
                distro = 'linux-generic'
        elif system == "darwin":
            distro = 'macos'
        elif system == "windows":
            distro = 'windows'
        else:
            distro = 'unknown'
        
        return system, arch, distro
    
    def find_python311_path(self) -> Optional[str]:
        """Find existing Python 3.11 installation across platforms"""
        if self.is_windows:
            # Windows: try py launcher first
            for cmd in ["py -3.11", "python3.11", "python"]:
                try:
                    result = subprocess.run(cmd.split() + ["--version"], capture_output=True, text=True, timeout=10)
                    if result.returncode == 0 and "3.11" in result.stdout:
                        if cmd.startswith("py"):
                            return "py -3.11"
                        else:
                            return shutil.which(cmd.split()[0])
                except:
                    continue
        else:
            # Unix-like: check common locations
            python311_candidates = [
                "/opt/homebrew/bin/python3.11",  # Homebrew ARM macOS
                "/usr/local/bin/python3.11",     # Homebrew Intel macOS
                "/usr/bin/python3.11",           # System package
                "python3.11"                     # PATH lookup
            ]
            
            for candidate in python311_candidates:
                try:
                    if candidate == "python3.11":
                        python_path = shutil.which("python3.11")
                        if not python_path:
                            continue
                        cmd = [python_path, "--version"]
                    else:
                        if not Path(candidate).exists():
                            continue
                        cmd = [candidate, "--version"]
                    
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                    if result.returncode == 0 and "3.11" in result.stdout:
                        return candidate if candidate != "python3.11" else python_path
                except:
                    continue
        
        return None
    
    def ensure_homebrew_macos(self) -> bool:
        """Ensure Homebrew is available on macOS"""
        if not self.is_macos:
            return False
        
        # Check if Homebrew is already installed
        if shutil.which("brew"):
            print("✅ Homebrew already available")
            return True
        
        print("📦 Installing Homebrew...")
        # Use the official Homebrew installation script
        try:
            install_script_url = "https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh"
            
            # Download and execute the install script
            result = subprocess.run([
                "/bin/bash", "-c", 
                f'$(curl -fsSL {install_script_url})'
            ], capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0:
                # Update PATH for current session
                homebrew_paths = ["/opt/homebrew/bin", "/usr/local/bin"]
                current_path = os.environ.get("PATH", "")
                for hb_path in homebrew_paths:
                    if Path(hb_path).exists() and hb_path not in current_path:
                        os.environ["PATH"] = f"{hb_path}:{current_path}"
                        break
                
                print("✅ Homebrew installed successfully")
                return True
            else:
                print(f"❌ Homebrew installation failed: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"❌ Homebrew installation error: {e}")
            return False
    
    def install_python311_macos(self) -> Optional[str]:
        """Install Python 3.11 on macOS using Homebrew"""
        if not self.ensure_homebrew_macos():
            print("⚠️  Cannot install Python 3.11 without Homebrew")
            print("💡 Please install Homebrew manually from https://brew.sh")
            return None
        
        print("🐍 Installing Python 3.11 via Homebrew...")
        
        # Install Python 3.11
        success, _, stderr = self.run_command(
            ["brew", "install", "python@3.11"],
            "Installing python@3.11",
            timeout=600
        )
        
        if not success:
            print(f"❌ Python 3.11 installation failed: {stderr}")
            return None
        
        # Find the installed Python 3.11 path
        try:
            result = subprocess.run(["brew", "--prefix", "python@3.11"], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                python311_path = Path(result.stdout.strip()) / "bin" / "python3.11"
                if python311_path.exists():
                    print(f"✅ Python 3.11 installed at: {python311_path}")
                    return str(python311_path)
        except Exception as e:
            print(f"⚠️  Error finding Python 3.11 path: {e}")
        
        # Fallback: try common Homebrew locations
        common_paths = [
            "/opt/homebrew/opt/python@3.11/bin/python3.11",
            "/usr/local/opt/python@3.11/bin/python3.11"
        ]
        
        for path in common_paths:
            if Path(path).exists():
                print(f"✅ Found Python 3.11 at: {path}")
                return path
        
        print("❌ Could not locate installed Python 3.11")
        return None
    
    def install_python311_debian(self) -> Optional[str]:
        """Install Python 3.11 on Debian/Ubuntu using deadsnakes PPA"""
        if not self.is_linux:
            return None
        
        print("🐍 Installing Python 3.11 on Debian/Ubuntu...")
        
        # Check if we can use sudo
        can_sudo = subprocess.run(["sudo", "-n", "true"], capture_output=True).returncode == 0
        if not can_sudo:
            print("❌ This installation requires sudo privileges")
            print("💡 Please run: sudo -v")
            return None
        
        # Add deadsnakes PPA
        print("📦 Adding deadsnakes PPA...")
        ppa_commands = [
            ["sudo", "apt", "update"],
            ["sudo", "apt", "install", "-y", "software-properties-common"],
            ["sudo", "add-apt-repository", "ppa:deadsnakes/ppa", "-y"],
            ["sudo", "apt", "update"]
        ]
        
        for cmd in ppa_commands:
            success, _, stderr = self.run_command(cmd, f"Running {' '.join(cmd)}", timeout=180)
            if not success:
                print(f"⚠️  Command failed: {' '.join(cmd)}")
                print(f"Error: {stderr}")
                # Continue anyway - some commands might fail but installation could still work
        
        # Install Python 3.11 and required packages
        print("📦 Installing Python 3.11 packages...")
        install_packages = [
            "python3.11",
            "python3.11-venv", 
            "python3.11-dev",
            "python3.11-distutils"
        ]
        
        success, _, stderr = self.run_command(
            ["sudo", "apt", "install", "-y"] + install_packages,
            "Installing Python 3.11 and development packages",
            timeout=300
        )
        
        if not success:
            print(f"❌ Python 3.11 installation failed: {stderr}")
            return None
        
        # Verify installation
        python311_path = "/usr/bin/python3.11"
        if Path(python311_path).exists():
            try:
                result = subprocess.run([python311_path, "--version"], 
                                      capture_output=True, text=True, timeout=10)
                if result.returncode == 0 and "3.11" in result.stdout:
                    print(f"✅ Python 3.11 installed successfully at: {python311_path}")
                    return python311_path
            except Exception as e:
                print(f"⚠️  Error verifying Python 3.11: {e}")
        
        print("❌ Could not verify Python 3.11 installation")
        return None
    
    def install_python311_rpm(self) -> Optional[str]:
        """Install Python 3.11 on RPM-based distributions"""
        if not self.is_linux:
            return None
        
        print("🐍 Installing Python 3.11 on RPM-based system...")
        
        # Try different package managers
        package_managers = [
            (["dnf", "install", "-y", "python3.11"], "DNF"),
            (["yum", "install", "-y", "python3.11"], "YUM")
        ]
        
        for cmd_base, pm_name in package_managers:
            if shutil.which(cmd_base[0]):
                print(f"📦 Using {pm_name} package manager...")
                success, _, stderr = self.run_command(
                    ["sudo"] + cmd_base,
                    f"Installing Python 3.11 via {pm_name}",
                    timeout=300
                )
                
                if success:
                    python311_path = "/usr/bin/python3.11"
                    if Path(python311_path).exists():
                        print(f"✅ Python 3.11 installed at: {python311_path}")
                        return python311_path
        
        print("❌ Could not install Python 3.11 via package manager")
        print("💡 Consider building from source or using pyenv")
        return None
    
    def install_python311_windows(self) -> Optional[str]:
        """Install or guide Python 3.11 installation on Windows"""
        if not self.is_windows:
            return None
        
        print("🐍 Setting up Python 3.11 on Windows...")
        
        # Check if py launcher can access 3.11
        try:
            result = subprocess.run(["py", "-3.11", "--version"], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0 and "3.11" in result.stdout:
                print("✅ Python 3.11 already available via py launcher")
                return "py -3.11"
        except:
            pass
        
        # Guide user through manual installation
        print("💻 Python 3.11 needs to be installed manually on Windows")
        print("\n📍 Please follow these steps:")
        print("1. Visit: https://www.python.org/downloads/windows/")
        print("2. Download 'Python 3.11.x' (latest 3.11 version)")
        print("3. Run the installer with these options:")
        print("   ✓ Check 'Add python.exe to PATH'")
        print("   ✓ Check 'Install for all users' (if admin)")
        print("   ✓ Choose 'Customize installation'")
        print("   ✓ Select all optional features")
        print("4. After installation, restart this terminal")
        print("5. Run this installer again")
        
        # Wait for user confirmation
        response = input("\nHave you completed the Python 3.11 installation? (y/N): ")
        if response.lower().startswith('y'):
            # Re-check for Python 3.11
            try:
                result = subprocess.run(["py", "-3.11", "--version"], 
                                      capture_output=True, text=True, timeout=10)
                if result.returncode == 0 and "3.11" in result.stdout:
                    print("✅ Python 3.11 detected successfully!")
                    return "py -3.11"
                else:
                    print("❌ Python 3.11 not detected. Please check the installation.")
            except:
                print("❌ Could not verify Python 3.11 installation")
        
        print("⚠️  Cannot proceed without Python 3.11")
        return None
    
    def ensure_python311(self) -> Optional[str]:
        """Ensure Python 3.11 is available, installing if necessary"""
        print("\n🐍 Step: Ensuring Python 3.11 availability...")
        
        # First, check if Python 3.11 is already available
        existing_path = self.find_python311_path()
        if existing_path:
            print(f"✅ Python 3.11 already available at: {existing_path}")
            return existing_path
        
        if not self.auto_provision:
            print("⚠️  Python 3.11 not found and auto-provisioning disabled")
            print("💡 Use --auto-provision to enable automatic installation")
            return None
        
        print("📦 Python 3.11 not found, attempting installation...")
        
        system, arch, distro = self.detect_os_and_arch()
        
        if distro == 'macos':
            return self.install_python311_macos()
        elif distro == 'debian-based':
            return self.install_python311_debian()
        elif distro == 'rpm-based':
            return self.install_python311_rpm()
        elif distro == 'windows':
            return self.install_python311_windows()
        else:
            print(f"⚠️  Unsupported platform: {system} ({distro})")
            print("💡 Please install Python 3.11 manually")
            return None
    
    def run_command(self, command: List[str], description: str = "", env: Optional[Dict[str, str]] = None, 
                    ignore_errors: bool = False, timeout: int = 300) -> Tuple[bool, str, str]:
        """Run command with error handling and logging"""
        if description:
            print(f"📦 {description}...")
        
        # Merge environment variables
        cmd_env = os.environ.copy()
        if env:
            cmd_env.update(env)
        
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                env=cmd_env,
                timeout=timeout
            )
            
            if result.returncode != 0 and not ignore_errors:
                print(f"❌ Command failed: {' '.join(command)}")
                print(f"   Exit code: {result.returncode}")
                if result.stderr:
                    print(f"   Error: {result.stderr.strip()}")
                return False, result.stdout, result.stderr
            
            if description and result.returncode == 0:
                print(f"✅ {description} completed")
            
            return True, result.stdout, result.stderr
            
        except subprocess.TimeoutExpired:
            if not ignore_errors:
                print(f"⏰ Command timed out: {' '.join(command)}")
            return False, "", "Command timed out"
        except Exception as e:
            if not ignore_errors:
                print(f"❌ Command error: {e}")
            return False, "", str(e)
    
    def setup_string_home(self) -> bool:
        """Create and initialize STRING_HOME directory structure"""
        print(f"\n🏠 Step 1: Setting up STRING_HOME at {self.string_home}")
        
        try:
            # Create main directory
            self.string_home.mkdir(parents=True, exist_ok=True)
            
            # Create subdirectories
            subdirs = ["apps", "models", "config", "storage"]
            for subdir in subdirs:
                (self.string_home / subdir).mkdir(exist_ok=True)
            
            # Create storage subdirectories
            storage_subdirs = ["qdrant_storage", "memory_cubes"]
            for subdir in storage_subdirs:
                (self.string_home / "storage" / subdir).mkdir(exist_ok=True)
            
            # Create .installed marker
            marker_file = self.string_home / ".installed"
            with open(marker_file, 'w') as f:
                f.write(f"String CLI runtime home initialized on {time.ctime()}\\n")
            
            print(f"✅ STRING_HOME directory structure created")
            return True
            
        except Exception as e:
            print(f"❌ Failed to create STRING_HOME: {e}")
            return False
    
    def create_runtime_configs(self) -> bool:
        """Create default runtime configuration files"""
        print("📄 Creating runtime configuration files...")
        
        try:
            config_dir = self.string_home / "config"
            
            # Create models.json manifest
            models_manifest = {
                "models": [
                    {
                        "name": "SmolLM3-3B-Q4_K_M",
                        "repo_id": "unsloth/SmolLM3-3B-128K-GGUF",
                        "filename": "SmolLM3-3B-Q4_K_M.gguf",
                        "local_dir": "SmolLM3-3B",
                        "allow_patterns": ["SmolLM3-3B-Q4_K_M.gguf"]
                    },
                    {
                        "name": "gemma-3n-E4B-it-Q5_K_S",
                        "repo_id": "unsloth/gemma-3n-E4B-it-GGUF",
                        "filename": "gemma-3n-E4B-it-Q5_K_S.gguf",
                        "local_dir": "gemma-3n-E4B-it",
                        "allow_patterns": ["gemma-3n-E4B-it-Q5_K_S.gguf"]
                    },
                    {
                        "name": "Qwen3-1.7B-Q5_K_M",
                        "repo_id": "MaziyarPanahi/Qwen3-1.7B-GGUF",
                        "filename": "Qwen3-1.7B-Q5_K_M.gguf",
                        "local_dir": "Qwen3-1.7B",
                        "allow_patterns": ["Qwen3-1.7B-Q5_K_M.gguf"]
                    },
                    {
                        "name": "WebSailor-3B",
                        "repo_id": "mradermacher/WebSailor-3B-GGUF",
                        "filename": "WebSailor-3B.Q5_K_S.gguf",
                        "local_dir": "WebSailor-3B",
                        "allow_patterns": ["WebSailor-3B.Q5_K_S.gguf"]
                    }
                ],
                "embedding": {
                    "name": "all-MiniLM-L6-v2",
                    "repo_id": "sentence-transformers/all-MiniLM-L6-v2",
                    "local_dir": "embedding/all-MiniLM-L6-v2"
                }
            }
            
            with open(config_dir / "models.json", 'w') as f:
                json.dump(models_manifest, f, indent=2)
            
            # Create runtime_config.yaml
            runtime_config = f"""# String CLI Runtime Configuration
# Configuration for MemOS with GGUF Model Integration using STRING_HOME paths

memos:
  user_id: "default_user"
  session_id: "default_session"
  enable_textual_memory: true
  enable_activation_memory: false
  top_k: 5

model:
  model_path: "{self.string_home}/models/SmolLM3-3B/SmolLM3-3B-Q4_K_M.gguf"
  generation:
    max_tokens: 512
    temperature: 0.7
    top_p: 0.9
    top_k: 50
    do_sample: true
    add_generation_prompt: true
    n_ctx: 16384
    n_batch: 512
  loading:
    auto_load: true
    validate_on_load: true

service:
  health_check:
    enabled: true
    endpoint: "/health"
    include_model_info: true
  api:
    host: "0.0.0.0"
    port: 8000
    title: "MemOS with GGUF Integration (Runtime)"
    description: "A persistent service integrating MemOS memory layer with GGUF models from STRING_HOME"
    version: "1.0.0"

memory:
  retrieval:
    enabled: true
    top_k: 5
    mode: "fast"
    memory_types: ["All"]
  cube:
    default_cube_id: "default_cube"
    auto_create: true

storage:
  qdrant_storage: "{self.string_home}/storage/qdrant_storage"
  codebase_state: "{self.string_home}/storage/.codebase_state.json"
  memory_cubes: "{self.string_home}/storage/memory_cubes"

logging:
  level: "INFO"
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
"""
            
            with open(config_dir / "runtime_config.yaml", 'w') as f:
                f.write(runtime_config)
            
            # Create stringpref.md
            prefs_content = """# String CLI Runtime Preferences

## MemOS Configuration
- Local-first operation with Qdrant vector storage
- User ID: default_user
- Session isolation enabled
- Textual memory enabled, activation memory disabled
- Top-K retrieval: 5

## Model Preferences  
- Primary model: SmolLM3-3B (Q4_K_M quantized)
- Embedding model: all-MiniLM-L6-v2
- Context window: 16384 tokens
- Temperature: 0.7

## Storage Configuration
- Runtime storage: STRING_HOME/storage
- Qdrant storage: STRING_HOME/storage/qdrant_storage
- Codebase state: STRING_HOME/storage/.codebase_state.json

## Agent Configuration
- Multi-agent orchestration enabled
- Code generation, quality analysis, documentation agents
- Project-aware file monitoring with debouncing
"""
            
            with open(config_dir / "stringpref.md", 'w') as f:
                f.write(prefs_content)
            
            print("✅ Runtime configuration files created")
            return True
            
        except Exception as e:
            print(f"❌ Failed to create runtime configs: {e}")
            return False
    
    def ensure_pipx(self) -> bool:
        """Install pipx if not available, cross-platform"""
        print("\\n🔧 Step 2: Ensuring pipx is available...")
        
        # Check if pipx is already available
        success, _, _ = self.run_command(["pipx", "--version"], ignore_errors=True)
        if success:
            print("✅ pipx already available")
            
            # Ensure PATH is configured
            success, stdout, _ = self.run_command(["pipx", "ensurepath"], "Configuring pipx PATH", ignore_errors=True)
            if "already in PATH" not in stdout and "been added to PATH" in stdout:
                print("💡 PATH updated - you may need to restart your terminal for global access")
            
            return True
        
        print("📦 Installing pipx...")
        
        if self.is_macos:
            # Try Homebrew first, fallback to pip
            success, _, _ = self.run_command(["brew", "install", "pipx"], "Installing pipx via Homebrew", ignore_errors=True)
            if not success:
                success, _, _ = self.run_command([self.python_cmd, "-m", "pip", "install", "--user", "pipx"], 
                                              "Installing pipx via pip (user)")
        elif self.is_linux:
            # Try system package manager first, then pip
            for pkg_cmd in [["apt", "install", "-y", "pipx"], ["dnf", "install", "-y", "pipx"]]:
                success, _, _ = self.run_command(pkg_cmd, f"Installing pipx via {pkg_cmd[0]}", ignore_errors=True)
                if success:
                    break
            else:
                success, _, _ = self.run_command([self.python_cmd, "-m", "pip", "install", "--user", "pipx"],
                                              "Installing pipx via pip (user)")
        elif self.is_windows:
            success, _, _ = self.run_command([self.python_cmd, "-m", "pip", "install", "--user", "pipx"],
                                          "Installing pipx via pip (user)")
        else:
            print(f"⚠️  Unknown platform: {self.system}")
            return False
        
        if success:
            # Configure PATH
            self.run_command(["pipx", "ensurepath"], "Configuring pipx PATH", ignore_errors=True)
            return True
        else:
            return False
    
    def install_cli_globally(self) -> bool:
        """Install string-cli globally using pipx with proper llama-cpp-python build"""
        print("\\n🚀 Step 3: Installing string-cli globally with pipx...")
        
        # Check if already installed
        success, stdout, _ = self.run_command(["pipx", "list"], ignore_errors=True)
        if success and PACKAGE_NAME in stdout:
            print(f"⚠️  {PACKAGE_NAME} already installed")
            if not self.reinstall_metal and not input("Reinstall? (y/N): ").lower().startswith('y'):
                return True
            
            # Uninstall first
            self.run_command(["pipx", "uninstall", PACKAGE_NAME], "Removing existing installation", ignore_errors=True)
        
        # Prepare environment for llama-cpp-python build
        build_env = {}
        
        if self.is_apple_silicon or self.reinstall_metal:
            print("🔧 Configuring Metal support for Apple Silicon...")
            build_env.update({
                "CMAKE_ARGS": "-DGGML_METAL=ON -DGGML_METAL_EMBED_LIBRARY=ON",
                "FORCE_CMAKE": "1"
            })
        elif self.enable_cuda:
            print("🔧 Configuring CUDA support...")
            build_env.update({
                "CMAKE_ARGS": "-DGGML_CUDA=ON",
                "FORCE_CMAKE": "1"
            })
        elif self.enable_blas:
            print("🔧 Configuring OpenBLAS support...")
            build_env.update({
                "CMAKE_ARGS": "-DGGML_BLAS=ON",
                "FORCE_CMAKE": "1"
            })
        
        # Install the package with specific Python version
        install_cmd = ["pipx", "install", str(self.project_root)]
        if self.python_311:
            # Add Python 3.11 specification
            install_cmd.extend(["--python", self.python_cmd])
            print(f"📦 Installing {PACKAGE_NAME} with pipx using Python 3.11...")
            print(f"🔧 Python path: {self.python_cmd}")
        else:
            print(f"📦 Installing {PACKAGE_NAME} with pipx...")
        
        success, _, _ = self.run_command(
            install_cmd,
            f"Installing {PACKAGE_NAME}",
            env=build_env,
            timeout=600
        )
        
        if not success:
            return False
        
        # Install llama-cpp-python with proper backend
        print("🔧 Installing llama-cpp-python with optimized backend...")
        install_cmd = ["pipx", "runpip", PACKAGE_NAME, "install", "--upgrade", "--force-reinstall", "--no-cache-dir", "llama-cpp-python"]
        
        success, _, _ = self.run_command(
            install_cmd,
            "Installing llama-cpp-python with backend optimization",
            env=build_env,
            timeout=900
        )
        
        if not success:
            print("⚠️  llama-cpp-python installation had issues, but continuing...")
        
        # Install essential CLI and backend dependencies
        essential_deps = [
            "huggingface_hub[cli]", 
            "psutil", 
            "pathspec",  # Required for .memignore filtering
            "lxml_html_clean",  # Required for web research agent
            "numpy<2.0.0"  # Pin for compatibility with llama-cpp-python
        ]
        for dep in essential_deps:
            self.run_command(
                ["pipx", "runpip", PACKAGE_NAME, "install", dep],
                f"Installing {dep}",
                ignore_errors=True
            )
        
        return True
    
    def verify_cli_installation(self) -> bool:
        """Verify that string-cli is properly installed and accessible"""
        print("\\n🔍 Step 4: Verifying CLI installation...")
        
        # Check pipx installation
        success, stdout, _ = self.run_command(["pipx", "list"], ignore_errors=True)
        if not success or PACKAGE_NAME not in stdout:
            print("❌ Package not found in pipx list")
            return False
        
        # Configure pipx PATH and update current session
        success, _, _ = self.run_command(["pipx", "ensurepath"], "Configuring pipx PATH", ignore_errors=True)
        
        # Update PATH for current session
        pipx_bin_path = Path.home() / ".local" / "bin"
        current_path = os.environ.get("PATH", "")
        if str(pipx_bin_path) not in current_path:
            os.environ["PATH"] = f"{pipx_bin_path}:{current_path}"
            print(f"🔄 Updated PATH to include {pipx_bin_path}")
        
        # Check CLI availability with improved diagnostics
        success, stdout, _ = self.run_command([CLI_NAME, "--version"], ignore_errors=True)
        if success:
            print(f"✅ {CLI_NAME} is globally accessible")
            if "STRING_HOME" in stdout:
                print(f"✅ Runtime home properly configured")
            return True
        else:
            print(f"⚠️  {CLI_NAME} not immediately accessible - checking installation...")
            # Try with explicit path
            cli_path = pipx_bin_path / CLI_NAME
            if cli_path.exists():
                print(f"✅ CLI binary exists at {cli_path}")
                print("💡 You may need to restart your terminal or run: source ~/.bashrc")
                # Try with explicit path to verify functionality
                success, stdout, _ = self.run_command([str(cli_path), "--version"], ignore_errors=True)
                if success and "STRING_HOME" in stdout:
                    print(f"✅ CLI functionality verified")
                    return True
                else:
                    print("⚠️  CLI exists but may have configuration issues")
                    return False
            else:
                print("❌ CLI binary not found")
                return False
    
    def setup_models(self) -> bool:
        """Set up models in STRING_HOME"""
        print("\\n📥 Step 5: Setting up models...")
        
        models_dir = self.string_home / "models"
        repo_models_dir = self.project_root / "models"
        
        # Check if models exist in repo
        if repo_models_dir.exists():
            print("📦 Copying models from repository...")
            
            # Define model mappings
            model_files = [
                ("SmolLM3-3B-Q4_K_M.gguf", "SmolLM3-3B"),
                ("gemma-3n-E4B-it-Q5_K_S.gguf", "gemma-3n-E4B-it"),
                ("Qwen3-1.7B-Q5_K_M.gguf", "Qwen3-1.7B"),
                ("WebSailor-3B.Q5_K_S.gguf", "WebSailor-3B")
            ]
            
            # Copy GGUF models
            for filename, local_dir in model_files:
                src_file = repo_models_dir / filename
                dst_dir = models_dir / local_dir
                dst_file = dst_dir / filename
                
                if src_file.exists() and not dst_file.exists():
                    dst_dir.mkdir(parents=True, exist_ok=True)
                    try:
                        shutil.copy2(src_file, dst_file)
                        print(f"✅ Copied {filename}")
                    except Exception as e:
                        print(f"⚠️  Failed to copy {filename}: {e}")
            
            # Copy embedding model
            embedding_src = repo_models_dir / "embedding"
            embedding_dst = models_dir / "embedding"
            if embedding_src.exists() and not embedding_dst.exists():
                try:
                    shutil.copytree(embedding_src, embedding_dst)
                    print("✅ Copied embedding models")
                except Exception as e:
                    print(f"⚠️  Failed to copy embedding models: {e}")
        
        # If --with-models flag is set, download via HuggingFace CLI
        if self.with_models:
            print("🌐 Downloading models via HuggingFace CLI...")
            return self._download_models_hf()
        else:
            print("💡 Use --with-models to download additional models via HuggingFace CLI")
        
        return True
    
    def _download_models_hf(self) -> bool:
        """Download models using HuggingFace CLI"""
        # Check if huggingface-cli is available
        hf_cli_path = Path.home() / ".local" / "pipx" / "venvs" / PACKAGE_NAME / "bin" / "huggingface-cli"
        if not hf_cli_path.exists():
            print("❌ HuggingFace CLI not found in pipx environment")
            return False
        
        # Load models manifest
        try:
            with open(self.string_home / "config" / "models.json", 'r') as f:
                manifest = json.load(f)
        except Exception as e:
            print(f"❌ Failed to load models manifest: {e}")
            return False
        
        # Authenticate if needed
        success, _, _ = self.run_command([str(hf_cli_path), "whoami"], ignore_errors=True)
        if not success:
            print("🔐 HuggingFace authentication required...")
            token = input("Enter your HuggingFace token (or press Enter to skip): ").strip()
            if token:
                login_success, _, _ = self.run_command(
                    [str(hf_cli_path), "login", "--token", token], 
                    "Logging into HuggingFace", 
                    ignore_errors=True
                )
                if not login_success:
                    print("⚠️  Authentication failed, skipping model downloads")
                    return False
            else:
                print("⚠️  No token provided, skipping model downloads")
                return False
        
        # Download models
        models_dir = self.string_home / "models"
        
        for model in manifest.get("models", []):
            local_dir = models_dir / model["local_dir"]
            if not local_dir.exists() or not list(local_dir.glob("*.gguf")):
                print(f"📥 Downloading {model['name']}...")
                
                cmd = [str(hf_cli_path), "download", model["repo_id"], "--local-dir", str(local_dir)]
                if "allow_patterns" in model:
                    for pattern in model["allow_patterns"]:
                        cmd.extend(["--include", pattern])
                
                success, _, _ = self.run_command(cmd, f"Downloading {model['name']}", timeout=1800)
                if not success:
                    print(f"⚠️  Failed to download {model['name']}")
        
        # Download embedding model
        embedding_config = manifest.get("embedding", {})
        if embedding_config:
            embedding_dir = models_dir / embedding_config["local_dir"]
            if not embedding_dir.exists():
                print(f"📥 Downloading {embedding_config['name']}...")
                success, _, _ = self.run_command([
                    str(hf_cli_path), "download", embedding_config["repo_id"],
                    "--local-dir", str(embedding_dir)
                ], f"Downloading {embedding_config['name']}", timeout=1800)
        
        return True
    
    def install_backend_requirements_via_pipx(self) -> bool:
        """Install backend requirements via pipx after CLI installation"""
        print("\n📦 Step: Installing backend requirements into pipx environment...")
        
        requirements_files = [
            ("requirements.txt", "Core backend requirements"),
            ("requirements_gguf.txt", "GGUF-specific requirements")
        ]
        
        for req_file, description in requirements_files:
            req_path = self.project_root / req_file
            if req_path.exists():
                print(f"📦 Installing {description}...")
                success, _, stderr = self.run_command(
                    ["pipx", "runpip", PACKAGE_NAME, "install", "-r", str(req_path)],
                    f"Installing {description}",
                    timeout=600,
                    ignore_errors=True
                )
                if not success:
                    print(f"⚠️  {description} installation had issues: {stderr}")
                    print("Continuing anyway...")
            else:
                print(f"⚠️  {req_file} not found, skipping")
        
        # Install optimized llama-cpp-python if on Apple Silicon
        if self.is_apple_silicon:
            print("🔧 Installing Metal-optimized llama-cpp-python...")
            build_env = {
                "CMAKE_ARGS": "-DGGML_METAL=ON -DGGML_METAL_EMBED_LIBRARY=ON",
                "FORCE_CMAKE": "1"
            }
            
            # First ensure numpy compatibility
            self.run_command(
                ["pipx", "runpip", PACKAGE_NAME, "install", "numpy<2.0.0"],
                "Ensuring numpy compatibility",
                ignore_errors=True
            )
            
            success, _, stderr = self.run_command(
                ["pipx", "runpip", PACKAGE_NAME, "install", "--upgrade", "--force-reinstall", "--no-cache-dir", "llama-cpp-python>=0.2.57"],
                "Installing Metal-optimized llama-cpp-python",
                env=build_env,
                timeout=900,
                ignore_errors=True
            )
            
            if not success:
                print(f"⚠️  Metal llama-cpp-python installation had issues: {stderr}")
                print("Backend may use CPU-only mode")
        
        # Install additional critical backend dependencies that might be missing
        critical_backend_deps = [
            "pathspec",  # Essential for .memignore filtering
            "lxml_html_clean",  # Required for web research functionality  
            "numpy<2.0.0",  # Pin for llama-cpp-python compatibility
        ]
        
        for dep in critical_backend_deps:
            self.run_command(
                ["pipx", "runpip", PACKAGE_NAME, "install", dep],
                f"Ensuring {dep} is available",
                ignore_errors=True
            )
        
        return True
    
    def run_installation(self) -> bool:
        """Run the complete installation process"""
        print("🚀 Starting comprehensive String CLI installation...\\n")
        
        steps = [
            ("Setting up STRING_HOME", self.setup_string_home),
            ("Creating runtime configs", self.create_runtime_configs),
            ("Ensuring pipx availability", self.ensure_pipx),
            ("Installing CLI globally", self.install_cli_globally),
            ("Installing backend requirements", self.install_backend_requirements_via_pipx),
            ("Verifying installation", self.verify_cli_installation),
            ("Setting up models", self.setup_models)
        ]
        
        for step_name, step_func in steps:
            try:
                if not step_func():
                    print(f"❌ Failed at step: {step_name}")
                    return False
            except Exception as e:
                print(f"❌ Error in step '{step_name}': {e}")
                return False
        
        return True
    
    def print_summary(self):
        """Print installation summary and next steps"""
        print("\\n" + "="*60)
        print("🎉 String CLI Installation Complete!")
        print("="*60)
        print(f"STRING_HOME: {self.string_home}")
        print(f"CLI Command: {CLI_NAME}")
        print(f"Backend: Auto-starts on first CLI usage")
        print()
        print("🔧 Next Steps:")
        print(f"1. Restart your terminal (or run: source ~/.bashrc)")
        print(f"2. Test CLI: {CLI_NAME} --version")
        print(f"3. Validate setup: {CLI_NAME} validate")
        print(f"4. Check status: {CLI_NAME} status")
        print()
        print("💡 Usage Examples:")
        print(f"  {CLI_NAME} validate                    # Check installation")
        print(f"  {CLI_NAME} status                     # Show service status")
        print(f"  {CLI_NAME} 'Help me debug this code'  # Natural language query")
        print()
        if not self.with_models:
            print("📥 To download additional models:")
            print(f"   python {__file__} --with-models")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="String AI Coding Assistant Setup")
    parser.add_argument("--with-models", action="store_true", help="Download models via HuggingFace CLI")
    parser.add_argument("--enable-cuda", action="store_true", help="Enable CUDA support (Linux/Windows)")
    parser.add_argument("--enable-blas", action="store_true", help="Enable OpenBLAS support (Linux)")
    parser.add_argument("--reinstall-metal", action="store_true", help="Force Metal rebuild on macOS")
    parser.add_argument("--python-3-11", action="store_true", help="Use Python 3.11 for pipx installation")
    parser.add_argument("--auto-provision", action="store_true", default=True, help="Automatically provision Python 3.11 if missing (default: True)")
    parser.add_argument("--no-auto-provision", action="store_true", help="Disable automatic Python 3.11 provisioning")
    parser.add_argument("--string-home", type=str, help="Override STRING_HOME path")
    
    args = parser.parse_args()
    
    # Handle auto-provision logic
    auto_provision = args.auto_provision and not args.no_auto_provision
    
    setup = ComprehensiveSetup(
        enable_cuda=args.enable_cuda,
        enable_blas=args.enable_blas,
        with_models=args.with_models,
        string_home=args.string_home,
        reinstall_metal=args.reinstall_metal,
        python_311=args.python_3_11,
        auto_provision=auto_provision
    )
    
    try:
        if setup.run_installation():
            setup.print_summary()
            print("\\n✅ Installation completed successfully!")
        else:
            print("\\n❌ Installation failed. Check output above for details.")
            sys.exit(1)
    except KeyboardInterrupt:
        print("\\n⚠️  Installation interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\\n❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()