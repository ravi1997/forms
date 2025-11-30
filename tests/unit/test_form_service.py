import pytest
from app import create_app, db
from app.models import User, Form, FormTemplate
from app.services.form_service import FormService
from app.services.user_service import UserService

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

def test_create_form(app, user):
    """
    Test form creation.
    """
    with app.app_context():
        data = {
            'title': 'Test Form',
            'description': 'This is a test form.'
        }
        form, error = FormService.create_form(data, user.id)
        assert form is not None
        assert error is None
        assert form.title == 'Test Form'
        assert form.description == 'This is a test form.'
        assert form.created_by == user.id

def test_create_form_no_title(app, user):
    """
    Test creating a form with no title.
    """
    with app.app_context():
        data = {
            'description': 'This is a test form.'
        }
        form, error = FormService.create_form(data, user.id)
        assert form is None
        assert error == "Form title is required"

def test_update_form_structure(app, user):
    """
    Test updating a form's structure.
    """
    with app.app_context():
        # Create a form
        form_data = {
            'title': 'Test Form',
            'description': 'This is a test form.'
        }
        form, _ = FormService.create_form(form_data, user.id)

        # Update the structure
        structure = [
            {
                'title': 'Section 1',
                'description': 'This is section 1.',
                'order': 0,
                'questions': [
                    {
                        'question_type': 'TEXT',
                        'question_text': 'What is your name?',
                        'order': 0
                    }
                ]
            }
        ]
        updated_form, error = FormService.update_form_structure(form.id, structure)
        assert updated_form is not None
        assert error is None
        assert len(updated_form.sections) == 1
        assert updated_form.sections[0].title == 'Section 1'
        assert len(updated_form.sections[0].questions) == 1
        assert updated_form.sections[0].questions[0].question_text == 'What is your name?'

def test_create_form_from_template(app, user):
    """
    Test creating a form from a template.
    """
    with app.app_context():
        # Create a template
        template = FormTemplate(
            name='Test Template',
            description='This is a test template.',
            created_by=user.id,
            is_public=True,
            content={
                'sections': [
                    {
                        'title': 'Section 1',
                        'description': 'This is section 1.',
                        'order': 0,
                        'questions': [
                            {
                                'question_type': 'TEXT',
                                'question_text': 'What is your name?',
                                'order': 0
                            }
                        ]
                    }
                ]
            }
        )
        db.session.add(template)
        db.session.commit()

        # Create a form from the template
        form, error = FormService.create_form_from_template(template.id, user.id)
        assert form is not None
        assert error is None
        assert form.title == 'Copy of Test Template'
        assert len(form.sections) == 1
        assert form.sections[0].title == 'Section 1'
        assert len(form.sections[0].questions) == 1
        assert form.sections[0].questions[0].question_text == 'What is your name?'
