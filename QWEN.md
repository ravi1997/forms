# QWEN.md - Dynamic Form Builder Application Context

## Project Overview

This is a comprehensive Flask web application that functions as a Dynamic Form Builder similar to Google Forms. The system allows users to create, manage, and analyze dynamic forms with a hybrid architecture supporting both traditional web interface and RESTful API endpoints.

**Project Type:** Flask Web Application with PostgreSQL Database
**Primary Purpose:** Dynamic form creation, management, and analytics platform
**Architecture Style:** Hybrid (API + Server-Side Rendered Templates)

## Core Technology Stack

### Backend Technologies
- **Framework:** Flask 2.3.3 (web framework)
- **Database:** PostgreSQL (with SQLAlchemy ORM)
- **ORM:** Flask-SQLAlchemy 3.0.5
- **Serialization:** Flask-Marshmallow 0.15.0 + marshmallow-sqlalchemy 0.29.0
- **Database Migrations:** Flask-Migrate 4.0.5
- **Authentication:** Flask-JWT-Extended 4.5.3 + Flask-Login 0.6.3
- **Form Handling:** Flask-WTF 1.1.1 + WTForms 3.0.1
- **Security:** bcrypt 4.0.1, Flask-CORS 4.0.0, Flask-Limiter 3.5.0
- **Caching:** Flask-Caching with Redis 5.0.0
- **Background Tasks:** Celery 5.3.1
- **Email:** Flask-Mail 0.9.1
- **Testing:** pytest 7.4.2, pytest-flask 1.2.0, pytest-cov 4.1.0
- **Deployment:** Gunicorn 21.2.0, python-dotenv 1.0.0

### Frontend Technologies
- **Template Engine:** Jinja2 (server-side rendering)
- **CSS Framework:** Bootstrap 5
- **JavaScript:** jQuery, vanilla JavaScript
- **Visualizations:** Chart.js/D3.js
- **UI Components:** Dragula or SortableJS for drag-and-drop

### Infrastructure
- **Caching/Session Store:** Redis 5.0.0
- **Background Processing:** Celery + Redis broker
- **Containerization:** Docker ready
- **WSGI Server:** Gunicorn

## Application Architecture

### Main Components
- **`app/`**: Main Flask application package
  - **`__init__.py`**: Application factory with extensions initialization
  - **`models/`**: Database models and relationships
  - **`schemas/`**: Marshmallow schemas for validation and serialization
  - **`auth/`**: Authentication blueprint
  - **`api/`**: REST API endpoints
  - **`forms/`**: Form management blueprint
  - **`responses/`**: Response management blueprint
  - **`analytics/`**: Analytics functionality
  - **`main/`**: Main application routes
  - **`errors/`**: Error handlers

### Key Entry Points
- **`run.py`**: Main application entry point
- **`config.py`**: Configuration settings for different environments
- **`requirements.txt`**: Python dependencies
- **`package.json`**: Frontend dependencies

## Database Structure

### Core Models
- **User**: Authentication, roles (admin/creator/analyst/respondent), profiles
- **Form**: Form metadata, settings, publishing status, owned by users
- **Section**: Organizational containers for questions within forms
- **Question**: Questions with type enumeration, validation, options
- **Response**: Form submissions with metadata (IP, user agent, timestamp)
- **Answer**: Individual answers to questions within responses
- **FormTemplate**: Reusable form templates
- **QuestionLibrary**: Reusable questions
- **AuditLog**: Activity tracking for security and compliance

### Question Types
Enum values: text, long_text, multiple_choice, checkbox, dropdown, rating, file_upload, date, email, number

## API Structure

### Main Endpoints
- **`/auth/`**: Authentication (register, login, profile, refresh, forgot/reset password)
- **`/api/`**: Main API (users, forms, sections, questions, responses, analytics)
- **`/forms/`**: Form-related routes
- **`/responses/``: Response-related routes
- **`/analytics/`**: Analytics routes

### Authentication Methods
- JWT tokens for API authentication (15 min access, 7 day refresh)
- Session-based for web interface
- Dual authentication system supporting both approaches

## Configuration Management

### Environment Support
- **Development**: SQLite database, HTTP sessions allowed
- **Testing**: SQLite database, CSRF disabled
- **Production**: PostgreSQL database, HTTPS enforced

### Key Configuration Settings
- Database connections with pooling
- JWT token configuration
- Email server settings
- File upload limits (16MB max)
- Redis configuration for caching and sessions
- Security headers and logging settings

## Security Features

- Password hashing with bcrypt
- JWT tokens with proper expiration
- Input validation and sanitization (Marshmallow schemas)
- SQL injection prevention through SQLAlchemy
- XSS prevention with Jinja2 autoescaping
- Rate limiting (2000/day, 500/hour default)
- File upload validation
- Comprehensive audit logging
- CSRF protection

## Running and Development Commands

### Basic Setup
```bash
# 1. Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Set up environment
cp .env.example .env
# Edit .env with your configuration

# 4. Initialize database
flask db init
flask db migrate -m "Initial migration"
flask db upgrade

# 5. Run application
python run.py
```

### Testing
```bash
# Run all tests
pytest tests/

# Run with coverage
pytest tests/ --cov=app
```

### Development Conventions
- Follow PEP 8 Python coding standards
- Use Marshmallow schemas for request validation
- Implement proper logging with structured format
- Include audit logging for security events
- Use request ID for traceability
- Implement rate limiting for API endpoints

### Project Structure
The application follows a modular Flask structure with blueprints for different functionality areas. Each blueprint contains its own routes, templates, and static files where appropriate.

## Key Files and Directories

- **`app/__init__.py`**: Application factory and core configuration
- **`run.py`**: Application entry point
- **`config.py`**: Environment-specific configuration
- **`app/models/__init__.py`**: Database models and relationships
- **`app/schemas/__init__.py`**: Marshmallow schemas
- **`app/api/routes.py`**: REST API endpoints
- **`app/auth/routes.py`**: Authentication endpoints
- **`requirements.txt`**: Python dependencies
- **`logs/`**: Application log files
- **`migrations/`**: Database migration files
- **`uploads/`**: File upload storage
- **`tests/`**: Test files
- **`ARCHITECTURE.md`**: System architecture documentation
- **`TECHNICAL_DOCUMENTATION.md`**: Comprehensive technical documentation

## Special Considerations

1. **Security**: The application has a comprehensive security model with authentication, authorization, and audit logging.
2. **Performance**: Utilizes Redis for caching, background processing with Celery, and proper database indexing.
3. **Scalability**: Designed for horizontal scaling with stateless application servers and distributed caching.
4. **Monitoring**: Includes comprehensive logging with request IDs for traceability and monitoring.
5. **API Versioning**: RESTful API design with proper status codes and error handling.

When working with this codebase, remember to maintain security best practices, follow the existing patterns for error handling and validation, and ensure proper audit logging for security-sensitive operations.