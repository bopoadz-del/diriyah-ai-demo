"""
Analytics Router for Diriyah Brain AI
Provides API endpoints for accessing processed document insights and analytics
"""
from flask import Blueprint, request, jsonify
from datetime import datetime, timedelta
from diriyah_brain_ai.auth import rbac, require_auth
from diriyah_brain_ai.knowledge_base import knowledge_base
from diriyah_brain_ai.google_drive_client import google_drive_client
from diriyah_brain_ai.document_processor import DocumentProcessor
import logging

logger = logging.getLogger(__name__)
analytics_router = Blueprint('analytics', __name__)
document_processor = DocumentProcessor()

@analytics_router.route('/project-insights/<project_name>', methods=['GET'])
@require_auth
def get_project_insights(project_name):
    """Get comprehensive project insights from processed documents"""
    try:
        user_role = request.user_role
        
        # Check project access
        if not rbac.user_can_access_project(user_role, project_name):
            return jsonify({
                'error': 'Access denied',
                'message': 'You do not have access to this project'
            }), 403
        
        # Get project insights from knowledge base
        project_insights = knowledge_base.project_insights.get(project_name, {})
        
        # Filter insights based on user role
        filtered_insights = _filter_insights_by_role(project_insights, user_role)
        
        return jsonify({
            'project': project_name,
            'insights': filtered_insights,
            'last_updated': project_insights.get('last_updated', datetime.now().isoformat()),
            'documents_processed': project_insights.get('documents_processed', 0)
        })
        
    except Exception as e:
        logger.error(f"Failed to get project insights: {e}")
        return jsonify({'error': 'Failed to retrieve insights', 'details': str(e)}), 500

@analytics_router.route('/document-analysis', methods=['POST'])
@require_auth
def analyze_document():
    """Analyze a specific document and return insights"""
    try:
        user_role = request.user_role
        data = request.get_json()
        
        if not data or 'file_name' not in data:
            return jsonify({'error': 'file_name is required'}), 400
        
        file_name = data['file_name']
        project = data.get('project', 'default')
        
        # Check project access
        if not rbac.user_can_access_project(user_role, project):
            return jsonify({
                'error': 'Access denied',
                'message': 'You do not have access to this project'
            }), 403
        
        # Get document from Google Drive
        try:
            document_data = google_drive_client.get_file_content(file_name)
            if not document_data:
                return jsonify({'error': 'Document not found'}), 404
        except Exception as e:
            return jsonify({'error': 'Failed to retrieve document', 'details': str(e)}), 500
        
        # Process document
        processed_data = document_processor.process_document(file_name, document_data.get('type'))
        
        # Integrate into knowledge base
        integration_result = knowledge_base.integrate_document(processed_data, project)
        
        # Filter results based on user role
        filtered_results = _filter_document_analysis_by_role(processed_data, user_role)
        
        return jsonify({
            'file_name': file_name,
            'project': project,
            'analysis': filtered_results,
            'integration_status': integration_result.get('integration_status', 'unknown'),
            'processed_at': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Failed to analyze document: {e}")
        return jsonify({'error': 'Document analysis failed', 'details': str(e)}), 500

@analytics_router.route('/bulk-analysis/<project_name>', methods=['POST'])
@require_auth
def bulk_document_analysis(project_name):
    """Perform bulk analysis of all documents in a project"""
    try:
        user_role = request.user_role
        
        # Check project access
        if not rbac.user_can_access_project(user_role, project_name):
            return jsonify({
                'error': 'Access denied',
                'message': 'You do not have access to this project'
            }), 403
        
        # Get all documents for the project
        try:
            documents = google_drive_client.list_files(project_name)
        except Exception as e:
            return jsonify({'error': 'Failed to retrieve documents', 'details': str(e)}), 500
        
        analysis_results = []
        processed_count = 0
        failed_count = 0
        
        for doc in documents[:10]:  # Limit to 10 documents for performance
            try:
                # Get document content
                document_data = google_drive_client.get_file_content(doc['name'])
                
                # Process document
                processed_data = document_processor.process_document(doc['name'], document_data.get('type'))
                
                # Integrate into knowledge base
                integration_result = knowledge_base.integrate_document(processed_data, project_name)
                
                # Filter results based on user role
                filtered_results = _filter_document_analysis_by_role(processed_data, user_role)
                
                analysis_results.append({
                    'file_name': doc['name'],
                    'status': 'success',
                    'analysis_summary': _generate_analysis_summary(filtered_results),
                    'integration_status': integration_result.get('integration_status', 'unknown')
                })
                
                processed_count += 1
                
            except Exception as e:
                logger.error(f"Failed to process document {doc['name']}: {e}")
                analysis_results.append({
                    'file_name': doc['name'],
                    'status': 'failed',
                    'error': str(e)
                })
                failed_count += 1
        
        return jsonify({
            'project': project_name,
            'total_documents': len(documents),
            'processed_successfully': processed_count,
            'failed_processing': failed_count,
            'results': analysis_results,
            'bulk_analysis_completed_at': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Bulk analysis failed: {e}")
        return jsonify({'error': 'Bulk analysis failed', 'details': str(e)}), 500

@analytics_router.route('/risk-assessment/<project_name>', methods=['GET'])
@require_auth
def get_risk_assessment(project_name):
    """Get comprehensive risk assessment for a project"""
    try:
        user_role = request.user_role
        
        # Check project access
        if not rbac.user_can_access_project(user_role, project_name):
            return jsonify({
                'error': 'Access denied',
                'message': 'You do not have access to this project'
            }), 403
        
        # Get project insights
        project_insights = knowledge_base.project_insights.get(project_name, {})
        
        # Generate risk assessment
        risk_assessment = _generate_risk_assessment(project_insights, user_role)
        
        return jsonify({
            'project': project_name,
            'risk_assessment': risk_assessment,
            'assessment_date': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Risk assessment failed: {e}")
        return jsonify({'error': 'Risk assessment failed', 'details': str(e)}), 500

@analytics_router.route('/quality-metrics/<project_name>', methods=['GET'])
@require_auth
def get_quality_metrics(project_name):
    """Get quality metrics and compliance status for a project"""
    try:
        user_role = request.user_role
        
        # Check project access
        if not rbac.user_can_access_project(user_role, project_name):
            return jsonify({
                'error': 'Access denied',
                'message': 'You do not have access to this project'
            }), 403
        
        # Get project insights
        project_insights = knowledge_base.project_insights.get(project_name, {})
        
        # Generate quality metrics
        quality_metrics = _generate_quality_metrics(project_insights, user_role)
        
        return jsonify({
            'project': project_name,
            'quality_metrics': quality_metrics,
            'metrics_date': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Quality metrics retrieval failed: {e}")
        return jsonify({'error': 'Quality metrics failed', 'details': str(e)}), 500

@analytics_router.route('/progress-tracking/<project_name>', methods=['GET'])
@require_auth
def get_progress_tracking(project_name):
    """Get progress tracking data from processed documents"""
    try:
        user_role = request.user_role
        
        # Check project access
        if not rbac.user_can_access_project(user_role, project_name):
            return jsonify({
                'error': 'Access denied',
                'message': 'You do not have access to this project'
            }), 403
        
        # Get project insights
        project_insights = knowledge_base.project_insights.get(project_name, {})
        
        # Generate progress tracking data
        progress_data = _generate_progress_tracking(project_insights, user_role)
        
        return jsonify({
            'project': project_name,
            'progress_tracking': progress_data,
            'tracking_date': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Progress tracking failed: {e}")
        return jsonify({'error': 'Progress tracking failed', 'details': str(e)}), 500

@analytics_router.route('/document-types-summary/<project_name>', methods=['GET'])
@require_auth
def get_document_types_summary(project_name):
    """Get summary of document types processed for a project"""
    try:
        user_role = request.user_role
        
        # Check project access
        if not rbac.user_can_access_project(user_role, project_name):
            return jsonify({
                'error': 'Access denied',
                'message': 'You do not have access to this project'
            }), 403
        
        # Analyze document cache for this project
        document_types_summary = {}
        
        for doc_id, doc_info in knowledge_base.document_cache.items():
            if doc_info['project'] == project_name:
                doc_type = doc_info['data'].get('type', 'unknown')
                if doc_type not in document_types_summary:
                    document_types_summary[doc_type] = {
                        'count': 0,
                        'latest_processed': None,
                        'insights_count': 0
                    }
                
                document_types_summary[doc_type]['count'] += 1
                document_types_summary[doc_type]['insights_count'] += len(doc_info.get('insights', {}))
                
                # Update latest processed date
                processed_date = doc_info.get('integrated_at')
                if processed_date:
                    if (not document_types_summary[doc_type]['latest_processed'] or 
                        processed_date > document_types_summary[doc_type]['latest_processed']):
                        document_types_summary[doc_type]['latest_processed'] = processed_date
        
        return jsonify({
            'project': project_name,
            'document_types_summary': document_types_summary,
            'total_document_types': len(document_types_summary),
            'summary_date': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Document types summary failed: {e}")
        return jsonify({'error': 'Document types summary failed', 'details': str(e)}), 500

# Helper functions

def _filter_insights_by_role(insights: dict, user_role: str) -> dict:
    """Filter project insights based on user role"""
    role_context = rbac.get_role_context(user_role)
    allowed_data = role_context.get('data_access', [])
    
    filtered = {}
    
    # Always include basic information
    filtered['documents_processed'] = insights.get('documents_processed', 0)
    filtered['last_updated'] = insights.get('last_updated', '')
    
    # Include role-appropriate data
    if 'all' in allowed_data or user_role in ['ceo', 'director']:
        filtered = insights.copy()
    elif 'financial' in allowed_data or user_role == 'commercial_manager':
        filtered['financial_summary'] = insights.get('financial_summary', {})
    elif 'operational' in allowed_data or user_role in ['site_manager', 'engineer']:
        filtered['progress_summary'] = insights.get('progress_summary', {})
        filtered['quality_summary'] = insights.get('quality_summary', {})
        filtered['safety_summary'] = insights.get('safety_summary', {})
    
    return filtered

def _filter_document_analysis_by_role(analysis: dict, user_role: str) -> dict:
    """Filter document analysis results based on user role"""
    role_context = rbac.get_role_context(user_role)
    allowed_docs = role_context.get('allowed_documents', [])
    
    # Check if user can access this document type
    doc_category = analysis.get('analysis', {}).get('document_category', 'unknown')
    
    if 'all' in role_context.get('data_access', []) or doc_category in allowed_docs:
        return analysis
    else:
        # Return limited information
        return {
            'type': analysis.get('type', 'unknown'),
            'access_restricted': True,
            'message': f'Access to {doc_category} documents is restricted for your role'
        }

def _generate_analysis_summary(analysis: dict) -> dict:
    """Generate a summary of document analysis"""
    if analysis.get('access_restricted'):
        return {'status': 'access_restricted'}
    
    summary = {
        'document_type': analysis.get('type', 'unknown'),
        'has_text_content': bool(analysis.get('text_content')),
        'insights_count': len(analysis.get('analysis', {})),
        'processing_status': 'success'
    }
    
    # Add type-specific summaries
    if analysis.get('type') == 'pdf':
        summary['pages'] = len(analysis.get('pages', []))
        summary['tables'] = len(analysis.get('tables', []))
    elif analysis.get('type') == 'excel':
        summary['sheets'] = len(analysis.get('sheets', []))
    elif analysis.get('type') == 'cad':
        summary['entities'] = len(analysis.get('entities', []))
        summary['layers'] = len(analysis.get('layers', []))
    
    return summary

def _generate_risk_assessment(project_insights: dict, user_role: str) -> dict:
    """Generate risk assessment from project insights"""
    risk_summary = project_insights.get('risk_summary', {})
    
    assessment = {
        'overall_risk_level': 'medium',
        'total_risks_identified': risk_summary.get('total_risks', 0),
        'risk_categories': {
            'schedule': 'low',
            'financial': 'medium',
            'quality': 'low',
            'safety': 'low'
        },
        'recommendations': []
    }
    
    # Determine overall risk level
    total_risks = risk_summary.get('total_risks', 0)
    if total_risks > 10:
        assessment['overall_risk_level'] = 'high'
        assessment['recommendations'].append('Immediate risk mitigation required')
    elif total_risks > 5:
        assessment['overall_risk_level'] = 'medium'
        assessment['recommendations'].append('Monitor risks closely')
    else:
        assessment['overall_risk_level'] = 'low'
        assessment['recommendations'].append('Continue current risk management practices')
    
    # Add role-specific recommendations
    if user_role == 'ceo':
        assessment['recommendations'].append('Review strategic risk implications')
    elif user_role == 'director':
        assessment['recommendations'].append('Ensure operational risk controls are in place')
    elif user_role == 'site_manager':
        assessment['recommendations'].append('Focus on operational and safety risks')
    
    return assessment

def _generate_quality_metrics(project_insights: dict, user_role: str) -> dict:
    """Generate quality metrics from project insights"""
    quality_summary = project_insights.get('quality_summary', {})
    
    metrics = {
        'quality_score': 85,  # Simulated score
        'quality_issues_count': quality_summary.get('quality_issues', 0),
        'compliance_status': 'compliant',
        'inspection_pass_rate': 92,  # Simulated percentage
        'ncr_count': quality_summary.get('quality_issues', 0),
        'quality_trends': 'improving'
    }
    
    # Determine compliance status
    if metrics['quality_issues_count'] > 5:
        metrics['compliance_status'] = 'non-compliant'
        metrics['quality_score'] = 65
    elif metrics['quality_issues_count'] > 2:
        metrics['compliance_status'] = 'partially_compliant'
        metrics['quality_score'] = 75
    
    return metrics

def _generate_progress_tracking(project_insights: dict, user_role: str) -> dict:
    """Generate progress tracking data from project insights"""
    progress_summary = project_insights.get('progress_summary', {})
    
    tracking = {
        'overall_progress_percentage': 78,  # Simulated
        'milestones_completed': 12,
        'milestones_total': 16,
        'current_phase': 'Construction Phase 3',
        'schedule_variance_days': -3,  # Behind schedule
        'critical_path_status': 'on_track',
        'upcoming_milestones': [
            {'name': 'Foundation Completion', 'due_date': '2024-10-15'},
            {'name': 'MEP Rough-in', 'due_date': '2024-11-01'}
        ]
    }
    
    return tracking

