"""Reasoning service for document linking and knowledge graph operations."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from backend.reasoning.ule_engine import ULEEngine
from backend.reasoning.schemas import DocumentInput, Entity, Link, LinkResult
from backend.reasoning.packs.construction_pack import ConstructionPack
from backend.reasoning.packs.commercial_pack import CommercialPack

logger = logging.getLogger(__name__)


class ReasoningService:
    """
    Service for document linking and entity extraction.

    Wraps the ULEEngine and provides a simpler interface for common operations.
    Integrates with existing document storage and chat services.
    """

    def __init__(self, confidence_threshold: float = 0.75):
        """Initialize the reasoning service."""
        self._engine = ULEEngine(
            default_confidence_threshold=confidence_threshold,
            embedding_model="all-MiniLM-L6-v2",
            use_openai_embeddings=False,
        )
        self._engine.register_pack(ConstructionPack())
        self._engine.register_pack(CommercialPack())
        logger.info("ReasoningService initialized")

    async def process_and_link(
        self,
        project_id: int,
        text: str,
        doc_type: str = "general",
        document_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Process text to extract entities and find links.

        Args:
            project_id: The project ID
            text: Document or query text
            doc_type: Type of document (boq, specification, contract, etc.)
            document_id: Optional document ID

        Returns:
            Dictionary with extracted entities and links
        """
        doc = DocumentInput(
            document_id=document_id or f"proj-{project_id}-{hash(text)}",
            document_name=f"Document from project {project_id}",
            content=text,
            document_type=doc_type,
            project_id=str(project_id),
        )

        result = await self._engine.process_document(doc)

        return {
            "project_id": project_id,
            "document_id": doc.document_id,
            "entities_extracted": result.total_entities_processed,
            "links_found": result.total_links_found,
            "links": [self._link_to_dict(link) for link in result.links],
            "processing_time_ms": result.processing_time_ms,
        }

    async def get_document_links(
        self,
        document_id: str,
        confidence_threshold: float = 0.75,
        max_links: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Get all links for a document.

        Args:
            document_id: The document ID
            confidence_threshold: Minimum confidence score
            max_links: Maximum number of links to return

        Returns:
            List of link dictionaries
        """
        result = await self._engine.find_links(
            document_id=document_id,
            confidence_threshold=confidence_threshold,
            max_links=max_links,
        )

        return [self._link_to_dict(link) for link in result.links]

    async def search_related_entities(
        self,
        query: str,
        project_id: Optional[int] = None,
        top_k: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Search for entities related to a query.

        Args:
            query: Search query text
            project_id: Optional project ID filter
            top_k: Number of results to return

        Returns:
            List of entity dictionaries
        """
        result = await self._engine.find_links(
            query_text=query,
            max_links=top_k,
        )

        # Collect unique entities from links
        entities = {}
        for link in result.links:
            if link.source.id not in entities:
                entities[link.source.id] = self._entity_to_dict(link.source)
            if link.target.id not in entities:
                entities[link.target.id] = self._entity_to_dict(link.target)

        return list(entities.values())[:top_k]

    def get_link_explanation(self, link_id: str) -> Optional[str]:
        """
        Get a human-readable explanation for a link.

        Args:
            link_id: The link ID (UUID string)

        Returns:
            Explanation string or None if link not found
        """
        from uuid import UUID

        try:
            link_uuid = UUID(link_id)
        except ValueError:
            return None

        evidence_response = self._engine.get_evidence(link_uuid)
        if evidence_response is None:
            return None

        return evidence_response.explanation

    def get_statistics(self) -> Dict[str, Any]:
        """Get service statistics."""
        return self._engine.get_statistics()

    def _link_to_dict(self, link: Link) -> Dict[str, Any]:
        """Convert a Link to a dictionary."""
        return {
            "id": str(link.id),
            "source": self._entity_to_dict(link.source),
            "target": self._entity_to_dict(link.target),
            "link_type": link.link_type.value,
            "confidence": link.confidence,
            "evidence": [
                {
                    "type": e.type.value,
                    "value": e.value,
                    "weight": e.weight,
                }
                for e in link.evidence
            ],
            "pack_name": link.pack_name,
        }

    def _entity_to_dict(self, entity: Entity) -> Dict[str, Any]:
        """Convert an Entity to a dictionary."""
        return {
            "id": entity.id,
            "type": entity.type.value,
            "text": entity.text[:200],
            "document_id": entity.document_id,
            "section": entity.section,
        }


# Global singleton instance
_reasoning_service: Optional[ReasoningService] = None


def get_reasoning_service() -> ReasoningService:
    """Get or create the reasoning service singleton."""
    global _reasoning_service
    if _reasoning_service is None:
        _reasoning_service = ReasoningService()
    return _reasoning_service
