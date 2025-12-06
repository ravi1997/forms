from datetime import datetime, timedelta

from flask import current_app
from app.extensions import db,bcrypt

class StatusEnum(db.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    DELETED = "deleted"


class User(db.Model):
    id = db.Column(db.UUID(as_uuid=True), primary_key=True)
    
    first_name = db.Column(db.String(100), nullable=False)
    middle_name = db.Column(db.String(100), nullable=True)
    last_name = db.Column(db.String(100), nullable=True)
    
    dob = db.Column(db.Date, nullable=False)
    
    designation = db.Column(db.String(100), nullable=True)
    department = db.Column(db.String(100), nullable=True)
    
    status = db.Column(StatusEnum, default=StatusEnum.INACTIVE, nullable=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now(), nullable=False)
    
    updated_by = db.Column(db.String(100), nullable=True)
    updated_at = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now(), nullable=False)
    
    deleted_by = db.Column(db.String(100), nullable=True)
    deleted_at = db.Column(db.DateTime, nullable=True)
    
    accounts = db.relationship('Account', backref='user', lazy=True)
    
    def __repr__(self):
        return f'<User {self.id} - {self.first_name} {self.last_name}>'
    
    def to_dict(self):
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
    
    # Status management methods
    def activate(self, updated_by=None):
        """Activate the user"""
        self.status = StatusEnum.ACTIVE
        self.updated_by = updated_by
    
    def deactivate(self, updated_by=None):
        """Deactivate the user"""
        self.status = StatusEnum.INACTIVE
        self.updated_by = updated_by
    
    def suspend(self, updated_by=None):
        """Suspend the user"""
        self.status = StatusEnum.SUSPENDED
        self.updated_by = updated_by
    
    def delete(self, deleted_by=None):
        """Mark the user as deleted"""
        self.status = StatusEnum.DELETED
        self.deleted_by = deleted_by
        self.deleted_at = db.func.now()
        self.updated_by = deleted_by
    
    # Account management methods
    def add_account(self, account):
        """Add an account to the user"""
        if account not in self.accounts:
            self.accounts.append(account)
    
    def remove_account(self, account):
        """Remove an account from the user"""
        if account in self.accounts:
            self.accounts.remove(account)
    
    def get_active_accounts(self):
        """Get all active accounts for this user"""
        return [account for account in self.accounts if account.status == StatusEnum.ACTIVE]
    
    def get_inactive_accounts(self):
        """Get all inactive accounts for this user"""
        return [account for account in self.accounts if account.status == StatusEnum.INACTIVE]
    
    def get_suspended_accounts(self):
        """Get all suspended accounts for this user"""
        return [account for account in self.accounts if account.status == StatusEnum.SUSPENDED]
    
    def get_deleted_accounts(self):
        """Get all deleted accounts for this user"""
        return [account for account in self.accounts if account.status == StatusEnum.DELETED]
    
    # Utility methods
    def full_name(self):
        """Get the full name of the user"""
        name_parts = [self.first_name]
        if self.middle_name:
            name_parts.append(self.middle_name)
        if self.last_name:
            name_parts.append(self.last_name)
        return ' '.join(name_parts)
    
    def age(self):
        """Calculate the user's age"""
        if self.dob:
            today = datetime.now().date()
            return today.year - self.dob.year - ((today.month, today.day) < (self.dob.month, self.dob.day))
        return None
    
    def is_active(self):
        """Check if the user is active"""
        return self.status == StatusEnum.ACTIVE
    
    def is_inactive(self):
        """Check if the user is inactive"""
        return self.status == StatusEnum.INACTIVE
    
    def is_suspended(self):
        """Check if the user is suspended"""
        return self.status == StatusEnum.SUSPENDED
    
    def is_deleted(self):
        """Check if the user is deleted"""
        return self.status == StatusEnum.DELETED

class Role(db.Model):
    id = db.Column(db.UUID(as_uuid=True), primary_key=True)
    
    name = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.String(255), nullable=True)
    
    created_by = db.Column(db.String(100), nullable=True)
    created_at = db.Column(db.DateTime, server_default=db.func.now(), nullable=False)

    updated_by = db.Column(db.String(100), nullable=True)    
    updated_at = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now(), nullable=False)
    
    deleted_by = db.Column(db.String(100), nullable=True)   
    deleted_at = db.Column(db.DateTime, nullable=True)
    
    accounts = db.relationship('Account', secondary='account_roles', backref=db.backref('roles', lazy='dynamic'))

class AccountRoles(db.Model):
    __tablename__ = 'account_roles'
    
    account_id = db.Column(db.UUID(as_uuid=True), db.ForeignKey('account.id'), primary_key=True)
    role_id = db.Column(db.UUID(as_uuid=True), db.ForeignKey('role.id'), primary_key=True)

class Account(db.Model):
    id = db.Column(db.UUID(as_uuid=True), primary_key=True)
    
    user_id = db.Column(db.UUID(as_uuid=True), db.ForeignKey('user.id'), nullable=False)
    user = db.relationship('User', backref=db.backref('accounts', lazy=True))
    
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

    roles = db.relationship('Role', secondary='account_roles', backref=db.backref('accounts', lazy='dynamic'))
    
    status = db.Column(StatusEnum, default=StatusEnum.INACTIVE, nullable=False)
    
    
    def set_password(self, password):
        self.password_hash = bcrypt.generate_password_hash(password)
        self.password_set_on = db.func.now()
    
    def check_password(self, password):
        return bcrypt.check_password_hash(self.password_hash, password)
    
    def set_otp(self, otp):
        self.otp = otp
        self.otp_created_at = db.func.now()
    
    def check_otp(self, otp):
        nowtime = datetime.now()
        otp_time_delta = current_app.config.get('OTP_TIME_DELTA', 10)  # in minutes
        return self.otp == otp and nowtime - self.otp_created_at <= timedelta(minutes=otp_time_delta)
    
    
    def has_role(self, role_name):
        return any(role.name == role_name for role in self.roles)
    
    