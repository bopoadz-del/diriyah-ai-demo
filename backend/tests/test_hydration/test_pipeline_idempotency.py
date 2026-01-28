import json
from datetime import datetime, timezone

from backend.hydration.models import SourceType, WorkspaceSource
from backend.hydration.pipeline import HydrationOptions, HydrationPipeline


class FakeConnector:
    def __init__(self, config, secrets_ref=None):
        self.checksum = config["checksum"]

    def validate_config(self):
        return None

    def list_changes(self, cursor_json):
        return ([{"id": "doc-1", "file": {}}], {"token": "next"})

    def get_metadata(self, item):
        return {
            "source_document_id": "doc-1",
            "name": "boq.txt",
            "mime_type": "text/plain",
            "modified_time": datetime(2024, 1, 1, tzinfo=timezone.utc),
            "size_bytes": 10,
            "checksum": self.checksum,
            "path": "drive://doc-1",
            "removed": False,
        }

    def download(self, item):
        return b"BOQ line 1\nSpec line 2"


class NoopIndexing:
    def index_chunks(self, workspace_id, document_id, version_id, chunks):
        return len(list(chunks))


class NoopULE:
    def run(self, db, workspace_id, document_id, document_name, text):
        return 0


def test_pipeline_idempotency(db_session):
    source = WorkspaceSource(
        workspace_id="ws-1",
        source_type=SourceType.SERVER_FS,
        name="Test",
        config_json=json.dumps({"checksum": "abc"}),
    )
    db_session.add(source)
    db_session.commit()

    pipeline = HydrationPipeline(
        db_session,
        indexing_client=NoopIndexing(),
        ule_hook=NoopULE(),
        connectors={SourceType.SERVER_FS: FakeConnector},
    )

    options = HydrationOptions()
    pipeline.hydrate_workspace("ws-1", options)
    pipeline.hydrate_workspace("ws-1", options)

    from backend.hydration.models import Document
    doc = db_session.query(Document).filter(Document.workspace_id == "ws-1").one()
    assert len(doc.versions) == 1

    source.config_json = json.dumps({"checksum": "def"})
    db_session.commit()

    pipeline = HydrationPipeline(
        db_session,
        indexing_client=NoopIndexing(),
        ule_hook=NoopULE(),
        connectors={SourceType.SERVER_FS: FakeConnector},
    )
    pipeline.hydrate_workspace("ws-1", options)

    doc = db_session.query(Document).filter(Document.workspace_id == "ws-1").one()
    assert len(doc.versions) == 2
