from app import db
from app.models import Form, Section, Question, FormTemplate
from flask import url_for, current_app

class FormService:
    @staticmethod
    def create_form(data, user_id):
        """
        Creates a new form.
        """
        title = data.get('title')
        description = data.get('description', '')

        if not title:
            return None, "Form title is required"

        form = Form(
            title=title,
            description=description,
            created_by=user_id
        )

        db.session.add(form)
        db.session.commit()

        return form, None

    @staticmethod
    def update_form_structure(form_id, structure):
        """
        Updates the structure of a form.
        """
        form = Form.query.get(form_id)
        if not form:
            return None, "Form not found"

        # Get current sections and questions
        current_sections = {s.id: s for s in form.sections}
        current_questions = {q.id: q for s in form.sections for q in s.questions}

        # Keep track of sections and questions that are still in the form
        kept_section_ids = set()
        kept_question_ids = set()

        for section_data in structure:
            section_id = section_data.get('id')
            if section_id and section_id in current_sections:
                # Update existing section
                section = current_sections[section_id]
                section.title = section_data.get('title', '')
                section.description = section_data.get('description', '')
                section.order = section_data.get('order', 0)
                kept_section_ids.add(section_id)
            else:
                # Create new section
                section = Section(
                    title=section_data.get('title', ''),
                    description=section_data.get('description', ''),
                    form_id=form_id,
                    order=section_data.get('order', 0)
                )
                db.session.add(section)
                db.session.flush()  # Get section ID

            for question_data in section_data.get('questions', []):
                question_id = question_data.get('id')
                if question_id and question_id in current_questions:
                    # Update existing question
                    question = current_questions[question_id]
                    question.question_type = question_data['question_type']
                    question.question_text = question_data['question_text']
                    question.is_required = question_data.get('is_required', False)
                    question.order = question_data.get('order', 0)
                    question.validation_rules = question_data.get('validation_rules', {})
                    question.options = question_data.get('options', [])
                    kept_question_ids.add(question_id)
                else:
                    # Create new question
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
        
        # Delete sections that were removed
        for section_id, section in current_sections.items():
            if section_id not in kept_section_ids:
                for question in section.questions:
                    db.session.delete(question)
                db.session.delete(section)

        # Delete questions that were removed
        for question_id, question in current_questions.items():
            if question_id not in kept_question_ids:
                db.session.delete(question)

        db.session.commit()
        
        return form, None

    @staticmethod
    def create_form_from_template(template_id, user_id):
        """
        Creates a new form from a template.
        """
        template = FormTemplate.query.get(template_id)
        if not template:
            return None, "Template not found"

        if not template.is_public and template.created_by != user_id:
            return None, "You do not have access to this template"

        form = Form(
            title=f"Copy of {template.name}",
            description=template.description,
            created_by=user_id,
            template_id=template.id
        )
    
        db.session.add(form)
        db.session.flush() # Get form ID without committing
    
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
                db.session.flush()
            
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
        return form, None
