"""
Admin router for Diriyah Brain AI - User and Role Management
"""
from flask import Blueprint, request, jsonify
import json
import os
from datetime import datetime
from diriyah_brain_ai.auth import rbac, require_auth, require_permission

admin_router = Blueprint('admin', __name__)

# Admin data storage (in production, this would be a proper database)
ADMIN_DATA_FILE = '/tmp/diriyah_admin_data.json'

def load_admin_data():
    """Load admin data from file"""
    if os.path.exists(ADMIN_DATA_FILE):
        with open(ADMIN_DATA_FILE, 'r') as f:
            return json.load(f)
    return {
        'users': {},
        'roles': rbac.roles.copy(),
        'projects': [
            'heritage_resort',
            'boulevard_development', 
            'infrastructure_mc0a',
            'cultural_district'
        ],
        'activity_log': []
    }

def save_admin_data(data):
    """Save admin data to file"""
    with open(ADMIN_DATA_FILE, 'w') as f:
        json.dump(data, f, indent=2)

def log_admin_activity(user_id, action, details):
    """Log admin activity"""
    data = load_admin_data()
    data['activity_log'].append({
        'timestamp': datetime.now().isoformat(),
        'user_id': user_id,
        'action': action,
        'details': details
    })
    # Keep only last 100 entries
    data['activity_log'] = data['activity_log'][-100:]
    save_admin_data(data)

@admin_router.route('/dashboard', methods=['GET'])
@require_auth
@require_permission('admin')
def admin_dashboard():
    """Get admin dashboard data"""
    try:
        data = load_admin_data()
        
        # Calculate statistics
        stats = {
            'total_users': len(data['users']),
            'total_roles': len(data['roles']),
            'total_projects': len(data['projects']),
            'recent_activities': data['activity_log'][-10:],  # Last 10 activities
            'users_by_role': {}
        }
        
        # Count users by role
        for user_data in data['users'].values():
            role = user_data.get('role', 'unknown')
            stats['users_by_role'][role] = stats['users_by_role'].get(role, 0) + 1
        
        return jsonify({
            'success': True,
            'stats': stats,
            'data': data
        })
        
    except Exception as e:
        return jsonify({'error': 'Failed to load dashboard', 'details': str(e)}), 500

@admin_router.route('/users', methods=['GET'])
@require_auth
@require_permission('admin')
def list_users():
    """List all users"""
    try:
        data = load_admin_data()
        return jsonify({
            'success': True,
            'users': data['users']
        })
    except Exception as e:
        return jsonify({'error': 'Failed to list users', 'details': str(e)}), 500

@admin_router.route('/users', methods=['POST'])
@require_auth
@require_permission('admin')
def create_user():
    """Create a new user"""
    try:
        user_data = request.get_json()
        required_fields = ['username', 'email', 'role', 'projects']
        
        for field in required_fields:
            if field not in user_data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        data = load_admin_data()
        
        # Check if user already exists
        if user_data['username'] in data['users']:
            return jsonify({'error': 'User already exists'}), 400
        
        # Validate role
        if user_data['role'] not in data['roles']:
            return jsonify({'error': 'Invalid role'}), 400
        
        # Create user
        new_user = {
            'username': user_data['username'],
            'email': user_data['email'],
            'role': user_data['role'],
            'projects': user_data['projects'],
            'active': user_data.get('active', True),
            'created_at': datetime.now().isoformat(),
            'created_by': request.user.get('username'),
            'last_login': None,
            'permissions': data['roles'][user_data['role']].copy()
        }
        
        data['users'][user_data['username']] = new_user
        save_admin_data(data)
        
        # Log activity
        log_admin_activity(
            request.user.get('username'),
            'create_user',
            f"Created user {user_data['username']} with role {user_data['role']}"
        )
        
        return jsonify({
            'success': True,
            'message': 'User created successfully',
            'user': new_user
        })
        
    except Exception as e:
        return jsonify({'error': 'Failed to create user', 'details': str(e)}), 500

@admin_router.route('/users/<username>', methods=['PUT'])
@require_auth
@require_permission('admin')
def update_user(username):
    """Update an existing user"""
    try:
        user_data = request.get_json()
        data = load_admin_data()
        
        if username not in data['users']:
            return jsonify({'error': 'User not found'}), 404
        
        # Update user data
        current_user = data['users'][username]
        
        if 'role' in user_data and user_data['role'] != current_user['role']:
            if user_data['role'] not in data['roles']:
                return jsonify({'error': 'Invalid role'}), 400
            current_user['role'] = user_data['role']
            current_user['permissions'] = data['roles'][user_data['role']].copy()
        
        if 'projects' in user_data:
            current_user['projects'] = user_data['projects']
        
        if 'active' in user_data:
            current_user['active'] = user_data['active']
        
        if 'email' in user_data:
            current_user['email'] = user_data['email']
        
        current_user['updated_at'] = datetime.now().isoformat()
        current_user['updated_by'] = request.user.get('username')
        
        save_admin_data(data)
        
        # Log activity
        log_admin_activity(
            request.user.get('username'),
            'update_user',
            f"Updated user {username}"
        )
        
        return jsonify({
            'success': True,
            'message': 'User updated successfully',
            'user': current_user
        })
        
    except Exception as e:
        return jsonify({'error': 'Failed to update user', 'details': str(e)}), 500

@admin_router.route('/users/<username>', methods=['DELETE'])
@require_auth
@require_permission('admin')
def delete_user(username):
    """Delete a user"""
    try:
        data = load_admin_data()
        
        if username not in data['users']:
            return jsonify({'error': 'User not found'}), 404
        
        # Don't allow deleting yourself
        if username == request.user.get('username'):
            return jsonify({'error': 'Cannot delete your own account'}), 400
        
        del data['users'][username]
        save_admin_data(data)
        
        # Log activity
        log_admin_activity(
            request.user.get('username'),
            'delete_user',
            f"Deleted user {username}"
        )
        
        return jsonify({
            'success': True,
            'message': 'User deleted successfully'
        })
        
    except Exception as e:
        return jsonify({'error': 'Failed to delete user', 'details': str(e)}), 500

@admin_router.route('/roles', methods=['GET'])
@require_auth
@require_permission('admin')
def list_roles():
    """List all roles and their permissions"""
    try:
        data = load_admin_data()
        return jsonify({
            'success': True,
            'roles': data['roles']
        })
    except Exception as e:
        return jsonify({'error': 'Failed to list roles', 'details': str(e)}), 500

@admin_router.route('/roles', methods=['POST'])
@require_auth
@require_permission('admin')
def create_role():
    """Create a new role"""
    try:
        role_data = request.get_json()
        required_fields = ['name', 'permissions']
        
        for field in required_fields:
            if field not in role_data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        data = load_admin_data()
        
        # Check if role already exists
        if role_data['name'] in data['roles']:
            return jsonify({'error': 'Role already exists'}), 400
        
        # Create role
        new_role = {
            'allowed_documents': role_data['permissions'].get('allowed_documents', []),
            'data_access': role_data['permissions'].get('data_access', []),
            'permissions': role_data['permissions'].get('permissions', []),
            'description': role_data.get('description', ''),
            'created_at': datetime.now().isoformat(),
            'created_by': request.user.get('username')
        }
        
        data['roles'][role_data['name']] = new_role
        save_admin_data(data)
        
        # Log activity
        log_admin_activity(
            request.user.get('username'),
            'create_role',
            f"Created role {role_data['name']}"
        )
        
        return jsonify({
            'success': True,
            'message': 'Role created successfully',
            'role': new_role
        })
        
    except Exception as e:
        return jsonify({'error': 'Failed to create role', 'details': str(e)}), 500

@admin_router.route('/roles/<role_name>', methods=['PUT'])
@require_auth
@require_permission('admin')
def update_role(role_name):
    """Update an existing role"""
    try:
        role_data = request.get_json()
        data = load_admin_data()
        
        if role_name not in data['roles']:
            return jsonify({'error': 'Role not found'}), 404
        
        # Update role
        current_role = data['roles'][role_name]
        
        if 'permissions' in role_data:
            if 'allowed_documents' in role_data['permissions']:
                current_role['allowed_documents'] = role_data['permissions']['allowed_documents']
            if 'data_access' in role_data['permissions']:
                current_role['data_access'] = role_data['permissions']['data_access']
            if 'permissions' in role_data['permissions']:
                current_role['permissions'] = role_data['permissions']['permissions']
        
        if 'description' in role_data:
            current_role['description'] = role_data['description']
        
        current_role['updated_at'] = datetime.now().isoformat()
        current_role['updated_by'] = request.user.get('username')
        
        save_admin_data(data)
        
        # Update all users with this role
        for username, user_data in data['users'].items():
            if user_data['role'] == role_name:
                user_data['permissions'] = current_role.copy()
        
        save_admin_data(data)
        
        # Log activity
        log_admin_activity(
            request.user.get('username'),
            'update_role',
            f"Updated role {role_name}"
        )
        
        return jsonify({
            'success': True,
            'message': 'Role updated successfully',
            'role': current_role
        })
        
    except Exception as e:
        return jsonify({'error': 'Failed to update role', 'details': str(e)}), 500

@admin_router.route('/projects', methods=['GET'])
@require_auth
@require_permission('admin')
def list_projects():
    """List all projects"""
    try:
        data = load_admin_data()
        return jsonify({
            'success': True,
            'projects': data['projects']
        })
    except Exception as e:
        return jsonify({'error': 'Failed to list projects', 'details': str(e)}), 500

@admin_router.route('/projects', methods=['POST'])
@require_auth
@require_permission('admin')
def create_project():
    """Create a new project"""
    try:
        project_data = request.get_json()
        
        if 'name' not in project_data:
            return jsonify({'error': 'Missing required field: name'}), 400
        
        data = load_admin_data()
        project_id = project_data['name'].lower().replace(' ', '_')
        
        if project_id in data['projects']:
            return jsonify({'error': 'Project already exists'}), 400
        
        data['projects'].append(project_id)
        save_admin_data(data)
        
        # Log activity
        log_admin_activity(
            request.user.get('username'),
            'create_project',
            f"Created project {project_data['name']}"
        )
        
        return jsonify({
            'success': True,
            'message': 'Project created successfully',
            'project_id': project_id
        })
        
    except Exception as e:
        return jsonify({'error': 'Failed to create project', 'details': str(e)}), 500

@admin_router.route('/activity-log', methods=['GET'])
@require_auth
@require_permission('admin')
def get_activity_log():
    """Get admin activity log"""
    try:
        data = load_admin_data()
        limit = request.args.get('limit', 50, type=int)
        
        return jsonify({
            'success': True,
            'activities': data['activity_log'][-limit:]
        })
        
    except Exception as e:
        return jsonify({'error': 'Failed to get activity log', 'details': str(e)}), 500

@admin_router.route('/user-permissions/<username>', methods=['GET'])
@require_auth
@require_permission('admin')
def get_user_permissions(username):
    """Get detailed permissions for a specific user"""
    try:
        data = load_admin_data()
        
        if username not in data['users']:
            return jsonify({'error': 'User not found'}), 404
        
        user = data['users'][username]
        role_permissions = data['roles'].get(user['role'], {})
        
        return jsonify({
            'success': True,
            'user': user,
            'role_permissions': role_permissions,
            'effective_permissions': {
                'allowed_documents': role_permissions.get('allowed_documents', []),
                'data_access': role_permissions.get('data_access', []),
                'permissions': role_permissions.get('permissions', []),
                'projects': user.get('projects', [])
            }
        })
        
    except Exception as e:
        return jsonify({'error': 'Failed to get user permissions', 'details': str(e)}), 500

@admin_router.route('/bulk-update', methods=['POST'])
@require_auth
@require_permission('admin')
def bulk_update_users():
    """Bulk update multiple users"""
    try:
        bulk_data = request.get_json()
        
        if 'users' not in bulk_data or 'updates' not in bulk_data:
            return jsonify({'error': 'Missing required fields: users, updates'}), 400
        
        data = load_admin_data()
        updated_users = []
        
        for username in bulk_data['users']:
            if username in data['users']:
                user = data['users'][username]
                
                # Apply updates
                if 'role' in bulk_data['updates']:
                    new_role = bulk_data['updates']['role']
                    if new_role in data['roles']:
                        user['role'] = new_role
                        user['permissions'] = data['roles'][new_role].copy()
                
                if 'projects' in bulk_data['updates']:
                    user['projects'] = bulk_data['updates']['projects']
                
                if 'active' in bulk_data['updates']:
                    user['active'] = bulk_data['updates']['active']
                
                user['updated_at'] = datetime.now().isoformat()
                user['updated_by'] = request.user.get('username')
                updated_users.append(username)
        
        save_admin_data(data)
        
        # Log activity
        log_admin_activity(
            request.user.get('username'),
            'bulk_update',
            f"Bulk updated {len(updated_users)} users: {', '.join(updated_users)}"
        )
        
        return jsonify({
            'success': True,
            'message': f'Successfully updated {len(updated_users)} users',
            'updated_users': updated_users
        })
        
    except Exception as e:
        return jsonify({'error': 'Failed to bulk update users', 'details': str(e)}), 500

