from flask import Blueprint, request, jsonify, current_app
from app.models.user import Role, Account, AccountRoles
from app.schemas.role_schema import RoleSchema, RoleCreateSchema, RoleUpdateSchema, RolePublicSchema
from app.extensions import db
import uuid
from datetime import datetime
from functools import wraps

# Create the role blueprint
role_bp = Blueprint('role', __name__, url_prefix='/roles')

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
    name = request.args.get('name', '', type=str)
    return query, name

# Helper function to get sort parameters
def get_sort_params():
    sort_by = request.args.get('sort_by', 'created_at', type=str)
    sort_order = request.args.get('sort_order', 'desc', type=str).lower()
    return sort_by, sort_order

# GET /roles - List all roles with pagination, filtering, and sorting
@role_bp.route('/', methods=['GET'])
@require_auth
def get_roles():
    try:
        # Get pagination, filter, and sort parameters
        page, per_page = get_pagination_params()
        query, name = get_filter_params()
        sort_by, sort_order = get_sort_params()
        
        # Build the query
        roles_query = Role.query
        
        # Apply filters
        if name:
            roles_query = roles_query.filter(Role.name.ilike(f'%{name}%'))
        
        if query:
            roles_query = roles_query.filter(Role.name.ilike(f'%{query}%') | Role.description.ilike(f'%{query}%'))
        
        # Exclude soft-deleted roles unless specifically requested
        roles_query = roles_query.filter(Role.deleted_at.is_(None))
        
        # Apply sorting
        if hasattr(Role, sort_by):
            column = getattr(Role, sort_by)
            if sort_order == 'asc':
                roles_query = roles_query.order_by(column.asc())
            else:
                roles_query = roles_query.order_by(column.desc())
        else:
            # Default sorting by created_at descending
            roles_query = roles_query.order_by(Role.created_at.desc())
        
        # Paginate the results
        paginated_roles = roles_query.paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        # Serialize the roles using RolePublicSchema
        role_schema = RolePublicSchema(many=True)
        roles_data = role_schema.dump(paginated_roles.items)
        
        # Prepare the response
        response_data = {
            'roles': roles_data,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': paginated_roles.total,
                'pages': paginated_roles.pages,
                'has_next': paginated_roles.has_next,
                'has_prev': paginated_roles.has_prev
            }
        }
        
        return jsonify(response_data), 200
    except Exception as e:
        return jsonify({'error': 'An error occurred while fetching roles', 'details': str(e)}), 500

# GET /roles/<id> - Get a specific role by ID
@role_bp.route('/<uuid:id>', methods=['GET'])
@require_auth
def get_role(id):
    try:
        role = Role.query.filter_by(id=id, deleted_at=None).first()
        
        if not role:
            return jsonify({'error': 'Role not found'}), 404
        
        # Serialize the role using RolePublicSchema
        role_schema = RolePublicSchema()
        role_data = role_schema.dump(role)
        
        return jsonify({'role': role_data}), 200
    except Exception as e:
        return jsonify({'error': 'An error occurred while fetching the role', 'details': str(e)}), 500

# POST /roles - Create a new role
@role_bp.route('/', methods=['POST'])
@require_auth
@require_role('admin')
def create_role():
    try:
        # Validate and deserialize the input data
        role_schema = RoleCreateSchema()
        role_data = role_schema.load(request.json)
        
        # Check if a role with the same name already exists
        existing_role = Role.query.filter_by(name=role_data['name'], deleted_at=None).first()
        if existing_role:
            return jsonify({'error': 'A role with this name already exists'}), 409
        
        # Create a new role instance
        role = Role()
        role.id = uuid.uuid4()
        role.name = role_data['name']
        role.description = role_data.get('description')
        role.created_by = role_data.get('created_by')
        
        # Add the role to the database
        db.session.add(role)
        db.session.commit()
        
        # Serialize the created role using RolePublicSchema
        response_schema = RolePublicSchema()
        role_data = response_schema.dump(role)
        
        return jsonify({'role': role_data}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'An error occurred while creating the role', 'details': str(e)}), 500

# PUT /roles/<id> - Update a specific role by ID
@role_bp.route('/<uuid:id>', methods=['PUT'])
@require_auth
@require_role('admin')
def update_role(id):
    try:
        # Validate and deserialize the input data
        role_schema = RoleUpdateSchema()
        role_data = role_schema.load(request.json)
        
        # Find the role by ID
        role = Role.query.filter_by(id=id, deleted_at=None).first()
        
        if not role:
            return jsonify({'error': 'Role not found'}), 404
        
        # Check if a role with the same name already exists (excluding the current role)
        if 'name' in role_data:
            existing_role = Role.query.filter_by(name=role_data['name'], deleted_at=None).filter(Role.id != id).first()
            if existing_role:
                return jsonify({'error': 'A role with this name already exists'}), 409
        
        # Update the role fields with provided data
        for field, value in role_data.items():
            if value is not None:
                setattr(role, field, value)
        
        # Update the updated_at timestamp and updated_by if provided
        role.updated_at = db.func.now()
        if 'updated_by' in role_data and role_data['updated_by']:
            role.updated_by = role_data['updated_by']
        
        # Commit the changes to the database
        db.session.commit()
        
        # Serialize the updated role using RolePublicSchema
        response_schema = RolePublicSchema()
        role_data = response_schema.dump(role)
        
        return jsonify({'role': role_data}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'An error occurred while updating the role', 'details': str(e)}), 500

# PATCH /roles/<id> - Partially update a specific role by ID
@role_bp.route('/<uuid:id>', methods=['PATCH'])
@require_auth
@require_role('admin')
def partial_update_role(id):
    try:
        # Validate and deserialize the input data
        role_schema = RoleUpdateSchema()
        role_data = role_schema.load(request.json)
        
        # Find the role by ID
        role = Role.query.filter_by(id=id, deleted_at=None).first()
        
        if not role:
            return jsonify({'error': 'Role not found'}), 404
        
        # Check if a role with the same name already exists (excluding the current role)
        if 'name' in role_data:
            existing_role = Role.query.filter_by(name=role_data['name'], deleted_at=None).filter(Role.id != id).first()
            if existing_role:
                return jsonify({'error': 'A role with this name already exists'}), 409
        
        # Update only the fields that were provided in the request
        for field, value in role_data.items():
            if value is not None:
                setattr(role, field, value)
        
        # Update the updated_at timestamp and updated_by if provided
        role.updated_at = db.func.now()
        if 'updated_by' in role_data and role_data['updated_by']:
            role.updated_by = role_data['updated_by']
        
        # Commit the changes to the database
        db.session.commit()
        
        # Serialize the updated role using RolePublicSchema
        response_schema = RolePublicSchema()
        role_data = response_schema.dump(role)
        
        return jsonify({'role': role_data}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'An error occurred while updating the role', 'details': str(e)}), 500

# DELETE /roles/<id> - Soft delete a specific role by ID
@role_bp.route('/<uuid:id>', methods=['DELETE'])
@require_auth
@require_role('admin')
def delete_role(id):
    try:
        # Find the role by ID
        role = Role.query.filter_by(id=id, deleted_at=None).first()
        
        if not role:
            return jsonify({'error': 'Role not found'}), 404
        
        # Perform soft delete
        role.deleted_by = request.json.get('deleted_by') if request.is_json else None
        role.deleted_at = db.func.now()
        role.updated_by = request.json.get('deleted_by') if request.is_json else None
        
        # Commit the changes to the database
        db.session.commit()
        
        return jsonify({'message': 'Role soft deleted successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'An error occurred while deleting the role', 'details': str(e)}), 500

# Additional routes for specific role operations

# GET /roles/<id>/accounts - Get all accounts assigned to a specific role
@role_bp.route('/<uuid:id>/accounts', methods=['GET'])
@require_auth
def get_role_accounts(id):
    try:
        role = Role.query.filter_by(id=id, deleted_at=None).first()
        
        if not role:
            return jsonify({'error': 'Role not found'}), 404
        
        # Get all accounts associated with this role
        accounts = role.accounts.filter(Account.deleted_at.is_(None)).all()
        
        # Serialize the accounts
        from app.schemas.account_schema import AccountSchema
        account_schema = AccountSchema(many=True)
        accounts_data = account_schema.dump(accounts)
        
        return jsonify({'accounts': accounts_data}), 200
    except Exception as e:
        return jsonify({'error': 'An error occurred while fetching role accounts', 'details': str(e)}), 500

# POST /roles/<id>/assign - Assign a role to an account
@role_bp.route('/<uuid:id>/assign', methods=['POST'])
@require_auth
@require_role('admin')
def assign_role_to_account(id):
    try:
        # Validate the request data
        data = request.json
        if not data or 'account_id' not in data:
            return jsonify({'error': 'Account ID is required'}), 400
        
        # Find the role by ID
        role = Role.query.filter_by(id=id, deleted_at=None).first()
        if not role:
            return jsonify({'error': 'Role not found'}), 404
        
        # Find the account by ID
        account = Account.query.filter_by(id=data['account_id'], deleted_at=None).first()
        if not account:
            return jsonify({'error': 'Account not found'}), 404
        
        # Check if the role is already assigned to the account
        if role in account.roles:
            return jsonify({'error': 'Role is already assigned to this account'}), 409
        
        # Assign the role to the account
        account.roles.append(role)
        db.session.commit()
        
        # Return success response
        return jsonify({'message': 'Role assigned to account successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'An error occurred while assigning the role to the account', 'details': str(e)}), 500

# POST /roles/<id>/unassign - Remove a role from an account
@role_bp.route('/<uuid:id>/unassign', methods=['POST'])
@require_auth
@require_role('admin')
def unassign_role_from_account(id):
    try:
        # Validate the request data
        data = request.json
        if not data or 'account_id' not in data:
            return jsonify({'error': 'Account ID is required'}), 400
        
        # Find the role by ID
        role = Role.query.filter_by(id=id, deleted_at=None).first()
        if not role:
            return jsonify({'error': 'Role not found'}), 404
        
        # Find the account by ID
        account = Account.query.filter_by(id=data['account_id'], deleted_at=None).first()
        if not account:
            return jsonify({'error': 'Account not found'}), 404
        
        # Check if the role is assigned to the account
        if role not in account.roles:
            return jsonify({'error': 'Role is not assigned to this account'}), 404
        
        # Remove the role from the account
        account.roles.remove(role)
        db.session.commit()
        
        # Return success response
        return jsonify({'message': 'Role removed from account successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'An error occurred while removing the role from the account', 'details': str(e)}), 500

# GET /roles/search - Search roles with advanced filters
@role_bp.route('/search', methods=['GET'])
@require_auth
def search_roles():
    try:
        # Get pagination, filter, and sort parameters
        page, per_page = get_pagination_params()
        query, name = get_filter_params()
        sort_by, sort_order = get_sort_params()
        
        # Build the query
        roles_query = Role.query
        
        # Apply filters
        if name:
            roles_query = roles_query.filter(Role.name.ilike(f'%{name}%'))
        
        if query:
            roles_query = roles_query.filter(Role.name.ilike(f'%{query}%') | Role.description.ilike(f'%{query}%'))
        
        # Exclude soft-deleted roles
        roles_query = roles_query.filter(Role.deleted_at.is_(None))
        
        # Apply sorting
        if hasattr(Role, sort_by):
            column = getattr(Role, sort_by)
            if sort_order == 'asc':
                roles_query = roles_query.order_by(column.asc())
            else:
                roles_query = roles_query.order_by(column.desc())
        else:
            # Default sorting by created_at descending
            roles_query = roles_query.order_by(Role.created_at.desc())
        
        # Paginate the results
        paginated_roles = roles_query.paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        # Serialize the roles using RolePublicSchema
        role_schema = RolePublicSchema(many=True)
        roles_data = role_schema.dump(paginated_roles.items)
        
        # Prepare the response
        response_data = {
            'roles': roles_data,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': paginated_roles.total,
                'pages': paginated_roles.pages,
                'has_next': paginated_roles.has_next,
                'has_prev': paginated_roles.has_prev
            }
        }
        
        return jsonify(response_data), 200
    except Exception as e:
        return jsonify({'error': 'An error occurred while searching roles', 'details': str(e)}), 500