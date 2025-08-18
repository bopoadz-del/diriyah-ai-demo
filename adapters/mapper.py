def map_file_to_schema(file):
    """
    Maps file metadata into a simple format for AI.
    """
    return {
        "title": file.get("name"),
        "id": file.get("id"),
        "source": "gdrive"
    }
