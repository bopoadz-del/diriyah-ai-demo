import os
import tempfile
import fitz  # PyMuPDF
import docx
import openpyxl


def process_file(filename: str, content: bytes) -> dict:
    """
    Process an uploaded file based on its extension and return structured output.
    """
    extension = os.path.splitext(filename)[-1].lower()

    if extension == ".pdf":
        return {"text": extract_text_from_pdf(content)}

    elif extension in [".docx", ".doc"]:
        return {"text": extract_text_from_docx(content)}

    elif extension in [".xlsx", ".xls"]:
        return {"data": extract_data_from_excel(content)}

    else:
        return {"error": f"Unsupported file type: {extension}"}


def extract_text_from_pdf(content: bytes) -> str:
    """
    Extract text from PDF using PyMuPDF.
    """
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    try:
        text = ""
        with fitz.open(tmp_path) as pdf:
            for page in pdf:
                text += page.get_text()
        return text.strip()
    finally:
        os.remove(tmp_path)


def extract_text_from_docx(content: bytes) -> str:
    """
    Extract text from a DOCX file.
    """
    with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    try:
        doc = docx.Document(tmp_path)
        text = "\n".join([para.text for para in doc.paragraphs])
        return text.strip()
    finally:
        os.remove(tmp_path)


def extract_data_from_excel(content: bytes) -> list:
    """
    Extract data from an Excel file (rows as lists).
    """
    with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    try:
        workbook = openpyxl.load_workbook(tmp_path, data_only=True)
        sheet = workboo
