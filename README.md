# Dynamic Form Builder Application

A comprehensive Flask web application with PostgreSQL database for creating, managing, and analyzing dynamic forms similar to Google Forms. The system follows a hybrid approach with both API endpoints and template rendering, supporting real-time analytics and custom visualizations.

## Features

- **Form Management System**: Dynamic form creation with customizable properties, section-based organization, multiple question types, and form templates
- **User Management System**: Role-based access control, user authentication, and profile management
- **Response Collection and Analysis**: Real-time response collection, advanced analytics dashboard, and export functionality
- **Technical Features**: RESTful API, input validation, error handling, secure file uploads, and caching

## Tech Stack

- **Backend**: Flask web framework with PostgreSQL database
- **ORM**: Flask-SQLAlchemy
- **Serialization**: Flask-Marshmallow
- **Database Versioning**: Flask-Migrate
- **Frontend**: Jinja2 templates with Bootstrap 5, Chart.js for visualizations
- **Authentication**: JWT tokens and session-based authentication
- **Background Tasks**: Celery with Redis
- **Deployment**: Docker ready with Gunicorn

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd forms
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration
```

5. Initialize the database:
```bash
flask db init
flask db migrate -m "Initial migration"
flask db upgrade
```

6. Run the application:
```bash
python run.py
```

## Configuration

The application uses a `config.py` file with different configurations for development, testing, and production environments. Key settings include:

- Database URL
- JWT secret key
- Email server settings
- Upload folder configuration
- Redis URL for caching
- Security settings

## Project Structure

```
forms/
├── app/
│   ├── __init__.py          # Application factory
│   ├── models/              # Database models
│   ├── schemas/             # Marshmallow schemas
│   ├── auth/                # Authentication blueprint
│   ├── api/                 # API blueprint
│   ├── forms/               # Form management blueprint
│   ├── responses/           # Response management blueprint
│   ├── analytics/           # Analytics blueprint
│   ├── main/                # Main blueprint
│   └── errors/              # Error handlers
├── migrations/              # Database migrations
├── tests/                   # Test files
├── app/
│   └── templates/           # HTML templates
├── config.py                # Configuration settings
├── requirements.txt         # Dependencies
├── run.py                   # Application entry point
└── README.md
```

## API Endpoints

The application provides comprehensive RESTful API endpoints for all major operations:

- `/auth/` - Authentication (register, login, logout)
- `/api/users/` - User management
- `/api/forms/` - Form management
- `/api/forms/<id>/sections` - Section management
- `/api/sections/<id>/questions` - Question management
- `/api/forms/<id>/responses` - Response management
- `/api/analytics/` - Analytics endpoints

## Database Models

Key models include:
- User: Authentication and user profiles
- Form: Form definitions and settings
- Section: Organizational containers for questions
- Question: Questions with type, validation, and options
- Response: Form submissions with answers
- Answer: Individual answers to questions
- FormTemplate: Reusable form templates
- QuestionLibrary: Reusable questions
- AuditLog: Activity tracking and security logs

## Running Tests

Execute the test suite with pytest:

```bash
pytest tests/
```

Or with coverage:

```bash
pytest tests/ --cov=app
```

## Deployment

The application is designed for containerized deployment with Docker:

```bash
docker-compose up -d
```

For production deployment, ensure you have:
- PostgreSQL database configured
- Redis server for caching and sessions
- Proper environment variables set
- SSL certificates for HTTPS
- Reverse proxy (Nginx) configuration

## Security Considerations

- Passwords are hashed using bcrypt
- JWT tokens with proper expiration
- Input validation and sanitization
- SQL injection prevention through SQLAlchemy
- XSS prevention with Jinja2 autoescaping
- Rate limiting for API endpoints
- Secure file upload validation
- Audit logging for security events

## License

[Specify your license here]