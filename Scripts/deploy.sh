#!/bin/bash

# Deployment Script
# Handles production deployment and environment management

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

# Function to check deployment prerequisites
check_prerequisites() {
    print_status "Checking deployment prerequisites..."

    # Check if we're on a supported OS
    if [[ "$OSTYPE" != "linux-gnu"* ]]; then
        print_warning "This deployment script is designed for Linux systems"
    fi

    # Check for required tools
    REQUIRED_TOOLS=("python3" "pip3" "nginx" "certbot")
    for tool in "${REQUIRED_TOOLS[@]}"; do
        if ! command -v "$tool" &> /dev/null; then
            print_error "Required tool not found: $tool"
            print_error "Please install it and run this script again."
            exit 1
        fi
    done

    print_success "Prerequisites check passed"
}

# Function to setup production environment
setup_production() {
    print_status "Setting up production environment..."

    # Create production .env file if it doesn't exist
    if [ ! -f ".env.production" ]; then
        print_status "Creating production environment file..."

        # Generate secure keys
        SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
        JWT_SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")

        cat > .env.production << EOF
# Production Environment Configuration
APP_ENV=production
DEBUG=False
SECRET_KEY=${SECRET_KEY}

# Database Configuration (PostgreSQL required for production)
DATABASE_URL=postgresql://username:password@localhost:5432/form_builder_prod

# JWT Configuration
JWT_SECRET_KEY=${JWT_SECRET_KEY}
JWT_ACCESS_TOKEN_EXPIRES=900
JWT_REFRESH_TOKEN_EXPIRES=604800

# Email Configuration (Required for production)
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password
MAIL_DEFAULT_SENDER=noreply@yourdomain.com

# File Upload Configuration
UPLOAD_FOLDER=/var/www/forms/uploads
MAX_CONTENT_LENGTH=16777216

# Redis Configuration (Required for production)
REDIS_URL=redis://localhost:6379/0

# Security Configuration
SESSION_COOKIE_SECURE=True
SESSION_COOKIE_HTTPONLY=True
SESSION_COOKIE_SAMESITE=Lax

# Performance Configuration
CACHE_DEFAULT_TIMEOUT=300

# Analytics Configuration
ANALYTICS_RETENTION_DAYS=365

# Logging Configuration
LOG_LEVEL=INFO
LOG_FILE=/var/log/forms/app.log
EOF

        print_success "Production environment file created: .env.production"
        print_warning "Please edit .env.production with your actual production values!"
    else
        print_warning "Production environment file already exists"
    fi
}

# Function to setup Nginx
setup_nginx() {
    DOMAIN=${1:-"yourdomain.com"}

    if [ "$DOMAIN" = "yourdomain.com" ]; then
        print_warning "Using default domain. Please specify your actual domain."
        read -p "Enter your domain name: " DOMAIN
    fi

    print_status "Setting up Nginx configuration for $DOMAIN..."

    NGINX_CONF="/etc/nginx/sites-available/forms"

    sudo tee "$NGINX_CONF" > /dev/null << EOF
server {
    listen 80;
    server_name $DOMAIN www.$DOMAIN;

    location = /favicon.ico { access_log off; log_not_found off; }
    
    location /static {
        alias /var/www/forms/app/static;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    location / {
        include proxy_params;
        proxy_pass http://unix:/var/www/forms/forms.sock;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF

    # Enable the site
    sudo ln -sf "$NGINX_CONF" "/etc/nginx/sites-enabled/"

    # Remove default nginx site if it exists
    sudo rm -f "/etc/nginx/sites-enabled/default"

    # Test nginx configuration
    sudo nginx -t

    print_success "Nginx configuration created"
}

# Function to setup SSL certificate
setup_ssl() {
    DOMAIN=${1:-"yourdomain.com"}

    if [ "$DOMAIN" = "yourdomain.com" ]; then
        print_warning "Using default domain. Please specify your actual domain."
        read -p "Enter your domain name: " DOMAIN
    fi

    print_status "Setting up SSL certificate for $DOMAIN..."

    # Stop nginx temporarily for certbot
    sudo systemctl stop nginx

    # Get SSL certificate
    sudo certbot certonly --standalone -d "$DOMAIN" -d "www.$DOMAIN"

    # Start nginx again
    sudo systemctl start nginx

    # Update nginx config for SSL
    NGINX_SSL_CONF="/etc/nginx/sites-available/forms-ssl"

    sudo tee "$NGINX_SSL_CONF" > /dev/null << EOF
server {
    listen 443 ssl http2;
    server_name $DOMAIN www.$DOMAIN;

    ssl_certificate /etc/letsencrypt/live/$DOMAIN/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/$DOMAIN/privkey.pem;
    
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;

    location = /favicon.ico { access_log off; log_not_found off; }
    
    location /static {
        alias /var/www/forms/app/static;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    location / {
        include proxy_params;
        proxy_pass http://unix:/var/www/forms/forms.sock;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}

# Redirect HTTP to HTTPS
server {
    listen 80;
    server_name $DOMAIN www.$DOMAIN;
    return 301 https://\$server_name\$request_uri;
}
EOF

    # Enable SSL site and disable non-SSL
    sudo ln -sf "$NGINX_SSL_CONF" "/etc/nginx/sites-enabled/"
    sudo rm -f "/etc/nginx/sites-enabled/forms"

    # Test and reload nginx
    sudo nginx -t
    sudo systemctl reload nginx

    print_success "SSL certificate configured"
}

# Function to deploy application
deploy_app() {
    print_status "Deploying application..."

    # Create deployment directory
    sudo mkdir -p /var/www/forms
    sudo chown -R "$USER:$USER" /var/www/forms

    # Copy application files
    rsync -av --exclude='venv' --exclude='__pycache__' --exclude='*.pyc' --exclude='.git' . /var/www/forms/

    # Setup virtual environment
    cd /var/www/forms
    python3 -m venv venv
    source venv/bin/activate

    # Install dependencies
    pip install -r requirements.txt

    # Setup environment
    cp .env.production .env

    # Run database migrations
    export FLASK_APP=run.py
    export FLASK_ENV=production
    flask db upgrade

    # Create systemd service
    create_systemd_service

    print_success "Application deployed"
}

# Function to create systemd service
create_systemd_service() {
    print_status "Creating systemd service..."

    SERVICE_FILE="/etc/systemd/system/forms.service"

    sudo tee "$SERVICE_FILE" > /dev/null << EOF
[Unit]
Description=Dynamic Form Builder Flask App
After=network.target

[Service]
User=$USER
Group=$USER
WorkingDirectory=/var/www/forms
Environment="PATH=/var/www/forms/venv/bin"
ExecStart=/var/www/forms/venv/bin/gunicorn --bind unix:/var/www/forms/forms.sock -m 007 run:app
Restart=always

[Install]
WantedBy=multi-user.target
EOF

    sudo systemctl daemon-reload
    sudo systemctl enable forms
    sudo systemctl start forms

    print_success "Systemd service created and started"
}

# Function to setup log rotation
setup_logging() {
    print_status "Setting up log rotation..."

    LOGROTATE_CONF="/etc/logrotate.d/forms"

    sudo tee "$LOGROTATE_CONF" > /dev/null << EOF
/var/log/forms/*.log {
    daily
    missingok
    rotate 52
    compress
    delaycompress
    notifempty
    create 644 $USER $USER
    postrotate
        systemctl reload forms
    endscript
}
EOF

    print_success "Log rotation configured"
}

# Function to setup monitoring
setup_monitoring() {
    print_status "Setting up basic monitoring..."

    # Create monitoring script
    cat > /var/www/forms/monitor.sh << 'EOF'
#!/bin/bash
# Basic monitoring script

# Check if service is running
if systemctl is-active --quiet forms; then
    echo "✓ Forms service is running"
else
    echo "✗ Forms service is not running"
    exit 1
fi

# Check if nginx is running
if systemctl is-active --quiet nginx; then
    echo "✓ Nginx is running"
else
    echo "✗ Nginx is not running"
    exit 1
fi

# Check disk space
DISK_USAGE=$(df / | tail -1 | awk '{print $5}' | sed 's/%//')
if [ "$DISK_USAGE" -gt 90 ]; then
    echo "⚠ Disk usage is high: ${DISK_USAGE}%"
else
    echo "✓ Disk usage: ${DISK_USAGE}%"
fi

# Check database connectivity (basic check)
if pg_isready -h localhost -U postgres 2>/dev/null; then
    echo "✓ PostgreSQL is accessible"
else
    echo "⚠ PostgreSQL connection check failed"
fi
EOF

    chmod +x /var/www/forms/monitor.sh

    # Setup cron job for monitoring
    CRON_JOB="*/5 * * * * /var/www/forms/monitor.sh >> /var/log/forms/monitor.log 2>&1"
    (crontab -l ; echo "$CRON_JOB") | crontab -

    print_success "Basic monitoring setup completed"
}

# Function to show deployment status
show_status() {
    print_status "Deployment Status:"

    echo ""
    echo "Services:"
    if systemctl is-active --quiet forms 2>/dev/null; then
        echo "✓ Forms service: Running"
    else
        echo "✗ Forms service: Not running"
    fi

    if systemctl is-active --quiet nginx 2>/dev/null; then
        echo "✓ Nginx: Running"
    else
        echo "✗ Nginx: Not running"
    fi

    echo ""
    echo "Directories:"
    if [ -d "/var/www/forms" ]; then
        echo "✓ Application directory: /var/www/forms"
    else
        echo "✗ Application directory not found"
    fi

    if [ -d "/etc/nginx/sites-enabled/forms-ssl" ]; then
        echo "✓ SSL configuration: Enabled"
    else
        echo "⚠ SSL configuration: Not found"
    fi

    echo ""
    echo "Logs:"
    echo "  Application logs: /var/log/forms/"
    echo "  Nginx logs: /var/log/nginx/"
}

# Function to show help
show_help() {
    echo "Deployment Script"
    echo ""
    echo "Usage: $0 <command> [options]"
    echo ""
    echo "Commands:"
    echo "  setup          Setup production environment"
    echo "  nginx <domain> Setup Nginx configuration"
    echo "  ssl <domain>   Setup SSL certificate"
    echo "  deploy         Deploy the application"
    echo "  service        Create systemd service"
    echo "  logs           Setup log rotation"
    echo "  monitor        Setup basic monitoring"
    echo "  status         Show deployment status"
    echo "  full <domain>  Run full deployment (setup + nginx + ssl + deploy + logs + monitor)"
    echo "  help           Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 setup"
    echo "  $0 nginx mydomain.com"
    echo "  $0 full mydomain.com"
}

# Main function
main() {
    COMMAND=${1:-"help"}

    case $COMMAND in
        "setup")
            check_prerequisites
            setup_production
            ;;
        "nginx")
            setup_nginx "$2"
            ;;
        "ssl")
            setup_ssl "$2"
            ;;
        "deploy")
            deploy_app
            ;;
        "service")
            create_systemd_service
            ;;
        "logs")
            setup_logging
            ;;
        "monitor")
            setup_monitoring
            ;;
        "status")
            show_status
            ;;
        "full")
            DOMAIN="$2"
            if [ -z "$DOMAIN" ]; then
                print_error "Domain name is required for full deployment"
                exit 1
            fi
            check_prerequisites
            setup_production
            setup_nginx "$DOMAIN"
            setup_ssl "$DOMAIN"
            deploy_app
            setup_logging
            setup_monitoring
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