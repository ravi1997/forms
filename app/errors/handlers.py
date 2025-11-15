from flask import render_template, jsonify, request
from app.errors import bp
from app import db

@bp.app_errorhandler(400)
def bad_request(error):
    """Handle 400 Bad Request errors"""
    if request.path.startswith('/api/'):
        return jsonify({'error': 'bad_request', 'message': str(error.description) if hasattr(error, 'description') else 'Bad request'}), 400
    return render_template('errors/400.html'), 400

@bp.app_errorhandler(401)
def unauthorized(error):
    """Handle 401 Unauthorized errors"""
    if request.path.startswith('/api/'):
        return jsonify({'error': 'unauthorized', 'message': 'Authentication required'}), 401
    return render_template('errors/401.html'), 401

@bp.app_errorhandler(403)
def forbidden(error):
    """Handle 403 Forbidden errors"""
    if request.path.startswith('/api/'):
        return jsonify({'error': 'forbidden', 'message': 'Access denied'}), 403
    return render_template('errors/403.html'), 403

@bp.app_errorhandler(404)
def not_found(error):
    """Handle 404 Not Found errors"""
    if request.path.startswith('/api/'):
        return jsonify({'error': 'not_found', 'message': 'Resource not found'}), 404
    return render_template('errors/404.html'), 404

@bp.app_errorhandler(405)
def method_not_allowed(error):
    """Handle 405 Method Not Allowed errors"""
    if request.path.startswith('/api/'):
        return jsonify({'error': 'method_not_allowed', 'message': 'Method not allowed'}), 405
    return render_template('errors/405.html'), 405

@bp.app_errorhandler(500)
def internal_error(error):
    """Handle 500 Internal Server errors"""
    db.session.rollback()
    if request.path.startswith('/api/'):
        return jsonify({'error': 'internal_error', 'message': 'Internal server error'}), 500
    return render_template('errors/500.html'), 500