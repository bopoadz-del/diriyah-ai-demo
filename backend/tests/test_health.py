def test_health(client):
    r = client.get('/health')
    assert r.status_code == 200


def test_root_route_returns_message(client):
    response = client.get("/")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert "Diriyah Brain AI backend" in response.json()["message"]
