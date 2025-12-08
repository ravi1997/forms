"""Tests for User model"""

import pytest
from app.models.user import User
from datetime import date

def test_user_creation():
    """Test creating a new user"""
    user = User(
        first_name="Test",
        middle_name="Middle",
        last_name="User",
        dob=date(1990, 1, 1),
        status="active"
    )
    
    assert user.first_name == "Test"
    assert user.middle_name == "Middle"
    assert user.last_name == "User"
    assert user.dob == date(1990, 1, 1)
    assert user.id is None  # ID should be None before saving

def test_user_repr():
    """Test user string representation"""
    user = User(
        first_name="Test",
        middle_name="Middle",
        last_name="User",
        dob=date(1990, 1, 1)
    )
    
    expected_repr = "<User None - Test User>"
    assert repr(user) == expected_repr
