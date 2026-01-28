import json
from datetime import datetime, timezone

from backend.hydration.models import HydrationRunItem, SourceType, WorkspaceSource
from backend.hydration.pipeline import HydrationOptions, HydrationPipeline


class CursorConnector:
    def __init__(self, config, secrets_ref=None):
        self.config = config

    def validate_config(self):
        return None

    def list_changes(self, cursor_json):
        if cursor_json and cursor_json.get("token") == "c1":
            return ([{"id": "doc-2", "file": {}}], {"token": "c2"})
        return ([{"id": "doc-1", "file": {}}, {"id": "doc-2", "file": {}}], {"token": "c1"})

    def get_metadata(self, item):
        return {
            "source_document_id": item["id"],
            "name": f"{item['id']}.txt",
            "mime_type": "text/plain",
            "modified_time": datetime(2024, 1, 1, tzinfo=timezone.utc),
            "size_bytes": 10,
            "checksum": item["id"],
            "path": f"drive://{item['id']}",
            "removed": False,
        }

    def download(self, item):
        return f"Content {item['id']}".encode("utf-8")


class NoopIndexing:
    def index_chunks(self, workspace_id, document_id, version_id, chunks):
        return len(list(chunks))


class NoopULE:
    def run(self, db, workspace_id, document_id, document_name, text):
        return 0


def test_drive_cursor_incremental(db_session):
    source = WorkspaceSource(
        workspace_id="ws-1",
        source_type=SourceType.GOOGLE_DRIVE,
        name="Drive",
        config_json=json.dumps({"root_folder_id": "root"}),
    )
    db_session.add(source)
    db_session.commit()

    pipeline = HydrationPipeline(
        db_session,
        indexing_client=NoopIndexing(),
        ule_hook=NoopULE(),
        connectors={SourceType.GOOGLE_DRIVE: CursorConnector},
    )
    options = HydrationOptions()
    pipeline.hydrate_workspace("ws-1", options)

    run_items = db_session.query(HydrationRunItem).all()
    assert len(run_items) == 2

    pipeline.hydrate_workspace("ws-1", options)
    run_items = db_session.query(HydrationRunItem).all()
    assert len(run_items) == 3
