import pytest

from backend.connectors.factory import get_connector


@pytest.mark.parametrize(
    "connector_type, expected_status",
    [("aconex", "stubbed"), ("p6", "stubbed"), ("vision", "stubbed")],
)
def test_connector_factory_returns_stub(connector_type, expected_status, monkeypatch):
    monkeypatch.setenv("USE_STUB_CONNECTORS", "true")
    connector = get_connector(connector_type)
    assert connector.get("status") == expected_status
