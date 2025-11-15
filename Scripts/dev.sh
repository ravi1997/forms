#!/bin/bash

# Development Helper Script
# Provides shortcuts for common development tasks

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

# Function to activate virtual environment
activate_venv() {
    if [ -f "venv/bin/activate" ]; then
        source venv/bin/activate
    else
        print_error "Virtual environment not found. Run ./setup.sh first."
        exit 1
    fi
}

# Function to set Flask environment
set_flask_env() {
    export FLASK_APP=run.py
    export FLASK_ENV=development
    export FLASK_DEBUG=True
}

# Function to start development server
start_dev() {
    print_status "Starting development server..."

    activate_venv
    set_flask_env

    # Load environment variables
    if [ -f ".env" ]; then
        set -a
        source .env
        set +a
    fi

    # Start the development server
    python run.py
}

# Function to run tests
run_tests() {
    print_status "Running tests..."

    activate_venv
    export FLASK_APP=run.py
    export FLASK_ENV=testing

    if [ "$1" = "--coverage" ]; then
        python -m pytest tests/ --cov=app --cov-report=html --cov-report=term
        print_success "Tests completed with coverage report"
        print_status "HTML coverage report: htmlcov/index.html"
    elif [ "$1" = "--watch" ]; then
        # Install pytest-watch if not available
        if ! python -m pytest --version | grep -q "watch"; then
            pip install pytest-watch
        fi
        ptw tests/ --runner "python -m pytest"
    else
        python -m pytest tests/ -v "$@"
        print_success "Tests completed"
    fi
}

# Function to run linting
run_lint() {
    print_status "Running code linting..."

    activate_venv

    # Install linting tools if not available
    if ! command -v flake8 &> /dev/null; then
        pip install flake8
    fi

    if ! command -v black &> /dev/null; then
        pip install black
    fi

    # Run flake8
    print_status "Running flake8..."
    flake8 app/ tests/ --max-line-length=100 --extend-ignore=E203,W503

    # Run black (check only)
    print_status "Checking code formatting with black..."
    black --check --diff app/ tests/

    print_success "Linting completed"
}

# Function to format code
format_code() {
    print_status "Formatting code..."

    activate_venv

    if ! command -v black &> /dev/null; then
        pip install black
    fi

    black app/ tests/
    print_success "Code formatted"
}

# Function to run database migrations
run_migrations() {
    print_status "Running database migrations..."

    activate_venv
    set_flask_env

    flask db upgrade
    print_success "Migrations completed"
}

# Function to create new migration
create_migration() {
    if [ -z "$1" ]; then
        print_error "Please provide migration message"
        echo "Usage: $0 migrate <message>"
        exit 1
    fi

    MESSAGE="$1"
    print_status "Creating new migration: $MESSAGE"

    activate_venv
    set_flask_env

    flask db migrate -m "$MESSAGE"
    print_success "Migration created"
}

# Function to reset database
reset_db() {
    print_warning "This will delete all data. Are you sure?"
    read -p "Type 'yes' to continue: " -r
    if [[ ! $REPLY =~ ^yes$ ]]; then
        print_status "Operation cancelled."
        exit 0
    fi

    print_status "Resetting database..."

    activate_venv
    set_flask_env

    flask db downgrade base 2>/dev/null || true
    flask db upgrade

    print_success "Database reset"
}

# Function to start Flask shell
start_shell() {
    print_status "Starting Flask shell..."

    activate_venv
    set_flask_env

    flask shell
}

# Function to check code quality
check_quality() {
    print_status "Running code quality checks..."

    # Run tests
    run_tests --tb=short

    # Run linting
    run_lint

    # Check for security issues
    if command -v bandit &> /dev/null; then
        print_status "Running security checks..."
        bandit -r app/ -f txt
    else
        print_warning "Bandit not installed. Install with: pip install bandit"
    fi

    print_success "Code quality checks completed"
}

# Function to setup pre-commit hooks
setup_hooks() {
    print_status "Setting up pre-commit hooks..."

    if ! command -v pre-commit &> /dev/null; then
        pip install pre-commit
    fi

    # Create pre-commit config if it doesn't exist
    if [ ! -f ".pre-commit-config.yaml" ]; then
        cat > .pre-commit-config.yaml << 'EOF'
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.4.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files

  - repo: https://github.com/psf/black
    rev: 23.7.0
    hooks:
      - id: black
        language_version: python3

  - repo: https://github.com/pycqa/flake8
    rev: 6.0.0
    hooks:
      - id: flake8
        args: [--max-line-length=100, --extend-ignore=E203,W503]
EOF
    fi

    pre-commit install
    print_success "Pre-commit hooks installed"
}

# Function to create new feature branch
create_branch() {
    if [ -z "$1" ]; then
        print_error "Please provide branch name"
        echo "Usage: $0 branch <name>"
        exit 1
    fi

    BRANCH_NAME="feature/$1"
    print_status "Creating branch: $BRANCH_NAME"

    git checkout -b "$BRANCH_NAME"
    print_success "Branch created and checked out"
}

# Function to show development status
show_status() {
    print_status "Development Environment Status:"

    echo ""
    echo "Git Status:"
    git status --porcelain | head -10

    echo ""
    echo "Python Environment:"
    if [ -f "venv/bin/activate" ]; then
        echo "✓ Virtual environment: venv/"
        source venv/bin/activate
        echo "✓ Python version: $(python --version)"
        echo "✓ Flask version: $(python -c 'import flask; print(flask.__version__)')"
    else
        echo "✗ Virtual environment not found"
    fi

    echo ""
    echo "Database:"
    if [ -f "app.db" ]; then
        DB_SIZE=$(du -h app.db | cut -f1)
        echo "✓ SQLite database: $DB_SIZE"
    else
        echo "⚠ SQLite database not found"
    fi

    echo ""
    echo "Environment:"
    if [ -f ".env" ]; then
        echo "✓ Environment file: .env"
    else
        echo "✗ Environment file not found"
    fi

    echo ""
    echo "Directories:"
    DIRS=("uploads" "logs" "tests")
    for dir in "${DIRS[@]}"; do
        if [ -d "$dir" ]; then
            echo "✓ $dir/"
        else
            echo "✗ $dir/ not found"
        fi
    done
}

# Function to show help
show_help() {
    echo "Development Helper Script"
    echo ""
    echo "Usage: $0 <command> [options]"
    echo ""
    echo "Commands:"
    echo "  start          Start development server"
    echo "  test [options] Run tests (--coverage, --watch)"
    echo "  lint           Run code linting"
    echo "  format         Format code with black"
    echo "  migrate        Run database migrations"
    echo "  migrate <msg>  Create new migration"
    echo "  reset-db       Reset database (WARNING: deletes all data)"
    echo "  shell          Start Flask shell"
    echo "  quality        Run all quality checks"
    echo "  hooks          Setup pre-commit hooks"
    echo "  branch <name>  Create new feature branch"
    echo "  status         Show development environment status"
    echo "  help           Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 start"
    echo "  $0 test --coverage"
    echo "  $0 migrate 'add user preferences'"
    echo "  $0 branch user-authentication"
}

# Main function
main() {
    COMMAND=${1:-"help"}

    case $COMMAND in
        "start")
            start_dev
            ;;
        "test")
            shift
            run_tests "$@"
            ;;
        "lint")
            run_lint
            ;;
        "format")
            format_code
            ;;
        "migrate")
            if [ -n "$2" ]; then
                create_migration "$2"
            else
                run_migrations
            fi
            ;;
        "reset-db")
            reset_db
            ;;
        "shell")
            start_shell
            ;;
        "quality")
            check_quality
            ;;
        "hooks")
            setup_hooks
            ;;
        "branch")
            create_branch "$2"
            ;;
        "status")
            show_status
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