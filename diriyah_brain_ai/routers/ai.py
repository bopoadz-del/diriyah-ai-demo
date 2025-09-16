"""
AI router for Diriyah Brain AI with RBAC and document integration
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
import random
import os
from datetime import datetime, timedelta
from diriyah_brain_ai.google_drive_client import google_drive_client
from diriyah_brain_ai.knowledge_base import knowledge_base

# OpenAI integration
try:
    import openai
    openai.api_key = os.getenv("OPENAI_API_KEY")
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

router = APIRouter(prefix="/api/ai", tags=["ai"])

class ChatRequest(BaseModel):
    message: str
    project: str = "Heritage Resort"
    language: str = "en"

class ChatResponse(BaseModel):
    response: str
    project: str
    language: str
    timestamp: str

@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    """AI chat endpoint with role-based access control and document integration"""
    try:
        message = request.message
        project = request.project
        language = request.language
        
        if not message:
            raise HTTPException(status_code=400, detail="Message is required")
        
        # For now, assume user role (will be implemented with proper auth later)
        user_role = "engineer"  # Default role for testing
        user_projects = ["Heritage Resort"]  # Default project access for testing
        
        # Check if user has access to the requested project
        if 'all' not in user_projects and project.lower().replace(' ', '_') not in user_projects:
            raise HTTPException(
                status_code=403,
                detail={
                    'error': 'Access denied',
                    'message': 'You do not have access to this project'
                }
            )
        
        # Search for relevant documents based on the query
        relevant_docs = []
        contextual_data = {}
        try:
            search_results = google_drive_client.search_documents(message, None)
            # Filter results based on user role and integrate into knowledge base
            for doc in search_results[:3]:  # Limit to top 3 results
                if _user_can_access_document(user_role, doc):
                    # Integrate document into knowledge base
                    integration_result = knowledge_base.integrate_document(doc, project)
                    relevant_docs.append(doc)
            
            # Get enhanced contextual data from knowledge base
            contextual_data = knowledge_base.get_contextual_response_data(message, project, user_role)
            
        except Exception as e:
            print(f"Document search and knowledge base integration failed: {e}")
        
        # Generate role-aware AI response with enhanced context
        response = generate_enhanced_role_aware_response(
            message, project, user_role, relevant_docs, contextual_data
        )
        
        # Get appropriate citations
        citations = get_role_appropriate_citations(user_role, relevant_docs)
        
        return ChatResponse(
            response=response,
            project=project,
            language=language,
            timestamp=datetime.now().isoformat()
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat failed: {str(e)}")

def generate_enhanced_role_aware_response(message: str, project: str, user_role: str, 
                                        relevant_docs: list, contextual_data: dict) -> str:
    """Generate enhanced AI response using knowledge base insights"""
    # Detect language
    is_arabic = any('\u0600' <= char <= '\u06FF' for char in message)
    
    # Get role-specific context
    role_context = rbac.get_role_context(user_role)
    allowed_docs = role_context.get('allowed_documents', [])
    
    # Check for restricted information requests
    restricted_keywords = {
        'quotes': ['quote', 'quotation', 'pricing', 'cost', 'price', 'budget', 'financial'],
        'commercial': ['commercial', 'contract value', 'payment', 'invoice', 'profit', 'margin'],
        'financials': ['financial', 'budget', 'expenditure', 'profit', 'revenue', 'cash flow'],
        'contracts': ['contract terms', 'agreement details', 'legal terms', 'conditions']
    }
    
    message_lower = message.lower()
    
    # Check for restricted content requests
    for doc_type, keywords in restricted_keywords.items():
        if any(keyword in message_lower for keyword in keywords):
            if doc_type not in allowed_docs and 'all' not in role_context.get('data_access', []):
                if is_arabic:
                    return f"🔒 عذراً، ليس لديك صلاحية للوصول إلى المعلومات التجارية والمالية. يرجى التواصل مع المدير التجاري أو الإدارة العليا للحصول على هذه المعلومات."
                else:
                    return f"🔒 Sorry, you don't have permission to access {doc_type} information. Please contact the Commercial Manager or senior management for this information."
    
    # Use contextual insights from knowledge base
    contextual_insights = contextual_data.get('contextual_insights', {})
    query_analysis = contextual_data.get('query_analysis', {})
    
    # Build enhanced context
    enhanced_context = ""
    if contextual_insights.get('summary'):
        enhanced_context += f" {contextual_insights['summary']}"
    
    # Add alerts if any
    alerts = contextual_insights.get('alerts', [])
    if alerts:
        alert_text = " ".join(alerts)
        enhanced_context += f" {alert_text}"
    
    # Add recommendations for the role
    recommendations = contextual_insights.get('recommendations', [])
    if recommendations and user_role in ['ceo', 'director']:
        rec_text = recommendations[0] if recommendations else ""
        enhanced_context += f" Recommendation: {rec_text}"
    
    # Generate role-appropriate responses with enhanced context
    if user_role == 'ceo':
        return generate_enhanced_ceo_response(message, project, is_arabic, enhanced_context, contextual_insights)
    elif user_role == 'director':
        return generate_enhanced_director_response(message, project, is_arabic, enhanced_context, contextual_insights)
    elif user_role == 'site_manager':
        return generate_enhanced_site_manager_response(message, project, is_arabic, enhanced_context, contextual_insights)
    elif user_role == 'engineer':
        return generate_enhanced_engineer_response(message, project, is_arabic, enhanced_context, contextual_insights)
    elif user_role == 'commercial_manager':
        return generate_enhanced_commercial_response(message, project, is_arabic, enhanced_context, contextual_insights)
    else:
        return generate_general_response(message, project, is_arabic, enhanced_context)

def generate_enhanced_ceo_response(message: str, project: str, is_arabic: bool, 
                                 enhanced_context: str, insights: dict) -> str:
    """Generate enhanced CEO-level response with knowledge base insights"""
    confidence = insights.get('confidence_score', 0.5)
    data_sources = insights.get('data_sources', [])
    
    if is_arabic:
        base_responses = [
            f"📊 نظرة شاملة: مشروع {project} - إجمالي القيمة: 45.2 مليون ريال، الإنفاق: 72%، الربح المتوقع: 8.5 مليون ريال.",
            f"💼 تقرير تنفيذي: {project} يسير وفق الخطة الاستراتيجية. المخاطر المالية منخفضة، العائد على الاستثمار 18.5%.",
            f"🎯 الأداء الاستراتيجي: {project} حقق 95% من الأهداف المرحلية. التوقعات المالية تشير لتجاوز الأرباح المستهدفة بنسبة 12%."
        ]
    else:
        base_responses = [
            f"📊 Executive Overview: {project} - Total value: SAR 45.2M, expenditure: 72%, projected profit: SAR 8.5M.",
            f"💼 Strategic Report: {project} is aligned with strategic objectives. Financial risk is low, ROI at 18.5%.",
            f"🎯 Performance Summary: {project} achieved 95% of milestone targets. Financial projections indicate 12% profit margin above target."
        ]
    
    response = random.choice(base_responses)
    
    # Add enhanced context
    if enhanced_context:
        response += enhanced_context
    
    # Add confidence indicator for CEO
    if confidence > 0.8:
        confidence_text = " High confidence analysis." if not is_arabic else " تحليل عالي الثقة."
    elif confidence > 0.6:
        confidence_text = " Moderate confidence analysis." if not is_arabic else " تحليل متوسط الثقة."
    else:
        confidence_text = " Limited data available." if not is_arabic else " بيانات محدودة متاحة."
    
    response += confidence_text
    
    return response

def generate_enhanced_director_response(message: str, project: str, is_arabic: bool, 
                                      enhanced_context: str, insights: dict) -> str:
    """Generate enhanced Director-level response with knowledge base insights"""
    if is_arabic:
        base_responses = [
            f"📋 تقرير إداري: {project} - التقدم العام 78%، المعالم الرئيسية محققة. المخاطر التشغيلية تحت السيطرة.",
            f"⚡ حالة المشروع: {project} يواجه تحدي بسيط في الجدولة. الميزانية ضمن الحدود المقررة.",
            f"🔍 مراجعة استراتيجية: {project} يحتاج تعديل في خطة الموارد البشرية."
        ]
    else:
        base_responses = [
            f"📋 Management Report: {project} - Overall progress 78%, key milestones achieved. Operational risks under control.",
            f"⚡ Project Status: {project} facing minor scheduling challenges. Budget remains within approved limits.",
            f"🔍 Strategic Review: {project} requires resource allocation adjustment."
        ]
    
    response = random.choice(base_responses)
    
    if enhanced_context:
        response += enhanced_context
    
    return response

def generate_enhanced_site_manager_response(message: str, project: str, is_arabic: bool, 
                                          enhanced_context: str, insights: dict) -> str:
    """Generate enhanced Site Manager response with operational focus"""
    if is_arabic:
        base_responses = [
            f"🔧 تقرير الموقع: {project} - أعمال الأسفلت 68% مكتملة، الفريق يعمل بكامل طاقته. لا توجد مشاكل أمان.",
            f"⚠️ تحديث تشغيلي: {project} - تأخير 3 أيام في أعمال MC0A بسبب الطقس. خطة التعويض جاهزة.",
            f"📅 جدولة الأعمال: {project} - المرحلة الحالية تسير وفق الخطة. التفتيش القادم مجدول للأسبوع المقبل."
        ]
    else:
        base_responses = [
            f"🔧 Site Report: {project} - Asphalt works 68% complete, crew at full capacity. No safety incidents.",
            f"⚠️ Operational Update: {project} - 3-day delay in MC0A works due to weather. Recovery plan in place.",
            f"📅 Work Schedule: {project} - Current phase on track. Next inspection scheduled for next week."
        ]
    
    response = random.choice(base_responses)
    
    if enhanced_context:
        response += enhanced_context
    
    return response

def generate_enhanced_engineer_response(message: str, project: str, is_arabic: bool, 
                                      enhanced_context: str, insights: dict) -> str:
    """Generate enhanced Engineer response with technical focus"""
    if is_arabic:
        base_responses = [
            f"🔧 تفاصيل تقنية: {project} - كمية الأسفلت المطلوبة 15,420 م³، المواصفات وفق ASTM D6927. الجودة مطابقة.",
            f"📐 مراجعة هندسية: {project} - RFI #234 بانتظار الموافقة، NCR #45 تم حلها. المخططات محدثة.",
            f"🧪 تقرير الجودة: {project} - جميع الاختبارات المعملية مطابقة للمواصفات. معدل الجودة 98.5%."
        ]
    else:
        base_responses = [
            f"🔧 Technical Details: {project} - Asphalt quantity required 15,420 m³, specs per ASTM D6927. Quality compliant.",
            f"📐 Engineering Review: {project} - RFI #234 pending approval, NCR #45 resolved. Drawings updated.",
            f"🧪 Quality Report: {project} - All lab tests meet specifications. Quality rating 98.5%."
        ]
    
    response = random.choice(base_responses)
    
    if enhanced_context:
        response += enhanced_context
    
    return response

def generate_enhanced_commercial_response(message: str, project: str, is_arabic: bool, 
                                        enhanced_context: str, insights: dict) -> str:
    """Generate enhanced Commercial Manager response with financial focus"""
    if is_arabic:
        base_responses = [
            f"💰 تقرير تجاري: {project} - قيمة العقد 45.2 مليون ريال، المدفوعات 72%. الرصيد المتبقي 12.7 مليون.",
            f"📊 الحالة المالية: {project} - أمر التغيير #22 تمت الموافقة عليه. التأمين ساري حتى ديسمبر 2025.",
            f"💼 تحديث تعاقدي: {project} - مطالبة التأخير قيد المراجعة. قيمة الضمانات 2.3 مليون ريال."
        ]
    else:
        base_responses = [
            f"💰 Commercial Report: {project} - Contract value SAR 45.2M, payments 72%. Remaining SAR 12.7M.",
            f"📊 Financial Status: {project} - Variation Order #22 approved. Insurance valid until Dec 2025.",
            f"💼 Contract Update: {project} - Delay claim under review. Bond value SAR 2.3M."
        ]
    
    response = random.choice(base_responses)
    
    if enhanced_context:
        response += enhanced_context
    
    return response

def generate_role_aware_response(message: str, project: str, user_role: str, relevant_docs: list) -> str:
    """Generate AI response based on message, project, user role, and relevant documents"""
    # Detect language
    is_arabic = any('\u0600' <= char <= '\u06FF' for char in message)
    
    # Get role-specific context
    role_context = rbac.get_role_context(user_role)
    allowed_docs = role_context.get('allowed_documents', [])
    
    # Check if user is asking for restricted information
    restricted_keywords = {
        'quotes': ['quote', 'quotation', 'pricing', 'cost', 'price', 'budget', 'financial'],
        'commercial': ['commercial', 'contract value', 'payment', 'invoice', 'profit', 'margin'],
        'financials': ['financial', 'budget', 'expenditure', 'profit', 'revenue', 'cash flow'],
        'contracts': ['contract terms', 'agreement details', 'legal terms', 'conditions']
    }
    
    message_lower = message.lower()
    
    # Check for restricted content requests
    for doc_type, keywords in restricted_keywords.items():
        if any(keyword in message_lower for keyword in keywords):
            if doc_type not in allowed_docs and 'all' not in role_context.get('data_access', []):
                if is_arabic:
                    return f"🔒 عذراً، ليس لديك صلاحية للوصول إلى المعلومات التجارية والمالية. يرجى التواصل مع المدير التجاري أو الإدارة العليا للحصول على هذه المعلومات."
                else:
                    return f"🔒 Sorry, you don't have permission to access {doc_type} information. Please contact the Commercial Manager or senior management for this information."
    
    # Use document context if available
    document_context = ""
    if relevant_docs:
        doc_summaries = []
        for doc in relevant_docs:
            if 'analysis' in doc and doc['analysis'].get('document_category'):
                doc_type = doc['analysis']['document_category']
                file_name = doc.get('google_drive_metadata', {}).get('name', 'Unknown')
                doc_summaries.append(f"{doc_type.upper()}: {file_name}")
        
        if doc_summaries:
            document_context = f" Based on documents: {', '.join(doc_summaries)}."
    
    # Generate role-appropriate responses with document context
    if user_role == 'ceo':
        return generate_ceo_response(message, project, is_arabic, document_context, relevant_docs)
    elif user_role == 'director':
        return generate_director_response(message, project, is_arabic, document_context, relevant_docs)
    elif user_role == 'site_manager':
        return generate_site_manager_response(message, project, is_arabic, document_context, relevant_docs)
    elif user_role == 'engineer':
        return generate_engineer_response(message, project, is_arabic, document_context, relevant_docs)
    elif user_role == 'commercial_manager':
        return generate_commercial_response(message, project, is_arabic, document_context, relevant_docs)
    else:
        return generate_general_response(message, project, is_arabic, document_context)

def generate_ceo_response(message: str, project: str, is_arabic: bool, doc_context: str, docs: list) -> str:
    """Generate CEO-level response with full access and document insights"""
    if is_arabic:
        responses = [
            f"📊 نظرة شاملة: مشروع {project} - إجمالي القيمة: 45.2 مليون ريال، الإنفاق: 72%، الربح المتوقع: 8.5 مليون ريال.{doc_context} جميع المؤشرات الاستراتيجية إيجابية.",
            f"💼 تقرير تنفيذي: {project} يسير وفق الخطة الاستراتيجية. المخاطر المالية منخفضة، العائد على الاستثمار 18.5%.{doc_context}",
            f"🎯 الأداء الاستراتيجي: {project} حقق 95% من الأهداف المرحلية.{doc_context} التوقعات المالية تشير لتجاوز الأرباح المستهدفة بنسبة 12%."
        ]
    else:
        responses = [
            f"📊 Executive Overview: {project} - Total value: SAR 45.2M, expenditure: 72%, projected profit: SAR 8.5M.{doc_context} All strategic KPIs are positive.",
            f"💼 Strategic Report: {project} is aligned with strategic objectives. Financial risk is low, ROI at 18.5%.{doc_context}",
            f"🎯 Performance Summary: {project} achieved 95% of milestone targets.{doc_context} Financial projections indicate 12% profit margin above target."
        ]
    
    # Add document-specific insights for CEO
    if docs:
        doc_insight = _extract_ceo_insights(docs)
        if doc_insight:
            return random.choice(responses) + f" {doc_insight}"
    
    return random.choice(responses)

def generate_director_response(message: str, project: str, is_arabic: bool, doc_context: str, docs: list) -> str:
    """Generate Director-level response with strategic focus"""
    if is_arabic:
        responses = [
            f"📋 تقرير إداري: {project} - التقدم العام 78%، المعالم الرئيسية محققة.{doc_context} المخاطر التشغيلية تحت السيطرة.",
            f"⚡ حالة المشروع: {project} يواجه تحدي بسيط في الجدولة.{doc_context} الميزانية ضمن الحدود المقررة.",
            f"🔍 مراجعة استراتيجية: {project} يحتاج تعديل في خطة الموارد البشرية.{doc_context}"
        ]
    else:
        responses = [
            f"📋 Management Report: {project} - Overall progress 78%, key milestones achieved.{doc_context} Operational risks under control.",
            f"⚡ Project Status: {project} facing minor scheduling challenges.{doc_context} Budget remains within approved limits.",
            f"🔍 Strategic Review: {project} requires resource allocation adjustment.{doc_context}"
        ]
    return random.choice(responses)

def generate_site_manager_response(message: str, project: str, is_arabic: bool, doc_context: str, docs: list) -> str:
    """Generate Site Manager response with operational focus only"""
    if is_arabic:
        responses = [
            f"🔧 تقرير الموقع: {project} - أعمال الأسفلت 68% مكتملة، الفريق يعمل بكامل طاقته.{doc_context} لا توجد مشاكل أمان.",
            f"⚠️ تحديث تشغيلي: {project} - تأخير 3 أيام في أعمال MC0A بسبب الطقس.{doc_context} خطة التعويض جاهزة.",
            f"📅 جدولة الأعمال: {project} - المرحلة الحالية تسير وفق الخطة.{doc_context} التفتيش القادم مجدول للأسبوع المقبل."
        ]
    else:
        responses = [
            f"🔧 Site Report: {project} - Asphalt works 68% complete, crew at full capacity.{doc_context} No safety incidents.",
            f"⚠️ Operational Update: {project} - 3-day delay in MC0A works due to weather.{doc_context} Recovery plan in place.",
            f"📅 Work Schedule: {project} - Current phase on track.{doc_context} Next inspection scheduled for next week."
        ]
    return random.choice(responses)

def generate_engineer_response(message: str, project: str, is_arabic: bool, doc_context: str, docs: list) -> str:
    """Generate Engineer response with technical focus"""
    if is_arabic:
        responses = [
            f"🔧 تفاصيل تقنية: {project} - كمية الأسفلت المطلوبة 15,420 م³، المواصفات وفق ASTM D6927.{doc_context} الجودة مطابقة.",
            f"📐 مراجعة هندسية: {project} - RFI #234 بانتظار الموافقة، NCR #45 تم حلها.{doc_context} المخططات محدثة.",
            f"🧪 تقرير الجودة: {project} - جميع الاختبارات المعملية مطابقة للمواصفات.{doc_context} معدل الجودة 98.5%."
        ]
    else:
        responses = [
            f"🔧 Technical Details: {project} - Asphalt quantity required 15,420 m³, specs per ASTM D6927.{doc_context} Quality compliant.",
            f"📐 Engineering Review: {project} - RFI #234 pending approval, NCR #45 resolved.{doc_context} Drawings updated.",
            f"🧪 Quality Report: {project} - All lab tests meet specifications.{doc_context} Quality rating 98.5%."
        ]
    return random.choice(responses)

def generate_commercial_response(message: str, project: str, is_arabic: bool, doc_context: str, docs: list) -> str:
    """Generate Commercial Manager response with financial focus"""
    if is_arabic:
        responses = [
            f"💰 تقرير تجاري: {project} - قيمة العقد 45.2 مليون ريال، المدفوعات 72%.{doc_context} الرصيد المتبقي 12.7 مليون.",
            f"📊 الحالة المالية: {project} - أمر التغيير #22 تمت الموافقة عليه.{doc_context} التأمين ساري حتى ديسمبر 2025.",
            f"💼 تحديث تعاقدي: {project} - مطالبة التأخير قيد المراجعة.{doc_context} قيمة الضمانات 2.3 مليون ريال."
        ]
    else:
        responses = [
            f"💰 Commercial Report: {project} - Contract value SAR 45.2M, payments 72%.{doc_context} Remaining SAR 12.7M.",
            f"📊 Financial Status: {project} - Variation Order #22 approved.{doc_context} Insurance valid until Dec 2025.",
            f"💼 Contract Update: {project} - Delay claim under review.{doc_context} Bond value SAR 2.3M."
        ]
    return random.choice(responses)

def generate_general_response(message: str, project: str, is_arabic: bool, doc_context: str) -> str:
    """Generate general response for other roles"""
    if is_arabic:
        return f"📋 معلومات عامة: {project} يسير وفق الخطة المحددة.{doc_context} للحصول على تفاصيل أكثر، يرجى التواصل مع المسؤول المختص."
    else:
        return f"📋 General Information: {project} is progressing according to plan.{doc_context} For detailed information, please contact the relevant department."

def get_role_appropriate_citations(user_role: str, relevant_docs: list) -> list:
    """Get citations appropriate for user role from relevant documents"""
    role_context = rbac.get_role_context(user_role)
    allowed_docs = role_context.get('allowed_documents', [])
    
    citations = []
    for doc in relevant_docs:
        # Check if user can access this document
        if _user_can_access_document(user_role, doc):
            file_name = doc.get('google_drive_metadata', {}).get('name', 'Unknown Document')
            citations.append(file_name)
    
    # Limit to 3 citations to avoid clutter
    return citations[:3] if citations else ['Project_Summary.pdf']

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

def _extract_ceo_insights(docs: list) -> str:
    """Extract CEO-level insights from documents"""
    insights = []
    
    for doc in docs:
        if 'analysis' in doc:
            analysis = doc['analysis']
            doc_category = analysis.get('document_category', '')
            
            if doc_category == 'financial':
                insights.append("Financial performance tracking required.")
            elif doc_category == 'schedule':
                insights.append("Schedule optimization opportunities identified.")
            elif doc_category == 'contract':
                insights.append("Contract compliance review needed.")
            elif doc_category == 'bim':
                insights.append("BIM model analysis shows potential for cost savings.")
            elif doc_category == 'powerbi':
                insights.append("Power BI report indicates a need for resource reallocation.")
    
    return " ".join(insights) if insights else ""

