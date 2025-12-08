"""Tests for user routes"""

import json
from app.models.user import User
from datetime import date

def test_get_users(client):
    """Test getting all users"""
    response = client.get('/api/v1/users/')
    
    assert response.status_code == 200

def test_create_user(client):
    """Test creating a new user"""
    user_data = {
        'first_name': 'Test',
        'middle_name': 'Middle',
        'last_name': 'User',
        'dob': '1990-01-01',
        'designation': 'Developer',
        'department': 'Engineering',
        'status': 'active',
        'updated_by': 'admin'
    }
    
    response = client.post('/api/v1/users/',
                          data=json.dumps(user_data),
                          content_type='application/json')
    
    assert response.status_code == 201
