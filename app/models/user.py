from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import uuid

from flask import current_app
from app.extensions import db, bcrypt
from enum import Enum

from sqlalchemy.dialects.postgresql import UUID  # IMPORTANT for Postgres UUID


class StatusEnum(Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    DELETED = "deleted"


# Reusable enum type (Alembic-friendly)
status_enum_type = db.Enum(StatusEnum, name="status_enum")


class User(db.Model):
    __tablename__ = 'user'

    id = db.Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    first_name = db.Column(db.String(100), nullable=False)
    middle_name = db.Column(db.String(100), nullable=True)
    last_name = db.Column(db.String(100), nullable=True)

    dob = db.Column(db.Date, nullable=False)

    designation = db.Column(db.String(100), nullable=True)
    department = db.Column(db.String(100), nullable=True)

    status = db.Column(
        status_enum_type,
        default=StatusEnum.INACTIVE,
        nullable=False
    )

    created_at = db.Column(db.DateTime, server_default=db.func.now(), nullable=False)

    updated_by = db.Column(db.String(100), nullable=True)
    updated_at = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now(), nullable=False)

    deleted_by = db.Column(db.String(100), nullable=True)
    deleted_at = db.Column(db.DateTime, nullable=True)

    # Relationship to Account (NO backref conflict)
    accounts = db.relationship(
        'Account',
        back_populates='user',
        lazy=True
    )

    def __repr__(self):
        return f'<User {self.id} - {self.first_name} {self.last_name}>'

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the User object to a dictionary"""
        return {
            'id': str(self.id),
            'first_name': self.first_name,
            'middle_name': self.middle_name,
            'last_name': self.last_name,
            'dob': self.dob.isoformat() if self.dob else None,
            'designation': self.designation,
            'department': self.department,
            'status': self.status.value if self.status else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_by': self.updated_by,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'deleted_by': self.deleted_by,
            'deleted_at': self.deleted_at.isoformat() if self.deleted_at else None,
            'accounts': [account.to_dict() for account in self.accounts] if self.accounts else []
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'User':
        """Create a User instance from a dictionary"""

        # Convert the id to UUID if provided
        user_id = data.get('id')
        if user_id:
            user_id = uuid.UUID(user_id) if isinstance(user_id, str) else user_id

        # Handle date conversion
        dob = data.get('dob')
        if isinstance(dob, str) and dob:
            dob = datetime.fromisoformat(dob).date()

        # Handle status conversion (accept name or value, case-insensitive)
        raw_status = data.get('status')
        status = StatusEnum.INACTIVE
        if isinstance(raw_status, StatusEnum):
            status = raw_status
        elif isinstance(raw_status, str):
            try:
                # Try enum name first: "ACTIVE", "INACTIVE", etc.
                status = StatusEnum[raw_status.upper()]
            except KeyError:
                try:
                    # Then try enum value: "active", "inactive", etc.
                    status = StatusEnum(raw_status.lower())
                except ValueError:
                    status = StatusEnum.INACTIVE

        # Handle datetime fields (if strings are provided)
        def parse_dt(value):
            if isinstance(value, str) and value:
                return datetime.fromisoformat(value)
            return value

        created_at = parse_dt(data.get('created_at'))
        updated_at = parse_dt(data.get('updated_at'))
        deleted_at = parse_dt(data.get('deleted_at'))

        user = cls(
            id=user_id,
            first_name=data.get('first_name'),
            middle_name=data.get('middle_name'),
            last_name=data.get('last_name'),
            dob=dob,
            designation=data.get('designation'),
            department=data.get('department'),
            status=status,
            created_at=created_at,
            updated_by=data.get('updated_by'),
            updated_at=updated_at,
            deleted_by=data.get('deleted_by'),
            deleted_at=deleted_at
        )

        return user

    def to_json(self) -> Dict[str, Any]:
        """Convert user object to JSON-serializable format for API responses"""
        return self.to_dict()

    def to_api_response(self, include_accounts: bool = True) -> Dict[str, Any]:
        """Format user data for API responses"""
        user_data = self.to_dict()
        if not include_accounts:
            # Remove accounts from response if not needed
            user_data.pop('accounts', None)
        return user_data

    # Validation methods
    def validate(self) -> List[str]:
        """Validate user data and return a list of validation errors"""
        errors: List[str] = []

        # Validate required fields
        if not self.first_name or len(self.first_name.strip()) == 0:
            errors.append("First name is required")

        # Validate name lengths
        if self.first_name and len(self.first_name) > 100:
            errors.append("First name must be 100 characters or less")
        if self.middle_name and len(self.middle_name) > 100:
            errors.append("Middle name must be 100 characters or less")
        if self.last_name and len(self.last_name) > 100:
            errors.append("Last name must be 100 characters or less")

        # Validate department and designation lengths
        if self.department and len(self.department) > 100:
            errors.append("Department must be 100 characters or less")
        if self.designation and len(self.designation) > 100:
            errors.append("Designation must be 100 characters or less")

        # Validate date of birth (should not be in the future)
        if self.dob and self.dob > datetime.now().date():
            errors.append("Date of birth cannot be in the future")

        # Validate age (should be reasonable)
        if self.dob:
            today = datetime.now().date()
            age = today.year - self.dob.year - (
                (today.month, today.day) < (self.dob.month, self.dob.day)
            )
            if age < 0:
                errors.append("Date of birth cannot be in the future")
            elif age > 150:
                errors.append("Date of birth seems unrealistic (age > 150)")

        # Validate status
        if self.status not in list(StatusEnum):
            errors.append("Invalid status value")

        return errors

    def is_valid(self) -> bool:
        """Check if user data is valid"""
        return len(self.validate()) == 0

    # Search and filtering methods
    @classmethod
    def search(
        cls,
        query: Optional[str] = None,
        status: Optional[str] = None,
        department: Optional[str] = None,
        designation: Optional[str] = None,
        include_deleted: bool = False
    ) -> List['User']:
        """Search and filter users based on various criteria"""
        users_query = cls.query

        # Filter by status
        if status:
            status_enum: Optional[StatusEnum] = None
            try:
                status_enum = StatusEnum[status.upper()]
            except KeyError:
                try:
                    status_enum = StatusEnum(status.lower())
                except ValueError:
                    status_enum = None

            if status_enum:
                users_query = users_query.filter(cls.status == status_enum)

        # Filter by department
        if department:
            users_query = users_query.filter(cls.department.ilike(f'%{department}%'))

        # Filter by designation
        if designation:
            users_query = users_query.filter(cls.designation.ilike(f'%{designation}%'))

        # Filter by search query (searches in first name, middle name, last name)
        if query:
            search_filter = (
                cls.first_name.ilike(f'%{query}%') |
                cls.middle_name.ilike(f'%{query}%') |
                cls.last_name.ilike(f'%{query}%')
            )
            users_query = users_query.filter(search_filter)

        # Include or exclude deleted users
        if not include_deleted:
            users_query = users_query.filter(cls.deleted_at.is_(None))

        return users_query.all()

    @classmethod
    def filter_by_status(cls, status: str) -> List['User']:
        """Get users by status"""
        status_enum: Optional[StatusEnum] = None
        try:
            status_enum = StatusEnum[status.upper()]
        except KeyError:
            try:
                status_enum = StatusEnum(status.lower())
            except ValueError:
                return []

        return cls.query.filter(cls.status == status_enum).all()

    @classmethod
    def filter_by_age_range(
        cls,
        min_age: Optional[int] = None,
        max_age: Optional[int] = None
    ) -> List['User']:
        """Filter users by age range"""
        users = cls.query.filter(cls.deleted_at.is_(None)).all()
        result: List['User'] = []

        for user in users:
            age = user.age()
            if age is not None:
                if min_age is not None and age < min_age:
                    continue
                if max_age is not None and age > max_age:
                    continue
                result.append(user)

        return result

    # Data integrity methods
    def check_data_integrity(self) -> Dict[str, Any]:
        """Check data integrity and return report"""
        integrity_report: Dict[str, Any] = {
            'user_id': str(self.id),
            'issues': [],
            'warnings': [],
            'is_valid': True
        }

        # Check for missing required fields
        if not self.first_name or len(self.first_name.strip()) == 0:
            integrity_report['issues'].append('Missing first name')
            integrity_report['is_valid'] = False

        # Check for inconsistent status and deletion
        if self.status == StatusEnum.DELETED and self.deleted_at is None:
            integrity_report['issues'].append('Status is DELETED but deleted_at is None')
            integrity_report['is_valid'] = False
        elif self.status != StatusEnum.DELETED and self.deleted_at is not None:
            integrity_report['issues'].append('User has deletion timestamp but status is not DELETED')
            integrity_report['is_valid'] = False

        # Check for invalid dates
        if self.dob and self.dob > datetime.now().date():
            integrity_report['issues'].append('Date of birth is in the future')
            integrity_report['is_valid'] = False

        if self.created_at and self.updated_at and self.created_at > self.updated_at:
            integrity_report['warnings'].append('Updated time is earlier than creation time')

        # Check account references
        if self.accounts:
            for account in self.accounts:
                if account.user_id != self.id:
                    integrity_report['issues'].append(f'Account {account.id} has mismatched user_id')
                    integrity_report['is_valid'] = False

        return integrity_report

    def is_consistent(self) -> bool:
        """Check if user data is consistent"""
        integrity_report = self.check_data_integrity()
        return integrity_report['is_valid']

    # Status management methods
    def activate(self, updated_by: Optional[str] = None) -> None:
        """Activate the user"""
        self.status = StatusEnum.ACTIVE
        self.updated_by = updated_by

    def deactivate(self, updated_by: Optional[str] = None) -> None:
        """Deactivate the user"""
        self.status = StatusEnum.INACTIVE
        self.updated_by = updated_by

    def suspend(self, updated_by: Optional[str] = None) -> None:
        """Suspend the user"""
        self.status = StatusEnum.SUSPENDED
        self.updated_by = updated_by

    def delete(self, deleted_by: Optional[str] = None) -> None:
        """Mark the user as deleted (soft delete)"""
        self.status = StatusEnum.DELETED
        self.deleted_by = deleted_by
        self.deleted_at = datetime.utcnow()
        self.updated_by = deleted_by

    def restore(self, restored_by: Optional[str] = None) -> bool:
        """Restore a soft-deleted user"""
        if self.status == StatusEnum.DELETED:
            self.status = StatusEnum.INACTIVE  # Restore to inactive by default
            self.deleted_by = None
            self.deleted_at = None
            self.updated_by = restored_by
            return True
        return False

    def verify_soft_delete(self) -> bool:
        """Verify that a user has been soft-deleted"""
        return self.status == StatusEnum.DELETED and self.deleted_at is not None

    # Account management methods
    def add_account(self, account: 'Account') -> None:
        """Add an account to the user"""
        if account not in self.accounts:
            self.accounts.append(account)

    def remove_account(self, account: 'Account') -> None:
        """Remove an account from the user"""
        if account in self.accounts:
            self.accounts.remove(account)

    def get_active_accounts(self) -> List['Account']:
        """Get all active accounts for this user"""
        return [account for account in self.accounts if account.status == StatusEnum.ACTIVE]

    def get_inactive_accounts(self) -> List['Account']:
        """Get all inactive accounts for this user"""
        return [account for account in self.accounts if account.status == StatusEnum.INACTIVE]

    def get_suspended_accounts(self) -> List['Account']:
        """Get all suspended accounts for this user"""
        return [account for account in self.accounts if account.status == StatusEnum.SUSPENDED]

    def get_deleted_accounts(self) -> List['Account']:
        """Get all deleted accounts for this user"""
        return [account for account in self.accounts if account.status == StatusEnum.DELETED]

    # Bulk operations
    @classmethod
    def bulk_update_status(
        cls,
        user_ids: List[uuid.UUID],
        new_status: StatusEnum,
        updated_by: Optional[str] = None
    ) -> int:
        """Bulk update status for multiple users"""
        updated_count = cls.query.filter(
            cls.id.in_(user_ids)
        ).update({
            'status': new_status,
            'updated_by': updated_by,
            'updated_at': db.func.now()
        }, synchronize_session=False)

        db.session.commit()
        return updated_count

    @classmethod
    def bulk_delete(
        cls,
        user_ids: List[uuid.UUID],
        deleted_by: Optional[str] = None
    ) -> int:
        """Bulk soft delete users"""
        from sqlalchemy import func
        updated_count = cls.query.filter(
            cls.id.in_(user_ids)
        ).update({
            'status': StatusEnum.DELETED,
            'deleted_by': deleted_by,
            'deleted_at': func.now(),
            'updated_by': deleted_by,
            'updated_at': func.now()
        }, synchronize_session=False)

        db.session.commit()
        return updated_count

    @classmethod
    def bulk_restore(
        cls,
        user_ids: List[uuid.UUID],
        restored_by: Optional[str] = None
    ) -> int:
        """Bulk restore soft-deleted users"""
        updated_count = cls.query.filter(
            cls.id.in_(user_ids)
        ).update({
            'status': StatusEnum.INACTIVE,  # Restore to inactive by default
            'deleted_by': None,
            'deleted_at': None,
            'updated_by': restored_by,
            'updated_at': db.func.now()
        }, synchronize_session=False)

        db.session.commit()
        return updated_count

    # Permission methods
    def has_role_in_any_account(self, role_name: str) -> bool:
        """Check if the user has a specific role in any of their accounts"""
        for account in self.accounts:
            if account.has_role(role_name):
                return True
        return False

    def has_role_in_all_accounts(self, role_name: str) -> bool:
        """Check if the user has a specific role in all of their accounts"""
        if not self.accounts:
            return False

        for account in self.accounts:
            if not account.has_role(role_name):
                return False
        return True

    def get_unique_roles(self) -> List[str]:
        """Get all unique roles across all user accounts"""
        roles = set()
        for account in self.accounts:
            for role in account.roles:
                roles.add(role.name)
        return list(roles)

    def get_permissions_by_account(self) -> Dict[str, List[str]]:
        """Get permissions/roles for each account"""
        permissions: Dict[str, List[str]] = {}
        for account in self.accounts:
            account_roles = [role.name for role in account.roles]
            permissions[str(account.id)] = account_roles
        return permissions

    # Utility methods
    def full_name(self) -> str:
        """Get the full name of the user"""
        name_parts = [self.first_name]
        if self.middle_name:
            name_parts.append(self.middle_name)
        if self.last_name:
            name_parts.append(self.last_name)
        return ' '.join(name_parts)

    def age(self) -> Optional[int]:
        """Calculate the user's age"""
        if self.dob:
            today = datetime.now().date()
            return today.year - self.dob.year - (
                (today.month, today.day) < (self.dob.month, self.dob.day)
            )
        return None

    def is_active(self) -> bool:
        """Check if the user is active"""
        return self.status == StatusEnum.ACTIVE

    def is_inactive(self) -> bool:
        """Check if the user is inactive"""
        return self.status == StatusEnum.INACTIVE

    def is_suspended(self) -> bool:
        """Check if the user is suspended"""
        return self.status == StatusEnum.SUSPENDED

    def is_deleted(self) -> bool:
        """Check if the user is deleted"""
        return self.status == StatusEnum.DELETED


class Role(db.Model):
    __tablename__ = 'role'

    id = db.Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    name = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.String(255), nullable=True)

    created_by = db.Column(db.String(100), nullable=True)
    created_at = db.Column(db.DateTime, server_default=db.func.now(), nullable=False)

    updated_by = db.Column(db.String(100), nullable=True)
    updated_at = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now(), nullable=False)

    deleted_by = db.Column(db.String(100), nullable=True)
    deleted_at = db.Column(db.DateTime, nullable=True)

    # Many-to-many with Account
    accounts = db.relationship(
        'Account',
        secondary='account_roles',
        back_populates='roles'
    )


class AccountRoles(db.Model):
    __tablename__ = 'account_roles'

    account_id = db.Column(
        UUID(as_uuid=True),
        db.ForeignKey('account.id'),
        primary_key=True
    )
    role_id = db.Column(
        UUID(as_uuid=True),
        db.ForeignKey('role.id'),
        primary_key=True
    )


class Account(db.Model):
    __tablename__ = 'account'

    id = db.Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    user_id = db.Column(
        UUID(as_uuid=True),
        db.ForeignKey('user.id'),
        nullable=False
    )
    user = db.relationship(
        'User',
        back_populates='accounts'
    )

    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    password_set_on = db.Column(db.DateTime, nullable=False)

    password_reset_token = db.Column(db.String(100), nullable=True)
    password_reset_token_expires_at = db.Column(db.DateTime, nullable=True)

    created_at = db.Column(db.DateTime, server_default=db.func.now(), nullable=False)

    updated_by = db.Column(db.String(100), nullable=True)
    updated_at = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now(), nullable=False)

    deleted_by = db.Column(db.String(100), nullable=True)
    deleted_at = db.Column(db.DateTime, nullable=True)

    otp = db.Column(db.String(10), nullable=True)
    otp_created_at = db.Column(db.DateTime, nullable=True)

    # Many-to-many with Role
    roles = db.relationship(
        'Role',
        secondary='account_roles',
        back_populates='accounts'
    )

    status = db.Column(
        status_enum_type,
        default=StatusEnum.INACTIVE,
        nullable=False
    )

    # -------- Password & OTP --------
    def set_password(self, password: str) -> None:
        self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')
        self.password_set_on = datetime.utcnow()

    def check_password(self, password: str) -> bool:
        return bcrypt.check_password_hash(self.password_hash, password)

    def set_otp(self, otp: str) -> None:
        self.otp = otp
        self.otp_created_at = datetime.utcnow()

    def check_otp(self, otp: str) -> bool:
        if not self.otp or not self.otp_created_at:
            return False
        nowtime = datetime.utcnow()
        otp_time_delta = current_app.config.get('OTP_TIME_DELTA', 10)  # in minutes
        return self.otp == otp and (nowtime - self.otp_created_at) <= timedelta(minutes=otp_time_delta)

    # -------- Roles --------
    def has_role(self, role_name: str) -> bool:
        return any(role.name == role_name for role in self.roles)

    # (Optional) helper to_dict if you want it for User.to_dict
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': str(self.id),
            'user_id': str(self.user_id),
            'username': self.username,
            'status': self.status.value if self.status else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_by': self.updated_by,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'deleted_by': self.deleted_by,
            'deleted_at': self.deleted_at.isoformat() if self.deleted_at else None,
            'roles': [role.name for role in self.roles]
        }
