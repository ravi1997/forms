"""Tests for user schema"""

from app.schemas.user_schema import UserSchema

def test_user_schema_serialization():
    """Test serializing user data"""
    user_data = {
        'username': 'testuser',
        'email': 'test@example.com'
    }
    
    schema = UserSchema()
    result = schema.dump(user_data)
    
    assert result['username'] == 'testuser'
    assert result['email'] == 'test@example.com'

def test_user_schema_deserialization():
    """Test deserializing user data"""
    user_data = {
        'username': 'testuser',
        'email': 'test@example.com'
    }
    
    schema = UserSchema()
    result = schema.load(user_data)
    
    assert result['username'] == 'testuser'
    assert result['email'] == 'test@example.com'