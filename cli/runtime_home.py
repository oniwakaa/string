#!/usr/bin/env python3
"""
Runtime Home Management for String CLI

Manages the user-scoped runtime home directory independent of git checkout.
Creates and maintains the directory structure needed for global CLI operation.
"""

import os
import platform
from pathlib import Path
from typing import Optional
import json


def get_string_home() -> Path:
    """
    Get the STRING_HOME directory path.
    
    Returns:
        Path: User-scoped runtime home directory
    """
    # Check for environment override
    if "STRING_HOME" in os.environ:
        return Path(os.environ["STRING_HOME"]).resolve()
    
    # Platform-specific defaults
    system = platform.system().lower()
    if system == "windows":
        home_base = Path(os.environ.get("USERPROFILE", Path.home()))
        return home_base / ".string"
    else:
        # macOS and Linux
        return Path.home() / ".string"


def ensure_string_home() -> Path:
    """
    Ensure STRING_HOME exists with proper directory structure.
    
    Returns:
        Path: The STRING_HOME directory path
    """
    string_home = get_string_home()
    
    # Create main directory
    string_home.mkdir(exist_ok=True)
    
    # Create subdirectories
    subdirs = ["apps", "models", "config", "storage"]
    for subdir in subdirs:
        (string_home / subdir).mkdir(exist_ok=True)
    
    # Create .installed marker for idempotent checks
    marker_file = string_home / ".installed"
    if not marker_file.exists():
        marker_file.write_text(f"String CLI runtime home initialized\n")
    
    return string_home


def is_runtime_initialized() -> bool:
    """
    Check if runtime home is properly initialized.
    
    Returns:
        bool: True if runtime home exists and is initialized
    """
    string_home = get_string_home()
    marker_file = string_home / ".installed"
    return marker_file.exists()


def get_models_manifest_path() -> Path:
    """
    Get the path to the models manifest file.
    
    Returns:
        Path: Path to models.json in config directory
    """
    return get_string_home() / "config" / "models.json"


def get_default_models_manifest() -> dict:
    """
    Get default models manifest configuration.
    
    Returns:
        dict: Default models configuration
    """
    return {
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
            },
            {
                "name": "Qwen3-Embedding-0.6B",
                "repo_id": "Qwen/Qwen3-Embedding-0.6B-GGUF",
                "filename": "Qwen3-Embedding-0.6B-f16.gguf",
                "local_dir": "Qwen3-Embedding-0.6B",
                "allow_patterns": ["Qwen3-Embedding-0.6B-f16.gguf"]
            }
        ],
        "embedding": {
            "name": "all-MiniLM-L6-v2",
            "repo_id": "sentence-transformers/all-MiniLM-L6-v2", 
            "local_dir": "embedding/all-MiniLM-L6-v2"
        }
    }


def initialize_default_configs():
    """
    Initialize default configuration files in STRING_HOME if they don't exist.
    """
    string_home = get_string_home()
    config_dir = string_home / "config"
    
    # Create default models manifest
    models_manifest_path = config_dir / "models.json"
    if not models_manifest_path.exists():
        manifest = get_default_models_manifest()
        with open(models_manifest_path, 'w') as f:
            json.dump(manifest, f, indent=2)
    
    # Create default runtime preferences
    prefs_path = config_dir / "stringpref.md"
    if not prefs_path.exists():
        default_prefs = """# String CLI Runtime Preferences

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
        prefs_path.write_text(default_prefs)


def get_storage_paths() -> dict:
    """
    Get all runtime storage paths.
    
    Returns:
        dict: Dictionary of storage path mappings
    """
    string_home = get_string_home()
    storage_dir = string_home / "storage"
    
    return {
        "storage_dir": storage_dir,
        "qdrant_storage": storage_dir / "qdrant_storage", 
        "codebase_state": storage_dir / ".codebase_state.json",
        "models_dir": string_home / "models",
        "config_dir": string_home / "config"
    }