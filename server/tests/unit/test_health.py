from __future__ import annotations

from fastapi.testclient import TestClient


def test_live_health(client: TestClient) -> None:
    response = client.get("/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "live"}


def test_request_id_is_returned(client: TestClient) -> None:
    response = client.get("/health/live", headers={"X-Request-ID": "test-request"})
    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "test-request"
