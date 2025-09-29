_active_project_id = None
def set_active_project(project_id: str):
    global _active_project_id
    _active_project_id = project_id
def get_active_project():
    return _active_project_id
