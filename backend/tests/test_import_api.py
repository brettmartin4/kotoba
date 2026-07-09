from fastapi.testclient import TestClient

from app.core.config import get_wordbank_folder
from app.core.db import get_engine
from app.main import app
from tests.helpers import write_wordbank


def test_refresh_list_and_detail_endpoints(engine, wordbank_dir):
    write_wordbank(
        wordbank_dir / "work.xlsx",
        [
            {
                "item_type": "word",
                "japanese": "確認",
                "kana": "かくにん",
                "romaji": "kakunin",
                "meanings": "confirm",
                "part_of_speech": "noun",
            }
        ],
    )

    app.dependency_overrides[get_engine] = lambda: engine
    app.dependency_overrides[get_wordbank_folder] = lambda: wordbank_dir
    try:
        client = TestClient(app)

        refresh_response = client.post("/api/import/refresh")
        assert refresh_response.status_code == 200
        body = refresh_response.json()
        assert body["summary"] == {"new": 1}

        runs_response = client.get("/api/import/runs")
        assert runs_response.status_code == 200
        assert len(runs_response.json()) == 1

        run_id = body["import_run_id"]
        detail_response = client.get(f"/api/import/runs/{run_id}")
        assert detail_response.status_code == 200
        detail = detail_response.json()
        assert len(detail["items"]) == 1
        assert detail["items"][0]["status"] == "new"

        missing_response = client.get("/api/import/runs/999")
        assert missing_response.status_code == 404
    finally:
        app.dependency_overrides.clear()
