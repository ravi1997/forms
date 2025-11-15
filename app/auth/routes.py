from flask import request, jsonify, current_app
from flask_jwt_extended import create_access_token, create_refresh_token, jwt_required, get_jwt_identity, get_jwt
from app import db
from app.auth import bp
from app.models import User
from app.schemas import LoginFormSchema, RegisterFormSchema, UserSchema
from werkzeug.security import check_password_hash
from datetime import datetime
import re

# Schema instances
user_schema = UserSchema()
users_schema = UserSchema(many=True)
login_schema = LoginFormSchema()
register_schema = RegisterFormSchema()

@bp.route('/register', methods=['POST'])
def register():
    """Register a new user account"""
    try:
        # Validate and deserialize input
        errors = register_schema.validate(request.json)
        if errors:
            return jsonify({'error': 'validation_error', 'message': 'Invalid input data', 'details': errors}), 400
        
        # Extract data
        username = request.json.get('username')
        email = request.json.get('email')
        password = request.json.get('password')
        first_name = request.json.get('first_name', '')
        last_name = request.json.get('last_name', '')
        
        # Check if user already exists
        if User.query.filter_by(username=username).first():
            return jsonify({'error': 'username_exists', 'message': 'Username already exists'}), 409
        
        if User.query.filter_by(email=email).first():
            return jsonify({'error': 'email_exists', 'message': 'Email already registered'}), 409
        
        # Create new user
        user = User(
            username=username,
            email=email,
            first_name=first_name,
            last_name=last_name,
            is_verified=False  # Email verification would be implemented in a real app
        )
        user.set_password(password)
        
        # Add to database
        db.session.add(user)
        db.session.commit()
        
        # Return user data (without password)
        result = user_schema.dump(user)
        return jsonify({'message': 'User registered successfully', 'data': result}), 201
    
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Registration error: {str(e)}")
        return jsonify({'error': 'registration_failed', 'message': 'Registration failed'}), 500

@bp.route('/login', methods=['POST'])
def login():
    """Authenticate user and return JWT tokens"""
    try:
        # Validate input
        errors = login_schema.validate(request.json)
        if errors:
            return jsonify({'error': 'validation_error', 'message': 'Invalid input data', 'details': errors}), 40
        
        username = request.json.get('username')
        password = request.json.get('password')
        
        # Find user
        user = User.query.filter_by(username=username).first()
        
        if not user or not user.check_password(password):
            return jsonify({'error': 'invalid_credentials', 'message': 'Invalid username or password'}), 401
        
        if not user.is_active:
            return jsonify({'error': 'account_disabled', 'message': 'Account is disabled'}), 401
        
        # Create tokens
        access_token = create_access_token(identity=user.id)
        refresh_token = create_refresh_token(identity=user.id)
        
        # Update last login
        user.last_login = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'message': 'Login successful',
            'access_token': access_token,
            'refresh_token': refresh_token,
            'user': user_schema.dump(user)
        }), 200
    
    except Exception as e:
        current_app.logger.error(f"Login error: {str(e)}")
        return jsonify({'error': 'login_failed', 'message': 'Login failed'}), 500

@bp.route('/logout', methods=['POST'])
@jwt_required()
def logout():
    """Invalidate user session"""
    # In a real application, you would add the token to a blacklist
    current_user_id = get_jwt_identity()
    current_app.logger.info(f"User {current_user_id} logged out")
    return jsonify({'message': 'Logged out successfully'}), 200

@bp.route('/profile', methods=['GET'])
@jwt_required()
def get_profile():
    """Get current user's profile information"""
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if not user:
            return jsonify({'error': 'user_not_found', 'message': 'User not found'}), 404
        
        return jsonify({'data': user_schema.dump(user)}), 200
    
    except Exception as e:
        current_app.logger.error(f"Profile retrieval error: {str(e)}")
        return jsonify({'error': 'profile_error', 'message': 'Could not retrieve profile'}), 500

@bp.route('/profile', methods=['PUT'])
@jwt_required()
def update_profile():
    """Update current user's profile information"""
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if not user:
            return jsonify({'error': 'user_not_found', 'message': 'User not found'}), 404
        
        # Get update data
        first_name = request.json.get('first_name')
        last_name = request.json.get('last_name')
        email = request.json.get('email')
        preferences = request.json.get('preferences')
        
        # Update fields if provided
        if first_name is not None:
            user.first_name = first_name
        if last_name is not None:
            user.last_name = last_name
        if email is not None:
            # Check if email is already taken by another user
            existing_user = User.query.filter_by(email=email).first()
            if existing_user and existing_user.id != user.id:
                return jsonify({'error': 'email_exists', 'message': 'Email already registered'}), 409
            user.email = email
        if preferences is not None:
            user.preferences = preferences
        
        user.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({'message': 'Profile updated successfully', 'data': user_schema.dump(user)}), 200
    
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Profile update error: {str(e)}")
        return jsonify({'error': 'profile_update_failed', 'message': 'Could not update profile'}), 500

@bp.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    """Refresh access token using refresh token"""
    current_user_id = get_jwt_identity()
    new_token = create_access_token(identity=current_user_id)
    return jsonify({'access_token': new_token}), 200