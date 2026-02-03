"""Hydration pipeline orchestration."""

from __future__ import annotations

import hashlib
import json
import logging
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional, Tuple

from sqlalchemy.orm import Session

from backend.hydration.alerts import AlertManager
from backend.hydration.connectors.google_drive import GoogleDriveConnector
from backend.hydration.connectors.google_drive_public import GoogleDrivePublicConnector
from backend.hydration.connectors.server_fs import ServerFSConnector
from backend.hydration.extractors.router import get_extractor
from backend.hydration.indexing import IndexingClient
from backend.hydration.models import (
    AlertCategory,
    AlertSeverity,
    Document,
    DocumentType,
    DocumentVersion,
    HydrationRun,
    HydrationRunItem,
    HydrationRunStatus,
    HydrationState,
    HydrationStatus,
    HydrationTrigger,
    IngestionStatus,
    RunItemAction,
    RunItemStatus,
    SourceType,
    VersionStatus,
    WorkspaceSource,
)
from backend.hydration.ule_hook import ULEHook

logger = logging.getLogger(__name__)


@dataclass
class HydrationOptions:
    trigger: HydrationTrigger = HydrationTrigger.SCHEDULED
    source_ids: Optional[List[int]] = None
    force_full_scan: bool = False
    max_files: Optional[int] = None
    dry_run: bool = False


class HydrationPipeline:
    def __init__(
        self,
        db: Session,
        indexing_client: Optional[IndexingClient] = None,
        ule_hook: Optional[ULEHook] = None,
        connectors: Optional[Dict[SourceType, Any]] = None,
    ) -> None:
        self.db = db
        self.indexing = indexing_client or IndexingClient()
        self.ule_hook = ule_hook or ULEHook()
        self.alerts = AlertManager(db)
        self.connectors = connectors or {
            SourceType.GOOGLE_DRIVE: GoogleDriveConnector,
            SourceType.GOOGLE_DRIVE_PUBLIC: GoogleDrivePublicConnector,
            SourceType.SERVER_FS: ServerFSConnector,
        }

    def hydrate_workspace(self, workspace_id: str, options: HydrationOptions) -> HydrationRun:
        sources_query = (
            self.db.query(WorkspaceSource)
            .filter(WorkspaceSource.workspace_id == workspace_id, WorkspaceSource.is_enabled == True)
        )
        if options.source_ids:
            sources_query = sources_query.filter(WorkspaceSource.id.in_(options.source_ids))
        sources = sources_query.all()

        run = HydrationRun(
            workspace_id=workspace_id,
            trigger=options.trigger,
            status=HydrationRunStatus.RUNNING,
            sources_count=len(sources),
        )
        self.db.add(run)
        self.db.commit()
        self.db.refresh(run)

        for source in sources:
            try:
                self.hydrate_source(source, run, options)
            except Exception as exc:
                logger.exception("Hydration source %s failed: %s", source.id, exc)
                run.files_failed += 1
                run.status = HydrationRunStatus.PARTIAL
                run.error_summary = str(exc)
                self.alerts.create_alert(
                    workspace_id,
                    AlertSeverity.WARN,
                    AlertCategory.SYSTEM,
                    f"Hydration source {source.name} failed: {exc}",
                    run.id,
                )

        if run.status == HydrationRunStatus.RUNNING:
            run.status = HydrationRunStatus.SUCCESS
        run.finished_at = datetime.now(timezone.utc)
        self.db.commit()
        return run

    def hydrate_source(self, source: WorkspaceSource, run: HydrationRun, options: HydrationOptions) -> None:
        state = (
            self.db.query(HydrationState)
            .filter(HydrationState.workspace_source_id == source.id)
            .one_or_none()
        )
        if not state:
            state = HydrationState(workspace_source_id=source.id, status=HydrationStatus.IDLE)
            self.db.add(state)
            self.db.commit()
            self.db.refresh(state)

        state.status = HydrationStatus.RUNNING
        state.last_error = None
        self.db.commit()

        config = json.loads(source.config_json or "{}")
        connector_cls = self.connectors[source.source_type]
        connector = connector_cls(config, source.secrets_ref)
        connector.validate_config()

        cursor = None if options.force_full_scan else json.loads(state.cursor_json) if state.cursor_json else None
        items, new_cursor = connector.list_changes(cursor)

        for item in items[: options.max_files or len(items)]:
            run.files_seen += 1
            self.process_item(item, source, run, connector, options)

        state.cursor_json = json.dumps(new_cursor) if new_cursor is not None else state.cursor_json
        state.last_run_at = datetime.now(timezone.utc)
        state.status = HydrationStatus.SUCCESS if run.status != HydrationRunStatus.FAILED else HydrationStatus.FAILED
        if run.status == HydrationRunStatus.FAILED:
            state.consecutive_failures += 1
        else:
            state.consecutive_failures = 0
        self.db.commit()

    def process_item(
        self,
        item: Dict[str, Any],
        source: WorkspaceSource,
        run: HydrationRun,
        connector,
        options: HydrationOptions,
    ) -> None:
        start = time.time()
        metadata = connector.get_metadata(item)
        action = RunItemAction.DELETE if metadata.get("removed") else RunItemAction.NEW
        run_item = HydrationRunItem(
            run_id=run.id,
            workspace_source_id=source.id,
            source_document_id=str(metadata.get("source_document_id")),
            action=action,
            status=RunItemStatus.PENDING,
        )
        self.db.add(run_item)
        self.db.commit()

        try:
            document, is_new, is_update, version = self.upsert_document(source, metadata)
            run_item.document_id = document.id if document else None

            if action == RunItemAction.DELETE:
                if document:
                    document.ingestion_status = IngestionStatus.SKIPPED
                run_item.status = RunItemStatus.LINKED
                run.files_failed += 0
                self.db.commit()
                return

            if not is_new and not is_update:
                run_item.action = RunItemAction.SKIP
                run_item.status = RunItemStatus.LINKED
                run_item.details_json = json.dumps({"reason": "unchanged"})
                self.db.commit()
                return

            if options.dry_run:
                run_item.status = RunItemStatus.LINKED
                run_item.details_json = json.dumps({"dry_run": True})
                self.db.commit()
                return

            download_start = time.time()
            content = connector.download(item)
            download_ms = int((time.time() - download_start) * 1000)

            extract_start = time.time()
            extractor = get_extractor(document.name, document.mime_type)
            ocr_enabled = self._bool_env("HYDRATION_OCR_ENABLED", False)
            extracted_text, extracted_json = extractor(content, ocr_enabled)
            extract_ms = int((time.time() - extract_start) * 1000)

            document.doc_type = self.classify(document.name, extracted_text)
            document.ingestion_status = IngestionStatus.EXTRACTED
            version.extracted_text = extracted_text
            version.extracted_json = json.dumps(extracted_json)

            chunk_start = time.time()
            chunks = self.chunk(extracted_text)
            chunk_ms = int((time.time() - chunk_start) * 1000)

            embed_start = time.time()
            chunk_count = self.indexing.index_chunks(document.workspace_id, document.id, version.id, chunks)
            embed_ms = int((time.time() - embed_start) * 1000)
            version.chunk_count = chunk_count
            version.embedding_status = VersionStatus.DONE
            version.index_status = VersionStatus.DONE
            document.ingestion_status = IngestionStatus.INDEXED
            run.files_indexed += 1

            ule_start = time.time()
            entity_count = self.ule_hook.run(self.db, document.workspace_id, document.id, document.name, extracted_text)
            ule_ms = int((time.time() - ule_start) * 1000)
            version.ule_status = VersionStatus.DONE
            document.ingestion_status = IngestionStatus.LINKED
            run.files_ule_processed += 1

            run.files_downloaded += 1
            run.files_extracted += 1
            if is_new:
                run.files_new += 1
            if is_update:
                run.files_updated += 1

            run_item.status = RunItemStatus.LINKED
            run_item.duration_ms = int((time.time() - start) * 1000)
            run_item.details_json = json.dumps(
                {
                    "download_ms": download_ms,
                    "extract_ms": extract_ms,
                    "chunk_ms": chunk_ms,
                    "embed_ms": embed_ms,
                    "ule_ms": ule_ms,
                    "entities": entity_count,
                }
            )
            self.db.commit()
        except Exception as exc:
            logger.exception("Hydration item failed: %s", exc)
            run.files_failed += 1
            run.status = HydrationRunStatus.PARTIAL
            run_item.status = RunItemStatus.FAILED
            run_item.error_message = str(exc)
            self.db.commit()
            self.alerts.create_alert(
                source.workspace_id,
                AlertSeverity.WARN,
                AlertCategory.EXTRACTION,
                f"Hydration item failed: {exc}",
                run.id,
            )

    def upsert_document(self, source: WorkspaceSource, metadata: Dict[str, Any]) -> Tuple[Document, bool, bool, DocumentVersion]:
        document = (
            self.db.query(Document)
            .filter(
                Document.workspace_id == source.workspace_id,
                Document.source_type == source.source_type,
                Document.source_document_id == metadata["source_document_id"],
            )
            .one_or_none()
        )

        checksum = metadata.get("checksum") or self._checksum_fallback(metadata)
        modified_time = metadata.get("modified_time")

        if not document:
            document = Document(
                workspace_id=source.workspace_id,
                source_type=source.source_type,
                source_document_id=metadata["source_document_id"],
                source_path=metadata["path"],
                name=metadata.get("name") or metadata["source_document_id"],
                mime_type=metadata.get("mime_type"),
                size_bytes=metadata.get("size_bytes"),
                modified_time=modified_time,
                checksum=checksum,
                doc_type=DocumentType.OTHER,
            )
            self.db.add(document)
            self.db.commit()
            self.db.refresh(document)
            version = self._create_version(document, modified_time, checksum)
            return document, True, False, version

        if document.checksum == checksum:
            return document, False, False, document.versions[-1]

        document.name = metadata.get("name") or document.name
        document.mime_type = metadata.get("mime_type") or document.mime_type
        document.size_bytes = metadata.get("size_bytes") or document.size_bytes
        document.modified_time = modified_time
        document.checksum = checksum

        version = self._create_version(document, modified_time, checksum)
        return document, False, True, version

    def _create_version(self, document: Document, modified_time: Optional[datetime], checksum: Optional[str]) -> DocumentVersion:
        version_num = (document.versions[-1].version_num + 1) if document.versions else 1
        version = DocumentVersion(
            document_id=document.id,
            version_num=version_num,
            modified_time=modified_time,
            checksum=checksum,
        )
        self.db.add(version)
        self.db.commit()
        self.db.refresh(version)
        return version

    def classify(self, name: str, text: str) -> DocumentType:
        token = (name or "").lower() + " " + (text or "").lower()
        if "boq" in token:
            return DocumentType.BOQ
        if "spec" in token:
            return DocumentType.SPEC
        if "contract" in token:
            return DocumentType.CONTRACT
        if "drawing" in token:
            return DocumentType.DRAWING
        if "report" in token:
            return DocumentType.REPORT
        return DocumentType.OTHER

    def chunk(self, text: str, max_length: int = 800) -> List[str]:
        if not text:
            return []
        chunks: List[str] = []
        current = []
        current_len = 0
        for paragraph in text.split("\n"):
            if not paragraph.strip():
                continue
            if current_len + len(paragraph) > max_length and current:
                chunks.append("\n".join(current))
                current = []
                current_len = 0
            current.append(paragraph)
            current_len += len(paragraph)
        if current:
            chunks.append("\n".join(current))
        return chunks

    def _checksum_fallback(self, metadata: Dict[str, Any]) -> Optional[str]:
        source_id = metadata.get("source_document_id")
        if source_id:
            return hashlib.md5(str(source_id).encode("utf-8")).hexdigest()
        return None

    def _bool_env(self, key: str, default: bool) -> bool:
        value = str(os.getenv(key, str(default))).lower()
        return value in {"1", "true", "yes", "on"}


import os  # noqa: E402
