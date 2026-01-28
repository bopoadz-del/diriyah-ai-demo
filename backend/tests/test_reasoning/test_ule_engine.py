"""Tests for the ULE Engine."""

import pytest
from unittest.mock import MagicMock, patch

from backend.reasoning.ule_engine import ULEEngine
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
from backend.reasoning.packs.base_pack import BasePack
from backend.reasoning.packs.construction_pack import ConstructionPack
from backend.reasoning.packs.commercial_pack import CommercialPack


class TestULEEngineInitialization:
    """Test ULE engine initialization."""

    def test_engine_initializes_with_defaults(self):
        """Test engine initializes with default values."""
        engine = ULEEngine()
        assert engine._default_threshold == 0.75
        assert len(engine._packs) == 0
        assert len(engine._entities) == 0
        assert len(engine._links) == 0

    def test_engine_initializes_with_custom_threshold(self):
        """Test engine initializes with custom threshold."""
        engine = ULEEngine(default_confidence_threshold=0.9)
        assert engine._default_threshold == 0.9


class TestPackRegistration:
    """Test pack registration."""

    def test_register_pack(self):
        """Test registering a pack."""
        engine = ULEEngine()
        pack = ConstructionPack()
        engine.register_pack(pack)
        assert "ConstructionPack" in engine._packs
        assert engine._packs["ConstructionPack"] is pack

    def test_register_multiple_packs(self):
        """Test registering multiple packs."""
        engine = ULEEngine()
        engine.register_pack(ConstructionPack())
        engine.register_pack(CommercialPack())
        assert len(engine._packs) == 2
        assert "ConstructionPack" in engine._packs
        assert "CommercialPack" in engine._packs

    def test_unregister_pack(self):
        """Test unregistering a pack."""
        engine = ULEEngine()
        engine.register_pack(ConstructionPack())
        result = engine.unregister_pack("ConstructionPack")
        assert result is True
        assert "ConstructionPack" not in engine._packs

    def test_unregister_nonexistent_pack(self):
        """Test unregistering a pack that doesn't exist."""
        engine = ULEEngine()
        result = engine.unregister_pack("NonexistentPack")
        assert result is False

    def test_get_pack(self):
        """Test getting a pack by name."""
        engine = ULEEngine()
        pack = ConstructionPack()
        engine.register_pack(pack)
        retrieved = engine.get_pack("ConstructionPack")
        assert retrieved is pack

    def test_list_packs(self):
        """Test listing all packs."""
        engine = ULEEngine()
        engine.register_pack(ConstructionPack())
        engine.register_pack(CommercialPack())
        configs = engine.list_packs()
        assert len(configs) == 2
        names = [c.name for c in configs]
        assert "ConstructionPack" in names
        assert "CommercialPack" in names


class TestDocumentProcessing:
    """Test document processing."""

    @pytest.mark.asyncio
    async def test_process_document_extracts_entities(self):
        """Test that processing a document extracts entities."""
        engine = ULEEngine()
        engine.register_pack(ConstructionPack())

        doc = DocumentInput(
            document_id="test-doc-001",
            document_name="Test BOQ",
            content="""
            Item 1.1 Concrete Grade C40 for foundations - 500 m3
            Item 1.2 Steel reinforcement Y16 bars - 50 tons
            Section 03300 - Cast-in-Place Concrete
            """,
            document_type="boq",
            project_id="proj-001",
        )

        result = await engine.process_document(doc)

        assert result.document_id == "test-doc-001"
        assert result.total_entities_processed > 0
        assert "ConstructionPack" in result.packs_used

    @pytest.mark.asyncio
    async def test_process_empty_document(self):
        """Test processing an empty document."""
        engine = ULEEngine()
        engine.register_pack(ConstructionPack())

        doc = DocumentInput(
            document_id="empty-doc",
            document_name="Empty",
            content="",
            document_type="general",
        )

        result = await engine.process_document(doc)

        assert result.document_id == "empty-doc"
        assert result.total_entities_processed == 0


class TestLinkFinding:
    """Test link finding functionality."""

    @pytest.mark.asyncio
    async def test_find_links_by_document_id(self):
        """Test finding links by document ID."""
        engine = ULEEngine()
        engine.register_pack(ConstructionPack())

        # Process a document first
        doc = DocumentInput(
            document_id="link-test-doc",
            document_name="Test BOQ",
            content="Concrete Grade C40 as per specification 03300",
            document_type="boq",
        )
        await engine.process_document(doc)

        # Find links
        result = await engine.find_links(document_id="link-test-doc")

        assert result is not None
        assert result.document_id == "link-test-doc"

    @pytest.mark.asyncio
    async def test_find_links_with_threshold(self):
        """Test finding links with confidence threshold."""
        engine = ULEEngine()
        engine.register_pack(ConstructionPack())

        result = await engine.find_links(
            query_text="concrete",
            confidence_threshold=0.9,
        )

        # All returned links should meet threshold
        for link in result.links:
            assert link.confidence >= 0.9


class TestStatistics:
    """Test statistics functionality."""

    def test_get_statistics_empty(self):
        """Test statistics for empty engine."""
        engine = ULEEngine()
        stats = engine.get_statistics()

        assert stats["total_packs"] == 0
        assert stats["total_entities"] == 0
        assert stats["total_links"] == 0
        assert stats["total_documents"] == 0

    def test_get_statistics_with_packs(self):
        """Test statistics with registered packs."""
        engine = ULEEngine()
        engine.register_pack(ConstructionPack())
        engine.register_pack(CommercialPack())

        stats = engine.get_statistics()

        assert stats["total_packs"] == 2
        assert "ConstructionPack" in stats["packs"]
        assert "CommercialPack" in stats["packs"]


class TestExportImport:
    """Test export/import functionality."""

    def test_export_links_empty(self):
        """Test exporting links from empty engine."""
        engine = ULEEngine()
        exported = engine.export_links()
        assert exported == []

    def test_import_link(self):
        """Test importing a link."""
        engine = ULEEngine()

        link_data = {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "source_entity_id": "entity-1",
            "source_entity_type": "BOQItem",
            "target_entity_id": "entity-2",
            "target_entity_type": "SpecSection",
            "link_type": "specifies",
            "confidence": 0.85,
            "evidence": [],
            "pack_name": "ConstructionPack",
            "created_at": "2024-01-01T00:00:00",
            "validated": False,
        }

        engine.import_link(link_data)

        from uuid import UUID
        link = engine.get_link(UUID("550e8400-e29b-41d4-a716-446655440000"))
        assert link is not None
        assert link.confidence == 0.85
