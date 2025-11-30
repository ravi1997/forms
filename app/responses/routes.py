from flask import render_template, request, jsonify, current_app, send_file, session
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import db, cache, celery
from app.responses import bp
from app.models import User, Form, Response, Answer, UserRoles
from app.schemas import ResponseSchema
import csv
import json
import io
from datetime import datetime
import pandas as pd
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors

response_schema = ResponseSchema()

from app.utils.decorators import login_required, roles_required

...

from app.services.response_service import ResponseService

...

@bp.route('/<int:form_id>', methods=['GET'])
@login_required
def list_responses(form_id, current_user_id):
    """List all responses for a form"""
    form = Form.query.get_or_404(form_id)

    # Check if user has permission to view responses
    user = User.query.get(current_user_id)
    if form.created_by != current_user_id and not user.can_view_analytics():
        if request.is_json:
            return jsonify({'error': 'forbidden', 'message': 'You do not have permission to view responses'}), 403
        else:
            from flask import flash, redirect, url_for
            flash('You do not have permission to view responses', 'error')
            return redirect(url_for('main.dashboard'))
    
    # Get responses with pagination
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 10, type=int), 100)
    
    responses = ResponseService.get_responses_paginated(form_id, page, per_page)
    
    return render_template('responses/list.html', form=form, responses=responses)

@bp.route('/<int:form_id>/export', methods=['GET'])
@login_required
def export_responses(form_id, current_user_id):
    """Export form responses in specified format"""
    form = Form.query.get_or_404(form_id)

    # Check if user has permission to export responses
    if form.created_by != current_user_id and not User.query.get(current_user_id).can_view_analytics():
        if request.is_json:
            return jsonify({'error': 'forbidden', 'message': 'You do not have permission to export responses'}), 403
        else:
            from flask import flash, redirect, url_for
            flash('You do not have permission to export responses', 'error')
            return redirect(url_for('main.dashboard'))
    
    # Get format from query parameter
    format_type = request.args.get('format', 'csv').lower()
    
    # Check if this is a large export that should be processed in background
    response_count = Response.query.filter_by(form_id=form_id).count()

    # For large datasets (>1000 responses), use background processing
    if response_count > 1000:
        from app.tasks import export_responses_task
        task = export_responses_task.delay(form_id, format_type, current_user_id)
        return jsonify({
            'status': 'processing',
            'task_id': task.id,
            'message': 'Large export started. You will receive a notification when complete.',
            'response_count': response_count
        })

    # For smaller datasets, process immediately
    data, mimetype = ResponseService.export_responses(form_id, format_type)

    if data is None:
        return jsonify({'error': 'invalid_format', 'message': 'Invalid export format. Use csv, json, excel, or pdf'}), 400

    return send_file(
        io.BytesIO(data) if isinstance(data, bytes) else io.StringIO(data),
        mimetype=mimetype,
        as_attachment=True,
        download_name=f'responses_{form_id}.{format_type}'
    )

@bp.route('/<int:form_id>/analytics', methods=['GET'])
@login_required
@cache.cached(timeout=300, key_prefix=lambda: f"form_analytics_{request.args.get('form_id', '')}")
def form_analytics(form_id, current_user_id):
    """Display analytics for a form"""
    form = Form.query.get_or_404(form_id)

    # Check if user has permission to view analytics
    if form.created_by != current_user_id and not User.query.get(current_user_id).can_view_analytics():
        if request.is_json:
            return jsonify({'error': 'forbidden', 'message': 'You do not have permission to view analytics'}), 403
        else:
            from flask import flash, redirect, url_for
            flash('You do not have permission to view analytics', 'error')
            return redirect(url_for('main.dashboard'))
    
    # Get response count
    response_count = Response.query.filter_by(form_id=form_id).count()
    
    # Get responses to calculate analytics
    responses = Response.query.filter_by(form_id=form_id).all()
    
    # Calculate submission times (for time-based analytics)
    submission_times = []
    for response in responses:
        if response.submitted_at:
            submission_times.append(response.submitted_at)
    
    # Prepare analytics data for each question
    analytics_data = []
    all_sections = form.sections
    questions = []
    for section in all_sections:
        questions.extend(section.questions)
    
    for question in questions:
        question_analytics = {
            'question_id': question.id,
            'question_text': question.question_text,
            'question_type': question.question_type.value,
            'total_responses': 0,
            'answers': {}
        }
        
        # Get all answers for this question
        answers = Answer.query.join(Response).filter(
            Answer.question_id == question.id,
            Response.form_id == form_id
        ).all()
        
        question_analytics['total_responses'] = len(answers)
        
        # Process answers based on question type
        if question.question_type in ['multiple_choice', 'checkbox', 'dropdown']:
            # Count options
            for answer in answers:
                if answer.answer_value:
                    if isinstance(answer.answer_value, list):
                        # For checkboxes, answer_value is a list
                        for option in answer.answer_value:
                            if option in question_analytics['answers']:
                                question_analytics['answers'][option] += 1
                            else:
                                question_analytics['answers'][option] = 1
                    else:
                        option = answer.answer_value or answer.answer_text
                        if option in question_analytics['answers']:
                            question_analytics['answers'][option] += 1
                        else:
                            question_analytics['answers'][option] = 1
                elif answer.answer_text:
                    option = answer.answer_text
                    if option in question_analytics['answers']:
                        question_analytics['answers'][option] += 1
                    else:
                        question_analytics['answers'][option] = 1
        elif question.question_type == 'rating':
            # Calculate average rating and distribution
            ratings = []
            for answer in answers:
                try:
                    rating = int(answer.answer_text) if answer.answer_text else 0
                    ratings.append(rating)
                    str_rating = str(rating)
                    if str_rating in question_analytics['answers']:
                        question_analytics['answers'][str_rating] += 1
                    else:
                        question_analytics['answers'][str_rating] = 1
                except ValueError:
                    pass  # Skip invalid ratings
        else:
            # For text questions, just count responses
            question_analytics['answers'] = {'total_responses': len(answers)}
        
        analytics_data.append(question_analytics)
    
    # Prepare time-based analytics
    time_analytics = {
        'total_responses': response_count,
        'responses_over_time': {}
    }
    
    if submission_times:
        for time in submission_times:
            date_str = time.strftime('%Y-%m-%d')
            if date_str in time_analytics['responses_over_time']:
                time_analytics['responses_over_time'][date_str] += 1
            else:
                time_analytics['responses_over_time'][date_str] = 1
    
    return render_template('responses/analytics.html', 
                          form=form, 
                          response_count=response_count,
                          analytics_data=analytics_data,
                          time_analytics=time_analytics)

@bp.route('/<int:response_id>/details', methods=['GET'])
@login_required
def response_details(response_id, current_user_id):
    """Show details of a specific response"""
    response = Response.query.get_or_404(response_id)

    # Check if user has permission to view this response
    form = response.form
    if form.created_by != current_user_id and not User.query.get(current_user_id).can_view_analytics():
        if request.is_json:
            return jsonify({'error': 'forbidden', 'message': 'You do not have permission to view this response'}), 403
        else:
            from flask import flash, redirect, url_for
            flash('You do not have permission to view this response', 'error')
            return redirect(url_for('main.dashboard'))
    
    # Get all answers for this response
    answers = Answer.query.filter_by(response_id=response_id).all()
    
    # Get user info if available
    user_info = User.query.get(response.user_id) if response.user_id else None
    
    return render_template('responses/details.html', 
                          response=response, 
                          answers=answers, 
                          user_info=user_info,
                          form=form)

@bp.route('/<int:form_id>/filter', methods=['GET'])
@login_required
def filter_responses(form_id, current_user_id):
    """Filter responses based on criteria"""
    form = Form.query.get_or_404(form_id)

    # Check if user has permission to view responses
    if form.created_by != current_user_id and not User.query.get(current_user_id).can_view_analytics():
        if request.is_json:
            return jsonify({'error': 'forbidden', 'message': 'You do not have permission to view responses'}), 403
        else:
            from flask import flash, redirect, url_for
            flash('You do not have permission to view responses', 'error')
            return redirect(url_for('main.dashboard'))
    
    # Get filter parameters
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    user_id = request.args.get('user_id')
    
    # Build query
    query = Response.query.filter_by(form_id=form_id)
    
    if start_date:
        start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        query = query.filter(Response.submitted_at >= start_dt)
    
    if end_date:
        end_dt = datetime.strptime(end_date, '%Y-%m-%d')
        query = query.filter(Response.submitted_at <= end_dt)
    
    if user_id:
        query = query.filter(Response.user_id == user_id)
    
    # Get filtered responses
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 10, type=int), 10)
    
    # Use eager loading to avoid N+1 queries
    responses = query.options(
        db.joinedload(Response.answers),
        db.joinedload(Response.user)
    ).paginate(page=page, per_page=per_page, error_out=False)
    
    return render_template('responses/list.html', form=form, responses=responses, filtered=True)

@bp.route('/<int:response_id>/delete', methods=['DELETE'])
@login_required
def delete_response(response_id, current_user_id):
    """Delete a specific response"""
    response = Response.query.get_or_404(response_id)
    form = response.form

    # Check if user has permission to delete this response
    # Only form owner or admin can delete responses
    user = User.query.get(current_user_id)
    if form.created_by != current_user_id and not user.has_role(UserRoles.ADMIN):
        if request.is_json:
            return jsonify({'error': 'forbidden', 'message': 'You do not have permission to delete this response'}), 403
        else:
            from flask import flash, redirect, url_for
            flash('You do not have permission to delete this response', 'error')
            return redirect(url_for('responses.list_responses', form_id=form.id))

    try:
        # Delete associated answers first
        Answer.query.filter_by(response_id=response_id).delete()
        # Delete the response
        db.session.delete(response)
        db.session.commit()

        if request.is_json:
            return jsonify({'message': 'Response deleted successfully'}), 200
        else:
            from flask import flash, redirect, url_for
            flash('Response deleted successfully', 'success')
            return redirect(url_for('responses.list_responses', form_id=form.id))
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting response: {str(e)}")
        if request.is_json:
            return jsonify({'error': 'delete_failed', 'message': 'Failed to delete response'}), 500
        else:
            from flask import flash, redirect, url_for
            flash('Failed to delete response', 'error')
            return redirect(url_for('responses.list_responses', form_id=form.id))
