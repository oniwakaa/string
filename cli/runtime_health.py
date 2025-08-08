#!/usr/bin/env python3
"""
Runtime Health Validation Module

This module provides runtime-focused dependency checking for the String CLI tool,
validating essential components from STRING_HOME rather than repo files.
"""

import importlib
import json
import platform
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .runtime_home import get_string_home, get_models_manifest_path


class DependencyError(Exception):
    """Custom exception for dependency validation failures."""
    
    def __init__(self, message: str, component: str, suggestions: List[str] = None):
        self.message = message
        self.component = component
        self.suggestions = suggestions or []
        super().__init__(self.message)


class RuntimeHealthChecker:
    """Runtime-focused health checking system using STRING_HOME."""
    
    def __init__(self):
        """Initialize the runtime health checker."""
        self.string_home = get_string_home()
        self.console = Console()
        
        # Core runtime packages required for CLI operation
        self.core_packages = {
            # Essential backend dependencies
            "llama_cpp": "LLaMA.cpp Python bindings (llama-cpp-python)",
            "transformers": "Hugging Face Transformers library",
            "sentence_transformers": "Sentence embeddings library",
            "torch": "PyTorch machine learning framework",
            "numpy": "Numerical computing library",
            
            # CLI dependencies
            "typer": "CLI framework",
            "rich": "Rich text and beautiful formatting",
            "httpx": "Async HTTP client",
            "yaml": "YAML parser (PyYAML)",
            
            # Optional but recommended
            "fastapi": "FastAPI web framework (for backend)",
            "qdrant_client": "Qdrant vector database client",
        }
        
        # Detect platform for specific checks
        self.system = platform.system().lower()
        self.arch = platform.machine().lower()
        self.is_apple_silicon = self.system == "darwin" and self.arch in ["arm64", "aarch64"]

    def check_runtime_essentials(self) -> Tuple[bool, List[str]]:
        """
        Verify that runtime essentials are properly configured.
        
        Returns:
            Tuple[bool, List[str]]: (success, list of issues)
        """
        issues = []
        
        # Check STRING_HOME exists and is initialized
        if not self.string_home.exists():
            issues.append("STRING_HOME directory not found - run setup to initialize")
            return False, issues
            
        marker_file = self.string_home / ".installed"
        if not marker_file.exists():
            issues.append("STRING_HOME not properly initialized - run setup")
            return False, issues
        
        # Check essential directories
        required_dirs = ["models", "config", "storage"]
        for dir_name in required_dirs:
            dir_path = self.string_home / dir_name
            if not dir_path.exists():
                issues.append(f"Missing {dir_name} directory in STRING_HOME")
        
        # Check essential config files (runtime-critical only)
        config_dir = self.string_home / "config"
        required_configs = ["models.json"]  # Only check critical runtime configs
        for config_name in required_configs:
            config_path = config_dir / config_name
            if not config_path.exists():
                issues.append(f"Missing critical config file: {config_name}")
        
        return len(issues) == 0, issues

    def check_core_packages(self) -> Tuple[bool, List[str]]:
        """
        Verify that essential Python packages are installed and importable.
        
        Returns:
            Tuple[bool, List[str]]: (success, list of missing packages)
        """
        missing_packages = []
        
        for package_name, description in self.core_packages.items():
            try:
                importlib.import_module(package_name)
            except ImportError:
                if package_name in ["fastapi", "qdrant_client"]:
                    # These are optional for CLI operation
                    continue
                missing_packages.append(f"{package_name} ({description})")
        
        return len(missing_packages) == 0, missing_packages

    def check_llama_cpp_backend(self) -> Tuple[bool, List[str]]:
        """
        Check llama-cpp-python installation and backend mode.
        
        Returns:
            Tuple[bool, List[str]]: (success, list of issues)
        """
        issues = []
        
        try:
            import llama_cpp
            
            # On macOS arm64, check for Metal support by examining build info
            if self.is_apple_silicon:
                try:
                    # Try to detect Metal support through various methods
                    metal_indicators = [
                        hasattr(llama_cpp, 'GGML_USE_METAL'),
                        'metal' in str(llama_cpp.__file__).lower(),
                        any('metal' in str(attr).lower() for attr in dir(llama_cpp) if not attr.startswith('_'))
                    ]
                    
                    if any(metal_indicators):
                        issues.append("✅ llama-cpp-python with Metal support detected")
                    else:
                        # Metal may still be available even if not explicitly detected
                        issues.append("✅ llama-cpp-python installed (Metal may be available)")
                except Exception:
                    issues.append("✅ llama-cpp-python installed (Metal status unknown)")
                    
        except ImportError:
            issues.append("❌ llama-cpp-python not installed")
            issues.append("   Run: pipx runpip string-ai-coding-assistant install llama-cpp-python")
            return False, issues
        
        return True, issues

    def check_models_availability(self) -> Tuple[bool, List[str]]:
        """
        Check if models are available in STRING_HOME.
        
        Returns:
            Tuple[bool, List[str]]: (success, list of missing models)
        """
        issues = []
        models_manifest_path = get_models_manifest_path()
        
        if not models_manifest_path.exists():
            issues.append("Models manifest not found in STRING_HOME/config")
            return False, issues
        
        try:
            with open(models_manifest_path, 'r') as f:
                manifest = json.load(f)
            
            models_dir = self.string_home / "models"
            missing_models = []
            
            # Check GGUF models
            for model in manifest.get("models", []):
                model_path = models_dir / model["local_dir"] / model["filename"]
                if not model_path.exists():
                    missing_models.append(f"{model['name']} ({model['filename']})")
            
            # Check embedding model
            embedding_config = manifest.get("embedding", {})
            if embedding_config:
                embedding_path = models_dir / embedding_config["local_dir"]
                if not embedding_path.exists():
                    missing_models.append(f"Embedding model ({embedding_config['name']})")
            
            if missing_models:
                issues.extend([f"Missing model: {model}" for model in missing_models])
                issues.append("Run setup with --with-models to download missing models")
                return False, issues
            else:
                issues.append(f"✅ All models present in {models_dir}")
                
        except Exception as e:
            issues.append(f"Error checking models manifest: {e}")
            return False, issues
        
        return True, issues

    def check_storage_paths(self) -> Tuple[bool, List[str]]:
        """
        Check if storage paths exist or can be created.
        
        Returns:
            Tuple[bool, List[str]]: (success, list of issues)
        """
        issues = []
        storage_dir = self.string_home / "storage"
        
        required_storage_dirs = ["qdrant_storage", "memory_cubes"]
        for dir_name in required_storage_dirs:
            dir_path = storage_dir / dir_name
            if not dir_path.exists():
                try:
                    dir_path.mkdir(parents=True, exist_ok=True)
                    issues.append(f"Created storage directory: {dir_path}")
                except Exception as e:
                    issues.append(f"Cannot create storage directory {dir_name}: {e}")
                    return False, issues
            else:
                issues.append(f"✅ Storage directory exists: {dir_path}")
        
        return True, issues

    def check_cli_availability(self) -> Tuple[bool, List[str]]:
        """
        Check if string-cli is globally available.
        
        Returns:
            Tuple[bool, List[str]]: (success, list of issues)
        """
        issues = []
        
        try:
            import shutil
            cli_path = shutil.which("string-cli")
            if cli_path:
                issues.append(f"✅ string-cli available at: {cli_path}")
                return True, issues
            else:
                issues.append("❌ string-cli not found in PATH")
                issues.append("   Add ~/.local/bin to PATH or restart terminal")
                return False, issues
        except Exception as e:
            issues.append(f"Error checking CLI availability: {e}")
            return False, issues

    def run_comprehensive_check(self, verbose: bool = False) -> bool:
        """
        Run comprehensive runtime health check.
        
        Args:
            verbose (bool): Show detailed progress information
            
        Returns:
            bool: True if all checks pass
        """
        all_passed = True
        
        if verbose:
            self.console.print("🏥 [blue]Runtime Health Check[/blue]")
            self.console.print(f"STRING_HOME: {self.string_home}")
            self.console.print()
        
        # Runtime essentials check
        success, issues = self.check_runtime_essentials()
        if not success:
            all_passed = False
            if verbose:
                self.console.print("❌ [red]Runtime Essentials:[/red]")
                for issue in issues:
                    self.console.print(f"   {issue}")
        elif verbose:
            self.console.print("✅ [green]Runtime Essentials:[/green] OK")
        
        # Core packages check
        success, issues = self.check_core_packages()
        if not success:
            all_passed = False
            if verbose:
                self.console.print("❌ [red]Core Packages:[/red]")
                for issue in issues:
                    self.console.print(f"   {issue}")
        elif verbose:
            self.console.print("✅ [green]Core Packages:[/green] OK")
        
        # llama-cpp-python check
        success, issues = self.check_llama_cpp_backend()
        if verbose:
            status = "✅ [green]" if success else "❌ [red]"
            self.console.print(f"{status}LLaMA Backend:[/] ")
            for issue in issues:
                self.console.print(f"   {issue}")
        if not success:
            all_passed = False
        
        # Models availability check
        success, issues = self.check_models_availability()
        if not success:
            all_passed = False
            if verbose:
                self.console.print("⚠️  [yellow]Models:[/yellow]")
                for issue in issues:
                    self.console.print(f"   {issue}")
        elif verbose:
            self.console.print("✅ [green]Models:[/green] Available")
            if issues:  # Show success messages
                for issue in issues:
                    self.console.print(f"   {issue}")
        
        # Storage paths check
        success, issues = self.check_storage_paths()
        if verbose:
            status = "✅ [green]" if success else "❌ [red]"
            self.console.print(f"{status}Storage Paths:[/]")
            for issue in issues:
                self.console.print(f"   {issue}")
        if not success:
            all_passed = False
        
        # CLI availability check
        success, issues = self.check_cli_availability()
        if verbose:
            status = "✅ [green]" if success else "⚠️  [yellow]"
            self.console.print(f"{status}CLI Availability:[/]")
            for issue in issues:
                self.console.print(f"   {issue}")
        
        return all_passed


def run_runtime_checks(verbose: bool = False) -> None:
    """
    Run runtime health checks and exit with appropriate code.
    
    Args:
        verbose (bool): Show detailed progress information
        
    Raises:
        DependencyError: If critical dependencies are missing
    """
    checker = RuntimeHealthChecker()
    
    if not checker.run_comprehensive_check(verbose=verbose):
        # Generate helpful error message
        suggestions = [
            "Run: python setup_cli.py --with-models",
            "Ensure pipx is properly configured: pipx ensurepath",
            "Restart terminal to refresh PATH"
        ]
        
        raise DependencyError(
            "Runtime validation failed - see output above for details",
            "runtime",
            suggestions
        )