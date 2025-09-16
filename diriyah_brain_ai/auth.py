"""
Authentication and Role-Based Access Control (RBAC) for Diriyah Brain AI
"""
from functools import wraps
from typing import Dict, List, Optional
import jwt
from datetime import datetime, timedelta

# Role hierarchy and permissions
ROLE_PERMISSIONS = {
    'ceo': {
        'data_access': ['all'],
        'documents': ['boq', 'schedules', 'contracts', 'financials', 'insurances', 'rfis', 'moms', 'ncrs', 'quotes', 'commercial'],
        'actions': ['view', 'edit', 'delete', 'approve', 'export'],
        'projects': ['all'],
        'description': 'Chief Executive Officer - Full access to all data and operations'
    },
    'director': {
        'data_access': ['strategic', 'operational', 'financial'],
        'documents': ['boq', 'schedules', 'contracts', 'financials', 'insurances', 'rfis', 'moms', 'ncrs'],
        'actions': ['view', 'edit', 'approve', 'export'],
        'projects': ['all'],
        'description': 'Director - Strategic oversight and financial access'
    },
    'project_manager': {
        'data_access': ['operational', 'technical'],
        'documents': ['boq', 'schedules', 'rfis', 'moms', 'ncrs', 'technical_drawings'],
        'actions': ['view', 'edit', 'export'],
        'projects': ['assigned'],
        'description': 'Project Manager - Operational and technical project data'
    },
    'site_manager': {
        'data_access': ['operational', 'technical'],
        'documents': ['schedules', 'rfis', 'moms', 'ncrs', 'technical_drawings', 'safety_reports'],
        'actions': ['view', 'edit'],
        'projects': ['assigned'],
        'description': 'Site Manager - On-site operations and technical data only'
    },
    'engineer': {
        'data_access': ['technical'],
        'documents': ['boq', 'schedules', 'technical_drawings', 'rfis', 'ncrs'],
        'actions': ['view', 'edit'],
        'projects': ['assigned'],
        'description': 'Engineer - Technical documentation and specifications'
    },
    'commercial_manager': {
        'data_access': ['commercial', 'financial'],
        'documents': ['contracts', 'quotes', 'financials', 'insurances', 'variations'],
        'actions': ['view', 'edit', 'approve'],
        'projects': ['assigned'],
        'description': 'Commercial Manager - Financial and contractual matters'
    },
    'safety_officer': {
        'data_access': ['safety', 'operational'],
        'documents': ['safety_reports', 'ncrs', 'moms', 'schedules'],
        'actions': ['view', 'edit'],
        'projects': ['assigned'],
        'description': 'Safety Officer - Safety compliance and reporting'
    }
}

# Mock user database (in production, this would be from a real database)
MOCK_USERS = {
    'ahmed.ceo@diriyah.sa': {
        'name': 'Ahmed Al-Rashid',
        'role': 'ceo',
        'projects': ['all'],
        'department': 'Executive',
        'employee_id': 'DIR001'
    },
    'sara.director@diriyah.sa': {
        'name': 'Sara Al-Mansouri',
        'role': 'director',
        'projects': ['heritage_resort', 'boulevard_development'],
        'department': 'Operations',
        'employee_id': 'DIR002'
    },
    'mohammed.pm@diriyah.sa': {
        'name': 'Mohammed Al-Otaibi',
        'role': 'project_manager',
        'projects': ['heritage_resort'],
        'department': 'Project Management',
        'employee_id': 'DIR003'
    },
    'fatima.site@diriyah.sa': {
        'name': 'Fatima Al-Zahra',
        'role': 'site_manager',
        'projects': ['infrastructure_mc0a'],
        'department': 'Site Operations',
        'employee_id': 'DIR004'
    },
    'omar.engineer@diriyah.sa': {
        'name': 'Omar Al-Harbi',
        'role': 'engineer',
        'projects': ['heritage_resort', 'infrastructure_mc0a'],
        'department': 'Engineering',
        'employee_id': 'DIR005'
    },
    'layla.commercial@diriyah.sa': {
        'name': 'Layla Al-Dosari',
        'role': 'commercial_manager',
        'projects': ['boulevard_development', 'cultural_district'],
        'department': 'Commercial',
        'employee_id': 'DIR006'
    }
}

class RBACManager:
    """Role-Based Access Control Manager"""
    
    def __init__(self):
        self.secret_key = "diriyah_brain_ai_secret_2024"  # In production, use environment variable
    
    def authenticate_user(self, email: str, password: str) -> Optional[Dict]:
        """Authenticate user and return user info if valid"""
        # In production, verify password hash
        if email in MOCK_USERS:
            user_info = MOCK_USERS[email].copy()
            user_info['email'] = email
            return user_info
        return None
    
    def generate_token(self, user_info: Dict) -> str:
        """Generate JWT token for authenticated user"""
        payload = {
            'email': user_info['email'],
            'role': user_info['role'],
            'projects': user_info['projects'],
            'exp': datetime.utcnow() + timedelta(hours=8)  # 8-hour session
        }
        return jwt.encode(payload, self.secret_key, algorithm='HS256')
    
    def verify_token(self, token: str) -> Optional[Dict]:
        """Verify JWT token and return user info"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=['HS256'])
            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None
    
    def check_permission(self, user_role: str, action: str, document_type: str = None, project_id: str = None) -> bool:
        """Check if user role has permission for specific action"""
        if user_role not in ROLE_PERMISSIONS:
            return False
        
        role_perms = ROLE_PERMISSIONS[user_role]
        
        # Check action permission
        if action not in role_perms.get('actions', []):
            return False
        
        # Check document access if specified
        if document_type:
            allowed_docs = role_perms.get('documents', [])
            if document_type not in allowed_docs and 'all' not in role_perms.get('data_access', []):
                return False
        
        return True
    
    def filter_documents_by_role(self, user_role: str, documents: List[Dict]) -> List[Dict]:
        """Filter documents based on user role permissions"""
        if user_role not in ROLE_PERMISSIONS:
            return []
        
        role_perms = ROLE_PERMISSIONS[user_role]
        allowed_docs = role_perms.get('documents', [])
        
        # CEO has access to all documents
        if 'all' in role_perms.get('data_access', []):
            return documents
        
        # Filter documents based on role permissions
        filtered_docs = []
        for doc in documents:
            doc_type = doc.get('type', '').lower()
            if doc_type in allowed_docs:
                filtered_docs.append(doc)
        
        return filtered_docs
    
    def get_role_context(self, user_role: str) -> Dict:
        """Get role-specific context for AI responses"""
        if user_role not in ROLE_PERMISSIONS:
            return {}
        
        role_info = ROLE_PERMISSIONS[user_role]
        return {
            'role': user_role,
            'description': role_info['description'],
            'data_access': role_info['data_access'],
            'allowed_documents': role_info['documents'],
            'allowed_actions': role_info['actions']
        }
    
    def generate_role_aware_prompt(self, user_role: str, query: str) -> str:
        """Generate role-aware prompt for AI based on user permissions"""
        role_context = self.get_role_context(user_role)
        
        if not role_context:
            return query
        
        # Create role-specific prompt prefix
        prompt_prefix = f"""
You are responding to a {role_context['description']} in the Diriyah construction project.

IMPORTANT ROLE RESTRICTIONS:
- User role: {user_role.upper()}
- Data access level: {', '.join(role_context['data_access'])}
- Allowed documents: {', '.join(role_context['allowed_documents'])}
- Allowed actions: {', '.join(role_context['allowed_actions'])}

RESPONSE GUIDELINES:
- Only provide information the user is authorized to see
- If asked about restricted information, politely explain access limitations
- Focus responses on their area of responsibility
- Use appropriate technical level for their role

User query: {query}
"""
        return prompt_prefix

# Global RBAC instance
rbac = RBACManager()

def require_auth(f):
    """Decorator to require authentication for API endpoints"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        from flask import request, jsonify
        
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'error': 'No authorization token provided'}), 401
        
        if token.startswith('Bearer '):
            token = token[7:]
        
        user_info = rbac.verify_token(token)
        if not user_info:
            return jsonify({'error': 'Invalid or expired token'}), 401
        
        # Add user info to request context
        request.user = user_info
        return f(*args, **kwargs)
    
    return decorated_function

def require_permission(action: str, document_type: str = None):
    """Decorator to require specific permission for API endpoints"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            from flask import request, jsonify
            
            if not hasattr(request, 'user'):
                return jsonify({'error': 'Authentication required'}), 401
            
            user_role = request.user.get('role')
            if not rbac.check_permission(user_role, action, document_type):
                return jsonify({'error': f'Insufficient permissions for {action} on {document_type}'}), 403
            
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator

