from collections.abc import Generator
import os
import pytest
from fastapi.testclient import TestClient
from backend.main import app

@pytest.fixture(autouse=True, scope="session")
def force_fixture_projects():
    os.environ["USE_FIXTURE_PROJECTS"] = "true"
    os.environ["REQUIRE_TENANT_ID"] = "false"

@pytest.fixture()
def client() -> Generator[TestClient, None, None]:
    with TestClient(app) as test_client:
        yield test_client
