"""Integration tests for the Reasoning API endpoints."""

import pytest
from typing import Generator
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.api.reasoning import router, get_engine


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    """Create a test client for the reasoning API."""
    app = FastAPI()
    app.include_router(router, prefix="/api")

    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(autouse=True)
def reset_engine():
    """Reset the engine singleton between tests."""
    import backend.api.reasoning as reasoning_module
    reasoning_module._engine = None
    yield
    reasoning_module._engine = None


class TestLinkEndpoint:
    """Test POST /api/reasoning/link endpoint."""

    def test_find_links_basic(self, client: TestClient):
        """Test basic link finding."""
        response = client.post(
            "/api/reasoning/link",
            json={
                "text": "Concrete Grade C40 as per specification section 03300",
                "document_type": "boq",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "links" in data
        assert "total_entities" in data
        assert "processing_time_ms" in data

    def test_find_links_with_project_id(self, client: TestClient):
        """Test link finding with project ID."""
        response = client.post(
            "/api/reasoning/link",
            json={
                "text": "Steel reinforcement Y16 per drawing S-201",
                "project_id": 1,
                "document_type": "boq",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "links" in data

    def test_find_links_with_confidence_threshold(self, client: TestClient):
        """Test link finding with custom confidence threshold."""
        response = client.post(
            "/api/reasoning/link",
            json={
                "text": "Payment for concrete works",
                "confidence_threshold": 0.9,
            },
        )

        assert response.status_code == 200
        data = response.json()

        # All returned links should meet the threshold
        for link in data.get("links", []):
            assert link["confidence"] >= 0.9

    def test_find_links_empty_text(self, client: TestClient):
        """Test link finding with empty text."""
        response = client.post(
            "/api/reasoning/link",
            json={"text": ""},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total_entities"] == 0


class TestProcessDocumentEndpoint:
    """Test POST /api/reasoning/process-document/{document_id} endpoint."""

    def test_process_document_basic(self, client: TestClient):
        """Test basic document processing."""
        response = client.post(
            "/api/reasoning/process-document/DOC-001",
            json={
                "content": """
                Item 1.1 Concrete Grade C40 - 500 m3
                Section 03300 - Cast-in-Place Concrete
                """,
                "document_type": "boq",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["document_id"] == "DOC-001"
        assert "entities_extracted" in data
        assert "links_found" in data
        assert "packs_used" in data

    def test_process_document_with_project(self, client: TestClient):
        """Test document processing with project ID."""
        response = client.post(
            "/api/reasoning/process-document/DOC-002",
            json={
                "content": "Variation Order VO-001: Additional excavation - $50,000",
                "document_type": "variation",
                "project_id": 1,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["document_id"] == "DOC-002"


class TestGetLinksEndpoint:
    """Test GET /api/reasoning/links/{document_id} endpoint."""

    def test_get_links_for_document(self, client: TestClient):
        """Test getting links for a processed document."""
        # First process a document
        client.post(
            "/api/reasoning/process-document/LINK-DOC-001",
            json={
                "content": "Concrete Grade C40 per spec 03300",
                "document_type": "boq",
            },
        )

        # Then get links
        response = client.get("/api/reasoning/links/LINK-DOC-001")

        assert response.status_code == 200
        data = response.json()
        assert data["document_id"] == "LINK-DOC-001"
        assert "links" in data
        assert "total_links" in data

    def test_get_links_with_threshold(self, client: TestClient):
        """Test getting links with confidence threshold."""
        response = client.get(
            "/api/reasoning/links/SOME-DOC?confidence_threshold=0.8&max_links=50"
        )

        assert response.status_code == 200
        data = response.json()
        assert "links" in data


class TestEvidenceEndpoint:
    """Test GET /api/reasoning/evidence/{link_id} endpoint."""

    def test_get_evidence_invalid_id(self, client: TestClient):
        """Test getting evidence with invalid link ID."""
        response = client.get("/api/reasoning/evidence/invalid-uuid")

        assert response.status_code == 400
        assert "Invalid link ID" in response.json()["detail"]

    def test_get_evidence_not_found(self, client: TestClient):
        """Test getting evidence for non-existent link."""
        response = client.get(
            "/api/reasoning/evidence/550e8400-e29b-41d4-a716-446655440000"
        )

        assert response.status_code == 404


class TestGraphEndpoint:
    """Test GET /api/reasoning/graph/{project_id} endpoint."""

    def test_get_graph(self, client: TestClient):
        """Test getting knowledge graph for a project."""
        response = client.get("/api/reasoning/graph/1")

        assert response.status_code == 200
        data = response.json()
        assert data["project_id"] == 1
        assert "nodes" in data
        assert "edges" in data
        assert "stats" in data


class TestPacksEndpoint:
    """Test GET /api/reasoning/packs endpoint."""

    def test_list_packs(self, client: TestClient):
        """Test listing registered packs."""
        response = client.get("/api/reasoning/packs")

        assert response.status_code == 200
        data = response.json()
        assert "packs" in data
        assert len(data["packs"]) >= 2  # ConstructionPack and CommercialPack

        pack_names = [p["name"] for p in data["packs"]]
        assert "ConstructionPack" in pack_names
        assert "CommercialPack" in pack_names


class TestStatsEndpoint:
    """Test GET /api/reasoning/stats endpoint."""

    def test_get_stats(self, client: TestClient):
        """Test getting engine statistics."""
        response = client.get("/api/reasoning/stats")

        assert response.status_code == 200
        data = response.json()
        assert "total_packs" in data
        assert "total_entities" in data
        assert "total_links" in data
        assert "packs" in data


class TestMetadataEndpoints:
    """Test metadata endpoints."""

    def test_list_entity_types(self, client: TestClient):
        """Test listing entity types."""
        response = client.get("/api/reasoning/entity-types")

        assert response.status_code == 200
        data = response.json()
        assert len(data) > 0

        values = [item["value"] for item in data]
        assert "BOQItem" in values
        assert "SpecSection" in values

    def test_list_link_types(self, client: TestClient):
        """Test listing link types."""
        response = client.get("/api/reasoning/link-types")

        assert response.status_code == 200
        data = response.json()
        assert len(data) > 0

        values = [item["value"] for item in data]
        assert "specifies" in values
        assert "references" in values
