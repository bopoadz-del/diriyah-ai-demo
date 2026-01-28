import json
from datetime import datetime, timezone

from backend.hydration.models import HydrationRun, HydrationRunItem, SourceType, WorkspaceSource
from backend.hydration.pipeline import HydrationOptions, HydrationPipeline


class LoggingConnector:
    def __init__(self, config, secrets_ref=None):
        return None

    def validate_config(self):
        return None

    def list_changes(self, cursor_json):
        return ([{"id": "doc-1", "file": {}}], {"token": "t"})

    def get_metadata(self, item):
        return {
            "source_document_id": item["id"],
            "name": "report.txt",
            "mime_type": "text/plain",
            "modified_time": datetime(2024, 1, 1, tzinfo=timezone.utc),
            "size_bytes": 10,
            "checksum": "abc",
            "path": f"drive://{item['id']}",
            "removed": False,
        }

    def download(self, item):
        return b"report content"


class NoopIndexing:
    def index_chunks(self, workspace_id, document_id, version_id, chunks):
        return len(list(chunks))


class NoopULE:
    def run(self, db, workspace_id, document_id, document_name, text):
        return 0


def test_run_logging(db_session):
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
        connectors={SourceType.GOOGLE_DRIVE: LoggingConnector},
    )
    pipeline.hydrate_workspace("ws-1", HydrationOptions())

    run = db_session.query(HydrationRun).one()
    items = db_session.query(HydrationRunItem).all()
    assert run.files_seen == 1
    assert len(items) == 1
