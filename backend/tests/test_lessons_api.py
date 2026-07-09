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
                "japanese": "確認",
                "kana": "かくにん",
                "romaji": "kakunin",
                "meanings": "confirm; verify",
                "part_of_speech": "noun",
            }
        ],
    )
    run_import(engine, wordbank_dir)


def test_full_lesson_flow_through_the_api(engine, wordbank_dir):
    _seed_one_item_source(engine, wordbank_dir)

    app.dependency_overrides[get_engine] = lambda: engine
    try:
        client = TestClient(app)

        available = client.get("/api/lessons/available")
        assert available.status_code == 200
        assert available.json()["sources"][0]["lessons_available_in_source"] == 1

        start_response = client.post("/api/lessons/start", json={"source_id": 1})
        assert start_response.status_code == 200
        start_body = start_response.json()
        session_id = start_body["session_id"]
        item = start_body["items"][0]
        assert item["japanese"] == "確認"

        # romaji must be rejected end-to-end
        romaji_attempt = client.post(
            f"/api/lessons/{session_id}/answer",
            json={"item_id": item["item_id"], "prompt_type": "japanese", "submitted_answer": "kakunin"},
        )
        assert romaji_attempt.status_code == 200
        assert romaji_attempt.json()["is_correct"] is False

        meaning_attempt = client.post(
            f"/api/lessons/{session_id}/answer",
            json={"item_id": item["item_id"], "prompt_type": "meaning", "submitted_answer": "Confirm!"},
        )
        assert meaning_attempt.status_code == 200
        assert meaning_attempt.json()["is_correct"] is True
        assert meaning_attempt.json()["item_activated"] is False

        japanese_attempt = client.post(
            f"/api/lessons/{session_id}/answer",
            json={"item_id": item["item_id"], "prompt_type": "japanese", "submitted_answer": "かくにん"},
        )
        assert japanese_attempt.status_code == 200
        assert japanese_attempt.json()["is_correct"] is True
        assert japanese_attempt.json()["item_activated"] is True

        complete_response = client.post(f"/api/lessons/{session_id}/complete")
        assert complete_response.status_code == 200
        assert complete_response.json()["activated_item_ids"] == [item["item_id"]]

        dashboard = client.get("/api/dashboard").json()
        assert dashboard["srs_distribution"]["1"] == 1
        assert dashboard["srs_distribution"]["0"] == 0
        assert dashboard["lessons_available"] == 0
        assert dashboard["daily_streak"] == 0  # lesson quiz activity must not count as a review streak
    finally:
        app.dependency_overrides.clear()


def test_start_lesson_404_for_unknown_source(engine):
    app.dependency_overrides[get_engine] = lambda: engine
    try:
        client = TestClient(app)
        response = client.post("/api/lessons/start", json={"source_id": 999})
        assert response.status_code == 404
    finally:
        app.dependency_overrides.clear()


def test_start_lesson_400_when_no_items_eligible(engine, wordbank_dir):
    _seed_one_item_source(engine, wordbank_dir)

    app.dependency_overrides[get_engine] = lambda: engine
    try:
        client = TestClient(app)
        start_body = client.post("/api/lessons/start", json={"source_id": 1}).json()
        session_id = start_body["session_id"]
        item_id = start_body["items"][0]["item_id"]
        client.post(
            f"/api/lessons/{session_id}/answer",
            json={"item_id": item_id, "prompt_type": "meaning", "submitted_answer": "confirm"},
        )
        client.post(
            f"/api/lessons/{session_id}/answer",
            json={"item_id": item_id, "prompt_type": "japanese", "submitted_answer": "かくにん"},
        )

        # the only item in this source is now learned, so no lessons remain
        response = client.post("/api/lessons/start", json={"source_id": 1})
        assert response.status_code == 400
    finally:
        app.dependency_overrides.clear()


def test_answer_404_for_unknown_session(engine):
    app.dependency_overrides[get_engine] = lambda: engine
    try:
        client = TestClient(app)
        response = client.post(
            "/api/lessons/999/answer",
            json={"item_id": 1, "prompt_type": "meaning", "submitted_answer": "x"},
        )
        assert response.status_code == 404
    finally:
        app.dependency_overrides.clear()


def test_complete_404_for_unknown_session(engine):
    app.dependency_overrides[get_engine] = lambda: engine
    try:
        client = TestClient(app)
        response = client.post("/api/lessons/999/complete")
        assert response.status_code == 404
    finally:
        app.dependency_overrides.clear()
