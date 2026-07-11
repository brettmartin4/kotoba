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
    item_meaning_sources,
    item_meanings,
    item_forms,
    similar_item_sources,
    similar_items as similar_items_table,
    source_items,
    source_row_resolutions,
    sources,
    study_progress,
    vocab_items,
)
from app.services.excel_parser import ParsedExample, ParsedRow, WordBankFileError, parse_workbook
from app.services.item_service import get_item_page
from app.services.text_normalization import normalize_japanese, normalize_kana, normalize_meaning


class ImportRunItemNotFoundError(Exception):
    pass


class AlreadyResolvedError(Exception):
    pass


class InvalidMergeTargetError(Exception):
    pass


class ItemNotFoundError(Exception):
    pass


class SourceRelationshipNotFoundError(Exception):
    pass


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


def _existing_examples_for_source(conn: Connection, item_id: int, source_id: int) -> Set[Tuple[str, str, str]]:
    rows = conn.execute(
        select(
            examples_table.c.japanese_sentence,
            examples_table.c.kana_sentence,
            examples_table.c.english_translation,
        ).where(examples_table.c.item_id == item_id, examples_table.c.source_id == source_id)
    ).all()
    return {tuple(r) for r in rows}


def _meanings_attributed_to_source(conn: Connection, item_id: int, source_id: int) -> Set[str]:
    """Imported meanings this specific source has previously contributed to this
    item, per item_meaning_sources -- never includes user_synonym-origin meanings,
    and never includes meanings only some *other* source contributed."""
    rows = conn.execute(
        select(item_meanings.c.normalized_meaning)
        .select_from(item_meanings.join(item_meaning_sources, item_meanings.c.id == item_meaning_sources.c.item_meaning_id))
        .where(
            item_meanings.c.item_id == item_id,
            item_meanings.c.origin == "imported",
            item_meaning_sources.c.source_id == source_id,
        )
    ).all()
    return {r[0] for r in rows}


def _similar_items_attributed_to_source(conn: Connection, item_id: int, source_id: int) -> Set[str]:
    rows = conn.execute(
        select(similar_items_table.c.similar_text)
        .select_from(
            similar_items_table.join(
                similar_item_sources, similar_items_table.c.id == similar_item_sources.c.similar_item_id
            )
        )
        .where(similar_items_table.c.item_id == item_id, similar_item_sources.c.source_id == source_id)
    ).all()
    return {r[0] for r in rows}


def _ensure_meaning_source_link(conn: Connection, item_meaning_id: int, source_id: int) -> None:
    exists = conn.execute(
        select(item_meaning_sources.c.id).where(
            item_meaning_sources.c.item_meaning_id == item_meaning_id,
            item_meaning_sources.c.source_id == source_id,
        )
    ).first()
    if exists is None:
        conn.execute(insert(item_meaning_sources).values(item_meaning_id=item_meaning_id, source_id=source_id))


def _ensure_similar_item_source_link(conn: Connection, similar_item_id: int, source_id: int) -> None:
    exists = conn.execute(
        select(similar_item_sources.c.id).where(
            similar_item_sources.c.similar_item_id == similar_item_id,
            similar_item_sources.c.source_id == source_id,
        )
    ).first()
    if exists is None:
        conn.execute(
            insert(similar_item_sources).values(similar_item_id=similar_item_id, source_id=source_id)
        )


def _insert_new_meanings(conn: Connection, item_id: int, source_id: int, meanings: List[str]) -> None:
    """Adds any meanings not already present for this item, and -- for every meaning
    in the list, whether just-created or already there -- links it to source_id so
    future reimports can diff this source's own contribution precisely."""
    existing = {
        r[1]: r[0]
        for r in conn.execute(
            select(item_meanings.c.id, item_meanings.c.normalized_meaning).where(item_meanings.c.item_id == item_id)
        )
    }
    for meaning in meanings:
        normalized = normalize_meaning(meaning)
        if normalized not in existing:
            new_id = conn.execute(
                insert(item_meanings).values(
                    item_id=item_id, meaning=meaning, normalized_meaning=normalized, origin="imported",
                )
            ).inserted_primary_key[0]
            existing[normalized] = new_id
        _ensure_meaning_source_link(conn, existing[normalized], source_id)


def _insert_new_similar_items(conn: Connection, item_id: int, source_id: int, similar: List[str]) -> None:
    existing = {
        r[1]: r[0]
        for r in conn.execute(
            select(similar_items_table.c.id, similar_items_table.c.similar_text).where(
                similar_items_table.c.item_id == item_id
            )
        )
    }
    for text in similar:
        if text not in existing:
            new_id = conn.execute(
                insert(similar_items_table).values(item_id=item_id, similar_text=text)
            ).inserted_primary_key[0]
            existing[text] = new_id
        _ensure_similar_item_source_link(conn, existing[text], source_id)


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


def _create_vocab_item(conn: Connection, source_id: int, row: ParsedRow) -> int:
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

    _insert_new_meanings(conn, item_id, source_id, row.meanings)
    _insert_new_similar_items(conn, item_id, source_id, row.similar_items)

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


def _find_resolution(conn: Connection, source_id: int, normalized_japanese: str, normalized_kana: str) -> Optional[dict]:
    row = conn.execute(
        select(source_row_resolutions).where(
            source_row_resolutions.c.source_id == source_id,
            source_row_resolutions.c.normalized_japanese == normalized_japanese,
            source_row_resolutions.c.normalized_kana == normalized_kana,
        )
    ).mappings().first()
    return dict(row) if row else None


def _upsert_resolution(
    conn: Connection,
    source_id: int,
    japanese: str,
    kana: str,
    resolution_type: str,
    resolved_item_id: Optional[int],
    import_run_item_id: Optional[int],
) -> None:
    normalized_japanese = normalize_japanese(japanese)
    normalized_kana = normalize_kana(kana)
    now = _now()

    existing = conn.execute(
        select(source_row_resolutions).where(
            source_row_resolutions.c.source_id == source_id,
            source_row_resolutions.c.normalized_japanese == normalized_japanese,
            source_row_resolutions.c.normalized_kana == normalized_kana,
        )
    ).mappings().first()

    if existing is None:
        conn.execute(
            insert(source_row_resolutions).values(
                source_id=source_id,
                normalized_japanese=normalized_japanese,
                normalized_kana=normalized_kana,
                resolution_type=resolution_type,
                resolved_item_id=resolved_item_id,
                created_from_import_run_item_id=import_run_item_id,
                created_at=now,
                updated_at=now,
            )
        )
    else:
        conn.execute(
            update(source_row_resolutions)
            .where(source_row_resolutions.c.id == existing["id"])
            .values(
                resolution_type=resolution_type,
                resolved_item_id=resolved_item_id,
                created_from_import_run_item_id=import_run_item_id,
                updated_at=now,
            )
        )


def _apply_merge_content(conn: Connection, target_item_id: int, source_id: int, raw: dict) -> None:
    """Additive merge of a row's content onto an existing canonical item, plus
    creating or reactivating the source_items relationship for this source. Never
    touches vocab_items.japanese/kana/romaji/part_of_speech, study_progress,
    item_notes, or user_synonym-origin item_meanings -- shared by merge_duplicate
    and the automatic prior-resolution fast path in _process_row."""
    examples = [ParsedExample(**example) for example in raw["examples"]]
    _insert_new_meanings(conn, target_item_id, source_id, raw["meanings"])
    _insert_new_similar_items(conn, target_item_id, source_id, raw["similar_items"])
    _insert_examples_for_source(conn, target_item_id, source_id, examples)

    existing_source_item = conn.execute(
        select(source_items).where(
            source_items.c.source_id == source_id, source_items.c.item_id == target_item_id
        )
    ).mappings().first()

    if existing_source_item is None:
        level, position = _next_slot(conn, source_id)
        conn.execute(
            insert(source_items).values(
                source_id=source_id,
                item_id=target_item_id,
                source_level=level,
                level_position=position,
                is_active=True,
                source_note=raw.get("source_note"),
            )
        )
    else:
        conn.execute(
            update(source_items)
            .where(source_items.c.id == existing_source_item["id"])
            .values(is_active=True, last_seen_at=_now())
        )


def _apply_resolution(
    conn: Connection, source_id: int, row: ParsedRow, resolution: dict
) -> Tuple[Optional[int], str, Optional[str], Optional[List[int]]]:
    resolution_type = resolution["resolution_type"]

    if resolution_type == "skipped":
        return (
            None,
            "skipped",
            "Resolved as skipped in a prior duplicate review; not re-staged.",
            None,
        )

    target_item_id = resolution["resolved_item_id"]
    target = conn.execute(select(vocab_items).where(vocab_items.c.id == target_item_id)).mappings().first()
    if target is None:
        return (
            None,
            "error",
            (
                f"A prior duplicate resolution for this row points to item {target_item_id}, "
                "which no longer exists. Needs manual attention."
            ),
            None,
        )

    existing_source_item_before = conn.execute(
        select(source_items).where(
            source_items.c.source_id == source_id, source_items.c.item_id == target_item_id
        )
    ).mappings().first()
    was_inactive_or_absent = existing_source_item_before is None or not existing_source_item_before["is_active"]

    _apply_merge_content(conn, target_item_id, source_id, _row_to_dict(row))

    status = "added_to_source" if was_inactive_or_absent else "unchanged"
    return target_item_id, status, "Resolved via a prior duplicate decision.", None


def _process_row(
    conn: Connection, source_id: int, row: ParsedRow
) -> Tuple[Optional[int], str, Optional[str], Optional[List[int]]]:
    normalized_japanese = normalize_japanese(row.japanese)
    normalized_kana = normalize_kana(row.kana)

    exact = _find_exact_match(conn, normalized_japanese, normalized_kana)

    if exact is None:
        resolution = _find_resolution(conn, source_id, normalized_japanese, normalized_kana)
        if resolution is not None:
            return _apply_resolution(conn, source_id, row, resolution)

        partials = _find_partial_matches(conn, normalized_japanese, normalized_kana)
        if partials:
            candidate_ids = [p["id"] for p in partials]
            message = (
                f"Matches existing item(s) {candidate_ids} on Japanese or kana only "
                "(not both); needs manual review before merging."
            )
            return None, "duplicate_pending_merge", message, candidate_ids

        item_id = _create_vocab_item(conn, source_id, row)
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
        _insert_new_meanings(conn, item_id, source_id, row.meanings)
        _insert_new_similar_items(conn, item_id, source_id, row.similar_items)
        _insert_examples_for_source(conn, item_id, source_id, row.examples)
        _create_source_item(conn, source_id, item_id, row)
        membership_status = "added_to_source"
    else:
        row_meanings = {normalize_meaning(m) for m in row.meanings}
        row_similar = set(row.similar_items)
        row_examples = {(e.japanese, e.kana, e.english) for e in row.examples}

        # Scoped to what THIS source previously contributed, not everything any
        # source ever added to the shared canonical item (that was the bug: a
        # merge from another source made this source's unchanged reimport look
        # "changed" forever). No attribution history yet means this relationship
        # predates attribution tracking -- treat as no diff and backfill silently
        # rather than flagging a spurious first-time change.
        attributed_meanings = _meanings_attributed_to_source(conn, item_id, source_id)
        if attributed_meanings:
            if row_meanings != attributed_meanings:
                content_diff = True
                diff_fields.append("meanings")
        else:
            _insert_new_meanings(conn, item_id, source_id, row.meanings)

        attributed_similar = _similar_items_attributed_to_source(conn, item_id, source_id)
        if attributed_similar:
            if row_similar != attributed_similar:
                content_diff = True
                diff_fields.append("similar_items")
        else:
            _insert_new_similar_items(conn, item_id, source_id, row.similar_items)

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


def _format_import_run_item(row: dict) -> dict:
    formatted = dict(row)
    raw_data_json = formatted.pop("raw_data_json", None)
    candidate_item_ids_json = formatted.pop("candidate_item_ids_json", None)
    formatted["raw_data"] = json.loads(raw_data_json) if raw_data_json else None
    formatted["candidate_item_ids"] = json.loads(candidate_item_ids_json) if candidate_item_ids_json else None
    return formatted


def get_import_run_detail(engine: Engine, run_id: int) -> Optional[dict]:
    with engine.connect() as conn:
        run = conn.execute(select(import_runs).where(import_runs.c.id == run_id)).mappings().first()
        if run is None:
            return None
        items = conn.execute(
            select(import_run_items).where(import_run_items.c.import_run_id == run_id)
        ).mappings().all()
        return {"run": dict(run), "items": [_format_import_run_item(dict(i)) for i in items]}


def _get_pending_import_run_item(conn: Connection, import_run_item_id: int, expected_status: str) -> dict:
    row = conn.execute(
        select(import_run_items).where(import_run_items.c.id == import_run_item_id)
    ).mappings().first()
    if row is None:
        raise ImportRunItemNotFoundError(f"Import run item {import_run_item_id} not found")
    if row["status"] != expected_status:
        raise AlreadyResolvedError(
            f"Import run item {import_run_item_id} is already resolved (status={row['status']!r})"
        )
    return dict(row)


def _row_from_raw_data(raw: dict, row_number: Optional[int]) -> ParsedRow:
    return ParsedRow(
        row_number=row_number,
        item_type=raw["item_type"],
        japanese=raw["japanese"],
        kana=raw["kana"],
        romaji=raw["romaji"],
        meanings=raw["meanings"],
        part_of_speech=raw["part_of_speech"],
        examples=[ParsedExample(**example) for example in raw["examples"]],
        similar_items=raw["similar_items"],
        source_note=raw.get("source_note"),
    )


def _enrich_with_source_name(conn: Connection, formatted_item: dict) -> dict:
    formatted_item["source_display_name"] = conn.execute(
        select(sources.c.display_name).where(sources.c.id == formatted_item["source_id"])
    ).scalar()
    return formatted_item


def get_pending_duplicates(engine: Engine) -> List[dict]:
    """Every still-unresolved duplicate_pending_merge row, enriched with each staged
    candidate's current full detail so the frontend can render the side-by-side
    comparison (spec 22.9) without extra round-trips."""
    with engine.connect() as conn:
        rows = conn.execute(
            select(import_run_items)
            .where(import_run_items.c.status == "duplicate_pending_merge")
            .order_by(import_run_items.c.id.desc())
        ).mappings().all()

        results = []
        for row in rows:
            formatted = _format_import_run_item(dict(row))
            _enrich_with_source_name(conn, formatted)
            candidate_ids = formatted["candidate_item_ids"] or []
            candidates = []
            for candidate_id in candidate_ids:
                detail = get_item_page(conn, candidate_id)
                if detail is not None:
                    candidates.append(detail)
            formatted["candidates"] = candidates
            results.append(formatted)
        return results


def get_pending_changes(engine: Engine) -> List[dict]:
    """Every still-unresolved updated_pending_approval row, enriched with the target
    item's current stored values so the frontend can render a before/after diff."""
    with engine.connect() as conn:
        rows = conn.execute(
            select(import_run_items)
            .where(import_run_items.c.status == "updated_pending_approval")
            .order_by(import_run_items.c.id.desc())
        ).mappings().all()

        results = []
        for row in rows:
            formatted = _format_import_run_item(dict(row))
            _enrich_with_source_name(conn, formatted)
            formatted["current_item"] = get_item_page(conn, row["item_id"]) if row["item_id"] else None
            results.append(formatted)
        return results


def merge_duplicate(engine: Engine, import_run_item_id: int, target_item_id: int) -> dict:
    """Applies a staged duplicate_pending_merge row onto an existing canonical item.

    Additive only: meanings/similar_items/examples are merged in, and the source
    relationship is created (or reactivated) for this source. The target's
    japanese/kana/romaji/part_of_speech are never touched -- merge resolves identity,
    it is not a content-change approval, so display-defining fields stay exactly as
    the target already has them (spec 16). study_progress, item_notes, and
    user_synonym-origin item_meanings rows are never referenced here, so they are
    preserved by construction.
    """
    with engine.begin() as conn:
        row = _get_pending_import_run_item(conn, import_run_item_id, "duplicate_pending_merge")

        candidate_ids = json.loads(row["candidate_item_ids_json"]) if row["candidate_item_ids_json"] else []
        if target_item_id not in candidate_ids:
            raise InvalidMergeTargetError(
                f"{target_item_id} is not one of the staged candidates {candidate_ids}"
            )

        target = conn.execute(select(vocab_items).where(vocab_items.c.id == target_item_id)).mappings().first()
        if target is None:
            raise ItemNotFoundError(f"Item {target_item_id} not found")

        raw = json.loads(row["raw_data_json"])
        source_id = row["source_id"]

        _apply_merge_content(conn, target_item_id, source_id, raw)
        _upsert_resolution(
            conn, source_id, raw["japanese"], raw["kana"], "merged", target_item_id, import_run_item_id
        )

        conn.execute(
            update(import_run_items)
            .where(import_run_items.c.id == import_run_item_id)
            .values(status="merged", item_id=target_item_id)
        )

    return {"import_run_item_id": import_run_item_id, "status": "merged", "item_id": target_item_id}


def keep_separate_duplicate(engine: Engine, import_run_item_id: int) -> dict:
    """Resolves a staged duplicate by creating it as a brand-new canonical item,
    via the exact same path a genuinely-new import row uses (fresh study_progress
    at stage 0, source_items slot computed now). For confirmed false-positive
    matches (e.g. real homophones) where merging would incorrectly conflate two
    different words."""
    with engine.begin() as conn:
        row = _get_pending_import_run_item(conn, import_run_item_id, "duplicate_pending_merge")

        raw = json.loads(row["raw_data_json"])
        reconstructed = _row_from_raw_data(raw, row["row_number"])

        item_id = _create_vocab_item(conn, row["source_id"], reconstructed)
        _insert_examples_for_source(conn, item_id, row["source_id"], reconstructed.examples)
        _create_source_item(conn, row["source_id"], item_id, reconstructed)
        _upsert_resolution(
            conn, row["source_id"], raw["japanese"], raw["kana"], "kept_separate", item_id, import_run_item_id
        )

        conn.execute(
            update(import_run_items)
            .where(import_run_items.c.id == import_run_item_id)
            .values(status="kept_separate", item_id=item_id)
        )

    return {"import_run_item_id": import_run_item_id, "status": "kept_separate", "item_id": item_id}


def skip_duplicate(engine: Engine, import_run_item_id: int) -> dict:
    with engine.begin() as conn:
        row = _get_pending_import_run_item(conn, import_run_item_id, "duplicate_pending_merge")
        raw = json.loads(row["raw_data_json"])
        _upsert_resolution(
            conn, row["source_id"], raw["japanese"], raw["kana"], "skipped", None, import_run_item_id
        )
        conn.execute(
            update(import_run_items).where(import_run_items.c.id == import_run_item_id).values(status="skipped")
        )
    return {"import_run_item_id": import_run_item_id, "status": "skipped"}


def approve_change(engine: Engine, import_run_item_id: int) -> dict:
    """Applies a staged updated_pending_approval row: romaji/part_of_speech are
    replaced if they still differ (re-checked now, not trusting the stale diff
    computed at import time); meanings/similar_items/examples are additive only,
    never removed. Fails safely (SourceRelationshipNotFoundError) rather than
    inventing a new source relationship if the expected one is gone."""
    with engine.begin() as conn:
        row = _get_pending_import_run_item(conn, import_run_item_id, "updated_pending_approval")

        item_id = row["item_id"]
        if item_id is None:
            raise ItemNotFoundError("Staged change has no associated item")

        target = conn.execute(select(vocab_items).where(vocab_items.c.id == item_id)).mappings().first()
        if target is None:
            raise ItemNotFoundError(f"Item {item_id} not found")

        source_id = row["source_id"]
        existing_source_item = conn.execute(
            select(source_items).where(
                source_items.c.source_id == source_id, source_items.c.item_id == item_id
            )
        ).mappings().first()
        if existing_source_item is None:
            raise SourceRelationshipNotFoundError(
                f"No source relationship between source {source_id} and item {item_id}; "
                "cannot approve a content change without an existing membership."
            )

        raw = json.loads(row["raw_data_json"])

        updates = {}
        if raw["romaji"] != target["romaji"]:
            updates["romaji"] = raw["romaji"]
        if raw["part_of_speech"] != target["part_of_speech"]:
            updates["part_of_speech"] = raw["part_of_speech"]
        if updates:
            updates["updated_at"] = _now()
            conn.execute(update(vocab_items).where(vocab_items.c.id == item_id).values(**updates))

        examples = [ParsedExample(**example) for example in raw["examples"]]
        _insert_new_meanings(conn, item_id, source_id, raw["meanings"])
        _insert_new_similar_items(conn, item_id, source_id, raw["similar_items"])
        _insert_examples_for_source(conn, item_id, source_id, examples)

        if raw.get("source_note") != existing_source_item["source_note"]:
            conn.execute(
                update(source_items)
                .where(source_items.c.id == existing_source_item["id"])
                .values(source_note=raw.get("source_note"))
            )

        conn.execute(
            update(import_run_items).where(import_run_items.c.id == import_run_item_id).values(status="approved")
        )

    return {"import_run_item_id": import_run_item_id, "status": "approved", "item_id": item_id}


def reject_change(engine: Engine, import_run_item_id: int) -> dict:
    with engine.begin() as conn:
        _get_pending_import_run_item(conn, import_run_item_id, "updated_pending_approval")
        conn.execute(
            update(import_run_items).where(import_run_items.c.id == import_run_item_id).values(status="skipped")
        )
    return {"import_run_item_id": import_run_item_id, "status": "skipped"}
