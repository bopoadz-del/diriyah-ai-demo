import json
from datetime import datetime, timezone

from backend.hydration.models import SourceType, WorkspaceSource
from backend.hydration.pipeline import HydrationOptions, HydrationPipeline
from backend.reasoning.db_models import DocumentEntity, DocumentLink


class SimpleConnector:
    def __init__(self, config, secrets_ref=None):
        return None

    def validate_config(self):
        return None

    def list_changes(self, cursor_json):
        return ([{"id": "doc-1", "file": {}}], {"token": "t"})

    def get_metadata(self, item):
        return {
            "source_document_id": item["id"],
            "name": "boq.txt",
            "mime_type": "text/plain",
            "modified_time": datetime(2024, 1, 1, tzinfo=timezone.utc),
            "size_bytes": 10,
            "checksum": "abc",
            "path": f"drive://{item['id']}",
            "removed": False,
        }

    def download(self, item):
        return b"BOQ item 1\nSpec section A"


class NoopIndexing:
    def index_chunks(self, workspace_id, document_id, version_id, chunks):
        return len(list(chunks))


def test_ule_hook_persist(db_session):
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
        connectors={SourceType.GOOGLE_DRIVE: SimpleConnector},
    )
    pipeline.hydrate_workspace("ws-1", HydrationOptions())

    assert db_session.query(DocumentEntity).count() > 0
    assert db_session.query(DocumentLink).count() > 0
