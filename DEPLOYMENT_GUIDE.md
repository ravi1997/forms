# Deployment Guide

## Overview

This guide provides instructions for deploying the Flask form builder application in production environments. The application is designed for containerized deployment with Docker and supports horizontal scaling.

## Prerequisites

### System Requirements
- Docker and Docker Compose
- At least 4GB RAM (8GB recommended)
- 20GB free disk space
- Linux server (Ubuntu 20.04 LTS or later recommended)

### External Services
- PostgreSQL database (12 or later)
- Redis server for caching and sessions
- Email service (SMTP) for notifications
- File storage (local or cloud-based)

## Environment Configuration

### Environment Variables
Create a `.env` file with the following variables:

```bash
# Application Settings
APP_ENV=production
SECRET_KEY=your-very-secure-secret-key-here
DEBUG=False

# Database Configuration
DATABASE_URL=postgresql://username:password@db_host:5432/database_name
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=30

# Redis Configuration
REDIS_URL=redis://redis_host:6379/0

# Email Configuration
MAIL_SERVER=smtp.example.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=your-email-username
MAIL_PASSWORD=your-email-password
MAIL_DEFAULT_SENDER=noreply@example.com

# File Storage
FILE_STORAGE_TYPE=local  # or 's3' for AWS S3
UPLOAD_FOLDER=/app/uploads
MAX_CONTENT_LENGTH=16 * 1024 * 1024  # 16MB max file size

# Security
JWT_SECRET_KEY=your-jwt-secret-key-here
JWT_ACCESS_TOKEN_EXPIRES=900  # 15 minutes
JWT_REFRESH_TOKEN_EXPIRES=604800  # 7 days

# Analytics
ANALYTICS_RETENTION_DAYS=365

# Performance
CACHE_DEFAULT_TIMEOUT=300  # 5 minutes
```

## Docker Configuration

### Docker Compose File
Create a `docker-compose.yml` file:

```yaml
version: '3.8'

services:
  web:
    build: .
    ports:
      - "5000:5000"
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=${REDIS_URL}
      - SECRET_KEY=${SECRET_KEY}
      - MAIL_SERVER=${MAIL_SERVER}
      - MAIL_PORT=${MAIL_PORT}
      - MAIL_USE_TLS=${MAIL_USE_TLS}
      - MAIL_USERNAME=${MAIL_USERNAME}
      - MAIL_PASSWORD=${MAIL_PASSWORD}
      - UPLOAD_FOLDER=${UPLOAD_FOLDER}
    volumes:
      - uploads:/app/uploads
    depends_on:
      - db
      - redis
    restart: unless-stopped

  worker:
    build: .
    command: celery -A app.celery_worker.celery worker --loglevel=info
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=${REDIS_URL}
      - SECRET_KEY=${SECRET_KEY}
    depends_on:
      - db
      - redis
    restart: unless-stopped

  db:
    image: postgres:14
    environment:
      - POSTGRES_DB=form_builder
      - POSTGRES_USER=form_user
      - POSTGRES_PASSWORD=form_password
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data
    restart: unless-stopped

volumes:
  postgres_data:
 redis_data:
  uploads:
```

### Dockerfile
```Dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5000

CMD ["gunicorn", "--bind", "0.0.0:5000", "--workers", "4", "--timeout", "120", "run:app"]
```

## Database Setup

### Initial Migration
Run database migrations after deployment:

```bash
docker-compose exec web flask db upgrade
```

### Creating Admin User
Create an initial admin user:

```bash
docker-compose exec web python -c "
from app import create_app, db
from app.models.user import User
from werkzeug.security import generate_password_hash

app = create_app()
with app.app_context():
    admin = User(
        username='admin',
        email='admin@example.com',
        password_hash=generate_password_hash('secure_password'),
        role='admin',
        is_active=True,
        is_verified=True
    )
    db.session.add(admin)
    db.session.commit()
"
```

## Production Configuration

### Web Server
Use a reverse proxy (Nginx) in front of the application:

```nginx
upstream flask_app {
    server localhost:500;
}

server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://flask_app;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static {
        alias /path/to/static/files;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
```

### SSL Configuration
Enable HTTPS with Let's Encrypt:

```nginx
server {
    listen 443 ssl http2;
    server_name your-domain.com;

    ssl_certificate /path/to/certificate.crt;
    ssl_certificate_key /path/to/private.key;

    # SSL configuration settings
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;

    # Rest of configuration...
}
```

## Monitoring and Logging

### Application Logs
Configure centralized logging:

```python
import logging
from logging.handlers import RotatingFileHandler
import os

if not app.debug:
    if not os.path.exists('logs'):
        os.mkdir('logs')
    file_handler = RotatingFileHandler('logs/form_builder.log', maxBytes=1024000, backupCount=10)
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
    ))
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.setLevel(logging.INFO)
    app.logger.info('Form Builder startup')
```

### Health Checks
Implement health check endpoints:

```python
@app.route('/health')
def health_check():
    return {
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'version': '1.0.0'
    }
```

## Scaling Configuration

### Horizontal Scaling
For high-traffic deployments, scale the web service:

```bash
docker-compose up --scale web=3
```

### Load Balancer Configuration
Configure your load balancer to distribute traffic across multiple instances.

## Backup Strategy

### Database Backups
Schedule regular database backups:

```bash
#!/bin/bash
# backup_db.sh
DATE=$(date +%Y%m%d_%H%M%S)
pg_dump -h db_host -U form_user -d form_builder > backup_$DATE.sql
gzip backup_$DATE.sql
```

### File Storage Backups
Backup uploaded files regularly:

```bash
#!/bin/bash
# backup_files.sh
DATE=$(date +%Y%m%d_%H%M%S)
tar -czf uploads_$DATE.tar.gz /app/uploads
```

## Security Hardening

### Firewall Configuration
Configure firewall to only allow necessary ports:

```bash
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow 'Nginx Full'
sudo ufw enable
```

### File Permissions
Set appropriate file permissions:

```bash
chown -R www-data:www-data /app/uploads
chmod -R 755 /app/uploads
```

## Maintenance Tasks

### Regular Maintenance
Schedule regular maintenance tasks:

```bash
# Clean up old files
find /app/uploads -type f -mtime +30 -delete

# Clean up old sessions
redis-cli -n 0 KEYS "session:*" | xargs redis-cli -n 0 DEL

# Update statistics
docker-compose exec web flask update-stats
```

### Monitoring Commands
Monitor application performance:

```bash
# Check container status
docker-compose ps

# Monitor logs
docker-compose logs -f web

# Check resource usage
docker stats
```

## Rollback Procedure

### Version Rollback
To rollback to a previous version:

1. Stop the current containers: `docker-compose down`
2. Revert the code to the previous version
3. Rebuild the images: `docker-compose build`
4. Start the services: `docker-compose up -d`
5. Run any necessary database migrations if required

## Troubleshooting

### Common Issues
- **Database Connection**: Verify database credentials and network connectivity
- **File Uploads**: Check file permissions and storage space
- **Performance**: Monitor resource usage and scale accordingly
- **SSL Issues**: Verify certificate configuration and paths

### Debugging
Enable debug mode temporarily for troubleshooting:

```bash
# In .env file
DEBUG=True
```

Remember to disable debug mode in production!