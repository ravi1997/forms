from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_marshmallow import Marshmallow
from flask_login import LoginManager
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from flask_mail import Mail
from celery import Celery
from config import config
import os

# Initialize extensions
db = SQLAlchemy()
migrate = Migrate()
ma = Marshmallow()
login_manager = LoginManager()
jwt = JWTManager()
cors = CORS()
mail = Mail()

# Initialize Celery
celery = Celery()

def create_app(config_name='default'):
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    
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
    
    # Initialize Celery with Flask app context
    class ContextTask(celery.Task):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)
    
    celery.Task = ContextTask
    
    return app

from app import models, tasks