#!/usr/bin/env python3
"""
Cross-Platform Automated Installation Script for String AI Coding Assistant

This script provides a fully automated installation flow that:
- Installs string-cli globally using pipx (cross-platform)  
- Builds llama-cpp-python with correct backend per OS (Metal/CUDA/OpenBLAS)
- Updates PATH automatically without manual steps
- Downloads models via authenticated Hugging Face CLI

Usage:
    python setup_cli.py                    # Basic installation
    python setup_cli.py --with-models      # Include model downloads
    python setup_cli.py --enable-cuda      # Enable CUDA on Linux/Windows
    python setup_cli.py --enable-blas      # Enable OpenBLAS on Linux
"""

import sys
import subprocess
import os
import platform
import json
import shutil
import getpass
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import argparse

# Constants
PACKAGE_NAME = "string-ai-coding-assistant"
CLI_NAME = "string-cli"
MODELS_MANIFEST = "models/config.json"

class SetupError(Exception):
    """Custom exception for setup failures"""
    pass

class CrossPlatformSetup:
    """Cross-platform setup orchestrator for String CLI"""
    
    def __init__(self, enable_cuda: bool = False, enable_blas: bool = False, with_models: bool = False):
        self.enable_cuda = enable_cuda
        self.enable_blas = enable_blas
        self.with_models = with_models
        self.system = platform.system().lower()
        self.arch = platform.machine().lower()
        self.is_windows = self.system == "windows"
        self.is_macos = self.system == "darwin"
        self.is_linux = self.system == "linux"
        self.is_apple_silicon = self.is_macos and self.arch in ["arm64", "aarch64"]
        
        # Set project root
        self.project_root = Path.cwd()
        
        # Determine Python command
        if self.is_windows:
            self.python_cmd = self._find_python_windows()
        else:
            self.python_cmd = sys.executable
        
        print(f"🖥️  Detected: {platform.system()} {platform.release()} ({self.arch})")
        print(f"🐍 Python: {self.python_cmd}")
    
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
    
    def run_command(self, command: List[str], description: str = "", env: Optional[Dict[str, str]] = None, 
                    ignore_errors: bool = False) -> Tuple[bool, str, str]:
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
                timeout=300
            )
            
            if result.returncode != 0 and not ignore_errors:
                print(f"❌ Command failed: {' '.join(command)}")
                print(f"   Exit code: {result.returncode}")
                if result.stderr:
                    print(f"   Error: {result.stderr.strip()}")
                return False, result.stdout, result.stderr
            
            if result.stdout and description:
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
    
    def ensure_pipx(self) -> bool:
        """Install pipx if not available, cross-platform"""
        print("\n🔧 Step 1: Ensuring pipx is available...")
        
        # Check if pipx is already available
        success, _, _ = self.run_command(["pipx", "--version"], ignore_errors=True)
        if success:
            print("✅ pipx already available")
            return True
        
        print("📦 Installing pipx...")
        
        if self.is_macos:
            # Try Homebrew first, fallback to pip
            success, _, _ = self.run_command(["brew", "install", "pipx"], "Installing pipx via Homebrew", ignore_errors=True)
            if success:
                return True
            
            # Fallback to pip user install
            success, _, _ = self.run_command([self.python_cmd, "-m", "pip", "install", "--user", "pipx"], 
                                          "Installing pipx via pip (user)")
            
        elif self.is_linux:
            # Try system package manager first, then pip
            for pkg_cmd in [["apt", "install", "-y", "pipx"], ["dnf", "install", "-y", "pipx"], 
                          ["yum", "install", "-y", "pipx"], ["pacman", "-S", "--noconfirm", "pipx"]]:
                success, _, _ = self.run_command(pkg_cmd, f"Installing pipx via {pkg_cmd[0]}", ignore_errors=True)
                if success:
                    return True
            
            # Fallback to pip user install
            success, _, _ = self.run_command([self.python_cmd, "-m", "pip", "install", "--user", "pipx"],
                                          "Installing pipx via pip (user)")
            
        elif self.is_windows:
            # Use pip user install on Windows
            success, _, _ = self.run_command([self.python_cmd, "-m", "pip", "install", "--user", "pipx"],
                                          "Installing pipx via pip (user)")
        
        if not success:
            raise SetupError("Failed to install pipx. Please install it manually and retry.")
        
        return True
    
    def ensure_pipx_path(self) -> bool:
        """Configure pipx PATH with ensurepath and update current session"""
        print("\n🛤️  Step 2: Configuring PATH for pipx...")
        
        # Run pipx ensurepath with force and prepend
        success, stdout, stderr = self.run_command(
            ["pipx", "ensurepath", "--force"],
            "Configuring pipx PATH"
        )
        
        if not success:
            print("⚠️  pipx ensurepath failed, trying basic version...")
            success, _, _ = self.run_command(["pipx", "ensurepath"], ignore_errors=True)
        
        # Get pipx binary directory
        if self.is_windows:
            pipx_bin_dir = Path.home() / "AppData" / "Roaming" / "Python" / "Scripts"
            if not pipx_bin_dir.exists():
                pipx_bin_dir = Path.home() / ".local" / "bin"
        else:
            pipx_bin_dir = Path.home() / ".local" / "bin"
        
        # Update PATH for current session
        current_path = os.environ.get("PATH", "")
        if str(pipx_bin_dir) not in current_path:
            if self.is_windows:
                os.environ["PATH"] = f"{pipx_bin_dir};{current_path}"
            else:
                os.environ["PATH"] = f"{pipx_bin_dir}:{current_path}"
            print(f"✅ Updated PATH for current session: {pipx_bin_dir}")
        
        return True
    
    def get_llama_cpp_build_env(self) -> Dict[str, str]:
        """Get environment variables for llama-cpp-python build based on OS and options"""
        env = {}
        
        if self.is_apple_silicon:
            # macOS Apple Silicon - use Metal
            env.update({
                "CMAKE_ARGS": "-DGGML_METAL=ON -DGGML_METAL_EMBED_LIBRARY=ON",
                "FORCE_CMAKE": "1"
            })
            print("🍎 Configured Metal backend for macOS Apple Silicon")
            
        elif self.is_macos:
            # macOS Intel - default build
            print("🍎 Using default build for macOS Intel")
            
        elif self.is_linux:
            cmake_args = []
            
            if self.enable_cuda:
                cmake_args.append("-DGGML_CUDA=ON")
                env["FORCE_CMAKE"] = "1"
                print("🚀 Configured CUDA backend for Linux")
                
            elif self.enable_blas:
                cmake_args.extend(["-DGGML_BLAS=ON", "-DGGML_BLAS_VENDOR=OpenBLAS"])
                env["FORCE_CMAKE"] = "1"
                print("📊 Configured OpenBLAS backend for Linux")
            else:
                print("🐧 Using default CPU backend for Linux")
            
            if cmake_args:
                env["CMAKE_ARGS"] = " ".join(cmake_args)
                
        elif self.is_windows:
            cmake_args = []
            
            if self.enable_cuda:
                cmake_args.append("-DGGML_CUDA=ON")
                env["FORCE_CMAKE"] = "1"
                print("🚀 Configured CUDA backend for Windows")
            else:
                print("🪟 Using default CPU backend for Windows")
            
            if cmake_args:
                env["CMAKE_ARGS"] = " ".join(cmake_args)
        
        return env
    
    def install_globally_with_pipx(self) -> bool:
        """Install string-cli globally using pipx with OS-specific llama-cpp-python build"""
        print("\n🌍 Step 3: Installing string-cli globally with pipx...")
        
        # Get build environment
        build_env = self.get_llama_cpp_build_env()
        
        # Check if already installed
        success, stdout, _ = self.run_command(["pipx", "list"], ignore_errors=True)
        if success and PACKAGE_NAME in stdout:
            print(f"⚠️  {PACKAGE_NAME} already installed, checking if rebuild needed...")
            
            # On macOS Apple Silicon, check if we need to rebuild for Metal
            if self.is_apple_silicon and build_env:
                print("🔄 Reinstalling with Metal backend...")
                success, _, _ = self.run_command([
                    "pipx", "reinstall", PACKAGE_NAME
                ], "Reinstalling with Metal backend", env=build_env)
                
                if not success:
                    raise SetupError("Failed to reinstall with Metal backend")
            else:
                print("✅ Installation already up to date")
                
            # Always ensure dependencies are up to date  
            print("📦 Updating dependencies in pipx environment...")
            self.run_command([
                "pipx", "runpip", PACKAGE_NAME, "install", "-r", "requirements.txt", "-r", "requirements_gguf.txt"
            ], "Installing backend dependencies", ignore_errors=True)
            
            return True
        else:
            # Fresh installation
            success, _, _ = self.run_command([
                "pipx", "install", "."
            ], "Installing string-cli globally", env=build_env)
            
            if not success:
                raise SetupError("Failed to install string-cli with pipx")
            
            # Install additional requirements
            print("📦 Installing backend service dependencies...")
            self.run_command([
                "pipx", "runpip", PACKAGE_NAME, "install", "-r", "requirements.txt", "-r", "requirements_gguf.txt"
            ], "Installing backend dependencies", ignore_errors=True)
        
        return True
    
    def verify_metal_backend(self) -> bool:
        """Verify Metal backend is working on macOS (optional diagnostic)"""
        if not self.is_apple_silicon:
            return True
        
        print("🔍 Verifying Metal backend...")
        try:
            # Test import in the pipx environment
            pipx_python = Path.home() / ".local" / "pipx" / "venvs" / PACKAGE_NAME / "bin" / "python"
            if pipx_python.exists():
                success, _, _ = self.run_command([
                    str(pipx_python), "-c", 
                    "import llama_cpp; print('✅ Metal backend available')"
                ], ignore_errors=True)
                return success
        except Exception:
            pass
        return True  # Don't fail setup for diagnostic issues
    
    def ensure_hf_cli(self) -> bool:
        """Ensure Hugging Face CLI is available in the pipx environment"""
        print("\n🤗 Installing Hugging Face CLI...")
        
        success, _, _ = self.run_command([
            "pipx", "runpip", PACKAGE_NAME, "install", "-U", "huggingface_hub[cli]"
        ], "Installing Hugging Face CLI in pipx environment")
        
        return success
    
    def hf_auth_and_download_models(self) -> bool:
        """Authenticate with HF and download models from manifest"""
        print("\n📥 Step 4: Downloading models via Hugging Face CLI...")
        
        if not self.ensure_hf_cli():
            raise SetupError("Failed to install Hugging Face CLI")
        
        # Load models manifest
        manifest_path = Path(MODELS_MANIFEST)
        if not manifest_path.exists():
            print(f"⚠️  Model manifest not found: {manifest_path}")
            return True
        
        try:
            with open(manifest_path, 'r') as f:
                config = json.load(f)
            models = config.get("models", {})
        except json.JSONDecodeError as e:
            raise SetupError(f"Invalid models manifest: {e}")
        
        # Check for gated models and authenticate if needed
        print("🔐 Checking authentication...")
        pipx_python = Path.home() / ".local" / "pipx" / "venvs" / PACKAGE_NAME / "bin" / "python"
        
        # Test auth status
        success, stdout, _ = self.run_command([
            str(pipx_python), "-c", 
            "from huggingface_hub import whoami; print(whoami())"
        ], ignore_errors=True)
        
        if not success or "not logged in" in stdout.lower():
            print("🔑 Authentication required for model downloads")
            token = getpass.getpass("Enter your Hugging Face token (or press Enter to skip): ")
            
            if token.strip():
                success, _, _ = self.run_command([
                    str(pipx_python), "-c",
                    f"from huggingface_hub import login; login('{token.strip()}')"
                ], "Authenticating with Hugging Face")
                
                if not success:
                    print("⚠️  Authentication failed, continuing without auth...")
        
        # Download models based on correct repository mappings for existing config.json models
        model_repos = {
            "SmolLM3-3B-Q4_K_M.gguf": ("unsloth/SmolLM3-3B-128K-GGUF", "SmolLM3-3B-Q4_K_M.gguf"),
            "gemma-3n-E4B-it-Q5_K_S.gguf": ("unsloth/gemma-3n-E4B-it-GGUF", "gemma-3n-E4B-it-Q5_K_S.gguf"),
            "Qwen3-1.7B-Q5_K_M.gguf": ("MaziyarPanahi/Qwen3-1.7B-GGUF", "Qwen3-1.7B-Q5_K_M.gguf"),
            "WebSailor-3B.Q5_K_S.gguf": ("mradermacher/WebSailor-3B-GGUF", "WebSailor-3B.Q5_K_S.gguf"),
            "Qwen3-Embedding-0.6B-f16.gguf": ("Qwen/Qwen3-Embedding-0.6B-GGUF", "Qwen3-Embedding-0.6B-f16.gguf")
        }
        
        downloaded = 0
        
        # First, download the embedding model for MemOS
        embedding_model_path = self.project_root / "models" / "embedding" / "all-MiniLM-L6-v2"
        if not embedding_model_path.exists():
            print("📥 Downloading embedding model for MemOS...")
            embedding_model_path.mkdir(parents=True, exist_ok=True)
            success, _, _ = self.run_command([
                str(pipx_python), "-c",
                f"""
from huggingface_hub import snapshot_download
try:
    snapshot_download(
        'sentence-transformers/all-MiniLM-L6-v2',
        local_dir='{embedding_model_path}',
        local_dir_use_symlinks=False
    )
    print('✅ Embedding model downloaded successfully')
except Exception as e:
    print(f'❌ Embedding model download failed: {{e}}')
    exit(1)
                """
            ], "Downloading embedding model")
            
            if success:
                downloaded += 1
        else:
            print("✅ Embedding model already exists")
            downloaded += 1
        
        # Download GGUF models from config.json
        for model_name, model_config in models.items():
            model_path = Path(model_config["path"])
            filename = model_path.name
            local_dir = model_path.parent
            
            # Check if already exists
            if model_path.exists():
                print(f"✅ {filename} already exists")
                downloaded += 1
                continue
            
            # Get repository info
            if filename not in model_repos:
                print(f"⚠️  No repository mapping for {filename}, skipping")
                continue
                
            repo_id, repo_filename = model_repos[filename]
            local_dir.mkdir(parents=True, exist_ok=True)
            
            print(f"⬇️  Downloading {filename} from {repo_id}...")
            
            # Use HF CLI download
            success, _, _ = self.run_command([
                str(pipx_python), "-c",
                f"""
from huggingface_hub import snapshot_download
try:
    snapshot_download(
        '{repo_id}',
        allow_patterns=['{repo_filename}'],
        local_dir='{local_dir}',
        local_dir_use_symlinks=False
    )
    print('✅ Download successful')
except Exception as e:
    print(f'❌ Download failed: {{e}}')
    exit(1)
                """
            ], f"Downloading {filename}")
            
            if success:
                # Rename if needed
                downloaded_file = local_dir / repo_filename
                if downloaded_file.exists() and repo_filename != filename:
                    downloaded_file.rename(model_path)
                downloaded += 1
            else:
                print(f"❌ Failed to download {filename}")
        
        print(f"📊 Downloaded {downloaded}/{len(models)} models")
        return downloaded > 0
    
    def verify_global_cli(self) -> bool:
        """Verify global CLI installation and functionality"""
        print("\n✅ Step 5: Verifying global CLI installation...")
        
        # Check if CLI is on PATH
        success, stdout, _ = self.run_command([CLI_NAME, "--version"], "Testing CLI availability")
        if not success:
            # Try to find it manually
            if self.is_windows:
                cli_path = Path.home() / "AppData" / "Roaming" / "Python" / "Scripts" / f"{CLI_NAME}.exe"
                if not cli_path.exists():
                    cli_path = Path.home() / ".local" / "bin" / CLI_NAME
            else:
                cli_path = Path.home() / ".local" / "bin" / CLI_NAME
            
            if cli_path.exists():
                print(f"✅ CLI found at: {cli_path}")
                print("ℹ️  You may need to restart your terminal for PATH changes to take effect")
                return True
            else:
                raise SetupError(f"CLI not found on PATH. Expected location: {cli_path}")
        
        print("✅ string-cli is globally accessible")
        
        # Test help command
        success, _, _ = self.run_command([CLI_NAME, "--help"], "Testing CLI help", ignore_errors=True)
        if success:
            print("✅ CLI help command works")
        
        # Verify Metal backend if on macOS Apple Silicon
        if self.is_apple_silicon:
            self.verify_metal_backend()
        
        return True
    
    def run_setup(self) -> bool:
        """Run the complete setup flow"""
        try:
            print("🚀 Starting automated String CLI installation...")
            print(f"🎯 Target: Global {CLI_NAME} with {self.system.title()} optimizations")
            print("")
            
            # Step 1: Ensure pipx
            self.ensure_pipx()
            
            # Step 2: Configure PATH
            self.ensure_pipx_path()
            
            # Step 3: Install globally
            self.install_globally_with_pipx()
            
            # Step 4: Download models (optional)
            if self.with_models:
                self.hf_auth_and_download_models()
            
            # Step 5: Verify installation
            self.verify_global_cli()
            
            print("\n🎉 Installation completed successfully!")
            print(f"✅ {CLI_NAME} is now globally available")
            print(f"✅ Optimized for {self.system.title()} ({self.arch})")
            
            if self.is_apple_silicon:
                print("✅ Metal backend configured")
            elif self.enable_cuda:
                print("✅ CUDA backend configured")
            elif self.enable_blas:
                print("✅ OpenBLAS backend configured")
            
            print("\n📖 Usage:")
            print(f"  {CLI_NAME} --help")
            print(f"  {CLI_NAME} --version")
            print(f"  {CLI_NAME} validate")
            print(f"  {CLI_NAME} \"analyze my code\"")
            
            if not self.with_models:
                print(f"\n💡 To download models, run: python setup_cli.py --with-models")
            
            return True
            
        except SetupError as e:
            print(f"\n❌ Setup failed: {e}")
            return False
        except KeyboardInterrupt:
            print("\n\n⚠️  Installation interrupted by user")
            return False
        except Exception as e:
            print(f"\n❌ Unexpected error: {e}")
            return False

def main():
    """Main entry point with argument parsing"""
    parser = argparse.ArgumentParser(
        description="Automated String CLI installation with cross-platform optimizations"
    )
    parser.add_argument(
        "--with-models", 
        action="store_true",
        help="Download AI models via Hugging Face CLI"
    )
    parser.add_argument(
        "--enable-cuda", 
        action="store_true",
        help="Enable CUDA backend for GPU acceleration (Linux/Windows)"
    )
    parser.add_argument(
        "--enable-blas", 
        action="store_true",
        help="Enable OpenBLAS backend for CPU optimization (Linux)"
    )
    
    args = parser.parse_args()
    
    # Create and run setup
    setup = CrossPlatformSetup(
        enable_cuda=args.enable_cuda,
        enable_blas=args.enable_blas,
        with_models=args.with_models
    )
    
    success = setup.run_setup()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()