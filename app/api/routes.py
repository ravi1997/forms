from flask import request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import db
from app.api import bp
from app.models import User, Form, Section, Question, Response, Answer, FormTemplate, QuestionLibrary, AuditLog, UserRoles, QuestionTypes
from app.schemas import (
    UserSchema, FormSchema, SectionSchema, QuestionSchema, ResponseSchema,
    AnswerSchema, FormTemplateSchema, QuestionLibrarySchema, AuditLogSchema,
    CreateFormSchema, UpdateFormSchema, CreateSectionSchema, UpdateSectionSchema,
    CreateQuestionSchema, UpdateQuestionSchema, SubmitResponseSchema,
    CreateTemplateSchema, CreateQuestionLibrarySchema
)
from datetime import datetime
from sqlalchemy.exc import IntegrityError

# Schema instances
user_schema = UserSchema()
users_schema = UserSchema(many=True)
form_schema = FormSchema()
forms_schema = FormSchema(many=True)
section_schema = SectionSchema()
sections_schema = SectionSchema(many=True)
question_schema = QuestionSchema()
questions_schema = QuestionSchema(many=True)
response_schema = ResponseSchema()
responses_schema = ResponseSchema(many=True)
answer_schema = AnswerSchema()
answers_schema = AnswerSchema(many=True)
template_schema = FormTemplateSchema()
templates_schema = FormTemplateSchema(many=True)
question_lib_schema = QuestionLibrarySchema()
question_libs_schema = QuestionLibrarySchema(many=True)

# Utility function to create audit log
def create_audit_log(user_id, action, resource_type, resource_id, details=None, ip_address=None, user_agent=None):
    audit_log = AuditLog(
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        details=details,
        ip_address=ip_address,
        user_agent=user_agent
    )
    db.session.add(audit_log)
    db.session.commit()

@bp.route('/users', methods=['GET'])
@jwt_required()
def get_users():
    """Get all users (admin only)"""
    current_user_id = get_jwt_identity()
    current_user = User.query.get(current_user_id)
    
    if not current_user or current_user.role != UserRoles.ADMIN:
        return jsonify({'error': 'forbidden', 'message': 'Access denied'}), 403
    
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 10, type=int), 100)
    
    users = User.query.paginate(page=page, per_page=per_page, error_out=False)
    result = users_schema.dump(users.items)
    
    return jsonify({
        'data': result,
        'pagination': {
            'page': page,
            'pages': users.pages,
            'per_page': per_page,
            'total': users.total
        }
    }), 200

@bp.route('/users/profile', methods=['GET'])
@jwt_required()
def get_current_user_profile():
    """Get current user's profile"""
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    
    if not user:
        return jsonify({'error': 'user_not_found', 'message': 'User not found'}), 404
    
    return jsonify({'data': user_schema.dump(user)}), 200

@bp.route('/users/profile', methods=['PUT'])
@jwt_required()
def update_current_user_profile():
    """Update current user's profile"""
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    
    if not user:
        return jsonify({'error': 'user_not_found', 'message': 'User not found'}), 404
    
    # Get update data
    first_name = request.json.get('first_name')
    last_name = request.json.get('last_name')
    email = request.json.get('email')
    preferences = request.json.get('preferences')
    
    # Update fields if provided
    if first_name is not None:
        user.first_name = first_name
    if last_name is not None:
        user.last_name = last_name
    if email is not None:
        # Check if email is already taken by another user
        existing_user = User.query.filter_by(email=email).first()
        if existing_user and existing_user.id != user.id:
            return jsonify({'error': 'email_exists', 'message': 'Email already registered'}), 409
        user.email = email
    if preferences is not None:
        user.preferences = preferences
    
    user.updated_at = datetime.utcnow()
    db.session.commit()
    
    # Create audit log
    create_audit_log(
        user_id=user.id,
        action='update_profile',
        resource_type='user',
        resource_id=user.id,
        details={'updated_fields': [f for f in ['first_name', 'last_name', 'email', 'preferences'] if request.json.get(f) is not None]},
        ip_address=request.environ.get('REMOTE_ADDR'),
        user_agent=request.headers.get('User-Agent')
    )
    
    return jsonify({'message': 'Profile updated successfully', 'data': user_schema.dump(user)}), 200

@bp.route('/forms', methods=['GET'])
@jwt_required()
def get_forms():
    """Get all forms for the current user"""
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)

    if not user:
        return jsonify({'error': 'user_not_found', 'message': 'User not found'}), 404

    print(f"DEBUG get_forms: user role: {user.role}")
    
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 10, type=int), 100)
    status = request.args.get('status')  # 'published', 'draft', 'archived'
    
    query = Form.query.filter_by(created_by=current_user_id)
    
    if status:
        if status == 'published':
            query = query.filter_by(is_published=True)
        elif status == 'draft':
            query = query.filter_by(is_published=False, is_archived=False)
        elif status == 'archived':
            query = query.filter_by(is_archived=True)
    
    forms = query.paginate(page=page, per_page=per_page, error_out=False)
    result = forms_schema.dump(forms.items)
    
    return jsonify({
        'data': result,
        'pagination': {
            'page': page,
            'pages': forms.pages,
            'per_page': per_page,
            'total': forms.total
        }
    }), 200

@bp.route('/forms', methods=['POST'])
@jwt_required()
def create_form():
    """Create a new form"""
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)

    if not user:
        return jsonify({'error': 'user_not_found', 'message': 'User not found'}), 404

    print(f"DEBUG: user role: {user.role}, can_create: {user.can_create_forms()}")

    if not user.can_create_forms():
        return jsonify({'error': 'forbidden', 'message': 'You do not have permission to create forms'}), 403
    
    # Validate input
    errors = CreateFormSchema().validate(request.json)
    if errors:
        return jsonify({'error': 'validation_error', 'message': 'Invalid input data', 'details': errors}), 400
    
    # Extract data
    title = request.json.get('title')
    description = request.json.get('description', '')
    settings = request.json.get('settings', {})
    
    # Create form
    form = Form(
        title=title,
        description=description,
        settings=settings,
        created_by=current_user_id
    )
    
    db.session.add(form)
    db.session.commit()
    
    # Create audit log
    create_audit_log(
        user_id=user.id,
        action='create_form',
        resource_type='form',
        resource_id=form.id,
        details={'title': title},
        ip_address=request.environ.get('REMOTE_ADDR'),
        user_agent=request.headers.get('User-Agent')
    )
    
    return jsonify({'message': 'Form created successfully', 'data': form_schema.dump(form)}), 201

@bp.route('/forms/<int:form_id>', methods=['GET'])
@jwt_required()
def get_form(form_id):
    """Get detailed information about a specific form"""
    current_user_id = get_jwt_identity()
    form = Form.query.get(form_id)
    
    if not form:
        return jsonify({'error': 'form_not_found', 'message': 'Form not found'}), 404
    
    # Check if user has access to this form
    if form.created_by != current_user_id and form.is_published == False:
        return jsonify({'error': 'forbidden', 'message': 'You do not have access to this form'}), 403
    
    return jsonify({'data': form_schema.dump(form)}), 200

@bp.route('/forms/<int:form_id>', methods=['PUT'])
@jwt_required()
def update_form(form_id):
    """Update form information"""
    current_user_id = get_jwt_identity()
    form = Form.query.get(form_id)
    
    if not form:
        return jsonify({'error': 'form_not_found', 'message': 'Form not found'}), 404
    
    # Check if user has permission to update this form
    if form.created_by != current_user_id:
        return jsonify({'error': 'forbidden', 'message': 'You do not have permission to update this form'}), 403
    
    # Validate input
    errors = UpdateFormSchema().validate(request.json)
    if errors:
        return jsonify({'error': 'validation_error', 'message': 'Invalid input data', 'details': errors}), 400
    
    # Update fields if provided
    if 'title' in request.json:
        form.title = request.json['title']
    if 'description' in request.json:
        form.description = request.json['description']
    if 'settings' in request.json:
        form.settings = request.json['settings']
    if 'is_published' in request.json:
        form.is_published = request.json['is_published']
        if form.is_published and not form.published_at:
            form.published_at = datetime.utcnow()
    
    form.updated_at = datetime.utcnow()
    db.session.commit()
    
    # Create audit log
    create_audit_log(
        user_id=current_user_id,
        action='update_form',
        resource_type='form',
        resource_id=form.id,
        details={'updated_fields': list(request.json.keys())},
        ip_address=request.environ.get('REMOTE_ADDR'),
        user_agent=request.headers.get('User-Agent')
    )
    
    return jsonify({'message': 'Form updated successfully', 'data': form_schema.dump(form)}), 200

@bp.route('/forms/<int:form_id>', methods=['DELETE'])
@jwt_required()
def delete_form(form_id):
    """Delete a form"""
    current_user_id = get_jwt_identity()
    form = Form.query.get(form_id)
    
    if not form:
        return jsonify({'error': 'form_not_found', 'message': 'Form not found'}), 404
    
    # Check if user has permission to delete this form
    if form.created_by != current_user_id:
        return jsonify({'error': 'forbidden', 'message': 'You do not have permission to delete this form'}), 403
    
    db.session.delete(form)
    db.session.commit()
    
    # Create audit log
    create_audit_log(
        user_id=current_user_id,
        action='delete_form',
        resource_type='form',
        resource_id=form_id,
        details={'title': form.title},
        ip_address=request.environ.get('REMOTE_ADDR'),
        user_agent=request.headers.get('User-Agent')
    )
    
    return jsonify({'message': 'Form deleted successfully'}), 204

@bp.route('/forms/<int:form_id>/publish', methods=['POST'])
@jwt_required()
def publish_form(form_id):
    """Publish a form to make it available for responses"""
    current_user_id = get_jwt_identity()
    form = Form.query.get(form_id)
    
    if not form:
        return jsonify({'error': 'form_not_found', 'message': 'Form not found'}), 404
    
    # Check if user has permission to publish this form
    if form.created_by != current_user_id:
        return jsonify({'error': 'forbidden', 'message': 'You do not have permission to publish this form'}), 403
    
    if form.is_published:
        return jsonify({'message': 'Form is already published'}), 200
    
    form.is_published = True
    form.published_at = datetime.utcnow()
    form.updated_at = datetime.utcnow()
    db.session.commit()
    
    # Create audit log
    create_audit_log(
        user_id=current_user_id,
        action='publish_form',
        resource_type='form',
        resource_id=form.id,
        details={'title': form.title},
        ip_address=request.environ.get('REMOTE_ADDR'),
        user_agent=request.headers.get('User-Agent')
    )
    
    return jsonify({'message': 'Form published successfully', 'data': form_schema.dump(form)}), 200

@bp.route('/forms/<int:form_id>/unpublish', methods=['POST'])
@jwt_required()
def unpublish_form(form_id):
    """Unpublish a form to stop accepting responses"""
    current_user_id = get_jwt_identity()
    form = Form.query.get(form_id)
    
    if not form:
        return jsonify({'error': 'form_not_found', 'message': 'Form not found'}), 404
    
    # Check if user has permission to unpublish this form
    if form.created_by != current_user_id:
        return jsonify({'error': 'forbidden', 'message': 'You do not have permission to unpublish this form'}), 403
    
    if not form.is_published:
        return jsonify({'message': 'Form is already unpublished'}), 200
    
    form.is_published = False
    form.updated_at = datetime.utcnow()
    db.session.commit()
    
    # Create audit log
    create_audit_log(
        user_id=current_user_id,
        action='unpublish_form',
        resource_type='form',
        resource_id=form.id,
        details={'title': form.title},
        ip_address=request.environ.get('REMOTE_ADDR'),
        user_agent=request.headers.get('User-Agent')
    )
    
    return jsonify({'message': 'Form unpublished successfully', 'data': form_schema.dump(form)}), 200

@bp.route('/forms/<int:form_id>/sections', methods=['GET'])
@jwt_required()
def get_form_sections(form_id):
    """Get all sections of a form"""
    current_user_id = get_jwt_identity()
    form = Form.query.get(form_id)
    
    if not form:
        return jsonify({'error': 'form_not_found', 'message': 'Form not found'}), 404
    
    # Check if user has access to this form
    if form.created_by != current_user_id:
        return jsonify({'error': 'forbidden', 'message': 'You do not have access to this form'}), 403
    
    sections = Section.query.filter_by(form_id=form_id).order_by(Section.order).all()
    result = sections_schema.dump(sections)
    
    return jsonify({'data': result}), 200

@bp.route('/forms/<int:form_id>/sections', methods=['POST'])
@jwt_required()
def create_section(form_id):
    """Create a new section in a form"""
    current_user_id = get_jwt_identity()
    form = Form.query.get(form_id)
    
    if not form:
        return jsonify({'error': 'form_not_found', 'message': 'Form not found'}), 404
    
    # Check if user has permission to modify this form
    if form.created_by != current_user_id:
        return jsonify({'error': 'forbidden', 'message': 'You do not have permission to modify this form'}), 403
    
    # Validate input
    errors = CreateSectionSchema().validate(request.json)
    if errors:
        return jsonify({'error': 'validation_error', 'message': 'Invalid input data', 'details': errors}), 400
    
    # Extract data
    title = request.json.get('title', '')
    description = request.json.get('description', '')
    order = request.json.get('order', 0)
    
    # Create section
    section = Section(
        title=title,
        description=description,
        form_id=form_id,
        order=order
    )
    
    db.session.add(section)
    db.session.commit()
    
    # Create audit log
    create_audit_log(
        user_id=current_user_id,
        action='create_section',
        resource_type='section',
        resource_id=section.id,
        details={'title': title, 'form_id': form_id},
        ip_address=request.environ.get('REMOTE_ADDR'),
        user_agent=request.headers.get('User-Agent')
    )
    
    return jsonify({'message': 'Section created successfully', 'data': section_schema.dump(section)}), 201

@bp.route('/sections/<int:section_id>', methods=['PUT'])
@jwt_required()
def update_section(section_id):
    """Update a section"""
    current_user_id = get_jwt_identity()
    section = Section.query.get(section_id)
    
    if not section:
        return jsonify({'error': 'section_not_found', 'message': 'Section not found'}), 404
    
    # Check if user has permission to modify this section
    if section.form.created_by != current_user_id:
        return jsonify({'error': 'forbidden', 'message': 'You do not have permission to modify this section'}), 403
    
    # Validate input
    errors = UpdateSectionSchema().validate(request.json)
    if errors:
        return jsonify({'error': 'validation_error', 'message': 'Invalid input data', 'details': errors}), 400
    
    # Update fields if provided
    if 'title' in request.json:
        section.title = request.json['title']
    if 'description' in request.json:
        section.description = request.json['description']
    if 'order' in request.json:
        section.order = request.json['order']
    
    section.updated_at = datetime.utcnow()
    db.session.commit()
    
    # Create audit log
    create_audit_log(
        user_id=current_user_id,
        action='update_section',
        resource_type='section',
        resource_id=section.id,
        details={'updated_fields': list(request.json.keys())},
        ip_address=request.environ.get('REMOTE_ADDR'),
        user_agent=request.headers.get('User-Agent')
    )
    
    return jsonify({'message': 'Section updated successfully', 'data': section_schema.dump(section)}), 20

@bp.route('/sections/<int:section_id>', methods=['DELETE'])
@jwt_required()
def delete_section(section_id):
    """Delete a section (and all its questions)"""
    current_user_id = get_jwt_identity()
    section = Section.query.get(section_id)
    
    if not section:
        return jsonify({'error': 'section_not_found', 'message': 'Section not found'}), 404
    
    # Check if user has permission to delete this section
    if section.form.created_by != current_user_id:
        return jsonify({'error': 'forbidden', 'message': 'You do not have permission to delete this section'}), 403
    
    db.session.delete(section)
    db.session.commit()
    
    # Create audit log
    create_audit_log(
        user_id=current_user_id,
        action='delete_section',
        resource_type='section',
        resource_id=section_id,
        details={'title': section.title, 'form_id': section.form_id},
        ip_address=request.environ.get('REMOTE_ADDR'),
        user_agent=request.headers.get('User-Agent')
    )
    
    return jsonify({'message': 'Section deleted successfully'}), 204

@bp.route('/sections/<int:section_id>/questions', methods=['GET'])
@jwt_required()
def get_section_questions(section_id):
    """Get all questions in a section"""
    current_user_id = get_jwt_identity()
    section = Section.query.get(section_id)
    
    if not section:
        return jsonify({'error': 'section_not_found', 'message': 'Section not found'}), 404
    
    # Check if user has access to this section
    if section.form.created_by != current_user_id:
        return jsonify({'error': 'forbidden', 'message': 'You do not have access to this section'}), 403
    
    questions = Question.query.filter_by(section_id=section_id).order_by(Question.order).all()
    result = questions_schema.dump(questions)
    
    return jsonify({'data': result}), 200

@bp.route('/sections/<int:section_id>/questions', methods=['POST'])
@jwt_required()
def create_question(section_id):
    """Create a new question in a section"""
    current_user_id = get_jwt_identity()
    section = Section.query.get(section_id)
    
    if not section:
        return jsonify({'error': 'section_not_found', 'message': 'Section not found'}), 404
    
    # Check if user has permission to modify this section
    if section.form.created_by != current_user_id:
        return jsonify({'error': 'forbidden', 'message': 'You do not have permission to modify this section'}), 403
    
    # Validate input
    errors = CreateQuestionSchema().validate(request.json)
    if errors:
        return jsonify({'error': 'validation_error', 'message': 'Invalid input data', 'details': errors}), 400
    
    # Extract data
    question_type = request.json.get('question_type')
    question_text = request.json.get('question_text')
    is_required = request.json.get('is_required', False)
    order = request.json.get('order', 0)
    validation_rules = request.json.get('validation_rules', {})
    options = request.json.get('options', [])
    
    # Create question
    question = Question(
        section_id=section_id,
        question_type=question_type,
        question_text=question_text,
        is_required=is_required,
        order=order,
        validation_rules=validation_rules,
        options=options
    )
    
    db.session.add(question)
    db.session.commit()
    
    # Create audit log
    create_audit_log(
        user_id=current_user_id,
        action='create_question',
        resource_type='question',
        resource_id=question.id,
        details={'question_text': question_text, 'question_type': question_type.value, 'section_id': section_id},
        ip_address=request.environ.get('REMOTE_ADDR'),
        user_agent=request.headers.get('User-Agent')
    )
    
    return jsonify({'message': 'Question created successfully', 'data': question_schema.dump(question)}), 201

@bp.route('/questions/<int:question_id>', methods=['PUT'])
@jwt_required()
def update_question(question_id):
    """Update a question"""
    current_user_id = get_jwt_identity()
    question = Question.query.get(question_id)
    
    if not question:
        return jsonify({'error': 'question_not_found', 'message': 'Question not found'}), 404
    
    # Check if user has permission to modify this question
    if question.section.form.created_by != current_user_id:
        return jsonify({'error': 'forbidden', 'message': 'You do not have permission to modify this question'}), 403
    
    # Validate input
    errors = UpdateQuestionSchema().validate(request.json)
    if errors:
        return jsonify({'error': 'validation_error', 'message': 'Invalid input data', 'details': errors}), 400
    
    # Update fields if provided
    if 'question_type' in request.json:
        question.question_type = request.json['question_type']
    if 'question_text' in request.json:
        question.question_text = request.json['question_text']
    if 'is_required' in request.json:
        question.is_required = request.json['is_required']
    if 'order' in request.json:
        question.order = request.json['order']
    if 'validation_rules' in request.json:
        question.validation_rules = request.json['validation_rules']
    if 'options' in request.json:
        question.options = request.json['options']
    
    question.updated_at = datetime.utcnow()
    db.session.commit()
    
    # Create audit log
    create_audit_log(
        user_id=current_user_id,
        action='update_question',
        resource_type='question',
        resource_id=question.id,
        details={'updated_fields': list(request.json.keys())},
        ip_address=request.environ.get('REMOTE_ADDR'),
        user_agent=request.headers.get('User-Agent')
    )
    
    return jsonify({'message': 'Question updated successfully', 'data': question_schema.dump(question)}), 200

@bp.route('/questions/<int:question_id>', methods=['DELETE'])
@jwt_required()
def delete_question(question_id):
    """Delete a question"""
    current_user_id = get_jwt_identity()
    question = Question.query.get(question_id)
    
    if not question:
        return jsonify({'error': 'question_not_found', 'message': 'Question not found'}), 404
    
    # Check if user has permission to delete this question
    if question.section.form.created_by != current_user_id:
        return jsonify({'error': 'forbidden', 'message': 'You do not have permission to delete this question'}), 403
    
    db.session.delete(question)
    db.session.commit()
    
    # Create audit log
    create_audit_log(
        user_id=current_user_id,
        action='delete_question',
        resource_type='question',
        resource_id=question_id,
        details={'question_text': question.question_text, 'section_id': question.section_id},
        ip_address=request.environ.get('REMOTE_ADDR'),
        user_agent=request.headers.get('User-Agent')
    )
    
    return jsonify({'message': 'Question deleted successfully'}), 204

@bp.route('/forms/<int:form_id>/responses', methods=['POST'])
def submit_form_response(form_id):
    """Submit a response to a form"""
    # Check if form exists and is published
    form = Form.query.get(form_id)
    
    if not form:
        return jsonify({'error': 'form_not_found', 'message': 'Form not found'}), 404
    
    if not form.is_published:
        return jsonify({'error': 'form_not_published', 'message': 'Form is not published'}), 404
    
    # Validate input
    errors = SubmitResponseSchema().validate(request.json)
    if errors:
        return jsonify({'error': 'validation_error', 'message': 'Invalid input data', 'details': errors}), 400
    
    # Extract answers
    answers_data = request.json.get('answers', [])
    
    # Verify that all question IDs belong to this form
    question_ids = [ans['question_id'] for ans in answers_data]
    questions = Question.query.filter(Question.id.in_(question_ids), Question.section.has(form_id=form_id)).all()
    valid_question_ids = [q.id for q in questions]
    
    invalid_questions = set(question_ids) - set(valid_question_ids)
    if invalid_questions:
        return jsonify({'error': 'invalid_questions', 'message': f'Invalid question IDs: {list(invalid_questions)}'}), 400
    
    # Create response
    current_user_id = get_jwt_identity() if hasattr(request, 'jwt') else None
    
    response = Response(
        form_id=form_id,
        user_id=current_user_id,
        ip_address=request.environ.get('REMOTE_ADDR'),
        user_agent=request.headers.get('User-Agent'),
        metadata={'submitted_from': 'web'}
    )
    
    db.session.add(response)
    db.session.flush() # Get the response ID without committing
    
    # Create answers
    for answer_data in answers_data:
        question_id = answer_data['question_id']
        answer_text = answer_data.get('answer_text')
        answer_value = answer_data.get('answer_value')
        
        answer = Answer(
            response_id=response.id,
            question_id=question_id,
            answer_text=answer_text,
            answer_value=answer_value
        )
        db.session.add(answer)
    
    db.session.commit()
    
    # Create audit log
    create_audit_log(
        user_id=current_user_id or 0,  # Use 0 for anonymous responses
        action='submit_response',
        resource_type='response',
        resource_id=response.id,
        details={'form_id': form_id, 'answer_count': len(answers_data)},
        ip_address=request.environ.get('REMOTE_ADDR'),
        user_agent=request.headers.get('User-Agent')
    )
    
    return jsonify({'message': 'Response submitted successfully', 'data': response_schema.dump(response)}), 201

@bp.route('/forms/<int:form_id>/responses', methods=['GET'])
@jwt_required()
def get_form_responses(form_id):
    """Get all responses for a form"""
    current_user_id = get_jwt_identity()
    form = Form.query.get(form_id)
    
    if not form:
        return jsonify({'error': 'form_not_found', 'message': 'Form not found'}), 404
    
    # Check if user has permission to view responses
    if form.created_by != current_user_id and not User.query.get(current_user_id).can_view_analytics():
        return jsonify({'error': 'forbidden', 'message': 'You do not have permission to view responses'}), 403
    
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 10, type=int), 100)
    
    responses = Response.query.filter_by(form_id=form_id).paginate(page=page, per_page=per_page, error_out=False)
    result = responses_schema.dump(responses.items)
    
    return jsonify({
        'data': result,
        'pagination': {
            'page': page,
            'pages': responses.pages,
            'per_page': per_page,
            'total': responses.total
        }
    }), 200

@bp.route('/responses/<int:response_id>', methods=['GET'])
@jwt_required()
def get_response(response_id):
    """Get details of a specific response"""
    current_user_id = get_jwt_identity()
    response = Response.query.get(response_id)
    
    if not response:
        return jsonify({'error': 'response_not_found', 'message': 'Response not found'}), 404
    
    # Check if user has permission to view this response
    form = response.form
    if form.created_by != current_user_id and not User.query.get(current_user_id).can_view_analytics():
        return jsonify({'error': 'forbidden', 'message': 'You do not have permission to view this response'}), 403
    
    return jsonify({'data': response_schema.dump(response)}), 200

@bp.route('/templates', methods=['GET'])
@jwt_required()
def get_templates():
    """Get available form templates"""
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    
    if not user:
        return jsonify({'error': 'user_not_found', 'message': 'User not found'}), 404
    
    # Get query parameter for public templates
    include_public = request.args.get('public', 'false').lower() == 'true'
    
    query = FormTemplate.query
    
    if not include_public:
        # Only get templates created by this user
        query = query.filter_by(created_by=current_user_id)
    else:
        # Get templates created by this user OR public templates
        query = query.filter(
            (FormTemplate.created_by == current_user_id) | 
            (FormTemplate.is_public == True)
        )
    
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 10, type=int), 100)
    
    templates = query.paginate(page=page, per_page=per_page, error_out=False)
    result = templates_schema.dump(templates.items)
    
    return jsonify({
        'data': result,
        'pagination': {
            'page': page,
            'pages': templates.pages,
            'per_page': per_page,
            'total': templates.total
        }
    }), 200

@bp.route('/templates', methods=['POST'])
@jwt_required()
def create_template():
    """Create a new form template"""
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    
    if not user:
        return jsonify({'error': 'user_not_found', 'message': 'User not found'}), 404
    
    # Validate input
    errors = CreateTemplateSchema().validate(request.json)
    if errors:
        return jsonify({'error': 'validation_error', 'message': 'Invalid input data', 'details': errors}), 400
    
    # Extract data
    name = request.json.get('name')
    description = request.json.get('description', '')
    is_public = request.json.get('is_public', False)
    content = request.json.get('content')
    
    # Create template
    template = FormTemplate(
        name=name,
        description=description,
        is_public=is_public,
        created_by=current_user_id,
        content=content
    )
    
    db.session.add(template)
    db.session.commit()
    
    # Create audit log
    create_audit_log(
        user_id=current_user_id,
        action='create_template',
        resource_type='template',
        resource_id=template.id,
        details={'name': name, 'is_public': is_public},
        ip_address=request.environ.get('REMOTE_ADDR'),
        user_agent=request.headers.get('User-Agent')
    )
    
    return jsonify({'message': 'Template created successfully', 'data': template_schema.dump(template)}), 201

@bp.route('/templates/<int:template_id>/use', methods=['POST'])
@jwt_required()
def use_template(template_id):
    """Create a new form using a template"""
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    
    if not user:
        return jsonify({'error': 'user_not_found', 'message': 'User not found'}), 404
    
    if not user.can_create_forms():
        return jsonify({'error': 'forbidden', 'message': 'You do not have permission to create forms'}), 403
    
    template = FormTemplate.query.get(template_id)
    
    if not template:
        return jsonify({'error': 'template_not_found', 'message': 'Template not found'}), 404
    
    # Check if user has access to this template
    if not template.is_public and template.created_by != current_user_id:
        return jsonify({'error': 'forbidden', 'message': 'You do not have access to this template'}), 403
    
    # Extract form data
    title = request.json.get('title')
    description = request.json.get('description', '')
    
    if not title:
        return jsonify({'error': 'validation_error', 'message': 'Title is required'}), 400
    
    # Create new form from template
    form = Form(
        title=title,
        description=description,
        created_by=current_user_id,
        template_id=template_id
    )
    
    db.session.add(form)
    db.session.flush() # Get form ID without committing
    
    # Create sections and questions from template content
    template_content = template.content
    if 'sections' in template_content:
        for section_data in template_content['sections']:
            section = Section(
                title=section_data.get('title', ''),
                description=section_data.get('description', ''),
                form_id=form.id,
                order=section_data.get('order', 0)
            )
            db.session.add(section)
            db.session.flush()  # Get section ID without committing
            
            # Add questions to the section
            if 'questions' in section_data:
                for question_data in section_data['questions']:
                    question = Question(
                        section_id=section.id,
                        question_type=question_data['question_type'],
                        question_text=question_data['question_text'],
                        is_required=question_data.get('is_required', False),
                        order=question_data.get('order', 0),
                        validation_rules=question_data.get('validation_rules', {}),
                        options=question_data.get('options', [])
                    )
                    db.session.add(question)
    
    db.session.commit()
    
    # Create audit log
    create_audit_log(
        user_id=current_user_id,
        action='create_form_from_template',
        resource_type='form',
        resource_id=form.id,
        details={'template_id': template_id, 'title': title},
        ip_address=request.environ.get('REMOTE_ADDR'),
        user_agent=request.headers.get('User-Agent')
    )
    
    return jsonify({'message': 'Form created from template successfully', 'data': form_schema.dump(form)}), 201