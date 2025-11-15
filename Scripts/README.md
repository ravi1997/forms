# Scripts Directory

This directory contains utility scripts to help with development, deployment, maintenance, and troubleshooting of the Dynamic Form Builder application.

## Available Scripts

### Main Scripts (Root Directory)

#### `setup.sh`
**Purpose**: One-time setup script for initializing the development environment.

**Usage**:
```bash
./setup.sh
```

**What it does**:
- Checks system requirements
- Creates Python virtual environment
- Installs all dependencies
- Sets up environment configuration
- Initializes database
- Creates admin user
- Runs initial tests

#### `run.sh`
**Purpose**: Main execution script for running the application.

**Usage**:
```bash
./run.sh [command] [options]
```

**Commands**:
- (no command): Start the Flask application
- `migrate`: Run database migrations
- `test`: Run test suite
- `shell`: Start Flask shell
- `help`: Show help

**Examples**:
```bash
./run.sh                    # Start development server
./run.sh test --coverage    # Run tests with coverage
./run.sh migrate           # Run database migrations
```

### Development Scripts

#### `Scripts/dev.sh`
**Purpose**: Development helper script with common development tasks.

**Usage**:
```bash
./Scripts/dev.sh <command> [options]
```

**Commands**:
- `start`: Start development server
- `test`: Run tests with options (--coverage, --watch)
- `lint`: Run code linting
- `format`: Format code with black
- `migrate`: Run/create database migrations
- `reset-db`: Reset database (WARNING: deletes all data)
- `shell`: Start Flask shell
- `quality`: Run all quality checks
- `hooks`: Setup pre-commit hooks
- `branch <name>`: Create new feature branch
- `status`: Show development environment status

**Examples**:
```bash
./Scripts/dev.sh start
./Scripts/dev.sh test --coverage
./Scripts/dev.sh branch user-authentication
./Scripts/dev.sh quality
```

### Database Management

#### `Scripts/database.sh`
**Purpose**: Database management and backup/restore operations.

**Usage**:
```bash
./Scripts/database.sh <command> [options]
```

**Commands**:
- `backup`: Create database backup
- `restore <file>`: Restore database from backup
- `reset`: Reset database (delete all data)
- `info`: Show database information
- `migrate`: Run pending migrations
- `create <msg>`: Create new migration

**Examples**:
```bash
./Scripts/database.sh backup
./Scripts/database.sh restore backups/sqlite_backup_20231115.db.gz
./Scripts/database.sh create "add user preferences"
```

### Maintenance Scripts

#### `Scripts/maintenance.sh`
**Purpose**: System maintenance, cleanup, and health checks.

**Usage**:
```bash
./Scripts/maintenance.sh <command> [options]
```

**Commands**:
- `cleanup`: Clean up old files (logs, uploads, backups)
- `logs [days]`: Clean up old log files
- `uploads [days]`: Clean up old uploaded files
- `backups [days]`: Clean up old backup files
- `cache`: Clean up Python cache files
- `sessions`: Clean up old session files
- `health`: Run system health check
- `disk`: Show disk usage information
- `optimize`: Optimize database

**Examples**:
```bash
./Scripts/maintenance.sh cleanup
./Scripts/maintenance.sh health
./Scripts/maintenance.sh disk
```

### Deployment Scripts

#### `Scripts/deploy.sh`
**Purpose**: Production deployment and server configuration.

**Usage**:
```bash
./Scripts/deploy.sh <command> [options]
```

**Commands**:
- `setup`: Setup production environment
- `nginx <domain>`: Setup Nginx configuration
- `ssl <domain>`: Setup SSL certificate
- `deploy`: Deploy the application
- `service`: Create systemd service
- `logs`: Setup log rotation
- `monitor`: Setup basic monitoring
- `status`: Show deployment status
- `full <domain>`: Run full deployment

**Examples**:
```bash
./Scripts/deploy.sh setup
./Scripts/deploy.sh full mydomain.com
./Scripts/deploy.sh status
```

### System Check Scripts

#### `Scripts/check.sh`
**Purpose**: System requirements checking and troubleshooting.

**Usage**:
```bash
./Scripts/check.sh [command]
```

**Commands**:
- `all`: Run all checks (default)
- `os`: Check operating system
- `python`: Check Python installation
- `deps`: Check system dependencies
- `project`: Check project structure
- `venv`: Check virtual environment
- `env`: Check environment configuration
- `database`: Check database
- `permissions`: Check file permissions
- `disk`: Check disk space
- `troubleshoot`: Show troubleshooting tips

**Examples**:
```bash
./Scripts/check.sh all
./Scripts/check.sh troubleshoot
```

## Quick Start Guide

### For New Developers

1. **Initial Setup**:
   ```bash
   ./setup.sh
   ```

2. **Start Development**:
   ```bash
   ./run.sh
   ```

3. **Check Everything is Working**:
   ```bash
   ./Scripts/check.sh all
   ```

### For Production Deployment

1. **Setup Production Environment**:
   ```bash
   ./Scripts/deploy.sh setup
   ```

2. **Full Deployment**:
   ```bash
   ./Scripts/deploy.sh full yourdomain.com
   ```

3. **Check Deployment Status**:
   ```bash
   ./Scripts/deploy.sh status
   ```

### Common Development Tasks

- **Run Tests**: `./run.sh test` or `./Scripts/dev.sh test --coverage`
- **Format Code**: `./Scripts/dev.sh format`
- **Database Backup**: `./Scripts/database.sh backup`
- **System Health**: `./Scripts/maintenance.sh health`
- **Create Feature Branch**: `./Scripts/dev.sh branch feature-name`

## Script Dependencies

Most scripts require:
- Bash shell
- Python 3.8+
- Basic Unix tools (grep, sed, awk, etc.)

Some scripts have additional requirements:
- `deploy.sh`: Requires sudo access for system configuration
- Database scripts: May require PostgreSQL client tools
- Development scripts: May install additional Python packages

## Troubleshooting

If scripts fail to run:
1. Ensure scripts are executable: `chmod +x *.sh Scripts/*.sh`
2. Check system requirements: `./Scripts/check.sh all`
3. Review error messages and logs
4. Use troubleshooting tips: `./Scripts/check.sh troubleshoot`

## Contributing

When adding new scripts:
1. Follow the existing naming and structure conventions
2. Include comprehensive help text
3. Add error handling and user-friendly messages
4. Update this README with the new script information
5. Test on both Linux and macOS if possible