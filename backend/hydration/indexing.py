"""Hydration indexing wrapper."""

from __future__ import annotations

from typing import Iterable, List

class IndexingClient:
    """Wrapper around existing semantic store (FAISS via rag_service)."""

    def index_chunks(self, workspace_id: str, document_id: int, version_id: int, chunks: Iterable[str]) -> int:
        from backend.backend.services import rag_service
        count = 0
        for chunk in chunks:
            if not chunk.strip():
                continue
            source = f"doc:{document_id}:v{version_id}"
            rag_service.add_document(workspace_id, chunk, source)
            count += 1
        return count

    def delete_document(self, workspace_id: str, document_id: int) -> None:
        # rag_service does not support deletions; placeholder for future index.
        return
