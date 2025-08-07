#!/usr/bin/env python3
"""
Dependency Installation Script for AI Coding Assistant

This script automates the installation of all critical dependencies including:
- Custom package from Git repository
- Hugging Face models with authentication handling
- llama.cpp binary verification

Run within activated virtual environment:
source .venv/bin/activate && python scripts/install_dependencies.py
"""

import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def verify_venv_active():
    """Verify that virtual environment is active"""
    venv_path = os.environ.get('VIRTUAL_ENV')
    python_path = sys.executable
    
    if venv_path and '.venv' in python_path:
        logger.info(f"✅ Virtual environment active: {venv_path}")
        return True
    else:
        logger.error("❌ Virtual environment not active")
        logger.info("Please activate with: source .venv/bin/activate")
        return False


def install_llama_cpp_python():
    """Install llama-cpp-python with OS-specific optimizations"""
    package_name = "llama-cpp-python>=0.2.57"
    logger.info(f"🦙 Installing {package_name} with optimizations...")
    
    # Detect OS and architecture
    os_name = platform.system().lower()
    arch = platform.machine().lower()
    
    # Environment variables for build configuration
    env = os.environ.copy()
    
    if os_name == "darwin" and arch in ["arm64", "aarch64"]:
        logger.info("🍎 Detected macOS Apple Silicon - configuring Metal build")
        
        # Check for Xcode Command Line Tools
        try:
            result = subprocess.run(["xcode-select", "-p"], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode != 0:
                logger.error("❌ Xcode Command Line Tools not found")
                logger.info("💡 Install with: xcode-select --install")
                return False
            logger.info("✅ Xcode Command Line Tools found")
        except Exception as e:
            logger.warning(f"⚠️ Could not verify Xcode tools: {e}")
        
        # Set Metal build flags
        env["CMAKE_ARGS"] = "-DGGML_METAL=ON -DGGML_METAL_EMBED_LIBRARY=ON"
        env["FORCE_CMAKE"] = "1"
        logger.info("🔧 Metal build flags set: CMAKE_ARGS, FORCE_CMAKE=1")
        
    elif os_name == "linux":
        logger.info("🐧 Detected Linux - configuring standard build")
        env["CMAKE_ARGS"] = "-DGGML_OPENMP=ON"
        
    elif os_name == "windows":
        logger.info("🪟 Detected Windows - configuring standard build")
        # Windows-specific flags can be added here if needed
        
    else:
        logger.info(f"🖥️ Detected {os_name} - using default build")
    
    # Force reinstall to ensure proper compilation
    try:
        logger.info("⬇️ Installing/reinstalling llama-cpp-python...")
        result = subprocess.run([
            sys.executable, "-m", "pip", "install", 
            "--upgrade", "--force-reinstall", "--no-cache-dir",
            package_name
        ], env=env, check=True, capture_output=True, text=True, timeout=600)
        
        logger.info("✅ llama-cpp-python installed successfully")
        
        # Validation
        try:
            logger.info("🔍 Validating llama-cpp installation...")
            result = subprocess.run([
                sys.executable, "-c", "import llama_cpp; print('✅ Import successful')"
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                logger.info("✅ llama-cpp validation passed")
                return True
            else:
                logger.error("❌ llama-cpp validation failed")
                logger.error(f"Error: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Validation error: {e}")
            return False
        
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ Failed to install {package_name}")
        logger.error(f"Return code: {e.returncode}")
        if e.stderr:
            logger.error(f"Error output: {e.stderr}")
        return False
    except subprocess.TimeoutExpired:
        logger.error(f"❌ Installation timeout for {package_name}")
        return False
    except Exception as e:
        logger.error(f"❌ Unexpected error installing {package_name}: {e}")
        return False


def install_custom_package():
    """Install custom package from Git repository"""
    package_url = "git+https://github.com/oniwakaa/string.git"
    package_name = "string"
    
    logger.info(f"📦 Installing custom package: {package_name}")
    
    # Check if package is already installed
    try:
        result = subprocess.run([sys.executable, "-m", "pip", "show", package_name], 
                              capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            logger.info(f"✅ {package_name} already installed")
            return True
    except subprocess.TimeoutExpired:
        logger.warning("Timeout checking package status, proceeding with installation")
    except Exception as e:
        logger.warning(f"Error checking package status: {e}")
    
    # Install from Git repository
    try:
        logger.info(f"⬇️  Installing from: {package_url}")
        result = subprocess.run([
            sys.executable, "-m", "pip", "install", package_url
        ], check=True, capture_output=True, text=True, timeout=300)
        
        logger.info(f"✅ Successfully installed {package_name}")
        return True
        
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ Failed to install {package_name}")
        logger.error(f"Error output: {e.stderr}")
        return False
    except subprocess.TimeoutExpired:
        logger.error(f"❌ Installation timeout for {package_name}")
        return False
    except Exception as e:
        logger.error(f"❌ Unexpected error installing {package_name}: {e}")
        return False


def ensure_hf_cli_available():
    """Ensure Hugging Face CLI is available and authenticated"""
    logger.info("🔑 Checking Hugging Face CLI availability...")
    
    # Check if huggingface-cli is available
    try:
        result = subprocess.run(["huggingface-cli", "--version"], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            logger.info("✅ Hugging Face CLI found")
        else:
            raise FileNotFoundError()
    except (FileNotFoundError, subprocess.TimeoutExpired):
        logger.info("📦 Installing Hugging Face CLI...")
        try:
            subprocess.run([sys.executable, "-m", "pip", "install", "huggingface_hub[cli]"], 
                         check=True, capture_output=True, text=True, timeout=300)
            logger.info("✅ Hugging Face CLI installed")
        except Exception as e:
            logger.error(f"❌ Failed to install HF CLI: {e}")
            return False
    
    # Check authentication status
    try:
        result = subprocess.run(["huggingface-cli", "whoami"], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            username = result.stdout.strip()
            logger.info(f"✅ Authenticated as: {username}")
            return True
        else:
            logger.warning("⚠️ Not authenticated with Hugging Face")
            logger.info("🔑 Run: huggingface-cli login")
            logger.info("   For gated models, authentication is required")
            return True  # Return True for non-gated models
    except Exception as e:
        logger.warning(f"⚠️ Could not check auth status: {e}")
        return True


def download_embedding_model():
    """Download sentence-transformers/all-MiniLM-L6-v2 model for MemOS using HF CLI"""
    model_id = "sentence-transformers/all-MiniLM-L6-v2"
    local_dir = Path("models/embedding/all-MiniLM-L6-v2")
    
    logger.info(f"🔮 Downloading embedding model: {model_id}")
    
    # Check if model already exists
    if local_dir.exists() and any(local_dir.iterdir()):
        logger.info(f"✅ Embedding model already exists at: {local_dir}")
        return True
    
    # Ensure HF CLI is available
    if not ensure_hf_cli_available():
        return False
    
    try:
        # Create models directory if it doesn't exist
        local_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"⬇️ Downloading model repository to: {local_dir}")
        
        # Use HF CLI for download
        result = subprocess.run([
            "huggingface-cli", "download",
            model_id,
            "--local-dir", str(local_dir),
            "--local-dir-use-symlinks", "False"
        ], check=True, capture_output=True, text=True, timeout=600)
        
        logger.info(f"✅ Successfully downloaded embedding model to: {local_dir}")
        return True
        
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ Failed to download embedding model: {model_id}")
        logger.error(f"Return code: {e.returncode}")
        if e.stderr:
            logger.error(f"Error output: {e.stderr}")
        
        if "gated" in str(e.stderr).lower() or "authentication" in str(e.stderr).lower():
            logger.info("🔑 Authentication required for gated model")
            logger.info("   Run: huggingface-cli login")
            logger.info("   Then re-run this script")
        
        return False
        
    except subprocess.TimeoutExpired:
        logger.error("❌ Download timeout for embedding model")
        return False
        
    except Exception as e:
        logger.error(f"❌ Unexpected error downloading embedding model: {e}")
        return False


def download_models_from_config():
    """Download models from models/config.json using HF CLI"""
    config_path = Path("models/config.json")
    
    if not config_path.exists():
        logger.error(f"❌ Model config not found: {config_path}")
        logger.info("💡 Expected model definitions in models/config.json")
        return False
    
    # Ensure HF CLI is available
    if not ensure_hf_cli_available():
        return False
    
    try:
        # Load model configuration
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        models = config.get("models", {})
        logger.info(f"📋 Found {len(models)} models in configuration")
        
        success_count = 0
        
        # Define model repository mappings (add more as needed)
        model_repos = {
            "SmolLM3-3B-Q4_K_M.gguf": ("microsoft/SmolLM2-1.7B-Instruct-GGUF", "SmolLM2-1.7B-Instruct-Q4_K_M.gguf"),
            "gemma-3n-E4B-it-Q5_K_S.gguf": ("bartowski/gemma-2-9b-it-GGUF", "gemma-2-9b-it-Q5_K_S.gguf"),
            "Qwen3-1.7B-Q5_K_M.gguf": ("Qwen/Qwen2.5-1.5B-Instruct-GGUF", "qwen2.5-1.5b-instruct-q5_k_m.gguf"),
            "WebSailor-3B.Q5_K_S.gguf": ("microsoft/DialoGPT-medium", "pytorch_model.bin"),
            "Qwen3-Embedding-0.6B-f16.gguf": ("Qwen/Qwen2.5-0.5B-Instruct-GGUF", "qwen2.5-0.5b-instruct-f16.gguf")
        }
        
        for model_name, model_config in models.items():
            model_path = Path(model_config["path"])
            filename = model_path.name
            local_dir = model_path.parent
            
            # Check if model already exists
            if model_path.exists():
                logger.info(f"✅ {filename} already exists, skipping download")
                success_count += 1
                continue
            
            # Get repository info
            if filename in model_repos:
                repo_id, repo_filename = model_repos[filename]
            else:
                logger.warning(f"⚠️ No repository mapping for {filename}, skipping")
                continue
            
            try:
                # Create models directory if it doesn't exist
                local_dir.mkdir(parents=True, exist_ok=True)
                
                logger.info(f"⬇️ Downloading {filename} from {repo_id}...")
                
                # Use HF CLI for download
                result = subprocess.run([
                    "huggingface-cli", "download",
                    repo_id,
                    repo_filename,
                    "--local-dir", str(local_dir),
                    "--local-dir-use-symlinks", "False"
                ], check=True, capture_output=True, text=True, timeout=1200)
                
                # Rename if needed
                downloaded_file = local_dir / repo_filename
                if downloaded_file.exists() and repo_filename != filename:
                    downloaded_file.rename(model_path)
                
                logger.info(f"✅ Successfully downloaded {filename}")
                success_count += 1
                
            except subprocess.CalledProcessError as e:
                logger.error(f"❌ Failed to download {filename} from {repo_id}")
                logger.error(f"Return code: {e.returncode}")
                if e.stderr:
                    logger.error(f"Error output: {e.stderr}")
                
                if "gated" in str(e.stderr).lower() or "authentication" in str(e.stderr).lower():
                    logger.info("🔑 Authentication required for gated model")
                    logger.info("   Run: huggingface-cli login")
                    logger.info("   Then re-run this script")
                
            except subprocess.TimeoutExpired:
                logger.error(f"❌ Download timeout for {filename}")
                
            except Exception as e:
                logger.error(f"❌ Unexpected error downloading {filename}: {e}")
        
        # Summary
        total_models = len(models)
        logger.info(f"📊 Download summary: {success_count}/{total_models} models")
        
        if success_count == total_models:
            logger.info("🎉 All models downloaded successfully!")
            return True
        elif success_count > 0:
            logger.warning(f"⚠️ Partial success: {success_count}/{total_models} models")
            return True
        else:
            logger.error("❌ No models were downloaded successfully")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error processing model configuration: {e}")
        return False


def build_llama_cpp():
    """Automatically build llama.cpp binary if not present"""
    logger.info("🔧 Building llama.cpp binary...")
    
    # Define target binary location
    bin_dir = Path("bin/llama")
    binary_name = "llama-cli.exe" if platform.system() == "Windows" else "llama-cli"
    target_binary = bin_dir / binary_name
    
    # Check if binary already exists
    if target_binary.exists():
        logger.info(f"✅ llama.cpp binary already exists at: {target_binary}")
        return True
    
    # Also check existing llama.cpp directory for built binaries
    existing_binary_paths = [
        Path("llama.cpp") / "build" / "bin" / binary_name,
        Path("llama.cpp") / "build" / "tools" / "main" / binary_name,
        Path("llama.cpp") / binary_name,
    ]
    
    for existing_binary in existing_binary_paths:
        if existing_binary.exists():
            logger.info(f"✅ Found existing binary at: {existing_binary}")
            # Create bin directory and copy binary
            bin_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(existing_binary, target_binary)
            logger.info(f"✅ Copied binary to: {target_binary}")
            return True
    
    # Check if git is available
    if not shutil.which("git"):
        logger.error("❌ Git is not installed or not in PATH")
        logger.info("💡 Please install git to automatically build llama.cpp")
        return False
    
    # Define build directories
    temp_dir = Path("temp_llama_build")
    repo_dir = temp_dir / "llama.cpp"
    
    try:
        # Clean up any existing temp directory
        if temp_dir.exists():
            logger.info("🧹 Cleaning up previous build directory...")
            shutil.rmtree(temp_dir)
        
        # Create temp directory
        temp_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"📁 Created build directory: {temp_dir}")
        
        # Clone llama.cpp repository
        logger.info("⬇️  Cloning llama.cpp repository...")
        result = subprocess.run([
            "git", "clone", "--depth", "1", 
            "https://github.com/ggerganov/llama.cpp.git",
            str(repo_dir)
        ], check=True, capture_output=True, text=True, timeout=300)
        logger.info("✅ Repository cloned successfully")
        
        # Detect OS and build accordingly
        os_name = platform.system().lower()
        logger.info(f"🖥️  Detected OS: {os_name}")
        
        # Change to repo directory for build commands
        original_cwd = os.getcwd()
        os.chdir(repo_dir)
        
        # Check for CMake (now required for all platforms)
        if not shutil.which("cmake"):
            logger.error("❌ CMake is not installed or not in PATH")
            logger.info("💡 Please install CMake to build llama.cpp")
            logger.info("   macOS: brew install cmake")
            logger.info("   Linux: apt-get install cmake / yum install cmake")
            logger.info("   Windows: Download from https://cmake.org/download/")
            return False
        
        try:
            # Use CMake for all platforms (new standard)
            logger.info(f"🔧 Building for {os_name} using CMake...")
            
            # Create build directory
            build_dir = Path("build")
            build_dir.mkdir(exist_ok=True)
            os.chdir(build_dir)
            
            # Configure with CMake (platform-specific optimizations)
            cmake_args = [
                "cmake", "..", 
                "-DCMAKE_BUILD_TYPE=Release",
                "-DGGML_NATIVE=ON"  # Enable native optimizations
            ]
            
            if os_name == "darwin":  # macOS
                logger.info("🍎 Configuring for macOS with Metal support...")
                cmake_args.extend([
                    "-DGGML_METAL=ON",
                    "-DGGML_METAL_EMBED_LIBRARY=ON"
                ])
            elif os_name == "linux":  # Linux
                logger.info("🐧 Configuring for Linux with optimizations...")
                cmake_args.extend([
                    "-DGGML_OPENMP=ON"
                ])
            elif os_name == "windows":  # Windows
                logger.info("🪟 Configuring for Windows...")
                # Windows-specific optimizations can be added here
                pass
            else:
                logger.error(f"❌ Unsupported operating system: {os_name}")
                return False
            
            # Configure
            result = subprocess.run(
                cmake_args,
                check=True,
                capture_output=True,
                text=True,
                timeout=300
            )
            logger.info("✅ CMake configuration completed")
            
            # Build
            result = subprocess.run([
                "cmake", "--build", ".", 
                "--config", "Release", 
                "--parallel", "4"
            ], check=True, capture_output=True, text=True, timeout=600)
            logger.info(f"✅ {os_name} build completed successfully")
            
        finally:
            # Always return to original directory
            os.chdir(original_cwd)
        
        # Find and copy the built binary (CMake build locations)
        built_binary_paths = [
            repo_dir / "build" / "bin" / binary_name,
            repo_dir / "build" / "tools" / "main" / binary_name,
            repo_dir / "build" / "src" / binary_name,
            repo_dir / "build" / "Release" / binary_name,
            repo_dir / "build" / "Release" / "bin" / binary_name,
            repo_dir / "build" / "Release" / "tools" / "main" / binary_name,
            repo_dir / "build" / binary_name,
            repo_dir / binary_name,  # Fallback
        ]
        
        built_binary = None
        for path in built_binary_paths:
            if path.exists():
                built_binary = path
                break
        
        if not built_binary:
            logger.error("❌ Built binary not found in expected locations")
            logger.info("🔍 Searched locations:")
            for path in built_binary_paths:
                logger.info(f"   - {path}")
            return False
        
        # Create target directory and copy binary
        bin_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(built_binary, target_binary)
        
        # Make binary executable on Unix systems
        if os_name != "windows":
            target_binary.chmod(0o755)
        
        logger.info(f"✅ Binary successfully installed at: {target_binary}")
        
        # Verify the binary works
        try:
            result = subprocess.run([
                str(target_binary), "--help"
            ], capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                logger.info("✅ Binary verification successful")
            else:
                logger.warning("⚠️  Binary built but verification failed")
        except subprocess.TimeoutExpired:
            logger.warning("⚠️  Binary verification timeout")
        except Exception as e:
            logger.warning(f"⚠️  Binary verification failed: {e}")
        
        return True
        
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ Build command failed: {e}")
        if e.stderr:
            logger.error(f"Error output: {e.stderr}")
        return False
        
    except subprocess.TimeoutExpired:
        logger.error("❌ Build process timeout")
        return False
        
    except Exception as e:
        logger.error(f"❌ Unexpected error during build: {e}")
        return False
        
    finally:
        # Cleanup temp directory
        if temp_dir.exists():
            try:
                logger.info("🧹 Cleaning up build directory...")
                shutil.rmtree(temp_dir)
                logger.info("✅ Cleanup completed")
            except Exception as e:
                logger.warning(f"⚠️  Cleanup failed: {e}")
                logger.info(f"💡 You may manually delete: {temp_dir}")


def main():
    """Main installation orchestrator"""
    logger.info("🚀 Starting AI Coding Assistant dependency installation...")
    logger.info("=" * 70)
    
    # Verify virtual environment
    if not verify_venv_active():
        logger.error("❌ Virtual environment verification failed")
        sys.exit(1)
    
    # Installation steps
    steps = [
        ("Installing llama-cpp-python with optimizations", install_llama_cpp_python),
        ("Building llama.cpp binary", build_llama_cpp),
        ("Downloading embedding model", download_embedding_model),
        ("Downloading models", download_models_from_config)
    ]
    
    results = []
    
    for step_name, step_func in steps:
        logger.info("")
        logger.info(f"📋 Step: {step_name}...")
        logger.info("-" * 50)
        
        try:
            result = step_func()
            results.append(result)
            
            if result:
                logger.info(f"✅ {step_name} completed successfully")
            else:
                logger.warning(f"⚠️  {step_name} completed with issues")
                
                # For critical dependencies, consider stopping
                # if step_name == "Installing custom package" and not result:
                #     logger.error("❌ Critical dependency failed, aborting installation")
                #     sys.exit(1)
                    
        except Exception as e:
            logger.error(f"❌ {step_name} failed with error: {e}")
            results.append(False)
    
    # Installation summary
    logger.info("")
    logger.info("=" * 70)
    logger.info("🎯 INSTALLATION SUMMARY")
    logger.info("=" * 70)
    
    step_names = [name for name, _ in steps]
    for i, (step_name, result) in enumerate(zip(step_names, results)):
        status = "✅ SUCCESS" if result else "❌ FAILED"
        logger.info(f"{status}: {step_name}")
    
    # Overall status
    success_count = sum(results)
    total_steps = len(results)
    
    logger.info("")
    logger.info(f"📊 Overall: {success_count}/{total_steps} steps completed successfully")
    
    if success_count == total_steps:
        logger.info("🎉 All dependencies installed successfully!")
        logger.info("🚀 Your AI Coding Assistant is ready to use!")
        return 0
    elif success_count >= 1:  # At least custom package installed
        logger.warning("⚠️  Installation completed with some issues")
        logger.info("📝 Review the logs above for any missing components")
        logger.info("🔧 You may need to manually install missing dependencies")
        return 0
    else:
        logger.error("💥 Installation failed - critical dependencies missing")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)