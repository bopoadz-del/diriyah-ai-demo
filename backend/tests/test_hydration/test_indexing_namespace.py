import json
from datetime import datetime, timezone

from backend.hydration.models import SourceType, WorkspaceSource
from backend.hydration.pipeline import HydrationOptions, HydrationPipeline


class NamespaceConnector:
    def __init__(self, config, secrets_ref=None):
        return None

    def validate_config(self):
        return None

    def list_changes(self, cursor_json):
        return ([{"id": "doc-1", "file": {}}], {"token": "t"})

    def get_metadata(self, item):
        return {
            "source_document_id": item["id"],
            "name": "spec.txt",
            "mime_type": "text/plain",
            "modified_time": datetime(2024, 1, 1, tzinfo=timezone.utc),
            "size_bytes": 10,
            "checksum": "abc",
            "path": f"drive://{item['id']}",
            "removed": False,
        }

    def download(self, item):
        return b"spec content"


class TrackingIndexing:
    def __init__(self):
        self.calls = []

    def index_chunks(self, workspace_id, document_id, version_id, chunks):
        self.calls.append(workspace_id)
        return len(list(chunks))


class NoopULE:
    def run(self, db, workspace_id, document_id, document_name, text):
        return 0


def test_indexing_namespace(db_session):
    source = WorkspaceSource(
        workspace_id="ws-namespace",
        source_type=SourceType.GOOGLE_DRIVE,
        name="Drive",
        config_json=json.dumps({"root_folder_id": "root"}),
    )
    db_session.add(source)
    db_session.commit()

    indexing = TrackingIndexing()
    pipeline = HydrationPipeline(
        db_session,
        indexing_client=indexing,
        ule_hook=NoopULE(),
        connectors={SourceType.GOOGLE_DRIVE: NamespaceConnector},
    )
    pipeline.hydrate_workspace("ws-namespace", HydrationOptions())

    assert indexing.calls == ["ws-namespace"]
