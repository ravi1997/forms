from marshmallow import Schema, fields, validates, ValidationError
from app.models.user import StatusEnum
from app.extensions import db
import uuid


class StatusEnumField(fields.Field):
    """Custom field for handling StatusEnum values"""
    
    def _serialize(self, value, attr, obj, **kwargs):
        if value is None:
            return None
        return value.value if hasattr(value, 'value') else str(value)
    
    def _deserialize(self, value, attr, data, **kwargs):
        if value is None:
            return None
        try:
            return StatusEnum(value)
        except ValueError:
            raise ValidationError(f'Invalid status value: {value}. Must be one of {list(StatusEnum.__members__.keys())}')


class BaseSchema(Schema):
    """Base schema containing common fields for all models"""
    id = fields.UUID(required=True)
    created_at = fields.DateTime(required=True)
    updated_by = fields.Str(allow_none=True)
    updated_at = fields.DateTime(required=True)
    deleted_by = fields.Str(allow_none=True)
    deleted_at = fields.DateTime(allow_none=True)


class TimestampSchema(Schema):
    """Schema containing only timestamp fields"""
    created_at = fields.DateTime(required=True)
    updated_by = fields.Str(allow_none=True)
    updated_at = fields.DateTime(required=True)
    deleted_by = fields.Str(allow_none=True)
    deleted_at = fields.DateTime(allow_none=True)


class SoftDeleteSchema(Schema):
    """Schema containing soft delete fields"""
    deleted_by = fields.Str(allow_none=True)
    deleted_at = fields.DateTime(allow_none=True)


class StatusSchema(Schema):
    """Schema containing status field"""
    status = StatusEnumField(required=True)


class CreateSchema(Schema):
    """Base schema for creation operations (excludes auto-generated fields)"""
    updated_by = fields.Str(allow_none=True)
    deleted_by = fields.Str(allow_none=True)
    deleted_at = fields.DateTime(allow_none=True)


class UpdateSchema(Schema):
    """Base schema for update operations (makes most fields optional)"""
    updated_by = fields.Str(allow_none=True)
    deleted_by = fields.Str(allow_none=True)
    deleted_at = fields.DateTime(allow_none=True)


def validate_string_length(value, field_name, max_length, allow_empty=True):
    """
    Utility function to validate string length
    :param value: The value to validate
    :param field_name: Name of the field for error message
    :param max_length: Maximum allowed length
    :param allow_empty: Whether empty/None values are allowed
    :return: List of validation errors
    """
    errors = []
    
    if value is None or (isinstance(value, str) and len(value.strip()) == 0):
        if not allow_empty:
            errors.append(f'{field_name} is required')
        return errors
    
    if isinstance(value, str) and len(value) > max_length:
        errors.append(f'{field_name} must be {max_length} characters or less')
    
    return errors


def validate_date_not_future(value, field_name):
    """
    Utility function to validate that a date is not in the future
    :param value: The date value to validate
    :param field_name: Name of the field for error message
    :return: List of validation errors
    """
    errors = []
    
    if value and value > db.func.current_date():
        errors.append(f'{field_name} cannot be in the future')
    
    return errors


def validate_uuid(value, field_name, required=True):
    """
    Utility function to validate UUID format
    :param value: The value to validate
    :param field_name: Name of the field for error message
    :param required: Whether the field is required
    :return: List of validation errors
    """
    errors = []
    
    if value is None:
        if required:
            errors.append(f'{field_name} is required')
        return errors
    
    try:
        uuid.UUID(str(value))
    except ValueError:
        errors.append(f'{field_name} must be a valid UUID')
    
    return errors


def validate_password_strength(password, field_name="Password", min_length=8):
    """
    Utility function to validate password strength
    :param password: The password to validate
    :param field_name: Name of the field for error message
    :param min_length: Minimum length requirement
    :return: List of validation errors
    """
    errors = []
    
    if not password or len(password.strip()) == 0:
        errors.append(f'{field_name} is required')
        return errors
    
    if len(password) < min_length:
        errors.append(f'{field_name} must be at least {min_length} characters long')
    
    return errors