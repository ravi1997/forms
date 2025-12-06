import os
from flask import Flask
from dotenv import load_dotenv
from app.routes.user import user_bp
from app.routes.role import role_bp
from app.routes.account import account_bp
from app.routes.admin import admin_bp
from app.routes.superadmin import superadmin_bp

from app.extensions import db, migrate, bcrypt
from app.config import config

# Load environment variables from .env file
load_dotenv()

def create_app(config_name=None):
    app = Flask(__name__)
    
    # Determine configuration name
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'default')
    
    # Load the appropriate configuration class based on config_name
    config_class = config[config_name]
    app.config.from_object(config_class)
    
    # Initialize extensions after configuration is applied
    db.init_app(app)
    migrate.init_app(app, db)
    bcrypt.init_app(app)
    
    # Run any additional initialization specific to the config
    config_class.init_app(app)
    
    # Register blueprints
    app.register_blueprint(user_bp)
    app.register_blueprint(role_bp)
    app.register_blueprint(account_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(superadmin_bp)

    return app