from fastapi.testclient import TestClient

from app.core.db import get_engine
from app.main import app
from app.services.import_service import run_import
from tests.helpers import write_wordbank


def test_dashboard_endpoint_shape(engine, wordbank_dir):
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

    app.dependency_overrides[get_engine] = lambda: engine
    try:
        client = TestClient(app)
        response = client.get("/api/dashboard")

        assert response.status_code == 200
        body = response.json()
        assert body["lessons_available"] == 1
        assert body["reviews_available"] == 0
        assert body["daily_lesson_cap"] == 10
        assert body["lessons_learned_today"] == 0
        assert body["srs_distribution"]["0"] == 1
        assert body["daily_streak"] == 0
        assert body["new_items_last_7_days"] == 1
        assert len(body["sources"]) == 1
        assert body["sources"][0]["source_key"] == "work"
    finally:
        app.dependency_overrides.clear()
