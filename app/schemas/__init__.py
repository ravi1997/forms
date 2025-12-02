from marshmallow import Schema, fields, post_load, EXCLUDE
from app import ma
from app.models import User, Form, Section, Question, Response, Answer, FormTemplate, QuestionLibrary, AuditLog
from app.models import UserRoles, QuestionTypes

class UserSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = User
        load_instance = True
        exclude = ('password_hash',)
    
    responses = ma.Nested(lambda: ResponseSchema, many=True, exclude=('user',))
    created_forms = ma.Nested(lambda: FormSchema, many=True, exclude=('creator',))
    role = ma.Enum(UserRoles)

class FormSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Form
        load_instance = True
    
    creator = ma.Nested(UserSchema, exclude=('created_forms', 'responses'))
    sections = ma.Nested(lambda: SectionSchema, many=True)
    responses = ma.Nested(lambda: ResponseSchema, many=True, exclude=('form',))
    template_id = fields.Integer(required=False, allow_none=True)

class SectionSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Section
        load_instance = True
    
    questions = ma.Nested(lambda: QuestionSchema, many=True)

class QuestionSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Question
        load_instance = True
    
    question_type = ma.Enum(QuestionTypes)

class ResponseSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Response
        load_instance = True
    
    form = ma.Nested(FormSchema, exclude=('responses',))
    user = ma.Nested(UserSchema, exclude=('responses', 'created_forms'))
    answers = ma.Nested(lambda: AnswerSchema, many=True)

class AnswerSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Answer
        load_instance = True
    
    question = ma.Nested(QuestionSchema)

class FormTemplateSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = FormTemplate
        load_instance = True
    
    creator = ma.Nested(UserSchema, exclude=('created_forms',))

class QuestionLibrarySchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = QuestionLibrary
        load_instance = True
    
    question_type = ma.Enum(QuestionTypes)
    creator = ma.Nested(UserSchema, exclude=('created_questions',))

class AuditLogSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = AuditLog
        load_instance = True
    
    user = ma.Nested(UserSchema, exclude=('audit_logs',))

# Request Schemas for validation
class LoginFormSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    username = fields.Str(required=True, validate=lambda x: len(x) >= 3)
    password = fields.Str(required=True, validate=lambda x: len(x) >= 6)

class RegisterFormSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    username = fields.Str(required=True, validate=lambda x: 3 <= len(x) <= 80)
    email = fields.Email(required=True)
    password = fields.Str(required=True, validate=lambda x: len(x) >= 8)
    first_name = fields.Str(required=False)
    last_name = fields.Str(required=False)

class UpdateProfileSchema(Schema):
    first_name = fields.Str(required=False)
    last_name = fields.Str(required=False)
    email = fields.Email(required=False)
    preferences = fields.Dict(required=False)

class CreateFormSchema(Schema):
    title = fields.Str(required=True, validate=lambda x: 1 <= len(x) <= 200)
    description = fields.Str(required=False)
    settings = fields.Dict(required=False)

class UpdateFormSchema(Schema):
    title = fields.Str(required=False, validate=lambda x: 1 <= len(x) <= 200)
    description = fields.Str(required=False)
    settings = fields.Dict(required=False)
    is_published = fields.Bool(required=False)

class CreateSectionSchema(Schema):
    title = fields.Str(required=False, validate=lambda x: len(x) <= 200)
    description = fields.Str(required=False)
    order = fields.Int(required=False)

class UpdateSectionSchema(Schema):
    title = fields.Str(required=False, validate=lambda x: len(x) <= 200)
    description = fields.Str(required=False)
    order = fields.Int(required=False)

class CreateQuestionSchema(Schema):
    question_type = ma.Enum(QuestionTypes, required=True)
    question_text = fields.Str(required=True)
    is_required = fields.Bool(required=False)
    order = fields.Int(required=False)
    validation_rules = fields.Dict(required=False)
    options = fields.List(fields.Dict(), required=False)

class UpdateQuestionSchema(Schema):
    question_type = ma.Enum(QuestionTypes, required=False)
    question_text = fields.Str(required=False)
    is_required = fields.Bool(required=False)
    order = fields.Int(required=False)
    validation_rules = fields.Dict(required=False)
    options = fields.List(fields.Dict(), required=False)

class SubmitResponseSchema(Schema):
    answers = fields.List(fields.Dict(keys=fields.Int(), values=fields.Raw()), required=True)

class CreateTemplateSchema(Schema):
    name = fields.Str(required=True)
    description = fields.Str(required=False)
    is_public = fields.Bool(required=False)
    content = fields.Dict(required=True)

class CreateQuestionLibrarySchema(Schema):
    question_text = fields.Str(required=True)
    question_type = ma.Enum(QuestionTypes, required=True)
    options = fields.List(fields.Dict(), required=False)
    is_public = fields.Bool(required=False)
    validation_rules = fields.Dict(required=False)
    is_required = fields.Bool(required=False)