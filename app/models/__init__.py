from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from app import db, login_manager
import enum

# Association table for form templates
form_template_questions = db.Table('form_template_questions',
    db.Column('template_id', db.Integer, db.ForeignKey('form_template.id'), primary_key=True),
    db.Column('question_id', db.Integer, db.ForeignKey('question.id'), primary_key=True)
)

class UserRoles(enum.Enum):
    ADMIN = 'admin'
    CREATOR = 'creator'
    ANALYST = 'analyst'
    RESPONDENT = 'respondent'

class User(UserMixin, db.Model):
    __tablename__ = 'user'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.Enum(UserRoles), default=UserRoles.CREATOR, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    is_verified = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Profile fields
    first_name = db.Column(db.String(50))
    last_name = db.Column(db.String(50))
    avatar = db.Column(db.String(255))  # URL to avatar image
    preferences = db.Column(db.JSON)  # User preferences as JSON

    # Password reset fields
    password_reset_token = db.Column(db.String(100), unique=True)
    password_reset_expires = db.Column(db.DateTime)
    
    # Relationships
    created_forms = db.relationship('Form', backref='creator', lazy=True, foreign_keys='Form.created_by')
    responses = db.relationship('Response', backref='user', lazy=True)
    created_templates = db.relationship('FormTemplate', backref='creator', lazy=True, foreign_keys='FormTemplate.created_by')
    created_questions = db.relationship('QuestionLibrary', backref='creator', lazy=True, foreign_keys='QuestionLibrary.created_by')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def has_role(self, role):
        return self.role == role
    
    def can_create_forms(self):
        return self.role in [UserRoles.ADMIN, UserRoles.CREATOR]
    
    def can_view_analytics(self):
        return self.role in [UserRoles.ADMIN, UserRoles.CREATOR, UserRoles.ANALYST]

    def generate_reset_token(self):
        """Generate a password reset token"""
        import secrets
        from datetime import datetime, timedelta
        self.password_reset_token = secrets.token_urlsafe(32)
        self.password_reset_expires = datetime.utcnow() + timedelta(hours=1)  # Token expires in 1 hour
        return self.password_reset_token

    def verify_reset_token(self, token):
        """Verify if the reset token is valid"""
        from datetime import datetime
        if self.password_reset_token == token and self.password_reset_expires > datetime.utcnow():
            return True
        return False

    def clear_reset_token(self):
        """Clear the reset token after use"""
        self.password_reset_token = None
        self.password_reset_expires = None

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
    
    def __repr__(self):
        return f'<User {self.username}>'

class Form(db.Model):
    __tablename__ = 'form'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    is_published = db.Column(db.Boolean, default=False)
    is_archived = db.Column(db.Boolean, default=False)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    published_at = db.Column(db.DateTime)
    
    # Form settings
    settings = db.Column(db.JSON)  # Form-specific settings like expiration, limit, etc.
    sharing_settings = db.Column(db.JSON)  # Who can access the form
    
    # Relationships
    sections = db.relationship('Section', backref='form', lazy=True, order_by='Section.order')
    responses = db.relationship('Response', backref='form', lazy=True)
    analytics_cache = db.Column(db.JSON)  # Cached analytics data
    template_id = db.Column(db.Integer, db.ForeignKey('form_template.id'))  # If form was created from a template
    
    def __repr__(self):
        return f'<Form {self.title}>'

class Section(db.Model):
    __tablename__ = 'section'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200))
    description = db.Column(db.Text)
    form_id = db.Column(db.Integer, db.ForeignKey('form.id'), nullable=False)
    order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    questions = db.relationship('Question', backref='section', lazy=True, order_by='Question.order')
    
    def __repr__(self):
        return f'<Section {self.title}>'

class QuestionTypes(enum.Enum):
    TEXT = 'text'
    LONG_TEXT = 'long_text'
    MULTIPLE_CHOICE = 'multiple_choice'
    CHECKBOX = 'checkbox'
    DROPDOWN = 'dropdown'
    RATING = 'rating'
    FILE_UPLOAD = 'file_upload'
    DATE = 'date'
    EMAIL = 'email'
    NUMBER = 'number'

class Question(db.Model):
    __tablename__ = 'question'
    
    id = db.Column(db.Integer, primary_key=True)
    section_id = db.Column(db.Integer, db.ForeignKey('section.id'), nullable=False)
    question_type = db.Column(db.Enum(QuestionTypes), nullable=False)
    question_text = db.Column(db.Text, nullable=False)
    is_required = db.Column(db.Boolean, default=False)
    order = db.Column(db.Integer, default=0)
    validation_rules = db.Column(db.JSON)  # Validation rules as JSON
    options = db.Column(db.JSON)  # For multiple choice, dropdown options
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    answers = db.relationship('Answer', backref='question', lazy=True)
    
    def __repr__(self):
        return f'<Question {self.question_text[:50]}>'

class Response(db.Model):
    __tablename__ = 'response'

    id = db.Column(db.Integer, primary_key=True)
    form_id = db.Column(db.Integer, db.ForeignKey('form.id'), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), index=True)
    ip_address = db.Column(db.String(45))  # IPv4 or IPv6
    user_agent = db.Column(db.Text)  # Browser info
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    completed_at = db.Column(db.DateTime)  # When the response was fully submitted
    
    # Relationships
    answers = db.relationship('Answer', backref='response', lazy=True)
    
    # Metadata
    meta = db.Column(db.JSON)  # Additional metadata about the response
    
    def __repr__(self):
        return f'<Response {self.id}>'

class Answer(db.Model):
    __tablename__ = 'answer'

    id = db.Column(db.Integer, primary_key=True)
    response_id = db.Column(db.Integer, db.ForeignKey('response.id'), nullable=False, index=True)
    question_id = db.Column(db.Integer, db.ForeignKey('question.id'), nullable=False, index=True)
    answer_text = db.Column(db.Text)  # For text answers
    answer_value = db.Column(db.JSON)  # For complex answers (checkboxes, files, etc.)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<Answer {self.id}>'

class FormTemplate(db.Model):
    __tablename__ = 'form_template'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    is_public = db.Column(db.Boolean, default=False)  # Whether other users can use this template
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Template content as JSON structure
    content = db.Column(db.JSON, nullable=False)  # Form structure as JSON
    
    # Relationships
    created_forms = db.relationship('Form', backref='template', lazy=True)
    
    def __repr__(self):
        return f'<FormTemplate {self.name}>'

class QuestionLibrary(db.Model):
    __tablename__ = 'question_library'
    
    id = db.Column(db.Integer, primary_key=True)
    question_text = db.Column(db.Text, nullable=False)
    question_type = db.Column(db.Enum(QuestionTypes), nullable=False)
    options = db.Column(db.JSON)  # For multiple choice, dropdown options
    is_public = db.Column(db.Boolean, default=False)  # Whether other users can use this question
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Validation rules
    validation_rules = db.Column(db.JSON)
    is_required = db.Column(db.Boolean, default=False)
    
    def __repr__(self):
        return f'<QuestionLibrary {self.question_text[:50]}>'

class AuditLog(db.Model):
    __tablename__ = 'audit_log'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    action = db.Column(db.String(100), nullable=False)  # 'create_form', 'submit_response', etc.
    resource_type = db.Column(db.String(50))  # 'form', 'response', 'user', etc.
    resource_id = db.Column(db.Integer) # ID of the resource acted upon
    details = db.Column(db.JSON)  # Additional details about the action
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref='audit_logs')
    
    def __repr__(self):
        return f'<AuditLog {self.action} at {self.timestamp}>'
