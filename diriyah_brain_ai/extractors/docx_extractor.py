from docx import Document

def extract_docx_text(path:str)->str:
  try:
    d=Document(path); return '\n'.join(p.text for p in d.paragraphs)
  except Exception as e:
    return f'DOCX extraction error: {e}'
