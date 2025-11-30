import pytest
from app import create_app, db
from app.models import User, Form, Response, Answer, Section, Question
from app.services.response_service import ResponseService
from app.services.user_service import UserService
from app.services.form_service import FormService

@pytest.fixture
def app():
    """Create and configure a new app instance for each test."""
    app = create_app('testing')
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()

@pytest.fixture
def user(app):
    """Create a new user for each test."""
    with app.app_context():
        data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'password'
        }
        user, _ = UserService.create_user(data)
        return user

@pytest.fixture
def form(app, user):
    """Create a new form for each test."""
    with app.app_context():
        data = {
            'title': 'Test Form',
            'description': 'This is a test form.'
        }
        form, _ = FormService.create_form(data, user.id)
        # Add a section and a question to the form
        section = Section(form_id=form.id, title="Section 1", order=1)
        db.session.add(section)
        db.session.commit()
        question = Question(section_id=section.id, question_text="Question 1", question_type="TEXT", order=1)
        db.session.add(question)
        db.session.commit()
        return form

def test_get_responses_paginated(app, form, user):
    """
    Test getting paginated responses for a form.
    """
    with app.app_context():
        # Create a response
        response = Response(form_id=form.id, user_id=user.id)
        db.session.add(response)
        db.session.commit()

        # Get paginated responses
        responses = ResponseService.get_responses_paginated(form.id, 1, 10)
        assert responses is not None
        assert len(responses.items) == 1
        assert responses.items[0].id == response.id

def test_export_responses_csv(app, form, user):
    """
    Test exporting responses in CSV format.
    """
    with app.app_context():
        # Create a response
        response = Response(form_id=form.id, user_id=user.id)
        db.session.add(response)
        db.session.commit()
        question = form.sections[0].questions[0]
        answer = Answer(response_id=response.id, question_id=question.id, answer_text="Answer 1")
        db.session.add(answer)
        db.session.commit()

        # Export responses
        data, mimetype = ResponseService.export_responses(form.id, 'csv')
        assert data is not None
        assert mimetype == 'text/csv'
        assert b'Response ID,Submitted At,User ID,Question 1' in data
        assert b'Answer 1' in data

def test_export_responses_json(app, form, user):
    """
    Test exporting responses in JSON format.
    """
    with app.app_context():
        # Create a response
        response = Response(form_id=form.id, user_id=user.id)
        db.session.add(response)
        db.session.commit()
        question = form.sections[0].questions[0]
        answer = Answer(response_id=response.id, question_id=question.id, answer_text="Answer 1")
        db.session.add(answer)
        db.session.commit()

        # Export responses
        data, mimetype = ResponseService.export_responses(form.id, 'json')
        assert data is not None
        assert mimetype == 'application/json'
        assert '"response_id":' in data
        assert '"answer_text": "Answer 1"' in data
