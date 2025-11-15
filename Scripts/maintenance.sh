#!/bin/bash

# Maintenance Script
# Handles cleanup, log management, and system health checks

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

# Function to clean up old log files
cleanup_logs() {
    print_status "Cleaning up old log files..."

    DAYS=${1:-30}  # Default to 30 days

    if [ -d "logs" ]; then
        # Remove log files older than specified days
        find logs -name "*.log" -type f -mtime +$DAYS -delete
        print_success "Removed log files older than $DAYS days"
    else
        print_warning "Logs directory not found"
    fi
}

# Function to clean up old uploaded files
cleanup_uploads() {
    print_status "Cleaning up old uploaded files..."

    DAYS=${1:-90}  # Default to 90 days

    if [ -d "uploads" ]; then
        # Remove files older than specified days (be careful with this!)
        find uploads -type f -mtime +$DAYS -delete
        print_success "Removed uploaded files older than $DAYS days"
    else
        print_warning "Uploads directory not found"
    fi
}

# Function to clean up old database backups
cleanup_backups() {
    print_status "Cleaning up old database backups..."

    DAYS=${1:-30}  # Default to 30 days

    if [ -d "backups" ]; then
        # Remove backup files older than specified days
        find backups -name "*.gz" -type f -mtime +$DAYS -delete
        print_success "Removed backup files older than $DAYS days"
    else
        print_warning "Backups directory not found"
    fi
}

# Function to clean up Python cache files
cleanup_cache() {
    print_status "Cleaning up Python cache files..."

    # Remove __pycache__ directories
    find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    find . -name "*.pyc" -delete
    find . -name "*.pyo" -delete

    print_success "Python cache files cleaned up"
}

# Function to clean up old sessions (if using filesystem sessions)
cleanup_sessions() {
    print_status "Cleaning up old session files..."

    if [ -d "flask_session" ]; then
        # Remove session files older than 7 days
        find flask_session -type f -mtime +7 -delete
        print_success "Removed session files older than 7 days"
    else
        print_warning "Session directory not found"
    fi
}

# Function to check system health
check_health() {
    print_status "Performing system health check..."

    # Check disk space
    DISK_USAGE=$(df -h . | tail -1 | awk '{print $5}' | sed 's/%//')
    if [ "$DISK_USAGE" -gt 90 ]; then
        print_warning "Disk usage is high: ${DISK_USAGE}%"
    else
        print_success "Disk usage: ${DISK_USAGE}%"
    fi

    # Check database connectivity
    activate_venv
    export FLASK_APP=run.py
    export FLASK_ENV=${FLASK_ENV:-development}

    if python3 -c "
from app import create_app, db
app = create_app()
with app.app_context():
    try:
        db.engine.execute('SELECT 1')
        print('Database connection: OK')
    except Exception as e:
        print(f'Database connection: FAILED - {e}')
        exit(1)
    "; then
        print_success "Database connectivity check passed"
    else
        print_error "Database connectivity check failed"
    fi

    # Check if required directories exist and have proper permissions
    DIRS=("uploads" "logs" "backups")
    for dir in "${DIRS[@]}"; do
        if [ -d "$dir" ]; then
            PERMS=$(stat -c "%a" "$dir" 2>/dev/null || stat -f "%A" "$dir" 2>/dev/null)
            if [ "$PERMS" = "755" ]; then
                print_success "Directory $dir has correct permissions"
            else
                print_warning "Directory $dir has permissions $PERMS (should be 755)"
            fi
        else
            print_warning "Directory $dir does not exist"
        fi
    done

    # Check virtual environment
    if [ -f "venv/bin/activate" ]; then
        print_success "Virtual environment exists"
    else
        print_error "Virtual environment not found"
    fi

    # Check .env file
    if [ -f ".env" ]; then
        print_success ".env file exists"
    else
        print_warning ".env file not found"
    fi
}

# Function to show disk usage
show_disk_usage() {
    print_status "Disk usage information:"

    echo "Current directory:"
    du -sh .

    echo ""
    echo "By subdirectory:"
    du -sh */ 2>/dev/null || true

    echo ""
    echo "Database size:"
    if [ -f "app.db" ]; then
        du -sh app.db
    else
        echo "SQLite database not found"
    fi

    echo ""
    echo "Uploads directory:"
    if [ -d "uploads" ]; then
        du -sh uploads
    else
        echo "Uploads directory not found"
    fi

    echo ""
    echo "Logs directory:"
    if [ -d "logs" ]; then
        du -sh logs
    else
        echo "Logs directory not found"
    fi
}

# Function to optimize database
optimize_db() {
    print_status "Optimizing database..."

    activate_venv
    export FLASK_APP=run.py
    export FLASK_ENV=${FLASK_ENV:-development}

    # Load environment variables
    if [ -f ".env" ]; then
        set -a
        source .env
        set +a
    fi

    if [[ "$DATABASE_URL" =~ ^postgresql:// ]]; then
        # PostgreSQL optimization
        print_status "Running PostgreSQL VACUUM ANALYZE..."
        # This would require psql access to the database
        print_warning "PostgreSQL optimization requires manual VACUUM ANALYZE"
    else
        # SQLite optimization
        if [ -f "app.db" ]; then
            sqlite3 app.db "VACUUM;"
            sqlite3 app.db "REINDEX;"
            print_success "SQLite database optimized"
        else
            print_warning "SQLite database not found"
        fi
    fi
}

# Function to run all cleanup tasks
cleanup_all() {
    print_status "Running all cleanup tasks..."

    cleanup_logs "${1:-30}"
    cleanup_uploads "${2:-90}"
    cleanup_backups "${3:-30}"
    cleanup_cache
    cleanup_sessions

    print_success "All cleanup tasks completed"
}

# Function to show help
show_help() {
    echo "Maintenance Script"
    echo ""
    echo "Usage: $0 <command> [options]"
    echo ""
    echo "Commands:"
    echo "  cleanup [logs_days] [uploads_days] [backups_days]  Clean up old files"
    echo "  logs [days]                                          Clean up old log files"
    echo "  uploads [days]                                       Clean up old uploaded files"
    echo "  backups [days]                                       Clean up old backup files"
    echo "  cache                                                Clean up Python cache files"
    echo "  sessions                                             Clean up old session files"
    echo "  health                                               Run system health check"
    echo "  disk                                                 Show disk usage information"
    echo "  optimize                                             Optimize database"
    echo "  help                                                 Show this help message"
    echo ""
    echo "Default retention periods:"
    echo "  Logs: 30 days"
    echo "  Uploads: 90 days"
    echo "  Backups: 30 days"
    echo ""
    echo "Examples:"
    echo "  $0 cleanup              # Clean up with default retention"
    echo "  $0 cleanup 7 30 14      # Custom retention: logs=7d, uploads=30d, backups=14d"
    echo "  $0 health               # Run health check"
    echo "  $0 disk                 # Show disk usage"
}

# Main function
main() {
    COMMAND=${1:-"help"}

    case $COMMAND in
        "cleanup")
            shift
            cleanup_all "$@"
            ;;
        "logs")
            cleanup_logs "${2:-30}"
            ;;
        "uploads")
            cleanup_uploads "${2:-90}"
            ;;
        "backups")
            cleanup_backups "${2:-30}"
            ;;
        "cache")
            cleanup_cache
            ;;
        "sessions")
            cleanup_sessions
            ;;
        "health")
            check_health
            ;;
        "disk")
            show_disk_usage
            ;;
        "optimize")
            optimize_db
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