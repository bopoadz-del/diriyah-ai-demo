from backend.api import workspace


def setup_function() -> None:
    workspace._reset_state_for_tests()


def test_get_workspace_shell(client):
    response = client.get("/api/workspace/shell")
    assert response.status_code == 200
    payload = response.json()
    assert payload["activeProjectId"] == "villa-100"
    assert payload["activeChatId"] == "villa-ops"
    assert payload["microphoneEnabled"] is False
    assert "villa-ops" in payload["conversations"]


def test_create_chat_initialises_draft_conversation(client):
    response = client.post("/api/workspace/chats", json={"projectId": "tower-20"})
    assert response.status_code == 200
    payload = response.json()
    conversation = payload["conversation"]
    assert conversation["id"].startswith("draft-")
    assert conversation["context"]["summary"]
    # Confirm the sidebar metadata is present
    assert any(chat["id"] == conversation["id"] for chat in payload["chatGroups"][0]["chats"])


def test_submit_message_updates_activity_and_preview(client):
    response = client.post(
        "/api/workspace/chats/villa-ops/messages",
        json={"body": "Concrete pour complete."},
    )
    assert response.status_code == 200
    payload = response.json()
    conversation = payload["conversation"]
    messages = conversation["timeline"][0]["messages"]
    assert any(msg["body"] == "Concrete pour complete." for msg in messages)
    # Updated chat metadata should flow back with the same response
    summary = next(chat for chat in payload["chatGroups"][0]["chats"] if chat["id"] == "villa-ops")
    assert summary["preview"].startswith("Concrete pour complete")


def test_microphone_toggle_persists_state(client):
    initial = client.get("/api/workspace/shell").json()
    assert initial["microphoneEnabled"] is False

    response = client.post("/api/workspace/microphone", json={"enabled": True})
    assert response.status_code == 200
    assert response.json()["enabled"] is True

    updated = client.get("/api/workspace/shell").json()
    assert updated["microphoneEnabled"] is True
