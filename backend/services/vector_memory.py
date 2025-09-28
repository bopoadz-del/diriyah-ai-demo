import chromadb
chroma_client = chromadb.PersistentClient(path="./chroma_db")
active_project = {"id": None, "collection": None}
def set_active_project(project_id: str):
    collection_name = f"project_{project_id}"
    active_project["id"] = project_id
    try:
        active_project["collection"] = chroma_client.get_or_create_collection(name=collection_name)
    except Exception:
        active_project["collection"] = None
def get_active_project():
    return active_project
