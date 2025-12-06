from marshmallow import Schema, fields, validates, ValidationError
from app.models.user import Role, Account, StatusEnum, AccountRoles
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


class AccountSchema(Schema):
    """Schema for Account model - referenced in Role relationships"""
    id = fields.UUID(required=True)
    user_id = fields.UUID(required=True)
    username = fields.Str(required=True)
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
    status = StatusEnumField(required=True)


class RoleSchema(Schema):
    """Full schema with all fields for Role model"""
    id = fields.UUID(required=True)
    name = fields.Str(required=True)
    description = fields.Str(allow_none=True)
    created_by = fields.Str(allow_none=True)
    created_at = fields.DateTime(required=True)
    updated_by = fields.Str(allow_none=True)
    updated_at = fields.DateTime(required=True)
    deleted_by = fields.Str(allow_none=True)
    deleted_at = fields.DateTime(allow_none=True)
    accounts = fields.Nested(AccountSchema, many=True, required=False)

    @validates('name')
    def validate_name(self, value):
        if not value or len(value.strip()) == 0:
            raise ValidationError('Role name is required')
        if len(value) > 50:
            raise ValidationError('Role name must be 50 characters or less')

    @validates('description')
    def validate_description(self, value):
        if value and len(value) > 255:
            raise ValidationError('Description must be 255 characters or less')


class RoleCreateSchema(Schema):
    """Schema for creating new roles (excludes auto-generated fields)"""
    name = fields.Str(required=True)
    description = fields.Str(allow_none=True)
    created_by = fields.Str(allow_none=True)

    @validates('name')
    def validate_name(self, value):
        if not value or len(value.strip()) == 0:
            raise ValidationError('Role name is required')
        if len(value) > 50:
            raise ValidationError('Role name must be 50 characters or less')

    @validates('description')
    def validate_description(self, value):
        if value and len(value) > 255:
            raise ValidationError('Description must be 255 characters or less')


class RoleUpdateSchema(Schema):
    """Schema for updating roles (makes most fields optional)"""
    name = fields.Str(allow_none=True)
    description = fields.Str(allow_none=True)
    updated_by = fields.Str(allow_none=True)
    deleted_by = fields.Str(allow_none=True)
    deleted_at = fields.DateTime(allow_none=True)

    @validates('name')
    def validate_name(self, value):
        if value and len(value.strip()) == 0:
            raise ValidationError('Role name cannot be empty')
        if value and len(value) > 50:
            raise ValidationError('Role name must be 50 characters or less')

    @validates('description')
    def validate_description(self, value):
        if value and len(value) > 255:
            raise ValidationError('Description must be 255 characters or less')


class RolePublicSchema(Schema):
    """Schema for public display (excludes sensitive information)"""
    id = fields.UUID(required=True)
    name = fields.Str(required=True)
    description = fields.Str(allow_none=True)
    created_at = fields.DateTime(required=True)
    updated_at = fields.DateTime(required=True)
    accounts = fields.Nested(AccountSchema, many=True, required=False)

    @validates('name')
    def validate_name(self, value):
        if not value or len(value.strip()) == 0:
            raise ValidationError('Role name is required')
        if len(value) > 50:
            raise ValidationError('Role name must be 50 characters or less')

    @validates('description')
    def validate_description(self, value):
        if value and len(value) > 255:
            raise ValidationError('Description must be 255 characters or less')