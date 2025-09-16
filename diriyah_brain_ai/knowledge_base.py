"""
AI Knowledge Base Integration for Diriyah Brain AI
Integrates processed document data into AI responses for enhanced intelligence
"""
import json
import logging
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
from collections import defaultdict
import re

logger = logging.getLogger(__name__)

class AIKnowledgeBase:
    """
    Centralized knowledge base that integrates all processed document data
    to provide enhanced AI responses with contextual insights
    """
    
    def __init__(self):
        self.document_cache = {}
        self.project_insights = defaultdict(dict)
        self.user_context = {}
        self.analysis_patterns = self._initialize_analysis_patterns()
        
    def _initialize_analysis_patterns(self) -> Dict[str, Any]:
        """Initialize patterns for analyzing different types of construction data"""
        return {
            'schedule_patterns': {
                'delay_indicators': ['behind schedule', 'delayed', 'overdue', 'late', 'postponed'],
                'progress_indicators': ['completed', 'finished', 'done', 'achieved', 'delivered'],
                'risk_indicators': ['risk', 'issue', 'problem', 'concern', 'critical']
            },
            'financial_patterns': {
                'cost_overrun': ['over budget', 'exceeded', 'overrun', 'additional cost'],
                'savings': ['under budget', 'savings', 'reduced cost', 'cost effective'],
                'payment_issues': ['payment delay', 'invoice pending', 'cash flow']
            },
            'quality_patterns': {
                'defects': ['defect', 'non-conformance', 'ncr', 'rework', 'rejection'],
                'compliance': ['compliant', 'approved', 'accepted', 'passed inspection'],
                'standards': ['astm', 'bs', 'saso', 'specification', 'standard']
            },
            'safety_patterns': {
                'incidents': ['accident', 'incident', 'injury', 'near miss', 'unsafe'],
                'compliance': ['safety compliant', 'ppe', 'safety training', 'hazard control'],
                'violations': ['violation', 'non-compliance', 'unsafe practice']
            }
        }
    
    def integrate_document(self, document_data: Dict[str, Any], project_name: str) -> Dict[str, Any]:
        """
        Integrate processed document data into the knowledge base
        
        Args:
            document_data: Processed document data from document_processor
            project_name: Name of the project this document belongs to
            
        Returns:
            Integration summary with extracted insights
        """
        try:
            doc_id = self._generate_document_id(document_data)
            
            # Store document in cache
            self.document_cache[doc_id] = {
                'data': document_data,
                'project': project_name,
                'integrated_at': datetime.now().isoformat(),
                'insights': {}
            }
            
            # Extract and store insights
            insights = self._extract_insights(document_data, project_name)
            self.document_cache[doc_id]['insights'] = insights
            
            # Update project-level insights
            self._update_project_insights(project_name, insights, document_data)
            
            logger.info(f"Integrated document {doc_id} for project {project_name}")
            
            return {
                'document_id': doc_id,
                'insights_extracted': len(insights),
                'project_insights_updated': True,
                'integration_status': 'success'
            }
            
        except Exception as e:
            logger.error(f"Failed to integrate document: {e}")
            return {'integration_status': 'failed', 'error': str(e)}
    
    def get_contextual_response_data(self, query: str, project: str, user_role: str) -> Dict[str, Any]:
        """
        Get contextual data to enhance AI responses based on query, project, and user role
        
        Args:
            query: User's query
            project: Project name
            user_role: User's role for access control
            
        Returns:
            Contextual data for AI response enhancement
        """
        try:
            # Analyze query to understand intent
            query_analysis = self._analyze_query(query)
            
            # Get relevant documents
            relevant_docs = self._find_relevant_documents(query, project, user_role)
            
            # Get project insights
            project_insights = self.project_insights.get(project, {})
            
            # Generate contextual insights
            contextual_insights = self._generate_contextual_insights(
                query_analysis, relevant_docs, project_insights, user_role
            )
            
            return {
                'query_analysis': query_analysis,
                'relevant_documents': relevant_docs,
                'project_insights': project_insights,
                'contextual_insights': contextual_insights,
                'confidence_score': self._calculate_confidence_score(relevant_docs, query_analysis)
            }
            
        except Exception as e:
            logger.error(f"Failed to get contextual response data: {e}")
            return {'error': str(e)}
    
    def _generate_document_id(self, document_data: Dict[str, Any]) -> str:
        """Generate unique document ID"""
        file_path = document_data.get('file_path', 'unknown')
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        return f"doc_{hash(file_path)}_{timestamp}"
    
    def _extract_insights(self, document_data: Dict[str, Any], project_name: str) -> Dict[str, Any]:
        """Extract actionable insights from processed document data"""
        insights = {
            'document_type': document_data.get('type', 'unknown'),
            'key_findings': [],
            'risks_identified': [],
            'opportunities': [],
            'compliance_status': {},
            'financial_impact': {},
            'schedule_impact': {},
            'quality_indicators': {},
            'safety_indicators': {}
        }
        
        # Get document analysis
        analysis = document_data.get('analysis', {})
        text_content = document_data.get('text_content', '')
        
        # Extract insights based on document type
        doc_type = document_data.get('type', '')
        
        if doc_type == 'pdf' and analysis:
            insights.update(self._extract_pdf_insights(analysis, text_content))
        elif doc_type == 'excel' and 'sheets' in document_data:
            insights.update(self._extract_excel_insights(document_data['sheets']))
        elif doc_type == 'cad' and 'entities' in document_data:
            insights.update(self._extract_cad_insights(document_data))
        elif doc_type == 'image':
            insights.update(self._extract_image_insights(analysis))
        elif doc_type == 'video':
            insights.update(self._extract_video_insights(analysis))
        
        # Apply pattern matching for construction-specific insights
        insights.update(self._apply_pattern_matching(text_content))
        
        return insights
    
    def _extract_pdf_insights(self, analysis: Dict[str, Any], text_content: str) -> Dict[str, Any]:
        """Extract insights from PDF documents"""
        insights = {}
        
        doc_category = analysis.get('document_category', 'unknown')
        
        if doc_category == 'boq':
            insights['financial_impact'] = {
                'type': 'bill_of_quantities',
                'estimated_value': self._extract_boq_value(text_content),
                'line_items': self._count_boq_items(text_content)
            }
        elif doc_category == 'schedule':
            insights['schedule_impact'] = {
                'type': 'project_schedule',
                'critical_path_items': self._extract_critical_path(text_content),
                'milestones': self._extract_milestones(text_content)
            }
        elif doc_category == 'rfi':
            insights['risks_identified'] = self._extract_rfi_risks(text_content)
        elif doc_category == 'ncr':
            insights['quality_indicators'] = self._extract_ncr_quality_issues(text_content)
        
        return insights
    
    def _extract_excel_insights(self, sheets: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Extract insights from Excel/CSV data"""
        insights = {}
        
        for sheet in sheets:
            columns = sheet.get('column_names', [])
            
            # Check for financial data
            if any(col.lower() in ['amount', 'cost', 'price', 'value'] for col in columns):
                insights['financial_impact'] = {
                    'type': 'financial_data',
                    'data_points': sheet.get('rows', 0)
                }
            
            # Check for schedule data
            if any(col.lower() in ['date', 'start', 'finish', 'duration'] for col in columns):
                insights['schedule_impact'] = {
                    'type': 'schedule_data',
                    'activities': sheet.get('rows', 0)
                }
        
        return insights
    
    def _extract_cad_insights(self, cad_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract insights from CAD files"""
        insights = {}
        
        entities = cad_data.get('entities', [])
        layers = cad_data.get('layers', [])
        
        insights['technical_details'] = {
            'type': 'cad_drawing',
            'entity_count': len(entities),
            'layer_count': len(layers),
            'drawing_complexity': 'high' if len(entities) > 1000 else 'medium' if len(entities) > 100 else 'low'
        }
        
        # Extract text annotations for additional insights
        text_entities = [e for e in entities if e.get('type') == 'TEXT']
        if text_entities:
            annotations = [e.get('text', '') for e in text_entities]
            insights['annotations'] = annotations[:10]  # Limit to first 10
        
        return insights
    
    def _extract_image_insights(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Extract insights from image analysis"""
        insights = {}
        
        if 'progress_stage' in analysis:
            insights['progress_indicators'] = {
                'type': 'visual_progress',
                'stage': analysis['progress_stage'],
                'confidence': analysis.get('confidence', 0)
            }
        
        if 'qa_issues' in analysis:
            insights['quality_indicators'] = {
                'type': 'visual_inspection',
                'issues_detected': len(analysis['qa_issues']),
                'critical_issues': [issue for issue in analysis['qa_issues'] if issue.get('severity') == 'high']
            }
        
        return insights
    
    def _extract_video_insights(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Extract insights from video analysis"""
        insights = {}
        
        if 'events_detected' in analysis:
            insights['activity_indicators'] = {
                'type': 'video_analysis',
                'events_count': len(analysis['events_detected']),
                'activity_level': analysis.get('activity_level', 'unknown')
            }
        
        return insights
    
    def _apply_pattern_matching(self, text_content: str) -> Dict[str, Any]:
        """Apply pattern matching to extract construction-specific insights"""
        insights = {}
        text_lower = text_content.lower()
        
        # Schedule pattern matching
        schedule_risks = []
        for pattern in self.analysis_patterns['schedule_patterns']['delay_indicators']:
            if pattern in text_lower:
                schedule_risks.append(f"Potential delay indicator: {pattern}")
        
        if schedule_risks:
            insights['schedule_risks'] = schedule_risks
        
        # Financial pattern matching
        financial_alerts = []
        for pattern in self.analysis_patterns['financial_patterns']['cost_overrun']:
            if pattern in text_lower:
                financial_alerts.append(f"Cost overrun indicator: {pattern}")
        
        if financial_alerts:
            insights['financial_alerts'] = financial_alerts
        
        # Quality pattern matching
        quality_issues = []
        for pattern in self.analysis_patterns['quality_patterns']['defects']:
            if pattern in text_lower:
                quality_issues.append(f"Quality issue: {pattern}")
        
        if quality_issues:
            insights['quality_issues'] = quality_issues
        
        # Safety pattern matching
        safety_concerns = []
        for pattern in self.analysis_patterns['safety_patterns']['incidents']:
            if pattern in text_lower:
                safety_concerns.append(f"Safety concern: {pattern}")
        
        if safety_concerns:
            insights['safety_concerns'] = safety_concerns
        
        return insights
    
    def _update_project_insights(self, project_name: str, insights: Dict[str, Any], document_data: Dict[str, Any]):
        """Update project-level insights with new document insights"""
        if project_name not in self.project_insights:
            self.project_insights[project_name] = {
                'documents_processed': 0,
                'last_updated': datetime.now().isoformat(),
                'risk_summary': {},
                'progress_summary': {},
                'financial_summary': {},
                'quality_summary': {},
                'safety_summary': {}
            }
        
        project_data = self.project_insights[project_name]
        project_data['documents_processed'] += 1
        project_data['last_updated'] = datetime.now().isoformat()
        
        # Aggregate risks
        if 'risks_identified' in insights:
            if 'total_risks' not in project_data['risk_summary']:
                project_data['risk_summary']['total_risks'] = 0
            project_data['risk_summary']['total_risks'] += len(insights['risks_identified'])
        
        # Aggregate financial data
        if 'financial_impact' in insights:
            project_data['financial_summary']['last_financial_update'] = datetime.now().isoformat()
            if 'estimated_value' in insights['financial_impact']:
                project_data['financial_summary']['latest_estimate'] = insights['financial_impact']['estimated_value']
        
        # Aggregate quality data
        if 'quality_indicators' in insights:
            if 'quality_issues' not in project_data['quality_summary']:
                project_data['quality_summary']['quality_issues'] = 0
            project_data['quality_summary']['quality_issues'] += 1
        
        # Aggregate safety data
        if 'safety_indicators' in insights:
            if 'safety_incidents' not in project_data['safety_summary']:
                project_data['safety_summary']['safety_incidents'] = 0
            project_data['safety_summary']['safety_incidents'] += 1
    
    def _analyze_query(self, query: str) -> Dict[str, Any]:
        """Analyze user query to understand intent and extract keywords"""
        query_lower = query.lower()
        
        analysis = {
            'intent': 'general',
            'keywords': [],
            'document_types_requested': [],
            'data_categories': [],
            'urgency': 'normal'
        }
        
        # Detect intent
        if any(word in query_lower for word in ['cost', 'budget', 'financial', 'payment', 'invoice']):
            analysis['intent'] = 'financial'
            analysis['data_categories'].append('financial')
        elif any(word in query_lower for word in ['schedule', 'timeline', 'delay', 'milestone']):
            analysis['intent'] = 'schedule'
            analysis['data_categories'].append('schedule')
        elif any(word in query_lower for word in ['quality', 'defect', 'ncr', 'inspection']):
            analysis['intent'] = 'quality'
            analysis['data_categories'].append('quality')
        elif any(word in query_lower for word in ['safety', 'incident', 'hazard', 'ppe']):
            analysis['intent'] = 'safety'
            analysis['data_categories'].append('safety')
        elif any(word in query_lower for word in ['progress', 'status', 'completion']):
            analysis['intent'] = 'progress'
            analysis['data_categories'].append('progress')
        
        # Detect document types
        if 'boq' in query_lower or 'bill of quantities' in query_lower:
            analysis['document_types_requested'].append('boq')
        if 'schedule' in query_lower or 'gantt' in query_lower:
            analysis['document_types_requested'].append('schedule')
        if 'rfi' in query_lower:
            analysis['document_types_requested'].append('rfi')
        if 'ncr' in query_lower:
            analysis['document_types_requested'].append('ncr')
        if 'contract' in query_lower:
            analysis['document_types_requested'].append('contract')
        
        # Detect urgency
        if any(word in query_lower for word in ['urgent', 'critical', 'immediate', 'asap']):
            analysis['urgency'] = 'high'
        elif any(word in query_lower for word in ['when convenient', 'later', 'eventually']):
            analysis['urgency'] = 'low'
        
        # Extract keywords (simple approach)
        words = re.findall(r'\b\w+\b', query_lower)
        analysis['keywords'] = [word for word in words if len(word) > 3 and word not in ['what', 'when', 'where', 'how', 'the', 'and', 'or']]
        
        return analysis
    
    def _find_relevant_documents(self, query: str, project: str, user_role: str) -> List[Dict[str, Any]]:
        """Find documents relevant to the query, project, and user role"""
        relevant_docs = []
        
        query_analysis = self._analyze_query(query)
        
        for doc_id, doc_info in self.document_cache.items():
            if doc_info['project'] != project:
                continue
            
            # Check if user can access this document type
            if not self._user_can_access_document_type(user_role, doc_info['data']):
                continue
            
            # Calculate relevance score
            relevance_score = self._calculate_document_relevance(
                doc_info, query_analysis
            )
            
            if relevance_score > 0.3:  # Threshold for relevance
                relevant_docs.append({
                    'document_id': doc_id,
                    'document_data': doc_info['data'],
                    'insights': doc_info['insights'],
                    'relevance_score': relevance_score
                })
        
        # Sort by relevance score
        relevant_docs.sort(key=lambda x: x['relevance_score'], reverse=True)
        
        return relevant_docs[:5]  # Return top 5 most relevant documents
    
    def _calculate_document_relevance(self, doc_info: Dict[str, Any], query_analysis: Dict[str, Any]) -> float:
        """Calculate how relevant a document is to the query"""
        score = 0.0
        
        doc_data = doc_info['data']
        doc_analysis = doc_data.get('analysis', {})
        
        # Match document type with query intent
        doc_category = doc_analysis.get('document_category', '')
        if query_analysis['intent'] == 'financial' and doc_category in ['boq', 'contract', 'financial']:
            score += 0.5
        elif query_analysis['intent'] == 'schedule' and doc_category in ['schedule', 'mom']:
            score += 0.5
        elif query_analysis['intent'] == 'quality' and doc_category in ['ncr', 'rfi', 'inspection']:
            score += 0.5
        elif query_analysis['intent'] == 'safety' and doc_category in ['safety', 'incident']:
            score += 0.5
        
        # Match keywords in document content
        text_content = doc_data.get('text_content', '').lower()
        keyword_matches = sum(1 for keyword in query_analysis['keywords'] if keyword in text_content)
        score += (keyword_matches / max(len(query_analysis['keywords']), 1)) * 0.3
        
        # Boost score for recent documents
        try:
            integrated_at = datetime.fromisoformat(doc_info['integrated_at'])
            days_old = (datetime.now() - integrated_at).days
            if days_old < 7:
                score += 0.2
            elif days_old < 30:
                score += 0.1
        except:
            pass
        
        return min(score, 1.0)  # Cap at 1.0
    
    def _user_can_access_document_type(self, user_role: str, document_data: Dict[str, Any]) -> bool:
        """Check if user role can access this document type"""
        # Import RBAC here to avoid circular imports
        from diriyah_brain_ai.auth import rbac
        
        role_context = rbac.get_role_context(user_role)
        allowed_docs = role_context.get('allowed_documents', [])
        
        if 'all' in role_context.get('data_access', []):
            return True
        
        doc_analysis = document_data.get('analysis', {})
        doc_category = doc_analysis.get('document_category', 'unknown')
        
        return doc_category in allowed_docs
    
    def _generate_contextual_insights(self, query_analysis: Dict[str, Any], 
                                    relevant_docs: List[Dict[str, Any]], 
                                    project_insights: Dict[str, Any], 
                                    user_role: str) -> Dict[str, Any]:
        """Generate contextual insights for AI response enhancement"""
        insights = {
            'summary': '',
            'key_points': [],
            'recommendations': [],
            'alerts': [],
            'data_sources': []
        }
        
        # Generate summary based on query intent
        if query_analysis['intent'] == 'financial':
            insights['summary'] = self._generate_financial_summary(relevant_docs, project_insights)
        elif query_analysis['intent'] == 'schedule':
            insights['summary'] = self._generate_schedule_summary(relevant_docs, project_insights)
        elif query_analysis['intent'] == 'quality':
            insights['summary'] = self._generate_quality_summary(relevant_docs, project_insights)
        elif query_analysis['intent'] == 'safety':
            insights['summary'] = self._generate_safety_summary(relevant_docs, project_insights)
        else:
            insights['summary'] = self._generate_general_summary(relevant_docs, project_insights)
        
        # Extract key points from relevant documents
        for doc in relevant_docs:
            doc_insights = doc['insights']
            if 'key_findings' in doc_insights:
                insights['key_points'].extend(doc_insights['key_findings'])
            
            # Add data source
            file_name = doc['document_data'].get('google_drive_metadata', {}).get('name', 'Unknown')
            insights['data_sources'].append(file_name)
        
        # Generate recommendations based on role
        insights['recommendations'] = self._generate_role_based_recommendations(
            user_role, query_analysis, relevant_docs
        )
        
        # Generate alerts
        insights['alerts'] = self._generate_alerts(relevant_docs, project_insights)
        
        return insights
    
    def _generate_financial_summary(self, relevant_docs: List[Dict[str, Any]], 
                                  project_insights: Dict[str, Any]) -> str:
        """Generate financial summary from relevant documents"""
        financial_data = []
        
        for doc in relevant_docs:
            insights = doc['insights']
            if 'financial_impact' in insights:
                financial_data.append(insights['financial_impact'])
        
        if not financial_data:
            return "No recent financial data available."
        
        return f"Financial analysis based on {len(financial_data)} documents shows current project financial status."
    
    def _generate_schedule_summary(self, relevant_docs: List[Dict[str, Any]], 
                                 project_insights: Dict[str, Any]) -> str:
        """Generate schedule summary from relevant documents"""
        schedule_data = []
        
        for doc in relevant_docs:
            insights = doc['insights']
            if 'schedule_impact' in insights:
                schedule_data.append(insights['schedule_impact'])
        
        if not schedule_data:
            return "No recent schedule data available."
        
        return f"Schedule analysis based on {len(schedule_data)} documents shows current project timeline status."
    
    def _generate_quality_summary(self, relevant_docs: List[Dict[str, Any]], 
                                project_insights: Dict[str, Any]) -> str:
        """Generate quality summary from relevant documents"""
        quality_issues = 0
        
        for doc in relevant_docs:
            insights = doc['insights']
            if 'quality_indicators' in insights:
                quality_issues += 1
        
        return f"Quality analysis shows {quality_issues} quality-related documents in recent activity."
    
    def _generate_safety_summary(self, relevant_docs: List[Dict[str, Any]], 
                               project_insights: Dict[str, Any]) -> str:
        """Generate safety summary from relevant documents"""
        safety_items = 0
        
        for doc in relevant_docs:
            insights = doc['insights']
            if 'safety_indicators' in insights:
                safety_items += 1
        
        return f"Safety analysis shows {safety_items} safety-related items in recent documentation."
    
    def _generate_general_summary(self, relevant_docs: List[Dict[str, Any]], 
                                project_insights: Dict[str, Any]) -> str:
        """Generate general summary from relevant documents"""
        return f"Analysis based on {len(relevant_docs)} relevant project documents."
    
    def _generate_role_based_recommendations(self, user_role: str, query_analysis: Dict[str, Any], 
                                           relevant_docs: List[Dict[str, Any]]) -> List[str]:
        """Generate recommendations based on user role and context"""
        recommendations = []
        
        if user_role == 'ceo':
            recommendations.append("Review strategic implications of current project status")
            recommendations.append("Consider resource allocation optimization")
        elif user_role == 'director':
            recommendations.append("Monitor key performance indicators")
            recommendations.append("Ensure milestone alignment with strategic objectives")
        elif user_role == 'site_manager':
            recommendations.append("Focus on operational efficiency")
            recommendations.append("Maintain safety compliance standards")
        elif user_role == 'engineer':
            recommendations.append("Review technical specifications")
            recommendations.append("Ensure quality standards compliance")
        
        return recommendations
    
    def _generate_alerts(self, relevant_docs: List[Dict[str, Any]], 
                        project_insights: Dict[str, Any]) -> List[str]:
        """Generate alerts based on document analysis"""
        alerts = []
        
        for doc in relevant_docs:
            insights = doc['insights']
            
            if 'risks_identified' in insights and insights['risks_identified']:
                alerts.append(f"⚠️ Risk identified in {doc['document_data'].get('type', 'document')}")
            
            if 'schedule_risks' in insights and insights['schedule_risks']:
                alerts.append("⚠️ Schedule risk detected")
            
            if 'financial_alerts' in insights and insights['financial_alerts']:
                alerts.append("⚠️ Financial concern identified")
            
            if 'quality_issues' in insights and insights['quality_issues']:
                alerts.append("⚠️ Quality issue detected")
            
            if 'safety_concerns' in insights and insights['safety_concerns']:
                alerts.append("⚠️ Safety concern identified")
        
        return alerts[:3]  # Limit to top 3 alerts
    
    def _calculate_confidence_score(self, relevant_docs: List[Dict[str, Any]], 
                                  query_analysis: Dict[str, Any]) -> float:
        """Calculate confidence score for the response"""
        if not relevant_docs:
            return 0.2
        
        # Base confidence on number and relevance of documents
        avg_relevance = sum(doc['relevance_score'] for doc in relevant_docs) / len(relevant_docs)
        doc_count_factor = min(len(relevant_docs) / 3, 1.0)  # Optimal around 3 documents
        
        confidence = (avg_relevance * 0.7) + (doc_count_factor * 0.3)
        
        return min(confidence, 0.95)  # Cap at 95%
    
    # Helper methods for specific data extraction
    def _extract_boq_value(self, text: str) -> Optional[float]:
        """Extract total value from BOQ text"""
        # Simple pattern matching for total amounts
        import re
        patterns = [
            r'total[:\s]+([0-9,]+\.?[0-9]*)',
            r'amount[:\s]+([0-9,]+\.?[0-9]*)',
            r'([0-9,]+\.?[0-9]*)\s*total'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text.lower())
            if match:
                try:
                    value_str = match.group(1).replace(',', '')
                    return float(value_str)
                except:
                    continue
        return None
    
    def _count_boq_items(self, text: str) -> int:
        """Count line items in BOQ"""
        lines = text.split('\n')
        item_count = 0
        for line in lines:
            if re.match(r'^\d+\.?\d*', line.strip()):
                item_count += 1
        return item_count
    
    def _extract_critical_path(self, text: str) -> List[str]:
        """Extract critical path items from schedule text"""
        critical_items = []
        lines = text.split('\n')
        
        for line in lines:
            if 'critical' in line.lower():
                critical_items.append(line.strip())
        
        return critical_items[:5]  # Limit to 5 items
    
    def _extract_milestones(self, text: str) -> List[str]:
        """Extract milestones from schedule text"""
        milestones = []
        lines = text.split('\n')
        
        for line in lines:
            if any(word in line.lower() for word in ['milestone', 'completion', 'delivery', 'phase']):
                milestones.append(line.strip())
        
        return milestones[:5]  # Limit to 5 milestones
    
    def _extract_rfi_risks(self, text: str) -> List[str]:
        """Extract risks from RFI text"""
        risks = []
        
        if 'conflict' in text.lower():
            risks.append("Design conflict identified")
        if 'clarification' in text.lower():
            risks.append("Specification clarification needed")
        if 'urgent' in text.lower():
            risks.append("Urgent response required")
        
        return risks
    
    def _extract_ncr_quality_issues(self, text: str) -> Dict[str, Any]:
        """Extract quality issues from NCR text"""
        issues = {
            'severity': 'medium',
            'category': 'general',
            'corrective_action_required': True
        }
        
        if 'critical' in text.lower() or 'major' in text.lower():
            issues['severity'] = 'high'
        elif 'minor' in text.lower():
            issues['severity'] = 'low'
        
        if 'concrete' in text.lower():
            issues['category'] = 'concrete'
        elif 'steel' in text.lower():
            issues['category'] = 'steel'
        elif 'safety' in text.lower():
            issues['category'] = 'safety'
        
        return issues

# Global instance
knowledge_base = AIKnowledgeBase()

