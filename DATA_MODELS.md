# Database Models Specification

## User Model
```python
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.Enum('admin', 'creator', 'analyst', 'respondent', name='user_roles'), default='respondent')
    is_active = db.Column(db.Boolean, default=True)
    is_verified = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    created_forms = db.relationship('Form', backref='creator', lazy=True)
    responses = db.relationship('Response', backref='user', lazy=True)
    
    # Profile fields
    first_name = db.Column(db.String(50))
    last_name = db.Column(db.String(50))
    avatar = db.Column(db.String(255))  # URL to avatar image
    preferences = db.Column(db.JSON)  # User preferences as JSON
```

## Form Model
```python
class Form(db.Model):
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
```

## Section Model
```python
class Section(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200))
    description = db.Column(db.Text)
    form_id = db.Column(db.Integer, db.ForeignKey('form.id'), nullable=False)
    order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    questions = db.relationship('Question', backref='section', lazy=True, order_by='Question.order')
```

## Question Model
```python
class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    section_id = db.Column(db.Integer, db.ForeignKey('section.id'), nullable=False)
    question_type = db.Column(db.Enum(
        'text', 'long_text', 'multiple_choice', 'checkbox', 
        'dropdown', 'rating', 'file_upload', 'date', 
        'email', 'number', name='question_types'
    ), nullable=False)
    question_text = db.Column(db.Text, nullable=False)
    is_required = db.Column(db.Boolean, default=False)
    order = db.Column(db.Integer, default=0)
    validation_rules = db.Column(db.JSON)  # Validation rules as JSON
    options = db.Column(db.JSON)  # For multiple choice, dropdown options
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    answers = db.relationship('Answer', backref='question', lazy=True)
```

## Response Model
```python
class Response(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    form_id = db.Column(db.Integer, db.ForeignKey('form.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    ip_address = db.Column(db.String(45))  # IPv4 or IPv6
    user_agent = db.Column(db.Text)  # Browser info
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime)  # When the response was fully submitted
    
    # Relationships
    answers = db.relationship('Answer', backref='response', lazy=True)
    
    # Metadata
    metadata = db.Column(db.JSON)  # Additional metadata about the response
```

## Answer Model
```python
class Answer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    response_id = db.Column(db.Integer, db.ForeignKey('response.id'), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('question.id'), nullable=False)
    answer_text = db.Column(db.Text)  # For text answers
    answer_value = db.Column(db.JSON)  # For complex answers (checkboxes, files, etc.)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

## Form Template Model
```python
class FormTemplate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    is_public = db.Column(db.Boolean, default=False)  # Whether other users can use this template
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Template content as JSON structure
    content = db.Column(db.JSON, nullable=False) # Form structure as JSON
    
    # Relationships
    created_forms = db.relationship('Form', backref='template', lazy=True)
```

## Question Library Model
```python
class QuestionLibrary(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    question_text = db.Column(db.Text, nullable=False)
    question_type = db.Column(db.Enum(
        'text', 'long_text', 'multiple_choice', 'checkbox', 
        'dropdown', 'rating', 'file_upload', 'date', 
        'email', 'number', name='question_types'
    ), nullable=False)
    options = db.Column(db.JSON)  # For multiple choice, dropdown options
    is_public = db.Column(db.Boolean, default=False)  # Whether other users can use this question
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Validation rules
    validation_rules = db.Column(db.JSON)
    is_required = db.Column(db.Boolean, default=False)
```

## Audit Log Model
```python
class AuditLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    action = db.Column(db.String(100), nullable=False)  # 'create_form', 'submit_response', etc.
    resource_type = db.Column(db.String(50))  # 'form', 'response', 'user', etc.
    resource_id = db.Column(db.Integer)  # ID of the resource acted upon
    details = db.Column(db.JSON)  # Additional details about the action
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
```

## Schema Definitions (Marshmallow)

### User Schema
```python
class UserSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = User
        load_instance = True
        exclude = ('password_hash',)
    
    responses = ma.Nested(lambda: ResponseSchema, many=True, exclude=('user',))
    created_forms = ma.Nested(lambda: FormSchema, many=True, exclude=('creator',))
```

### Form Schema
```python
class FormSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Form
        load_instance = True
    
    creator = ma.Nested(UserSchema, exclude=('created_forms', 'responses'))
    sections = ma.Nested(lambda: SectionSchema, many=True)
    responses = ma.Nested(lambda: ResponseSchema, many=True, exclude=('form',))
```

### Section Schema
```python
class SectionSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Section
        load_instance = True
    
    questions = ma.Nested(lambda: QuestionSchema, many=True)
```

### Question Schema
```python
class QuestionSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Question
        load_instance = True
```

### Response Schema
```python
class ResponseSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Response
        load_instance = True
    
    form = ma.Nested(FormSchema, exclude=('responses',))
    user = ma.Nested(UserSchema, exclude=('responses', 'created_forms'))
    answers = ma.Nested(lambda: AnswerSchema, many=True)
```

### Answer Schema
```python
class AnswerSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Answer
        load_instance = True
    
    question = ma.Nested(QuestionSchema)