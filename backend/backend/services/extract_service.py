def extract_text(file_path: str) -> str:
    try:
        import textract
        return textract.process(file_path).decode("utf-8")
    except ModuleNotFoundError:
        return "Extraction failed: textract is not installed"
    except Exception as e:
        return f"Extraction failed: {e}"
