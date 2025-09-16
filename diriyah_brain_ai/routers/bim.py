"""
BIM Router for Diriyah Brain AI
Provides API endpoints specifically for BIM model processing and analysis
"""
from flask import Blueprint, request, jsonify
from datetime import datetime
from diriyah_brain_ai.auth import rbac, require_auth
from diriyah_brain_ai.processors.bim_processor import bim_processor
from diriyah_brain_ai.knowledge_base import knowledge_base
import logging
import os

logger = logging.getLogger(__name__)
bim_router = Blueprint('bim', __name__)

@bim_router.route('/process-model', methods=['POST'])
@require_auth
def process_bim_model():
    """Process a BIM model file and extract detailed information"""
    try:
        user_role = request.user_role
        data = request.get_json()
        
        if not data or 'file_path' not in data:
            return jsonify({'error': 'file_path is required'}), 400
        
        file_path = data['file_path']
        project = data.get('project', 'default')
        
        # Check project access
        if not rbac.user_can_access_project(user_role, project):
            return jsonify({
                'error': 'Access denied',
                'message': 'You do not have access to this project'
            }), 403
        
        # Check if user can access BIM documents
        role_context = rbac.get_role_context(user_role)
        allowed_docs = role_context.get('allowed_documents', [])
        
        if 'bim' not in allowed_docs and 'all' not in role_context.get('data_access', []):
            return jsonify({
                'error': 'Access denied',
                'message': 'You do not have permission to access BIM models'
            }), 403
        
        # Process BIM model
        bim_analysis = bim_processor.process_bim_file(file_path, {'project': project})
        
        # Integrate into knowledge base
        integration_result = knowledge_base.integrate_document(bim_analysis, project)
        
        return jsonify({
            'file_path': file_path,
            'project': project,
            'bim_analysis': bim_analysis,
            'integration_status': integration_result.get('integration_status', 'unknown'),
            'processed_at': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"BIM model processing failed: {e}")
        return jsonify({'error': 'BIM processing failed', 'details': str(e)}), 500

@bim_router.route('/clash-detection/<project_name>', methods=['GET'])
@require_auth
def get_clash_detection_summary(project_name):
    """Get clash detection summary for all BIM models in a project"""
    try:
        user_role = request.user_role
        
        # Check project access
        if not rbac.user_can_access_project(user_role, project_name):
            return jsonify({
                'error': 'Access denied',
                'message': 'You do not have access to this project'
            }), 403
        
        # Check BIM access
        role_context = rbac.get_role_context(user_role)
        allowed_docs = role_context.get('allowed_documents', [])
        
        if 'bim' not in allowed_docs and 'all' not in role_context.get('data_access', []):
            return jsonify({
                'error': 'Access denied',
                'message': 'You do not have permission to access BIM models'
            }), 403
        
        # Collect clash detection data from knowledge base
        clash_summary = _collect_clash_detection_data(project_name)
        
        return jsonify({
            'project': project_name,
            'clash_detection_summary': clash_summary,
            'summary_date': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Clash detection summary failed: {e}")
        return jsonify({'error': 'Clash detection summary failed', 'details': str(e)}), 500

@bim_router.route('/quantity-takeoff/<project_name>', methods=['GET'])
@require_auth
def get_quantity_takeoff(project_name):
    """Get quantity take-off data from BIM models"""
    try:
        user_role = request.user_role
        
        # Check project access
        if not rbac.user_can_access_project(user_role, project_name):
            return jsonify({
                'error': 'Access denied',
                'message': 'You do not have access to this project'
            }), 403
        
        # Check BIM access
        role_context = rbac.get_role_context(user_role)
        allowed_docs = role_context.get('allowed_documents', [])
        
        if 'bim' not in allowed_docs and 'all' not in role_context.get('data_access', []):
            return jsonify({
                'error': 'Access denied',
                'message': 'You do not have permission to access BIM models'
            }), 403
        
        # Collect QTO data from knowledge base
        qto_data = _collect_quantity_takeoff_data(project_name)
        
        return jsonify({
            'project': project_name,
            'quantity_takeoff': qto_data,
            'qto_date': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Quantity take-off retrieval failed: {e}")
        return jsonify({'error': 'Quantity take-off failed', 'details': str(e)}), 500

@bim_router.route('/model-coordination/<project_name>', methods=['GET'])
@require_auth
def get_model_coordination_status(project_name):
    """Get model coordination status across all BIM models"""
    try:
        user_role = request.user_role
        
        # Check project access
        if not rbac.user_can_access_project(user_role, project_name):
            return jsonify({
                'error': 'Access denied',
                'message': 'You do not have access to this project'
            }), 403
        
        # Check BIM access
        role_context = rbac.get_role_context(user_role)
        allowed_docs = role_context.get('allowed_documents', [])
        
        if 'bim' not in allowed_docs and 'all' not in role_context.get('data_access', []):
            return jsonify({
                'error': 'Access denied',
                'message': 'You do not have permission to access BIM models'
            }), 403
        
        # Collect coordination data from knowledge base
        coordination_status = _collect_coordination_status(project_name)
        
        return jsonify({
            'project': project_name,
            'coordination_status': coordination_status,
            'status_date': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Model coordination status failed: {e}")
        return jsonify({'error': 'Model coordination status failed', 'details': str(e)}), 500

@bim_router.route('/elements-summary/<project_name>', methods=['GET'])
@require_auth
def get_elements_summary(project_name):
    """Get summary of BIM elements across all models in a project"""
    try:
        user_role = request.user_role
        
        # Check project access
        if not rbac.user_can_access_project(user_role, project_name):
            return jsonify({
                'error': 'Access denied',
                'message': 'You do not have access to this project'
            }), 403
        
        # Check BIM access
        role_context = rbac.get_role_context(user_role)
        allowed_docs = role_context.get('allowed_documents', [])
        
        if 'bim' not in allowed_docs and 'all' not in role_context.get('data_access', []):
            return jsonify({
                'error': 'Access denied',
                'message': 'You do not have permission to access BIM models'
            }), 403
        
        # Collect elements data from knowledge base
        elements_summary = _collect_elements_summary(project_name)
        
        return jsonify({
            'project': project_name,
            'elements_summary': elements_summary,
            'summary_date': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Elements summary failed: {e}")
        return jsonify({'error': 'Elements summary failed', 'details': str(e)}), 500

@bim_router.route('/model-comparison', methods=['POST'])
@require_auth
def compare_bim_models():
    """Compare two BIM models for differences and coordination issues"""
    try:
        user_role = request.user_role
        data = request.get_json()
        
        if not data or 'model1_path' not in data or 'model2_path' not in data:
            return jsonify({'error': 'model1_path and model2_path are required'}), 400
        
        model1_path = data['model1_path']
        model2_path = data['model2_path']
        project = data.get('project', 'default')
        
        # Check project access
        if not rbac.user_can_access_project(user_role, project):
            return jsonify({
                'error': 'Access denied',
                'message': 'You do not have access to this project'
            }), 403
        
        # Check BIM access
        role_context = rbac.get_role_context(user_role)
        allowed_docs = role_context.get('allowed_documents', [])
        
        if 'bim' not in allowed_docs and 'all' not in role_context.get('data_access', []):
            return jsonify({
                'error': 'Access denied',
                'message': 'You do not have permission to access BIM models'
            }), 403
        
        # Process both models
        model1_analysis = bim_processor.process_bim_file(model1_path, {'project': project})
        model2_analysis = bim_processor.process_bim_file(model2_path, {'project': project})
        
        # Compare models
        comparison_result = _compare_bim_models(model1_analysis, model2_analysis)
        
        return jsonify({
            'project': project,
            'model1': model1_path,
            'model2': model2_path,
            'comparison': comparison_result,
            'comparison_date': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"BIM model comparison failed: {e}")
        return jsonify({'error': 'BIM model comparison failed', 'details': str(e)}), 500

# Helper functions

def _collect_clash_detection_data(project_name: str) -> dict:
    """Collect clash detection data from all BIM models in a project"""
    clash_data = {
        'total_clashes': 0,
        'critical_clashes': 0,
        'resolved_clashes': 0,
        'unresolved_clashes': 0,
        'clash_types': {},
        'models_analyzed': 0,
        'unresolved_details': []
    }
    
    # Scan knowledge base for BIM documents
    for doc_id, doc_info in knowledge_base.document_cache.items():
        if (doc_info['project'] == project_name and 
            doc_info['data'].get('type') == 'bim'):
            
            clash_summary = doc_info['data'].get('clash_detection_summary', {})
            
            clash_data['total_clashes'] += clash_summary.get('total_clashes', 0)
            clash_data['critical_clashes'] += clash_summary.get('critical_clashes', 0)
            clash_data['resolved_clashes'] += clash_summary.get('resolved_clashes', 0)
            clash_data['unresolved_clashes'] += clash_summary.get('unresolved_clashes_count', 0)
            clash_data['models_analyzed'] += 1
            
            # Collect unresolved clash details
            unresolved_details = clash_summary.get('unresolved_clashes_details', [])
            clash_data['unresolved_details'].extend(unresolved_details[:5])  # Limit to 5 per model
            
            # Count clash types
            for clash in unresolved_details:
                clash_type = clash.get('type', 'Unknown')
                clash_data['clash_types'][clash_type] = clash_data['clash_types'].get(clash_type, 0) + 1
    
    return clash_data

def _collect_quantity_takeoff_data(project_name: str) -> dict:
    """Collect quantity take-off data from all BIM models in a project"""
    qto_data = {
        'total_concrete_m3': 0,
        'total_steel_tonnes': 0,
        'total_wall_area_m2': 0,
        'total_floor_area_m2': 0,
        'total_door_count': 0,
        'total_window_count': 0,
        'total_pipe_length_m': 0,
        'models_analyzed': 0,
        'accuracy_estimate': '90%'
    }
    
    # Scan knowledge base for BIM documents
    for doc_id, doc_info in knowledge_base.document_cache.items():
        if (doc_info['project'] == project_name and 
            doc_info['data'].get('type') == 'bim'):
            
            quantities = doc_info['data'].get('quantities_extracted', {})
            
            qto_data['total_concrete_m3'] += quantities.get('concrete_volume_m3', 0)
            qto_data['total_steel_tonnes'] += quantities.get('steel_rebar_tonnes', 0)
            qto_data['total_wall_area_m2'] += quantities.get('wall_area_m2', 0)
            qto_data['total_floor_area_m2'] += quantities.get('floor_area_m2', 0)
            qto_data['total_door_count'] += quantities.get('door_count', 0)
            qto_data['total_window_count'] += quantities.get('window_count', 0)
            qto_data['total_pipe_length_m'] += quantities.get('pipe_length_m', 0)
            qto_data['models_analyzed'] += 1
    
    # Round values for presentation
    for key in qto_data:
        if isinstance(qto_data[key], float):
            qto_data[key] = round(qto_data[key], 2)
    
    return qto_data

def _collect_coordination_status(project_name: str) -> dict:
    """Collect model coordination status from all BIM models in a project"""
    coordination_status = {
        'overall_status': 'Good',
        'models_analyzed': 0,
        'coordination_issues': 0,
        'completeness_scores': [],
        'last_coordination_check': None,
        'recommendations': []
    }
    
    # Scan knowledge base for BIM documents
    for doc_id, doc_info in knowledge_base.document_cache.items():
        if (doc_info['project'] == project_name and 
            doc_info['data'].get('type') == 'bim'):
            
            analysis = doc_info['data'].get('analysis', {})
            
            coordination_status['models_analyzed'] += 1
            
            # Collect completeness scores
            completeness = analysis.get('model_completeness', 'Medium')
            if completeness == 'High':
                coordination_status['completeness_scores'].append(90)
            elif completeness == 'Medium':
                coordination_status['completeness_scores'].append(75)
            else:
                coordination_status['completeness_scores'].append(60)
            
            # Count coordination issues
            potential_issues = analysis.get('potential_issues', [])
            coordination_status['coordination_issues'] += len(potential_issues)
            
            # Update last check date
            last_qa = analysis.get('last_qa_check')
            if last_qa:
                if (not coordination_status['last_coordination_check'] or 
                    last_qa > coordination_status['last_coordination_check']):
                    coordination_status['last_coordination_check'] = last_qa
    
    # Calculate overall status
    if coordination_status['completeness_scores']:
        avg_completeness = sum(coordination_status['completeness_scores']) / len(coordination_status['completeness_scores'])
        if avg_completeness >= 85:
            coordination_status['overall_status'] = 'Excellent'
        elif avg_completeness >= 75:
            coordination_status['overall_status'] = 'Good'
        elif avg_completeness >= 65:
            coordination_status['overall_status'] = 'Fair'
        else:
            coordination_status['overall_status'] = 'Poor'
    
    # Generate recommendations
    if coordination_status['coordination_issues'] > 5:
        coordination_status['recommendations'].append('Address coordination issues immediately')
    if coordination_status['overall_status'] in ['Fair', 'Poor']:
        coordination_status['recommendations'].append('Improve model completeness and coordination')
    
    return coordination_status

def _collect_elements_summary(project_name: str) -> dict:
    """Collect elements summary from all BIM models in a project"""
    elements_summary = {
        'total_walls': 0,
        'total_slabs': 0,
        'total_beams': 0,
        'total_columns': 0,
        'total_doors': 0,
        'total_windows': 0,
        'total_pipes': 0,
        'total_ducts': 0,
        'total_equipment': 0,
        'total_foundations': 0,
        'total_spaces': 0,
        'models_analyzed': 0
    }
    
    # Scan knowledge base for BIM documents
    for doc_id, doc_info in knowledge_base.document_cache.items():
        if (doc_info['project'] == project_name and 
            doc_info['data'].get('type') == 'bim'):
            
            elements = doc_info['data'].get('elements_summary', {})
            
            elements_summary['total_walls'] += elements.get('walls', 0)
            elements_summary['total_slabs'] += elements.get('slabs', 0)
            elements_summary['total_beams'] += elements.get('beams', 0)
            elements_summary['total_columns'] += elements.get('columns', 0)
            elements_summary['total_doors'] += elements.get('doors', 0)
            elements_summary['total_windows'] += elements.get('windows', 0)
            elements_summary['total_pipes'] += elements.get('pipes', 0)
            elements_summary['total_ducts'] += elements.get('ducts', 0)
            elements_summary['total_equipment'] += elements.get('equipment', 0)
            elements_summary['total_foundations'] += elements.get('foundations', 0)
            elements_summary['total_spaces'] += elements.get('spaces', 0)
            elements_summary['models_analyzed'] += 1
    
    return elements_summary

def _compare_bim_models(model1_analysis: dict, model2_analysis: dict) -> dict:
    """Compare two BIM model analyses"""
    comparison = {
        'elements_comparison': {},
        'quantities_comparison': {},
        'clash_comparison': {},
        'differences_summary': []
    }
    
    # Compare elements
    elements1 = model1_analysis.get('elements_summary', {})
    elements2 = model2_analysis.get('elements_summary', {})
    
    for element_type in set(list(elements1.keys()) + list(elements2.keys())):
        count1 = elements1.get(element_type, 0)
        count2 = elements2.get(element_type, 0)
        difference = count2 - count1
        
        comparison['elements_comparison'][element_type] = {
            'model1_count': count1,
            'model2_count': count2,
            'difference': difference,
            'percentage_change': (difference / count1 * 100) if count1 > 0 else 0
        }
        
        if abs(difference) > 0:
            comparison['differences_summary'].append(
                f"{element_type.title()}: {difference:+d} elements ({difference/count1*100:+.1f}%)" if count1 > 0 
                else f"{element_type.title()}: {difference:+d} elements"
            )
    
    # Compare quantities
    quantities1 = model1_analysis.get('quantities_extracted', {})
    quantities2 = model2_analysis.get('quantities_extracted', {})
    
    for quantity_type in set(list(quantities1.keys()) + list(quantities2.keys())):
        value1 = quantities1.get(quantity_type, 0)
        value2 = quantities2.get(quantity_type, 0)
        difference = value2 - value1
        
        comparison['quantities_comparison'][quantity_type] = {
            'model1_value': value1,
            'model2_value': value2,
            'difference': difference,
            'percentage_change': (difference / value1 * 100) if value1 > 0 else 0
        }
    
    # Compare clashes
    clashes1 = model1_analysis.get('clash_detection_summary', {})
    clashes2 = model2_analysis.get('clash_detection_summary', {})
    
    comparison['clash_comparison'] = {
        'model1_total_clashes': clashes1.get('total_clashes', 0),
        'model2_total_clashes': clashes2.get('total_clashes', 0),
        'clash_difference': clashes2.get('total_clashes', 0) - clashes1.get('total_clashes', 0)
    }
    
    return comparison

