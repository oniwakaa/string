# AI Coding Assistant - Windows Setup Script
# This script installs all dependencies required for the local AI coding assistant

param(
    [switch]$NoGPU = $false,
    [switch]$SkipModels = $false,
    [switch]$Verbose = $false
)

# Enable verbose output if requested
if ($Verbose) {
    $VerbosePreference = "Continue"
}

Write-Host "🚀 AI Coding Assistant - Windows Setup" -ForegroundColor Cyan
Write-Host "=======================================" -ForegroundColor Cyan

# Function to print colored output
function Write-Status {
    param($Message)
    Write-Host "[INFO] $Message" -ForegroundColor Blue
}

function Write-Success {
    param($Message)
    Write-Host "[SUCCESS] $Message" -ForegroundColor Green
}

function Write-Warning {
    param($Message)
    Write-Host "[WARNING] $Message" -ForegroundColor Yellow
}

function Write-Error-Custom {
    param($Message)
    Write-Host "[ERROR] $Message" -ForegroundColor Red
}

# Function to check if command exists
function Test-CommandExists {
    param($Command)
    try {
        Get-Command $Command -ErrorAction Stop
        return $true
    }
    catch {
        return $false
    }
}

# Function to check version requirement
function Test-Version {
    param($CurrentVersion, $RequiredVersion)
    return [version]$CurrentVersion -ge [version]$RequiredVersion
}

# Check if running as Administrator
function Test-Administrator {
    $currentUser = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($currentUser)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

# Detect architecture
$Architecture = $env:PROCESSOR_ARCHITECTURE
Write-Status "Detected architecture: $Architecture"

if ($Architecture -eq "AMD64") {
    Write-Status "Running on x64 architecture"
} elseif ($Architecture -eq "ARM64") {
    Write-Status "Running on ARM64 architecture"
} else {
    Write-Warning "Unsupported architecture: $Architecture"
}

# Check for administrator privileges for some installations
$IsAdmin = Test-Administrator
if ($IsAdmin) {
    Write-Success "Running with administrator privileges"
} else {
    Write-Warning "Not running as administrator. Some installations may require elevation."
}

# Check for Chocolatey
Write-Status "Checking for Chocolatey package manager..."
if (-not (Test-CommandExists "choco")) {
    Write-Warning "Chocolatey not found. Installing Chocolatey..."
    
    # Check execution policy
    $ExecutionPolicy = Get-ExecutionPolicy
    if ($ExecutionPolicy -eq "Restricted") {
        Write-Status "Setting execution policy to allow Chocolatey installation..."
        Set-ExecutionPolicy Bypass -Scope Process -Force
    }
    
    # Install Chocolatey
    [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072
    Invoke-Expression ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))
    
    # Refresh environment variables
    $env:PATH = [System.Environment]::GetEnvironmentVariable("PATH","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("PATH","User")
    
    if (Test-CommandExists "choco") {
        Write-Success "Chocolatey installed successfully"
    } else {
        Write-Error-Custom "Chocolatey installation failed"
        exit 1
    }
} else {
    Write-Success "Chocolatey already installed"
    # Update Chocolatey
    Write-Status "Updating Chocolatey..."
    choco upgrade chocolatey -y
}

# Check for Python 3.11+
Write-Status "Checking for Python 3.11+..."
$PythonCommand = ""

# Check various Python commands
$PythonCommands = @("python3.11", "python3.12", "python3.13", "python3", "python", "py")

foreach ($cmd in $PythonCommands) {
    if (Test-CommandExists $cmd) {
        try {
            $version = & $cmd --version 2>&1
            if ($version -match "Python (\d+\.\d+\.\d+)") {
                $pythonVersion = $matches[1]
                if (Test-Version $pythonVersion "3.11.0") {
                    $PythonCommand = $cmd
                    Write-Success "Found Python $pythonVersion at $(Get-Command $cmd | Select-Object -ExpandProperty Source)"
                    break
                }
            }
        }
        catch {
            continue
        }
    }
}

if (-not $PythonCommand) {
    Write-Warning "Python 3.11+ not found. Installing Python 3.11..."
    choco install python311 -y
    
    # Refresh environment variables
    $env:PATH = [System.Environment]::GetEnvironmentVariable("PATH","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("PATH","User")
    
    $PythonCommand = "python"
    Write-Success "Python 3.11 installed successfully"
}

# Verify Python installation
try {
    $pythonVersionOutput = & $PythonCommand --version 2>&1
    if ($pythonVersionOutput -match "Python (\d+\.\d+\.\d+)") {
        $pythonVersion = $matches[1]
        Write-Status "Using Python $pythonVersion at $(Get-Command $PythonCommand | Select-Object -ExpandProperty Source)"
    }
} catch {
    Write-Error-Custom "Failed to verify Python installation"
    exit 1
}

# Check for Git
Write-Status "Checking for Git..."
if (-not (Test-CommandExists "git")) {
    Write-Warning "Git not found. Installing Git..."
    choco install git -y
    
    # Refresh environment variables
    $env:PATH = [System.Environment]::GetEnvironmentVariable("PATH","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("PATH","User")
    
    Write-Success "Git installed successfully"
} else {
    Write-Success "Git already installed"
}

# Check for Poetry
Write-Status "Checking for Poetry..."
if (-not (Test-CommandExists "poetry")) {
    Write-Warning "Poetry not found. Installing Poetry..."
    
    # Install Poetry using the official installer
    (Invoke-WebRequest -Uri https://install.python-poetry.org -UseBasicParsing).Content | & $PythonCommand -
    
    # Add Poetry to PATH for this session
    $PoetryPath = "$env:APPDATA\Python\Scripts"
    $env:PATH += ";$PoetryPath"
    
    # Verify Poetry installation
    if (Test-CommandExists "poetry") {
        Write-Success "Poetry installed successfully"
    } else {
        Write-Error-Custom "Poetry installation failed. Please check your PATH and try again."
        exit 1
    }
} else {
    Write-Success "Poetry already installed"
}

# Install Visual Studio Build Tools (for llama-cpp-python compilation)
Write-Status "Checking for Visual Studio Build Tools..."
$VSWhere = "${env:ProgramFiles(x86)}\Microsoft Visual Studio\Installer\vswhere.exe"

if (Test-Path $VSWhere) {
    $VSInstallations = & "$VSWhere" -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -format json | ConvertFrom-Json
    if ($VSInstallations.Count -gt 0) {
        Write-Success "Visual Studio Build Tools already installed"
    } else {
        Write-Warning "Visual Studio Build Tools with C++ support not found"
        Write-Status "Installing Visual Studio Build Tools..."
        choco install visualstudio2022buildtools --package-parameters "--add Microsoft.VisualStudio.Workload.VCTools" -y
    }
} else {
    Write-Warning "Visual Studio Build Tools not found. Installing..."
    choco install visualstudio2022buildtools --package-parameters "--add Microsoft.VisualStudio.Workload.VCTools" -y
}

# Install CMake
Write-Status "Checking for CMake..."
if (-not (Test-CommandExists "cmake")) {
    Write-Warning "CMake not found. Installing CMake..."
    choco install cmake -y
    
    # Refresh environment variables
    $env:PATH = [System.Environment]::GetEnvironmentVariable("PATH","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("PATH","User")
    
    Write-Success "CMake installed successfully"
} else {
    Write-Success "CMake already installed"
}

# Install Ollama for web research models
Write-Status "Checking for Ollama..."
if (-not (Test-CommandExists "ollama")) {
    Write-Warning "Ollama not found. Installing Ollama..."
    
    # Download and install Ollama
    $OllamaInstaller = "$env:TEMP\OllamaSetup.exe"
    Invoke-WebRequest -Uri "https://ollama.ai/download/windows" -OutFile $OllamaInstaller
    Start-Process -FilePath $OllamaInstaller -ArgumentList "/S" -Wait
    
    # Add Ollama to PATH
    $OllamaPath = "$env:LOCALAPPDATA\Programs\Ollama"
    $env:PATH += ";$OllamaPath"
    
    Write-Success "Ollama installed successfully"
} else {
    Write-Success "Ollama already installed"
}

# Start Ollama service
Write-Status "Starting Ollama service..."
try {
    $OllamaProcess = Get-Process -Name "ollama" -ErrorAction SilentlyContinue
    if (-not $OllamaProcess) {
        Start-Process -FilePath "ollama" -ArgumentList "serve" -WindowStyle Hidden
        Start-Sleep -Seconds 3
        Write-Success "Ollama service started"
    } else {
        Write-Success "Ollama service already running"
    }
} catch {
    Write-Warning "Could not start Ollama service. You may need to start it manually."
}

# Install required Ollama models for web research
Write-Status "Installing Ollama models for web research..."
$OllamaModels = @("llama3.2:3b")

foreach ($model in $OllamaModels) {
    Write-Status "Checking for model: $model"
    $modelList = & ollama list 2>&1
    if ($modelList -match $model) {
        Write-Success "Model $model already installed"
    } else {
        Write-Status "Pulling model: $model"
        & ollama pull $model
        Write-Success "Model $model installed"
    }
}

# Install project dependencies with Poetry
Write-Status "Installing project dependencies with Poetry..."

# Configure Poetry to use the correct Python version
& poetry env use $PythonCommand

# Install dependencies
& poetry install --with dev

Write-Success "Project dependencies installed"

# Download and setup GGUF models (if not skipped)
if (-not $SkipModels) {
    Write-Status "Setting up GGUF models..."

    # Create models directory
    New-Item -ItemType Directory -Force -Path "models\gemma", "models\qwen", "models\websailor" | Out-Null
    New-Item -ItemType Directory -Force -Path "smollm-quantized" | Out-Null

    # Function to download file with progress
    function Get-FileWithProgress {
        param($Url, $Output, $Description)
        
        if (-not (Test-Path $Output)) {
            Write-Status "Downloading $Description..."
            try {
                $webClient = New-Object System.Net.WebClient
                $webClient.DownloadFile($Url, $Output)
                Write-Success "$Description downloaded"
            } catch {
                Write-Error-Custom "Failed to download $Description: $($_.Exception.Message)"
                return $false
            }
        } else {
            Write-Success "$Description already exists"
        }
        return $true
    }

    # SmolLM3-3B (Primary model)
    $SmolLMUrl = "https://huggingface.co/HuggingFaceTB/SmolLM2-1.7B-Instruct-GGUF/resolve/main/smollm2-1.7b-instruct-q4_k_m.gguf"
    Get-FileWithProgress $SmolLMUrl "smollm-quantized\smollm-q4_K_M.gguf" "SmolLM3-3B GGUF model"

    # Gemma 3n-E4B-it (Code generator)
    $GemmaUrl = "https://huggingface.co/bartowski/gemma-2-2b-it-GGUF/resolve/main/gemma-2-2b-it-Q4_K_M.gguf"
    Get-FileWithProgress $GemmaUrl "models\gemma\gemma-3n-e4b-it_q4_k_m.gguf" "Gemma 3n-E4B-it GGUF model"

    # Qwen3-1.7B (Quality analyzer)
    $QwenUrl = "https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF/resolve/main/qwen2.5-1.5b-instruct-q4_k_m.gguf"
    Get-FileWithProgress $QwenUrl "models\qwen\qwen3-1.7b-q4_k_m.gguf" "Qwen3-1.7B GGUF model"

    # WebSailor (Web research)
    $WebSailorUrl = "https://huggingface.co/fblgit/Llama-3.2-1B-Instruct-GGUF/resolve/main/llama-3.2-1b-instruct-q4_k_m.gguf"
    Get-FileWithProgress $WebSailorUrl "models\websailor\WebSailor-3B.Q4_K_M.gguf" "WebSailor GGUF model"
}

# Create .memignore file if it doesn't exist
if (-not (Test-Path ".memignore")) {
    Write-Status "Creating .memignore file..."
    $MemignoreContent = @"
# Dependencies
node_modules/
venv/
__pycache__/
*.egg-info/

# Build artifacts
build/
dist/
*.so
*.dll
*.pyd

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
"@
    $MemignoreContent | Out-File -FilePath ".memignore" -Encoding UTF8
    Write-Success ".memignore file created"
} else {
    Write-Success ".memignore file already exists"
}

# Set up environment variables
Write-Status "Setting up environment variables..."

$EnvFile = ".env.local"
if (-not (Test-Path $EnvFile)) {
    $EnvContent = @"
# AI Coding Assistant Environment Configuration

# Workspace settings
WORKSPACE_ROOT=$(Get-Location)\workspace
QDRANT_STORAGE=.\qdrant_storage

# Ollama settings
OLLAMA_HOST=http://127.0.0.1:11434

# Model settings
GGUF_GPU_LAYERS=$($NoGPU ? "0" : "-1")
GGUF_THREADS=0
GGUF_CONTEXT_LENGTH=16384

# Service settings
SERVICE_HOST=127.0.0.1
SERVICE_PORT=8000
LOG_LEVEL=INFO
"@
    $EnvContent | Out-File -FilePath $EnvFile -Encoding UTF8
    Write-Success "Environment file created: $EnvFile"
} else {
    Write-Success "Environment file already exists: $EnvFile"
}

# Create workspace directory
New-Item -ItemType Directory -Force -Path "workspace" | Out-Null
Write-Success "Workspace directory created"

# Run environment validation
Write-Status "Running environment validation..."
try {
    & poetry run python validate_environment.py 2>$null
    Write-Success "Environment validation passed"
} catch {
    Write-Warning "Environment validation script not found or failed"
}

# Create launch script
Write-Status "Creating launch script..."
$LaunchScript = @'
@echo off
rem AI Coding Assistant Launcher

rem Load environment variables from .env.local
if exist .env.local (
    for /f "tokens=1,2 delims==" %%a in (.env.local) do (
        if not "%%a"=="" if not "%%a:~0,1%"=="#" set %%a=%%b
    )
)

rem Start the backend
echo 🚀 Starting AI Coding Assistant Backend...
poetry run python backend_controller.py start --host %SERVICE_HOST% --port %SERVICE_PORT%

pause
'@
$LaunchScript | Out-File -FilePath "launch.bat" -Encoding ASCII
Write-Success "Launch script created: .\launch.bat"

# Create PowerShell launch script
$PSLaunchScript = @'
# AI Coding Assistant PowerShell Launcher

# Load environment variables from .env.local
if (Test-Path .env.local) {
    Get-Content .env.local | ForEach-Object {
        if ($_ -match "^([^#][^=]+)=(.*)$") {
            [Environment]::SetEnvironmentVariable($matches[1], $matches[2], "Process")
        }
    }
}

# Start the backend
Write-Host "🚀 Starting AI Coding Assistant Backend..." -ForegroundColor Cyan
& poetry run python backend_controller.py start --host $env:SERVICE_HOST --port $env:SERVICE_PORT

Read-Host "Press Enter to continue..."
'@
$PSLaunchScript | Out-File -FilePath "launch.ps1" -Encoding UTF8
Write-Success "PowerShell launch script created: .\launch.ps1"

# Print setup summary
Write-Host ""
Write-Host "🎉 Setup Complete!" -ForegroundColor Green
Write-Host "==================" -ForegroundColor Green
Write-Success "All dependencies installed successfully"
Write-Status "Python: $(Get-Command $PythonCommand | Select-Object -ExpandProperty Source)"
Write-Status "Poetry: $(Get-Command poetry | Select-Object -ExpandProperty Source)"
if (Test-CommandExists "ollama") {
    Write-Status "Ollama: $(Get-Command ollama | Select-Object -ExpandProperty Source)"
}

Write-Host ""
Write-Host "📋 Next Steps:" -ForegroundColor Yellow
Write-Host "1. Start the backend: .\launch.bat (or .\launch.ps1)"
Write-Host "2. Or manually: poetry run python backend_controller.py start"
Write-Host "3. Check status: poetry run python backend_controller.py status"
Write-Host "4. View logs: poetry run python backend_controller.py logs"

Write-Host ""
Write-Host "🔗 API Endpoints:" -ForegroundColor Yellow
Write-Host "- Health check: http://127.0.0.1:8000/health"
Write-Host "- Chat: http://127.0.0.1:8000/chat"
Write-Host "- Documentation: http://127.0.0.1:8000/docs"

Write-Host ""
Write-Host "📁 Important Files:" -ForegroundColor Yellow
Write-Host "- Configuration: config.yaml"
Write-Host "- Environment: .env.local"
Write-Host "- Models: .\models\ and .\smollm-quantized\"
Write-Host "- Backend controller: .\backend_controller.py"

Write-Success "Windows setup completed successfully! 🎉"