def test_analytics_log_endpoint(client):
    response = client.get("/api/analytics")

    assert response.status_code == 200

    payload = response.json()
    assert isinstance(payload, list)
    assert payload, "expected stub analytics log entries"

    for entry in payload:
        assert isinstance(entry, dict)
        assert {"id", "action", "user_id", "message_id", "timestamp"}.issubset(entry)
        assert all(entry[field] for field in ("action", "user_id", "message_id", "timestamp"))
        assert isinstance(entry["action"], str)
        assert isinstance(entry["user_id"], str)
        assert isinstance(entry["message_id"], str)
        assert isinstance(entry["timestamp"], str)

    unique_ids = {entry["id"] for entry in payload}
    assert len(unique_ids) == len(payload)
