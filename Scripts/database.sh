#!/bin/bash

# Database Management Script
# Handles database operations like backup, restore, reset, etc.

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
    export FLASK_ENV=${FLASK_ENV:-development}
}

# Function to backup database
backup_db() {
    print_status "Creating database backup..."

    TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
    BACKUP_DIR="backups"
    mkdir -p "$BACKUP_DIR"

    # Load environment variables
    if [ -f ".env" ]; then
        set -a
        source .env
        set +a
    fi

    if [[ "$DATABASE_URL" =~ ^postgresql:// ]]; then
        # PostgreSQL backup
        BACKUP_FILE="$BACKUP_DIR/postgres_backup_$TIMESTAMP.sql"
        pg_dump "$DATABASE_URL" > "$BACKUP_FILE"
        print_success "PostgreSQL backup created: $BACKUP_FILE"
    else
        # SQLite backup
        BACKUP_FILE="$BACKUP_DIR/sqlite_backup_$TIMESTAMP.db"
        cp app.db "$BACKUP_FILE"
        print_success "SQLite backup created: $BACKUP_FILE"
    fi

    # Compress the backup
    gzip "$BACKUP_FILE"
    print_success "Backup compressed: ${BACKUP_FILE}.gz"
}

# Function to restore database
restore_db() {
    if [ -z "$1" ]; then
        print_error "Please provide backup file path"
        echo "Usage: $0 restore <backup_file>"
        exit 1
    fi

    BACKUP_FILE="$1"

    if [ ! -f "$BACKUP_FILE" ]; then
        print_error "Backup file not found: $BACKUP_FILE"
        exit 1
    fi

    print_warning "This will overwrite the current database. Are you sure?"
    read -p "Type 'yes' to continue: " -r
    if [[ ! $REPLY =~ ^yes$ ]]; then
        print_status "Operation cancelled."
        exit 0
    fi

    print_status "Restoring database from $BACKUP_FILE..."

    # Load environment variables
    if [ -f ".env" ]; then
        set -a
        source .env
        set +a
    fi

    if [[ "$DATABASE_URL" =~ ^postgresql:// ]]; then
        # PostgreSQL restore
        if [[ "$BACKUP_FILE" =~ \.gz$ ]]; then
            gunzip -c "$BACKUP_FILE" | psql "$DATABASE_URL"
        else
            psql "$DATABASE_URL" < "$BACKUP_FILE"
        fi
        print_success "PostgreSQL database restored"
    else
        # SQLite restore
        if [[ "$BACKUP_FILE" =~ \.gz$ ]]; then
            gunzip -c "$BACKUP_FILE" > app.db
        else
            cp "$BACKUP_FILE" app.db
        fi
        print_success "SQLite database restored"
    fi
}

# Function to reset database
reset_db() {
    print_warning "This will delete all data and recreate the database. Are you sure?"
    read -p "Type 'yes' to continue: " -r
    if [[ ! $REPLY =~ ^yes$ ]]; then
        print_status "Operation cancelled."
        exit 0
    fi

    print_status "Resetting database..."

    activate_venv
    set_flask_env

    # Drop all tables and recreate
    flask db downgrade base 2>/dev/null || true
    flask db upgrade

    print_success "Database reset completed"
}

# Function to show database info
show_info() {
    print_status "Database Information:"

    # Load environment variables
    if [ -f ".env" ]; then
        set -a
        source .env
        set +a
    fi

    echo "Database URL: $DATABASE_URL"

    if [[ "$DATABASE_URL" =~ ^postgresql:// ]]; then
        echo "Database Type: PostgreSQL"
        # Try to get PostgreSQL info
        if command -v psql &> /dev/null; then
            echo "PostgreSQL Version: $(psql --version)"
        fi
    else
        echo "Database Type: SQLite"
        if [ -f "app.db" ]; then
            DB_SIZE=$(du -h app.db | cut -f1)
            echo "Database Size: $DB_SIZE"
        fi
    fi

    # Show migration status
    activate_venv
    set_flask_env
    echo ""
    print_status "Migration Status:"
    flask db current
}

# Function to run migrations
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

# Function to show help
show_help() {
    echo "Database Management Script"
    echo ""
    echo "Usage: $0 <command> [options]"
    echo ""
    echo "Commands:"
    echo "  backup          Create database backup"
    echo "  restore <file>  Restore database from backup"
    echo "  reset           Reset database (delete all data)"
    echo "  info            Show database information"
    echo "  migrate         Run pending migrations"
    echo "  create <msg>    Create new migration"
    echo "  help            Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 backup"
    echo "  $0 restore backups/sqlite_backup_20231115_120000.db.gz"
    echo "  $0 create 'add user preferences'"
}

# Main function
main() {
    COMMAND=${1:-"help"}

    case $COMMAND in
        "backup")
            backup_db
            ;;
        "restore")
            restore_db "$2"
            ;;
        "reset")
            reset_db
            ;;
        "info")
            show_info
            ;;
        "migrate")
            run_migrations
            ;;
        "create")
            create_migration "$2"
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