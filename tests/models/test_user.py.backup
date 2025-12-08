"""Tests for User model"""

import pytest
from app.models.user import User

def test_user_creation():
    """Test creating a new user"""
    user = User(username="testuser", email="test@example.com")
    
    assert user.username == "testuser"
    assert user.email == "test@example.com"
    assert user.id is None  # ID should be None before saving

def test_user_repr():
    """Test user string representation"""
    user = User(username="testuser", email="test@example.com")
    
    expected_repr = "<User testuser>"
    assert repr(user) == expected_repr