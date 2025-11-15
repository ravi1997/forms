#!/bin/bash

# System Check Script
# Checks system requirements and provides troubleshooting help

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

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

# Function to check operating system
check_os() {
    print_status "Checking operating system..."

    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        print_success "Linux system detected"
        echo "  Distribution: $(lsb_release -d 2>/dev/null | cut -f2 || echo 'Unknown')"
        echo "  Kernel: $(uname -r)"
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        print_success "macOS system detected"
        echo "  Version: $(sw_vers -productVersion 2>/dev/null || echo 'Unknown')"
    elif [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "win32" ]]; then
        print_warning "Windows system detected"
        print_warning "This application is designed for Linux/macOS"
        print_warning "Consider using WSL2 on Windows for better compatibility"
    else
        print_warning "Unknown operating system: $OSTYPE"
    fi
}

# Function to check Python installation
check_python() {
    print_status "Checking Python installation..."

    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 --version 2>&1 | cut -d' ' -f2)
        print_success "Python 3 found: $PYTHON_VERSION"

        # Check if version is >= 3.8
        PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
        PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

        if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 8 ]); then
            print_warning "Python 3.8+ is recommended. Current version: $PYTHON_VERSION"
        fi
    else
        print_error "Python 3 not found"
        echo "  Install Python 3.8+ from https://python.org"
        return 1
    fi

    # Check pip
    if command -v pip3 &> /dev/null; then
        PIP_VERSION=$(pip3 --version 2>&1 | cut -d' ' -f2)
        print_success "pip found: $PIP_VERSION"
    else
        print_error "pip3 not found"
        echo "  Install pip: python3 -m ensurepip --upgrade"
        return 1
    fi
}

# Function to check system dependencies
check_dependencies() {
    print_status "Checking system dependencies..."

    local missing_deps=()

    # Check for essential build tools
    if ! command -v gcc &> /dev/null && ! command -v clang &> /dev/null; then
        missing_deps+=("build-essential (gcc/clang)")
    fi

    # Check for development headers
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        if ! dpkg -l | grep -q "python3-dev\|python3-devel"; then
            missing_deps+=("python3-dev")
        fi
    fi

    # Check for PostgreSQL (optional)
    if command -v psql &> /dev/null; then
        PG_VERSION=$(psql --version 2>&1 | head -1 | cut -d' ' -f3)
        print_success "PostgreSQL client found: $PG_VERSION"
    else
        print_warning "PostgreSQL client not found"
        echo "  Install PostgreSQL client for full functionality"
    fi

    # Check for Redis (optional)
    if command -v redis-server &> /dev/null; then
        REDIS_VERSION=$(redis-server --version 2>&1 | cut -d' ' -f3)
        print_success "Redis found: $REDIS_VERSION"
    else
        print_warning "Redis not found"
        echo "  Install Redis for caching and background tasks"
    fi

    # Check for Node.js (optional, for frontend development)
    if command -v node &> /dev/null; then
        NODE_VERSION=$(node --version)
        print_success "Node.js found: $NODE_VERSION"
    else
        print_warning "Node.js not found"
        echo "  Install Node.js for frontend development tools"
    fi

    if [ ${#missing_deps[@]} -ne 0 ]; then
        print_warning "Missing recommended dependencies:"
        for dep in "${missing_deps[@]}"; do
            echo "  - $dep"
        done
    fi
}

# Function to check project structure
check_project() {
    print_status "Checking project structure..."

    local required_files=(
        "run.py"
        "config.py"
        "requirements.txt"
        "README.md"
        "setup.sh"
        "app/__init__.py"
        "app/models/__init__.py"
        "app/schemas/__init__.py"
    )

    local missing_files=()

    for file in "${required_files[@]}"; do
        if [ ! -f "$file" ]; then
            missing_files+=("$file")
        fi
    done

    if [ ${#missing_files[@]} -eq 0 ]; then
        print_success "Project structure is complete"
    else
        print_error "Missing required files:"
        for file in "${missing_files[@]}"; do
            echo "  - $file"
        done
        return 1
    fi

    # Check directories
    local required_dirs=(
        "app"
        "app/templates"
        "app/static"
        "tests"
        "Scripts"
    )

    local missing_dirs=()

    for dir in "${required_dirs[@]}"; do
        if [ ! -d "$dir" ]; then
            missing_dirs+=("$dir")
        fi
    done

    if [ ${#missing_dirs[@]} -eq 0 ]; then
        print_success "Required directories exist"
    else
        print_warning "Missing directories:"
        for dir in "${missing_dirs[@]}"; do
            echo "  - $dir/"
        done
    fi
}

# Function to check virtual environment
check_venv() {
    print_status "Checking virtual environment..."

    if [ -d "venv" ]; then
        print_success "Virtual environment exists"

        if [ -f "venv/bin/activate" ]; then
            print_success "Virtual environment activation script found"
        else
            print_warning "Virtual environment activation script not found"
        fi

        # Check if virtual environment has required packages
        if [ -f "venv/bin/python" ]; then
            # Try to import Flask
            if venv/bin/python -c "import flask" 2>/dev/null; then
                FLASK_VERSION=$(venv/bin/python -c "import flask; print(flask.__version__)")
                print_success "Flask installed in virtual environment: $FLASK_VERSION"
            else
                print_warning "Flask not found in virtual environment"
                echo "  Run: source venv/bin/activate && pip install -r requirements.txt"
            fi
        fi
    else
        print_warning "Virtual environment not found"
        echo "  Run: ./setup.sh"
    fi
}

# Function to check environment configuration
check_env() {
    print_status "Checking environment configuration..."

    if [ -f ".env" ]; then
        print_success "Environment file exists"

        # Check for required environment variables
        local required_vars=(
            "SECRET_KEY"
            "DATABASE_URL"
            "JWT_SECRET_KEY"
        )

        local missing_vars=()

        for var in "${required_vars[@]}"; do
            if ! grep -q "^$var=" .env; then
                missing_vars+=("$var")
            fi
        done

        if [ ${#missing_vars[@]} -eq 0 ]; then
            print_success "Required environment variables are set"
        else
            print_warning "Missing environment variables:"
            for var in "${missing_vars[@]}"; do
                echo "  - $var"
            done
        fi
    else
        print_warning "Environment file not found"
        echo "  Run: ./setup.sh"
    fi
}

# Function to check database
check_database() {
    print_status "Checking database..."

    # Load environment variables
    if [ -f ".env" ]; then
        set -a
        source .env
        set +a
    fi

    if [[ "$DATABASE_URL" =~ ^postgresql:// ]]; then
        print_status "PostgreSQL database configured"

        # Try to connect (basic check)
        if command -v psql &> /dev/null; then
            if psql "$DATABASE_URL" -c "SELECT 1;" &>/dev/null; then
                print_success "PostgreSQL connection successful"
            else
                print_warning "Cannot connect to PostgreSQL database"
                echo "  Check DATABASE_URL in .env file"
                echo "  Ensure PostgreSQL server is running"
            fi
        else
            print_warning "psql command not found - cannot test database connection"
        fi
    elif [ -f "app.db" ]; then
        DB_SIZE=$(du -h app.db | cut -f1)
        print_success "SQLite database exists: $DB_SIZE"
    else
        print_warning "No database found"
        echo "  Run: ./setup.sh"
    fi
}

# Function to check permissions
check_permissions() {
    print_status "Checking file permissions..."

    local issues=()

    # Check script permissions
    for script in setup.sh run.sh Scripts/*.sh; do
        if [ -f "$script" ]; then
            if [ ! -x "$script" ]; then
                issues+=("$script is not executable")
            fi
        fi
    done

    # Check directory permissions
    for dir in uploads logs; do
        if [ -d "$dir" ]; then
            PERMS=$(stat -c "%a" "$dir" 2>/dev/null || stat -f "%A" "$dir" 2>/dev/null)
            if [ "$PERMS" != "755" ]; then
                issues+=("$dir permissions should be 755, currently $PERMS")
            fi
        fi
    done

    if [ ${#issues[@]} -eq 0 ]; then
        print_success "File permissions are correct"
    else
        print_warning "Permission issues found:"
        for issue in "${issues[@]}"; do
            echo "  - $issue"
        done
    fi
}

# Function to check disk space
check_disk() {
    print_status "Checking disk space..."

    DISK_INFO=$(df -h . | tail -1)
    DISK_USAGE=$(echo "$DISK_INFO" | awk '{print $5}' | sed 's/%//')
    DISK_AVAILABLE=$(echo "$DISK_INFO" | awk '{print $4}')

    echo "  Available space: $DISK_AVAILABLE"
    echo "  Usage: $DISK_USAGE%"

    if [ "$DISK_USAGE" -gt 90 ]; then
        print_warning "Disk usage is very high ($DISK_USAGE%)"
        echo "  Consider cleaning up old files or expanding storage"
    elif [ "$DISK_USAGE" -gt 80 ]; then
        print_warning "Disk usage is high ($DISK_USAGE%)"
    else
        print_success "Disk space is adequate"
    fi
}

# Function to run all checks
run_all_checks() {
    print_status "Running comprehensive system check..."
    echo "=========================================="

    check_os
    echo

    check_python
    echo

    check_dependencies
    echo

    check_project
    echo

    check_venv
    echo

    check_env
    echo

    check_database
    echo

    check_permissions
    echo

    check_disk

    echo
    echo "=========================================="
    print_success "System check completed"
}

# Function to show troubleshooting tips
show_troubleshooting() {
    echo "Troubleshooting Tips:"
    echo "====================="
    echo
    echo "1. If setup.sh fails:"
    echo "   - Ensure you have sudo access for system package installation"
    echo "   - Check internet connection for downloading dependencies"
    echo "   - Try: sudo apt update && sudo apt upgrade (on Ubuntu/Debian)"
    echo
    echo "2. If virtual environment issues:"
    echo "   - Delete venv/ and run ./setup.sh again"
    echo "   - Ensure python3-venv is installed"
    echo
    echo "3. If database connection fails:"
    echo "   - For PostgreSQL: ensure server is running and credentials are correct"
    echo "   - For SQLite: check file permissions on app.db"
    echo "   - Run: ./Scripts/database.sh reset"
    echo
    echo "4. If application won't start:"
    echo "   - Check .env file has correct values"
    echo "   - Ensure all dependencies are installed"
    echo "   - Check logs/ directory for error messages"
    echo "   - Try: ./run.sh test"
    echo
    echo "5. If tests fail:"
    echo "   - Ensure database is properly initialized"
    echo "   - Check test database configuration"
    echo "   - Run: ./Scripts/database.sh reset"
    echo
    echo "6. For production deployment:"
    echo "   - Use PostgreSQL instead of SQLite"
    echo "   - Set up Redis for caching"
    echo "   - Configure proper SSL certificates"
    echo "   - Use a reverse proxy like Nginx"
    echo
    echo "For more help, check the documentation or create an issue on GitHub."
}

# Function to show help
show_help() {
    echo "System Check Script"
    echo ""
    echo "Usage: $0 [command]"
    echo ""
    echo "Commands:"
    echo "  all          Run all checks (default)"
    echo "  os           Check operating system"
    echo "  python       Check Python installation"
    echo "  deps         Check system dependencies"
    echo "  project      Check project structure"
    echo "  venv         Check virtual environment"
    echo "  env          Check environment configuration"
    echo "  database     Check database"
    echo "  permissions  Check file permissions"
    echo "  disk         Check disk space"
    echo "  troubleshoot Show troubleshooting tips"
    echo "  help         Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 all"
    echo "  $0 troubleshoot"
}

# Main function
main() {
    COMMAND=${1:-"all"}

    case $COMMAND in
        "all")
            run_all_checks
            ;;
        "os")
            check_os
            ;;
        "python")
            check_python
            ;;
        "deps")
            check_dependencies
            ;;
        "project")
            check_project
            ;;
        "venv")
            check_venv
            ;;
        "env")
            check_env
            ;;
        "database")
            check_database
            ;;
        "permissions")
            check_permissions
            ;;
        "disk")
            check_disk
            ;;
        "troubleshoot")
            show_troubleshooting
            ;;
        "help"|"-h"|"--help")
            show_help
            ;;
        *)
            print_error "Unknown command: $COMMAND"
            echo ""
            show_help
            exit 1
            ;;
    esac
}

main "$@"