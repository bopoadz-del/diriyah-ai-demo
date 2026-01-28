"""Pydantic models for the Universal Linking Engine (ULE) system."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class EntityType(str, Enum):
    """Types of entities that can be linked."""

    # Construction entities
    BOQ_ITEM = "BOQItem"
    SPEC_SECTION = "SpecSection"
    CONTRACT_CLAUSE = "ContractClause"
    DRAWING_REF = "DrawingRef"

    # Commercial entities
    COST_ITEM = "CostItem"
    PAYMENT_CERT = "PaymentCert"
    VARIATION_ORDER = "VariationOrder"
    INVOICE = "Invoice"

    # General entities
    RFI = "RFI"
    SUBMITTAL = "Submittal"
    SCHEDULE_ACTIVITY = "ScheduleActivity"
    RESOURCE = "Resource"
    MATERIAL = "Material"
    EQUIPMENT = "Equipment"


class LinkType(str, Enum):
    """Types of relationships between entities."""

    # Specification relationships
    SPECIFIES = "specifies"
    SPECIFIED_BY = "specified_by"

    # Reference relationships
    REFERENCES = "references"
    REFERENCED_BY = "referenced_by"

    # Containment relationships
    CONTAINS = "contains"
    CONTAINED_IN = "contained_in"

    # Commercial relationships
    PAYS_FOR = "pays_for"
    PAID_BY = "paid_by"
    VARIES = "varies"
    VARIED_BY = "varied_by"
    INVOICES = "invoices"
    INVOICED_BY = "invoiced_by"

    # Compliance relationships
    COMPLIES_WITH = "complies_with"
    GOVERNS = "governs"

    # Drawing relationships
    DEPICTS = "depicts"
    DEPICTED_IN = "depicted_in"

    # Schedule relationships
    REQUIRES = "requires"
    REQUIRED_BY = "required_by"
    PRECEDES = "precedes"
    FOLLOWS = "follows"

    # Material relationships
    USES_MATERIAL = "uses_material"
    MATERIAL_USED_IN = "material_used_in"


class EvidenceType(str, Enum):
    """Types of evidence supporting a link."""

    KEYWORD_MATCH = "keyword_match"
    SEMANTIC_SIMILARITY = "semantic_similarity"
    CSI_CODE_MATCH = "csi_code_match"
    MATERIAL_MATCH = "material_match"
    QUANTITY_REFERENCE = "quantity_reference"
    CLAUSE_REFERENCE = "clause_reference"
    DRAWING_REFERENCE = "drawing_reference"
    COST_CODE_MATCH = "cost_code_match"
    DATE_PROXIMITY = "date_proximity"
    PROJECT_CONTEXT = "project_context"
    ENTITY_OVERLAP = "entity_overlap"
    RULE_BASED = "rule_based"


class Evidence(BaseModel):
    """Evidence supporting a link between entities."""

    type: EvidenceType
    value: Any = Field(description="The matched value or similarity score")
    weight: float = Field(ge=0.0, le=1.0, description="Weight of this evidence in confidence calculation")
    source_text: Optional[str] = Field(default=None, description="Source text that matched")
    target_text: Optional[str] = Field(default=None, description="Target text that matched")
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        json_schema_extra = {
            "example": {
                "type": "semantic_similarity",
                "value": 0.89,
                "weight": 0.6,
                "source_text": "Concrete Grade C40",
                "target_text": "Cast-in-Place Concrete C40/50",
            }
        }


class Entity(BaseModel):
    """An entity that can be linked to other entities."""

    id: str = Field(description="Unique identifier for the entity")
    type: EntityType
    text: str = Field(description="Primary text content of the entity")
    document_id: Optional[str] = Field(default=None, description="ID of the source document")
    document_name: Optional[str] = Field(default=None, description="Name of the source document")
    page_number: Optional[int] = Field(default=None, description="Page number in source document")
    section: Optional[str] = Field(default=None, description="Section identifier (e.g., CSI code)")
    metadata: Dict[str, Any] = Field(default_factory=dict)
    embedding: Optional[List[float]] = Field(default=None, exclude=True, description="Vector embedding")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "B-1234",
                "type": "BOQItem",
                "text": "Concrete Grade C40 for foundations",
                "document_id": "DOC-001",
                "document_name": "BOQ_Foundations.xlsx",
                "section": "03300",
            }
        }


class Link(BaseModel):
    """A link between two entities with confidence and evidence."""

    id: UUID = Field(default_factory=uuid4, description="Unique identifier for the link")
    source: Entity
    target: Entity
    link_type: LinkType
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence score for this link")
    evidence: List[Evidence] = Field(default_factory=list)
    pack_name: str = Field(description="Name of the pack that created this link")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    validated: bool = Field(default=False, description="Whether the link has been manually validated")
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        json_schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "source": {
                    "type": "BOQItem",
                    "id": "B-1234",
                    "text": "Concrete Grade C40",
                },
                "target": {
                    "type": "SpecSection",
                    "id": "03300",
                    "text": "Cast-in-Place Concrete",
                },
                "link_type": "specifies",
                "confidence": 0.92,
                "evidence": [
                    {"type": "keyword_match", "value": "C40", "weight": 0.4},
                    {"type": "semantic_similarity", "value": 0.89, "weight": 0.6},
                ],
                "pack_name": "ConstructionPack",
            }
        }


class LinkResult(BaseModel):
    """Result of a linking operation."""

    query_id: Optional[str] = Field(default=None, description="ID of the query that generated these links")
    document_id: Optional[str] = Field(default=None, description="ID of the processed document")
    links: List[Link] = Field(default_factory=list)
    total_entities_processed: int = Field(default=0)
    total_links_found: int = Field(default=0)
    processing_time_ms: float = Field(default=0.0)
    packs_used: List[str] = Field(default_factory=list)
    confidence_threshold: float = Field(default=0.75)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        json_schema_extra = {
            "example": {
                "document_id": "DOC-001",
                "links": [],
                "total_entities_processed": 150,
                "total_links_found": 45,
                "processing_time_ms": 1234.5,
                "packs_used": ["ConstructionPack", "CommercialPack"],
                "confidence_threshold": 0.75,
            }
        }


class PackConfig(BaseModel):
    """Configuration for a linking pack."""

    name: str = Field(description="Unique name for the pack")
    version: str = Field(default="1.0.0")
    description: Optional[str] = Field(default=None)
    entity_types: List[EntityType] = Field(description="Entity types this pack handles")
    link_types: List[LinkType] = Field(description="Link types this pack can create")
    confidence_threshold: float = Field(default=0.75, ge=0.0, le=1.0)
    semantic_weight: float = Field(default=0.6, ge=0.0, le=1.0, description="Weight for semantic similarity")
    keyword_weight: float = Field(default=0.4, ge=0.0, le=1.0, description="Weight for keyword matching")
    enabled: bool = Field(default=True)
    settings: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        json_schema_extra = {
            "example": {
                "name": "ConstructionPack",
                "version": "1.0.0",
                "description": "Links BOQ items to specifications, contracts, and drawings",
                "entity_types": ["BOQItem", "SpecSection", "ContractClause", "DrawingRef"],
                "link_types": ["specifies", "references", "depicts"],
                "confidence_threshold": 0.75,
                "semantic_weight": 0.6,
                "keyword_weight": 0.4,
            }
        }


# Request/Response models for API endpoints

class LinkRequest(BaseModel):
    """Request to find links for a document or query."""

    document_id: Optional[str] = Field(default=None, description="Document ID to find links for")
    query_text: Optional[str] = Field(default=None, description="Text query to find links for")
    entity_types: Optional[List[EntityType]] = Field(default=None, description="Filter by entity types")
    link_types: Optional[List[LinkType]] = Field(default=None, description="Filter by link types")
    packs: Optional[List[str]] = Field(default=None, description="Specific packs to use")
    confidence_threshold: float = Field(default=0.75, ge=0.0, le=1.0)
    max_links: int = Field(default=100, ge=1, le=1000)
    include_evidence: bool = Field(default=True)
    project_id: Optional[str] = Field(default=None)


class RegisterPackRequest(BaseModel):
    """Request to register a new pack."""

    config: PackConfig


class EntityInput(BaseModel):
    """Input for creating an entity."""

    id: str
    type: EntityType
    text: str
    document_id: Optional[str] = None
    document_name: Optional[str] = None
    page_number: Optional[int] = None
    section: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class DocumentInput(BaseModel):
    """Input for processing a document."""

    document_id: str
    document_name: str
    content: str
    document_type: str = Field(description="Type of document: boq, specification, contract, drawing")
    project_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class EvidenceResponse(BaseModel):
    """Response with evidence for a specific link."""

    link_id: UUID
    source: Entity
    target: Entity
    link_type: LinkType
    confidence: float
    evidence: List[Evidence]
    explanation: str = Field(description="Human-readable explanation of the link")
