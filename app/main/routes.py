from flask import render_template, request, jsonify, current_app, session, redirect, url_for
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import db
from app.main import bp
from app.models import User, Form

@bp.route('/')
def index():
    """Main landing page"""
    # Get published forms to show to anonymous users
    published_forms = Form.query.filter_by(is_published=True, is_archived=False).limit(6).all()
    
    # If user is logged in, also get their forms
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        user_forms = Form.query.filter_by(created_by=current_user_id).limit(6).all()
        return render_template('main/index.html', published_forms=published_forms, user_forms=user_forms, user=user)
    except:
        # User not logged in
        return render_template('main/index.html', published_forms=published_forms)

@bp.route('/dashboard')
def dashboard():
    """User dashboard"""
    # Try JWT first (API)
    try:
        current_user_id = get_jwt_identity()
    except:
        # Check session (web)
        if 'user' not in session:
            from flask import flash
            flash('Please login to access the dashboard', 'error')
            return redirect(url_for('auth.login'))
        user_data = session['user']
        current_user_id = user_data['id']
    
    user = User.query.get_or_404(current_user_id)
    
    # Get user's forms
    forms = Form.query.filter_by(created_by=current_user_id).all()
    
    # Get stats
    total_forms = len(forms)
    published_forms = Form.query.filter_by(created_by=current_user_id, is_published=True).count()
    draft_forms = Form.query.filter_by(created_by=current_user_id, is_published=False, is_archived=False).count()
    archived_forms = Form.query.filter_by(created_by=current_user_id, is_archived=True).count()
    
    # Get recent forms
    recent_forms = Form.query.filter_by(created_by=current_user_id).order_by(Form.created_at.desc()).limit(5).all()
    
    return render_template('main/dashboard.html',
                          user=user,
                          total_forms=total_forms,
                          published_forms=published_forms,
                          draft_forms=draft_forms,
                          archived_forms=archived_forms,
                          recent_forms=recent_forms)

@bp.route('/profile')
def profile():
    """User profile page"""
    # Try JWT first (API)
    try:
        current_user_id = get_jwt_identity()
    except:
        # Check session (web)
        if 'user' not in session:
            from flask import flash
            flash('Please login to access your profile', 'error')
            return redirect(url_for('auth.login'))
        user_data = session['user']
        current_user_id = user_data['id']
    
    user = User.query.get_or_404(current_user_id)
    
    return render_template('main/profile.html', user=user)

@bp.route('/search', methods=['GET'])
def search():
    """Search for forms"""
    query = request.args.get('q', '')
    
    if query:
        # Search in form titles and descriptions
        forms = Form.query.filter(
            Form.is_published == True,
            Form.is_archived == False
        ).filter(
            Form.title.contains(query) | Form.description.contains(query)
        ).all()
    else:
        forms = []
    
    return render_template('main/search.html', forms=forms, query=query)

@bp.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': current_app.config.get('START_TIME', 'unknown')
    })