from datetime import datetime
from app import create_app, db
from app.models import User, Form, Section, Question, Response, Answer, FormTemplate, QuestionLibrary, AuditLog
from flask_migrate import upgrade

app = create_app()

@app.shell_context_processor
def make_shell_context():
    return {'db': db, 'User': User, 'Form': Form, 'Section': Section, 'Question': Question,
            'Response': Response, 'Answer': Answer, 'FormTemplate': FormTemplate,
            'QuestionLibrary': QuestionLibrary, 'AuditLog': AuditLog}

if __name__ == '__main__':
    with app.app_context():
        # Run any pending migrations
        try:
            upgrade()
        except Exception as e:
            print(f"Error running migrations: {e}")
    
    # Set a start time for health checks
    app.config['START_TIME'] = 'started_at_' + str(datetime.utcnow())
    
    app.run(debug=app.config.get('DEBUG', False))