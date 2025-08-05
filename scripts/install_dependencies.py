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


def download_embedding_model():
    """Download sentence-transformers/all-MiniLM-L6-v2 model for MemOS"""
    model_id = "sentence-transformers/all-MiniLM-L6-v2"
    local_dir = Path("models/embedding/all-MiniLM-L6-v2")
    
    logger.info(f"🔮 Downloading embedding model: {model_id}")
    
    # Check if model already exists
    if local_dir.exists() and any(local_dir.iterdir()):
        logger.info(f"✅ Embedding model already exists at: {local_dir}")
        return True
    
    try:
        # Install huggingface_hub if not available
        try:
            import huggingface_hub
        except ImportError:
            logger.info("📦 Installing huggingface_hub...")
            subprocess.run([sys.executable, "-m", "pip", "install", "huggingface_hub"], 
                         check=True, capture_output=True)
            import huggingface_hub
        
        from huggingface_hub import snapshot_download
        from huggingface_hub.utils import RepositoryNotFoundError, GatedRepoError
        
        # Create models directory if it doesn't exist
        local_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"⬇️  Downloading complete model repository to: {local_dir}")
        
        # Download the entire model repository
        snapshot_download(
            repo_id=model_id,
            local_dir=local_dir,
            local_dir_use_symlinks=False,
            ignore_patterns=["*.msgpack", "*.h5"]  # Skip unnecessary files
        )
        
        logger.info(f"✅ Successfully downloaded embedding model to: {local_dir}")
        return True
        
    except GatedRepoError:
        logger.error(f"❌ Authentication required for {model_id}")
        logger.info("🔑 Please authenticate with Hugging Face:")
        logger.info("   Run: huggingface-cli login")
        logger.info("   Then re-run this script")
        return False
        
    except RepositoryNotFoundError:
        logger.error(f"❌ Repository not found: {model_id}")
        return False
        
    except Exception as e:
        logger.error(f"❌ Failed to download embedding model: {e}")
        logger.error(f"   This may be due to expired Hugging Face token or network issues")
        logger.info("💡 Try running: huggingface-cli login --token <your_token>")
        return False


def download_models_from_manifest():
    """Download models from models.json manifest"""
    manifest_path = Path("models.json")
    
    if not manifest_path.exists():
        logger.error(f"❌ Model manifest not found: {manifest_path}")
        return False
    
    try:
        # Install huggingface_hub if not available
        try:
            import huggingface_hub
        except ImportError:
            logger.info("📦 Installing huggingface_hub...")
            subprocess.run([sys.executable, "-m", "pip", "install", "huggingface_hub"], 
                         check=True, capture_output=True)
            import huggingface_hub
        
        from huggingface_hub import hf_hub_download
        from huggingface_hub.utils import RepositoryNotFoundError, GatedRepoError
        
        # Load manifest
        with open(manifest_path, 'r') as f:
            models = json.load(f)
        
        logger.info(f"📋 Found {len(models)} models in manifest")
        
        success_count = 0
        
        for model in models:
            repo_id = model["repo_id"]
            filename = model["filename"]
            local_path = Path(model["local_path"])
            
            # Create models directory if it doesn't exist
            local_path.mkdir(parents=True, exist_ok=True)
            
            model_file_path = local_path / filename
            
            # Check if model already exists
            if model_file_path.exists():
                logger.info(f"✅ {filename} already exists, skipping download")
                success_count += 1
                continue
            
            try:
                logger.info(f"⬇️  Downloading {filename} from {repo_id}...")
                
                downloaded_path = hf_hub_download(
                    repo_id=repo_id,
                    filename=filename,
                    local_dir=local_path,
                    local_dir_use_symlinks=False
                )
                
                logger.info(f"✅ Successfully downloaded {filename}")
                success_count += 1
                
            except GatedRepoError:
                logger.error(f"❌ Authentication required for {repo_id}")
                logger.info("🔑 Please authenticate with Hugging Face:")
                logger.info("   Run: huggingface-cli login")
                logger.info("   Then re-run this script")
                
            except RepositoryNotFoundError:
                logger.error(f"❌ Repository not found: {repo_id}")
                logger.info(f"   Please verify the repository URL exists")
                
            except Exception as e:
                logger.error(f"❌ Failed to download {filename}: {e}")
        
        # Summary
        total_models = len(models)
        logger.info(f"📊 Download summary: {success_count}/{total_models} models")
        
        if success_count == total_models:
            logger.info("🎉 All models downloaded successfully!")
            return True
        elif success_count > 0:
            logger.warning(f"⚠️  Partial success: {success_count}/{total_models} models")
            return True
        else:
            logger.error("❌ No models were downloaded successfully")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error processing model manifest: {e}")
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
        # ("Installing custom package", install_custom_package),  # Temporarily disabled
        ("Building llama.cpp binary", build_llama_cpp),
        ("Downloading embedding model", download_embedding_model),
        ("Downloading models", download_models_from_manifest)
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