"""API endpoints for the Universal Linking Engine (ULE) / Pack System."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.backend.db import get_db
from backend.reasoning.ule_engine import ULEEngine
from backend.reasoning.schemas import (
    DocumentInput,
    Entity,
    EntityType,
    Evidence,
    EvidenceType,
    Link,
    LinkRequest,
    LinkResult,
    LinkType,
    PackConfig,
)
from backend.reasoning.packs.construction_pack import ConstructionPack
from backend.reasoning.packs.commercial_pack import CommercialPack

logger = logging.getLogger(__name__)

router = APIRouter()

# Engine singleton
_engine: Optional[ULEEngine] = None


def get_engine() -> ULEEngine:
    """Get or create the ULE engine singleton."""
    global _engine
    if _engine is None:
        _engine = ULEEngine(
            default_confidence_threshold=0.75,
            embedding_model="all-MiniLM-L6-v2",
            use_openai_embeddings=False,
        )
        _engine.register_pack(ConstructionPack())
        _engine.register_pack(CommercialPack())
        logger.info("ULE Engine initialized with default packs")
    return _engine


# Request models
class LinkRequestBody(BaseModel):
    text: str = Field(description="Text to find links for")
    project_id: Optional[int] = Field(default=None)
    document_type: str = Field(default="general")
    confidence_threshold: float = Field(default=0.75)


class ProcessDocumentRequest(BaseModel):
    content: str = Field(description="Document text content")
    document_type: str = Field(default="general")
    project_id: Optional[int] = Field(default=None)


# Endpoints following existing pattern from backend/backend/api/ai.py

@router.post("/reasoning/link")
async def find_links(request: LinkRequestBody, db: Session = Depends(get_db)):
    """Find links for a text query."""
    engine = get_engine()

    # Create a temporary document to process
    doc = DocumentInput(
        document_id=f"query-{id(request)}",
        document_name="Query",
        content=request.text,
        document_type=request.document_type,
        project_id=str(request.project_id) if request.project_id else None,
    )

    try:
        result = await engine.process_document(doc)

        # Filter by confidence
        filtered_links = [
            link for link in result.links
            if link.confidence >= request.confidence_threshold
        ]

        return {
            "links": [
                {
                    "id": str(link.id),
                    "source": {
                        "type": link.source.type.value,
                        "id": link.source.id,
                        "text": link.source.text[:200],
                    },
                    "target": {
                        "type": link.target.type.value,
                        "id": link.target.id,
                        "text": link.target.text[:200],
                    },
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
                }
                for link in filtered_links
            ],
            "total_entities": result.total_entities_processed,
            "total_links": len(filtered_links),
            "processing_time_ms": result.processing_time_ms,
        }
    except Exception as e:
        logger.exception("Failed to find links")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reasoning/process-document/{document_id}")
async def process_document(
    document_id: str,
    request: ProcessDocumentRequest,
    db: Session = Depends(get_db),
):
    """Process a document to extract entities and find links."""
    engine = get_engine()

    doc = DocumentInput(
        document_id=document_id,
        document_name=document_id,
        content=request.content,
        document_type=request.document_type,
        project_id=str(request.project_id) if request.project_id else None,
    )

    try:
        result = await engine.process_document(doc)

        return {
            "document_id": document_id,
            "entities_extracted": result.total_entities_processed,
            "links_found": result.total_links_found,
            "links": [
                {
                    "id": str(link.id),
                    "source": {"type": link.source.type.value, "id": link.source.id, "text": link.source.text[:100]},
                    "target": {"type": link.target.type.value, "id": link.target.id, "text": link.target.text[:100]},
                    "link_type": link.link_type.value,
                    "confidence": link.confidence,
                }
                for link in result.links
            ],
            "packs_used": result.packs_used,
            "processing_time_ms": result.processing_time_ms,
        }
    except Exception as e:
        logger.exception("Failed to process document")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/reasoning/links/{document_id}")
async def get_document_links(
    document_id: str,
    confidence_threshold: float = 0.75,
    max_links: int = 100,
):
    """Get all links for a specific document."""
    engine = get_engine()

    try:
        result = await engine.find_links(
            document_id=document_id,
            confidence_threshold=confidence_threshold,
            max_links=max_links,
        )

        return {
            "document_id": document_id,
            "links": [
                {
                    "id": str(link.id),
                    "source": {
                        "type": link.source.type.value,
                        "id": link.source.id,
                        "text": link.source.text[:200],
                        "document_id": link.source.document_id,
                    },
                    "target": {
                        "type": link.target.type.value,
                        "id": link.target.id,
                        "text": link.target.text[:200],
                        "document_id": link.target.document_id,
                    },
                    "link_type": link.link_type.value,
                    "confidence": link.confidence,
                    "evidence": [e.model_dump() for e in link.evidence],
                }
                for link in result.links
            ],
            "total_links": result.total_links_found,
        }
    except Exception as e:
        logger.exception("Failed to get document links")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/reasoning/evidence/{link_id}")
async def get_link_evidence(link_id: str):
    """Get detailed evidence for a specific link."""
    engine = get_engine()

    try:
        link_uuid = UUID(link_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid link ID format")

    evidence_response = engine.get_evidence(link_uuid)

    if evidence_response is None:
        raise HTTPException(status_code=404, detail=f"Link {link_id} not found")

    return {
        "link_id": str(evidence_response.link_id),
        "source": {
            "type": evidence_response.source.type.value,
            "id": evidence_response.source.id,
            "text": evidence_response.source.text,
        },
        "target": {
            "type": evidence_response.target.type.value,
            "id": evidence_response.target.id,
            "text": evidence_response.target.text,
        },
        "link_type": evidence_response.link_type.value,
        "confidence": evidence_response.confidence,
        "evidence": [e.model_dump() for e in evidence_response.evidence],
        "explanation": evidence_response.explanation,
    }


@router.get("/reasoning/graph/{project_id}")
async def get_project_graph(project_id: int, db: Session = Depends(get_db)):
    """Get knowledge graph data for visualization."""
    engine = get_engine()

    # Get all links for the project
    stats = engine.get_statistics()

    # Build nodes and edges for visualization
    nodes = []
    edges = []
    seen_entities = set()

    for link in engine._links.values():
        # Add source node
        if link.source.id not in seen_entities:
            nodes.append({
                "id": link.source.id,
                "label": link.source.text[:50],
                "type": link.source.type.value,
                "document_id": link.source.document_id,
            })
            seen_entities.add(link.source.id)

        # Add target node
        if link.target.id not in seen_entities:
            nodes.append({
                "id": link.target.id,
                "label": link.target.text[:50],
                "type": link.target.type.value,
                "document_id": link.target.document_id,
            })
            seen_entities.add(link.target.id)

        # Add edge
        edges.append({
            "id": str(link.id),
            "source": link.source.id,
            "target": link.target.id,
            "link_type": link.link_type.value,
            "confidence": link.confidence,
        })

    return {
        "project_id": project_id,
        "nodes": nodes,
        "edges": edges,
        "stats": {
            "total_nodes": len(nodes),
            "total_edges": len(edges),
            "entity_types": stats["entity_types"],
            "link_types": stats["link_types"],
        },
    }


@router.get("/reasoning/packs")
async def list_packs():
    """List all registered packs."""
    engine = get_engine()

    return {
        "packs": [
            {
                "name": config.name,
                "version": config.version,
                "description": config.description,
                "entity_types": [et.value for et in config.entity_types],
                "link_types": [lt.value for lt in config.link_types],
                "confidence_threshold": config.confidence_threshold,
                "enabled": config.enabled,
            }
            for config in engine.list_packs()
        ]
    }


@router.get("/reasoning/stats")
async def get_stats():
    """Get engine statistics."""
    engine = get_engine()
    return engine.get_statistics()


@router.get("/reasoning/entity-types")
async def list_entity_types():
    """List all available entity types."""
    return [{"value": et.value, "name": et.name} for et in EntityType]


@router.get("/reasoning/link-types")
async def list_link_types():
    """List all available link types."""
    return [{"value": lt.value, "name": lt.name} for lt in LinkType]
