from functools import wraps
from flask import request, jsonify, session, flash, redirect, url_for
from flask_jwt_extended import get_jwt_identity
from app.models import User, Form

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_id = None
        if get_jwt_identity():
            user_id = get_jwt_identity()
        elif 'user' in session:
            user_id = session['user'].get('id')

        if not user_id:
            if request.is_json:
                return jsonify({'error': 'authentication_required', 'message': 'Authentication is required to access this resource.'}), 401
            flash('Authentication is required to access this resource.', 'error')
            return redirect(url_for('auth.login'))

        kwargs['current_user_id'] = user_id
        return f(*args, **kwargs)
    return decorated_function

def roles_required(roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user_id = kwargs.get('current_user_id')
            user = User.query.get(user_id)
            if not user or user.role.value not in roles:
                if request.is_json:
                    return jsonify({'error': 'forbidden', 'message': 'You do not have permission to perform this action.'}), 403
                flash('You do not have permission to perform this action.', 'error')
                return redirect(url_for('main.dashboard'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def form_owner_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_id = kwargs.get('current_user_id')
        form_id = kwargs.get('form_id')
        form = Form.query.get_or_404(form_id)
        if form.created_by != user_id:
            if request.is_json:
                return jsonify({'error': 'forbidden', 'message': 'You do not have permission to access this form.'}), 403
            flash('You do not have permission to access this form.', 'error')
            return redirect(url_for('main.dashboard'))
        kwargs['form'] = form
        return f(*args, **kwargs)
    return decorated_function
