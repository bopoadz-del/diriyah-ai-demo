class IntentRouter:
    def route(self, message: str, project_id: str = None):
        intent = "unknown"
        m = message.lower()
        if "upload" in m: intent = "UPLOAD_DOC"
        elif "image" in m or "photo" in m: intent = "VISION_ANALYZE"
        elif "audio" in m or "mic" in m: intent = "TRANSCRIBE_AUDIO"
        return {"intent": intent, "message": message, "project_id": project_id}
