import zipfile, rarfile, xml.etree.ElementTree as ET
import pptx, docx, openpyxl, PyPDF2
def extract_file_content(filepath: str) -> str:
    text = ""
    try:
        if filepath.endswith(".pdf"):
            reader = PyPDF2.PdfReader(open(filepath, "rb"))
            for page in reader.pages:
                text += page.extract_text() or ""
        elif filepath.endswith(".docx"):
            doc = docx.Document(filepath)
            text = "\n".join([p.text for p in doc.paragraphs])
        elif filepath.endswith(".pptx"):
            prs = pptx.Presentation(filepath)
            for slide in prs.slides:
                for shape in slide.shapes:
                    if hasattr(shape, "text"):
                        text += shape.text + "\n"
        elif filepath.endswith(".xlsx"):
            wb = openpyxl.load_workbook(filepath, data_only=True)
            for sheet in wb.sheetnames:
                ws = wb[sheet]
                for row in ws.iter_rows(values_only=True):
                    text += " ".join([str(c) for c in row if c]) + "\n"
        elif filepath.endswith(".xml"):
            root = ET.parse(filepath).getroot()
            text = ET.tostring(root, encoding="unicode")
        elif filepath.endswith(".xer") or filepath.endswith(".xml"):
            text = open(filepath, "r", errors="ignore").read()
        elif filepath.endswith(".zip"):
            with zipfile.ZipFile(filepath, "r") as z:
                for name in z.namelist():
                    try:
                        text += z.read(name).decode("utf-8") + "\n"
                    except:
                        pass
        elif filepath.endswith(".rar"):
            with rarfile.RarFile(filepath) as r:
                for name in r.namelist():
                    try:
                        text += r.read(name).decode("utf-8") + "\n"
                    except:
                        pass
        else:
            text = open(filepath, "r", errors="ignore").read()
    except Exception as e:
        text = f"[ERROR parsing {filepath}: {e}]"
    return text
