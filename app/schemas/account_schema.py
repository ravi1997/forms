from marshmallow import Schema, fields, validates, ValidationError
from app.models.user import Account, User, Role, StatusEnum
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


class UserSchema(Schema):
    """Schema for User model - referenced in Account relationships"""
    id = fields.UUID(required=True)
    first_name = fields.Str(required=True)
    middle_name = fields.Str(allow_none=True)
    last_name = fields.Str(allow_none=True)
    dob = fields.Date(required=True)
    designation = fields.Str(allow_none=True)
    department = fields.Str(allow_none=True)
    status = StatusEnumField(required=True)
    created_at = fields.DateTime(required=True)
    updated_by = fields.Str(allow_none=True)
    updated_at = fields.DateTime(required=True)
    deleted_by = fields.Str(allow_none=True)
    deleted_at = fields.DateTime(allow_none=True)


class RoleSchema(Schema):
    """Schema for Role model - referenced in Account relationships"""
    id = fields.UUID(required=True)
    name = fields.Str(required=True)
    description = fields.Str(allow_none=True)
    created_by = fields.Str(allow_none=True)
    created_at = fields.DateTime(required=True)
    updated_by = fields.Str(allow_none=True)
    updated_at = fields.DateTime(required=True)
    deleted_by = fields.Str(allow_none=True)
    deleted_at = fields.DateTime(allow_none=True)


class AccountSchema(Schema):
    """Full schema with all fields for Account model"""
    id = fields.UUID(required=True)
    user_id = fields.UUID(required=True)
    user = fields.Nested(UserSchema, required=False)
    username = fields.Str(required=True)
    password_hash = fields.Str(required=True)  # Included for completeness, but should be handled carefully
    password_set_on = fields.DateTime(required=True)
    password_reset_token = fields.Str(allow_none=True)
    password_reset_token_expires_at = fields.DateTime(allow_none=True)
    created_at = fields.DateTime(required=True)
    updated_by = fields.Str(allow_none=True)
    updated_at = fields.DateTime(required=True)
    deleted_by = fields.Str(allow_none=True)
    deleted_at = fields.DateTime(allow_none=True)
    otp = fields.Str(allow_none=True)
    otp_created_at = fields.DateTime(allow_none=True)
    roles = fields.Nested(RoleSchema, many=True, required=False)
    status = StatusEnumField(required=True)

    @validates('username')
    def validate_username(self, value):
        if not value or len(value.strip()) == 0:
            raise ValidationError('Username is required')
        if len(value) > 50:
            raise ValidationError('Username must be 50 characters or less')

    @validates('password_hash')
    def validate_password_hash(self, value):
        if not value or len(value.strip()) == 0:
            raise ValidationError('Password hash is required')
        if len(value) < 8:
            raise ValidationError('Password hash is too short')

    @validates('password_reset_token')
    def validate_password_reset_token(self, value):
        if value and len(value) > 100:
            raise ValidationError('Password reset token must be 100 characters or less')

    @validates('otp')
    def validate_otp(self, value):
        if value and len(value) > 10:
            raise ValidationError('OTP must be 10 characters or less')


class AccountCreateSchema(Schema):
    """Schema for creating new accounts (excludes auto-generated fields)"""
    user_id = fields.UUID(required=True)
    username = fields.Str(required=True)
    password = fields.Str(required=True, load_only=True)  # Password in plain text for input validation
    password_reset_token = fields.Str(allow_none=True)
    password_reset_token_expires_at = fields.DateTime(allow_none=True)
    updated_by = fields.Str(allow_none=True)
    deleted_by = fields.Str(allow_none=True)
    deleted_at = fields.DateTime(allow_none=True)
    otp = fields.Str(allow_none=True)
    otp_created_at = fields.DateTime(allow_none=True)
    status = StatusEnumField(load_default=StatusEnum.INACTIVE)  # Default to INACTIVE for new accounts

    @validates('username')
    def validate_username(self, value):
        if not value or len(value.strip()) == 0:
            raise ValidationError('Username is required')
        if len(value) > 50:
            raise ValidationError('Username must be 50 characters or less')

    @validates('password')
    def validate_password(self, value):
        if not value or len(value.strip()) == 0:
            raise ValidationError('Password is required')
        if len(value) < 8:
            raise ValidationError('Password must be at least 8 characters long')

    @validates('password_reset_token')
    def validate_password_reset_token(self, value):
        if value and len(value) > 100:
            raise ValidationError('Password reset token must be 100 characters or less')

    @validates('otp')
    def validate_otp(self, value):
        if value and len(value) > 10:
            raise ValidationError('OTP must be 10 characters or less')


class AccountUpdateSchema(Schema):
    """Schema for updating accounts (makes most fields optional)"""
    user_id = fields.UUID(allow_none=True)
    username = fields.Str(allow_none=True)
    password = fields.Str(allow_none=True, load_only=True)  # Password in plain text for input validation
    password_reset_token = fields.Str(allow_none=True)
    password_reset_token_expires_at = fields.DateTime(allow_none=True)
    updated_by = fields.Str(allow_none=True)
    deleted_by = fields.Str(allow_none=True)
    deleted_at = fields.DateTime(allow_none=True)
    otp = fields.Str(allow_none=True)
    otp_created_at = fields.DateTime(allow_none=True)
    status = StatusEnumField(allow_none=True)

    @validates('username')
    def validate_username(self, value):
        if value and len(value.strip()) == 0:
            raise ValidationError('Username cannot be empty')
        if value and len(value) > 50:
            raise ValidationError('Username must be 50 characters or less')

    @validates('password')
    def validate_password(self, value):
        if value and len(value.strip()) == 0:
            raise ValidationError('Password cannot be empty')
        if value and len(value) < 8:
            raise ValidationError('Password must be at least 8 characters long')

    @validates('password_reset_token')
    def validate_password_reset_token(self, value):
        if value and len(value) > 100:
            raise ValidationError('Password reset token must be 100 characters or less')

    @validates('otp')
    def validate_otp(self, value):
        if value and len(value) > 10:
            raise ValidationError('OTP must be 10 characters or less')


class AccountPublicSchema(Schema):
    """Schema for public display (excludes sensitive information like password_hash)"""
    id = fields.UUID(required=True)
    user_id = fields.UUID(required=True)
    user = fields.Nested(UserSchema, required=False)
    username = fields.Str(required=True)
    password_set_on = fields.DateTime(required=True)
    created_at = fields.DateTime(required=True)
    updated_at = fields.DateTime(required=True)
    otp = fields.Str(allow_none=True)
    otp_created_at = fields.DateTime(allow_none=True)
    roles = fields.Nested(RoleSchema, many=True, required=False)
    status = StatusEnumField(required=True)
    
    @validates('username')
    def validate_username(self, value):
        if not value or len(value.strip()) == 0:
            raise ValidationError('Username is required')
        if len(value) > 50:
            raise ValidationError('Username must be 50 characters or less')