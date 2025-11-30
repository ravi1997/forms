from app import db
from app.models import User, UserRoles
from flask import url_for, current_app
from flask_mail import Message

class UserService:
    @staticmethod
    def create_user(data):
        """
        Creates a new user.
        """
        username = data.get('username')
        email = data.get('email')
        password = data.get('password')
        first_name = data.get('first_name', '')
        last_name = data.get('last_name', '')

        if User.query.filter_by(username=username).first():
            return None, "Username already exists"
        
        if User.query.filter_by(email=email).first():
            return None, "Email already registered"

        user = User(
            username=username,
            email=email,
            first_name=first_name,
            last_name=last_name,
            is_verified=False
        )
        user.set_password(password)
        verification_token = user.generate_verification_token()

        db.session.add(user)
        db.session.commit()

        try:
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
            from app import mail
            mail.send(msg)
        except Exception as e:
            current_app.logger.error(f"Failed to send verification email: {str(e)}")

        return user, None

    @staticmethod
    def authenticate_user(data):
        """
        Authenticates a user.
        """
        username = data.get('username')
        password = data.get('password')

        user = User.query.filter_by(username=username).first()

        if not user or not user.check_password(password):
            return None, "Invalid username or password"

        if not user.is_active:
            return None, "Account is disabled"

        if not user.is_verified:
            return None, "Please verify your email before logging in"

        return user, None

    @staticmethod
    def update_user_profile(user_id, data):
        """
        Updates a user's profile.
        """
        user = User.query.get(user_id)
        if not user:
            return None, "User not found"

        first_name = data.get('first_name')
        last_name = data.get('last_name')
        email = data.get('email')
        preferences = data.get('preferences')

        if first_name is not None:
            user.first_name = first_name
        if last_name is not None:
            user.last_name = last_name
        if email is not None:
            existing_user = User.query.filter(User.email == email, User.id != user_id).first()
            if existing_user:
                return None, "Email already registered"
            user.email = email
        if preferences is not None:
            user.preferences = preferences

        db.session.commit()
        return user, None
