def test_render_debug_endpoint(client, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@db:5432/app_db")
    monkeypatch.setenv("REDIS_URL", "redis://:secret@redis:6379/0")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("RENDER", "true")
    monkeypatch.setenv("RENDER_REGION", "oregon")
    monkeypatch.setenv("USE_FIXTURE_PROJECTS", "false")
    monkeypatch.setenv("DEBUG", "1")

    response = client.get("/api/debug/render")

    assert response.status_code == 200

    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["services"]["database"]["hostname"] == "db"
    assert payload["services"]["database"]["database"] == "app_db"
    assert payload["services"]["redis"]["scheme"] == "redis"
    assert payload["services"]["openai_api_key_present"] is True
    assert payload["features"]["use_fixture_projects"] is False
    assert payload["features"]["debug_logging"] is True
