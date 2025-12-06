from flask import Flask
from app.routes.user import user_bp
from app.routes.role import role_bp
from app.routes.account import account_bp
from app.routes.admin import admin_bp
from app.routes.superadmin import superadmin_bp


def register_routes(app: Flask):
    """Register all blueprints with the Flask application."""
    # Register user routes with /api/v1/users prefix
    app.register_blueprint(user_bp, url_prefix='/api/v1/users')
    
    # Register role routes with /api/v1/roles prefix
    app.register_blueprint(role_bp, url_prefix='/api/v1/roles')
    
    # Register account routes with /api/v1/accounts prefix
    app.register_blueprint(account_bp, url_prefix='/api/v1/accounts')
    
    # Register admin routes with /api/v1/admin prefix
    app.register_blueprint(admin_bp, url_prefix='/api/v1/admin')
    
    # Register superadmin routes with /api/v1/superadmin prefix
    app.register_blueprint(superadmin_bp, url_prefix='/api/v1/superadmin')