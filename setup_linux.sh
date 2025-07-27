#!/bin/bash
set -e

# AI Coding Assistant - Linux Setup Script
# This script installs all dependencies required for the local AI coding assistant

echo "🚀 AI Coding Assistant - Linux Setup"
echo "====================================="

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check minimum version requirement
check_version() {
    local current_version="$1"
    local required_version="$2"
    
    if [ "$(printf '%s\n' "$required_version" "$current_version" | sort -V | head -n1)" = "$required_version" ]; then
        return 0
    else
        return 1
    fi
}

# Detect Linux distribution
if [ -f /etc/os-release ]; then
    . /etc/os-release
    DISTRO=$ID
    VERSION=$VERSION_ID
    print_status "Detected Linux distribution: $PRETTY_NAME"
else
    print_error "Cannot detect Linux distribution"
    exit 1
fi

# Detect architecture
ARCH=$(uname -m)
print_status "Detected architecture: $ARCH"

case $ARCH in
    x86_64)
        print_status "Running on x86_64 architecture"
        ;;
    aarch64|arm64)
        print_status "Running on ARM64 architecture"
        ;;
    *)
        print_warning "Unsupported architecture: $ARCH"
        ;;
esac

# Function to install packages based on distribution
install_packages() {
    local packages="$@"
    
    case $DISTRO in
        ubuntu|debian)
            print_status "Updating package lists..."
            sudo apt update
            print_status "Installing packages: $packages"
            sudo apt install -y $packages
            ;;
        fedora|centos|rhel)
            if command_exists dnf; then
                print_status "Installing packages: $packages"
                sudo dnf install -y $packages
            else
                print_status "Installing packages: $packages"
                sudo yum install -y $packages
            fi
            ;;
        arch|manjaro)
            print_status "Installing packages: $packages"
            sudo pacman -S --noconfirm $packages
            ;;
        opensuse*)
            print_status "Installing packages: $packages"
            sudo zypper install -y $packages
            ;;
        *)
            print_error "Unsupported Linux distribution: $DISTRO"
            print_error "Please install the following packages manually: $packages"
            exit 1
            ;;
    esac
}

# Install system dependencies
print_status "Installing system dependencies..."

case $DISTRO in
    ubuntu|debian)
        SYSTEM_PACKAGES="build-essential cmake git curl wget python3 python3-pip python3-venv python3-dev pkg-config libssl-dev"
        # Add GPU support packages if available
        if lspci | grep -i nvidia > /dev/null; then
            print_status "NVIDIA GPU detected, adding CUDA support packages"
            SYSTEM_PACKAGES="$SYSTEM_PACKAGES nvidia-cuda-toolkit"
        fi
        ;;
    fedora|centos|rhel)
        SYSTEM_PACKAGES="gcc gcc-c++ cmake git curl wget python3 python3-pip python3-devel openssl-devel pkg-config"
        # Add development tools group
        if command_exists dnf; then
            sudo dnf groupinstall -y "Development Tools"
        else
            sudo yum groupinstall -y "Development Tools"
        fi
        ;;
    arch|manjaro)
        SYSTEM_PACKAGES="base-devel cmake git curl wget python python-pip pkg-config openssl"
        ;;
    opensuse*)
        SYSTEM_PACKAGES="gcc gcc-c++ cmake git curl wget python3 python3-pip python3-devel libopenssl-devel pkg-config"
        ;;
esac

install_packages $SYSTEM_PACKAGES

# Check for Python 3.11+
print_status "Checking for Python 3.11+..."
PYTHON_CMD=""

# Check various Python commands
for cmd in python3.11 python3.12 python3.13 python3 python; do
    if command_exists $cmd; then
        PYTHON_VERSION=$($cmd --version 2>&1 | grep -oE '[0-9]+\.[0-9]+\.[0-9]+')
        if check_version "$PYTHON_VERSION" "3.11.0"; then
            PYTHON_CMD=$cmd
            print_success "Found Python $PYTHON_VERSION at $(which $cmd)"
            break
        fi
    fi
done

if [ -z "$PYTHON_CMD" ]; then
    print_warning "Python 3.11+ not found. Attempting to install..."
    
    case $DISTRO in
        ubuntu|debian)
            # Add deadsnakes PPA for newer Python versions
            if ! grep -q "deadsnakes" /etc/apt/sources.list.d/* 2>/dev/null; then
                sudo apt install -y software-properties-common
                sudo add-apt-repository -y ppa:deadsnakes/ppa
                sudo apt update
            fi
            sudo apt install -y python3.11 python3.11-dev python3.11-venv
            PYTHON_CMD="python3.11"
            ;;
        fedora)
            # Fedora usually has recent Python versions
            sudo dnf install -y python3.11 python3.11-devel
            PYTHON_CMD="python3.11"
            ;;
        arch|manjaro)
            # Arch usually has the latest Python
            sudo pacman -S --noconfirm python
            PYTHON_CMD="python"
            ;;
        *)
            print_error "Cannot automatically install Python 3.11+ on $DISTRO"
            print_error "Please install Python 3.11+ manually"
            exit 1
            ;;
    esac
    
    if [ -n "$PYTHON_CMD" ] && command_exists "$PYTHON_CMD"; then
        print_success "Python 3.11+ installed successfully"
    else
        print_error "Failed to install Python 3.11+"
        exit 1
    fi
fi

# Verify Python installation
PYTHON_VERSION=$($PYTHON_CMD --version 2>&1 | grep -oE '[0-9]+\.[0-9]+\.[0-9]+')
print_status "Using Python $PYTHON_VERSION at $(which $PYTHON_CMD)"

# Check for Poetry
print_status "Checking for Poetry..."
if ! command_exists poetry; then
    print_warning "Poetry not found. Installing Poetry..."
    curl -sSL https://install.python-poetry.org | $PYTHON_CMD -
    
    # Add Poetry to PATH
    export PATH="$HOME/.local/bin:$PATH"
    
    # Add to shell profile
    if [ -f "$HOME/.bashrc" ]; then
        echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
    fi
    if [ -f "$HOME/.zshrc" ]; then
        echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc
    fi
    
    # Verify Poetry installation
    if command_exists poetry; then
        print_success "Poetry installed successfully"
    else
        print_error "Poetry installation failed"
        exit 1
    fi
else
    print_success "Poetry already installed"
fi

# Install additional build dependencies for llama.cpp
print_status "Installing build dependencies for llama.cpp..."

case $DISTRO in
    ubuntu|debian)
        # Install additional packages for llama.cpp
        sudo apt install -y libopenblas-dev liblapack-dev
        
        # Check for GPU support
        if lspci | grep -i nvidia > /dev/null; then
            print_status "NVIDIA GPU detected"
            if ! command_exists nvcc; then
                print_warning "NVIDIA CUDA toolkit not found. Installing..."
                sudo apt install -y nvidia-cuda-toolkit
            fi
        fi
        ;;
    fedora|centos|rhel)
        # Install BLAS libraries
        if command_exists dnf; then
            sudo dnf install -y openblas-devel lapack-devel
        else
            sudo yum install -y openblas-devel lapack-devel
        fi
        ;;
    arch|manjaro)
        sudo pacman -S --noconfirm openblas lapack
        ;;
esac

print_success "Build dependencies installed"

# Install Ollama for web research models
print_status "Checking for Ollama..."
if ! command_exists ollama; then
    print_warning "Ollama not found. Installing Ollama..."
    curl -fsSL https://ollama.ai/install.sh | sh
    print_success "Ollama installed successfully"
else
    print_success "Ollama already installed"
fi

# Start Ollama service
print_status "Starting Ollama service..."
if ! pgrep -x "ollama" > /dev/null; then
    nohup ollama serve > /dev/null 2>&1 &
    sleep 3
    print_success "Ollama service started"
else
    print_success "Ollama service already running"
fi

# Install required Ollama models for web research
print_status "Installing Ollama models for web research..."
OLLAMA_MODELS=("llama3.2:3b")

for model in "${OLLAMA_MODELS[@]}"; do
    print_status "Checking for model: $model"
    if ! ollama list | grep -q "$model"; then
        print_status "Pulling model: $model"
        ollama pull "$model"
        print_success "Model $model installed"
    else
        print_success "Model $model already installed"
    fi
done

# Install project dependencies with Poetry
print_status "Installing project dependencies with Poetry..."

# Configure Poetry to use the correct Python version
poetry env use $PYTHON_CMD

# Install dependencies
poetry install --with dev

print_success "Project dependencies installed"

# Download and setup GGUF models
print_status "Setting up GGUF models..."

# Create models directory
mkdir -p models/{gemma,qwen,websailor}
mkdir -p smollm-quantized

# Function to download file with progress
download_with_progress() {
    local url="$1"
    local output="$2"
    local description="$3"
    
    if [ ! -f "$output" ]; then
        print_status "Downloading $description..."
        if command_exists curl; then
            curl -L --progress-bar -o "$output" "$url"
        elif command_exists wget; then
            wget --progress=bar --show-progress -O "$output" "$url"
        else
            print_error "Neither curl nor wget found. Please install one of them."
            return 1
        fi
        print_success "$description downloaded"
    else
        print_success "$description already exists"
    fi
}

# SmolLM3-3B (Primary model)
SMOLLM_URL="https://huggingface.co/HuggingFaceTB/SmolLM2-1.7B-Instruct-GGUF/resolve/main/smollm2-1.7b-instruct-q4_k_m.gguf"
download_with_progress "$SMOLLM_URL" "smollm-quantized/smollm-q4_K_M.gguf" "SmolLM3-3B GGUF model"

# Gemma 3n-E4B-it (Code generator)
GEMMA_URL="https://huggingface.co/bartowski/gemma-2-2b-it-GGUF/resolve/main/gemma-2-2b-it-Q4_K_M.gguf"
download_with_progress "$GEMMA_URL" "models/gemma/gemma-3n-e4b-it_q4_k_m.gguf" "Gemma 3n-E4B-it GGUF model"

# Qwen3-1.7B (Quality analyzer)
QWEN_URL="https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF/resolve/main/qwen2.5-1.5b-instruct-q4_k_m.gguf"
download_with_progress "$QWEN_URL" "models/qwen/qwen3-1.7b-q4_k_m.gguf" "Qwen3-1.7B GGUF model"

# WebSailor (Web research)
WEBSAILOR_URL="https://huggingface.co/fblgit/Llama-3.2-1B-Instruct-GGUF/resolve/main/llama-3.2-1b-instruct-q4_k_m.gguf"
download_with_progress "$WEBSAILOR_URL" "models/websailor/WebSailor-3B.Q4_K_M.gguf" "WebSailor GGUF model"

# Create .memignore file if it doesn't exist
if [ ! -f ".memignore" ]; then
    print_status "Creating .memignore file..."
    cat > .memignore << 'EOF'
# Dependencies
node_modules/
venv/
__pycache__/
*.egg-info/

# Build artifacts
build/
dist/
*.so
*.dylib
*.dll

# Logs and temporary files
*.log
logs/
tmp/
temp/

# IDE files
.vscode/
.idea/
*.swp
*.swo

# OS files
.DS_Store
Thumbs.db

# Model files (large)
*.gguf
*.bin
*.safetensors
models/

# Vector databases
qdrant_storage/
memory_cubes/

# Test artifacts
.pytest_cache/
.coverage
htmlcov/

# Virtual environments
venv*/
.env

# Git
.git/
.gitignore
EOF
    print_success ".memignore file created"
else
    print_success ".memignore file already exists"
fi

# Set up environment variables
print_status "Setting up environment variables..."

ENV_FILE=".env.local"
if [ ! -f "$ENV_FILE" ]; then
    # Detect GPU support
    GPU_LAYERS="-1"
    if lspci | grep -i nvidia > /dev/null && command_exists nvcc; then
        print_status "NVIDIA CUDA support detected - GPU acceleration enabled"
        GPU_LAYERS="-1"
    elif lspci | grep -i amd > /dev/null; then
        print_status "AMD GPU detected - using CPU inference"
        GPU_LAYERS="0"
    else
        print_status "No GPU acceleration detected - using CPU inference"
        GPU_LAYERS="0"
    fi
    
    cat > "$ENV_FILE" << EOF
# AI Coding Assistant Environment Configuration

# Workspace settings
WORKSPACE_ROOT=$(pwd)/workspace
QDRANT_STORAGE=./qdrant_storage

# Ollama settings
OLLAMA_HOST=http://127.0.0.1:11434

# Model settings
GGUF_GPU_LAYERS=$GPU_LAYERS
GGUF_THREADS=0
GGUF_CONTEXT_LENGTH=16384

# Service settings
SERVICE_HOST=127.0.0.1
SERVICE_PORT=8000
LOG_LEVEL=INFO
EOF
    print_success "Environment file created: $ENV_FILE"
else
    print_success "Environment file already exists: $ENV_FILE"
fi

# Create workspace directory
mkdir -p workspace
print_success "Workspace directory created"

# Run environment validation
print_status "Running environment validation..."
if poetry run python validate_environment.py 2>/dev/null; then
    print_success "Environment validation passed"
else
    print_warning "Environment validation script not found or failed"
fi

# Create launch script
print_status "Creating launch script..."
cat > launch.sh << 'EOF'
#!/bin/bash
# AI Coding Assistant Launcher

# Load environment variables
if [ -f .env.local ]; then
    export $(cat .env.local | grep -v '^#' | xargs)
fi

# Start the backend
echo "🚀 Starting AI Coding Assistant Backend..."
poetry run python backend_controller.py start --host ${SERVICE_HOST:-127.0.0.1} --port ${SERVICE_PORT:-8000}
EOF

chmod +x launch.sh
print_success "Launch script created: ./launch.sh"

# Create systemd service file (optional)
print_status "Creating systemd service file..."
cat > ai-coding-assistant.service << EOF
[Unit]
Description=AI Coding Assistant Backend
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$(pwd)
EnvironmentFile=$(pwd)/.env.local
ExecStart=$(which poetry) run python backend_controller.py start --host 127.0.0.1 --port 8000 --foreground
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

print_success "Systemd service file created: ai-coding-assistant.service"
print_status "To install as system service:"
print_status "  sudo cp ai-coding-assistant.service /etc/systemd/system/"
print_status "  sudo systemctl enable ai-coding-assistant"
print_status "  sudo systemctl start ai-coding-assistant"

# Print setup summary
echo ""
echo "🎉 Setup Complete!"
echo "=================="
print_success "All dependencies installed successfully"
print_status "Distribution: $PRETTY_NAME"
print_status "Architecture: $ARCH"
print_status "Python: $(which $PYTHON_CMD) ($($PYTHON_CMD --version))"
print_status "Poetry: $(which poetry) ($(poetry --version))"
print_status "Ollama: $(which ollama)"

echo ""
echo "📋 Next Steps:"
echo "1. Start the backend: ./launch.sh"
echo "2. Or manually: poetry run python backend_controller.py start"
echo "3. Check status: poetry run python backend_controller.py status"
echo "4. View logs: poetry run python backend_controller.py logs"

echo ""
echo "🔗 API Endpoints:"
echo "- Health check: http://127.0.0.1:8000/health"
echo "- Chat: http://127.0.0.1:8000/chat"
echo "- Documentation: http://127.0.0.1:8000/docs"

echo ""
echo "📁 Important Files:"
echo "- Configuration: config.yaml"
echo "- Environment: .env.local"
echo "- Models: ./models/ and ./smollm-quantized/"
echo "- Backend controller: ./backend_controller.py"
echo "- Systemd service: ai-coding-assistant.service"

echo ""
echo "🖥️ System Service (Optional):"
echo "- Install: sudo cp ai-coding-assistant.service /etc/systemd/system/ && sudo systemctl enable ai-coding-assistant"
echo "- Start: sudo systemctl start ai-coding-assistant"
echo "- Status: sudo systemctl status ai-coding-assistant"

print_success "Linux setup completed successfully! 🎉"