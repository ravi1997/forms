"""
Analytics utilities for the form builder application.
Provides functions for calculating various analytics and metrics.
"""
from datetime import datetime, timedelta
from sqlalchemy import func
from app import db
from app.models import Form, Response, Answer, Question


def calculate_form_response_count(form_id):
    """Calculate the total number of responses for a form."""
    return Response.query.filter_by(form_id=form_id).count()


def calculate_question_analytics(form_id, question_id):
    """Calculate analytics for a specific question in a form."""
    from app.models import QuestionTypes
    
    question = Question.query.get(question_id)
    if not question or question.section.form_id != form_id:
        return None

    answers = Answer.query.join(Response).filter(
        Answer.question_id == question_id,
        Response.form_id == form_id
    ).all()

    analytics = {
        'question_id': question.id,
        'question_text': question.question_text,
        'question_type': question.question_type.value,
        'total_responses': len(answers),
        'answers': {}
    }

    # Process answers based on question type
    if question.question_type in [QuestionTypes.MULTIPLE_CHOICE, 
                                  QuestionTypes.CHECKBOX, 
                                  QuestionTypes.DROPDOWN]:
        # Count options
        for answer in answers:
            if answer.answer_value:
                if isinstance(answer.answer_value, list):
                    # For checkboxes, answer_value is a list
                    for option in answer.answer_value:
                        analytics['answers'][option] = analytics['answers'].get(option, 0) + 1
                else:
                    option = answer.answer_value or answer.answer_text
                    analytics['answers'][option] = analytics['answers'].get(option, 0) + 1
            elif answer.answer_text:
                option = answer.answer_text
                analytics['answers'][option] = analytics['answers'].get(option, 0) + 1
    elif question.question_type == QuestionTypes.RATING:
        # Calculate average rating and distribution
        ratings = []
        for answer in answers:
            try:
                rating = int(answer.answer_text) if answer.answer_text else 0
                ratings.append(rating)
                str_rating = str(rating)
                analytics['answers'][str_rating] = analytics['answers'].get(str_rating, 0) + 1
            except ValueError:
                pass  # Skip invalid ratings

        if ratings:
            analytics['average_rating'] = sum(ratings) / len(ratings)
    elif question.question_type in [QuestionTypes.TEXT, 
                                    QuestionTypes.LONG_TEXT, 
                                    QuestionTypes.EMAIL, 
                                    QuestionTypes.NUMBER]:
        # For text questions, collect responses for potential text analysis
        analytics['responses'] = [answer.answer_text for answer in answers if answer.answer_text]
    else:
        # For other question types
        analytics['answers'] = {'total_responses': len(answers)}

    return analytics


def calculate_form_time_analytics(form_id):
    """Calculate time-based analytics for a form."""
    responses = Response.query.filter_by(form_id=form_id).all()
    
    time_analytics = {
        'total_responses': len(responses),
        'responses_over_time': {}
    }

    for response in responses:
        if response.submitted_at:
            date_str = response.submitted_at.strftime('%Y-%m-%d')
            time_analytics['responses_over_time'][date_str] = time_analytics['responses_over_time'].get(date_str, 0) + 1

    return time_analytics


def calculate_form_completion_rate(form_id):
    """Calculate form completion rate based on required questions."""
    form = Form.query.get(form_id)
    if not form:
        return None

    required_questions = 0
    all_sections = form.sections
    for section in all_sections:
        for question in section.questions:
            if question.is_required:
                required_questions += 1

    responses = Response.query.filter_by(form_id=form_id).all()
    
    # This is a basic implementation - a more sophisticated approach would track form starts
    # For now, we'll return the number of required questions as a reference point
    return {
        'required_questions_count': required_questions,
        'total_responses': len(responses),
    }


def get_user_engagement_metrics(user_id):
    """Get engagement metrics for a specific user's forms."""
    from app.models import Response
    
    responses = Response.query.join(Form).filter(Form.created_by == user_id).all()

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

    return {
        'total_responses': len(responses),
        'day_responses': day_responses,
        'hour_responses': hour_responses
    }


def calculate_response_rate_trend(form_id, days=30):
    """Calculate response rate trend over specified number of days."""
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    daily_responses = db.session.query(
        func.date(Response.submitted_at).label('date'),
        func.count(Response.id).label('count')
    ).filter(
        Response.form_id == form_id,
        Response.submitted_at >= cutoff_date
    ).group_by(func.date(Response.submitted_at)).order_by('date').all()

    trend_data = []
    for date, count in daily_responses:
        trend_data.append({
            'date': date.isoformat() if hasattr(date, 'isoformat') else str(date),
            'count': count
        })

    return trend_data