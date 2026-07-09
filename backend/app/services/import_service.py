import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from sqlalchemy import insert, select, update
from sqlalchemy.engine import Connection, Engine

from app.core.config import settings
from app.models import (
    examples as examples_table,
)
from app.models import (
    import_run_items,
    import_runs,
    item_meanings,
    item_forms,
    similar_items as similar_items_table,
    source_items,
    sources,
    study_progress,
    vocab_items,
)
from app.services.excel_parser import ParsedExample, ParsedRow, WordBankFileError, parse_workbook
from app.services.text_normalization import normalize_japanese, normalize_kana, normalize_meaning


def _now() -> datetime:
    return datetime.now(timezone.utc)


def humanize_source_key(key: str) -> str:
    return key.replace("_", " ").replace("-", " ").title()


def run_import(engine: Engine, wordbank_folder: Path) -> dict:
    wordbank_folder = Path(wordbank_folder)
    status_counts: Dict[str, int] = {}

    with engine.begin() as conn:
        run_id = conn.execute(
            insert(import_runs).values(started_at=_now(), status="running")
        ).inserted_primary_key[0]

        xlsx_files = (
            sorted(p for p in wordbank_folder.glob("*.xlsx") if not p.name.startswith("~$"))
            if wordbank_folder.exists()
            else []
        )

        for file_path in xlsx_files:
            _import_file(conn, run_id, file_path, status_counts)

        conn.execute(
            update(import_runs)
            .where(import_runs.c.id == run_id)
            .values(completed_at=_now(), status="completed", summary_json=json.dumps(status_counts))
        )

    return {"import_run_id": run_id, "summary": status_counts}


def _record(
    conn: Connection,
    status_counts: Dict[str, int],
    run_id: int,
    source_id: int,
    *,
    item_id: Optional[int] = None,
    candidate_item_ids: Optional[List[int]] = None,
    row_number: Optional[int] = None,
    status: str,
    message: Optional[str] = None,
    raw_data: Optional[dict] = None,
) -> None:
    conn.execute(
        insert(import_run_items).values(
            import_run_id=run_id,
            source_id=source_id,
            item_id=item_id,
            candidate_item_ids_json=json.dumps(candidate_item_ids) if candidate_item_ids else None,
            row_number=row_number,
            status=status,
            message=message,
            raw_data_json=json.dumps(raw_data) if raw_data is not None else None,
        )
    )
    status_counts[status] = status_counts.get(status, 0) + 1


def _row_to_dict(row: ParsedRow) -> dict:
    return {
        "item_type": row.item_type,
        "japanese": row.japanese,
        "kana": row.kana,
        "romaji": row.romaji,
        "meanings": row.meanings,
        "part_of_speech": row.part_of_speech,
        "examples": [ex.__dict__ for ex in row.examples],
        "similar_items": row.similar_items,
        "source_note": row.source_note,
    }


def _import_file(conn: Connection, run_id: int, file_path: Path, status_counts: Dict[str, int]) -> None:
    source_key = file_path.stem.lower()
    source_row = conn.execute(
        select(sources).where(sources.c.source_key == source_key)
    ).mappings().first()

    if source_row is None:
        source_id = conn.execute(
            insert(sources).values(
                source_key=source_key,
                display_name=humanize_source_key(source_key),
                file_path=str(file_path),
                is_active=True,
            )
        ).inserted_primary_key[0]
    else:
        source_id = source_row["id"]
        conn.execute(update(sources).where(sources.c.id == source_id).values(file_path=str(file_path)))

    try:
        parsed = parse_workbook(file_path)
    except WordBankFileError as exc:
        _record(conn, status_counts, run_id, source_id, status="error", message=str(exc))
        return

    seen_item_ids: Set[int] = set()

    for row_error in parsed.errors:
        _record(
            conn, status_counts, run_id, source_id,
            row_number=row_error.row_number, status="error", message=row_error.message,
        )

    for row in parsed.rows:
        item_id, status, message, candidates = _process_row(conn, source_id, row)
        _record(
            conn, status_counts, run_id, source_id,
            item_id=item_id, candidate_item_ids=candidates,
            row_number=row.row_number, status=status, message=message,
            raw_data=_row_to_dict(row),
        )
        if item_id is not None:
            seen_item_ids.add(item_id)

    active_rows = conn.execute(
        select(source_items.c.id, source_items.c.item_id).where(
            source_items.c.source_id == source_id, source_items.c.is_active.is_(True)
        )
    ).all()
    for source_item_id, item_id in active_rows:
        if item_id not in seen_item_ids:
            conn.execute(
                update(source_items).where(source_items.c.id == source_item_id).values(is_active=False)
            )
            _record(conn, status_counts, run_id, source_id, item_id=item_id, status="inactive")

    conn.execute(update(sources).where(sources.c.id == source_id).values(last_imported_at=_now()))


def _find_exact_match(conn: Connection, normalized_japanese: str, normalized_kana: str):
    return conn.execute(
        select(vocab_items).where(
            vocab_items.c.normalized_japanese == normalized_japanese,
            vocab_items.c.normalized_kana == normalized_kana,
        )
    ).mappings().first()


def _find_partial_matches(conn: Connection, normalized_japanese: str, normalized_kana: str):
    rows = conn.execute(
        select(vocab_items).where(
            (vocab_items.c.normalized_japanese == normalized_japanese)
            | (vocab_items.c.normalized_kana == normalized_kana)
        )
    ).mappings().all()
    return [
        r for r in rows
        if not (r["normalized_japanese"] == normalized_japanese and r["normalized_kana"] == normalized_kana)
    ]


def _next_slot(conn: Connection, source_id: int) -> Tuple[int, int]:
    row = conn.execute(
        select(source_items.c.source_level, source_items.c.level_position)
        .where(source_items.c.source_id == source_id)
        .order_by(source_items.c.source_level.desc(), source_items.c.level_position.desc())
        .limit(1)
    ).first()
    if row is None:
        return 1, 1
    level, position = row
    if position < settings.level_size:
        return level, position + 1
    return level + 1, 1


def _existing_meanings_all(conn: Connection, item_id: int) -> Set[str]:
    return {
        r[0] for r in conn.execute(
            select(item_meanings.c.normalized_meaning).where(item_meanings.c.item_id == item_id)
        )
    }


def _existing_meanings_imported(conn: Connection, item_id: int) -> Set[str]:
    return {
        r[0] for r in conn.execute(
            select(item_meanings.c.normalized_meaning).where(
                item_meanings.c.item_id == item_id, item_meanings.c.origin == "imported"
            )
        )
    }


def _existing_similar(conn: Connection, item_id: int) -> Set[str]:
    return {
        r[0] for r in conn.execute(
            select(similar_items_table.c.similar_text).where(similar_items_table.c.item_id == item_id)
        )
    }


def _existing_examples_for_source(conn: Connection, item_id: int, source_id: int) -> Set[Tuple[str, str, str]]:
    rows = conn.execute(
        select(
            examples_table.c.japanese_sentence,
            examples_table.c.kana_sentence,
            examples_table.c.english_translation,
        ).where(examples_table.c.item_id == item_id, examples_table.c.source_id == source_id)
    ).all()
    return {tuple(r) for r in rows}


def _insert_new_meanings(conn: Connection, item_id: int, meanings: List[str]) -> None:
    existing = _existing_meanings_all(conn, item_id)
    for meaning in meanings:
        normalized = normalize_meaning(meaning)
        if normalized not in existing:
            conn.execute(
                insert(item_meanings).values(
                    item_id=item_id, meaning=meaning, normalized_meaning=normalized, origin="imported",
                )
            )
            existing.add(normalized)


def _insert_new_similar_items(conn: Connection, item_id: int, similar: List[str]) -> None:
    existing = _existing_similar(conn, item_id)
    for text in similar:
        if text not in existing:
            conn.execute(insert(similar_items_table).values(item_id=item_id, similar_text=text))
            existing.add(text)


def _insert_examples_for_source(
    conn: Connection, item_id: int, source_id: int, examples_list: List[ParsedExample]
) -> None:
    for example in examples_list:
        conn.execute(
            insert(examples_table).values(
                item_id=item_id,
                source_id=source_id,
                japanese_sentence=example.japanese,
                kana_sentence=example.kana,
                english_translation=example.english,
            )
        )


def _create_vocab_item(conn: Connection, row: ParsedRow) -> int:
    normalized_japanese = normalize_japanese(row.japanese)
    normalized_kana = normalize_kana(row.kana)

    item_id = conn.execute(
        insert(vocab_items).values(
            item_type=row.item_type,
            japanese=row.japanese,
            kana=row.kana,
            romaji=row.romaji,
            part_of_speech=row.part_of_speech,
            normalized_japanese=normalized_japanese,
            normalized_kana=normalized_kana,
        )
    ).inserted_primary_key[0]

    conn.execute(
        insert(item_forms).values(
            item_id=item_id, form=row.japanese, normalized_form=normalized_japanese, form_type="display",
        )
    )
    conn.execute(
        insert(item_forms).values(
            item_id=item_id, form=row.kana, normalized_form=normalized_kana, form_type="kana",
        )
    )

    _insert_new_meanings(conn, item_id, row.meanings)
    _insert_new_similar_items(conn, item_id, row.similar_items)

    conn.execute(insert(study_progress).values(item_id=item_id, srs_stage=0))

    return item_id


def _create_source_item(conn: Connection, source_id: int, item_id: int, row: ParsedRow) -> None:
    level, position = _next_slot(conn, source_id)
    conn.execute(
        insert(source_items).values(
            source_id=source_id,
            item_id=item_id,
            source_level=level,
            level_position=position,
            is_active=True,
            source_note=row.source_note,
        )
    )


def _process_row(
    conn: Connection, source_id: int, row: ParsedRow
) -> Tuple[Optional[int], str, Optional[str], Optional[List[int]]]:
    normalized_japanese = normalize_japanese(row.japanese)
    normalized_kana = normalize_kana(row.kana)

    exact = _find_exact_match(conn, normalized_japanese, normalized_kana)

    if exact is None:
        partials = _find_partial_matches(conn, normalized_japanese, normalized_kana)
        if partials:
            candidate_ids = [p["id"] for p in partials]
            message = (
                f"Matches existing item(s) {candidate_ids} on Japanese or kana only "
                "(not both); needs manual review before merging."
            )
            return None, "duplicate_pending_merge", message, candidate_ids

        item_id = _create_vocab_item(conn, row)
        _insert_examples_for_source(conn, item_id, source_id, row.examples)
        _create_source_item(conn, source_id, item_id, row)
        return item_id, "new", None, None

    item_id = exact["id"]
    existing_source_item = conn.execute(
        select(source_items).where(
            source_items.c.source_id == source_id, source_items.c.item_id == item_id
        )
    ).mappings().first()

    content_diff = False
    diff_fields: List[str] = []

    if row.romaji != exact["romaji"]:
        content_diff = True
        diff_fields.append("romaji")
    if row.part_of_speech != exact["part_of_speech"]:
        content_diff = True
        diff_fields.append("part_of_speech")

    if existing_source_item is None:
        # First time this source has contributed this item: safe to add additively,
        # since nothing existing is being overwritten, only appended.
        _insert_new_meanings(conn, item_id, row.meanings)
        _insert_new_similar_items(conn, item_id, row.similar_items)
        _insert_examples_for_source(conn, item_id, source_id, row.examples)
        _create_source_item(conn, source_id, item_id, row)
        membership_status = "added_to_source"
    else:
        row_meanings = {normalize_meaning(m) for m in row.meanings}
        row_similar = set(row.similar_items)
        row_examples = {(e.japanese, e.kana, e.english) for e in row.examples}

        if row_meanings != _existing_meanings_imported(conn, item_id):
            content_diff = True
            diff_fields.append("meanings")
        if row_similar != _existing_similar(conn, item_id):
            content_diff = True
            diff_fields.append("similar_items")
        if row_examples != _existing_examples_for_source(conn, item_id, source_id):
            content_diff = True
            diff_fields.append("examples")
        if (row.source_note or "") != (existing_source_item["source_note"] or ""):
            content_diff = True
            diff_fields.append("source_note")

        was_inactive = not existing_source_item["is_active"]
        conn.execute(
            update(source_items)
            .where(source_items.c.id == existing_source_item["id"])
            .values(is_active=True, last_seen_at=_now())
        )
        membership_status = "added_to_source" if was_inactive else "unchanged"

    if content_diff:
        message = (
            "Imported content differs from stored data (" + ", ".join(diff_fields) + "); "
            "existing data preserved pending manual approval."
        )
        return item_id, "updated_pending_approval", message, None

    return item_id, membership_status, None, None


def get_import_runs(engine: Engine) -> List[dict]:
    with engine.connect() as conn:
        rows = conn.execute(select(import_runs).order_by(import_runs.c.id.desc())).mappings().all()
        return [dict(r) for r in rows]


def get_import_run_detail(engine: Engine, run_id: int) -> Optional[dict]:
    with engine.connect() as conn:
        run = conn.execute(select(import_runs).where(import_runs.c.id == run_id)).mappings().first()
        if run is None:
            return None
        items = conn.execute(
            select(import_run_items).where(import_run_items.c.import_run_id == run_id)
        ).mappings().all()
        return {"run": dict(run), "items": [dict(i) for i in items]}
