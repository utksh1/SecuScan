#!/bin/bash

# ==============================================================================
# SecuScan Setup Script
# ==============================================================================
# This script prepares the development environment for SecuScan by:
# 1. Checking for system prerequisites
# 2. Creating a Python virtual environment and installing backend dependencies
# 3. Installing frontend dependencies via npm
# 4. Creating required data and log directories
# 5. Setting up initial configuration files
# ==============================================================================

set -e # Exit on error

# --- Visual Helpers ---
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color
BOLD='\033[1m'

log_info() { echo -e "${BLUE}INFO:${NC} $1"; }
log_success() { echo -e "${GREEN}SUCCESS:${NC} $1"; }
log_warning() { echo -e "${YELLOW}WARNING:${NC} $1"; }
log_error() { echo -e "${RED}ERROR:${NC} $1"; }
log_header() { 
    echo -e "\n${BOLD}${CYAN}=== $1 ===${NC}"
}

find_compatible_python() {
    local candidates=()
    local candidate=""
    local path=""

    if [ -n "${PYTHON:-}" ]; then
        candidates+=("${PYTHON}")
    fi

    candidates+=(
        "python3"
        "python"
        "/opt/homebrew/bin/python3"
        "/usr/local/bin/python3"
        "python3.13"
        "python3.12"
        "python3.11"
    )

    for candidate in "${candidates[@]}"; do
        if command -v "$candidate" >/dev/null 2>&1; then
            path="$(command -v "$candidate")"
        elif [ -x "$candidate" ]; then
            path="$candidate"
        else
            continue
        fi

        if "$path" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)' >/dev/null 2>&1; then
            printf '%s\n' "$path"
            return 0
        fi
    done

    return 1
}

# --- Initialization ---
ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT_DIR"

log_header "SecuScan Development Setup"
echo "Starting installation at $(date)"

# --- Prerequisites Check ---
log_header "Prerequisites Check"

# Check Python 3
PYTHON_BIN="$(find_compatible_python || true)"
if [ -z "$PYTHON_BIN" ]; then
    log_error "Python 3.11+ is required. Install a compatible version and make sure it is available on PATH, or run with PYTHON=/path/to/python3.11 ./setup.sh."
    exit 1
fi
PYTHON_VER="$("$PYTHON_BIN" --version | cut -d' ' -f2)"
log_info "Python version: $PYTHON_VER"
log_info "Using Python interpreter: $PYTHON_BIN"

# Check Node.js
if ! command -v node &> /dev/null; then
    log_error "Node.js is not installed. Please install Node.js 16+ and try again."
    exit 1
fi
NODE_VER=$(node --version)
log_info "Node.js version: $NODE_VER"

# Check npm
if ! command -v npm &> /dev/null; then
    log_error "npm is not installed. Please install npm and try again."
    exit 1
fi
NPM_VER=$(npm --version)
log_info "npm version: $NPM_VER"

# Check Docker (Optional)
if command -v docker &> /dev/null; then
    DOCKER_VER=$(docker --version | cut -d' ' -f3 | tr -d ',')
    log_info "Docker version: $DOCKER_VER (Detected)"
else
    log_warning "Docker not found. Docker-based scanning plugins will be disabled."
fi

# --- File System Setup ---
log_header "Directory Structure"
DIRS=("data" "data/raw" "data/reports" "logs" "wordlists")
for dir in "${DIRS[@]}"; do
    if [ ! -d "$ROOT_DIR/$dir" ]; then
        mkdir -p "$ROOT_DIR/$dir"
        log_info "Created directory: $dir"
    else
        log_info "Directory already exists: $dir"
    fi
    # Ensure directory is writable and has a .gitkeep if needed
    touch "$ROOT_DIR/$dir/.gitkeep"
done

# --- Backend Setup ---
log_header "Backend Setup"

# If a venv already exists, verify it was created with a compatible Python.
# A stale venv built from Python 3.9 would otherwise bypass the version check above and silently re-use the wrong interpreter during pip install.
if [ -d "venv" ]; then
    if [ -d "venv/Scripts" ]; then
        VENV_BIN="venv/Scripts"
    else
        VENV_BIN="venv/bin"
    fi

    if [ -x "$VENV_BIN/python3" ]; then
        VENV_PYTHON="$VENV_BIN/python3"
    elif [ -x "$VENV_BIN/python" ]; then
        VENV_PYTHON="$VENV_BIN/python"
    else
        VENV_PYTHON="$VENV_BIN/python3"
    fi

    if [ ! -x "$VENV_PYTHON" ] || \
       ! "$VENV_PYTHON" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)' >/dev/null 2>&1; then
        VENV_OLD_VER="$("$VENV_PYTHON" --version 2>/dev/null | cut -d' ' -f2 || echo 'unknown')"
        log_warning "Existing venv uses Python $VENV_OLD_VER (< 3.11). Removing and recreating with $PYTHON_BIN..."
        rm -rf venv
    else
        log_info "Existing virtual environment found (Python $("$VENV_PYTHON" --version | cut -d' ' -f2))."
    fi
fi

if [ ! -d "venv" ]; then
    log_info "Creating virtual environment in 'venv'..."
    "$PYTHON_BIN" -m venv venv
    log_success "Virtual environment created."
fi

if [ -d "venv/Scripts" ]; then
    VENV_BIN="venv/Scripts"
else
    VENV_BIN="venv/bin"
fi

# Activate venv for installation
source "$VENV_BIN/activate"
log_info "Upgrading pip..."
pip install --upgrade pip -q

log_info "Installing backend dependencies from backend/requirements.txt..."
pip install -r backend/requirements.txt -q
log_info "Installing HTTPX CLI extras required by scanner plugins..."
pip install "httpx[cli]>=0.28.1" -q
if [ -f "backend/requirements-dev.txt" ]; then
    log_info "Installing backend development dependencies..."
    pip install -r backend/requirements-dev.txt -q
fi
log_success "Backend dependencies installed successfully."
deactivate

# --- Frontend Setup ---
log_header "Frontend Setup"
if [ -d "frontend" ]; then
    cd frontend
    
    # Check if node_modules is missing or broken (missing vite binary)
    if [ ! -d "node_modules" ] || [ ! -f "node_modules/.bin/vite" ]; then
        log_info "node_modules is missing or incomplete. Performing clean install..."
        rm -rf node_modules package-lock.json
        npm install
    else
        log_info "Existing node_modules found. Updating dependencies..."
        npm install
    fi
    
    log_success "Frontend dependencies installed successfully."
    cd ..
else
    log_error "Frontend directory not found!"
    exit 1
fi

# --- Environment Configuration ---
log_header "Configuration"
if [ ! -f ".env" ]; then
    log_info "Creating default .env file..."
    cat > .env << EOL
# SecuScan Environment Configuration
# Generated by setup.sh on $(date)

# Backend Settings
SECUSCAN_DEBUG=true
SECUSCAN_LOG_LEVEL=INFO
SECUSCAN_BIND_ADDRESS=127.0.0.1
SECUSCAN_BIND_PORT=8000

# Docker Support (Set to true if Docker is running)
SECUSCAN_DOCKER_ENABLED=false

# Security Settings
SECUSCAN_SAFE_MODE_DEFAULT=true
SECUSCAN_REQUIRE_CONSENT=true
EOL
    log_success ".env file created with default development settings."
else
    log_info ".env file already exists. Skipping creation."
fi

# --- Completion ---
log_header "Setup Complete!"
echo -e "${YELLOW}${BOLD}Thank you for setting up SecuScan!${NC}"
echo ""
echo "To start the development environment, you can run:"
echo -e "  ${BOLD}./start.sh${NC}"
echo ""
echo "Or start them manually in separate terminals:"
if [ -d "venv/Scripts" ]; then
    echo -e "  ${CYAN}Backend:${NC}  source venv/Scripts/activate && python -m uvicorn backend.secuscan.main:app --reload"
else
    echo -e "  ${CYAN}Backend:${NC}  source venv/bin/activate && python -m uvicorn backend.secuscan.main:app --reload"
fi
echo -e "  ${CYAN}Frontend:${NC} cd frontend && npm run dev"
echo ""
echo "Access the app at: ${BOLD}http://localhost:5173${NC}"
echo "--------------------------------------------------------------------------------"
echo ""