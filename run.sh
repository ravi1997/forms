#!/bin/bash

# Dynamic Form Builder - Run Script
# This script executes the Flask application with proper environment setup

set -e  # Exit on any error

# Colors for output
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

# Function to check if virtual environment exists
check_venv() {
    if [ ! -d "venv" ]; then
        print_error "Virtual environment not found!"
        print_error "Please run ./setup.sh first to set up the project."
        exit 1
    fi
}

# Function to check if .env file exists
check_env() {
    if [ ! -f ".env" ]; then
        print_error ".env file not found!"
        print_error "Please run ./setup.sh first or create a .env file."
        exit 1
    fi
}

# Function to check if database is initialized
check_database() {
    if [ ! -f "app.db" ] && [[ ! "$DATABASE_URL" =~ ^postgresql:// ]]; then
        print_warning "Database not found. Running database initialization..."
        source venv/bin/activate
        export FLASK_APP=run.py
        export FLASK_ENV=development
        flask db upgrade
        print_success "Database initialized"
    fi
}

# Function to start the Flask application
start_flask() {
    print_status "Starting Flask application..."

    # Activate virtual environment
    source venv/bin/activate

    # Set Flask environment variables
    export FLASK_APP=run.py
    export FLASK_ENV=${FLASK_ENV:-development}
    export FLASK_DEBUG=${FLASK_DEBUG:-True}

    # Load environment variables from .env file
    if [ -f ".env" ]; then
        set -a
        source .env
        set +a
    fi

    # Check database
    check_database

    # Start the application
    print_success "Application starting on http://localhost:5000"
    print_status "Press Ctrl+C to stop the application"

    # Run with auto-reload for development
    if [ "$FLASK_ENV" = "development" ]; then
        python run.py
    else
        # For production, use gunicorn
        if command -v gunicorn &> /dev/null; then
            gunicorn --bind 0.0.0.0:5000 --workers 4 --timeout 120 "run:app"
        else
            print_warning "Gunicorn not found. Falling back to Flask development server."
            python run.py
        fi
    fi
}

# Function to run database migrations
run_migrations() {
    print_status "Running database migrations..."

    source venv/bin/activate
    export FLASK_APP=run.py
    export FLASK_ENV=${FLASK_ENV:-development}

    flask db upgrade
    print_success "Database migrations completed"
}

# Function to run tests
run_tests() {
    print_status "Running tests..."

    source venv/bin/activate
    export FLASK_APP=run.py
    export FLASK_ENV=testing

    if [ -n "$1" ] && [ "$1" = "--coverage" ]; then
        python -m pytest tests/ --cov=app --cov-report=html
        print_success "Tests completed with coverage report"
        print_status "Coverage report saved to htmlcov/index.html"
    else
        python -m pytest tests/ -v
        print_success "Tests completed"
    fi
}

# Function to run Flask shell
run_shell() {
    print_status "Starting Flask shell..."

    source venv/bin/activate
    export FLASK_APP=run.py
    export FLASK_ENV=${FLASK_ENV:-development}

    flask shell
}

# Function to show help
show_help() {
    echo "Dynamic Form Builder - Run Script"
    echo ""
    echo "Usage: $0 [COMMAND] [OPTIONS]"
    echo ""
    echo "Commands:"
    echo "  (no command)    Start the Flask application"
    echo "  migrate         Run database migrations"
    echo "  test           Run the test suite"
    echo "  shell          Start Flask shell"
    echo "  help           Show this help message"
    echo ""
    echo "Options:"
    echo "  --coverage     Run tests with coverage report (only with test command)"
    echo ""
    echo "Environment Variables:"
    echo "  FLASK_ENV      Set to 'production' for production mode (default: development)"
    echo "  FLASK_DEBUG    Set to 'False' to disable debug mode (default: True)"
    echo ""
    echo "Examples:"
    echo "  $0                    # Start development server"
    echo "  $0 test --coverage   # Run tests with coverage"
    echo "  FLASK_ENV=production $0  # Start in production mode"
}

# Function to check system requirements
check_requirements() {
    # Check if virtual environment exists
    check_venv

    # Check if .env file exists
    check_env

    # Check if required directories exist
    if [ ! -d "uploads" ]; then
        print_warning "uploads directory not found. Creating..."
        mkdir -p uploads
        chmod 755 uploads
    fi

    if [ ! -d "logs" ]; then
        print_warning "logs directory not found. Creating..."
        mkdir -p logs
        chmod 755 logs
    fi
}

# Main function
main() {
    # Parse command line arguments
    COMMAND=${1:-""}

    case $COMMAND in
        "migrate")
            check_requirements
            run_migrations
            ;;
        "test")
            check_requirements
            shift
            run_tests "$@"
            ;;
        "shell")
            check_requirements
            run_shell
            ;;
        "help"|"-h"|"--help")
            show_help
            ;;
        "")
            check_requirements
            start_flask
            ;;
        *)
            print_error "Unknown command: $COMMAND"
            echo ""
            show_help
            exit 1
            ;;
    esac
}

# Run main function with all arguments
main "$@"