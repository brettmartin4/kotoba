from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.config import get_wordbank_folder
from app.core.db import get_engine
from app.main import app
from app.models import vocab_items
from app.services.import_service import run_import
from tests.helpers import write_wordbank


def _row(**overrides):
    row = {
        "item_type": "word",
        "japanese": "確認",
        "kana": "かくにん",
        "romaji": "kakunin",
        "meanings": "confirm",
        "part_of_speech": "noun",
    }
    row.update(overrides)
    return row


def _stage_duplicate(engine, wordbank_dir):
    write_wordbank(wordbank_dir / "work.xlsx", [_row()])
    run_import(engine, wordbank_dir)
    with engine.connect() as conn:
        target_item_id = conn.execute(select(vocab_items.c.id)).scalar()

    write_wordbank(wordbank_dir / "manga.xlsx", [_row(japanese="別の漢字")])
    run_import(engine, wordbank_dir)
    return target_item_id


def _stage_change(engine, wordbank_dir):
    path = wordbank_dir / "work.xlsx"
    write_wordbank(path, [_row()])
    run_import(engine, wordbank_dir)
    with engine.connect() as conn:
        item_id = conn.execute(select(vocab_items.c.id)).scalar()

    write_wordbank(path, [_row(romaji="kakunin2")])
    run_import(engine, wordbank_dir)
    return item_id


def test_duplicate_queue_and_merge_endpoint(engine, wordbank_dir):
    target_item_id = _stage_duplicate(engine, wordbank_dir)

    app.dependency_overrides[get_engine] = lambda: engine
    app.dependency_overrides[get_wordbank_folder] = lambda: wordbank_dir
    try:
        client = TestClient(app)

        pending = client.get("/api/import/duplicates/pending")
        assert pending.status_code == 200
        body = pending.json()
        assert len(body) == 1
        duplicate_id = body[0]["id"]
        assert body[0]["candidates"][0]["item_id"] == target_item_id

        merge_response = client.post(
            f"/api/import/duplicates/{duplicate_id}/merge", json={"target_item_id": target_item_id}
        )
        assert merge_response.status_code == 200
        assert merge_response.json()["status"] == "merged"

        assert client.get("/api/import/duplicates/pending").json() == []

        # already resolved -> 409
        again = client.post(
            f"/api/import/duplicates/{duplicate_id}/merge", json={"target_item_id": target_item_id}
        )
        assert again.status_code == 409
    finally:
        app.dependency_overrides.clear()


def test_merge_endpoint_rejects_invalid_target(engine, wordbank_dir):
    target_item_id = _stage_duplicate(engine, wordbank_dir)

    app.dependency_overrides[get_engine] = lambda: engine
    app.dependency_overrides[get_wordbank_folder] = lambda: wordbank_dir
    try:
        client = TestClient(app)
        duplicate_id = client.get("/api/import/duplicates/pending").json()[0]["id"]

        response = client.post(
            f"/api/import/duplicates/{duplicate_id}/merge", json={"target_item_id": target_item_id + 999}
        )
        assert response.status_code == 400
    finally:
        app.dependency_overrides.clear()


def test_keep_separate_endpoint(engine, wordbank_dir):
    _stage_duplicate(engine, wordbank_dir)

    app.dependency_overrides[get_engine] = lambda: engine
    app.dependency_overrides[get_wordbank_folder] = lambda: wordbank_dir
    try:
        client = TestClient(app)
        duplicate_id = client.get("/api/import/duplicates/pending").json()[0]["id"]

        response = client.post(f"/api/import/duplicates/{duplicate_id}/keep-separate")
        assert response.status_code == 200
        assert response.json()["status"] == "kept_separate"

        assert client.get("/api/import/duplicates/pending").json() == []
    finally:
        app.dependency_overrides.clear()


def test_skip_duplicate_endpoint(engine, wordbank_dir):
    _stage_duplicate(engine, wordbank_dir)

    app.dependency_overrides[get_engine] = lambda: engine
    app.dependency_overrides[get_wordbank_folder] = lambda: wordbank_dir
    try:
        client = TestClient(app)
        duplicate_id = client.get("/api/import/duplicates/pending").json()[0]["id"]

        response = client.post(f"/api/import/duplicates/{duplicate_id}/skip")
        assert response.status_code == 200
        assert response.json()["status"] == "skipped"
    finally:
        app.dependency_overrides.clear()


def test_change_queue_approve_and_reject_endpoints(engine, wordbank_dir):
    _stage_change(engine, wordbank_dir)

    app.dependency_overrides[get_engine] = lambda: engine
    app.dependency_overrides[get_wordbank_folder] = lambda: wordbank_dir
    try:
        client = TestClient(app)

        pending = client.get("/api/import/changes/pending")
        assert pending.status_code == 200
        body = pending.json()
        assert len(body) == 1
        change_id = body[0]["id"]
        assert body[0]["current_item"]["romaji"] == "kakunin"
        assert body[0]["raw_data"]["romaji"] == "kakunin2"

        approve_response = client.post(f"/api/import/changes/{change_id}/approve")
        assert approve_response.status_code == 200
        assert approve_response.json()["status"] == "approved"

        assert client.get("/api/import/changes/pending").json() == []

        already = client.post(f"/api/import/changes/{change_id}/approve")
        assert already.status_code == 409
    finally:
        app.dependency_overrides.clear()


def test_reject_change_endpoint(engine, wordbank_dir):
    _stage_change(engine, wordbank_dir)

    app.dependency_overrides[get_engine] = lambda: engine
    app.dependency_overrides[get_wordbank_folder] = lambda: wordbank_dir
    try:
        client = TestClient(app)
        change_id = client.get("/api/import/changes/pending").json()[0]["id"]

        response = client.post(f"/api/import/changes/{change_id}/reject")
        assert response.status_code == 200
        assert response.json()["status"] == "skipped"
    finally:
        app.dependency_overrides.clear()


def test_unknown_import_run_item_returns_404(engine):
    app.dependency_overrides[get_engine] = lambda: engine
    try:
        client = TestClient(app)
        assert client.post("/api/import/duplicates/999/merge", json={"target_item_id": 1}).status_code == 404
        assert client.post("/api/import/duplicates/999/keep-separate").status_code == 404
        assert client.post("/api/import/duplicates/999/skip").status_code == 404
        assert client.post("/api/import/changes/999/approve").status_code == 404
        assert client.post("/api/import/changes/999/reject").status_code == 404
    finally:
        app.dependency_overrides.clear()
