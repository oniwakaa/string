# String CLI - Automated Setup Guide

This document describes the automated, cross-platform installation process for the String CLI that ensures global availability and optimal performance.

## 🚀 Quick Start

### Basic Installation
```bash
python3 setup_cli.py
```

### Installation with Models
```bash
python3 setup_cli.py --with-models
```

### Platform-Specific Optimizations

#### macOS Apple Silicon
```bash
# Automatically configures Metal backend
python3 setup_cli.py
```

#### Linux with CUDA
```bash
python3 setup_cli.py --enable-cuda
```

#### Linux with OpenBLAS
```bash
python3 setup_cli.py --enable-blas
```

## 🎯 What the Setup Does

### 1. Global CLI Installation via pipx
- Installs `pipx` if not available (cross-platform)
- Uses pipx to install `string-cli` globally in an isolated environment
- Automatically updates PATH for global access
- Avoids PEP 668 issues by using isolated app environments

### 2. OS-Specific Backend Optimization
- **macOS (arm64)**: Builds llama-cpp-python with Metal backend
- **macOS (x64)**: Uses default CPU backend
- **Linux**: Supports CUDA, OpenBLAS, or default CPU backend
- **Windows**: Supports CUDA or default CPU backend

### 3. PATH Management
- Runs `pipx ensurepath --force` to update shell profiles
- Updates current session PATH to avoid manual terminal restart
- Works across bash, zsh, PowerShell, and Command Prompt

### 4. Model Downloads (Optional)
- Installs Hugging Face CLI in the pipx environment
- Supports authenticated downloads for gated models
- Downloads models based on `models/config.json` manifest
- Uses hardcoded repository mappings for reliability

## 🔧 Technical Details

### pipx Installation Hierarchy
1. **macOS**: `brew install pipx` → `pip install --user pipx`
2. **Linux**: System package manager → `pip install --user pipx`
3. **Windows**: `pip install --user pipx`

### Build Environment Variables
- **Metal (macOS arm64)**: `CMAKE_ARGS="-DGGML_METAL=ON -DGGML_METAL_EMBED_LIBRARY=ON" FORCE_CMAKE=1`
- **CUDA**: `CMAKE_ARGS="-DGGML_CUDA=ON" FORCE_CMAKE=1`  
- **OpenBLAS**: `CMAKE_ARGS="-DGGML_BLAS=ON -DGGML_BLAS_VENDOR=OpenBLAS" FORCE_CMAKE=1`

### PATH Locations
- **Unix**: `~/.local/bin/string-cli`
- **Windows**: `%APPDATA%\Python\Scripts\string-cli.exe` or `%USERPROFILE%\.local\bin\string-cli`

## ✅ Verification Commands

After installation, test with:
```bash
which string-cli                    # Should show global path
string-cli --version                # Should show version info
string-cli --help                   # Should show help menu
string-cli validate                 # Should run dependency checks
```

## 🔄 Reinstallation/Updates

### Force Metal Backend Rebuild (macOS)
```bash
CMAKE_ARGS="-DGGML_METAL=ON -DGGML_METAL_EMBED_LIBRARY=ON" FORCE_CMAKE=1 pipx reinstall string-ai-coding-assistant
```

### Force CUDA Rebuild (Linux/Windows)  
```bash
CMAKE_ARGS="-DGGML_CUDA=ON" FORCE_CMAKE=1 pipx reinstall string-ai-coding-assistant
```

### Update to Latest Version
```bash
pipx upgrade string-ai-coding-assistant
```

## 🐛 Troubleshooting

### "string-cli command not found"
1. Check if pipx bin directory is on PATH: `echo $PATH | grep -o "\.local/bin"`
2. Manually add to current session: `export PATH="$HOME/.local/bin:$PATH"`
3. Restart terminal or source shell config: `source ~/.bashrc` / `source ~/.zshrc`

### PEP 668 "externally managed environment" Error
This is handled automatically by using pipx instead of system pip. If you see this error, the script will install pipx and continue.

### Metal Backend Not Working (macOS)
1. Verify Xcode Command Line Tools: `xcode-select -p`
2. Check Metal import: `python -c "import llama_cpp; print('Metal OK')"`
3. Force reinstall: `python3 setup_cli.py` (will detect and rebuild)

### Model Download Issues
1. Verify authentication: `huggingface-cli whoami`
2. Login with token: `huggingface-cli login`
3. Check model manifest: `cat models/config.json`

## 📁 File Structure

```
string-ai-coding-assistant/
├── setup_cli.py              # Main setup script
├── pyproject.toml            # Package configuration with console scripts
├── models/
│   └── config.json           # Model manifest for downloads
├── cli/
│   └── main.py               # CLI entry point
└── requirements.txt          # Python dependencies
```

## 🌐 Cross-Platform Compatibility

The setup script automatically detects:
- Operating System (macOS/Linux/Windows)
- Architecture (arm64/x86_64)
- Available package managers (brew/apt/dnf/yum/pacman)
- Python command variant (python3/python/py)
- Shell type for PATH updates

## 🚨 Requirements

- Python 3.11+
- Internet connection for downloads
- ~2GB disk space for models (if using `--with-models`)
- Xcode Command Line Tools (macOS Metal)
- CUDA Toolkit (Linux/Windows CUDA backend)

## 📞 Support

If the automated setup fails:
1. Check the error message for specific guidance
2. Try manual installation: `pipx install .`
3. Review troubleshooting section above
4. Report issues with full error output