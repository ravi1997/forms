from flask import Blueprint, request, jsonify, current_app
from app.models.user import User, Role, Account, StatusEnum
from app.schemas.user_schema import UserSchema, UserPublicSchema
from app.schemas.role_schema import RoleSchema, RolePublicSchema
from app.schemas.account_schema import AccountSchema, AccountPublicSchema
from app.extensions import db
import uuid
from datetime import datetime
from functools import wraps

# Create the admin blueprint
admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

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

def require_admin(f):
    """Decorator to require admin-level permissions"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # In a real application, you would check if the user has admin permissions
        # For now, we'll just continue with the request
        # You would typically check if the user has admin role/permission from the token
        return f(*args, **kwargs)
    return decorated_function

def require_superadmin(f):
    """Decorator to require superadmin-level permissions"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # In a real application, you would check if the user has superadmin permissions
        # For now, we'll just continue with the request
        # You would typically check if the user has superadmin role/permission from the token
        return f(*args, **kwargs)
    return decorated_function

# Helper function to get pagination parameters
def get_pagination_params():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    # Limit per_page to prevent abuse
    per_page = min(per_page, 100)
    return page, per_page

# Helper function to get filter parameters for advanced filtering
def get_user_filter_params():
    query = request.args.get('query', '', type=str)
    status = request.args.get('status', '', type=str)
    department = request.args.get('department', '', type=str)
    designation = request.args.get('designation', '', type=str)
    created_after = request.args.get('created_after', '', type=str)
    created_before = request.args.get('created_before', '', type=str)
    age_min = request.args.get('age_min', '', type=str)
    age_max = request.args.get('age_max', '', type=str)
    include_deleted = request.args.get('include_deleted', 'false', type=str).lower() == 'true'
    return query, status, department, designation, created_after, created_before, age_min, age_max, include_deleted

def get_role_filter_params():
    query = request.args.get('query', '', type=str)
    name = request.args.get('name', '', type=str)
    include_deleted = request.args.get('include_deleted', 'false', type=str).lower() == 'true'
    return query, name, include_deleted

def get_account_filter_params():
    query = request.args.get('query', '', type=str)
    username = request.args.get('username', '', type=str)
    status = request.args.get('status', '', type=str)
    user_id = request.args.get('user_id', '', type=str)
    created_after = request.args.get('created_after', '', type=str)
    created_before = request.args.get('created_before', '', type=str)
    include_deleted = request.args.get('include_deleted', 'false', type=str).lower() == 'true'
    return query, username, status, user_id, created_after, created_before, include_deleted

# Helper function to get sort parameters
def get_sort_params():
    sort_by = request.args.get('sort_by', 'created_at', type=str)
    sort_order = request.args.get('sort_order', 'desc', type=str).lower()
    return sort_by, sort_order

# GET /admin/users - List all users with administrative capabilities (with advanced filtering)
@admin_bp.route('/users', methods=['GET'])
@require_auth
@require_admin
def get_admin_users():
    try:
        # Get pagination, filter, and sort parameters
        page, per_page = get_pagination_params()
        query, status, department, designation, created_after, created_before, age_min, age_max, include_deleted = get_user_filter_params()
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
        
        # Filter by creation date range
        if created_after:
            try:
                created_after_date = datetime.fromisoformat(created_after)
                users_query = users_query.filter(User.created_at >= created_after_date)
            except ValueError:
                return jsonify({'error': f'Invalid date format for created_after: {created_after}'}), 400
        
        if created_before:
            try:
                created_before_date = datetime.fromisoformat(created_before)
                users_query = users_query.filter(User.created_at <= created_before_date)
            except ValueError:
                return jsonify({'error': f'Invalid date format for created_before: {created_before}'}), 400
        
        # Filter by age range
        if age_min or age_max:
            try:
                current_users = users_query.all()
                age_filtered_users = []
                for user in current_users:
                    age = user.age()
                    if age is not None:
                        if age_min and age < int(age_min):
                            continue
                        if age_max and age > int(age_max):
                            continue
                        age_filtered_users.append(user)
                
                # Since we can't filter by age in the query, we'll paginate the filtered list manually
                start = (page - 1) * per_page
                end = start + per_page
                paginated_users = age_filtered_users[start:end]
                
                # Serialize the users using UserPublicSchema
                user_schema = UserPublicSchema(many=True)
                users_data = user_schema.dump(paginated_users)
                
                # Prepare the response
                response_data = {
                    'users': users_data,
                    'pagination': {
                        'page': page,
                        'per_page': per_page,
                        'total': len(age_filtered_users),
                        'pages': (len(age_filtered_users) + per_page - 1) // per_page,
                        'has_next': end < len(age_filtered_users),
                        'has_prev': start > 0
                    }
                }
                
                return jsonify(response_data), 200
            except ValueError:
                return jsonify({'error': 'Invalid age range values'}), 400
        
        # Exclude soft-deleted users unless specifically requested
        if not include_deleted:
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

# GET /admin/roles - List all roles with administrative capabilities
@admin_bp.route('/roles', methods=['GET'])
@require_auth
@require_admin
def get_admin_roles():
    try:
        # Get pagination, filter, and sort parameters
        page, per_page = get_pagination_params()
        query, name, include_deleted = get_role_filter_params()
        sort_by, sort_order = get_sort_params()
        
        # Build the query
        roles_query = Role.query
        
        # Apply filters
        if name:
            roles_query = roles_query.filter(Role.name.ilike(f'%{name}%'))
        
        if query:
            roles_query = roles_query.filter(Role.name.ilike(f'%{query}%') | Role.description.ilike(f'%{query}%'))
        
        # Exclude soft-deleted roles unless specifically requested
        if not include_deleted:
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

# GET /admin/accounts - List all accounts with administrative capabilities
@admin_bp.route('/accounts', methods=['GET'])
@require_auth
@require_admin
def get_admin_accounts():
    try:
        # Get pagination, filter, and sort parameters
        page, per_page = get_pagination_params()
        query, username, status, user_id, created_after, created_before, include_deleted = get_account_filter_params()
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
        
        # Filter by creation date range
        if created_after:
            try:
                created_after_date = datetime.fromisoformat(created_after)
                accounts_query = accounts_query.filter(Account.created_at >= created_after_date)
            except ValueError:
                return jsonify({'error': f'Invalid date format for created_after: {created_after}'}), 400
        
        if created_before:
            try:
                created_before_date = datetime.fromisoformat(created_before)
                accounts_query = accounts_query.filter(Account.created_at <= created_before_date)
            except ValueError:
                return jsonify({'error': f'Invalid date format for created_before: {created_before}'}), 400
        
        # Exclude soft-deleted accounts unless specifically requested
        if not include_deleted:
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

# PUT /admin/users/<id>/status - Update user status (activate, deactivate, suspend, delete)
@admin_bp.route('/users/<uuid:id>/status', methods=['PUT'])
@require_auth
@require_admin
def update_user_status(id):
    try:
        # Validate the request data
        data = request.json
        if not data or 'status' not in data:
            return jsonify({'error': 'Status is required'}), 400
        
        # Find the user by ID
        user = User.query.filter_by(id=id).first() # Include deleted users
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Validate the status
        try:
            new_status = StatusEnum(data['status'].upper())
        except ValueError:
            return jsonify({'error': f'Invalid status value: {data["status"]}'}), 400
        
        # Update the status based on the new status
        updated_by = data.get('updated_by')
        if new_status == StatusEnum.ACTIVE:
            user.activate(updated_by)
        elif new_status == StatusEnum.INACTIVE:
            user.deactivate(updated_by)
        elif new_status == StatusEnum.SUSPENDED:
            user.suspend(updated_by)
        elif new_status == StatusEnum.DELETED:
            user.delete(updated_by)
        
        # Commit the changes to the database
        db.session.commit()
        
        return jsonify({
            'message': 'User status updated successfully',
            'status': user.status.value
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'An error occurred while updating user status', 'details': str(e)}), 500

# PUT /admin/accounts/<id>/status - Update account status (activate, deactivate, suspend, delete)
@admin_bp.route('/accounts/<uuid:id>/status', methods=['PUT'])
@require_auth
@require_admin
def update_account_status(id):
    try:
        # Validate the request data
        data = request.json
        if not data or 'status' not in data:
            return jsonify({'error': 'Status is required'}), 400
        
        # Find the account by ID
        account = Account.query.filter_by(id=id).first() # Include deleted accounts
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
        
        # If the status is DELETED, also set deleted_at timestamp
        if new_status == StatusEnum.DELETED:
            account.deleted_at = db.func.now()
            account.deleted_by = data.get('updated_by')
        
        # Commit the changes to the database
        db.session.commit()
        
        return jsonify({
            'message': 'Account status updated successfully',
            'status': account.status.value
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'An error occurred while updating account status', 'details': str(e)}), 500

# POST /admin/users/<id>/restore - Restore a deleted user
@admin_bp.route('/users/<uuid:id>/restore', methods=['POST'])
@require_auth
@require_admin
def restore_user(id):
    try:
        # Find the user by ID (including soft-deleted users)
        user = User.query.filter_by(id=id).first()
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Check if the user is actually deleted
        if user.status != StatusEnum.DELETED or user.deleted_at is None:
            return jsonify({'error': 'User is not in deleted status'}), 400
        
        # Restore the user
        restored_by = request.json.get('restored_by') if request.is_json else None
        user.restore(restored_by)
        
        # Commit the changes to the database
        db.session.commit()
        
        # Serialize the restored user using UserPublicSchema
        user_schema = UserPublicSchema()
        user_data = user_schema.dump(user)
        
        return jsonify({
            'message': 'User restored successfully',
            'user': user_data
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'An error occurred while restoring the user', 'details': str(e)}), 500

# POST /admin/accounts/<id>/restore - Restore a deleted account
@admin_bp.route('/accounts/<uuid:id>/restore', methods=['POST'])
@require_auth
@require_admin
def restore_account(id):
    try:
        # Find the account by ID (including soft-deleted accounts)
        account = Account.query.filter_by(id=id).first()
        if not account:
            return jsonify({'error': 'Account not found'}), 404
        
        # Check if the account is actually deleted
        if account.status != StatusEnum.DELETED or account.deleted_at is None:
            return jsonify({'error': 'Account is not in deleted status'}), 400
        
        # Restore the account
        account.status = StatusEnum.INACTIVE  # Restore to inactive by default
        account.deleted_by = None
        account.deleted_at = None
        account.updated_at = db.func.now()
        account.updated_by = request.json.get('restored_by') if request.is_json else None
        
        # Commit the changes to the database
        db.session.commit()
        
        # Serialize the restored account using AccountPublicSchema
        account_schema = AccountPublicSchema()
        account_data = account_schema.dump(account)
        
        return jsonify({
            'message': 'Account restored successfully',
            'account': account_data
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'An error occurred while restoring the account', 'details': str(e)}), 500

# Additional admin-specific routes for bulk operations and system management

# POST /admin/users/bulk-update-status - Bulk update user status
@admin_bp.route('/users/bulk-update-status', methods=['POST'])
@require_auth
@require_admin
def bulk_update_user_status():
    try:
        # Validate the request data
        data = request.json
        if not data or 'user_ids' not in data or 'status' not in data:
            return jsonify({'error': 'User IDs and status are required'}), 400
        
        user_ids = data['user_ids']
        if not isinstance(user_ids, list) or not user_ids:
            return jsonify({'error': 'User IDs must be a non-empty list'}), 400
        
        # Validate the status
        try:
            new_status = StatusEnum(data['status'].upper())
        except ValueError:
            return jsonify({'error': f'Invalid status value: {data["status"]}'}), 400
        
        # Validate that all user IDs are valid UUIDs
        validated_user_ids = []
        for user_id_str in user_ids:
            try:
                user_id = uuid.UUID(user_id_str)
                validated_user_ids.append(user_id)
            except ValueError:
                return jsonify({'error': f'Invalid user ID: {user_id_str}'}), 400
        
        # Perform bulk update
        updated_count = User.bulk_update_status(validated_user_ids, new_status, data.get('updated_by'))
        
        return jsonify({
            'message': f'Bulk update completed: {updated_count} users updated',
            'updated_count': updated_count
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'An error occurred during bulk update', 'details': str(e)}), 500

# POST /admin/users/bulk-delete - Bulk delete users
@admin_bp.route('/users/bulk-delete', methods=['POST'])
@require_auth
@require_admin
def bulk_delete_users():
    try:
        # Validate the request data
        data = request.json
        if not data or 'user_ids' not in data:
            return jsonify({'error': 'User IDs are required'}), 400
        
        user_ids = data['user_ids']
        if not isinstance(user_ids, list) or not user_ids:
            return jsonify({'error': 'User IDs must be a non-empty list'}), 400
        
        # Validate that all user IDs are valid UUIDs
        validated_user_ids = []
        for user_id_str in user_ids:
            try:
                user_id = uuid.UUID(user_id_str)
                validated_user_ids.append(user_id)
            except ValueError:
                return jsonify({'error': f'Invalid user ID: {user_id_str}'}), 400
        
        # Perform bulk delete
        deleted_count = User.bulk_delete(validated_user_ids, data.get('deleted_by'))
        
        return jsonify({
            'message': f'Bulk delete completed: {deleted_count} users deleted',
            'deleted_count': deleted_count
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'An error occurred during bulk delete', 'details': str(e)}), 500

# POST /admin/users/bulk-restore - Bulk restore users
@admin_bp.route('/users/bulk-restore', methods=['POST'])
@require_auth
@require_admin
def bulk_restore_users():
    try:
        # Validate the request data
        data = request.json
        if not data or 'user_ids' not in data:
            return jsonify({'error': 'User IDs are required'}), 400
        
        user_ids = data['user_ids']
        if not isinstance(user_ids, list) or not user_ids:
            return jsonify({'error': 'User IDs must be a non-empty list'}), 400
        
        # Validate that all user IDs are valid UUIDs
        validated_user_ids = []
        for user_id_str in user_ids:
            try:
                user_id = uuid.UUID(user_id_str)
                validated_user_ids.append(user_id)
            except ValueError:
                return jsonify({'error': f'Invalid user ID: {user_id_str}'}), 400
        
        # Perform bulk restore
        restored_count = User.bulk_restore(validated_user_ids, data.get('restored_by'))
        
        return jsonify({
            'message': f'Bulk restore completed: {restored_count} users restored',
            'restored_count': restored_count
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'An error occurred during bulk restore', 'details': str(e)}), 500

# GET /admin/system-stats - Get system statistics
@admin_bp.route('/system-stats', methods=['GET'])
@require_auth
@require_admin
def get_system_stats():
    try:
        # Get counts for users, roles, and accounts
        total_users = User.query.count()
        active_users = User.query.filter_by(status=StatusEnum.ACTIVE).count()
        inactive_users = User.query.filter_by(status=StatusEnum.INACTIVE).count()
        suspended_users = User.query.filter_by(status=StatusEnum.SUSPENDED).count()
        deleted_users = User.query.filter_by(status=StatusEnum.DELETED).count()
        
        total_roles = Role.query.count()
        active_roles = Role.query.filter_by(deleted_at=None).count()
        deleted_roles = Role.query.filter_by(deleted_at=None).count()
        
        total_accounts = Account.query.count()
        active_accounts = Account.query.filter_by(status=StatusEnum.ACTIVE).count()
        inactive_accounts = Account.query.filter_by(status=StatusEnum.INACTIVE).count()
        suspended_accounts = Account.query.filter_by(status=StatusEnum.SUSPENDED).count()
        deleted_accounts = Account.query.filter_by(status=StatusEnum.DELETED).count()
        
        stats = {
            'users': {
                'total': total_users,
                'active': active_users,
                'inactive': inactive_users,
                'suspended': suspended_users,
                'deleted': deleted_users
            },
            'roles': {
                'total': total_roles,
                'active': active_roles,
                'deleted': deleted_roles
            },
            'accounts': {
                'total': total_accounts,
                'active': active_accounts,
                'inactive': inactive_accounts,
                'suspended': suspended_accounts,
                'deleted': deleted_accounts
            }
        }
        
        return jsonify({'stats': stats}), 200
    except Exception as e:
        return jsonify({'error': 'An error occurred while fetching system stats', 'details': str(e)}), 500

# POST /admin/users/<id>/validate - Validate user data integrity
@admin_bp.route('/users/<uuid:id>/validate', methods=['POST'])
@require_auth
@require_admin
def validate_user(id):
    try:
        # Find the user by ID
        user = User.query.filter_by(id=id, deleted_at=None).first()
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Check data integrity
        integrity_report = user.check_data_integrity()
        
        return jsonify({'integrity_report': integrity_report}), 200
    except Exception as e:
        return jsonify({'error': 'An error occurred while validating user data', 'details': str(e)}), 500

# POST /admin/users/<id>/permissions - Get user permissions across all accounts
@admin_bp.route('/users/<uuid:id>/permissions', methods=['GET'])
@require_auth
@require_admin
def get_user_permissions(id):
    try:
        # Find the user by ID
        user = User.query.filter_by(id=id, deleted_at=None).first()
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Get permissions/roles for each account
        permissions = user.get_permissions_by_account()
        
        return jsonify({'permissions': permissions}), 200
    except Exception as e:
        return jsonify({'error': 'An error occurred while fetching user permissions', 'details': str(e)}), 500

# GET /admin/users/search - Advanced user search with all filters
@admin_bp.route('/users/search', methods=['GET'])
@require_auth
@require_admin
def search_admin_users():
    try:
        # Get pagination, filter, and sort parameters
        page, per_page = get_pagination_params()
        query, status, department, designation, created_after, created_before, age_min, age_max, include_deleted = get_user_filter_params()
        sort_by, sort_order = get_sort_params()
        
        # Use the search method from the User model
        users = User.search(
            query=query or None,
            status=status or None,
            department=department or None,
            designation=designation or None,
            include_deleted=include_deleted
        )
        
        # Filter by creation date range if provided
        if created_after or created_before:
            filtered_users = []
            for user in users:
                should_include = True
                if created_after:
                    try:
                        created_after_date = datetime.fromisoformat(created_after)
                        if user.created_at < created_after_date:
                            should_include = False
                    except ValueError:
                        return jsonify({'error': f'Invalid date format for created_after: {created_after}'}), 400
                
                if created_before:
                    try:
                        created_before_date = datetime.fromisoformat(created_before)
                        if user.created_at > created_before_date:
                            should_include = False
                    except ValueError:
                        return jsonify({'error': f'Invalid date format for created_before: {created_before}'}), 400
                
                if should_include:
                    filtered_users.append(user)
            users = filtered_users
        
        # Apply age filtering if specified
        if age_min or age_max:
            filtered_users = []
            for user in users:
                age = user.age()
                if age is not None:
                    if age_min and age < int(age_min):
                        continue
                    if age_max and age > int(age_max):
                        continue
                    filtered_users.append(user)
            users = filtered_users
        
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