from flask import render_template, jsonify, request, current_app
from app.errors import bp
from app import db
from datetime import datetime
import uuid

def create_api_error_response(error_code, error_type, message, status_code, details=None):
    """Create a standardized API error response"""
    response = {
        'error': {
            'code': error_code,
            'type': error_type,
            'message': message,
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'request_id': request.environ.get('REQUEST_ID', str(uuid.uuid4())),
            'path': request.path,
            'method': request.method
        }
    }

    if details:
        response['error']['details'] = details

    # Log the error for monitoring
    current_app.logger.warning(f"API Error {status_code}: {error_type} - {message} (Request ID: {response['error']['request_id']})")

    return jsonify(response), status_code

@bp.app_errorhandler(400)
def bad_request(error):
    """Handle 400 Bad Request errors"""
    if request.path.startswith('/api/'):
        message = str(error.description) if hasattr(error, 'description') else 'Bad request'
        return create_api_error_response(400, 'bad_request', message, 400)
    return render_template('errors/400.html'), 400

@bp.app_errorhandler(401)
def unauthorized(error):
    """Handle 401 Unauthorized errors"""
    if request.path.startswith('/api/'):
        return create_api_error_response(401, 'unauthorized', 'Authentication required', 401)
    return render_template('errors/401.html'), 401

@bp.app_errorhandler(403)
def forbidden(error):
    """Handle 403 Forbidden errors"""
    if request.path.startswith('/api/'):
        return create_api_error_response(403, 'forbidden', 'Access denied', 403)
    return render_template('errors/403.html'), 403

@bp.app_errorhandler(404)
def not_found(error):
    """Handle 404 Not Found errors"""
    if request.path.startswith('/api/'):
        return create_api_error_response(404, 'not_found', 'Resource not found', 404)
    return render_template('errors/404.html'), 404

@bp.app_errorhandler(405)
def method_not_allowed(error):
    """Handle 405 Method Not Allowed errors"""
    if request.path.startswith('/api/'):
        return create_api_error_response(405, 'method_not_allowed', 'Method not allowed', 405, {
            'allowed_methods': error.valid_methods if hasattr(error, 'valid_methods') else []
        })
    return render_template('errors/405.html'), 405

@bp.app_errorhandler(500)
def internal_error(error):
    """Handle 500 Internal Server errors"""
    db.session.rollback()
    if request.path.startswith('/api/'):
        return create_api_error_response(500, 'internal_error', 'Internal server error', 500)
    return render_template('errors/500.html'), 500