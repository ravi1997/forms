from flask import Flask, request, g
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_marshmallow import Marshmallow
from flask_login import LoginManager
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from flask_mail import Mail
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_caching import Cache
from celery import Celery
from config import config
import os
import logging
import uuid
from datetime import datetime

# Initialize extensions
db = SQLAlchemy()
migrate = Migrate()
ma = Marshmallow()
login_manager = LoginManager()
jwt = JWTManager()
cors = CORS()
mail = Mail()
csrf = CSRFProtect()
limiter = Limiter(key_func=get_remote_address, default_limits=["2000 per day", "500 per hour"],storage_uri="redis://localhost:6379",
    storage_options={"socket_connect_timeout": 30},
    strategy="fixed-window"
    )
cache = Cache()

# Initialize Celery
celery = Celery()

def create_app(config_name='default'):
    app = Flask(__name__)
    app.config.from_object(config[config_name])

    # Configure logging
    configure_logging(app)

    # Ensure upload folder exists
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    # Initialize extensions with app
    db.init_app(app)
    migrate.init_app(app, db)
    ma.init_app(app)
    login_manager.init_app(app)
    jwt.init_app(app)
    cors.init_app(app)
    mail.init_app(app)
    csrf.init_app(app)
    limiter.init_app(app)
    cache.init_app(app)

    # Configure Celery
    celery.conf.update(
        broker_url=app.config['REDIS_URL'],
        result_backend=app.config['REDIS_URL'],
        task_serializer='json',
        accept_content=['json'],
        result_serializer='json',
        timezone='UTC',
        enable_utc=True,
    )

    # Set login view for Flask-Login
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'

    # Request ID middleware
    @app.before_request
    def set_request_id():
        g.request_id = str(uuid.uuid4())
        request.environ['REQUEST_ID'] = g.request_id

    # Request logging middleware
    @app.after_request
    def log_request(response):
        if hasattr(g, 'request_id'):
            app.logger.info(f"Request {g.request_id}: {request.method} {request.path} - Status: {response.status_code}")
        return response

    # Import and register blueprints
    from app.main import bp as main_bp
    app.register_blueprint(main_bp)

    from app.auth import bp as auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')

    from app.api import bp as api_bp
    app.register_blueprint(api_bp, url_prefix='/api')

    from app.forms import bp as forms_bp
    app.register_blueprint(forms_bp, url_prefix='/forms')

    from app.responses import bp as responses_bp
    app.register_blueprint(responses_bp, url_prefix='/responses')

    from app.analytics import bp as analytics_bp
    app.register_blueprint(analytics_bp, url_prefix='/analytics')

    # Register error handlers
    from app.errors import bp as errors_bp
    app.register_blueprint(errors_bp)

    # Context processor for current user
    @app.context_processor
    def inject_current_user():
        from flask import session
        user = session.get('user')
        return {'current_user': user}

    # Initialize Celery with Flask app context
    class ContextTask(celery.Task):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)

    celery.Task = ContextTask

    return app

def configure_logging(app):
    """Configure application logging"""
    # Set up basic logging configuration
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Create logs directory if it doesn't exist
    log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'logs')
    os.makedirs(log_dir, exist_ok=True)

    # File handler for all logs
    file_handler = logging.FileHandler(os.path.join(log_dir, 'app.log'))
    file_handler.setLevel(logging.INFO)
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    file_handler.setFormatter(file_formatter)

    # Error file handler
    error_file_handler = logging.FileHandler(os.path.join(log_dir, 'error.log'))
    error_file_handler.setLevel(logging.ERROR)
    error_file_handler.setFormatter(file_formatter)

    # Add handlers to app logger
    app.logger.addHandler(file_handler)
    app.logger.addHandler(error_file_handler)

    # Set Flask's werkzeug logger to WARNING to reduce noise
    werkzeug_logger = logging.getLogger('werkzeug')
    werkzeug_logger.setLevel(logging.WARNING)

    app.logger.info("Application logging configured")

from app import models, tasks