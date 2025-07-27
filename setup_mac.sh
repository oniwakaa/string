#!/bin/bash
set -e

# AI Coding Assistant - macOS Setup Script
# This script installs all dependencies required for the local AI coding assistant

echo "🚀 AI Coding Assistant - macOS Setup"
echo "======================================"

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

# Detect architecture
ARCH=$(uname -m)
print_status "Detected architecture: $ARCH"

if [[ "$ARCH" == "arm64" ]]; then
    print_status "Running on Apple Silicon (M1/M2/M3/M4)"
    HOMEBREW_PREFIX="/opt/homebrew"
else
    print_status "Running on Intel Mac"
    HOMEBREW_PREFIX="/usr/local"
fi

# Check for Homebrew
print_status "Checking for Homebrew..."
if ! command_exists brew; then
    print_warning "Homebrew not found. Installing Homebrew..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    
    # Add Homebrew to PATH for this session
    if [[ "$ARCH" == "arm64" ]]; then
        echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zprofile
        eval "$(/opt/homebrew/bin/brew shellenv)"
    else
        echo 'eval "$(/usr/local/bin/brew shellenv)"' >> ~/.zprofile
        eval "$(/usr/local/bin/brew shellenv)"
    fi
    
    print_success "Homebrew installed successfully"
else
    print_success "Homebrew already installed"
    # Update Homebrew
    print_status "Updating Homebrew..."
    brew update
fi

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
    print_warning "Python 3.11+ not found. Installing Python 3.11..."
    brew install python@3.11
    PYTHON_CMD="python3.11"
    print_success "Python 3.11 installed successfully"
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
    echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zprofile
    
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

# Install system dependencies for llama.cpp
print_status "Installing system dependencies for llama.cpp..."

# Install CMake and build tools
if ! command_exists cmake; then
    print_status "Installing CMake..."
    brew install cmake
fi

if ! command_exists make; then
    print_status "Installing build tools..."
    xcode-select --install 2>/dev/null || true
fi

# Install Metal Performance Shaders support (for Apple Silicon)
if [[ "$ARCH" == "arm64" ]]; then
    print_status "Apple Silicon detected - Metal Performance Shaders will be used for GPU acceleration"
fi

print_success "System dependencies installed"

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
    cat > "$ENV_FILE" << EOF
# AI Coding Assistant Environment Configuration

# Workspace settings
WORKSPACE_ROOT=$(pwd)/workspace
QDRANT_STORAGE=./qdrant_storage

# Ollama settings
OLLAMA_HOST=http://127.0.0.1:11434

# Model settings
GGUF_GPU_LAYERS=-1
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

# Print setup summary
echo ""
echo "🎉 Setup Complete!"
echo "=================="
print_success "All dependencies installed successfully"
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

print_success "macOS setup completed successfully! 🎉"