from celery import current_task
from datetime import datetime, timedelta
from app import celery, db
from app.models import Form, Response, Answer, AuditLog
import logging

@celery.task
def update_form_analytics(form_id):
    """
    Background task to update form analytics
    This would typically aggregate response data for faster dashboard loading
    """
    try:
        # Get the form
        form = Form.query.get(form_id)
        if not form:
            logging.error(f"Form with ID {form_id} not found")
            return {'status': 'error', 'message': f'Form {form_id} not found'}
        
        # Calculate analytics data
        response_count = Response.query.filter_by(form_id=form_id).count()
        
        # Get all questions in the form
        all_sections = form.sections
        questions = []
        for section in all_sections:
            questions.extend(section.questions)
        
        # Calculate analytics for each question
        analytics_data = {}
        for question in questions:
            answers = Answer.query.join(Response).filter(
                Answer.question_id == question.id,
                Response.form_id == form_id
            ).all()
            
            if question.question_type.value in ['multiple_choice', 'checkbox', 'dropdown']:
                # Count options
                option_counts = {}
                for answer in answers:
                    if answer.answer_value:
                        if isinstance(answer.answer_value, list):
                            # For checkboxes, answer_value is a list
                            for option in answer.answer_value:
                                option_counts[option] = option_counts.get(option, 0) + 1
                        else:
                            option = answer.answer_value or answer.answer_text
                            option_counts[option] = option_counts.get(option, 0) + 1
                    elif answer.answer_text:
                        option = answer.answer_text
                        option_counts[option] = option_counts.get(option, 0) + 1
                
                analytics_data[question.id] = {
                    'type': 'options',
                    'counts': option_counts,
                    'total_responses': len(answers)
                }
            elif question.question_type.value == 'rating':
                # Calculate average rating
                ratings = []
                for answer in answers:
                    try:
                        rating = int(answer.answer_text) if answer.answer_text else 0
                        ratings.append(rating)
                    except ValueError:
                        pass  # Skip invalid ratings
                
                if ratings:
                    avg_rating = sum(ratings) / len(ratings)
                    analytics_data[question.id] = {
                        'type': 'rating',
                        'average': avg_rating,
                        'total_responses': len(answers)
                    }
            else:
                # For other question types, just count responses
                analytics_data[question.id] = {
                    'type': 'count',
                    'total_responses': len(answers)
                }
        
        # Update form's analytics cache
        form.analytics_cache = {
            'response_count': response_count,
            'question_analytics': analytics_data,
            'updated_at': datetime.utcnow().isoformat()
        }
        
        db.session.commit()
        
        # Update progress
        current_task.update_state(
            state='SUCCESS',
            meta={'status': 'Analytics updated successfully', 'response_count': response_count}
        )
        
        return {'status': 'success', 'response_count': response_count}
    
    except Exception as e:
        logging.error(f"Error updating form analytics: {str(e)}")
        db.session.rollback()
        
        current_task.update_state(
            state='FAILURE',
            meta={'status': 'Error updating analytics', 'error': str(e)}
        )
        
        return {'status': 'error', 'message': str(e)}

@celery.task
def export_responses_task(form_id, format_type, user_id):
    """
    Background task to export form responses
    This would handle large exports that might take time
    """
    try:
        from io import StringIO
        import csv
        import json
        
        # Get the form
        form = Form.query.get(form_id)
        if not form:
            return {'status': 'error', 'message': f'Form {form_id} not found'}
        
        # Get all responses for this form
        responses = Response.query.filter_by(form_id=form_id).all()
        
        # Get all questions in the form to create headers
        all_sections = form.sections
        questions = []
        for section in all_sections:
            questions.extend(section.questions)
        
        if format_type == 'csv':
            # Create CSV content
            output = StringIO()
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
            
            # In a real application, you would save this to a file and provide a download link
            content = output.getvalue()
            output.close()
            
            return {
                'status': 'success', 
                'format': 'csv', 
                'content': content,
                'filename': f'responses_{form_id}.csv'
            }
        
        elif format_type == 'json':
            # Create JSON content
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
            
            content = json.dumps(responses_data, indent=2, default=str)
            
            return {
                'status': 'success', 
                'format': 'json', 
                'content': content,
                'filename': f'responses_{form_id}.json'
            }
        
        else:
            return {'status': 'error', 'message': f'Unsupported format: {format_type}'}
    
    except Exception as e:
        logging.error(f"Error exporting responses: {str(e)}")
        
        current_task.update_state(
            state='FAILURE',
            meta={'status': 'Error exporting responses', 'error': str(e)}
        )
        
        return {'status': 'error', 'message': str(e)}

@celery.task
def cleanup_old_responses(form_id, days_to_keep):
    """
    Background task to cleanup old responses
    """
    try:
        cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
        
        # Count how many responses will be deleted
        old_responses = Response.query.filter(
            Response.form_id == form_id,
            Response.submitted_at < cutoff_date
        ).all()
        
        old_response_count = len(old_responses)
        
        # Delete old responses and their answers
        for response in old_responses:
            # Delete answers first (due to foreign key constraint)
            Answer.query.filter_by(response_id=response.id).delete()
            # Then delete the response
            db.session.delete(response)
        
        db.session.commit()
        
        return {
            'status': 'success',
            'form_id': form_id,
            'responses_deleted': old_response_count,
            'cutoff_date': cutoff_date.isoformat()
        }
    
    except Exception as e:
        logging.error(f"Error cleaning up old responses: {str(e)}")
        db.session.rollback()
        
        return {'status': 'error', 'message': str(e)}