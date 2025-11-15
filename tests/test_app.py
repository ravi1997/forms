import pytest
from app import create_app, db
from app.models import User, Form
from flask_jwt_extended import create_access_token

@pytest.fixture
def app():
    """Create application for testing"""
    app = create_app('testing')
    
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()

@pytest.fixture
def client(app):
    """Create test client"""
    return app.test_client()

def test_home_page(client):
    """Test home page loads successfully"""
    response = client.get('/')
    assert response.status_code == 200

def test_user_registration(client):
    """Test user registration"""
    response = client.post('/auth/register', json={
        'username': 'testuser',
        'email': 'test@example.com',
        'password': 'testpassword123',
        'first_name': 'Test',
        'last_name': 'User'
    })
    assert response.status_code == 201
    data = response.get_json()
    assert 'data' in data
    assert data['data']['username'] == 'testuser'

def test_user_login(client):
    """Test user login"""
    # First register a user
    client.post('/auth/register', json={
        'username': 'testuser',
        'email': 'test@example.com',
        'password': 'testpassword123'
    })
    
    # Then try to login
    response = client.post('/auth/login', json={
        'username': 'testuser',
        'password': 'testpassword123'
    })
    assert response.status_code == 200
    data = response.get_json()
    assert 'access_token' in data

def test_create_form(client):
    """Test form creation"""
    # Register and login a user first
    client.post('/auth/register', json={
        'username': 'testuser',
        'email': 'test@example.com',
        'password': 'testpassword123'
    })
    
    login_response = client.post('/auth/login', json={
        'username': 'testuser',
        'password': 'testpassword123'
    })
    
    token = login_response.get_json()['access_token']
    
    # Create a form
    response = client.post('/api/forms', 
                          json={'title': 'Test Form', 'description': 'A test form'},
                          headers={'Authorization': f'Bearer {token}'})
    
    assert response.status_code == 201
    data = response.get_json()
    assert data['data']['title'] == 'Test Form'

def test_get_forms(client):
    """Test getting user forms"""
    # Register and login a user first
    client.post('/auth/register', json={
        'username': 'testuser',
        'email': 'test@example.com',
        'password': 'testpassword123'
    })
    
    login_response = client.post('/auth/login', json={
        'username': 'testuser',
        'password': 'testpassword123'
    })
    
    token = login_response.get_json()['access_token']
    
    # Get forms (should be empty initially)
    response = client.get('/api/forms', headers={'Authorization': f'Bearer {token}'})
    assert response.status_code == 200
    data = response.get_json()
    assert 'data' in data
    assert len(data['data']) == 0