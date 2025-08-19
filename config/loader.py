"""
Configuration Loader - Environment variable resolution and defaults.
"""

import os
from typing import Dict, Any


def get_classifier_config() -> Dict[str, Any]:
    """
    Get classifier service configuration with environment variable resolution.
    
    Returns:
        Dictionary with classifier host, port, and timeout settings
    """
    return {
        "host": os.environ.get("SERVICEHOST_CLASSIFIER", "127.0.0.1"),
        "port": int(os.environ.get("SERVICEPORT_CLASSIFIER", "8001")),
        "timeout": {
            "connect": 0.5,
            "read": 0.8,
            "retries": 2
        },
        "model": {
            "name": "gemma-3n-E4B-it-Q5_K_S",
            "type": "gemma"
        }
    }


def get_backend_config() -> Dict[str, Any]:
    """
    Get backend service configuration with environment variable resolution.
    
    Returns:
        Dictionary with backend host, port, and model settings
    """
    return {
        "host": os.environ.get("SERVICEHOST", "127.0.0.1"),
        "port": int(os.environ.get("SERVICEPORT", "8000")),
        "model": {
            "name": "SmolLM3-3B-Q4_K_M",
            "type": "smollm"
        }
    }


def get_string_home_config() -> Dict[str, str]:
    """
    Get STRING_HOME path configuration with cross-platform support.
    
    Returns:
        Dictionary with paths to key STRING_HOME directories
    """
    from pathlib import Path
    
    # Resolve STRING_HOME
    if "STRING_HOME" in os.environ:
        string_home = Path(os.environ["STRING_HOME"]).expanduser().resolve()
    elif os.name == "nt":
        base = Path(os.environ.get("USERPROFILE", str(Path.home())))
        string_home = (base / ".string").resolve()
    else:
        string_home = (Path.home() / ".string").resolve()
    
    return {
        "base": str(string_home),
        "models": str(string_home / "models"),
        "storage": str(string_home / "storage"),
        "config": str(string_home / "config"),
        "logs": str(string_home / "storage" / "logs"),
        "pids": str(string_home / "storage" / ".pids"),
    }


def get_full_config() -> Dict[str, Any]:
    """
    Get complete configuration including all services and paths.
    
    Returns:
        Dictionary with classifier, backend, and path configurations
    """
    return {
        "classifier": get_classifier_config(),
        "backend": get_backend_config(), 
        "paths": get_string_home_config()
    }


def set_default_env_vars():
    """Set default environment variables if not already set."""
    defaults = {
        "SERVICEHOST_CLASSIFIER": "127.0.0.1",
        "SERVICEPORT_CLASSIFIER": "8001",
        "SERVICEHOST": "127.0.0.1",
        "SERVICEPORT": "8000"
    }
    
    for key, value in defaults.items():
        if key not in os.environ:
            os.environ[key] = value