import pytest
from app import create_app, db
from app.models import User
from app.services.user_service import UserService

@pytest.fixture
def app():
    """Create and configure a new app instance for each test."""
    app = create_app('testing')
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()

def test_create_user(app):
    """
    Test user creation.
    """
    with app.app_context():
        data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'password'
        }
        user, error = UserService.create_user(data)
        assert user is not None
        assert error is None
        assert user.username == 'testuser'
        assert user.email == 'test@example.com'

def test_create_user_duplicate_username(app):
    """
    Test creating a user with a duplicate username.
    """
    with app.app_context():
        data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'password'
        }
        UserService.create_user(data)
        user, error = UserService.create_user(data)
        assert user is None
        assert error == "Username already exists"

def test_create_user_duplicate_email(app):
    """
    Test creating a user with a duplicate email.
    """
    with app.app_context():
        data1 = {
            'username': 'testuser1',
            'email': 'test@example.com',
            'password': 'password'
        }
        UserService.create_user(data1)
        data2 = {
            'username': 'testuser2',
            'email': 'test@example.com',
            'password': 'password'
        }
        user, error = UserService.create_user(data2)
        assert user is None
        assert error == "Email already registered"

def test_authenticate_user(app):
    """
    Test user authentication.
    """
    with app.app_context():
        data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'password'
        }
        UserService.create_user(data)
        user, error = UserService.authenticate_user(data)
        assert user is not None
        assert error is None
        assert user.username == 'testuser'

def test_authenticate_user_invalid_password(app):
    """
    Test user authentication with an invalid password.
    """
    with app.app_context():
        data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'password'
        }
        UserService.create_user(data)
        data['password'] = 'wrongpassword'
        user, error = UserService.authenticate_user(data)
        assert user is None
        assert error == "Invalid username or password"

def test_update_user_profile(app):
    """
    Test updating a user's profile.
    """
    with app.app_context():
        data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'password'
        }
        user, _ = UserService.create_user(data)
        update_data = {
            'first_name': 'Test',
            'last_name': 'User',
            'email': 'new_email@example.com'
        }
        updated_user, error = UserService.update_user_profile(user.id, update_data)
        assert updated_user is not None
        assert error is None
        assert updated_user.first_name == 'Test'
        assert updated_user.last_name == 'User'
        assert updated_user.email == 'new_email@example.com'
