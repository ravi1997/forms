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

@bp.route('/<int:form_id>', methods=['GET'])
def list_responses(form_id):
    """List all responses for a form"""
    # Try JWT first (API)
    try:
        current_user_id = get_jwt_identity()
    except:
        # Check session (web)
        if 'user' not in session:
            from flask import flash, redirect, url_for
            flash('Please login to access responses', 'error')
            return redirect(url_for('auth.login'))
        user_data = session['user']
        current_user_id = user_data['id']

    form = Form.query.get_or_404(form_id)

    # Check if user has permission to view responses
    if form.created_by != current_user_id and not User.query.get(current_user_id).can_view_analytics():
        if request.is_json:
            return jsonify({'error': 'forbidden', 'message': 'You do not have permission to view responses'}), 403
        else:
            from flask import flash, redirect, url_for
            flash('You do not have permission to view responses', 'error')
            return redirect(url_for('main.dashboard'))
    
    # Get responses with pagination
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 10, type=int), 100)
    
    # Use eager loading to avoid N+1 queries
    responses = Response.query.filter_by(form_id=form_id).options(
        db.joinedload(Response.answers),
        db.joinedload(Response.user)
    ).paginate(page=page, per_page=per_page, error_out=False)
    
    return render_template('responses/list.html', form=form, responses=responses)

@bp.route('/<int:form_id>/export', methods=['GET'])
def export_responses(form_id):
    """Export form responses in specified format"""
    # Try JWT first (API)
    try:
        current_user_id = get_jwt_identity()
    except:
        # Check session (web)
        if 'user' not in session:
            from flask import flash, redirect, url_for
            flash('Please login to export responses', 'error')
            return redirect(url_for('auth.login'))
        user_data = session['user']
        current_user_id = user_data['id']

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
    responses = Response.query.filter_by(form_id=form_id).all()
    
    # Get all questions in the form to create headers
    all_sections = form.sections
    questions = []
    for section in all_sections:
        questions.extend(section.questions)
    
    if format_type == 'csv':
        # Create CSV
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Create header row with question texts
        headers = ['Response ID', 'Submitted At', 'User ID']
        for question in questions:
            headers.append(question.question_text)
        writer.writerow(headers)
        
        # Add response data
        for response in responses:
            answers = {answer.question_id: answer for answer in response.answers}
            row = [response.id, response.submitted_at, response.user_id or 'Anonymous']
            
            for question in questions:
                answer = answers.get(question.id)
                if answer:
                    # Use answer_text if available, otherwise answer_value
                    value = answer.answer_text or str(answer.answer_value) if answer.answer_value else ''
                    row.append(value)
                else:
                    row.append('')
            
            writer.writerow(row)
        
        # Convert to bytes
        output.seek(0)
        csv_content = output.getvalue().encode('utf-8')
        output.close()
        
        # Send CSV file
        from flask import Response
        return Response(
            csv_content,
            mimetype='text/csv',
            headers={'Content-Disposition': f'attachment; filename=responses_{form_id}.csv'}
        )
    
    elif format_type == 'json':
        # Create JSON
        responses_data = []
        for response in responses:
            response_data = {
                'response_id': response.id,
                'submitted_at': response.submitted_at.isoformat() if response.submitted_at else None,
                'user_id': response.user_id,
                'answers': []
            }
            
            for answer in response.answers:
                answer_data = {
                    'question_id': answer.question_id,
                    'question_text': answer.question.question_text,
                    'answer_text': answer.answer_text,
                    'answer_value': answer.answer_value
                }
                response_data['answers'].append(answer_data)
            
            responses_data.append(response_data)
        
        # Convert to JSON string
        json_content = json.dumps(responses_data, indent=2, default=str)
        
        # Send JSON file
        from flask import Response
        return Response(
            json_content,
            mimetype='application/json',
            headers={'Content-Disposition': f'attachment; filename=responses_{form_id}.json'}
        )
    
    elif format_type == 'excel':
        # Create Excel file using pandas
        import pandas as pd
        from io import BytesIO
        
        # Prepare data
        data = []
        for response in responses:
            answers = {answer.question_id: answer for answer in response.answers}
            row = {
                'Response ID': response.id,
                'Submitted At': response.submitted_at,
                'User ID': response.user_id or 'Anonymous'
            }
            
            for question in questions:
                answer = answers.get(question.id)
                if answer:
                    # Use answer_text if available, otherwise answer_value
                    value = answer.answer_text or str(answer.answer_value) if answer.answer_value else ''
                    row[question.question_text] = value
                else:
                    row[question.question_text] = ''
            
            data.append(row)
        
        # Create DataFrame
        df = pd.DataFrame(data)
        
        # Create Excel in memory
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Responses')
        
        # Send Excel file
        output.seek(0)
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=f'responses_{form_id}.xlsx'
        )
    
    elif format_type == 'pdf':
        # Create PDF
        from io import BytesIO
        
        # Prepare data for PDF
        data = []
        headers = ['Response ID', 'Submitted At', 'User ID']
        
        # Get all questions in the form to create headers
        all_sections = form.sections
        questions = []
        for section in all_sections:
            questions.extend(section.questions)
        
        # Add question titles as headers
        for question in questions:
            headers.append(question.question_text)
        
        data.append(headers)
        
        # Add response data
        for response in responses:
            answers = {answer.question_id: answer for answer in response.answers}
            row = [str(response.id), response.submitted_at.strftime('%Y-%m-%d %H:%M:%S') if response.submitted_at else 'N/A', 
                   str(response.user_id or 'Anonymous')]
            
            for question in questions:
                answer = answers.get(question.id)
                if answer:
                    # Use answer_text if available, otherwise answer_value
                    value = answer.answer_text or str(answer.answer_value) if answer.answer_value else ''
                    row.append(value)
                else:
                    row.append('')
            
            data.append(row)
        
        # Create PDF in memory
        output = BytesIO()
        doc = SimpleDocTemplate(output, pagesize=letter)
        story = []
        
        # Title
        styles = getSampleStyleSheet()
        title = Paragraph(f"Form Responses - {form.title}", styles['Title'])
        story.append(title)
        story.append(Spacer(1, 12))
        
        # Add form information
        form_info = Paragraph(f"Form ID: {form.id} | Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", styles['Normal'])
        story.append(form_info)
        story.append(Spacer(1, 12))
        
        # Create table
        table = Table(data)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(table)
        story.append(PageBreak())
        
        # Build PDF
        doc.build(story)
        
        # Return PDF file
        output.seek(0)
        return send_file(
            output,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f'responses_{form_id}.pdf'
        )
    
    else:
        return jsonify({'error': 'invalid_format', 'message': 'Invalid export format. Use csv, json, excel, or pdf'}), 400

@bp.route('/<int:form_id>/analytics', methods=['GET'])
@cache.cached(timeout=300, key_prefix=lambda: f"form_analytics_{request.args.get('form_id', '')}")
def form_analytics(form_id):
    """Display analytics for a form"""
    # Try JWT first (API)
    try:
        current_user_id = get_jwt_identity()
    except:
        # Check session (web)
        if 'user' not in session:
            from flask import flash, redirect, url_for
            flash('Please login to access analytics', 'error')
            return redirect(url_for('auth.login'))
        user_data = session['user']
        current_user_id = user_data['id']

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
def response_details(response_id):
    """Show details of a specific response"""
    # Try JWT first (API)
    try:
        current_user_id = get_jwt_identity()
    except:
        # Check session (web)
        if 'user' not in session:
            from flask import flash, redirect, url_for
            flash('Please login to access response details', 'error')
            return redirect(url_for('auth.login'))
        user_data = session['user']
        current_user_id = user_data['id']

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
def filter_responses(form_id):
    """Filter responses based on criteria"""
    # Try JWT first (API)
    try:
        current_user_id = get_jwt_identity()
    except:
        # Check session (web)
        if 'user' not in session:
            from flask import flash, redirect, url_for
            flash('Please login to filter responses', 'error')
            return redirect(url_for('auth.login'))
        user_data = session['user']
        current_user_id = user_data['id']

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
def delete_response(response_id):
    """Delete a specific response"""
    # Try JWT first (API)
    try:
        current_user_id = get_jwt_identity()
    except:
        # Check session (web)
        if 'user' not in session:
            from flask import flash, redirect, url_for
            flash('Please login to delete responses', 'error')
            return redirect(url_for('auth.login'))
        user_data = session['user']
        current_user_id = user_data['id']

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
