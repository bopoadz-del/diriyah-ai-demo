"""
Authentication router for Diriyah Brain AI
"""
from flask import Blueprint, request, jsonify
from diriyah_brain_ai.auth import rbac, ROLE_PERMISSIONS

auth_router = Blueprint('auth', __name__)

@auth_router.route('/login', methods=['POST'])
def login():
    """User login endpoint"""
    try:
        data = request.get_json()
        email = data.get('email', '').lower().strip()
        password = data.get('password', '')
        
        if not email or not password:
            return jsonify({'error': 'Email and password are required'}), 400
        
        # Authenticate user
        user_info = rbac.authenticate_user(email, password)
        if not user_info:
            return jsonify({'error': 'Invalid credentials'}), 401
        
        # Generate token
        token = rbac.generate_token(user_info)
        
        # Get role information
        role_info = ROLE_PERMISSIONS.get(user_info['role'], {})
        
        return jsonify({
            'success': True,
            'token': token,
            'user': {
                'name': user_info['name'],
                'email': user_info['email'],
                'role': user_info['role'],
                'role_description': role_info.get('description', ''),
                'department': user_info['department'],
                'employee_id': user_info['employee_id'],
                'projects': user_info['projects'],
                'permissions': {
                    'data_access': role_info.get('data_access', []),
                    'documents': role_info.get('documents', []),
                    'actions': role_info.get('actions', [])
                }
            }
        })
        
    except Exception as e:
        return jsonify({'error': 'Login failed', 'details': str(e)}), 500

@auth_router.route('/verify', methods=['GET'])
def verify_token():
    """Verify token and return user info"""
    try:
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'error': 'No authorization token provided'}), 401
        
        if token.startswith('Bearer '):
            token = token[7:]
        
        user_info = rbac.verify_token(token)
        if not user_info:
            return jsonify({'error': 'Invalid or expired token'}), 401
        
        # Get full user details
        email = user_info['email']
        from diriyah_brain_ai.auth import MOCK_USERS
        full_user_info = MOCK_USERS.get(email, {})
        role_info = ROLE_PERMISSIONS.get(user_info['role'], {})
        
        return jsonify({
            'success': True,
            'user': {
                'name': full_user_info.get('name', ''),
                'email': email,
                'role': user_info['role'],
                'role_description': role_info.get('description', ''),
                'department': full_user_info.get('department', ''),
                'employee_id': full_user_info.get('employee_id', ''),
                'projects': user_info['projects'],
                'permissions': {
                    'data_access': role_info.get('data_access', []),
                    'documents': role_info.get('documents', []),
                    'actions': role_info.get('actions', [])
                }
            }
        })
        
    except Exception as e:
        return jsonify({'error': 'Token verification failed', 'details': str(e)}), 500

@auth_router.route('/logout', methods=['POST'])
def logout():
    """User logout endpoint"""
    # In a real implementation, you might want to blacklist the token
    return jsonify({'success': True, 'message': 'Logged out successfully'})

@auth_router.route('/demo-users', methods=['GET'])
def get_demo_users():
    """Get list of demo users for testing (remove in production)"""
    from diriyah_brain_ai.auth import MOCK_USERS
    
    demo_users = []
    for email, user_info in MOCK_USERS.items():
        role_info = ROLE_PERMISSIONS.get(user_info['role'], {})
        demo_users.append({
            'email': email,
            'name': user_info['name'],
            'role': user_info['role'],
            'role_description': role_info.get('description', ''),
            'department': user_info['department'],
            'password': 'demo123'  # For demo purposes only
        })
    
    return jsonify({'demo_users': demo_users})

