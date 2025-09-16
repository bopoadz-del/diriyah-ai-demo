import logging

logger = logging.getLogger(__name__)

class GoogleDriveAdapter:
    def __init__(self):
        # In a real implementation, this would initialize Google Drive API client
        logger.info("GoogleDriveAdapter initialized (mock mode).")

    async def list_files(self, project_folder_id: str):
        logger.info(f"Mocking Google Drive list_files for folder: {project_folder_id}")
        # Mock file data based on project_folder_id
        if project_folder_id == "heritage":
            return [
                {"name": "Heritage Resort Plan.pdf", "url": "#", "size": "3.0MB", "modified": "2024-09-10"},
                {"name": "Heritage Budget.xlsx", "url": "#", "size": "1.5MB", "modified": "2024-09-09"},
                {"name": "Heritage Design.docx", "url": "#", "size": "4.2MB", "modified": "2024-09-08"}
            ]
        elif project_folder_id == "infra":
            return [
                {"name": "Infrastructure Master Plan.pdf", "url": "#", "size": "5.0MB", "modified": "2024-09-12"},
                {"name": "Infrastructure Schedule.xlsx", "url": "#", "size": "2.1MB", "modified": "2024-09-11"}
            ]
        else:
            return []

    async def search_files(self, project_folder_id: str, query: str):
        logger.info(f"Mocking Google Drive search_files for folder: {project_folder_id} with query: {query}")
        # Mock search results
        all_mock_files = await self.list_files(project_folder_id)
        results = [f for f in all_mock_files if query.lower() in f["name"].lower()]
        return results


