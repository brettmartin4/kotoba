from fastapi.testclient import TestClient

from app.core.db import get_engine
from app.main import app


def test_get_settings_returns_default(engine):
    app.dependency_overrides[get_engine] = lambda: engine
    try:
        client = TestClient(app)
        response = client.get("/api/settings")
        assert response.status_code == 200
        assert response.json() == {"daily_lesson_cap": 10}
    finally:
        app.dependency_overrides.clear()


def test_patch_settings_updates_value(engine):
    app.dependency_overrides[get_engine] = lambda: engine
    try:
        client = TestClient(app)
        patch_response = client.patch("/api/settings", json={"daily_lesson_cap": 3})
        assert patch_response.status_code == 200
        assert patch_response.json() == {"daily_lesson_cap": 3}

        get_response = client.get("/api/settings")
        assert get_response.json() == {"daily_lesson_cap": 3}
    finally:
        app.dependency_overrides.clear()


def test_patch_settings_rejects_non_positive_value(engine):
    app.dependency_overrides[get_engine] = lambda: engine
    try:
        client = TestClient(app)
        response = client.patch("/api/settings", json={"daily_lesson_cap": 0})
        assert response.status_code == 422  # Pydantic field_validator rejects it before the service layer
    finally:
        app.dependency_overrides.clear()
