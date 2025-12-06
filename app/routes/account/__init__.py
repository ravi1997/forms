from flask import Blueprint, request, jsonify, current_app
from app.models.user import Account, User, Role, StatusEnum
from app.schemas.account_schema import AccountSchema, AccountCreateSchema, AccountUpdateSchema, AccountPublicSchema
from app.extensions import db
import uuid
from datetime import datetime
from functools import wraps

# Create the account blueprint
account_bp = Blueprint('account', __name__, url_prefix='/accounts')

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
    username = request.args.get('username', '', type=str)
    status = request.args.get('status', '', type=str)
    user_id = request.args.get('user_id', '', type=str)
    return query, username, status, user_id

# Helper function to get sort parameters
def get_sort_params():
    sort_by = request.args.get('sort_by', 'created_at', type=str)
    sort_order = request.args.get('sort_order', 'desc', type=str).lower()
    return sort_by, sort_order

# GET /accounts - List all accounts with pagination, filtering, and sorting
@account_bp.route('/', methods=['GET'])
@require_auth
def get_accounts():
    try:
        # Get pagination, filter, and sort parameters
        page, per_page = get_pagination_params()
        query, username, status, user_id = get_filter_params()
        sort_by, sort_order = get_sort_params()
        
        # Build the query
        accounts_query = Account.query
        
        # Apply filters
        if username:
            accounts_query = accounts_query.filter(Account.username.ilike(f'%{username}%'))
        
        if status:
            try:
                status_enum = StatusEnum(status.upper())
                accounts_query = accounts_query.filter(Account.status == status_enum)
            except ValueError:
                return jsonify({'error': f'Invalid status value: {status}'}), 400
        
        if user_id:
            try:
                user_uuid = uuid.UUID(user_id)
                accounts_query = accounts_query.filter(Account.user_id == user_uuid)
            except ValueError:
                return jsonify({'error': f'Invalid user ID: {user_id}'}), 400
        
        if query:
            accounts_query = accounts_query.filter(Account.username.ilike(f'%{query}%'))
        
        # Exclude soft-deleted accounts unless specifically requested
        accounts_query = accounts_query.filter(Account.deleted_at.is_(None))
        
        # Apply sorting
        if hasattr(Account, sort_by):
            column = getattr(Account, sort_by)
            if sort_order == 'asc':
                accounts_query = accounts_query.order_by(column.asc())
            else:
                accounts_query = accounts_query.order_by(column.desc())
        else:
            # Default sorting by created_at descending
            accounts_query = accounts_query.order_by(Account.created_at.desc())
        
        # Paginate the results
        paginated_accounts = accounts_query.paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        # Serialize the accounts using AccountPublicSchema
        account_schema = AccountPublicSchema(many=True)
        accounts_data = account_schema.dump(paginated_accounts.items)
        
        # Prepare the response
        response_data = {
            'accounts': accounts_data,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': paginated_accounts.total,
                'pages': paginated_accounts.pages,
                'has_next': paginated_accounts.has_next,
                'has_prev': paginated_accounts.has_prev
            }
        }
        
        return jsonify(response_data), 200
    except Exception as e:
        return jsonify({'error': 'An error occurred while fetching accounts', 'details': str(e)}), 500

# GET /accounts/<id> - Get a specific account by ID
@account_bp.route('/<uuid:id>', methods=['GET'])
@require_auth
def get_account(id):
    try:
        account = Account.query.filter_by(id=id, deleted_at=None).first()
        
        if not account:
            return jsonify({'error': 'Account not found'}), 404
        
        # Serialize the account using AccountPublicSchema
        account_schema = AccountPublicSchema()
        account_data = account_schema.dump(account)
        
        return jsonify({'account': account_data}), 200
    except Exception as e:
        return jsonify({'error': 'An error occurred while fetching the account', 'details': str(e)}), 500

# POST /accounts - Create a new account
@account_bp.route('/', methods=['POST'])
@require_auth
@require_role('admin')
def create_account():
    try:
        # Validate and deserialize the input data
        account_schema = AccountCreateSchema()
        account_data = account_schema.load(request.json)
        
        # Check if a user with the provided user_id exists
        user = User.query.filter_by(id=account_data['user_id'], deleted_at=None).first()
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Check if an account with the same username already exists
        existing_account = Account.query.filter_by(username=account_data['username'], deleted_at=None).first()
        if existing_account:
            return jsonify({'error': 'An account with this username already exists'}), 409
        
        # Create a new account instance
        account = Account()
        account.id = uuid.uuid4()
        account.user_id = account_data['user_id']
        account.username = account_data['username']
        
        # Hash and set the password
        from app.extensions import bcrypt
        account.set_password(account_data['password'])
        
        account.password_reset_token = account_data.get('password_reset_token')
        account.password_reset_token_expires_at = account_data.get('password_reset_token_expires_at')
        account.otp = account_data.get('otp')
        account.otp_created_at = account_data.get('otp_created_at')
        account.status = account_data.get('status', StatusEnum.INACTIVE)
        account.updated_by = account_data.get('updated_by')
        account.deleted_by = account_data.get('deleted_by')
        account.deleted_at = account_data.get('deleted_at')
        
        # Add the account to the database
        db.session.add(account)
        db.session.commit()
        
        # Serialize the created account using AccountPublicSchema
        response_schema = AccountPublicSchema()
        account_data = response_schema.dump(account)
        
        return jsonify({'account': account_data}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'An error occurred while creating the account', 'details': str(e)}), 500

# PUT /accounts/<id> - Update a specific account by ID
@account_bp.route('/<uuid:id>', methods=['PUT'])
@require_auth
@require_role('admin')
def update_account(id):
    try:
        # Validate and deserialize the input data
        account_schema = AccountUpdateSchema()
        account_data = account_schema.load(request.json)
        
        # Find the account by ID
        account = Account.query.filter_by(id=id, deleted_at=None).first()
        
        if not account:
            return jsonify({'error': 'Account not found'}), 404
        
        # Check if a user with the provided user_id exists (if user_id is being updated)
        if 'user_id' in account_data and account_data['user_id']:
            user = User.query.filter_by(id=account_data['user_id'], deleted_at=None).first()
            if not user:
                return jsonify({'error': 'User not found'}), 404
        
        # Check if username is being updated and if it already exists for another account
        if 'username' in account_data:
            existing_account = Account.query.filter_by(username=account_data['username'], deleted_at=None).filter(Account.id != id).first()
            if existing_account:
                return jsonify({'error': 'An account with this username already exists'}), 409
        
        # Update the account fields with provided data
        for field, value in account_data.items():
            if value is not None:
                # Handle password separately as it needs to be hashed
                if field == 'password':
                    from app.extensions import bcrypt
                    account.set_password(value)
                else:
                    setattr(account, field, value)
        
        # Update the updated_at timestamp and updated_by if provided
        account.updated_at = db.func.now()
        if 'updated_by' in account_data and account_data['updated_by']:
            account.updated_by = account_data['updated_by']
        
        # Commit the changes to the database
        db.session.commit()
        
        # Serialize the updated account using AccountPublicSchema
        response_schema = AccountPublicSchema()
        account_data = response_schema.dump(account)
        
        return jsonify({'account': account_data}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'An error occurred while updating the account', 'details': str(e)}), 500

# PATCH /accounts/<id> - Partially update a specific account by ID
@account_bp.route('/<uuid:id>', methods=['PATCH'])
@require_auth
@require_role('admin')
def partial_update_account(id):
    try:
        # Validate and deserialize the input data
        account_schema = AccountUpdateSchema()
        account_data = account_schema.load(request.json)
        
        # Find the account by ID
        account = Account.query.filter_by(id=id, deleted_at=None).first()
        
        if not account:
            return jsonify({'error': 'Account not found'}), 404
        
        # Check if a user with the provided user_id exists (if user_id is being updated)
        if 'user_id' in account_data and account_data['user_id']:
            user = User.query.filter_by(id=account_data['user_id'], deleted_at=None).first()
            if not user:
                return jsonify({'error': 'User not found'}), 404
        
        # Check if username is being updated and if it already exists for another account
        if 'username' in account_data:
            existing_account = Account.query.filter_by(username=account_data['username'], deleted_at=None).filter(Account.id != id).first()
            if existing_account:
                return jsonify({'error': 'An account with this username already exists'}), 409
        
        # Update only the fields that were provided in the request
        for field, value in account_data.items():
            if value is not None:
                # Handle password separately as it needs to be hashed
                if field == 'password':
                    from app.extensions import bcrypt
                    account.set_password(value)
                else:
                    setattr(account, field, value)
        
        # Update the updated_at timestamp and updated_by if provided
        account.updated_at = db.func.now()
        if 'updated_by' in account_data and account_data['updated_by']:
            account.updated_by = account_data['updated_by']
        
        # Commit the changes to the database
        db.session.commit()
        
        # Serialize the updated account using AccountPublicSchema
        response_schema = AccountPublicSchema()
        account_data = response_schema.dump(account)
        
        return jsonify({'account': account_data}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'An error occurred while updating the account', 'details': str(e)}), 500

# DELETE /accounts/<id> - Soft delete a specific account by ID
@account_bp.route('/<uuid:id>', methods=['DELETE'])
@require_auth
@require_role('admin')
def delete_account(id):
    try:
        # Find the account by ID
        account = Account.query.filter_by(id=id, deleted_at=None).first()
        
        if not account:
            return jsonify({'error': 'Account not found'}), 404
        
        # Perform soft delete
        account.deleted_by = request.json.get('deleted_by') if request.is_json else None
        account.deleted_at = db.func.now()
        account.updated_by = request.json.get('deleted_by') if request.is_json else None
        # Set status to DELETED as well
        account.status = StatusEnum.DELETED
        
        # Commit the changes to the database
        db.session.commit()
        
        return jsonify({'message': 'Account soft deleted successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'An error occurred while deleting the account', 'details': str(e)}), 500

# Additional routes for specific account operations

# GET /accounts/<id>/user - Get the user associated with an account
@account_bp.route('/<uuid:id>/user', methods=['GET'])
@require_auth
def get_account_user(id):
    try:
        account = Account.query.filter_by(id=id, deleted_at=None).first()
        
        if not account:
            return jsonify({'error': 'Account not found'}), 404
        
        # Serialize the user using User schema
        from app.schemas.user_schema import UserPublicSchema
        user_schema = UserPublicSchema()
        user_data = user_schema.dump(account.user)
        
        return jsonify({'user': user_data}), 200
    except Exception as e:
        return jsonify({'error': 'An error occurred while fetching the user', 'details': str(e)}), 500

# GET /accounts/<id>/roles - Get all roles assigned to a specific account
@account_bp.route('/<uuid:id>/roles', methods=['GET'])
@require_auth
def get_account_roles(id):
    try:
        account = Account.query.filter_by(id=id, deleted_at=None).first()
        
        if not account:
            return jsonify({'error': 'Account not found'}), 404
        
        # Serialize the roles
        from app.schemas.role_schema import RolePublicSchema
        role_schema = RolePublicSchema(many=True)
        roles_data = role_schema.dump(account.roles)
        
        return jsonify({'roles': roles_data}), 200
    except Exception as e:
        return jsonify({'error': 'An error occurred while fetching account roles', 'details': str(e)}), 500

# POST /accounts/<id>/assign-role - Assign a role to an account
@account_bp.route('/<uuid:id>/assign-role', methods=['POST'])
@require_auth
@require_role('admin')
def assign_role_to_account(id):
    try:
        # Validate the request data
        data = request.json
        if not data or 'role_id' not in data:
            return jsonify({'error': 'Role ID is required'}), 400
        
        # Find the account by ID
        account = Account.query.filter_by(id=id, deleted_at=None).first()
        if not account:
            return jsonify({'error': 'Account not found'}), 404
        
        # Find the role by ID
        role = Role.query.filter_by(id=data['role_id'], deleted_at=None).first()
        if not role:
            return jsonify({'error': 'Role not found'}), 404
        
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

# POST /accounts/<id>/remove-role - Remove a role from an account
@account_bp.route('/<uuid:id>/remove-role', methods=['POST'])
@require_auth
@require_role('admin')
def remove_role_from_account(id):
    try:
        # Validate the request data
        data = request.json
        if not data or 'role_id' not in data:
            return jsonify({'error': 'Role ID is required'}), 400
        
        # Find the account by ID
        account = Account.query.filter_by(id=id, deleted_at=None).first()
        if not account:
            return jsonify({'error': 'Account not found'}), 404
        
        # Find the role by ID
        role = Role.query.filter_by(id=data['role_id'], deleted_at=None).first()
        if not role:
            return jsonify({'error': 'Role not found'}), 404
        
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

# POST /accounts/<id>/change-password - Change password for an account
@account_bp.route('/<uuid:id>/change-password', methods=['POST'])
@require_auth
def change_password(id):
    try:
        # Validate the request data
        data = request.json
        if not data or 'new_password' not in data:
            return jsonify({'error': 'New password is required'}), 400
        
        # Find the account by ID
        account = Account.query.filter_by(id=id, deleted_at=None).first()
        if not account:
            return jsonify({'error': 'Account not found'}), 404
        
        # Validate new password
        new_password = data['new_password']
        if len(new_password) < 8:
            return jsonify({'error': 'Password must be at least 8 characters long'}), 400
        
        # Update the password
        from app.extensions import bcrypt
        account.set_password(new_password)
        account.updated_at = db.func.now()
        account.updated_by = data.get('updated_by')
        
        # Commit the changes to the database
        db.session.commit()
        
        return jsonify({'message': 'Password changed successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'An error occurred while changing the password', 'details': str(e)}), 500

# POST /accounts/<id>/reset-password - Reset password for an account
@account_bp.route('/<uuid:id>/reset-password', methods=['POST'])
@require_auth
@require_role('admin')
def reset_password(id):
    try:
        # Validate the request data
        data = request.json
        if not data or 'new_password' not in data:
            return jsonify({'error': 'New password is required'}), 400
        
        # Find the account by ID
        account = Account.query.filter_by(id=id, deleted_at=None).first()
        if not account:
            return jsonify({'error': 'Account not found'}), 404
        
        # Validate new password
        new_password = data['new_password']
        if len(new_password) < 8:
            return jsonify({'error': 'Password must be at least 8 characters long'}), 400
        
        # Update the password
        from app.extensions import bcrypt
        account.set_password(new_password)
        account.updated_at = db.func.now()
        account.updated_by = data.get('updated_by')
        
        # Commit the changes to the database
        db.session.commit()
        
        return jsonify({'message': 'Password reset successfully'}), 20
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'An error occurred while resetting the password', 'details': str(e)}), 500

# GET /accounts/search - Search accounts with advanced filters
@account_bp.route('/search', methods=['GET'])
@require_auth
def search_accounts():
    try:
        # Get pagination, filter, and sort parameters
        page, per_page = get_pagination_params()
        query, username, status, user_id = get_filter_params()
        sort_by, sort_order = get_sort_params()
        
        # Build the query
        accounts_query = Account.query
        
        # Apply filters
        if username:
            accounts_query = accounts_query.filter(Account.username.ilike(f'%{username}%'))
        
        if status:
            try:
                status_enum = StatusEnum(status.upper())
                accounts_query = accounts_query.filter(Account.status == status_enum)
            except ValueError:
                return jsonify({'error': f'Invalid status value: {status}'}), 400
        
        if user_id:
            try:
                user_uuid = uuid.UUID(user_id)
                accounts_query = accounts_query.filter(Account.user_id == user_uuid)
            except ValueError:
                return jsonify({'error': f'Invalid user ID: {user_id}'}), 400
        
        if query:
            accounts_query = accounts_query.filter(Account.username.ilike(f'%{query}%'))
        
        # Exclude soft-deleted accounts
        accounts_query = accounts_query.filter(Account.deleted_at.is_(None))
        
        # Apply sorting
        if hasattr(Account, sort_by):
            column = getattr(Account, sort_by)
            if sort_order == 'asc':
                accounts_query = accounts_query.order_by(column.asc())
            else:
                accounts_query = accounts_query.order_by(column.desc())
        else:
            # Default sorting by created_at descending
            accounts_query = accounts_query.order_by(Account.created_at.desc())
        
        # Paginate the results
        paginated_accounts = accounts_query.paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        # Serialize the accounts using AccountPublicSchema
        account_schema = AccountPublicSchema(many=True)
        accounts_data = account_schema.dump(paginated_accounts.items)
        
        # Prepare the response
        response_data = {
            'accounts': accounts_data,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': paginated_accounts.total,
                'pages': paginated_accounts.pages,
                'has_next': paginated_accounts.has_next,
                'has_prev': paginated_accounts.has_prev
            }
        }
        
        return jsonify(response_data), 200
    except Exception as e:
        return jsonify({'error': 'An error occurred while searching accounts', 'details': str(e)}), 500

# GET /accounts/<id>/status - Get the status of an account
@account_bp.route('/<uuid:id>/status', methods=['GET'])
@require_auth
def get_account_status(id):
    try:
        account = Account.query.filter_by(id=id, deleted_at=None).first()
        
        if not account:
            return jsonify({'error': 'Account not found'}), 404
        
        return jsonify({
            'status': account.status.value if account.status else None,
            'is_active': account.status == StatusEnum.ACTIVE,
            'is_inactive': account.status == StatusEnum.INACTIVE,
            'is_suspended': account.status == StatusEnum.SUSPENDED,
            'is_deleted': account.status == StatusEnum.DELETED
        }), 200
    except Exception as e:
        return jsonify({'error': 'An error occurred while fetching account status', 'details': str(e)}), 500

# PUT /accounts/<id>/status - Update the status of an account
@account_bp.route('/<uuid:id>/status', methods=['PUT'])
@require_auth
@require_role('admin')
def update_account_status(id):
    try:
        # Validate the request data
        data = request.json
        if not data or 'status' not in data:
            return jsonify({'error': 'Status is required'}), 400
        
        # Find the account by ID
        account = Account.query.filter_by(id=id, deleted_at=None).first()
        if not account:
            return jsonify({'error': 'Account not found'}), 404
        
        # Validate the status
        try:
            new_status = StatusEnum(data['status'].upper())
        except ValueError:
            return jsonify({'error': f'Invalid status value: {data["status"]}'}), 400
        
        # Update the status
        account.status = new_status
        account.updated_at = db.func.now()
        account.updated_by = data.get('updated_by')
        
        # Commit the changes to the database
        db.session.commit()
        
        return jsonify({
            'message': 'Account status updated successfully',
            'status': account.status.value
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'An error occurred while updating account status', 'details': str(e)}), 500