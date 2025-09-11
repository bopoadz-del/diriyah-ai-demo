"""
export_pdf.py
--------------

Provides a utility to turn a chat history (list of dictionaries with
``role`` and ``text`` fields) into a PDF using reportlab.  The
function returns the file path of the generated document.  Users can
download the PDF via a ``FileResponse``.

Note: For simplicity, this demo uses the default font.  You may
register additional fonts (e.g. for Arabic) if your environment
supports them.
"""

import uuid
from typing import List, Dict

from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

def export_chat_to_pdf(chat: List[Dict]) -> str:
    """
    Generate a PDF from a chat history.  Each message appears on its
    own line with a prefix icon to distinguish user and assistant.
    Returns the filename of the generated PDF.
    """
    fn = f"chat_{uuid.uuid4().hex}.pdf"
    doc = SimpleDocTemplate(fn)
    styles = getSampleStyleSheet()
    elements = []
    for m in chat:
        role = m.get("role")
        icon = "👤" if role == "user" else "🤖"
        text = m.get("text", "")
        elements.append(Paragraph(f"{icon} {text}", styles["Normal"]))
        elements.append(Spacer(1, 6))
    doc.build(elements)
    return fn