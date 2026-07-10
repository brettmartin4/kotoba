from datetime import datetime, timezone
from typing import Dict, List, Optional, Set

from sqlalchemy import delete, insert, select, update
from sqlalchemy.engine import Connection

from app.models import examples as examples_table
from app.models import item_meanings, item_notes
from app.models import similar_items as similar_items_table
from app.models import review_attempts, review_sessions, source_items, sources, study_progress, vocab_items
from app.services.text_normalization import normalize_meaning

SRS_GROUPS = {
    "unstarted": (0, 0),
    "apprentice": (1, 4),
    "guru": (5, 6),
    "master": (7, 7),
    "enlightened": (8, 8),
    "burned": (9, 9),
}

STAGE_LABELS = {
    0: "Unstarted",
    1: "Apprentice 1",
    2: "Apprentice 2",
    3: "Apprentice 3",
    4: "Apprentice 4",
    5: "Guru 1",
    6: "Guru 2",
    7: "Master",
    8: "Enlightened",
    9: "Burned",
}


class ItemNotFoundError(Exception):
    pass


class SynonymNotFoundError(Exception):
    pass


class CannotDeleteImportedMeaningError(Exception):
    pass


def _now_naive() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _search_item_ids(conn: Connection, search: str) -> Set[int]:
    """Substring match (case-insensitive) across every field spec 18 lists:
    japanese/kana/romaji, meanings, notes/mnemonics, source name/note, similar items."""
    pattern = f"%{search.lower()}%"
    ids: Set[int] = set()

    rows = conn.execute(
        select(vocab_items.c.id).where(
            vocab_items.c.japanese.ilike(pattern)
            | vocab_items.c.kana.ilike(pattern)
            | vocab_items.c.romaji.ilike(pattern)
        )
    ).all()
    ids.update(r[0] for r in rows)

    rows = conn.execute(select(item_meanings.c.item_id).where(item_meanings.c.meaning.ilike(pattern))).all()
    ids.update(r[0] for r in rows)

    rows = conn.execute(
        select(item_notes.c.item_id).where(
            item_notes.c.note_text.ilike(pattern) | item_notes.c.mnemonic_text.ilike(pattern)
        )
    ).all()
    ids.update(r[0] for r in rows)

    rows = conn.execute(
        select(similar_items_table.c.item_id).where(similar_items_table.c.similar_text.ilike(pattern))
    ).all()
    ids.update(r[0] for r in rows)

    rows = conn.execute(
        select(source_items.c.item_id)
        .select_from(source_items.join(sources, source_items.c.source_id == sources.c.id))
        .where(source_items.c.source_note.ilike(pattern) | sources.c.display_name.ilike(pattern))
    ).all()
    ids.update(r[0] for r in rows)

    return ids


def _source_filtered_item_ids(conn: Connection, source_id: int, active_filter: str) -> Set[int]:
    query = select(source_items.c.item_id).where(source_items.c.source_id == source_id)
    if active_filter == "active_only":
        query = query.where(source_items.c.is_active.is_(True))
    elif active_filter == "inactive_only":
        query = query.where(source_items.c.is_active.is_(False))
    return {r[0] for r in conn.execute(query)}


def _active_filter_item_ids(conn: Connection, active_filter: str) -> Optional[Set[int]]:
    """Only used when no source_id is given -- 'does this item have any membership
    matching this activity state, in any source.' Returns None for 'all' (no restriction)."""
    if active_filter == "active_only":
        rows = conn.execute(select(source_items.c.item_id).where(source_items.c.is_active.is_(True))).all()
    elif active_filter == "inactive_only":
        rows = conn.execute(select(source_items.c.item_id).where(source_items.c.is_active.is_(False))).all()
    else:
        return None
    return {r[0] for r in rows}


def _srs_group_item_ids(conn: Connection, srs_group: str) -> Optional[Set[int]]:
    if srs_group not in SRS_GROUPS:
        return None
    low, high = SRS_GROUPS[srs_group]
    rows = conn.execute(select(study_progress.c.item_id).where(study_progress.c.srs_stage.between(low, high))).all()
    return {r[0] for r in rows}


def _build_browse_row(conn: Connection, item_row) -> dict:
    item_id = item_row["id"]
    membership_rows = conn.execute(
        select(source_items.c.source_id, sources.c.display_name, source_items.c.is_active, source_items.c.source_level)
        .select_from(source_items.join(sources, source_items.c.source_id == sources.c.id))
        .where(source_items.c.item_id == item_id)
    ).all()
    stage = conn.execute(select(study_progress.c.srs_stage).where(study_progress.c.item_id == item_id)).scalar()
    meanings = [r[0] for r in conn.execute(select(item_meanings.c.meaning).where(item_meanings.c.item_id == item_id))]

    return {
        "item_id": item_id,
        "item_type": item_row["item_type"],
        "japanese": item_row["japanese"],
        "kana": item_row["kana"],
        "romaji": item_row["romaji"],
        "meanings": meanings,
        "srs_stage": stage,
        "srs_stage_label": STAGE_LABELS.get(stage, "Unknown"),
        "sources": [
            {
                "source_id": source_id,
                "display_name": display_name,
                "is_active": is_active,
                "source_level": source_level,
            }
            for source_id, display_name, is_active, source_level in membership_rows
        ],
    }


def list_items(
    conn: Connection,
    *,
    search: Optional[str] = None,
    source_id: Optional[int] = None,
    item_type: Optional[str] = None,
    srs_group: str = "all",
    active_filter: str = "active_only",
) -> List[dict]:
    candidate_ids: Optional[Set[int]] = None

    def intersect(ids: Set[int]) -> None:
        nonlocal candidate_ids
        candidate_ids = ids if candidate_ids is None else candidate_ids & ids

    if search:
        intersect(_search_item_ids(conn, search))

    if source_id is not None:
        intersect(_source_filtered_item_ids(conn, source_id, active_filter))
    else:
        active_ids = _active_filter_item_ids(conn, active_filter)
        if active_ids is not None:
            intersect(active_ids)

    srs_ids = _srs_group_item_ids(conn, srs_group)
    if srs_ids is not None:
        intersect(srs_ids)

    query = select(vocab_items).order_by(vocab_items.c.japanese)
    if item_type:
        query = query.where(vocab_items.c.item_type == item_type)
    if candidate_ids is not None:
        if not candidate_ids:
            return []
        query = query.where(vocab_items.c.id.in_(candidate_ids))

    item_rows = conn.execute(query).mappings().all()
    return [_build_browse_row(conn, row) for row in item_rows]


def get_item_page(conn: Connection, item_id: int) -> Optional[dict]:
    item = conn.execute(select(vocab_items).where(vocab_items.c.id == item_id)).mappings().first()
    if item is None:
        return None

    meaning_rows = conn.execute(
        select(item_meanings).where(item_meanings.c.item_id == item_id).order_by(item_meanings.c.id)
    ).mappings().all()

    example_rows = conn.execute(
        select(
            examples_table.c.japanese_sentence,
            examples_table.c.kana_sentence,
            examples_table.c.english_translation,
        ).where(examples_table.c.item_id == item_id)
    ).all()

    similar = [
        r[0]
        for r in conn.execute(
            select(similar_items_table.c.similar_text).where(similar_items_table.c.item_id == item_id)
        )
    ]

    membership_rows = conn.execute(
        select(
            source_items.c.source_id,
            sources.c.display_name,
            source_items.c.is_active,
            source_items.c.source_level,
            source_items.c.level_position,
            source_items.c.source_note,
        )
        .select_from(source_items.join(sources, source_items.c.source_id == sources.c.id))
        .where(source_items.c.item_id == item_id)
    ).all()

    progress = conn.execute(select(study_progress).where(study_progress.c.item_id == item_id)).mappings().first()
    note_row = conn.execute(select(item_notes).where(item_notes.c.item_id == item_id)).mappings().first()

    history_rows = conn.execute(
        select(review_attempts.c.prompt_type, review_attempts.c.is_correct, review_attempts.c.created_at)
        .select_from(review_attempts.join(review_sessions, review_attempts.c.session_id == review_sessions.c.id))
        .where(review_attempts.c.item_id == item_id, review_sessions.c.session_type == "review")
        .order_by(review_attempts.c.created_at.desc())
        .limit(10)
    ).all()

    stage = progress["srs_stage"] if progress else 0
    accuracy_percent = None
    if progress and progress["total_reviews"]:
        accuracy_percent = round(progress["correct_reviews"] / progress["total_reviews"] * 100, 1)

    return {
        "item_id": item["id"],
        "item_type": item["item_type"],
        "japanese": item["japanese"],
        "kana": item["kana"],
        "romaji": item["romaji"],
        "part_of_speech": item["part_of_speech"],
        "meanings": [{"id": r["id"], "meaning": r["meaning"], "origin": r["origin"]} for r in meaning_rows],
        "examples": [
            {"japanese_sentence": ja, "kana_sentence": ka, "english_translation": en}
            for ja, ka, en in example_rows
        ],
        "similar_items": similar,
        "sources": [
            {
                "source_id": source_id,
                "display_name": display_name,
                "is_active": is_active,
                "source_level": source_level,
                "level_position": level_position,
                "source_note": source_note,
            }
            for source_id, display_name, is_active, source_level, level_position, source_note in membership_rows
        ],
        "srs": {
            "stage": stage,
            "stage_label": STAGE_LABELS.get(stage, "Unknown"),
            "next_review_at": progress["next_review_at"] if progress else None,
            "learned_at": progress["learned_at"] if progress else None,
            "burned_at": progress["burned_at"] if progress else None,
            "total_reviews": progress["total_reviews"] if progress else 0,
            "correct_reviews": progress["correct_reviews"] if progress else 0,
            "incorrect_reviews": progress["incorrect_reviews"] if progress else 0,
            "meaning_correct": progress["meaning_correct"] if progress else 0,
            "meaning_incorrect": progress["meaning_incorrect"] if progress else 0,
            "japanese_correct": progress["japanese_correct"] if progress else 0,
            "japanese_incorrect": progress["japanese_incorrect"] if progress else 0,
            "current_correct_streak": progress["current_correct_streak"] if progress else 0,
            "longest_correct_streak": progress["longest_correct_streak"] if progress else 0,
            "accuracy_percent": accuracy_percent,
        },
        "notes": {
            "note_text": note_row["note_text"] if note_row else None,
            "mnemonic_text": note_row["mnemonic_text"] if note_row else None,
        },
        "review_history": [
            {"prompt_type": pt, "is_correct": ic, "created_at": ca} for pt, ic, ca in history_rows
        ],
    }


def add_synonym(conn: Connection, item_id: int, meaning: str) -> dict:
    item_exists = conn.execute(select(vocab_items.c.id).where(vocab_items.c.id == item_id)).scalar()
    if item_exists is None:
        raise ItemNotFoundError(f"Item {item_id} not found")

    normalized = normalize_meaning(meaning)
    existing = conn.execute(
        select(item_meanings).where(
            item_meanings.c.item_id == item_id, item_meanings.c.normalized_meaning == normalized
        )
    ).mappings().first()
    if existing:
        return {"id": existing["id"], "meaning": existing["meaning"], "origin": existing["origin"]}

    new_id = conn.execute(
        insert(item_meanings).values(
            item_id=item_id, meaning=meaning, normalized_meaning=normalized, origin="user_synonym"
        )
    ).inserted_primary_key[0]
    return {"id": new_id, "meaning": meaning, "origin": "user_synonym"}


def delete_synonym(conn: Connection, item_id: int, synonym_id: int) -> None:
    row = conn.execute(
        select(item_meanings).where(item_meanings.c.id == synonym_id, item_meanings.c.item_id == item_id)
    ).mappings().first()
    if row is None:
        raise SynonymNotFoundError(f"Synonym {synonym_id} not found for item {item_id}")
    if row["origin"] != "user_synonym":
        raise CannotDeleteImportedMeaningError("Imported meanings cannot be deleted through this endpoint")
    conn.execute(delete(item_meanings).where(item_meanings.c.id == synonym_id))


def update_notes(conn: Connection, item_id: int, updates: Dict[str, Optional[str]]) -> Optional[dict]:
    item_exists = conn.execute(select(vocab_items.c.id).where(vocab_items.c.id == item_id)).scalar()
    if item_exists is None:
        return None

    existing = conn.execute(select(item_notes).where(item_notes.c.item_id == item_id)).mappings().first()
    note_text = updates.get("note_text", existing["note_text"] if existing else None)
    mnemonic_text = updates.get("mnemonic_text", existing["mnemonic_text"] if existing else None)
    now = _now_naive()

    if existing is None:
        conn.execute(
            insert(item_notes).values(
                item_id=item_id, note_text=note_text, mnemonic_text=mnemonic_text, updated_at=now
            )
        )
    else:
        conn.execute(
            update(item_notes)
            .where(item_notes.c.item_id == item_id)
            .values(note_text=note_text, mnemonic_text=mnemonic_text, updated_at=now)
        )

    return {"note_text": note_text, "mnemonic_text": mnemonic_text}
