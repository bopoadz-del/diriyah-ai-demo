import textract

def extract_text(file_path: str) -> str:
    try:
        return textract.process(file_path).decode("utf-8")
    except Exception as e:
        return f"Extraction failed: {e}"