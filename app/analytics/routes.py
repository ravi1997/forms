from flask import render_template, request, jsonify, current_app, session
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import db, cache
from app.analytics import bp
from app.models import User, Form, Response, Answer, AuditLog, UserRoles
from datetime import datetime, timedelta
from sqlalchemy import func
import json
from app.utils.analytics import (
    calculate_form_response_count,
    calculate_question_analytics,
    calculate_form_time_analytics,
    calculate_form_completion_rate,
    get_user_engagement_metrics,
    calculate_response_rate_trend
)
from app.utils.caching import (
    get_cached_form_analytics,
    cache_form_analytics,
    get_cached_dashboard_stats,
    cache_dashboard_stats,
    get_cached_user_engagement,
    cache_user_engagement,
    invalidate_user_dashboard_stats,
    invalidate_form_analytics
)

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

    # Try to get cached dashboard stats first
    cached_stats = get_cached_dashboard_stats(current_user_id)
    if cached_stats:
        total_forms = cached_stats['total_forms']
        total_responses = cached_stats['total_responses']
        recent_responses = cached_stats['recent_responses']
        chart_data = cached_stats['chart_data']
        # For top forms, we still need to fetch fresh data since we need form objects
        user_forms = Form.query.filter_by(created_by=current_user_id).all()
        form_stats = []
        for form in user_forms:
            response_count = Response.query.filter_by(form_id=form.id).count()
            form_stats.append({
                'form': form,
                'response_count': response_count
            })
        form_stats.sort(key=lambda x: x['response_count'], reverse=True)
        top_forms = form_stats[:5]  # Top 5 forms
    else:
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

        # Cache the stats for future requests
        cache_dashboard_stats(current_user_id, {
            'total_forms': total_forms,
            'total_responses': total_responses,
            'recent_responses': recent_responses,
            'chart_data': chart_data
        })

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

    # Try to get cached form analytics first
    cached_analytics = get_cached_form_analytics(form_id)
    if cached_analytics:
        response_count = cached_analytics['response_count']
        analytics_data = cached_analytics['analytics_data']
        time_analytics = cached_analytics['time_analytics']
        required_questions = cached_analytics['required_questions']
    else:
        # Get response count
        response_count = calculate_form_response_count(form_id)

        # Get responses to calculate analytics
        responses = Response.query.filter_by(form_id=form_id).all()

        # Prepare analytics data for each question
        analytics_data = []
        all_sections = form.sections
        questions = []
        for section in all_sections:
            questions.extend(section.questions)

        for question in questions:
            question_analytics = calculate_question_analytics(form_id, question.id)
            if question_analytics:
                analytics_data.append(question_analytics)

        # Prepare time-based analytics
        time_analytics = calculate_form_time_analytics(form_id)

        # Get completion rate information
        completion_rate_info = calculate_form_completion_rate(form_id)
        required_questions = completion_rate_info['required_questions_count']

        # Cache the analytics data
        cache_form_analytics(form_id, {
            'response_count': response_count,
            'analytics_data': analytics_data,
            'time_analytics': time_analytics,
            'required_questions': required_questions
        })

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

    # Try to get cached user engagement metrics first
    cached_engagement = get_cached_user_engagement(current_user_id)
    if cached_engagement:
        total_responses = cached_engagement['total_responses']
        day_responses = cached_engagement['day_responses']
        hour_responses = cached_engagement['hour_responses']

        # Calculate form popularity (not cached since it's per-form)
        forms = Form.query.filter_by(created_by=current_user_id).all()
        form_popularity = {}
        for form in forms:
            count = Response.query.filter_by(form_id=form.id).count()
            form_popularity[form.title] = count
    else:
        # Calculate engagement metrics
        engagement_metrics = get_user_engagement_metrics(current_user_id)
        total_responses = engagement_metrics['total_responses']
        day_responses = engagement_metrics['day_responses']
        hour_responses = engagement_metrics['hour_responses']

        # Cache the engagement metrics
        cache_user_engagement(current_user_id, {
            'total_responses': total_responses,
            'day_responses': day_responses,
            'hour_responses': hour_responses
        })

        # Calculate form popularity
        forms = Form.query.filter_by(created_by=current_user_id).all()
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

    # Try to get cached form analytics first
    cached_analytics = get_cached_form_analytics(form_id)
    if cached_analytics:
        analytics_data = cached_analytics['analytics_data']
        time_analytics = cached_analytics['time_analytics']
    else:
        # Get responses to calculate analytics
        responses = Response.query.filter_by(form_id=form_id).all()

        # Prepare analytics data for each question
        analytics_data = []
        all_sections = form.sections
        questions = []
        for section in all_sections:
            questions.extend(section.questions)

        for question in questions:
            question_analytics = calculate_question_analytics(form_id, question.id)
            if question_analytics:
                analytics_data.append(question_analytics)

        # Prepare time-based analytics
        time_analytics = calculate_form_time_analytics(form_id)

        # Cache the analytics data
        cache_form_analytics(form_id, {
            'response_count': len(responses),
            'analytics_data': analytics_data,
            'time_analytics': time_analytics,
            'required_questions': 0  # Not needed for API response
        })

    return jsonify({
        'analytics_data': analytics_data,
        'time_analytics': time_analytics
    })

@bp.route('/api/dashboard-stats', methods=['GET'])
@jwt_required()
def api_dashboard_stats():
    """API endpoint to get dashboard statistics"""
    current_user_id = get_jwt_identity()

    # Try to get cached dashboard stats first
    cached_stats = get_cached_dashboard_stats(current_user_id)
    if cached_stats:
        return jsonify({
            'total_forms': cached_stats['total_forms'],
            'total_responses': cached_stats['total_responses'],
            'recent_responses': cached_stats['recent_responses'],
            'chart_data': cached_stats['chart_data']
        })
    else:
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

        # Cache the stats for future API requests
        stats_data = {
            'total_forms': total_forms,
            'total_responses': total_responses,
            'recent_responses': recent_responses,
            'chart_data': chart_data
        }
        cache_dashboard_stats(current_user_id, stats_data)

        return jsonify(stats_data)