"""SQLAlchemy models for the Universal Linking Engine (ULE) system."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from backend.backend.db import Base


# Use JSON type that falls back to TEXT for SQLite
try:
    from sqlalchemy.dialects.postgresql import JSONB as JSONType
except ImportError:
    from sqlalchemy import JSON as JSONType


class DocumentEntity(Base):
    """
    Represents an entity extracted from a document.

    Entities are the building blocks of links - they represent meaningful
    items like BOQ items, specification sections, contract clauses, etc.
    """

    __tablename__ = "document_entities"

    id = Column(String(255), primary_key=True, index=True)
    entity_type = Column(String(50), nullable=False, index=True)
    text = Column(Text, nullable=False)
    document_id = Column(String(255), nullable=True, index=True)
    document_name = Column(String(500), nullable=True)
    page_number = Column(Integer, nullable=True)
    section = Column(String(100), nullable=True, index=True)
    project_id = Column(String(255), nullable=True, index=True)
    metadata_ = Column("metadata", JSONType, default=dict)
    embedding_id = Column(String(255), nullable=True)  # Reference to vector store
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    source_links = relationship(
        "DocumentLink",
        foreign_keys="DocumentLink.source_entity_id",
        back_populates="source_entity",
        lazy="dynamic",
    )
    target_links = relationship(
        "DocumentLink",
        foreign_keys="DocumentLink.target_entity_id",
        back_populates="target_entity",
        lazy="dynamic",
    )

    __table_args__ = (
        Index("ix_document_entities_doc_type", "document_id", "entity_type"),
        Index("ix_document_entities_project", "project_id", "entity_type"),
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert entity to dictionary."""
        return {
            "id": self.id,
            "entity_type": self.entity_type,
            "text": self.text,
            "document_id": self.document_id,
            "document_name": self.document_name,
            "page_number": self.page_number,
            "section": self.section,
            "project_id": self.project_id,
            "metadata": self.metadata_ or {},
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class DocumentLink(Base):
    """
    Represents a link between two entities.

    Links connect related entities with confidence scores and evidence trails.
    Examples: BOQ item → Specification section, Cost item → Payment certificate
    """

    __tablename__ = "document_links"

    id = Column(String(36), primary_key=True)  # UUID as string
    source_entity_id = Column(
        String(255),
        ForeignKey("document_entities.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_entity_type = Column(String(50), nullable=False)
    source_document_id = Column(String(255), nullable=True, index=True)

    target_entity_id = Column(
        String(255),
        ForeignKey("document_entities.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    target_entity_type = Column(String(50), nullable=False)
    target_document_id = Column(String(255), nullable=True, index=True)

    link_type = Column(String(50), nullable=False, index=True)
    confidence = Column(Float, nullable=False, default=0.0, index=True)
    evidence = Column(JSONType, default=list)
    pack_name = Column(String(100), nullable=False, index=True)

    validated = Column(Boolean, default=False)
    validated_by = Column(String(255), nullable=True)
    validated_at = Column(DateTime(timezone=True), nullable=True)

    project_id = Column(String(255), nullable=True, index=True)
    metadata_ = Column("metadata", JSONType, default=dict)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    source_entity = relationship(
        "DocumentEntity",
        foreign_keys=[source_entity_id],
        back_populates="source_links",
    )
    target_entity = relationship(
        "DocumentEntity",
        foreign_keys=[target_entity_id],
        back_populates="target_links",
    )

    __table_args__ = (
        Index("ix_document_links_source_target", "source_entity_id", "target_entity_id"),
        Index("ix_document_links_type_confidence", "link_type", "confidence"),
        Index("ix_document_links_documents", "source_document_id", "target_document_id"),
        Index("ix_document_links_project_type", "project_id", "link_type"),
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert link to dictionary."""
        return {
            "id": self.id,
            "source": {
                "entity_id": self.source_entity_id,
                "entity_type": self.source_entity_type,
                "document_id": self.source_document_id,
            },
            "target": {
                "entity_id": self.target_entity_id,
                "entity_type": self.target_entity_type,
                "document_id": self.target_document_id,
            },
            "link_type": self.link_type,
            "confidence": self.confidence,
            "evidence": self.evidence or [],
            "pack_name": self.pack_name,
            "validated": self.validated,
            "validated_by": self.validated_by,
            "validated_at": self.validated_at.isoformat() if self.validated_at else None,
            "project_id": self.project_id,
            "metadata": self.metadata_ or {},
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class LinkValidation(Base):
    """
    Tracks manual validations of links by users.

    Allows tracking of user feedback on link quality for model improvement.
    """

    __tablename__ = "link_validations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    link_id = Column(
        String(36),
        ForeignKey("document_links.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = Column(String(255), nullable=False, index=True)
    action = Column(String(20), nullable=False)  # "approve", "reject", "uncertain"
    comment = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_link_validations_link_user", "link_id", "user_id"),
    )


class PackRegistration(Base):
    """
    Stores custom pack configurations registered via API.
    """

    __tablename__ = "pack_registrations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    version = Column(String(20), nullable=False, default="1.0.0")
    description = Column(Text, nullable=True)
    entity_types = Column(JSONType, default=list)
    link_types = Column(JSONType, default=list)
    confidence_threshold = Column(Float, default=0.75)
    semantic_weight = Column(Float, default=0.6)
    keyword_weight = Column(Float, default=0.4)
    settings = Column(JSONType, default=dict)
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def to_config_dict(self) -> Dict[str, Any]:
        """Convert to PackConfig-compatible dictionary."""
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "entity_types": self.entity_types or [],
            "link_types": self.link_types or [],
            "confidence_threshold": self.confidence_threshold,
            "semantic_weight": self.semantic_weight,
            "keyword_weight": self.keyword_weight,
            "settings": self.settings or {},
            "enabled": self.enabled,
        }


class LinkingJob(Base):
    """
    Tracks batch linking jobs for large document sets.
    """

    __tablename__ = "linking_jobs"

    id = Column(String(36), primary_key=True)  # UUID
    project_id = Column(String(255), nullable=True, index=True)
    status = Column(String(20), nullable=False, default="pending", index=True)  # pending, running, completed, failed
    total_documents = Column(Integer, default=0)
    processed_documents = Column(Integer, default=0)
    total_entities = Column(Integer, default=0)
    total_links = Column(Integer, default=0)
    packs_used = Column(JSONType, default=list)
    error_message = Column(Text, nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    metadata_ = Column("metadata", JSONType, default=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert job to dictionary."""
        return {
            "id": self.id,
            "project_id": self.project_id,
            "status": self.status,
            "progress": {
                "total_documents": self.total_documents,
                "processed_documents": self.processed_documents,
                "total_entities": self.total_entities,
                "total_links": self.total_links,
            },
            "packs_used": self.packs_used or [],
            "error_message": self.error_message,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "metadata": self.metadata_ or {},
        }


# Migration helper function
def create_all_tables(engine) -> None:
    """Create all ULE tables."""
    Base.metadata.create_all(engine, tables=[
        DocumentEntity.__table__,
        DocumentLink.__table__,
        LinkValidation.__table__,
        PackRegistration.__table__,
        LinkingJob.__table__,
    ])
