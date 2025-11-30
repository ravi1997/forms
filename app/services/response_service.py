from app import db
from app.models import Response, Answer, Form, User
from flask import current_app
import csv
import json
import io
from datetime import datetime
import pandas as pd
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors

class ResponseService:
    @staticmethod
    def get_responses_paginated(form_id, page, per_page):
        """
        Gets paginated responses for a form.
        """
        return Response.query.filter_by(form_id=form_id).options(
            db.joinedload(Response.answers),
            db.joinedload(Response.user)
        ).paginate(page=page, per_page=per_page, error_out=False)

    @staticmethod
    def export_responses(form_id, format_type):
        """
        Exports responses for a form in the specified format.
        """
        form = Form.query.get_or_404(form_id)
        responses = Response.query.filter_by(form_id=form_id).all()
        all_sections = form.sections
        questions = []
        for section in all_sections:
            questions.extend(section.questions)

        if format_type == 'csv':
            output = io.StringIO()
            writer = csv.writer(output)
            
            headers = ['Response ID', 'Submitted At', 'User ID']
            for question in questions:
                headers.append(question.question_text)
            writer.writerow(headers)
            
            for response in responses:
                answers = {answer.question_id: answer for answer in response.answers}
                row = [response.id, response.submitted_at, response.user_id or 'Anonymous']
                
                for question in questions:
                    answer = answers.get(question.id)
                    if answer:
                        value = answer.answer_text or str(answer.answer_value) if answer.answer_value else ''
                        row.append(value)
                    else:
                        row.append('')
                
                writer.writerow(row)
            
            output.seek(0)
            return output.getvalue().encode('utf-8'), 'text/csv'

        elif format_type == 'json':
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
            
            return json.dumps(responses_data, indent=2, default=str), 'application/json'

        elif format_type == 'excel':
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
                        value = answer.answer_text or str(answer.answer_value) if answer.answer_value else ''
                        row[question.question_text] = value
                    else:
                        row[question.question_text] = ''
                
                data.append(row)
            
            df = pd.DataFrame(data)
            
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='Responses')
            
            output.seek(0)
            return output, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'

        elif format_type == 'pdf':
            output = io.BytesIO()
            doc = SimpleDocTemplate(output, pagesize=letter)
            story = []
            
            styles = getSampleStyleSheet()
            title = Paragraph(f"Form Responses - {form.title}", styles['Title'])
            story.append(title)
            story.append(Spacer(1, 12))
            
            form_info = Paragraph(f"Form ID: {form.id} | Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", styles['Normal'])
            story.append(form_info)
            story.append(Spacer(1, 12))
            
            data = [['Response ID', 'Submitted At', 'User ID'] + [q.question_text for q in questions]]
            for response in responses:
                answers = {answer.question_id: answer for answer in response.answers}
                row = [str(response.id), response.submitted_at.strftime('%Y-%m-%d %H:%M:%S') if response.submitted_at else 'N/A', 
                       str(response.user_id or 'Anonymous')]
                
                for question in questions:
                    answer = answers.get(question.id)
                    if answer:
                        value = answer.answer_text or str(answer.answer_value) if answer.answer_value else ''
                        row.append(value)
                    else:
                        row.append('')
                
                data.append(row)
            
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
            
            doc.build(story)
            
            output.seek(0)
            return output, 'application/pdf'
        
        return None, None
