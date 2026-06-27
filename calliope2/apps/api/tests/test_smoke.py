from fastapi.testclient import TestClient

from calliope2.app import app


def test_health() -> None:
    client = TestClient(app)
    response = client.get("/v3/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert "version" in body
