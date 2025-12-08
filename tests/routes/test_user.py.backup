"""Tests for user routes"""

import json
from app.models.user import User

def test_get_users(client):
    """Test getting all users"""
    response = client.get('/users')
    
    assert response.status_code == 200

def test_create_user(client):
    """Test creating a new user"""
    user_data = {
        'username': 'testuser',
        'email': 'test@example.com'
    }
    
    response = client.post('/users',
                          data=json.dumps(user_data),
                          content_type='application/json')
    
    assert response.status_code == 201