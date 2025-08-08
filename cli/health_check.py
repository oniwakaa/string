#!/usr/bin/env python3
"""
CLI Pre-flight Dependency Validation Module

This module provides comprehensive dependency checking for the String CLI tool,
including Python packages, custom components, machine learning models, and 
system binaries required for the multi-agent AI coding assistant.
"""

import glob
import importlib
import json
import platform
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table


class DependencyError(Exception):
    """Custom exception for dependency validation failures."""
    
    def __init__(self, message: str, component: str, suggestions: List[str] = None):
        self.message = message
        self.component = component
        self.suggestions = suggestions or []
        super().__init__(self.message)


class HealthChecker:
    """Centralized health checking system for CLI dependencies."""
    
    def __init__(self, project_root: Optional[Path] = None):
        """Initialize the health checker with project root detection."""
        if project_root is None:
            # Auto-detect project root by finding pyproject.toml or models directory
            # First try current working directory 
            if (Path.cwd() / "pyproject.toml").exists() or (Path.cwd() / "models").exists():
                project_root = Path.cwd()
            else:
                # Try searching from CLI module location
                current = Path(__file__).parent
                while current != current.parent:
                    if (current / "pyproject.toml").exists() or (current / "models").exists():
                        project_root = current
                        break
                    current = current.parent
                else:
                    # Fallback to current directory
                    project_root = Path.cwd()
        
        self.project_root = Path(project_root).resolve()
        self.console = Console()
        
        # Core package requirements based on pyproject.toml
        self.core_packages = {
            # Backend dependencies
            "fastapi": "FastAPI web framework",
            "uvicorn": "ASGI server for FastAPI",
            "llama_cpp": "LLaMA.cpp Python bindings (llama-cpp-python)",
            "transformers": "Hugging Face Transformers library",
            "qdrant_client": "Qdrant vector database client",
            "sqlalchemy": "SQL toolkit and ORM",
            "pydantic": "Data validation library",
            "numpy": "Numerical computing library",
            "torch": "PyTorch machine learning framework",
            "sentence_transformers": "Sentence embeddings library",
            "requests": "HTTP library",
            "aiofiles": "Async file operations",
            "pyyaml": "YAML parser",
            
            # CLI dependencies
            "typer": "CLI framework",
            "rich": "Rich text and beautiful formatting",
            "httpx": "Async HTTP client",
        }
        
        # Custom components and their expected locations
        self.custom_components = {
            "memos": "MemOS custom component",
            "agents": "Multi-agent system components",
        }
        
        # Expected llama.cpp binary locations
        self.llama_cpp_paths = [
            self.project_root / "llama.cpp" / "build" / "bin" / "llama-cli",
            self.project_root / "llama.cpp" / "build" / "bin" / "llama-server",
            self.project_root / "llama.cpp" / "llama-cli",  # Alternative location
            self.project_root / "llama.cpp" / "llama",      # Alternative location
        ]

    def check_core_packages(self) -> Tuple[bool, List[str]]:
        """
        Verify that all essential Python packages are installed and importable.
        
        Returns:
            Tuple[bool, List[str]]: (success, list of missing packages)
        """
        missing_packages = []
        
        for package_name, description in self.core_packages.items():
            try:
                # Handle special cases for package import names
                import_name = package_name
                if package_name == "llama_cpp":
                    import_name = "llama_cpp"
                elif package_name == "sentence_transformers":
                    import_name = "sentence_transformers"
                elif package_name == "qdrant_client":
                    import_name = "qdrant_client"
                elif package_name == "pyyaml":
                    import_name = "yaml"
                
                importlib.import_module(import_name)
                
            except ImportError as e:
                missing_packages.append(f"{package_name} ({description})")
        
        return len(missing_packages) == 0, missing_packages
    
    def check_llama_cpp_backend(self) -> Tuple[bool, List[str]]:
        """
        Verify llama-cpp-python backend configuration and Metal availability on macOS.
        
        Returns:
            Tuple[bool, List[str]]: (success, list of backend issues)
        """
        backend_issues = []
        
        try:
            import llama_cpp
            
            # On macOS Apple Silicon, check if Metal is available
            system = platform.system().lower()
            arch = platform.machine().lower()
            is_apple_silicon = system == "darwin" and arch in ["arm64", "aarch64"]
            
            if is_apple_silicon:
                try:
                    # Try to create a minimal Metal-enabled model instance to verify Metal support
                    # This is a basic test - we don't need to load a full model
                    test_params = {
                        "model_path": "/dev/null",  # Non-existent path for testing
                        "n_ctx": 512,
                        "n_gpu_layers": 1,  # Test Metal availability
                        "verbose": False
                    }
                    
                    # The constructor will fail for missing model but Metal init should succeed
                    try:
                        llama_cpp.Llama(**test_params)
                    except Exception as e:
                        error_msg = str(e).lower()
                        if "metal" not in error_msg and "gpu" not in error_msg:
                            # Metal is available but model path is invalid (expected)
                            pass  
                        else:
                            backend_issues.append("Metal backend not available (CPU-only build detected)")
                            
                except Exception:
                    backend_issues.append("Unable to verify Metal backend availability")
                    
        except ImportError:
            backend_issues.append("llama-cpp-python not installed or not importable")
        
        return len(backend_issues) == 0, backend_issues

    def check_custom_components(self) -> Tuple[bool, List[str]]:
        """
        Validate project-specific custom components and dependencies.
        
        Returns:
            Tuple[bool, List[str]]: (success, list of missing components)
        """
        missing_components = []
        
        # Check for custom Python modules in the project
        for component, description in self.custom_components.items():
            component_path = self.project_root / component
            src_component_path = self.project_root / "src" / component
            
            if not (component_path.exists() or src_component_path.exists()):
                missing_components.append(f"{component} ({description})")
        
        # Check for MemOS integration
        memos_paths = [
            self.project_root / "src" / "memos",
            self.project_root / "MemOS" / "src" / "memos",
        ]
        
        memos_found = any(path.exists() and path.is_dir() for path in memos_paths)
        if not memos_found:
            missing_components.append("MemOS integration (required for RAG functionality)")
        
        # Check for llama.cpp binary availability
        llama_cpp_found = any(path.exists() and path.is_file() for path in self.llama_cpp_paths)
        if not llama_cpp_found:
            missing_components.append("llama.cpp binary (required for local model inference)")
        
        return len(missing_components) == 0, missing_components

    def check_ml_models(self) -> Tuple[bool, List[str]]:
        """
        Verify that all required machine learning models are present.
        
        Returns:
            Tuple[bool, List[str]]: (success, list of missing models)
        """
        missing_models = []
        
        # Note: Skip strict models.json validation as filenames may vary due to different quantization levels
        # Instead rely on pattern-based checking below for more flexibility
        
        # Check for critical models that should be present based on CLAUDE.md documentation
        # Only check for models that are actually expected to exist
        models_dir = self.project_root / "models"
        if models_dir.exists():
            # Check for at least some core models - be flexible about exact filenames/quantization
            core_model_patterns = [
                "SmolLM3-3B*.gguf",      # Primary LLM  
                "gemma-3n-E4B*.gguf",    # Code Generator LLM
                "Qwen3-1.7B*.gguf",      # Quality LLM
                "WebSailor*.gguf",       # Web Scraper LLM
            ]
            
            for pattern in core_model_patterns:
                matching_files = list(models_dir.glob(pattern))
                if not matching_files:
                    # Extract base name from pattern for error message
                    base_name = pattern.replace("*.gguf", "").replace("*", "")
                    missing_models.append(f"{base_name} model (no files matching {pattern} found in models/)")
        else:
            missing_models.append("models/ directory not found")
        
        return len(missing_models) == 0, missing_models

    def check_backend_configuration(self) -> Tuple[bool, List[str]]:
        """
        Verify that runtime configuration and models are present.
        
        Returns:
            Tuple[bool, List[str]]: (success, list of missing runtime components)
        """
        missing_configs = []
        
        # Check for local embedding model path as per HANDOFF_CLI.md
        embedding_path = self.project_root / "models" / "embedding" / "all-MiniLM-L6-v2"
        if not embedding_path.exists():
            missing_configs.append("Local embedding model (models/embedding/all-MiniLM-L6-v2)")
        
        # Check for models configuration file
        models_config = self.project_root / "models" / "config.json"
        if not models_config.exists():
            missing_configs.append("Models configuration (models/config.json)")
        
        # Check for at least one agent configuration (optional but recommended)
        config_dir = self.project_root / "config"
        if config_dir.exists():
            agent_configs = list(config_dir.glob("*agent*.yaml")) + list(config_dir.glob("*agent*.yml"))
            if not agent_configs:
                missing_configs.append("Agent configuration files (config/*agent*.yaml)")
        
        return len(missing_configs) == 0, missing_configs

    def run_preflight_checks(self, verbose: bool = False) -> bool:
        """
        Execute all pre-flight dependency checks in sequence.
        
        Args:
            verbose: If True, display detailed progress information
            
        Returns:
            bool: True if all checks pass
            
        Raises:
            DependencyError: If any critical dependency is missing
        """
        if verbose:
            self.console.print("\n🔍 Running pre-flight dependency checks...\n")
        
        all_errors = []
        
        # Execute all health checks
        checks = [
            ("Core Python Packages", self.check_core_packages),
            ("LLaMA.cpp Backend", self.check_llama_cpp_backend),
            ("Custom Components", self.check_custom_components),  
            ("Machine Learning Models", self.check_ml_models),
            ("Runtime Configuration", self.check_backend_configuration),
        ]
        
        if verbose:
            # Show progress with rich progress bar
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=self.console,
                transient=True
            ) as progress:
                for check_name, check_func in checks:
                    task = progress.add_task(f"Checking {check_name.lower()}...", total=None)
                    success, errors = check_func()
                    
                    if success:
                        progress.update(task, description=f"✅ {check_name}")
                    else:
                        progress.update(task, description=f"❌ {check_name}")
                        all_errors.extend([(check_name, error) for error in errors])
        else:
            # Run checks silently for normal CLI operation
            for check_name, check_func in checks:
                success, errors = check_func()
                if not success:
                    all_errors.extend([(check_name, error) for error in errors])
        
        # If any errors found, raise comprehensive exception
        if all_errors:
            self._handle_dependency_errors(all_errors)
            return False
        
        if verbose:
            self.console.print(Panel.fit(
                "✅ All pre-flight checks passed successfully!",
                title="Dependency Validation",
                border_style="green"
            ))
        
        return True

    def _handle_dependency_errors(self, errors: List[Tuple[str, str]]) -> None:
        """
        Handle and display dependency errors with actionable guidance.
        
        Args:
            errors: List of (category, error_message) tuples
        """
        # Group errors by category
        error_groups = {}
        for category, error in errors:
            if category not in error_groups:
                error_groups[category] = []
            error_groups[category].append(error)
        
        # Build comprehensive error message
        error_table = Table(title="🚨 Dependency Validation Failed")
        error_table.add_column("Category", style="red", no_wrap=True)
        error_table.add_column("Missing Dependencies", style="white")
        error_table.add_column("Suggested Fix", style="cyan")
        
        suggestions = []
        
        for category, category_errors in error_groups.items():
            error_list = "\n".join(f"• {error}" for error in category_errors)
            
            # Generate category-specific suggestions
            if category == "Core Python Packages":
                suggestion = "Install via pipx and download models"
                suggestions.append("Install globally: python3 setup_cli.py")
                
            elif category == "LLaMA.cpp Backend":
                suggestion = "Reinstall with correct backend"
                suggestions.append("Reinstall with backend: python3 setup_cli.py")
                
            elif category == "Custom Components":
                suggestion = "Install via pipx and download models"
                suggestions.append("Install globally: python3 setup_cli.py")
                
            elif category == "Machine Learning Models":
                suggestion = "Run setup_cli.py --with-models"
                suggestions.append("Download models: python3 setup_cli.py --with-models")
                
            elif category == "Runtime Configuration":
                suggestion = "Run setup_cli.py --with-models"
                suggestions.append("Setup runtime components: python3 setup_cli.py --with-models")
                
            else:
                suggestion = "Run python3 setup_cli.py"
            
            error_table.add_row(category, error_list, suggestion)
        
        self.console.print(error_table)
        
        # Display actionable guidance
        if suggestions:
            self.console.print(Panel(
                "\n".join(f"• {suggestion}" for suggestion in suggestions),
                title="🔧 Recommended Actions",
                border_style="yellow"
            ))
        
        # Raise exception with detailed message
        error_summary = f"Found {len(errors)} missing dependencies across {len(error_groups)} categories."
        raise DependencyError(
            error_summary,
            "multiple_components", 
            suggestions
        )


def run_preflight_checks(verbose: bool = False) -> bool:
    """
    Convenience function to run all pre-flight checks.
    
    Args:
        verbose: If True, display detailed progress information
        
    Returns:
        bool: True if all checks pass
        
    Raises:
        DependencyError: If any critical dependency is missing
    """
    checker = HealthChecker()
    return checker.run_preflight_checks(verbose=verbose)