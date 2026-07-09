from fastapi.testclient import TestClient

from app.core.db import get_engine
from app.main import app
from app.services.import_service import run_import
from tests.helpers import write_wordbank


def _seed_one_item_source(engine, wordbank_dir):
    write_wordbank(
        wordbank_dir / "work.xlsx",
        [
            {
                "item_type": "word",
                "japanese": "a",
                "kana": "a",
                "romaji": "r",
                "meanings": "x",
                "part_of_speech": "noun",
            }
        ],
    )
    run_import(engine, wordbank_dir)


def test_list_sources_returns_levels_and_lesson_count(engine, wordbank_dir):
    _seed_one_item_source(engine, wordbank_dir)

    app.dependency_overrides[get_engine] = lambda: engine
    try:
        client = TestClient(app)
        response = client.get("/api/sources")

        assert response.status_code == 200
        body = response.json()
        assert len(body) == 1
        assert body[0]["source_key"] == "work"
        assert body[0]["current_level"] == 1
        assert len(body[0]["levels"]) == 1
        assert body[0]["lessons_available_in_source"] == 1
    finally:
        app.dependency_overrides.clear()


def test_patch_source_renames_display_name(engine, wordbank_dir):
    _seed_one_item_source(engine, wordbank_dir)

    app.dependency_overrides[get_engine] = lambda: engine
    try:
        client = TestClient(app)
        source_id = client.get("/api/sources").json()[0]["id"]

        response = client.patch(f"/api/sources/{source_id}", json={"display_name": "My Work Words"})
        assert response.status_code == 200
        assert response.json()["display_name"] == "My Work Words"

        refreshed = client.get("/api/sources").json()
        assert refreshed[0]["display_name"] == "My Work Words"
    finally:
        app.dependency_overrides.clear()


def test_patch_source_rejects_blank_name(engine, wordbank_dir):
    _seed_one_item_source(engine, wordbank_dir)

    app.dependency_overrides[get_engine] = lambda: engine
    try:
        client = TestClient(app)
        source_id = client.get("/api/sources").json()[0]["id"]

        response = client.patch(f"/api/sources/{source_id}", json={"display_name": "   "})
        assert response.status_code == 422
    finally:
        app.dependency_overrides.clear()


def test_patch_source_404_for_unknown_id(engine):
    app.dependency_overrides[get_engine] = lambda: engine
    try:
        client = TestClient(app)
        response = client.patch("/api/sources/999", json={"display_name": "Anything"})
        assert response.status_code == 404
    finally:
        app.dependency_overrides.clear()
