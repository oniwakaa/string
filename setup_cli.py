#!/usr/bin/env python3
"""
Cross-Platform Installation Script for String AI Coding Assistant

This script creates a virtual environment and installs the string-cli package
with all dependencies. Works on Windows, macOS, and Linux.

Usage:
    python setup_cli.py
"""

import sys
import subprocess
import os
import platform
from pathlib import Path

VENV_NAME = "venv_string_cli"
PYTHON_CMD = sys.executable

def print_banner():
    """Display installation banner."""
    print("=" * 60)
    print("🤖 String AI Coding Assistant - Installation Script")
    print("=" * 60)
    print(f"Python version: {sys.version}")
    print(f"Operating System: {platform.system()} {platform.release()}")
    print(f"Virtual environment: {VENV_NAME}")
    print("-" * 60)

def run_command(command, description="Running command"):
    """
    Runs a command and exits if it fails.
    
    Args:
        command: List of command arguments
        description: Human-readable description of the command
    """
    print(f"📦 {description}...")
    print(f"   Command: {' '.join(command)}")
    
    try:
        result = subprocess.run(
            command, 
            check=True, 
            capture_output=True, 
            text=True
        )
        
        if result.stdout:
            print(f"   Output: {result.stdout.strip()}")
            
        return result
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Error executing command: {' '.join(command)}")
        print(f"   Return code: {e.returncode}")
        if e.stdout:
            print(f"   Stdout: {e.stdout}")
        if e.stderr:
            print(f"   Stderr: {e.stderr}")
        print("\n💡 Installation failed. Please check the error above and try again.")
        sys.exit(1)

def check_python_version():
    """Verify Python version meets requirements."""
    if sys.version_info < (3, 11):
        print(f"❌ Python 3.11+ required, but found {sys.version}")
        print("💡 Please install Python 3.11 or newer and try again.")
        sys.exit(1)
    
    print(f"✅ Python version check passed: {sys.version_info.major}.{sys.version_info.minor}")

def check_pip_available():
    """Ensure pip is available."""
    try:
        run_command([PYTHON_CMD, "-m", "pip", "--version"], "Checking pip availability")
        print("✅ pip is available")
    except:
        print("❌ pip is not available or not working properly")
        print("💡 Please ensure pip is installed and try again.")
        sys.exit(1)

def create_virtual_environment():
    """Create virtual environment."""
    venv_path = Path(VENV_NAME)
    
    if venv_path.exists():
        print(f"⚠️  Virtual environment '{VENV_NAME}' already exists")
        response = input("Do you want to remove it and create a new one? [y/N]: ")
        if response.lower() in ['y', 'yes']:
            import shutil
            print(f"🗑️  Removing existing virtual environment...")
            shutil.rmtree(venv_path)
        else:
            print("💡 Using existing virtual environment")
            return
    
    print(f"🔧 Creating virtual environment: {VENV_NAME}")
    run_command([PYTHON_CMD, "-m", "venv", VENV_NAME], "Creating virtual environment")
    print("✅ Virtual environment created successfully")

def get_pip_path():
    """Get the path to pip in the virtual environment."""
    system = platform.system().lower()
    venv_path = Path(VENV_NAME)
    
    if system == "windows":
        return venv_path / "Scripts" / "pip.exe"
    else:
        return venv_path / "bin" / "pip"

def get_activation_command():
    """Get the command to activate the virtual environment."""
    system = platform.system().lower()
    
    if system == "windows":
        return {
            "cmd": f"{VENV_NAME}\\Scripts\\activate.bat",
            "powershell": f".\\{VENV_NAME}\\Scripts\\Activate.ps1"
        }
    else:
        return f"source {VENV_NAME}/bin/activate"

def install_package():
    """Install the string-cli package and dependencies."""
    pip_path = get_pip_path()
    
    if not pip_path.exists():
        print(f"❌ pip not found at expected location: {pip_path}")
        sys.exit(1)
    
    print("📦 Installing string-cli and dependencies...")
    print("   This may take a few minutes depending on your internet connection...")
    
    # Upgrade pip first
    run_command([str(pip_path), "install", "--upgrade", "pip"], "Upgrading pip")
    
    # Install the package in editable mode
    run_command([str(pip_path), "install", "-e", "."], "Installing string-cli package")
    
    print("✅ Installation completed successfully!")

def verify_installation():
    """Verify that the installation was successful."""
    print("🔍 Verifying installation...")
    
    # Get the path to the installed CLI
    system = platform.system().lower()
    venv_path = Path(VENV_NAME)
    
    if system == "windows":
        cli_path = venv_path / "Scripts" / "string-cli.exe"
    else:
        cli_path = venv_path / "bin" / "string-cli"
    
    if cli_path.exists():
        print(f"✅ string-cli executable found at: {cli_path}")
    else:
        print(f"⚠️  string-cli executable not found at expected location: {cli_path}")
        print("💡 The installation may have succeeded, but the executable location is different than expected.")
    
    # Try to run the CLI version command
    try:
        if system == "windows":
            python_path = venv_path / "Scripts" / "python.exe"
        else:
            python_path = venv_path / "bin" / "python"
        
        result = run_command([str(python_path), "-m", "cli.main", "--version"], "Testing CLI functionality")
        print("✅ CLI functionality test passed")
        
    except:
        print("⚠️  CLI functionality test failed, but the package may still be installed correctly")

def print_success_message():
    """Print final success message with usage instructions."""
    activation_cmd = get_activation_command()
    
    print("\n" + "=" * 60)
    print("🎉 Installation complete!")
    print("=" * 60)
    print("To use the String AI Coding Assistant, follow these steps:")
    print("\n1️⃣  Activate the virtual environment:")
    
    if isinstance(activation_cmd, dict):
        print(f"   Command Prompt:  {activation_cmd['cmd']}")
        print(f"   PowerShell:      {activation_cmd['powershell']}")
    else:
        print(f"   {activation_cmd}")
    
    print("\n2️⃣  Verify the installation:")
    print("   string-cli --version")
    
    print("\n3️⃣  Get help and see available commands:")
    print("   string-cli --help")
    
    print("\n4️⃣  Start using the assistant:")
    print("   string-cli validate                    # Run dependency checks")
    print("   string-cli health                      # Check backend status")
    print("   string-cli \"analyze my Python code\"   # Natural language tasks")
    
    print("\n💡 Pro tip: Run 'string-cli validate' first to ensure all dependencies are properly configured.")
    print("\n📚 For more information, see the project documentation.")
    print("=" * 60)

def main():
    """Main installation process."""
    try:
        print_banner()
        
        # Pre-flight checks
        check_python_version()
        check_pip_available()
        
        # Create virtual environment
        create_virtual_environment()
        
        # Install package
        install_package()
        
        # Verify installation
        verify_installation()
        
        # Success message
        print_success_message()
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Installation interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Unexpected error during installation: {e}")
        print("💡 Please report this issue on the project's GitHub repository.")
        sys.exit(1)

if __name__ == "__main__":
    main()