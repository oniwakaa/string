#!/usr/bin/env python3
"""
Environment validation script for MemOS quantization testing
"""
import sys
import torch
import transformers
import psutil
import os
from pathlib import Path

def check_environment():
    """Check environment setup for quantization validation."""
    print("=== Environment Check ===")
    
    # Basic packages
    print(f"Python: {sys.version}")
    print(f"PyTorch: {torch.__version__}")
    print(f"Transformers: {transformers.__version__}")
    
    # Device availability
    print(f"CUDA available: {torch.cuda.is_available()}")
    if hasattr(torch.backends, 'mps'):
        print(f"MPS available: {torch.backends.mps.is_available()}")
    
    # BitsAndBytes check
    try:
        import bitsandbytes as bnb
        print(f"BitsAndBytes: {bnb.__version__}")
    except ImportError:
        print("BitsAndBytes: NOT INSTALLED")
        print("Installing bitsandbytes...")
        os.system("pip install bitsandbytes")
    
    # Memory check
    memory = psutil.virtual_memory()
    print(f"Total RAM: {memory.total / (1024**3):.1f} GB")
    print(f"Available RAM: {memory.available / (1024**3):.1f} GB")
    
    # Model files check
    model_path = Path("./smollm")
    print(f"Model directory exists: {model_path.exists()}")
    if model_path.exists():
        total_size = sum(f.stat().st_size for f in model_path.rglob('*') if f.is_file())
        print(f"Model size: {total_size / (1024**3):.1f} GB")
    
    print("=== Environment Check Complete ===")

if __name__ == "__main__":
    check_environment() 