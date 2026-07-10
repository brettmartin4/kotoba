from fastapi.testclient import TestClient
from sqlalchemy import insert

from app.core.db import get_engine
from app.main import app
from app.models import item_meanings, source_items, sources, study_progress, vocab_items


def _seed_item(engine, japanese="確認", kana="かくにん", meaning="confirm"):
    with engine.begin() as conn:
        source_id = conn.execute(
            insert(sources).values(source_key="work", display_name="Work", file_path="work.xlsx")
        ).inserted_primary_key[0]
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
            insert(item_meanings).values(
                item_id=item_id, meaning=meaning, normalized_meaning=meaning.lower(), origin="imported"
            )
        )
        conn.execute(insert(study_progress).values(item_id=item_id, srs_stage=0))
        conn.execute(
            insert(source_items).values(
                source_id=source_id, item_id=item_id, source_level=1, level_position=1, is_active=True
            )
        )
    return item_id


def test_list_items_endpoint(engine):
    item_id = _seed_item(engine)

    app.dependency_overrides[get_engine] = lambda: engine
    try:
        client = TestClient(app)
        response = client.get("/api/items", params={"search": "confirm"})
        assert response.status_code == 200
        body = response.json()
        assert len(body) == 1
        assert body[0]["item_id"] == item_id
        assert body[0]["sources"][0]["display_name"] == "Work"
    finally:
        app.dependency_overrides.clear()


def test_get_item_detail_endpoint(engine):
    item_id = _seed_item(engine)

    app.dependency_overrides[get_engine] = lambda: engine
    try:
        client = TestClient(app)
        response = client.get(f"/api/items/{item_id}")
        assert response.status_code == 200
        body = response.json()
        assert body["japanese"] == "確認"
        assert body["srs"]["stage_label"] == "Unstarted"

        missing = client.get("/api/items/999")
        assert missing.status_code == 404
    finally:
        app.dependency_overrides.clear()


def test_synonym_add_and_delete_endpoints(engine):
    item_id = _seed_item(engine)

    app.dependency_overrides[get_engine] = lambda: engine
    try:
        client = TestClient(app)

        add_response = client.post(f"/api/items/{item_id}/synonyms", json={"meaning": "double-check"})
        assert add_response.status_code == 200
        synonym_id = add_response.json()["id"]
        assert add_response.json()["origin"] == "user_synonym"

        blank_response = client.post(f"/api/items/{item_id}/synonyms", json={"meaning": "   "})
        assert blank_response.status_code == 422

        delete_response = client.delete(f"/api/items/{item_id}/synonyms/{synonym_id}")
        assert delete_response.status_code == 200

        missing_delete = client.delete(f"/api/items/{item_id}/synonyms/{synonym_id}")
        assert missing_delete.status_code == 404
    finally:
        app.dependency_overrides.clear()


def test_cannot_delete_imported_meaning_via_synonym_endpoint(engine):
    item_id = _seed_item(engine)

    app.dependency_overrides[get_engine] = lambda: engine
    try:
        client = TestClient(app)
        detail = client.get(f"/api/items/{item_id}").json()
        imported_meaning_id = detail["meanings"][0]["id"]

        response = client.delete(f"/api/items/{item_id}/synonyms/{imported_meaning_id}")
        assert response.status_code == 403
    finally:
        app.dependency_overrides.clear()


def test_add_synonym_404_for_unknown_item(engine):
    app.dependency_overrides[get_engine] = lambda: engine
    try:
        client = TestClient(app)
        response = client.post("/api/items/999/synonyms", json={"meaning": "x"})
        assert response.status_code == 404
    finally:
        app.dependency_overrides.clear()


def test_patch_notes_partial_update(engine):
    item_id = _seed_item(engine)

    app.dependency_overrides[get_engine] = lambda: engine
    try:
        client = TestClient(app)

        first = client.patch(f"/api/items/{item_id}/notes", json={"note_text": "hello", "mnemonic_text": "world"})
        assert first.status_code == 200
        assert first.json() == {"note_text": "hello", "mnemonic_text": "world"}

        second = client.patch(f"/api/items/{item_id}/notes", json={"note_text": "updated"})
        assert second.status_code == 200
        assert second.json() == {"note_text": "updated", "mnemonic_text": "world"}

        missing = client.patch("/api/items/999/notes", json={"note_text": "x"})
        assert missing.status_code == 404
    finally:
        app.dependency_overrides.clear()
