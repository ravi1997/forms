#!/bin/bash

# Dynamic Form Builder - Setup Script
# This script handles one-time setup tasks for the Flask application

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

# Check if running on supported OS
check_os() {
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        print_status "Detected Linux system"
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        print_status "Detected macOS system"
    else
        print_warning "Unsupported OS: $OSTYPE. This script is designed for Linux/macOS."
        read -p "Continue anyway? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
}

# Check if required tools are installed
check_dependencies() {
    print_status "Checking system dependencies..."

    local missing_deps=()

    # Check for Python
    if ! command -v python3 &> /dev/null; then
        missing_deps+=("python3")
    fi

    # Check for pip
    if ! command -v pip3 &> /dev/null; then
        missing_deps+=("python3-pip")
    fi

    # Check for PostgreSQL (optional for development)
    if ! command -v psql &> /dev/null && ! command -v pg_isready &> /dev/null; then
        print_warning "PostgreSQL not found. The application will use SQLite for development."
        print_warning "For production use, install PostgreSQL and update DATABASE_URL in .env"
    fi

    # Check for Redis (optional)
    if ! command -v redis-server &> /dev/null; then
        print_warning "Redis not found. Some features may not work without Redis."
        print_warning "Install Redis for full functionality."
    fi

    if [ ${#missing_deps[@]} -ne 0 ]; then
        print_error "Missing required dependencies: ${missing_deps[*]}"
        print_error "Please install them and run this script again."
        exit 1
    fi

    print_success "System dependencies check passed"
}

# Create virtual environment
create_venv() {
    print_status "Creating Python virtual environment..."

    if [ -d "venv" ]; then
        print_warning "Virtual environment already exists. Skipping creation."
        return
    fi

    python3 -m venv venv
    print_success "Virtual environment created"
}

# Activate virtual environment and install dependencies
install_dependencies() {
    print_status "Installing Python dependencies..."

    # Activate virtual environment
    source venv/bin/activate

    # Upgrade pip
    pip install --upgrade pip

    # Install dependencies
    if [ -f "requirements.txt" ]; then
        pip install -r requirements.txt
        print_success "Dependencies installed successfully"
    else
        print_error "requirements.txt not found!"
        exit 1
    fi
}

# Create environment configuration
create_env_file() {
    print_status "Setting up environment configuration..."

    if [ -f ".env" ]; then
        print_warning ".env file already exists. Skipping creation."
        print_warning "Please review the existing .env file to ensure it has correct settings."
        return
    fi

    # Generate secure random keys
    SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
    JWT_SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")

    cat > .env << EOF
# Flask Configuration
APP_ENV=development
DEBUG=True
SECRET_KEY=${SECRET_KEY}

# Database Configuration (SQLite for development)
DATABASE_URL=sqlite:///app.db

# JWT Configuration
JWT_SECRET_KEY=${JWT_SECRET_KEY}
JWT_ACCESS_TOKEN_EXPIRES=900
JWT_REFRESH_TOKEN_EXPIRES=604800

# Email Configuration (Configure for production)
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password
MAIL_DEFAULT_SENDER=noreply@example.com

# File Upload Configuration
UPLOAD_FOLDER=uploads
MAX_CONTENT_LENGTH=16777216

# Redis Configuration (Optional - comment out if not using Redis)
REDIS_URL=redis://localhost:6379/0

# Security Configuration
SESSION_COOKIE_SECURE=False
SESSION_COOKIE_HTTPONLY=True
SESSION_COOKIE_SAMESITE=Lax

# Analytics Configuration
ANALYTICS_RETENTION_DAYS=365

# Performance Configuration
CACHE_DEFAULT_TIMEOUT=300
EOF

    print_success "Environment file created at .env"
    print_warning "Please edit .env file with your actual configuration values!"
}

# Initialize database
init_database() {
    print_status "Initializing database..."

    # Activate virtual environment
    source venv/bin/activate

    # Set Flask environment
    export FLASK_APP=run.py
    export FLASK_ENV=development

    # Initialize Flask-Migrate
    if [ ! -d "migrations" ]; then
        flask db init
        print_status "Flask-Migrate initialized"
    else
        print_warning "Migrations directory already exists. Skipping init."
    fi

    # Create initial migration
    flask db migrate -m "Initial migration"
    print_status "Initial migration created"

    # Apply migrations
    flask db upgrade
    print_success "Database initialized and migrated"
}

# Create necessary directories
create_directories() {
    print_status "Creating necessary directories..."

    mkdir -p uploads
    mkdir -p logs
    mkdir -p instance

    # Set proper permissions
    chmod 755 uploads
    chmod 755 logs
    chmod 755 instance

    print_success "Directories created"
}

# Create admin user
create_admin_user() {
    print_status "Creating initial admin user..."

    # Activate virtual environment
    source venv/bin/activate

    # Set Flask environment
    export FLASK_APP=run.py
    export FLASK_ENV=development

    # Run Python script to create admin user
    python3 -c "
from app import create_app, db
from app.models import User, UserRoles

app = create_app()
with app.app_context():
    # Check if admin user already exists
    admin = User.query.filter_by(username='admin').first()
    if admin:
        print('Admin user already exists')
    else:
        admin = User(
            username='admin',
            email='admin@example.com',
            first_name='Admin',
            last_name='User',
            role=UserRoles.ADMIN,
            is_active=True,
            is_verified=True
        )
        admin.set_password('admin123')
        db.session.add(admin)
        db.session.commit()
        print('Admin user created successfully')
        print('Username: admin')
        print('Password: admin123')
        print('Please change the password after first login!')
    "

    print_success "Admin user setup completed"
}

# Run tests to verify setup
run_tests() {
    print_status "Running tests to verify setup..."

    # Activate virtual environment
    source venv/bin/activate

    # Set Flask environment
    export FLASK_APP=run.py
    export FLASK_ENV=testing

    # Run tests
    if python -m pytest tests/ -v --tb=short; then
        print_success "All tests passed!"
    else
        print_warning "Some tests failed. Please check the output above."
        print_warning "You can run tests manually with: source venv/bin/activate && python -m pytest tests/"
    fi
}

# Display next steps
show_next_steps() {
    echo
    print_success "Setup completed successfully!"
    echo
    echo "Next steps:"
    echo "1. Review and update the .env file with your actual configuration"
    echo "2. Start the application: ./run.sh"
    echo "3. Access the application at http://localhost:5000"
    echo "4. Login with admin credentials (admin/admin123)"
    echo "5. Change the admin password after first login"
    echo
    echo "Useful commands:"
    echo "- Start application: ./run.sh"
    echo "- Run tests: source venv/bin/activate && python -m pytest tests/"
    echo "- Access Flask shell: source venv/bin/activate && flask shell"
    echo "- Run database migrations: source venv/bin/activate && flask db upgrade"
    echo
}

# Main setup function
main() {
    echo "=========================================="
    echo "Dynamic Form Builder - Setup Script"
    echo "=========================================="
    echo

    check_os
    check_dependencies
    create_venv
    install_dependencies
    create_env_file
    create_directories
    init_database
    create_admin_user
    run_tests
    show_next_steps

    echo "=========================================="
    print_success "Setup completed!"
    echo "=========================================="
}

# Run main function
main "$@"