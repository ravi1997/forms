from flask import render_template, request, jsonify, current_app, redirect, url_for, session, flash
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import db
from app.forms import bp
from app.models import User, Form, Section, Question, Response, Answer, FormTemplate, QuestionLibrary
from app.schemas import FormSchema, SectionSchema, QuestionSchema
from datetime import datetime

form_schema = FormSchema()
section_schema = SectionSchema()
question_schema = QuestionSchema()

def _get_current_user_id():
    """Return the authenticated user's ID from JWT or session, otherwise None."""
    try:
        return get_jwt_identity()
    except Exception:
        user_data = session.get('user')
        if user_data:
            return user_data.get('id')
    return None

def _login_required_response(message):
    """Return an authentication required response appropriate for the request type."""
    if request.is_json:
        return jsonify({'error': 'authentication_required', 'message': message}), 401
    flash(message, 'error')
    return redirect(url_for('auth.login'))

def _permission_denied_response(message, redirect_endpoint='main.dashboard'):
    """Return a permission denied response appropriate for the request type."""
    if request.is_json:
        return jsonify({'error': 'forbidden', 'message': message}), 403
    flash(message, 'error')
    return redirect(url_for(redirect_endpoint))

def _parse_question_payload():
    """Extract question payload data from JSON or form submissions."""
    if request.is_json:
        data = request.get_json(silent=True) or {}
        options = data.get('options') or []
        if not isinstance(options, list):
            options = [options]
        is_required = bool(data.get('is_required'))
        is_public = bool(data.get('is_public'))
    else:
        data = request.form
        options = request.form.getlist('options[]')
        is_required = data.get('is_required') == 'on'
        is_public = data.get('is_public') == 'on'

    question_text = (data.get('question_text') or '').strip()
    question_type = data.get('question_type')
    # Clean up option values and drop empties
    cleaned_options = [opt.strip() for opt in options if opt and str(opt).strip()]

    return question_text, question_type, cleaned_options, is_required, is_public

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
def update_form_structure(form_id):
    """Update form structure (sections and questions)"""
    # Try JWT first (API)
    try:
        current_user_id = get_jwt_identity()
    except:
        # Check session (web)
        if 'user' not in session:
            from flask import flash, redirect, url_for
            flash('Please login to update form structure', 'error')
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

@bp.route('/<int:form_id>/edit', methods=['GET', 'POST'])
def edit_form(form_id):
    """Edit form metadata"""
    # Try JWT first (API)
    try:
        current_user_id = get_jwt_identity()
    except:
        # Check session (web)
        if 'user' not in session:
            from flask import flash, redirect, url_for
            flash('Please login to edit forms', 'error')
            return redirect(url_for('auth.login'))
        user_data = session['user']
        current_user_id = user_data['id']

    form = Form.query.get_or_404(form_id)

    # Check if user has permission to edit this form
    if form.created_by != current_user_id:
        from flask import flash, redirect, url_for
        flash('You do not have permission to edit this form', 'error')
        return redirect(url_for('main.dashboard'))

    if request.method == 'GET':
        return render_template('forms/edit_form.html', form=form)

    # Handle POST request
    title = request.form.get('title')
    description = request.form.get('description', '')

    # Validate required fields
    if not title:
        from flask import flash
        flash('Form title is required', 'error')
        return render_template('forms/edit_form.html', form=form)

    # Update form
    form.title = title
    form.description = description
    form.updated_at = datetime.utcnow()

    db.session.commit()

    from flask import flash, redirect, url_for
    flash('Form updated successfully', 'success')
    return redirect(url_for('forms.edit_form', form_id=form_id))

@bp.route('/<int:form_id>/delete', methods=['POST'])
def delete_form(form_id):
    """Delete a form"""
    # Try JWT first (API)
    try:
        current_user_id = get_jwt_identity()
    except:
        # Check session (web)
        if 'user' not in session:
            from flask import flash, redirect, url_for
            flash('Please login to delete forms', 'error')
            return redirect(url_for('auth.login'))
        user_data = session['user']
        current_user_id = user_data['id']

    form = Form.query.get_or_404(form_id)

    # Check if user has permission to delete this form
    if form.created_by != current_user_id:
        if request.is_json:
            return jsonify({'error': 'forbidden', 'message': 'You do not have permission to delete this form'}), 403
        else:
            from flask import flash, redirect, url_for
            flash('You do not have permission to delete this form', 'error')
            return redirect(url_for('main.dashboard'))

    try:
        db.session.delete(form)
        db.session.commit()

        if request.is_json:
            return jsonify({'message': 'Form deleted successfully'}), 200
        else:
            from flask import flash, redirect, url_for
            flash('Form deleted successfully', 'success')
            return redirect(url_for('forms.my_forms'))
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting form: {str(e)}")
        if request.is_json:
            return jsonify({'error': 'delete_failed', 'message': 'Failed to delete form'}), 500
        else:
            from flask import flash, redirect, url_for
            flash('Failed to delete form', 'error')
            return redirect(url_for('forms.my_forms'))

@bp.route('/<int:form_id>/publish', methods=['POST'])
def publish_form(form_id):
    """Publish a form so it becomes publicly accessible."""
    current_user_id = _get_current_user_id()
    if not current_user_id:
        return _login_required_response('Please login to publish forms')

    form = Form.query.get_or_404(form_id)
    if form.created_by != current_user_id:
        return _permission_denied_response('You do not have permission to publish this form')

    form.is_published = True
    form.is_archived = False
    form.published_at = datetime.utcnow()
    form.updated_at = datetime.utcnow()
    db.session.commit()

    message = 'Form published successfully'
    if request.is_json:
        return jsonify({'message': message, 'form_id': form.id, 'status': 'published'}), 200

    flash(message, 'success')
    return redirect(request.referrer or url_for('forms.form_builder', form_id=form.id))

@bp.route('/<int:form_id>/unpublish', methods=['POST'])
def unpublish_form(form_id):
    """Mark a form as draft so it is no longer public."""
    current_user_id = _get_current_user_id()
    if not current_user_id:
        return _login_required_response('Please login to update forms')

    form = Form.query.get_or_404(form_id)
    if form.created_by != current_user_id:
        return _permission_denied_response('You do not have permission to unpublish this form')

    form.is_published = False
    form.updated_at = datetime.utcnow()
    db.session.commit()

    message = 'Form unpublished successfully'
    if request.is_json:
        return jsonify({'message': message, 'form_id': form.id, 'status': 'draft'}), 200

    flash(message, 'success')
    return redirect(request.referrer or url_for('forms.form_builder', form_id=form.id))

@bp.route('/<int:form_id>/archive', methods=['POST'])
def archive_form(form_id):
    """Archive a form to remove it from the active list."""
    current_user_id = _get_current_user_id()
    if not current_user_id:
        return _login_required_response('Please login to archive forms')

    form = Form.query.get_or_404(form_id)
    if form.created_by != current_user_id:
        return _permission_denied_response('You do not have permission to archive this form')

    form.is_archived = True
    form.is_published = False
    form.updated_at = datetime.utcnow()
    db.session.commit()

    message = 'Form archived successfully'
    if request.is_json:
        return jsonify({'message': message, 'form_id': form.id, 'status': 'archived'}), 200

    flash(message, 'success')
    return redirect(request.referrer or url_for('forms.my_forms'))

@bp.route('/<int:form_id>/restore', methods=['POST'])
def restore_form(form_id):
    """Restore an archived form."""
    current_user_id = _get_current_user_id()
    if not current_user_id:
        return _login_required_response('Please login to restore forms')

    form = Form.query.get_or_404(form_id)
    if form.created_by != current_user_id:
        return _permission_denied_response('You do not have permission to restore this form')

    form.is_archived = False
    form.updated_at = datetime.utcnow()
    db.session.commit()

    message = 'Form restored successfully'
    if request.is_json:
        return jsonify({'message': message, 'form_id': form.id, 'status': 'draft'}), 200

    flash(message, 'success')
    return redirect(request.referrer or url_for('forms.my_forms'))

@bp.route('/my-forms', methods=['GET'])
def my_forms():
    """List user's forms"""
    # Try JWT first (API)
    try:
        current_user_id = get_jwt_identity()
    except:
        # Check session (web)
        if 'user' not in session:
            from flask import flash, redirect, url_for
            flash('Please login to view your forms', 'error')
            return redirect(url_for('auth.login'))
        user_data = session['user']
        current_user_id = user_data['id']

    # Get user's forms, ordered by creation date (newest first)
    forms = Form.query.filter_by(created_by=current_user_id).order_by(Form.created_at.desc()).all()

    return render_template('forms/my_forms.html', forms=forms)

@bp.route('/<int:form_id>/settings', methods=['GET', 'POST'])
def form_settings(form_id):
    """Manage form settings"""
    # Try JWT first (API)
    try:
        current_user_id = get_jwt_identity()
    except:
        # Check session (web)
        if 'user' not in session:
            from flask import flash, redirect, url_for
            flash('Please login to access form settings', 'error')
            return redirect(url_for('auth.login'))
        user_data = session['user']
        current_user_id = user_data['id']

    form = Form.query.get_or_404(form_id)

    # Check if user has permission to edit this form
    if form.created_by != current_user_id:
        from flask import flash, redirect, url_for
        flash('You do not have permission to edit this form', 'error')
        return redirect(url_for('main.dashboard'))

    if request.method == 'GET':
        return render_template('forms/form_settings.html', form=form)

    # Handle POST request
    settings = form.settings or {}

    # Update settings from form data
    expires_at = request.form.get('expires_at')
    if expires_at:
        from datetime import datetime
        try:
            settings['expires_at'] = datetime.strptime(expires_at, '%Y-%m-%dT%H:%M').isoformat()
        except ValueError:
            pass

    response_limit = request.form.get('response_limit')
    if response_limit:
        try:
            settings['response_limit'] = int(response_limit)
        except ValueError:
            pass

    settings['require_login'] = 'require_login' in request.form
    settings['collect_ip'] = 'collect_ip' in request.form
    settings['allow_multiple_responses'] = 'allow_multiple_responses' in request.form

    form.settings = settings
    form.updated_at = datetime.utcnow()

    db.session.commit()

    from flask import flash, redirect, url_for
    flash('Form settings updated successfully', 'success')
    return redirect(url_for('forms.form_settings', form_id=form_id))

@bp.route('/question_library', methods=['GET'])
def question_library():
    """Display question library"""
    # Try JWT first (API)
    try:
        current_user_id = get_jwt_identity()
    except:
        # Check session (web)
        if 'user' not in session:
            from flask import flash, redirect, url_for
            flash('Please login to access question library', 'error')
            return redirect(url_for('auth.login'))
        user_data = session['user']
        current_user_id = user_data['id']

    # Get all public questions and questions created by this user
    questions = QuestionLibrary.query.filter(
        (QuestionLibrary.is_public == True) | (QuestionLibrary.created_by == current_user_id)
    ).all()

    return render_template('forms/question_library.html', questions=questions)

@bp.route('/question_library', methods=['POST'])
def add_to_question_library():
    """Add a question to the library"""
    current_user_id = _get_current_user_id()
    if not current_user_id:
        return _login_required_response('Please login to add questions')

    question_text, question_type, options, is_required, is_public = _parse_question_payload()

    # Validate required fields
    if not question_text or not question_type:
        if request.is_json:
            return jsonify({'error': 'validation_error', 'message': 'Question text and type are required'}), 400
        flash('Question text and type are required', 'error')
        return redirect(url_for('forms.question_library'))

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

    success_message = 'Question added to library successfully'
    if request.is_json:
        return jsonify({
            'message': success_message,
            'question': {
                'id': question_lib.id,
                'question_text': question_lib.question_text,
                'question_type': getattr(question_lib.question_type, 'value', question_lib.question_type),
                'options': question_lib.options or [],
                'is_required': question_lib.is_required,
                'is_public': question_lib.is_public
            }
        }), 201

    flash(success_message, 'success')
    return redirect(url_for('forms.question_library'))

@bp.route('/question_library/<int:question_id>', methods=['PUT'])
def update_question_library(question_id):
    """Update an existing question library entry."""
    current_user_id = _get_current_user_id()
    if not current_user_id:
        return _login_required_response('Please login to update questions')

    question = QuestionLibrary.query.get_or_404(question_id)
    if question.created_by != current_user_id:
        return _permission_denied_response('You do not have permission to edit this question', 'forms.question_library')

    question_text, question_type, options, is_required, is_public = _parse_question_payload()

    if not question_text or not question_type:
        if request.is_json:
            return jsonify({'error': 'validation_error', 'message': 'Question text and type are required'}), 400
        flash('Question text and type are required', 'error')
        return redirect(url_for('forms.question_library'))

    question.question_text = question_text
    question.question_type = question_type
    question.options = options or None
    question.is_required = is_required
    question.is_public = is_public

    db.session.commit()

    message = 'Question updated successfully'
    if request.is_json:
        return jsonify({
            'message': message,
            'question': {
                'id': question.id,
                'question_text': question.question_text,
                'question_type': getattr(question.question_type, 'value', question.question_type),
                'options': question.options or [],
                'is_required': question.is_required,
                'is_public': question.is_public
            }
        }), 200

    flash(message, 'success')
    return redirect(url_for('forms.question_library'))

@bp.route('/question_library/<int:question_id>', methods=['DELETE'])
def delete_question_library(question_id):
    """Delete a question from the library."""
    current_user_id = _get_current_user_id()
    if not current_user_id:
        return _login_required_response('Please login to delete questions')

    question = QuestionLibrary.query.get_or_404(question_id)
    if question.created_by != current_user_id:
        return _permission_denied_response('You do not have permission to delete this question', 'forms.question_library')

    db.session.delete(question)
    db.session.commit()

    message = 'Question deleted successfully'
    if request.is_json:
        return jsonify({'message': message, 'question_id': question_id}), 200

    flash(message, 'success')
    return redirect(url_for('forms.question_library'))

@bp.route('/<int:form_id>/update_order', methods=['POST'])
def update_order(form_id):
    """Update the order of sections and questions"""
    current_user_id = _get_current_user_id()
    if not current_user_id:
        return _login_required_response('Please login to update order')

    form = Form.query.get_or_404(form_id)
    if form.created_by != current_user_id:
        return _permission_denied_response('You do not have permission to edit this form')

    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'message': 'No data provided'}), 400

    try:
        # Update section orders
        if 'sections' in data:
            for section_data in data['sections']:
                section_id = section_data.get('id')
                order = section_data.get('order')
                if section_id is not None and order is not None:
                    section = Section.query.filter_by(id=section_id, form_id=form_id).first()
                    if section:
                        section.order = order

        # Update question orders
        if 'questions' in data:
            for question_data in data['questions']:
                question_id = question_data.get('id')
                order = question_data.get('order')
                if question_id is not None and order is not None:
                    question = Question.query.filter_by(id=question_id).join(Section).filter(Section.form_id == form_id).first()
                    if question:
                        question.order = order

        db.session.commit()
        return jsonify({'success': True, 'message': 'Order updated successfully'}), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error updating order: {str(e)}")
        return jsonify({'success': False, 'message': 'Failed to update order'}), 500

@bp.route('/create', methods=['GET', 'POST'])
def create_form():
    """Create a new form"""
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
        from flask import flash, redirect, url_for
        flash('You do not have permission to create forms', 'error')
        return redirect(url_for('main.dashboard'))

    if request.method == 'GET':
        return render_template('forms/create_form.html')

    # Handle POST request
    title = request.form.get('title')
    description = request.form.get('description', '')

    # Validate required fields
    if not title:
        from flask import flash
        flash('Form title is required', 'error')
        return render_template('forms/create_form.html', title=title, description=description)

    # Create new form
    form = Form(
        title=title,
        description=description,
        created_by=current_user_id
    )

    db.session.add(form)
    db.session.commit()

    # Redirect to form builder
@bp.route('/<int:form_id>/update_metadata', methods=['POST'])
def update_form_metadata(form_id):
    """Update form title and description via AJAX"""
    current_user_id = _get_current_user_id()
    if not current_user_id:
        return _login_required_response('Please login to update forms')

    form = Form.query.get_or_404(form_id)
    if form.created_by != current_user_id:
        return _permission_denied_response('You do not have permission to edit this form')

    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    title = data.get('title', '').strip()
    description = data.get('description', '').strip()

    if not title:
        return jsonify({'error': 'Title is required'}), 400

    form.title = title
    form.description = description
    form.updated_at = datetime.utcnow()
    db.session.commit()

    return jsonify({'message': 'Form metadata updated successfully'}), 200

@bp.route('/<int:form_id>/sections', methods=['POST'])
def add_section(form_id):
    """Add a new section to the form"""
    current_user_id = _get_current_user_id()
    if not current_user_id:
        return _login_required_response('Please login to add sections')

    form = Form.query.get_or_404(form_id)
    if form.created_by != current_user_id:
        return _permission_denied_response('You do not have permission to edit this form')

    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    title = data.get('title', '').strip()
    description = data.get('description', '').strip()

    # Get the next order
    max_order = db.session.query(db.func.max(Section.order)).filter_by(form_id=form_id).scalar() or 0
    order = max_order + 1

    section = Section(
        title=title,
        description=description,
        form_id=form_id,
        order=order
    )
    db.session.add(section)
    db.session.commit()

    return jsonify({
        'message': 'Section added successfully',
        'section': {
            'id': section.id,
            'title': section.title,
            'description': section.description,
            'order': section.order
        }
    }), 201

@bp.route('/<int:form_id>/sections/<int:section_id>', methods=['PUT'])
def update_section(form_id, section_id):
    """Update a section"""
    current_user_id = _get_current_user_id()
    if not current_user_id:
        return _login_required_response('Please login to update sections')

    form = Form.query.get_or_404(form_id)
    if form.created_by != current_user_id:
        return _permission_denied_response('You do not have permission to edit this form')

    section = Section.query.filter_by(id=section_id, form_id=form_id).first_or_404()

    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    title = data.get('title', '').strip()
    description = data.get('description', '').strip()

    section.title = title
    section.description = description
    section.updated_at = datetime.utcnow()
    db.session.commit()

    return jsonify({'message': 'Section updated successfully'}), 200

@bp.route('/<int:form_id>/sections/<int:section_id>', methods=['DELETE'])
def delete_section(form_id, section_id):
    """Delete a section"""
    current_user_id = _get_current_user_id()
    if not current_user_id:
        return _login_required_response('Please login to delete sections')

    form = Form.query.get_or_404(form_id)
    if form.created_by != current_user_id:
        return _permission_denied_response('You do not have permission to edit this form')

    section = Section.query.filter_by(id=section_id, form_id=form_id).first_or_404()

    # Delete all questions in the section first
    Question.query.filter_by(section_id=section_id).delete()

    db.session.delete(section)
    db.session.commit()

    return jsonify({'message': 'Section deleted successfully'}), 200

@bp.route('/<int:form_id>/sections/<int:section_id>/questions', methods=['POST'])
def add_question(form_id, section_id):
    """Add a new question to a section"""
    current_user_id = _get_current_user_id()
    if not current_user_id:
        return _login_required_response('Please login to add questions')

    form = Form.query.get_or_404(form_id)
    if form.created_by != current_user_id:
        return _permission_denied_response('You do not have permission to edit this form')

    section = Section.query.filter_by(id=section_id, form_id=form_id).first_or_404()

    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    question_text = data.get('question_text', '').strip()
    question_type = data.get('question_type')
    is_required = data.get('is_required', False)
    options = data.get('options', [])
    validation_rules = data.get('validation_rules', {})

    if not question_text or not question_type:
        return jsonify({'error': 'Question text and type are required'}), 400

    # Get the next order
    max_order = db.session.query(db.func.max(Question.order)).filter_by(section_id=section_id).scalar() or 0
    order = max_order + 1

    question = Question(
        section_id=section_id,
        question_text=question_text,
        question_type=question_type,
        is_required=is_required,
        order=order,
        options=options,
        validation_rules=validation_rules
    )
    db.session.add(question)
    db.session.commit()

    return jsonify({
        'message': 'Question added successfully',
        'question': {
            'id': question.id,
            'question_text': question.question_text,
            'question_type': question.question_type.value if hasattr(question.question_type, 'value') else question.question_type,
            'is_required': question.is_required,
            'order': question.order,
            'options': question.options or [],
            'validation_rules': question.validation_rules or {}
        }
    }), 201

@bp.route('/<int:form_id>/sections/<int:section_id>/questions/<int:question_id>', methods=['PUT'])
def update_question(form_id, section_id, question_id):
    """Update a question"""
    current_user_id = _get_current_user_id()
    if not current_user_id:
        return _login_required_response('Please login to update questions')

    form = Form.query.get_or_404(form_id)
    if form.created_by != current_user_id:
        return _permission_denied_response('You do not have permission to edit this form')

    question = Question.query.filter_by(id=question_id, section_id=section_id).join(Section).filter(Section.form_id == form_id).first_or_404()

    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    question_text = data.get('question_text', '').strip()
    question_type = data.get('question_type')
    is_required = data.get('is_required', False)
    options = data.get('options', [])
    validation_rules = data.get('validation_rules', {})

    if not question_text or not question_type:
        return jsonify({'error': 'Question text and type are required'}), 400

    question.question_text = question_text
    question.question_type = question_type
    question.is_required = is_required
    question.options = options
    question.validation_rules = validation_rules
    question.updated_at = datetime.utcnow()
    db.session.commit()

    return jsonify({'message': 'Question updated successfully'}), 200

@bp.route('/<int:form_id>/sections/<int:section_id>/questions/<int:question_id>', methods=['DELETE'])
def delete_question(form_id, section_id, question_id):
    """Delete a question"""
    current_user_id = _get_current_user_id()
    if not current_user_id:
        return _login_required_response('Please login to delete questions')

    form = Form.query.get_or_404(form_id)
    if form.created_by != current_user_id:
        return _permission_denied_response('You do not have permission to edit this form')

    question = Question.query.filter_by(id=question_id, section_id=section_id).join(Section).filter(Section.form_id == form_id).first_or_404()

    db.session.delete(question)
    db.session.commit()

    return jsonify({'message': 'Question deleted successfully'}), 200
    return redirect(url_for('forms.form_builder', form_id=form.id))
