from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from sqlalchemy import insert

from app.core.db import get_engine
from app.main import app
from app.models import item_forms, item_meanings, study_progress, vocab_items


def _now_naive():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _seed_due_item(engine, japanese="確認", kana="かくにん", meaning="check"):
    with engine.begin() as conn:
        item_id = conn.execute(
            insert(vocab_items).values(
                item_type="word",
                japanese=japanese,
                kana=kana,
                romaji="r",
                part_of_speech="noun",
                normalized_japanese=japanese,
                normalized_kana=kana,
            )
        ).inserted_primary_key[0]
        conn.execute(
            insert(item_forms).values(item_id=item_id, form=japanese, normalized_form=japanese, form_type="display")
        )
        conn.execute(insert(item_forms).values(item_id=item_id, form=kana, normalized_form=kana, form_type="kana"))
        conn.execute(
            insert(item_meanings).values(
                item_id=item_id, meaning=meaning, normalized_meaning=meaning.lower(), origin="imported"
            )
        )
        conn.execute(
            insert(study_progress).values(
                item_id=item_id, srs_stage=1, next_review_at=_now_naive() - timedelta(hours=1)
            )
        )
    return item_id


def test_full_review_flow_through_the_api(engine):
    item_id = _seed_due_item(engine)

    app.dependency_overrides[get_engine] = lambda: engine
    try:
        client = TestClient(app)

        available = client.get("/api/reviews/available")
        assert available.status_code == 200
        assert available.json()["reviews_available"] == 1

        start_response = client.post("/api/reviews/start")
        assert start_response.status_code == 200
        start_body = start_response.json()
        session_id = start_body["session_id"]
        assert start_body["items"][0]["japanese"] == "確認"

        romaji_attempt = client.post(
            f"/api/reviews/{session_id}/answer",
            json={"item_id": item_id, "prompt_type": "japanese", "submitted_answer": "kakunin"},
        )
        assert romaji_attempt.status_code == 200
        assert romaji_attempt.json()["status"] == "incorrect"

        # item already failed via the japanese prompt, but the meaning prompt is
        # still asked and graded for complete statistics
        meaning_attempt = client.post(
            f"/api/reviews/{session_id}/answer",
            json={"item_id": item_id, "prompt_type": "meaning", "submitted_answer": "check"},
        )
        assert meaning_attempt.status_code == 200
        assert meaning_attempt.json()["status"] == "correct"
        assert meaning_attempt.json()["item_resolved"] is True
        assert meaning_attempt.json()["item_passed"] is False
        assert meaning_attempt.json()["new_srs_stage"] == 1  # demoted, floored at Apprentice 1 (was already 1)

        complete_response = client.post(f"/api/reviews/{session_id}/complete")
        assert complete_response.status_code == 200
        assert complete_response.json()["results"] == [
            {"item_id": item_id, "passed": False, "new_srs_stage": 1}
        ]

        dashboard = client.get("/api/dashboard").json()
        assert dashboard["daily_streak"] == 1  # a real review must count toward the streak
    finally:
        app.dependency_overrides.clear()


def test_start_review_400_when_none_due(engine):
    app.dependency_overrides[get_engine] = lambda: engine
    try:
        client = TestClient(app)
        response = client.post("/api/reviews/start")
        assert response.status_code == 400
    finally:
        app.dependency_overrides.clear()


def test_answer_404_for_unknown_session(engine):
    app.dependency_overrides[get_engine] = lambda: engine
    try:
        client = TestClient(app)
        response = client.post(
            "/api/reviews/999/answer",
            json={"item_id": 1, "prompt_type": "meaning", "submitted_answer": "x"},
        )
        assert response.status_code == 404
    finally:
        app.dependency_overrides.clear()


def test_complete_404_for_unknown_session(engine):
    app.dependency_overrides[get_engine] = lambda: engine
    try:
        client = TestClient(app)
        response = client.post("/api/reviews/999/complete")
        assert response.status_code == 404
    finally:
        app.dependency_overrides.clear()
