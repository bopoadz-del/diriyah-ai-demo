import fitz

def extract_pdf_text(path:str)->str:
  try:
    doc=fitz.open(path); return '\n'.join(p.get_text() for p in doc)
  except Exception as e:
    return f'PDF extraction error: {e}'
