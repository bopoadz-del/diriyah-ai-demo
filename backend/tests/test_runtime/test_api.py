"""Tests for the runtime API endpoints."""

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Create test client."""
    from backend.main import app
    return TestClient(app, headers={"X-Tenant-ID": "test-tenant"})


class TestExecuteEndpoint:
    """Test the /runtime/execute endpoint."""

    def test_execute_simple_query(self, client):
        """Test executing a simple query."""
        response = client.post(
            "/api/runtime/execute",
            json={
                "query": "Calculate sum of [1, 2, 3, 4, 5]",
                "project_id": None,
                "dry_run": False,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "generated_code" in data
        assert "status" in data

    def test_execute_dry_run(self, client):
        """Test executing with dry_run=True."""
        response = client.post(
            "/api/runtime/execute",
            json={
                "query": "Calculate the total cost",
                "project_id": 1,
                "dry_run": True,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "generated_code" in data
        assert data["status"] == "dry_run"

    def test_execute_with_context(self, client):
        """Test executing with custom context."""
        response = client.post(
            "/api/runtime/execute",
            json={
                "query": "Sum the values",
                "project_id": None,
                "context": {"values": [10, 20, 30]},
                "dry_run": False,
            },
        )

        assert response.status_code == 200


class TestGenerateEndpoint:
    """Test the /runtime/generate endpoint."""

    def test_generate_code(self, client):
        """Test generating code only."""
        response = client.post(
            "/api/runtime/generate",
            json={
                "query": "Calculate cost variance",
                "project_id": 1,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "generated_code" in data
        assert "validation" in data

    def test_generate_returns_validation(self, client):
        """Test that generation returns validation info."""
        response = client.post(
            "/api/runtime/generate",
            json={
                "query": "Run Monte Carlo simulation",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "validation" in data
        assert "is_safe" in data["validation"]


class TestFunctionsEndpoint:
    """Test the /runtime/functions endpoint."""

    def test_list_functions(self, client):
        """Test listing approved functions."""
        response = client.get("/api/runtime/functions")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0

    def test_functions_have_metadata(self, client):
        """Test that functions have required metadata."""
        response = client.get("/api/runtime/functions")

        assert response.status_code == 200
        data = response.json()

        for func in data:
            assert "name" in func
            assert "signature" in func
            assert "description" in func
            assert "risk_level" in func

    def test_functions_include_monte_carlo(self, client):
        """Test that Monte Carlo function is included."""
        response = client.get("/api/runtime/functions")

        assert response.status_code == 200
        data = response.json()
        names = [f["name"] for f in data]
        assert "monte_carlo_sim" in names


class TestValidateEndpoint:
    """Test the /runtime/validate endpoint."""

    def test_validate_safe_code(self, client):
        """Test validating safe code."""
        response = client.post(
            "/api/runtime/validate",
            json={"code": "import pandas as pd\nresult = pd.DataFrame()"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["is_safe"] is True

    def test_validate_unsafe_code(self, client):
        """Test validating unsafe code."""
        response = client.post(
            "/api/runtime/validate",
            json={"code": "import os\nresult = os.system('ls')"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["is_safe"] is False
        assert "os" in data["forbidden_imports"]


class TestHistoryEndpoint:
    """Test the /runtime/history endpoint."""

    def test_get_history(self, client):
        """Test getting execution history."""
        response = client.get("/api/runtime/history/1")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_get_history_with_limit(self, client):
        """Test getting history with limit."""
        response = client.get("/api/runtime/history/1?limit=10")

        assert response.status_code == 200
        data = response.json()
        assert len(data) <= 10


class TestFunctionExecutionEndpoint:
    """Test the /runtime/function/{name} endpoint."""

    def test_execute_cost_variance(self, client):
        """Test executing cost_variance function directly."""
        response = client.post(
            "/api/runtime/function/cost_variance",
            json={"budget": 1000000, "actual": 800000},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "result" in data
        assert data["result"]["variance"] == 200000

    def test_execute_monte_carlo(self, client):
        """Test executing monte_carlo_sim function directly."""
        response = client.post(
            "/api/runtime/function/monte_carlo_sim",
            json={"values": [100, 110, 105, 95, 100], "iterations": 100},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "mean" in data["result"]

    def test_execute_nonexistent_function(self, client):
        """Test executing non-existent function."""
        response = client.post(
            "/api/runtime/function/nonexistent_function",
            json={},
        )

        assert response.status_code == 404

    def test_execute_with_invalid_params(self, client):
        """Test executing function with invalid parameters."""
        response = client.post(
            "/api/runtime/function/cost_variance",
            json={"invalid_param": 123},
        )

        assert response.status_code == 400
