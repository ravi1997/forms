from flask import render_template, request, jsonify, current_app, session, redirect, url_for
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import db
from app.admin import bp
from app.models import User, Form, Response, UserRoles
from datetime import datetime
from app.utils.helpers import log_route

def admin_dashboard():
@bp.route('/', methods=['GET'])
@log_route
def admin_dashboard():
    """Admin dashboard"""
    # Try JWT first (API)
    try:
        current_user_id = get_jwt_identity()
    except:
        # Check session (web)
        if 'user' not in session:
            from flask import flash
            flash('Please login to access admin panel', 'error')
            return redirect(url_for('auth.login'))
        user_data = session['user']
        current_user_id = user_data['id']

    user = User.query.get_or_404(current_user_id)

    if user.role != UserRoles.ADMIN:
        from flask import flash
        flash('Access denied', 'error')
        return redirect(url_for('main.dashboard'))

    # Get admin stats
    total_users = User.query.count()
    total_forms = Form.query.count()
    total_responses = Response.query.count()
    recent_users = User.query.order_by(User.created_at.desc()).limit(5).all()

    return render_template('admin/dashboard.html',
                         total_users=total_users,
                         total_forms=total_forms,
                         total_responses=total_responses,
                         recent_users=recent_users)

def manage_users():
@bp.route('/users', methods=['GET'])
@log_route
def manage_users():
    """User management page"""
    # Try JWT first (API)
    try:
        current_user_id = get_jwt_identity()
    except:
        # Check session (web)
        if 'user' not in session:
            from flask import flash
            flash('Please login to access admin panel', 'error')
            return redirect(url_for('auth.login'))
        user_data = session['user']
        current_user_id = user_data['id']

    user = User.query.get_or_404(current_user_id)

    if user.role != UserRoles.ADMIN:
        from flask import flash
        flash('Access denied', 'error')
        return redirect(url_for('main.dashboard'))

    page = request.args.get('page', 1, type=int)
    per_page = 20

    users = User.query.paginate(page=page, per_page=per_page, error_out=False)

    return render_template('admin/users.html', users=users)

def edit_user(user_id):
@bp.route('/users/<int:user_id>/edit', methods=['GET', 'POST'])
@log_route
def edit_user(user_id):
    """Edit user details"""
    # Try JWT first (API)
    try:
        current_user_id = get_jwt_identity()
    except:
        # Check session (web)
        if 'user' not in session:
            from flask import flash
            flash('Please login to access admin panel', 'error')
            return redirect(url_for('auth.login'))
        user_data = session['user']
        current_user_id = user_data['id']

    admin_user = User.query.get_or_404(current_user_id)

    if admin_user.role != UserRoles.ADMIN:
        from flask import flash
        flash('Access denied', 'error')
        return redirect(url_for('main.dashboard'))

    user = User.query.get_or_404(user_id)

    if request.method == 'GET':
        return render_template('admin/edit_user.html', user=user)

    # Handle POST request
    role = request.form.get('role')
    is_active = 'is_active' in request.form

    if role in [r.value for r in UserRoles]:
        user.role = UserRoles(role)

    user.is_active = is_active
    user.updated_at = datetime.utcnow()

    db.session.commit()

    from flask import flash
    flash('User updated successfully', 'success')
    return redirect(url_for('admin.edit_user', user_id=user_id))

def delete_user(user_id):
@bp.route('/users/<int:user_id>/delete', methods=['POST'])
@log_route
def delete_user(user_id):
    """Delete user"""
    # Try JWT first (API)
    try:
        current_user_id = get_jwt_identity()
    except:
        # Check session (web)
        if 'user' not in session:
            from flask import flash
            flash('Please login to access admin panel', 'error')
            return redirect(url_for('auth.login'))
        user_data = session['user']
        current_user_id = user_data['id']

    admin_user = User.query.get_or_404(current_user_id)

    if admin_user.role != UserRoles.ADMIN:
        from flask import flash
        flash('Access denied', 'error')
        return redirect(url_for('main.dashboard'))

    user = User.query.get_or_404(user_id)

    # Prevent deleting self
    if user.id == current_user_id:
        from flask import flash
        flash('Cannot delete your own account', 'error')
        return redirect(url_for('admin.manage_users'))

    db.session.delete(user)
    db.session.commit()

    from flask import flash
    flash('User deleted successfully', 'success')
    return redirect(url_for('admin.manage_users'))