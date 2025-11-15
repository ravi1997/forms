from flask import render_template, request, jsonify, current_app, redirect, url_for
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import db
from app.forms import bp
from app.models import User, Form, Section, Question, Response, Answer, FormTemplate, QuestionLibrary
from app.schemas import FormSchema, SectionSchema, QuestionSchema
from datetime import datetime

form_schema = FormSchema()
section_schema = SectionSchema()
question_schema = QuestionSchema()

@bp.route('/<int:form_id>', methods=['GET'])
def display_form(form_id):
    """Display a form to be filled by respondents"""
    form = Form.query.get_or_404(form_id)
    
    if not form.is_published:
        return render_template('forms/form_not_available.html'), 404
    
    # Get form sections and questions
    sections = Section.query.filter_by(form_id=form_id).order_by(Section.order).all()
    
    # For each section, get its questions
    for section in sections:
        section.questions = Question.query.filter_by(section_id=section.id).order_by(Question.order).all()
    
    return render_template('forms/display_form.html', form=form, sections=sections)

@bp.route('/<int:form_id>/submit', methods=['POST'])
def submit_form(form_id):
    """Handle form submission"""
    form = Form.query.get_or_404(form_id)
    
    if not form.is_published:
        return render_template('forms/form_not_available.html'), 404
    
    # Get current user if authenticated, otherwise None
    try:
        current_user_id = get_jwt_identity()
        current_user = User.query.get(current_user_id)
    except:
        current_user = None
    
    # Create response
    response = Response(
        form_id=form_id,
        user_id=current_user.id if current_user else None,
        ip_address=request.environ.get('REMOTE_ADDR'),
        user_agent=request.headers.get('User-Agent'),
        metadata={'submitted_from': 'web'}
    )
    
    db.session.add(response)
    db.session.flush()  # Get the response ID without committing
    
    # Process form data
    form_data = request.form
    sections = Section.query.filter_by(form_id=form_id).order_by(Section.order).all()
    
    for section in sections:
        questions = Question.query.filter_by(section_id=section.id).order_by(Question.order).all()
        
        for question in questions:
            # Get the answer from form data
            if question.question_type in ['checkbox', 'multiple_choice']:
                answer_values = form_data.getlist(f'question_{question.id}')
                answer_value = answer_values if len(answer_values) > 1 else answer_values[0] if answer_values else None
                answer_text = None
            elif question.question_type == 'file_upload':
                file = request.files.get(f'question_{question.id}')
                if file and file.filename != '':
                    # Handle file upload
                    import os
                    from werkzeug.utils import secure_filename
                    from datetime import datetime
                    
                    # Define upload folder and create if it doesn't exist
                    upload_folder = current_app.config.get('UPLOAD_FOLDER', 'uploads')
                    os.makedirs(upload_folder, exist_ok=True)
                    
                    # Create unique filename
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    filename = f"{timestamp}_{secure_filename(file.filename)}"
                    filepath = os.path.join(upload_folder, filename)
                    
                    # Save file
                    file.save(filepath)
                    
                    answer_text = f'/uploads/{filename}'  # Store path relative to static folder
                    answer_value = {'filename': filename, 'filepath': filepath}
                else:
                    answer_text = None
                    answer_value = None
            else:
                answer_text = form_data.get(f'question_{question.id}')
                answer_value = None
            
            # Validate required questions
            if question.is_required and not answer_text and not answer_value:
                db.session.rollback()
                return render_template('forms/form.html', form=form, sections=sections, 
                                     error=f'Required question not answered: {question.question_text}'), 400
            
            # Create answer
            if answer_text or answer_value:
                answer = Answer(
                    response_id=response.id,
                    question_id=question.id,
                    answer_text=answer_text,
                    answer_value=answer_value
                )
                db.session.add(answer)
    
    db.session.commit()
    
    # Redirect to success page
    return redirect(url_for('forms.form_submitted', form_id=form_id))

@bp.route('/<int:form_id>/submitted', methods=['GET'])
def form_submitted(form_id):
    """Show form submission confirmation"""
    form = Form.query.get_or_404(form_id)
    return render_template('forms/submitted.html', form=form)

@bp.route('/<int:form_id>/builder', methods=['GET'])
def form_builder(form_id):
    """Display form builder interface"""
    # Try JWT first (API)
    try:
        current_user_id = get_jwt_identity()
    except:
        # Check session (web)
        if 'user' not in session:
            from flask import flash, redirect, url_for
            flash('Please login to access form builder', 'error')
            return redirect(url_for('auth.login'))
        user_data = session['user']
        current_user_id = user_data['id']

    form = Form.query.get_or_404(form_id)

    # Check if user has permission to edit this form
    if form.created_by != current_user_id:
        if request.is_json:
            return jsonify({'error': 'forbidden', 'message': 'You do not have permission to edit this form'}), 403
        else:
            from flask import flash, redirect, url_for
            flash('You do not have permission to edit this form', 'error')
            return redirect(url_for('main.dashboard'))

    # Get existing sections and questions
    sections = Section.query.filter_by(form_id=form_id).order_by(Section.order).all()
    for section in sections:
        section.questions = Question.query.filter_by(section_id=section.id).order_by(Question.order).all()

    # Get available question templates
    question_templates = QuestionLibrary.query.filter(
        (QuestionLibrary.created_by == current_user_id) | (QuestionLibrary.is_public == True)
    ).all()

    return render_template('forms/builder.html', form=form, sections=sections, question_templates=question_templates)

@bp.route('/<int:form_id>/update_structure', methods=['POST'])
@jwt_required()
def update_form_structure(form_id):
    """Update form structure (sections and questions)"""
    current_user_id = get_jwt_identity()
    form = Form.query.get_or_404(form_id)
    
    # Check if user has permission to edit this form
    if form.created_by != current_user_id:
        return jsonify({'error': 'forbidden', 'message': 'You do not have permission to edit this form'}), 403
    
    # Get new structure from request
    structure = request.json.get('structure', [])
    
    try:
        # Clear existing sections and questions
        # Note: This is simplified - in a real app, you'd want to update existing items
        # rather than deleting and recreating them to preserve responses
        for section in form.sections:
            for question in section.questions:
                db.session.delete(question)
            db.session.delete(section)
        
        # Create new structure
        for section_data in structure:
            section = Section(
                title=section_data.get('title', ''),
                description=section_data.get('description', ''),
                form_id=form_id,
                order=section_data.get('order', 0)
            )
            db.session.add(section)
            db.session.flush()  # Get section ID
            
            # Add questions to section
            for question_data in section_data.get('questions', []):
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
        
        return jsonify({'message': 'Form structure updated successfully'}), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error updating form structure: {str(e)}")
        return jsonify({'error': 'update_failed', 'message': 'Failed to update form structure'}), 500

@bp.route('/templates', methods=['GET'])
def list_templates():
    """List available form templates"""
    # Try JWT first (API)
    try:
        current_user_id = get_jwt_identity()
    except:
        # Check session (web)
        if 'user' not in session:
            from flask import flash, redirect, url_for
            flash('Please login to access templates', 'error')
            return redirect(url_for('auth.login'))
        user_data = session['user']
        current_user_id = user_data['id']

    # Get all public templates and templates created by this user
    templates = FormTemplate.query.filter(
        (FormTemplate.is_public == True) | (FormTemplate.created_by == current_user_id)
    ).all()

    return render_template('forms/templates.html', templates=templates)

@bp.route('/create_from_template/<int:template_id>', methods=['GET'])
def create_from_template(template_id):
    """Create a new form from a template"""
    # Try JWT first (API)
    try:
        current_user_id = get_jwt_identity()
    except:
        # Check session (web)
        if 'user' not in session:
            from flask import flash, redirect, url_for
            flash('Please login to create forms', 'error')
            return redirect(url_for('auth.login'))
        user_data = session['user']
        current_user_id = user_data['id']

    user = User.query.get_or_404(current_user_id)

    if not user.can_create_forms():
        if request.is_json:
            return jsonify({'error': 'forbidden', 'message': 'You do not have permission to create forms'}), 403
        else:
            from flask import flash, redirect, url_for
            flash('You do not have permission to create forms', 'error')
            return redirect(url_for('main.dashboard'))

    template = FormTemplate.query.get_or_404(template_id)

    # Check if user has access to this template
    if not template.is_public and template.created_by != current_user_id:
        if request.is_json:
            return jsonify({'error': 'forbidden', 'message': 'You do not have access to this template'}), 403
        else:
            from flask import flash, redirect, url_for
            flash('You do not have access to this template', 'error')
            return redirect(url_for('forms.list_templates'))
    
    # Create new form from template
    form = Form(
        title=f"Copy of {template.name}",
        description=template.description,
        created_by=current_user_id,
        template_id=template.id
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
    
    # Redirect to form builder
    return redirect(url_for('forms.form_builder', form_id=form.id))

@bp.route('/question_library', methods=['GET'])
@jwt_required()
def question_library():
    """Display question library"""
    current_user_id = get_jwt_identity()
    
    # Get all public questions and questions created by this user
    questions = QuestionLibrary.query.filter(
        (QuestionLibrary.is_public == True) | (QuestionLibrary.created_by == current_user_id)
    ).all()
    
    return render_template('forms/question_library.html', questions=questions)

@bp.route('/question_library', methods=['POST'])
@jwt_required()
def add_to_question_library():
    """Add a question to the library"""
    current_user_id = get_jwt_identity()
    
    # Get data from request
    question_text = request.form.get('question_text')
    question_type = request.form.get('question_type')
    options = request.form.getlist('options[]')  # For multiple choice, checkboxes, dropdowns
    is_required = request.form.get('is_required') == 'on'
    is_public = request.form.get('is_public') == 'on'
    
    # Validate required fields
    if not question_text or not question_type:
        return jsonify({'error': 'validation_error', 'message': 'Question text and type are required'}), 400
    
    # Create new question library entry
    question_lib = QuestionLibrary(
        question_text=question_text,
        question_type=question_type,
        options=options if options else None,
        is_public=is_public,
        created_by=current_user_id,
        is_required=is_required
    )
    
    db.session.add(question_lib)
    db.session.commit()
    
    return jsonify({'message': 'Question added to library successfully'}), 201