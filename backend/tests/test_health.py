from fastapi.testclient import TestClient

from app.core.db import get_engine
from app.main import app


def test_health_returns_ok(engine):
    app.dependency_overrides[get_engine] = lambda: engine
    try:
        client = TestClient(app)
        response = client.get("/api/health")
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "ok"
        assert body["db"] == "ok"
    finally:
        app.dependency_overrides.clear()
