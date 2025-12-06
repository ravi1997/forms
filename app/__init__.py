from flask import Flask
from app.routes.user import user_bp
from app.routes.role import role_bp
from app.routes.account import account_bp
from app.routes.admin import admin_bp

from app.extensions import db, migrate, bcrypt


def create_app():
    app = Flask(__name__)
    
    db.init_app(app)
    migrate.init_app(app, db)
    bcrypt.init_app(app)
    
    # Register blueprints
    app.register_blueprint(user_bp)
    app.register_blueprint(role_bp)
    app.register_blueprint(account_bp)
    app.register_blueprint(admin_bp)

    return app