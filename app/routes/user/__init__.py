from flask import Blueprint, request, jsonify, current_app
from app.models.user import User, StatusEnum
from app.schemas.user_schema import UserSchema, UserCreateSchema, UserUpdateSchema, UserPublicSchema
from app.extensions import db
import uuid
from datetime import datetime
from functools import wraps

# Create the user blueprint
user_bp = Blueprint('user', __name__, url_prefix='/users')

# Authentication and authorization decorators
def require_auth(f):
    """Decorator to require authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # In a real application, you would extract and validate the token here
        # For now, we'll implement a basic check
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return jsonify({'error': 'Authorization header is required'}), 401
        
        # Basic token validation (in real app, validate JWT or session)
        if not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Authorization header must start with Bearer'}), 401
        
        token = auth_header.split(' ')[1]
        if not token:
            return jsonify({'error': 'Token is required'}), 401
        
        # In a real application, you would validate the token against your auth system
        # For now, we'll just continue with the request
        # You would typically decode the JWT and store user info in g or request
        return f(*args, **kwargs)
    
    return decorated_function

def require_role(required_role):
    """Decorator to require a specific role"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # In a real application, you would check the user's roles from the token
            # For now, we'll just continue with the request
            # You would typically check if the user has the required role
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def require_permission(permission):
    """Decorator to require a specific permission"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # In a real application, you would check the user's permissions
            # For now, we'll just continue with the request
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# Helper function to get pagination parameters
def get_pagination_params():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    # Limit per_page to prevent abuse
    per_page = min(per_page, 100)
    return page, per_page

# Helper function to get filter parameters
def get_filter_params():
    query = request.args.get('query', '', type=str)
    status = request.args.get('status', '', type=str)
    department = request.args.get('department', '', type=str)
    designation = request.args.get('designation', '', type=str)
    return query, status, department, designation

# Helper function to get sort parameters
def get_sort_params():
    sort_by = request.args.get('sort_by', 'created_at', type=str)
    sort_order = request.args.get('sort_order', 'desc', type=str).lower()
    return sort_by, sort_order

# GET /users - List all users with pagination, filtering, and sorting
@user_bp.route('/', methods=['GET'])
@require_auth
def get_users():
    try:
        # Get pagination, filter, and sort parameters
        page, per_page = get_pagination_params()
        query, status, department, designation = get_filter_params()
        sort_by, sort_order = get_sort_params()
        
        # Build the query
        users_query = User.query
        
        # Apply filters
        if status:
            try:
                status_enum = StatusEnum(status.upper())
                users_query = users_query.filter(User.status == status_enum)
            except ValueError:
                return jsonify({'error': f'Invalid status value: {status}'}), 400
        
        if department:
            users_query = users_query.filter(User.department.ilike(f'%{department}%'))
        
        if designation:
            users_query = users_query.filter(User.designation.ilike(f'%{designation}%'))
        
        if query:
            search_filter = (
                User.first_name.ilike(f'%{query}%') |
                User.middle_name.ilike(f'%{query}%') |
                User.last_name.ilike(f'%{query}%')
            )
            users_query = users_query.filter(search_filter)
        
        # Exclude soft-deleted users unless specifically requested
        users_query = users_query.filter(User.deleted_at.is_(None))
        
        # Apply sorting
        if hasattr(User, sort_by):
            column = getattr(User, sort_by)
            if sort_order == 'asc':
                users_query = users_query.order_by(column.asc())
            else:
                users_query = users_query.order_by(column.desc())
        else:
            # Default sorting by created_at descending
            users_query = users_query.order_by(User.created_at.desc())
        
        # Paginate the results
        paginated_users = users_query.paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        # Serialize the users using UserPublicSchema
        user_schema = UserPublicSchema(many=True)
        users_data = user_schema.dump(paginated_users.items)
        
        # Prepare the response
        response_data = {
            'users': users_data,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': paginated_users.total,
                'pages': paginated_users.pages,
                'has_next': paginated_users.has_next,
                'has_prev': paginated_users.has_prev
            }
        }
        
        return jsonify(response_data), 200
    except Exception as e:
        return jsonify({'error': 'An error occurred while fetching users', 'details': str(e)}), 500

# GET /users/<id> - Get a specific user by ID
@user_bp.route('/<uuid:id>', methods=['GET'])
@require_auth
def get_user(id):
    try:
        user = User.query.filter_by(id=id, deleted_at=None).first()
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Serialize the user using UserPublicSchema
        user_schema = UserPublicSchema()
        user_data = user_schema.dump(user)
        
        return jsonify({'user': user_data}), 200
    except Exception as e:
        return jsonify({'error': 'An error occurred while fetching the user', 'details': str(e)}), 500

# POST /users - Create a new user
@user_bp.route('/', methods=['POST'])
@require_auth
@require_role('admin')
def create_user():
    try:
        # Validate and deserialize the input data
        user_schema = UserCreateSchema()
        user_data = user_schema.load(request.json)
        
        # Create a new user instance
        user = User.from_dict(user_data)
        
        # Set the ID if not provided
        if not user.id:
            user.id = uuid.uuid4()
        
        # Validate the user data
        validation_errors = user.validate()
        if validation_errors:
            return jsonify({'errors': validation_errors}), 400
        
        # Set status to INACTIVE by default if not provided
        if not user.status:
            user.status = StatusEnum.INACTIVE
        
        # Add the user to the database
        db.session.add(user)
        db.session.commit()
        
        # Serialize the created user using UserPublicSchema
        response_schema = UserPublicSchema()
        user_data = response_schema.dump(user)
        
        return jsonify({'user': user_data}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'An error occurred while creating the user', 'details': str(e)}), 500

# PUT /users/<id> - Update a specific user by ID
@user_bp.route('/<uuid:id>', methods=['PUT'])
@require_auth
@require_role('admin')
def update_user(id):
    try:
        # Validate and deserialize the input data
        user_schema = UserUpdateSchema()
        user_data = user_schema.load(request.json)
        
        # Find the user by ID
        user = User.query.filter_by(id=id, deleted_at=None).first()
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Update the user fields with provided data
        for field, value in user_data.items():
            if value is not None:
                setattr(user, field, value)
        
        # Update the updated_at timestamp and updated_by if provided
        user.updated_at = db.func.now()
        if 'updated_by' in user_data and user_data['updated_by']:
            user.updated_by = user_data['updated_by']
        
        # Validate the updated user data
        validation_errors = user.validate()
        if validation_errors:
            return jsonify({'errors': validation_errors}), 400
        
        # Commit the changes to the database
        db.session.commit()
        
        # Serialize the updated user using UserPublicSchema
        response_schema = UserPublicSchema()
        user_data = response_schema.dump(user)
        
        return jsonify({'user': user_data}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'An error occurred while updating the user', 'details': str(e)}), 500

# PATCH /users/<id> - Partially update a specific user by ID
@user_bp.route('/<uuid:id>', methods=['PATCH'])
@require_auth
@require_role('admin')
def partial_update_user(id):
    try:
        # Validate and deserialize the input data
        user_schema = UserUpdateSchema()
        user_data = user_schema.load(request.json)
        
        # Find the user by ID
        user = User.query.filter_by(id=id, deleted_at=None).first()
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Update only the fields that were provided in the request
        for field, value in user_data.items():
            if value is not None:
                setattr(user, field, value)
        
        # Update the updated_at timestamp and updated_by if provided
        user.updated_at = db.func.now()
        if 'updated_by' in user_data and user_data['updated_by']:
            user.updated_by = user_data['updated_by']
        
        # Validate the updated user data
        validation_errors = user.validate()
        if validation_errors:
            return jsonify({'errors': validation_errors}), 400
        
        # Commit the changes to the database
        db.session.commit()
        
        # Serialize the updated user using UserPublicSchema
        response_schema = UserPublicSchema()
        user_data = response_schema.dump(user)
        
        return jsonify({'user': user_data}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'An error occurred while updating the user', 'details': str(e)}), 500

# DELETE /users/<id> - Soft delete a specific user by ID
@user_bp.route('/<uuid:id>', methods=['DELETE'])
@require_auth
@require_role('admin')
def delete_user(id):
    try:
        # Find the user by ID
        user = User.query.filter_by(id=id, deleted_at=None).first()
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Perform soft delete
        user.delete(deleted_by=request.json.get('deleted_by') if request.is_json else None)
        
        # Commit the changes to the database
        db.session.commit()
        
        return jsonify({'message': 'User soft deleted successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'An error occurred while deleting the user', 'details': str(e)}), 500

# Additional routes for specific user operations

# GET /users/<id>/accounts - Get all accounts for a specific user
@user_bp.route('/<uuid:id>/accounts', methods=['GET'])
@require_auth
def get_user_accounts(id):
    try:
        user = User.query.filter_by(id=id, deleted_at=None).first()
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Serialize the user's accounts
        from app.schemas.account_schema import AccountSchema
        account_schema = AccountSchema(many=True)
        accounts_data = account_schema.dump(user.accounts)
        
        return jsonify({'accounts': accounts_data}), 200
    except Exception as e:
        return jsonify({'error': 'An error occurred while fetching user accounts', 'details': str(e)}), 500

# GET /users/search - Search users with advanced filters
@user_bp.route('/search', methods=['GET'])
@require_auth
def search_users():
    try:
        # Get pagination, filter, and sort parameters
        page, per_page = get_pagination_params()
        query, status, department, designation = get_filter_params()
        sort_by, sort_order = get_sort_params()
        
        # Use the search method from the User model
        users = User.search(
            query=query or None,
            status=status or None,
            department=department or None,
            designation=designation or None,
            include_deleted=False
        )
        
        # Apply sorting
        if hasattr(User, sort_by):
            reverse = sort_order == 'desc'
            users = sorted(users, key=lambda u: getattr(u, sort_by), reverse=reverse)
        
        # Apply pagination manually since we used the search method
        start = (page - 1) * per_page
        end = start + per_page
        paginated_users = users[start:end]
        
        # Serialize the users using UserPublicSchema
        user_schema = UserPublicSchema(many=True)
        users_data = user_schema.dump(paginated_users)
        
        # Prepare the response
        response_data = {
            'users': users_data,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': len(users),
                'pages': (len(users) + per_page - 1) // per_page,
                'has_next': end < len(users),
                'has_prev': start > 0
            }
        }
        
        return jsonify(response_data), 200
    except Exception as e:
        return jsonify({'error': 'An error occurred while searching users', 'details': str(e)}), 500