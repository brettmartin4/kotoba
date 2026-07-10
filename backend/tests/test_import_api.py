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
        item_row = detail["items"][0]
        assert item_row["status"] == "new"
        # raw_data_json/candidate_item_ids_json are parsed into real nested objects,
        # not left as JSON-encoded strings, for easier frontend consumption
        assert item_row["raw_data"]["japanese"] == "確認"
        assert item_row["raw_data"]["meanings"] == ["confirm"]
        assert item_row["candidate_item_ids"] is None
        assert "raw_data_json" not in item_row
        assert "candidate_item_ids_json" not in item_row

        missing_response = client.get("/api/import/runs/999")
        assert missing_response.status_code == 404
    finally:
        app.dependency_overrides.clear()


def test_duplicate_pending_merge_candidate_ids_are_parsed_as_a_list(engine, wordbank_dir):
    path = wordbank_dir / "work.xlsx"
    write_wordbank(
        path,
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
        client.post("/api/import/refresh")

        # same kana, different japanese -- kana-only match, staged for manual review
        write_wordbank(
            path,
            [
                {
                    "item_type": "word",
                    "japanese": "別の漢字",
                    "kana": "かくにん",
                    "romaji": "kakunin",
                    "meanings": "confirm",
                    "part_of_speech": "noun",
                }
            ],
        )
        second_run = client.post("/api/import/refresh").json()

        detail = client.get(f"/api/import/runs/{second_run['import_run_id']}").json()
        duplicate_row = next(i for i in detail["items"] if i["status"] == "duplicate_pending_merge")
        assert isinstance(duplicate_row["candidate_item_ids"], list)
        assert len(duplicate_row["candidate_item_ids"]) == 1
    finally:
        app.dependency_overrides.clear()
