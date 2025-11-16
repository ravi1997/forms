from flask import request, jsonify, current_app, render_template, session
from flask_jwt_extended import create_access_token, create_refresh_token, jwt_required, get_jwt_identity, get_jwt
from app import db, limiter
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

@bp.route('/register', methods=['GET', 'POST'])
@limiter.limit("5 per hour")
def register():
    """Register a new user account"""
    if request.method == 'GET':
        return render_template('auth/register.html')

    try:
        # Determine input type
        if request.is_json:
            data = request.json
        else:
            data = request.form.to_dict()

        # Validate and deserialize input
        errors = register_schema.validate(data)
        if errors:
            if request.is_json:
                return jsonify({'error': 'validation_error', 'message': 'Invalid input data', 'details': errors}), 400
            else:
                # For form, flash errors or redirect
                # For simplicity, redirect back with errors
                from flask import flash, redirect, url_for
                for field, msgs in errors.items():
                    flash(f"{field}: {'; '.join(msgs)}", 'error')
                return redirect(url_for('auth.register'))

        # Extract data
        username = data.get('username')
        email = data.get('email')
        password = data.get('password')
        first_name = data.get('first_name', '')
        last_name = data.get('last_name', '')
        
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
            is_verified=False
        )
        user.set_password(password)

        # Generate email verification token
        verification_token = user.generate_verification_token()

        # Add to database
        db.session.add(user)
        db.session.commit()

        # Send verification email
        try:
            from flask_mail import Message
            from app import mail
            from flask import current_app

            verification_url = url_for('auth.verify_email', token=verification_token, _external=True)
            msg = Message('Email Verification - Form Builder',
                         sender=current_app.config['MAIL_DEFAULT_SENDER'],
                         recipients=[user.email])
            msg.body = f'''Hi {user.username},

Thank you for registering with Form Builder!

Please click the following link to verify your email address:
{verification_url}

This link will expire in 24 hours.

If you didn't create an account, please ignore this email.

Best regards,
The Form Builder Team
'''
            mail.send(msg)
        except Exception as e:
            current_app.logger.error(f"Failed to send verification email: {str(e)}")
            # Don't fail registration if email fails, but log it

        # Return user data (without password)
        result = user_schema.dump(user)
        if request.is_json:
            return jsonify({'message': 'User registered successfully. Please check your email to verify your account.', 'data': result}), 201
        else:
            from flask import flash, redirect, url_for
            flash('Registration successful! Please check your email to verify your account.', 'success')
            return redirect(url_for('auth.login'))
    
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Registration error: {str(e)}")
        return jsonify({'error': 'registration_failed', 'message': 'Registration failed'}), 500

@bp.route('/login', methods=['GET', 'POST'])
@limiter.limit("10 per minute")
def login():
    """Authenticate user and return JWT tokens"""
    if request.method == 'GET':
        return render_template('auth/login.html')

    try:
        # Determine input type
        if request.is_json:
            data = request.json
        else:
            data = request.form.to_dict()

        # Validate input
        errors = login_schema.validate(data)
        if errors:
            if request.is_json:
                return jsonify({'error': 'validation_error', 'message': 'Invalid input data', 'details': errors}), 400
            else:
                from flask import flash, redirect, url_for
                flash('Invalid username or password', 'error')
                return redirect(url_for('auth.login'))

        username = data.get('username')
        password = data.get('password')
        
        # Find user
        user = User.query.filter_by(username=username).first()
        
        if not user or not user.check_password(password):
            if request.is_json:
                return jsonify({'error': 'invalid_credentials', 'message': 'Invalid username or password'}), 401
            else:
                from flask import flash, redirect, url_for
                flash('Invalid username or password', 'error')
                return redirect(url_for('auth.login'))

        if not user.is_active:
            if request.is_json:
                return jsonify({'error': 'account_disabled', 'message': 'Account is disabled'}), 401
            else:
                flash('Account is disabled', 'error')
                return redirect(url_for('auth.login'))

        if not user.is_verified:
            if request.is_json:
                return jsonify({'error': 'email_not_verified', 'message': 'Please verify your email before logging in'}), 401
            else:
                flash('Please verify your email before logging in', 'error')
                return redirect(url_for('auth.login'))
        
        # Create tokens
        access_token = create_access_token(identity=user.id)
        refresh_token = create_refresh_token(identity=user.id)
        
        # Update last login
        user.last_login = datetime.utcnow()
        db.session.commit()
        
        if request.is_json:
            return jsonify({
                'message': 'Login successful',
                'access_token': access_token,
                'refresh_token': refresh_token,
                'user': user_schema.dump(user)
            }), 200
        else:
            from flask import session, redirect, url_for
            session['access_token'] = access_token
            session['refresh_token'] = refresh_token
            session['user'] = user_schema.dump(user)
            return redirect(url_for('main.dashboard'))
    
    except Exception as e:
        current_app.logger.error(f"Login error: {str(e)}")
        return jsonify({'error': 'login_failed', 'message': 'Login failed'}), 500

@bp.route('/logout', methods=['GET', 'POST'])
def logout():
    """Invalidate user session"""
    from flask import session, redirect, url_for, flash
    # Clear session
    session.clear()
    flash('Logged out successfully', 'success')
    return redirect(url_for('main.index'))

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

@bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    """Handle forgot password requests"""
    if request.method == 'GET':
        return render_template('auth/forgot_password.html')

    try:
        # Determine input type
        if request.is_json:
            data = request.json
        else:
            data = request.form.to_dict()

        email = data.get('email')
        if not email:
            if request.is_json:
                return jsonify({'error': 'validation_error', 'message': 'Email is required'}), 400
            else:
                from flask import flash, redirect, url_for
                flash('Email is required', 'error')
                return redirect(url_for('auth.forgot_password'))

        # Find user by email
        user = User.query.filter_by(email=email).first()
        if not user:
            # Don't reveal if email exists or not for security
            if request.is_json:
                return jsonify({'message': 'If the email exists, a password reset link has been sent'}), 200
            else:
                from flask import flash, redirect, url_for
                flash('If the email exists, a password reset link has been sent', 'info')
                return redirect(url_for('auth.login'))

        # Generate reset token
        reset_token = user.generate_reset_token()
        db.session.commit()

        # Send reset email
        from flask_mail import Message
        from app import mail
        from flask import current_app

        reset_url = url_for('auth.reset_password', token=reset_token, _external=True)
        msg = Message('Password Reset Request',
                     sender=current_app.config['MAIL_DEFAULT_SENDER'],
                     recipients=[user.email])
        msg.body = f'''Hi {user.username},

You requested a password reset for your account.

Please click the following link to reset your password:
{reset_url}

This link will expire in 1 hour.

If you didn't request this reset, please ignore this email.

Best regards,
The Form Builder Team
'''
        mail.send(msg)

        if request.is_json:
            return jsonify({'message': 'Password reset link sent to your email'}), 200
        else:
            from flask import flash, redirect, url_for
            flash('Password reset link sent to your email', 'success')
            return redirect(url_for('auth.login'))

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Forgot password error: {str(e)}")
        return jsonify({'error': 'forgot_password_failed', 'message': 'Failed to process request'}), 500

@bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    """Handle password reset"""
    if request.method == 'GET':
        # Verify token is valid
        user = User.query.filter_by(password_reset_token=token).first()
        if not user or not user.verify_reset_token(token):
            from flask import flash, redirect, url_for
            flash('Invalid or expired reset token', 'error')
            return redirect(url_for('auth.login'))
        return render_template('auth/reset_password.html', token=token)

    try:
        # Determine input type
        if request.is_json:
            data = request.json
        else:
            data = request.form.to_dict()

        password = data.get('password')
        confirm_password = data.get('confirm_password')
        token = data.get('token') or request.form.get('token')

        if not password or not confirm_password:
            if request.is_json:
                return jsonify({'error': 'validation_error', 'message': 'Password and confirmation are required'}), 400
            else:
                from flask import flash, redirect, url_for
                flash('Password and confirmation are required', 'error')
                return redirect(url_for('auth.reset_password', token=token))

        if password != confirm_password:
            if request.is_json:
                return jsonify({'error': 'validation_error', 'message': 'Passwords do not match'}), 400
            else:
                from flask import flash, redirect, url_for
                flash('Passwords do not match', 'error')
                return redirect(url_for('auth.reset_password', token=token))

        if len(password) < 8:
            if request.is_json:
                return jsonify({'error': 'validation_error', 'message': 'Password must be at least 8 characters'}), 400
            else:
                from flask import flash, redirect, url_for
                flash('Password must be at least 8 characters', 'error')
                return redirect(url_for('auth.reset_password', token=token))

        # Find user by token
        user = User.query.filter_by(password_reset_token=token).first()
        if not user or not user.verify_reset_token(token):
            if request.is_json:
                return jsonify({'error': 'invalid_token', 'message': 'Invalid or expired reset token'}), 400
            else:
                from flask import flash, redirect, url_for
                flash('Invalid or expired reset token', 'error')
                return redirect(url_for('auth.login'))

        # Update password and clear reset token
        user.set_password(password)
        user.clear_reset_token()
        user.updated_at = datetime.utcnow()
        db.session.commit()

        if request.is_json:
            return jsonify({'message': 'Password reset successfully'}), 200
        else:
            from flask import flash, redirect, url_for
            flash('Password reset successfully! Please login with your new password.', 'success')
            return redirect(url_for('auth.login'))

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Reset password error: {str(e)}")
        return jsonify({'error': 'reset_failed', 'message': 'Failed to reset password'}), 500

@bp.route('/verify-email/<token>', methods=['GET', 'POST'])
def verify_email(token):
    """Handle email verification"""
    if request.method == 'GET':
        # Verify token is valid
        user = User.query.filter_by(email_verification_token=token).first()
        if not user or not user.verify_email_token(token):
            from flask import flash, redirect, url_for
            flash('Invalid or expired verification token', 'error')
            return redirect(url_for('auth.login'))
        return render_template('auth/verify_email.html', token=token)

    try:
        # Determine input type
        if request.is_json:
            data = request.json
        else:
            data = request.form.to_dict()

        token = data.get('token') or request.form.get('token')

        # Find user by token
        user = User.query.filter_by(email_verification_token=token).first()
        if not user or not user.verify_email_token(token):
            if request.is_json:
                return jsonify({'error': 'invalid_token', 'message': 'Invalid or expired verification token'}), 400
            else:
                from flask import flash, redirect, url_for
                flash('Invalid or expired verification token', 'error')
                return redirect(url_for('auth.login'))

        # Verify the user
        user.is_verified = True
        user.clear_verification_token()
        user.updated_at = datetime.utcnow()
        db.session.commit()

        if request.is_json:
            return jsonify({'message': 'Email verified successfully'}), 200
        else:
            from flask import flash, redirect, url_for
            flash('Email verified successfully! You can now login.', 'success')
            return redirect(url_for('auth.login'))

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Email verification error: {str(e)}")
        return jsonify({'error': 'verification_failed', 'message': 'Failed to verify email'}), 500