"""Tests for the ULE Packs."""

import pytest
from backend.reasoning.packs.construction_pack import ConstructionPack
from backend.reasoning.packs.commercial_pack import CommercialPack
from backend.reasoning.schemas import EntityType, LinkType


class TestConstructionPack:
    """Test the ConstructionPack."""

    def test_default_config(self):
        """Test default configuration."""
        pack = ConstructionPack()
        assert pack.name == "ConstructionPack"
        assert EntityType.BOQ_ITEM in pack.entity_types
        assert EntityType.SPEC_SECTION in pack.entity_types
        assert EntityType.CONTRACT_CLAUSE in pack.entity_types
        assert EntityType.DRAWING_REF in pack.entity_types

    def test_extract_boq_items(self):
        """Test BOQ item extraction."""
        pack = ConstructionPack()

        content = """
        1.1 Concrete Grade C40 for foundations - 500 m3
        1.2 Steel reinforcement Y16 bars - 50 tons
        1.3 Formwork for columns - 200 sqm
        """

        entities = pack.extract_entities(
            content=content,
            document_id="doc-001",
            document_name="BOQ.xlsx",
            document_type="boq",
        )

        # Should extract BOQ items
        boq_items = [e for e in entities if e.type == EntityType.BOQ_ITEM]
        assert len(boq_items) >= 1

    def test_extract_spec_sections(self):
        """Test specification section extraction."""
        pack = ConstructionPack()

        content = """
        SECTION 03300 - CAST-IN-PLACE CONCRETE

        PART 1 - GENERAL
        1.1 Related Documents
        A. Drawings and general provisions apply.

        SECTION 05120 - STRUCTURAL STEEL FRAMING

        PART 1 - GENERAL
        1.1 Related Documents
        """

        entities = pack.extract_entities(
            content=content,
            document_id="spec-001",
            document_name="Specifications.pdf",
            document_type="specification",
        )

        spec_sections = [e for e in entities if e.type == EntityType.SPEC_SECTION]
        assert len(spec_sections) >= 2

    def test_extract_drawing_refs(self):
        """Test drawing reference extraction."""
        pack = ConstructionPack()

        content = """
        Refer to drawings:
        - A-101 Ground Floor Plan
        - S-201 Foundation Details
        - M-301 HVAC Layout
        - E-401 Electrical Distribution
        """

        entities = pack.extract_entities(
            content=content,
            document_id="drawing-list",
            document_name="Drawing Index.pdf",
            document_type="drawing",
        )

        drawing_refs = [e for e in entities if e.type == EntityType.DRAWING_REF]
        assert len(drawing_refs) >= 2

    def test_extract_csi_codes(self):
        """Test CSI code extraction from text."""
        pack = ConstructionPack()
        codes = pack._extract_csi_codes("Concrete work per section 03300 and 03350")
        assert "03300" in codes
        assert "03350" in codes

    def test_identify_materials(self):
        """Test material identification."""
        pack = ConstructionPack()
        materials = pack._identify_materials("Concrete grade C40 with steel reinforcement")
        assert "concrete" in materials
        assert "steel" in materials


class TestCommercialPack:
    """Test the CommercialPack."""

    def test_default_config(self):
        """Test default configuration."""
        pack = CommercialPack()
        assert pack.name == "CommercialPack"
        assert EntityType.COST_ITEM in pack.entity_types
        assert EntityType.PAYMENT_CERT in pack.entity_types
        assert EntityType.VARIATION_ORDER in pack.entity_types
        assert EntityType.INVOICE in pack.entity_types

    def test_extract_cost_items(self):
        """Test cost item extraction."""
        pack = CommercialPack()

        content = """
        Budget Line Items:
        01.02.03 Excavation Works - 150,000.00
        01.02.04 Concrete Works - 450,000.00
        BL-001 Steel Structure - 800,000.00
        """

        entities = pack.extract_entities(
            content=content,
            document_id="budget-001",
            document_name="Budget.xlsx",
            document_type="cost",
        )

        cost_items = [e for e in entities if e.type == EntityType.COST_ITEM]
        assert len(cost_items) >= 1

    def test_extract_payment_certs(self):
        """Test payment certificate extraction."""
        pack = CommercialPack()

        content = """
        Payment Certificate No. 5
        Date: January 2024
        Amount: 500,000.00 USD

        IPC No. 6 - February 2024
        """

        entities = pack.extract_entities(
            content=content,
            document_id="payment-001",
            document_name="Payments.pdf",
            document_type="payment",
        )

        payment_certs = [e for e in entities if e.type == EntityType.PAYMENT_CERT]
        assert len(payment_certs) >= 1

    def test_extract_variations(self):
        """Test variation order extraction."""
        pack = CommercialPack()

        content = """
        Variation Order VO-001
        Description: Additional excavation required
        Original Amount: 100,000
        Variation Amount: 25,000

        Change Order CO-002
        """

        entities = pack.extract_entities(
            content=content,
            document_id="variation-001",
            document_name="Variations.pdf",
            document_type="variation",
        )

        variations = [e for e in entities if e.type == EntityType.VARIATION_ORDER]
        assert len(variations) >= 1

    def test_extract_invoices(self):
        """Test invoice extraction."""
        pack = CommercialPack()

        content = """
        Invoice No. INV-2024-001
        Date: 15 January 2024
        Amount: 75,500.00

        Bill No. BILL-002
        """

        entities = pack.extract_entities(
            content=content,
            document_id="invoice-001",
            document_name="Invoices.pdf",
            document_type="invoice",
        )

        invoices = [e for e in entities if e.type == EntityType.INVOICE]
        assert len(invoices) >= 1

    def test_extract_amounts(self):
        """Test amount extraction."""
        pack = CommercialPack()
        amounts = pack._extract_amounts("Total: $1,234,567.89 USD, VAT: 123,456.78")
        assert len(amounts) >= 2
        assert 1234567.89 in amounts

    def test_extract_date(self):
        """Test date extraction."""
        pack = CommercialPack()
        date = pack._extract_date("Payment due: 2024-01-15")
        assert date is not None
        assert "2024" in date


class TestPackMatching:
    """Test entity matching between packs."""

    def test_construction_pack_should_link(self):
        """Test should_link logic for ConstructionPack."""
        pack = ConstructionPack()

        from backend.reasoning.schemas import Entity

        boq_item = Entity(
            id="boq-1",
            type=EntityType.BOQ_ITEM,
            text="Concrete C40",
            document_id="doc-1",
        )

        spec_section = Entity(
            id="spec-1",
            type=EntityType.SPEC_SECTION,
            text="Cast-in-Place Concrete",
            document_id="doc-2",
        )

        # BOQ -> Spec should be linkable
        assert pack.should_link(boq_item, spec_section) is True

        # Same entity should not link
        assert pack.should_link(boq_item, boq_item) is False

    def test_commercial_pack_should_link(self):
        """Test should_link logic for CommercialPack."""
        pack = CommercialPack()

        from backend.reasoning.schemas import Entity

        cost_item = Entity(
            id="cost-1",
            type=EntityType.COST_ITEM,
            text="Concrete Works",
            document_id="doc-1",
        )

        payment = Entity(
            id="payment-1",
            type=EntityType.PAYMENT_CERT,
            text="IPC No. 5",
            document_id="doc-2",
        )

        # Cost -> Payment should be linkable
        assert pack.should_link(cost_item, payment) is True


class TestCrossPackScenarios:
    """Test scenarios involving multiple packs."""

    def test_extract_from_mixed_document(self):
        """Test extraction from a document with mixed content."""
        construction_pack = ConstructionPack()
        commercial_pack = CommercialPack()

        content = """
        Bill of Quantities - Foundation Works

        Item 1.1 Concrete Grade C40 per Section 03300 - 500 m3 @ 200 = 100,000.00

        Variation Order VO-001: Additional excavation
        Payment Certificate IPC No. 3 - Total: 150,000.00
        """

        # Extract with construction pack
        construction_entities = construction_pack.extract_entities(
            content=content,
            document_id="mixed-doc",
            document_name="Mixed.pdf",
            document_type="general",
        )

        # Extract with commercial pack
        commercial_entities = commercial_pack.extract_entities(
            content=content,
            document_id="mixed-doc",
            document_name="Mixed.pdf",
            document_type="general",
        )

        # Both packs should find relevant entities
        boq_items = [e for e in construction_entities if e.type == EntityType.BOQ_ITEM]
        variations = [e for e in commercial_entities if e.type == EntityType.VARIATION_ORDER]

        # At least something should be extracted
        assert len(construction_entities) + len(commercial_entities) > 0
