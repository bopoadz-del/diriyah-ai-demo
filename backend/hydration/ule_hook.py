"""ULE integration hook for hydration pipeline."""

from __future__ import annotations

import asyncio
import logging
from typing import Dict, List, Tuple
from uuid import uuid4

from sqlalchemy.orm import Session

from backend.reasoning.db_models import DocumentEntity, DocumentLink
from backend.reasoning.schemas import (
    DocumentInput,
    Entity,
    EntityType,
    Evidence,
    EvidenceType,
    Link,
    LinkType,
    PackConfig,
)
from backend.reasoning.ule_engine import ULEEngine
from backend.reasoning.packs.base_pack import BasePack

logger = logging.getLogger(__name__)


class SimpleHydrationPack(BasePack):
    """Lightweight pack for hydration ULE processing."""

    @classmethod
    def get_default_config(cls) -> PackConfig:
        return PackConfig(
            name="HydrationPack",
            version="1.0.0",
            description="Lightweight pack for hydration processing.",
            entity_types=[EntityType.BOQ_ITEM, EntityType.SPEC_SECTION],
            link_types=[LinkType.REFERENCES],
            confidence_threshold=0.6,
        )

    def extract_entities(
        self,
        content: str,
        document_id: str,
        document_name: str,
        document_type: str,
        metadata: Dict[str, object] | None = None,
    ) -> List[Entity]:
        tokens = [token for token in content.split("\n") if token.strip()]
        if not tokens:
            tokens = [content.strip()] if content.strip() else []
        entities: List[Entity] = []
        for idx, token in enumerate(tokens[:2]):
            entity_type = EntityType.BOQ_ITEM if idx == 0 else EntityType.SPEC_SECTION
            entities.append(
                Entity(
                    id=f"{document_id}-{idx}",
                    type=entity_type,
                    text=token,
                    document_id=document_id,
                    document_name=document_name,
                    metadata=metadata or {},
                )
            )
        return entities

    def match_entities(
        self,
        source_entities: List[Entity],
        target_entities: List[Entity],
        embeddings=None,
    ) -> List[Tuple[Entity, Entity, LinkType, float, List[Evidence]]]:
        links: List[Tuple[Entity, Entity, LinkType, float, List[Evidence]]] = []
        if len(source_entities) >= 2:
            evidence = [
                Evidence(
                    type=EvidenceType.KEYWORD_MATCH,
                    value=1.0,
                    weight=0.6,
                    source_text=source_entities[0].text,
                    target_text=source_entities[1].text,
                )
            ]
            links.append((source_entities[0], source_entities[1], LinkType.REFERENCES, 0.8, evidence))
        return links

    def calculate_confidence(self, source: Entity, target: Entity, evidence: List[Evidence]) -> float:
        if not evidence:
            return 0.0
        return min(1.0, sum(item.weight for item in evidence) / len(evidence))


class ULEHook:
    """Coordinate ULE processing and persistence."""

    def __init__(self) -> None:
        self.engine = ULEEngine()
        self.pack = SimpleHydrationPack()
        self.engine.register_pack(self.pack)

    def run(self, db: Session, workspace_id: str, document_id: int, document_name: str, text: str) -> int:
        if not text:
            return 0
        document = DocumentInput(
            document_id=str(document_id),
            document_name=document_name,
            content=text,
            document_type="hydration",
        )
        entities = self.pack.extract_entities(text, str(document_id), document_name, "hydration")
        result = self._run_engine(document)
        links = result.links or []
        self._persist_entities(db, workspace_id, entities)
        self._persist_links(db, workspace_id, links)
        return len(entities)

    def _run_engine(self, document: DocumentInput):
        try:
            return asyncio.run(self.engine.process_document(document))
        except RuntimeError:
            loop = asyncio.get_event_loop()
            return loop.run_until_complete(self.engine.process_document(document))

    def _persist_entities(self, db: Session, workspace_id: str, entities: List[Entity]) -> None:
        for entity in entities:
            existing = db.query(DocumentEntity).filter(DocumentEntity.id == entity.id).one_or_none()
            payload = {
                "id": entity.id,
                "entity_type": entity.type.value,
                "text": entity.text,
                "document_id": entity.document_id,
                "document_name": entity.document_name,
                "project_id": workspace_id,
                "metadata_": entity.metadata,
            }
            if existing:
                for key, value in payload.items():
                    setattr(existing, key, value)
            else:
                db.add(DocumentEntity(**payload))
        db.flush()

    def _persist_links(self, db: Session, workspace_id: str, links: List[Link]) -> None:
        for link in links:
            link_id = str(link.id or uuid4())
            existing = db.query(DocumentLink).filter(DocumentLink.id == link_id).one_or_none()
            payload = {
                "id": link_id,
                "source_entity_id": link.source.id,
                "source_entity_type": link.source.type.value,
                "source_document_id": link.source.document_id,
                "target_entity_id": link.target.id,
                "target_entity_type": link.target.type.value,
                "target_document_id": link.target.document_id,
                "link_type": link.link_type.value,
                "confidence": link.confidence,
                "evidence": [e.model_dump() for e in link.evidence],
                "pack_name": link.pack_name,
                "project_id": workspace_id,
                "metadata_": link.metadata,
            }
            if existing:
                for key, value in payload.items():
                    setattr(existing, key, value)
            else:
                db.add(DocumentLink(**payload))
        db.flush()
