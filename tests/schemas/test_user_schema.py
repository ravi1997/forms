"""Tests for user schema"""

from app.schemas.user_schema import UserSchema, UserCreateSchema, UserUpdateSchema

def test_user_schema_serialization():
    """Test serializing user data"""
    user_data = {
        'id': '123e4567-e89b-12d3-a456-426614174000',
        'first_name': 'Test',
        'middle_name': 'Middle',
        'last_name': 'User',
        'dob': '1990-01-01',
        'designation': 'Developer',
        'department': 'Engineering',
        'status': 'active',
        'created_at': '2023-01-01T00:00:00',
        'updated_by': 'admin',
        'updated_at': '2023-01-01T00:00:00',
        'deleted_by': None,
        'deleted_at': None,
        'accounts': []
    }
    
    schema = UserSchema()
    result = schema.dump(user_data)
    
    assert result['first_name'] == 'Test'
    assert result['last_name'] == 'User'

def test_user_schema_deserialization():
    """Test deserializing user data"""
    user_data = {
        'first_name': 'Test',
        'middle_name': 'Middle',
        'last_name': 'User',
        'dob': '1990-01-01',
        'designation': 'Developer',
        'department': 'Engineering',
        'status': 'active',
        'updated_by': 'admin',
        'deleted_by': None,
        'deleted_at': None
    }
    
    schema = UserCreateSchema()
    result = schema.load(user_data)
    
    assert result['first_name'] == 'Test'
    assert result['last_name'] == 'User'
    
def test_user_update_schema():
    """Test user update schema"""
    user_data = {
        'first_name': 'Updated',
        'middle_name': 'Middle',
        'last_name': 'User',
        'dob': '1990-01-01',
        'designation': 'Senior Developer',
        'department': 'Engineering',
        'status': 'inactive',
        'updated_by': 'admin'
    }
    
    schema = UserUpdateSchema()
    result = schema.load(user_data)
    
    assert result['first_name'] == 'Updated'
    assert result['last_name'] == 'User'
