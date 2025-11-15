from flask import render_template, request, jsonify, current_app, session
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import db
from app.analytics import bp
from app.models import User, Form, Response, Answer, AuditLog
from datetime import datetime, timedelta
from sqlalchemy import func
import json

@bp.route('/', methods=['GET'])
def dashboard():
    """Main analytics dashboard"""
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

    user = User.query.get_or_404(current_user_id)
    
    # Get user's forms
    user_forms = Form.query.filter_by(created_by=current_user_id).all()
    
    # Get overall stats
    total_forms = len(user_forms)
    total_responses = Response.query.join(Form).filter(Form.created_by == current_user_id).count()
    
    # Get recent activity (last 7 days)
    seven_days_ago = datetime.utcnow() - timedelta(days=7)
    recent_responses = Response.query.join(Form).filter(
        Form.created_by == current_user_id,
        Response.submitted_at >= seven_days_ago
    ).count()
    
    # Get responses over time for the last 30 days
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    daily_responses = db.session.query(
        func.date(Response.submitted_at).label('date'),
        func.count(Response.id).label('count')
    ).join(Form).filter(
        Form.created_by == current_user_id,
        Response.submitted_at >= thirty_days_ago
    ).group_by(func.date(Response.submitted_at)).order_by('date').all()
    
    # Prepare chart data
    chart_data = []
    for date, count in daily_responses:
        chart_data.append({
            'date': date.isoformat() if hasattr(date, 'isoformat') else str(date),
            'count': count
        })
    
    # Get top performing forms
    form_stats = []
    for form in user_forms:
        response_count = Response.query.filter_by(form_id=form.id).count()
        form_stats.append({
            'form': form,
            'response_count': response_count
        })
    
    # Sort by response count (descending)
    form_stats.sort(key=lambda x: x['response_count'], reverse=True)
    top_forms = form_stats[:5]  # Top 5 forms
    
    return render_template('analytics/dashboard.html',
                          total_forms=total_forms,
                          total_responses=total_responses,
                          recent_responses=recent_responses,
                          chart_data=chart_data,
                          top_forms=top_forms)

@bp.route('/form/<int:form_id>', methods=['GET'])
def form_analytics_page(form_id):
    """Detailed analytics for a specific form"""
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
            
            if ratings:
                question_analytics['average_rating'] = sum(ratings) / len(ratings)
        elif question.question_type in ['text', 'long_text', 'email', 'number']:
            # For text questions, collect responses for potential text analysis
            question_analytics['responses'] = [answer.answer_text for answer in answers if answer.answer_text]
        else:
            # For other question types
            question_analytics['answers'] = {'total_responses': len(answers)}
        
        analytics_data.append(question_analytics)
    
    # Prepare time-based analytics
    time_analytics = {
        'total_responses': response_count,
        'responses_over_time': {}
    }
    
    if responses:
        for response in responses:
            if response.submitted_at:
                date_str = response.submitted_at.strftime('%Y-%m-%d')
                if date_str in time_analytics['responses_over_time']:
                    time_analytics['responses_over_time'][date_str] += 1
                else:
                    time_analytics['responses_over_time'][date_str] = 1
    
    # Get completion rate (if we track form starts vs submissions)
    # For now, we'll estimate based on required questions
    required_questions = 0
    for section in all_sections:
        for question in section.questions:
            if question.is_required:
                required_questions += 1
    
    return render_template('analytics/form_analytics.html',
                          form=form,
                          response_count=response_count,
                          required_questions=required_questions,
                          analytics_data=analytics_data,
                          time_analytics=time_analytics)

@bp.route('/user-engagement', methods=['GET'])
def user_engagement():
    """User engagement analytics"""
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

    user = User.query.get_or_404(current_user_id)
    
    # Get forms created by user
    forms = Form.query.filter_by(created_by=current_user_id).all()
    
    # Get all responses to user's forms
    responses = Response.query.join(Form).filter(Form.created_by == current_user_id).all()
    
    # Calculate engagement metrics
    total_responses = len(responses)
    
    # Responses by day of week
    day_responses = {}
    for response in responses:
        if response.submitted_at:
            day_name = response.submitted_at.strftime('%A')
            day_responses[day_name] = day_responses.get(day_name, 0) + 1
    
    # Responses by hour
    hour_responses = {}
    for response in responses:
        if response.submitted_at:
            hour = response.submitted_at.hour
            hour_responses[hour] = hour_responses.get(hour, 0) + 1
    
    # Form popularity
    form_popularity = {}
    for form in forms:
        count = Response.query.filter_by(form_id=form.id).count()
        form_popularity[form.title] = count
    
    return render_template('analytics/user_engagement.html',
                          total_responses=total_responses,
                          day_responses=day_responses,
                          hour_responses=hour_responses,
                          form_popularity=form_popularity)

@bp.route('/api/form/<int:form_id>/responses', methods=['GET'])
@jwt_required()
def api_form_responses(form_id):
    """API endpoint to get form responses data for dynamic charts"""
    current_user_id = get_jwt_identity()
    form = Form.query.get_or_404(form_id)
    
    # Check if user has permission to view analytics
    if form.created_by != current_user_id and not User.query.get(current_user_id).can_view_analytics():
        return jsonify({'error': 'forbidden', 'message': 'You do not have permission to view analytics'}), 403
    
    # Get responses to calculate analytics
    responses = Response.query.filter_by(form_id=form_id).all()
    
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
                    pass # Skip invalid ratings
            
            if ratings:
                question_analytics['average_rating'] = sum(ratings) / len(ratings)
        else:
            # For other question types
            question_analytics['answers'] = {'total_responses': len(answers)}
        
        analytics_data.append(question_analytics)
    
    # Prepare time-based analytics
    time_analytics = {
        'total_responses': len(responses),
        'responses_over_time': {}
    }
    
    if responses:
        for response in responses:
            if response.submitted_at:
                date_str = response.submitted_at.strftime('%Y-%m-%d')
                if date_str in time_analytics['responses_over_time']:
                    time_analytics['responses_over_time'][date_str] += 1
                else:
                    time_analytics['responses_over_time'][date_str] = 1
    
    return jsonify({
        'analytics_data': analytics_data,
        'time_analytics': time_analytics
    })

@bp.route('/api/dashboard-stats', methods=['GET'])
@jwt_required()
def api_dashboard_stats():
    """API endpoint to get dashboard statistics"""
    current_user_id = get_jwt_identity()
    
    # Get user's forms
    user_forms = Form.query.filter_by(created_by=current_user_id).all()
    
    # Get overall stats
    total_forms = len(user_forms)
    total_responses = Response.query.join(Form).filter(Form.created_by == current_user_id).count()
    
    # Get recent activity (last 7 days)
    seven_days_ago = datetime.utcnow() - timedelta(days=7)
    recent_responses = Response.query.join(Form).filter(
        Form.created_by == current_user_id,
        Response.submitted_at >= seven_days_ago
    ).count()
    
    # Get responses over time for the last 30 days
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    daily_responses = db.session.query(
        func.date(Response.submitted_at).label('date'),
        func.count(Response.id).label('count')
    ).join(Form).filter(
        Form.created_by == current_user_id,
        Response.submitted_at >= thirty_days_ago
    ).group_by(func.date(Response.submitted_at)).order_by('date').all()
    
    # Prepare chart data
    chart_data = []
    for date, count in daily_responses:
        chart_data.append({
            'date': date.isoformat() if hasattr(date, 'isoformat') else str(date),
            'count': count
        })
    
    return jsonify({
        'total_forms': total_forms,
        'total_responses': total_responses,
        'recent_responses': recent_responses,
        'chart_data': chart_data
    })