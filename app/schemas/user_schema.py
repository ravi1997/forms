from marshmallow import Schema, fields, validates, ValidationError
from app.models.user import User, StatusEnum, Account
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
    """Schema for Account model"""
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


class UserSchema(Schema):
    """Full schema with all fields for User model"""
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
    accounts = fields.Nested(AccountSchema, many=True, required=False)

    @validates('first_name')
    def validate_first_name(self, value):
        if not value or len(value.strip()) == 0:
            raise ValidationError('First name is required')
        if len(value) > 100:
            raise ValidationError('First name must be 100 characters or less')

    @validates('middle_name')
    def validate_middle_name(self, value):
        if value and len(value) > 100:
            raise ValidationError('Middle name must be 100 characters or less')

    @validates('last_name')
    def validate_last_name(self, value):
        if value and len(value) > 100:
            raise ValidationError('Last name must be 100 characters or less')

    @validates('department')
    def validate_department(self, value):
        if value and len(value) > 100:
            raise ValidationError('Department must be 100 characters or less')

    @validates('designation')
    def validate_designation(self, value):
        if value and len(value) > 100:
            raise ValidationError('Designation must be 100 characters or less')

    @validates('dob')
    def validate_dob(self, value):
        if value and value > db.func.current_date():
            raise ValidationError('Date of birth cannot be in the future')
        # Additional validation for age can be added if needed


class UserCreateSchema(Schema):
    """Schema for creating new users (excludes auto-generated fields)"""
    first_name = fields.Str(required=True)
    middle_name = fields.Str(allow_none=True)
    last_name = fields.Str(allow_none=True)
    dob = fields.Date(required=True)
    designation = fields.Str(allow_none=True)
    department = fields.Str(allow_none=True)
    status = StatusEnumField(missing=StatusEnum.INACTIVE)  # Default to INACTIVE for new users
    updated_by = fields.Str(allow_none=True)
    deleted_by = fields.Str(allow_none=True)
    deleted_at = fields.DateTime(allow_none=True)

    @validates('first_name')
    def validate_first_name(self, value):
        if not value or len(value.strip()) == 0:
            raise ValidationError('First name is required')
        if len(value) > 100:
            raise ValidationError('First name must be 100 characters or less')

    @validates('middle_name')
    def validate_middle_name(self, value):
        if value and len(value) > 100:
            raise ValidationError('Middle name must be 100 characters or less')

    @validates('last_name')
    def validate_last_name(self, value):
        if value and len(value) > 100:
            raise ValidationError('Last name must be 100 characters or less')

    @validates('department')
    def validate_department(self, value):
        if value and len(value) > 100:
            raise ValidationError('Department must be 100 characters or less')

    @validates('designation')
    def validate_designation(self, value):
        if value and len(value) > 100:
            raise ValidationError('Designation must be 100 characters or less')

    @validates('dob')
    def validate_dob(self, value):
        if value and value > db.func.current_date():
            raise ValidationError('Date of birth cannot be in the future')


class UserUpdateSchema(Schema):
    """Schema for updating users (makes most fields optional)"""
    first_name = fields.Str(allow_none=True)
    middle_name = fields.Str(allow_none=True)
    last_name = fields.Str(allow_none=True)
    dob = fields.Date(allow_none=True)
    designation = fields.Str(allow_none=True)
    department = fields.Str(allow_none=True)
    status = StatusEnumField(allow_none=True)
    updated_by = fields.Str(allow_none=True)
    deleted_by = fields.Str(allow_none=True)
    deleted_at = fields.DateTime(allow_none=True)

    @validates('first_name')
    def validate_first_name(self, value):
        if value and len(value.strip()) == 0:
            raise ValidationError('First name cannot be empty')
        if value and len(value) > 100:
            raise ValidationError('First name must be 100 characters or less')

    @validates('middle_name')
    def validate_middle_name(self, value):
        if value and len(value) > 100:
            raise ValidationError('Middle name must be 100 characters or less')

    @validates('last_name')
    def validate_last_name(self, value):
        if value and len(value) > 100:
            raise ValidationError('Last name must be 100 characters or less')

    @validates('department')
    def validate_department(self, value):
        if value and len(value) > 100:
            raise ValidationError('Department must be 100 characters or less')

    @validates('designation')
    def validate_designation(self, value):
        if value and len(value) > 100:
            raise ValidationError('Designation must be 100 characters or less')

    @validates('dob')
    def validate_dob(self, value):
        if value and value > db.func.current_date():
            raise ValidationError('Date of birth cannot be in the future')


class UserPublicSchema(Schema):
    """Schema for public display (excludes sensitive information)"""
    id = fields.UUID(required=True)
    first_name = fields.Str(required=True)
    middle_name = fields.Str(allow_none=True)
    last_name = fields.Str(allow_none=True)
    dob = fields.Date(required=True)
    designation = fields.Str(allow_none=True)
    department = fields.Str(allow_none=True)
    status = StatusEnumField(required=True)
    created_at = fields.DateTime(required=True)
    updated_at = fields.DateTime(required=True)
    accounts = fields.Nested(AccountSchema, many=True, required=False)

    @validates('first_name')
    def validate_first_name(self, value):
        if not value or len(value.strip()) == 0:
            raise ValidationError('First name is required')
        if len(value) > 100:
            raise ValidationError('First name must be 100 characters or less')

    @validates('middle_name')
    def validate_middle_name(self, value):
        if value and len(value) > 100:
            raise ValidationError('Middle name must be 100 characters or less')

    @validates('last_name')
    def validate_last_name(self, value):
        if value and len(value) > 100:
            raise ValidationError('Last name must be 100 characters or less')

    @validates('department')
    def validate_department(self, value):
        if value and len(value) > 100:
            raise ValidationError('Department must be 100 characters or less')

    @validates('designation')
    def validate_designation(self, value):
        if value and len(value) > 100:
            raise ValidationError('Designation must be 100 characters or less')

    @validates('dob')
    def validate_dob(self, value):
        if value and value > db.func.current_date():
            raise ValidationError('Date of birth cannot be in the future')