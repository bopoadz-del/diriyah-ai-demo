"""API endpoints for the Universal Linking Engine (ULE) / Pack System."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.backend.db import get_db
from backend.reasoning import ULEEngine
from backend.reasoning.models import (
    DocumentInput,
    EntityType,
    EvidenceResponse,
    LinkRequest,
    LinkResult,
    LinkType,
    PackConfig,
    RegisterPackRequest,
)
from backend.reasoning.packs import BasePack, CommercialPack, ConstructionPack

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/reasoning", tags=["Reasoning"])


# -------------------------------------------------------------------------
# Engine singleton
# -------------------------------------------------------------------------

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
        # Register default packs
        _engine.register_pack(ConstructionPack())
        _engine.register_pack(CommercialPack())
        logger.info("ULE Engine initialized with default packs")
    return _engine


# -------------------------------------------------------------------------
# Request/Response Models
# -------------------------------------------------------------------------

class ProcessDocumentRequest(BaseModel):
    """Request to process a document for linking."""

    document_id: str = Field(description="Unique identifier for the document")
    document_name: str = Field(description="Human-readable document name")
    content: str = Field(description="Document text content")
    document_type: str = Field(
        description="Type of document: boq, specification, contract, drawing, cost, payment, variation, invoice"
    )
    project_id: Optional[str] = Field(default=None, description="Project identifier")
    packs: Optional[List[str]] = Field(default=None, description="Specific packs to use")
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        json_schema_extra = {
            "example": {
                "document_id": "DOC-001",
                "document_name": "BOQ_Foundations.xlsx",
                "content": "Item B-1234: Concrete Grade C40 for foundations - 500 m3\nSection 03300 - Cast-in-Place Concrete",
                "document_type": "boq",
                "project_id": "PROJ-001",
            }
        }


class LinkQueryRequest(BaseModel):
    """Request to find links."""

    document_id: Optional[str] = Field(default=None, description="Document ID to find links for")
    query_text: Optional[str] = Field(default=None, description="Text query to find links for")
    entity_types: Optional[List[str]] = Field(default=None, description="Filter by entity types")
    link_types: Optional[List[str]] = Field(default=None, description="Filter by link types")
    packs: Optional[List[str]] = Field(default=None, description="Specific packs to use")
    confidence_threshold: float = Field(default=0.75, ge=0.0, le=1.0)
    max_links: int = Field(default=100, ge=1, le=1000)
    include_evidence: bool = Field(default=True)

    class Config:
        json_schema_extra = {
            "example": {
                "document_id": "DOC-001",
                "confidence_threshold": 0.75,
                "max_links": 50,
            }
        }


class PackRegistrationRequest(BaseModel):
    """Request to register a custom pack."""

    name: str = Field(description="Unique name for the pack")
    version: str = Field(default="1.0.0")
    description: Optional[str] = None
    entity_types: List[str] = Field(description="Entity types this pack handles")
    link_types: List[str] = Field(description="Link types this pack can create")
    confidence_threshold: float = Field(default=0.75, ge=0.0, le=1.0)
    semantic_weight: float = Field(default=0.6, ge=0.0, le=1.0)
    keyword_weight: float = Field(default=0.4, ge=0.0, le=1.0)
    settings: Dict[str, Any] = Field(default_factory=dict)


class LinkResponse(BaseModel):
    """Response containing a link."""

    id: str
    source: Dict[str, Any]
    target: Dict[str, Any]
    link_type: str
    confidence: float
    evidence: List[Dict[str, Any]]
    pack_name: str
    created_at: str


class LinksResponse(BaseModel):
    """Response containing multiple links."""

    document_id: Optional[str] = None
    query_id: Optional[str] = None
    links: List[LinkResponse]
    total_entities_processed: int
    total_links_found: int
    processing_time_ms: float
    packs_used: List[str]
    confidence_threshold: float


class PackInfo(BaseModel):
    """Pack information response."""

    name: str
    version: str
    description: Optional[str]
    entity_types: List[str]
    link_types: List[str]
    confidence_threshold: float
    enabled: bool


class EngineStats(BaseModel):
    """Engine statistics response."""

    total_packs: int
    total_entities: int
    total_links: int
    total_documents: int
    entity_types: Dict[str, int]
    link_types: Dict[str, int]
    packs: List[str]
    embeddings_enabled: bool


# -------------------------------------------------------------------------
# API Endpoints
# -------------------------------------------------------------------------

@router.post("/link", response_model=LinksResponse)
async def find_links_for_query(
    request: LinkQueryRequest,
    db: Session = Depends(get_db),
) -> LinksResponse:
    """
    Find links for a document or text query.

    This endpoint searches for related entities and returns links with
    confidence scores and supporting evidence.
    """
    engine = get_engine()

    # Parse entity types
    entity_types_parsed: Optional[List[EntityType]] = None
    if request.entity_types:
        try:
            entity_types_parsed = [EntityType(et) for et in request.entity_types]
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid entity type: {e}",
            )

    # Parse link types
    link_types_parsed: Optional[List[LinkType]] = None
    if request.link_types:
        try:
            link_types_parsed = [LinkType(lt) for lt in request.link_types]
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid link type: {e}",
            )

    try:
        result = await engine.find_links(
            document_id=request.document_id,
            query_text=request.query_text,
            entity_types=entity_types_parsed,
            link_types=link_types_parsed,
            packs=request.packs,
            confidence_threshold=request.confidence_threshold,
            max_links=request.max_links,
        )
    except Exception as e:
        logger.exception("Failed to find links")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Link search failed: {str(e)}",
        )

    # Convert to response format
    links_response = [
        LinkResponse(
            id=str(link.id),
            source={
                "type": link.source.type.value,
                "id": link.source.id,
                "text": link.source.text[:200],
                "document_id": link.source.document_id,
                "section": link.source.section,
            },
            target={
                "type": link.target.type.value,
                "id": link.target.id,
                "text": link.target.text[:200],
                "document_id": link.target.document_id,
                "section": link.target.section,
            },
            link_type=link.link_type.value,
            confidence=link.confidence,
            evidence=[e.model_dump() for e in link.evidence] if request.include_evidence else [],
            pack_name=link.pack_name,
            created_at=link.created_at.isoformat(),
        )
        for link in result.links
    ]

    return LinksResponse(
        document_id=result.document_id,
        query_id=result.query_id,
        links=links_response,
        total_entities_processed=result.total_entities_processed,
        total_links_found=result.total_links_found,
        processing_time_ms=result.processing_time_ms,
        packs_used=result.packs_used,
        confidence_threshold=result.confidence_threshold,
    )


@router.post("/process", response_model=LinksResponse)
async def process_document(
    request: ProcessDocumentRequest,
    db: Session = Depends(get_db),
) -> LinksResponse:
    """
    Process a document to extract entities and find links.

    This endpoint extracts entities from the document using registered packs,
    computes embeddings, and discovers links with existing entities.
    """
    engine = get_engine()

    document = DocumentInput(
        document_id=request.document_id,
        document_name=request.document_name,
        content=request.content,
        document_type=request.document_type,
        project_id=request.project_id,
        metadata=request.metadata,
    )

    try:
        result = await engine.process_document(document, packs=request.packs)
    except Exception as e:
        logger.exception("Failed to process document")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Document processing failed: {str(e)}",
        )

    # Store links in database
    try:
        _store_links_to_db(db, result)
    except Exception as e:
        logger.warning("Failed to persist links to database: %s", e)

    # Convert to response format
    links_response = [
        LinkResponse(
            id=str(link.id),
            source={
                "type": link.source.type.value,
                "id": link.source.id,
                "text": link.source.text[:200],
                "document_id": link.source.document_id,
                "section": link.source.section,
            },
            target={
                "type": link.target.type.value,
                "id": link.target.id,
                "text": link.target.text[:200],
                "document_id": link.target.document_id,
                "section": link.target.section,
            },
            link_type=link.link_type.value,
            confidence=link.confidence,
            evidence=[e.model_dump() for e in link.evidence],
            pack_name=link.pack_name,
            created_at=link.created_at.isoformat(),
        )
        for link in result.links
    ]

    return LinksResponse(
        document_id=result.document_id,
        links=links_response,
        total_entities_processed=result.total_entities_processed,
        total_links_found=result.total_links_found,
        processing_time_ms=result.processing_time_ms,
        packs_used=result.packs_used,
        confidence_threshold=result.confidence_threshold,
    )


@router.get("/links/{document_id}", response_model=LinksResponse)
async def get_document_links(
    document_id: str,
    confidence_threshold: float = 0.75,
    max_links: int = 100,
) -> LinksResponse:
    """
    Get all links for a specific document.

    Returns links where the document's entities appear as either source or target.
    """
    engine = get_engine()

    try:
        result = await engine.find_links(
            document_id=document_id,
            confidence_threshold=confidence_threshold,
            max_links=max_links,
        )
    except Exception as e:
        logger.exception("Failed to get document links")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve links: {str(e)}",
        )

    links_response = [
        LinkResponse(
            id=str(link.id),
            source={
                "type": link.source.type.value,
                "id": link.source.id,
                "text": link.source.text[:200],
                "document_id": link.source.document_id,
                "section": link.source.section,
            },
            target={
                "type": link.target.type.value,
                "id": link.target.id,
                "text": link.target.text[:200],
                "document_id": link.target.document_id,
                "section": link.target.section,
            },
            link_type=link.link_type.value,
            confidence=link.confidence,
            evidence=[e.model_dump() for e in link.evidence],
            pack_name=link.pack_name,
            created_at=link.created_at.isoformat(),
        )
        for link in result.links
    ]

    return LinksResponse(
        document_id=document_id,
        links=links_response,
        total_entities_processed=result.total_entities_processed,
        total_links_found=result.total_links_found,
        processing_time_ms=result.processing_time_ms,
        packs_used=result.packs_used,
        confidence_threshold=confidence_threshold,
    )


@router.get("/evidence/{link_id}")
async def get_link_evidence(link_id: str) -> Dict[str, Any]:
    """
    Get detailed evidence for a specific link.

    Returns the full evidence chain with human-readable explanation.
    """
    engine = get_engine()

    try:
        link_uuid = UUID(link_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid link ID format (expected UUID)",
        )

    evidence_response = engine.get_evidence(link_uuid)

    if evidence_response is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Link {link_id} not found",
        )

    return {
        "link_id": str(evidence_response.link_id),
        "source": {
            "type": evidence_response.source.type.value,
            "id": evidence_response.source.id,
            "text": evidence_response.source.text,
            "document_id": evidence_response.source.document_id,
            "section": evidence_response.source.section,
            "metadata": evidence_response.source.metadata,
        },
        "target": {
            "type": evidence_response.target.type.value,
            "id": evidence_response.target.id,
            "text": evidence_response.target.text,
            "document_id": evidence_response.target.document_id,
            "section": evidence_response.target.section,
            "metadata": evidence_response.target.metadata,
        },
        "link_type": evidence_response.link_type.value,
        "confidence": evidence_response.confidence,
        "evidence": [e.model_dump() for e in evidence_response.evidence],
        "explanation": evidence_response.explanation,
    }


@router.post("/register-pack")
async def register_pack(request: PackRegistrationRequest) -> Dict[str, Any]:
    """
    Register a new pack with the engine.

    Note: Custom packs are configuration-only. For full custom logic,
    extend BasePack and register programmatically.
    """
    engine = get_engine()

    # Check if pack already exists
    existing = engine.get_pack(request.name)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Pack '{request.name}' already registered",
        )

    # Validate entity types
    try:
        entity_types = [EntityType(et) for et in request.entity_types]
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid entity type: {e}",
        )

    # Validate link types
    try:
        link_types = [LinkType(lt) for lt in request.link_types]
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid link type: {e}",
        )

    # For now, return config info (full custom pack registration requires Python code)
    config = PackConfig(
        name=request.name,
        version=request.version,
        description=request.description,
        entity_types=entity_types,
        link_types=link_types,
        confidence_threshold=request.confidence_threshold,
        semantic_weight=request.semantic_weight,
        keyword_weight=request.keyword_weight,
        settings=request.settings,
    )

    return {
        "status": "configuration_accepted",
        "message": f"Pack configuration for '{request.name}' accepted. "
                   "Note: For full custom logic, extend BasePack in Python.",
        "config": {
            "name": config.name,
            "version": config.version,
            "entity_types": [et.value for et in config.entity_types],
            "link_types": [lt.value for lt in config.link_types],
            "confidence_threshold": config.confidence_threshold,
        },
    }


@router.get("/packs", response_model=List[PackInfo])
async def list_packs() -> List[PackInfo]:
    """List all registered packs."""
    engine = get_engine()

    return [
        PackInfo(
            name=config.name,
            version=config.version,
            description=config.description,
            entity_types=[et.value for et in config.entity_types],
            link_types=[lt.value for lt in config.link_types],
            confidence_threshold=config.confidence_threshold,
            enabled=config.enabled,
        )
        for config in engine.list_packs()
    ]


@router.get("/stats", response_model=EngineStats)
async def get_engine_stats() -> EngineStats:
    """Get engine statistics."""
    engine = get_engine()
    stats = engine.get_statistics()

    return EngineStats(
        total_packs=stats["total_packs"],
        total_entities=stats["total_entities"],
        total_links=stats["total_links"],
        total_documents=stats["total_documents"],
        entity_types=stats["entity_types"],
        link_types=stats["link_types"],
        packs=stats["packs"],
        embeddings_enabled=stats["embeddings_enabled"],
    )


@router.get("/entity-types")
async def list_entity_types() -> List[Dict[str, str]]:
    """List all available entity types."""
    return [
        {"value": et.value, "name": et.name}
        for et in EntityType
    ]


@router.get("/link-types")
async def list_link_types() -> List[Dict[str, str]]:
    """List all available link types."""
    return [
        {"value": lt.value, "name": lt.name}
        for lt in LinkType
    ]


# -------------------------------------------------------------------------
# Database helpers
# -------------------------------------------------------------------------

def _store_links_to_db(db: Session, result: LinkResult) -> None:
    """Store links to the database."""
    from backend.reasoning.db_models import DocumentLink

    for link in result.links:
        db_link = DocumentLink(
            id=str(link.id),
            source_entity_id=link.source.id,
            source_entity_type=link.source.type.value,
            source_document_id=link.source.document_id,
            target_entity_id=link.target.id,
            target_entity_type=link.target.type.value,
            target_document_id=link.target.document_id,
            link_type=link.link_type.value,
            confidence=link.confidence,
            evidence=[e.model_dump() for e in link.evidence],
            pack_name=link.pack_name,
            validated=link.validated,
            metadata_=link.metadata,
        )
        db.merge(db_link)

    db.commit()
