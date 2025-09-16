"""
Documents router for Diriyah Brain AI
Handles document processing, analysis, and search
"""
from flask import Blueprint, request, jsonify
import os
import tempfile
from diriyah_brain_ai.auth import rbac, require_auth, require_permission
from diriyah_brain_ai.google_drive_client import google_drive_client
from diriyah_brain_ai.document_processor import document_processor

documents_router = Blueprint('documents', __name__)

@documents_router.route('/search', methods=['POST'])
@require_auth
def search_documents():
    """Search documents with role-based filtering"""
    try:
        data = request.get_json()
        query = data.get('query', '')
        project = data.get('project', '')
        document_types = data.get('document_types', [])
        
        if not query:
            return jsonify({'error': 'Query is required'}), 400
        
        # Get user role and permissions
        user_role = request.user.get('role')
        user_projects = request.user.get('projects', [])
        
        # Check project access
        if 'all' not in user_projects and project.lower().replace(' ', '_') not in user_projects:
            return jsonify({
                'error': 'Access denied',
                'message': 'You do not have access to this project'
            }), 403
        
        # Search documents
        search_query = f"{query} {project}" if project else query
        results = google_drive_client.search_documents(search_query, document_types)
        
        # Filter results based on user role permissions
        filtered_results = []
        for result in results:
            if _user_can_access_document(user_role, result):
                # Remove sensitive information based on role
                filtered_result = _filter_document_content(user_role, result)
                filtered_results.append(filtered_result)
        
        return jsonify({
            'results': filtered_results,
            'count': len(filtered_results),
            'query': query,
            'user_role': user_role
        })
        
    except Exception as e:
        return jsonify({'error': 'Search failed', 'details': str(e)}), 500

@documents_router.route('/process', methods=['POST'])
@require_auth
def process_document():
    """Process a specific document by ID"""
    try:
        data = request.get_json()
        file_id = data.get('file_id', '')
        
        if not file_id:
            return jsonify({'error': 'File ID is required'}), 400
        
        # Get user role
        user_role = request.user.get('role')
        
        # Process the document
        result = google_drive_client.process_file(file_id)
        
        if 'error' in result:
            return jsonify(result), 400
        
        # Check if user can access this document
        if not _user_can_access_document(user_role, result):
            return jsonify({
                'error': 'Access denied',
                'message': 'You do not have permission to access this document'
            }), 403
        
        # Filter content based on role
        filtered_result = _filter_document_content(user_role, result)
        
        return jsonify(filtered_result)
        
    except Exception as e:
        return jsonify({'error': 'Processing failed', 'details': str(e)}), 500

@documents_router.route('/project/<project_name>', methods=['GET'])
@require_auth
def get_project_documents(project_name):
    """Get all documents for a project, organized by type"""
    try:
        # Get user role and permissions
        user_role = request.user.get('role')
        user_projects = request.user.get('projects', [])
        
        # Check project access
        if 'all' not in user_projects and project_name.lower().replace(' ', '_') not in user_projects:
            return jsonify({
                'error': 'Access denied',
                'message': 'You do not have access to this project'
            }), 403
        
        # Get project documents
        documents = google_drive_client.get_project_documents(project_name)
        
        # Filter documents based on role permissions
        filtered_documents = {}
        for doc_type, doc_list in documents.items():
            if _user_can_access_document_type(user_role, doc_type):
                filtered_documents[doc_type] = doc_list
        
        return jsonify({
            'project': project_name,
            'documents': filtered_documents,
            'user_role': user_role,
            'total_documents': sum(len(docs) for docs in filtered_documents.values())
        })
        
    except Exception as e:
        return jsonify({'error': 'Failed to get project documents', 'details': str(e)}), 500

@documents_router.route('/analyze', methods=['POST'])
@require_auth
def analyze_document_content():
    """Analyze document content for construction-specific information"""
    try:
        data = request.get_json()
        text_content = data.get('text_content', '')
        document_type = data.get('document_type', 'unknown')
        
        if not text_content:
            return jsonify({'error': 'Text content is required'}), 400
        
        # Get user role
        user_role = request.user.get('role')
        
        # Analyze content
        analysis = document_processor._analyze_construction_content(text_content)
        
        # Add role-specific insights
        role_insights = _get_role_specific_insights(user_role, analysis, document_type)
        analysis['role_insights'] = role_insights
        
        return jsonify({
            'analysis': analysis,
            'user_role': user_role,
            'document_type': document_type
        })
        
    except Exception as e:
        return jsonify({'error': 'Analysis failed', 'details': str(e)}), 500

@documents_router.route('/upload', methods=['POST'])
@require_auth
@require_permission('edit')
def upload_document():
    """Upload and process a document"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        # Get user info
        user_role = request.user.get('role')
        
        # Save uploaded file temporarily
        temp_dir = tempfile.gettempdir()
        temp_path = os.path.join(temp_dir, file.filename)
        file.save(temp_path)
        
        try:
            # Process the uploaded file
            result = document_processor.process_document(temp_path)
            
            # Filter content based on role
            filtered_result = _filter_document_content(user_role, result)
            
            return jsonify({
                'success': True,
                'filename': file.filename,
                'processing_result': filtered_result
            })
            
        finally:
            # Clean up temporary file
            if os.path.exists(temp_path):
                os.remove(temp_path)
        
    except Exception as e:
        return jsonify({'error': 'Upload failed', 'details': str(e)}), 500

@documents_router.route('/types', methods=['GET'])
@require_auth
def get_supported_document_types():
    """Get list of supported document types for the user's role"""
    try:
        user_role = request.user.get('role')
        
        # Get all supported formats
        all_formats = document_processor.supported_formats
        
        # Filter based on role permissions
        allowed_formats = {}
        for format_type, extensions in all_formats.items():
            if _user_can_access_document_type(user_role, format_type):
                allowed_formats[format_type] = extensions
        
        return jsonify({
            'supported_formats': allowed_formats,
            'user_role': user_role
        })
        
    except Exception as e:
        return jsonify({'error': 'Failed to get document types', 'details': str(e)}), 500

def _user_can_access_document(user_role: str, document: dict) -> bool:
    """Check if user can access a specific document based on role"""
    if not document or 'analysis' not in document:
        return True  # Allow access if no analysis available
    
    analysis = document['analysis']
    doc_category = analysis.get('document_category', 'unknown')
    
    # Get role permissions
    role_context = rbac.get_role_context(user_role)
    allowed_docs = role_context.get('allowed_documents', [])
    
    # CEO has access to all documents
    if 'all' in role_context.get('data_access', []):
        return True
    
    # Check specific document type permissions
    doc_type_mapping = {
        'boq': 'boq',
        'schedule': 'schedules',
        'contract': 'contracts',
        'rfi': 'rfis',
        'ncr': 'ncrs',
        'mom': 'moms',
        'financial': 'financials',
        'commercial': 'quotes'
    }
    
    required_permission = doc_type_mapping.get(doc_category, doc_category)
    return required_permission in allowed_docs

def _user_can_access_document_type(user_role: str, doc_type: str) -> bool:
    """Check if user can access a document type based on role"""
    role_context = rbac.get_role_context(user_role)
    allowed_docs = role_context.get('allowed_documents', [])
    
    # CEO has access to all document types
    if 'all' in role_context.get('data_access', []):
        return True
    
    # Map document types to permissions
    type_mapping = {
        'boq': 'boq',
        'schedules': 'schedules',
        'contracts': 'contracts',
        'rfis': 'rfis',
        'ncrs': 'ncrs',
        'moms': 'moms',
        'drawings': 'technical_drawings',
        'photos': 'technical_drawings',
        'specifications': 'boq',
        'reports': 'moms',
        'financial': 'financials'
    }
    
    required_permission = type_mapping.get(doc_type, doc_type)
    return required_permission in allowed_docs

def _filter_document_content(user_role: str, document: dict) -> dict:
    """Filter document content based on user role permissions"""
    if not document:
        return document
    
    # Create a copy to avoid modifying the original
    filtered_doc = document.copy()
    
    # Get role permissions
    role_context = rbac.get_role_context(user_role)
    data_access = role_context.get('data_access', [])
    
    # CEO gets full access
    if 'all' in data_access:
        return filtered_doc
    
    # Filter sensitive information for other roles
    if 'commercial' not in data_access and 'financial' not in data_access:
        # Remove financial/commercial information
        if 'text_content' in filtered_doc:
            text = filtered_doc['text_content']
            # Remove lines containing financial keywords
            financial_keywords = ['cost', 'price', 'payment', 'invoice', 'budget', 'sar', '$', '€', '£']
            lines = text.split('\n')
            filtered_lines = []
            for line in lines:
                if not any(keyword in line.lower() for keyword in financial_keywords):
                    filtered_lines.append(line)
                else:
                    filtered_lines.append('[FINANCIAL INFORMATION REDACTED]')
            filtered_doc['text_content'] = '\n'.join(filtered_lines)
        
        # Remove financial tables
        if 'tables' in filtered_doc:
            filtered_tables = []
            for table in filtered_doc['tables']:
                # Check if table contains financial data
                table_text = str(table.get('data', '')).lower()
                if not any(keyword in table_text for keyword in ['cost', 'price', 'amount', 'total', 'sar']):
                    filtered_tables.append(table)
            filtered_doc['tables'] = filtered_tables
    
    return filtered_doc

def _get_role_specific_insights(user_role: str, analysis: dict, document_type: str) -> dict:
    """Generate role-specific insights from document analysis"""
    insights = {}
    
    if user_role == 'ceo':
        insights = {
            'strategic_importance': 'High' if analysis.get('confidence_score', 0) > 0.7 else 'Medium',
            'business_impact': 'Review for strategic decisions and resource allocation',
            'action_required': 'Monitor key metrics and milestone progress'
        }
    elif user_role == 'director':
        insights = {
            'operational_focus': 'Project coordination and resource management',
            'risk_assessment': 'Medium risk' if 'safety' in analysis.get('keywords_found', {}) else 'Low risk',
            'action_required': 'Ensure compliance and timeline adherence'
        }
    elif user_role == 'site_manager':
        insights = {
            'site_relevance': 'High' if document_type in ['schedule', 'rfi', 'ncr'] else 'Medium',
            'immediate_actions': 'Review for site implementation requirements',
            'safety_considerations': 'Check safety protocols' if 'safety' in analysis.get('keywords_found', {}) else 'Standard safety measures'
        }
    elif user_role == 'engineer':
        insights = {
            'technical_complexity': 'High' if 'materials' in analysis.get('keywords_found', {}) else 'Standard',
            'design_impact': 'Review technical specifications and requirements',
            'quality_focus': 'Ensure compliance with engineering standards'
        }
    elif user_role == 'commercial_manager':
        insights = {
            'financial_impact': 'High' if 'financial' in analysis.get('keywords_found', {}) else 'Low',
            'contract_relevance': 'Review for contractual implications',
            'cost_considerations': 'Monitor budget impact and variations'
        }
    
    return insights

