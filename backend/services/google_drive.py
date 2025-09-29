def get_drive_service():
    class _About:
        def get(self, fields=None):
            return self
        def execute(self):
            return {"user": {"emailAddress": "stub@example.com", "displayName": "Stub"}}
    class _Service:
        def about(self): return _About()
    return _Service()

def list_project_folders():
    return [{"name": "Gateway1", "mimeType": "application/vnd.google-apps.folder"}]

def get_project(project_id: str):
    return {"id": project_id, "name": f"Project {project_id}", "drive_id": "stub"}
