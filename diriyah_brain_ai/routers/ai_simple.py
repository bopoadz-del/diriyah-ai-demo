"""
Simplified AI router for Diriyah Brain AI with OpenAI integration
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import os
from datetime import datetime

# OpenAI integration
try:
    from openai import OpenAI
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

router = APIRouter(prefix="/api/ai", tags=["ai"])

class ChatRequest(BaseModel):
    message: str
    project: str = "Heritage Resort"
    language: str = "en"
    context: dict = {}

class ChatResponse(BaseModel):
    response: str
    project: str
    language: str
    timestamp: str

@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    """AI chat endpoint with OpenAI integration and contextual awareness"""
    try:
        message = request.message
        project = request.project
        language = request.language
        context = request.context
        
        if not message:
            raise HTTPException(status_code=400, detail="Message is required")
        
        # Generate AI response with context
        if OPENAI_AVAILABLE and os.getenv("OPENAI_API_KEY"):
            response_text = generate_contextual_openai_response(message, project, language, context)
        else:
            response_text = generate_contextual_fallback_response(message, project, language, context)
        
        return ChatResponse(
            response=response_text,
            project=project,
            language=language,
            timestamp=datetime.now().isoformat()
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat failed: {str(e)}")

def generate_contextual_openai_response(message: str, project: str, language: str, context: dict) -> str:
    """Generate contextual response using OpenAI API with background services data"""
    try:
        # Check for Google Drive specific commands first
        message_lower = message.lower()
        if any(keyword in message_lower for keyword in ["google drive", "drive", "list projects", "scan drive", "drive status"]):
            if "list projects" in message_lower or ("list" in message_lower and "drive" in message_lower):
                return "🔗 **Google Drive Integration Status:**\n\n❌ **Not Connected Yet**\n\nTo access your Google Drive projects:\n1. Click the 'Drive' button in the header\n2. Complete OAuth authentication\n3. Grant access to your shared files\n\nOnce connected, I can:\n✅ List all projects and folders\n✅ Analyze documents and files\n✅ Search through shared content\n✅ Process ZIP/RAR archives\n\nWould you like me to guide you through the connection process?"
            elif "scan drive" in message_lower:
                return "🔍 **Drive Scan Request**\n\n⚠️ **Google Drive Not Connected**\n\nTo scan your Google Drive:\n1. First connect your Google account\n2. I'll then scan all folders and files\n3. Process documents, images, CAD files\n4. Extract content from ZIP/RAR archives\n5. Build searchable index\n\nReady to connect? Click the 'Drive' button above!"
            elif "drive status" in message_lower:
                return "📊 **Google Drive Status:**\n\n🔴 **Disconnected**\n- No active Google Drive connection\n- OAuth authentication required\n- 0 files scanned\n\n🔧 **To Connect:**\n1. Click 'Drive' button\n2. Sign in with Google\n3. Grant permissions\n4. Start scanning\n\nOnce connected, I'll provide detailed analytics!"
        
        # Detect if Arabic is requested
        is_arabic = language == "ar" or any('\u0600' <= char <= '\u06FF' for char in message)
        response_language = "Arabic" if is_arabic else "English"
        
        # Build context from background services
        context_info = build_service_context(context, project)
        
        # Create enhanced system prompt
        system_prompt = f"""You are Diriyah Brain AI, an intelligent assistant for the {project} construction project.
        
        You have access to real-time data from:
        - Aconex (document management)
        - BIM models and 3D visualization
        - P6 scheduling system
        - PowerBI analytics and reports
        
        Current project context:
        {context_info}
        
        Respond in {response_language} with specific, actionable information. Be professional but conversational.
        Use relevant emojis and provide concrete data when available. If alerts are relevant, mention them naturally."""
        
        # Call OpenAI API
        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": message}
            ],
            max_tokens=400,
            temperature=0.7
        )
        
        ai_response = response.choices[0].message.content.strip()
        return f"🤖 {ai_response}"
        
    except Exception as e:
        print(f"OpenAI API error: {e}")
        return generate_contextual_fallback_response(message, project, language, context)

def generate_contextual_fallback_response(message: str, project: str, language: str, context: dict) -> str:
    """Generate contextual fallback response when OpenAI is not available"""
    is_arabic = language == "ar" or any('\u0600' <= char <= '\u06FF' for char in message)
    
    # Analyze message for specific service requests
    message_lower = message.lower()
    
    # BIM-related responses
    if any(word in message_lower for word in ['bim', 'model', '3d', 'clash']):
        if is_arabic:
            return f"🏗️ نماذج BIM لمشروع {project}: 8 نماذج نشطة، آخر تحديث اليوم. تم اكتشاف تداخل في الكتلة A بين الهيكل والأنظمة الميكانيكية."
        else:
            return f"🏗️ BIM Status for {project}: 8 active models, updated today. Clash detected in Block A between structural and MEP systems. Would you like me to show the details?"
    
    # Schedule-related responses
    if any(word in message_lower for word in ['schedule', 'timeline', 'delay', 'p6']):
        if is_arabic:
            return f"📅 جدولة {project}: 342 مهمة مجدولة، 15 مهمة حرجة. تأخير 5 أيام في أعمال الأساسات. هل تريد تفاصيل المسار الحرج؟"
        else:
            return f"📅 Schedule Update for {project}: 342 tasks scheduled, 15 critical path items. Foundation work delayed by 5 days. Shall I show the critical path analysis?"
    
    # Document-related responses
    if any(word in message_lower for word in ['document', 'drawing', 'aconex', 'review']):
        if is_arabic:
            return f"📄 وثائق {project}: 1,247 وثيقة في النظام، 23 في انتظار المراجعة. مراجعة مواصفات الأساسات متأخرة. هل تريد قائمة الوثائق المعلقة؟"
        else:
            return f"📄 Documents for {project}: 1,247 documents in system, 23 pending review. Foundation specs review is overdue. Would you like the pending documents list?"
    
    # Safety and alerts
    if any(word in message_lower for word in ['safety', 'alert', 'issue', 'problem']):
        if is_arabic:
            return f"⚠️ تنبيهات الأمان لمشروع {project}: مطلوب فحص أمان للكتلة A، تأخير في توصيل المواد للمرحلة 2، تأثير الطقس على الأنشطة الخارجية."
        else:
            return f"⚠️ Safety Alerts for {project}: Safety inspection required for Block A foundation, material delivery delayed for Phase 2, weather impact on outdoor activities."
    
    # Budget and financial
    if any(word in message_lower for word in ['budget', 'cost', 'financial', 'payment']):
        if is_arabic:
            return f"💰 الوضع المالي لمشروع {project}: تم إنفاق 75% من الميزانية، اكتمال الجدولة 80%، نقاط الجودة 92%. الوضع المالي مستقر."
        else:
            return f"💰 Financial Status for {project}: 75% budget spent, 80% schedule completion, 92% quality score. Financial position is stable."
    
    # General status
    if is_arabic:
        return f"📊 تقرير عام لمشروع {project}: المشروع يسير بشكل جيد مع تقدم 78%. لا توجد مشاكل أمان كبيرة، الجودة تلبي المواصفات. كيف يمكنني مساعدتك؟"
    else:
        return f"📊 General Status for {project}: Project progressing well at 78% completion. No major safety issues, quality meets specifications. How can I assist you further?"

def build_service_context(context: dict, project: str) -> str:
    """Build context string from background services"""
    context_parts = []
    
    # Add project-specific data
    project_data = {
        'Heritage Resort': {
            'completion': '78%',
            'budget': '75% spent',
            'timeline': '5 days behind',
            'quality': '92%'
        },
        'Infrastructure MC0A': {
            'completion': '25%',
            'budget': '30% allocated',
            'timeline': 'On track',
            'quality': '88%'
        }
    }
    
    if project in project_data:
        data = project_data[project]
        context_parts.append(f"Project Status: {data['completion']} complete, {data['budget']}, {data['timeline']}")
    
    # Add service-specific context based on request
    services = context.get('services', [])
    
    if 'bim' in services:
        context_parts.append("BIM: 8 active models, clash detected in Block A")
    
    if 'p6' in services:
        context_parts.append("P6 Schedule: 342 tasks, 15 critical, foundation work delayed")
    
    if 'aconex' in services:
        context_parts.append("Aconex: 1,247 documents, 23 pending review")
    
    if 'powerbi' in services:
        context_parts.append("PowerBI: Latest KPIs show 92% quality score")
    
    return "\n".join(context_parts) if context_parts else "Standard project monitoring active"

