#!/bin/bash

# telegram_coinglass_trader startup script
# Handles environment setup and application launch

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

# Check if script is run from project root
check_project_root() {
    if [ ! -f "pyproject.toml" ]; then
        error "pyproject.toml not found. Please run this script from the project root directory."
        exit 1
    fi
}

# Check Python version
check_python_version() {
    log "Checking Python version..."
    
    if ! command -v python3.11 &> /dev/null; then
        if ! command -v python3 &> /dev/null; then
            error "Python 3 not found. Please install Python 3.11 or higher."
            exit 1
        fi
        
        PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
        REQUIRED_VERSION="3.11"
        
        if ! printf '%s\n%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V -C; then
            error "Python $PYTHON_VERSION found, but Python $REQUIRED_VERSION or higher is required."
            exit 1
        fi
        
        PYTHON_CMD="python3"
    else
        PYTHON_CMD="python3.11"
    fi
    
    success "Python version check passed: $($PYTHON_CMD --version)"
}

# Check if Poetry is installed
check_poetry() {
    log "Checking Poetry installation..."
    
    if ! command -v poetry &> /dev/null; then
        warning "Poetry not found. Installing Poetry..."
        curl -sSL https://install.python-poetry.org | $PYTHON_CMD -
        
        # Add Poetry to PATH
        export PATH="$HOME/.local/bin:$PATH"
        
        if ! command -v poetry &> /dev/null; then
            error "Poetry installation failed. Please install manually: https://python-poetry.org/docs/#installation"
            exit 1
        fi
    fi
    
    success "Poetry is available: $(poetry --version)"
}

# Install dependencies
install_dependencies() {
    log "Installing dependencies with Poetry..."
    
    if [ ! -f "poetry.lock" ]; then
        warning "poetry.lock not found. Running poetry lock..."
        poetry lock
    fi
    
    poetry install
    success "Dependencies installed successfully"
}

# Check environment file
check_environment() {
    log "Checking environment configuration..."
    
    if [ ! -f ".env" ]; then
        if [ -f ".env.template" ]; then
            warning ".env file not found. Creating from template..."
            cp .env.template .env
            error "Please edit .env file with your API keys and configuration before running the bot."
            echo "Required settings:"
            echo "  - BYBIT_API_KEY"
            echo "  - BYBIT_SECRET" 
            echo "  - COINGLASS_API_KEY"
            echo "  - TELEGRAM_BOT_TOKEN"
            echo "  - TELEGRAM_CHAT_ID"
            exit 1
        else
            error ".env file not found and no template available. Please create .env with required configuration."
            exit 1
        fi
    fi
    
    # Check for required environment variables
    source .env
    
    REQUIRED_VARS=(
        "BYBIT_API_KEY"
        "BYBIT_SECRET"
        "COINGLASS_API_KEY" 
        "TELEGRAM_BOT_TOKEN"
        "TELEGRAM_CHAT_ID"
    )
    
    MISSING_VARS=()
    for var in "${REQUIRED_VARS[@]}"; do
        if [ -z "${!var}" ] || [ "${!var}" = "your_${var,,}_here" ]; then
            MISSING_VARS+=("$var")
        fi
    done
    
    if [ ${#MISSING_VARS[@]} -ne 0 ]; then
        error "Missing or placeholder values for required environment variables:"
        for var in "${MISSING_VARS[@]}"; do
            echo "  - $var"
        done
        echo "Please update your .env file with actual values."
        exit 1
    fi
    
    success "Environment configuration check passed"
}

# Create necessary directories
create_directories() {
    log "Creating necessary directories..."
    
    mkdir -p logs
    mkdir -p data
    mkdir -p backups
    
    success "Directories created"
}

# Run health checks
run_health_checks() {
    log "Running system health checks..."
    
    # Check if required services are accessible (if configured)
    if [ "${ENABLE_HEALTH_CHECKS:-true}" = "true" ]; then
        log "Performing basic connectivity checks..."
        
        # Test internet connectivity
        if ! curl -s --max-time 5 https://api.bybit.com/v5/market/time > /dev/null; then
            warning "Cannot reach Bybit API. Please check your internet connection."
        fi
        
        if ! curl -s --max-time 5 https://api.coinglass.com > /dev/null; then
            warning "Cannot reach CoinGlass API. Please check your internet connection."
        fi
    fi
    
    success "Health checks completed"
}

# Start the application
start_application() {
    log "Starting telegram_coinglass_trader..."
    
    # Set Python path
    export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"
    
    # Run with Poetry
    if [ "${USE_UVLOOP:-true}" = "true" ]; then
        log "Starting with uvloop for enhanced performance..."
    fi
    
    poetry run python src/main.py "$@"
}

# Cleanup function
cleanup() {
    log "Cleaning up..."
    # Add any necessary cleanup here
}

# Signal handling
trap cleanup EXIT
trap 'error "Script interrupted"; exit 130' INT
trap 'error "Script terminated"; exit 143' TERM

# Main execution
main() {
    log "🚀 Starting telegram_coinglass_trader setup..."
    
    # Perform all checks
    check_project_root
    check_python_version
    check_poetry
    install_dependencies
    check_environment
    create_directories
    run_health_checks
    
    success "Setup completed successfully!"
    log "Launching trading bot..."
    
    # Start the application
    start_application "$@"
}

# Help function
show_help() {
    echo "telegram_coinglass_trader startup script"
    echo ""
    echo "Usage: $0 [options]"
    echo ""
    echo "Options:"
    echo "  --help              Show this help message"
    echo "  --skip-checks       Skip health checks"
    echo "  --no-install        Skip dependency installation"
    echo "  --dry-run          Run setup without starting the bot"
    echo ""
    echo "Environment variables:"
    echo "  ENABLE_HEALTH_CHECKS=false    Disable connectivity checks"
    echo "  USE_UVLOOP=false              Disable uvloop"
    echo ""
    echo "Examples:"
    echo "  $0                             Normal startup"
    echo "  $0 --skip-checks              Skip health checks"
    echo "  $0 --dry-run                  Setup only, don't start bot"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --help)
            show_help
            exit 0
            ;;
        --skip-checks)
            ENABLE_HEALTH_CHECKS=false
            shift
            ;;
        --no-install)
            SKIP_INSTALL=true
            shift
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        *)
            # Unknown option, pass to main application
            break
            ;;
    esac
done

# Override functions if flags are set
if [ "${SKIP_INSTALL:-false}" = "true" ]; then
    install_dependencies() {
        log "Skipping dependency installation (--no-install flag)"
    }
fi

if [ "${DRY_RUN:-false}" = "true" ]; then
    start_application() {
        success "Dry run completed. Bot setup is ready. Use './start.sh' to start the bot."
        exit 0
    }
fi

# Run main function
main "$@" 