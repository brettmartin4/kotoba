import random
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Set

from sqlalchemy import insert, select, update
from sqlalchemy.engine import Connection, Engine

from app.core.config import settings
from app.models import item_forms, item_meanings, review_attempts, review_sessions
from app.models import source_items, sources, study_progress
from app.services.answer_checking import (
    check_japanese_answer,
    check_meaning_answer,
    normalize_meaning_answer,
)
from app.services.item_detail import get_item_detail
from app.services.level_service import get_source_levels, get_sources_overview
from app.services.text_normalization import normalize_japanese
from app.services.time_utils import round_down_to_hour, start_of_local_day_utc

PROMPT_TYPES = ("meaning", "japanese")


class SourceNotFoundError(Exception):
    pass


class NoEligibleItemsError(Exception):
    pass


class LessonSessionNotFoundError(Exception):
    pass


def _now_aware() -> datetime:
    return datetime.now(timezone.utc)


def eligible_lesson_item_ids(conn: Connection, sources_overview: List[dict]) -> Set[int]:
    """Distinct items eligible for a lesson across all given sources: active
    association, in an unlocked level, and not yet learned (srs_stage == 0).
    A shared canonical item counts once even if eligible via multiple sources."""
    eligible: Set[int] = set()
    for source in sources_overview:
        current_level = source["current_level"]
        if current_level <= 0:
            continue
        rows = conn.execute(
            select(source_items.c.item_id)
            .select_from(source_items.join(study_progress, source_items.c.item_id == study_progress.c.item_id))
            .where(
                source_items.c.source_id == source["id"],
                source_items.c.is_active.is_(True),
                source_items.c.source_level <= current_level,
                study_progress.c.srs_stage == 0,
            )
        ).all()
        eligible.update(r[0] for r in rows)
    return eligible


def lessons_learned_today(conn: Connection, now_aware_utc: datetime) -> int:
    cutoff = start_of_local_day_utc(now_aware_utc)
    rows = conn.execute(
        select(study_progress.c.item_id).where(
            study_progress.c.learned_at.is_not(None), study_progress.c.learned_at >= cutoff
        )
    ).all()
    return len(rows)


def get_lessons_available(engine: Engine) -> dict:
    with engine.connect() as conn:
        now = _now_aware()
        overview = get_sources_overview(conn)
        learned_today = lessons_learned_today(conn, now)
        remaining_today = max(0, settings.daily_lesson_cap - learned_today)

        sources_payload = [
            {
                "source_id": source["id"],
                "source_key": source["source_key"],
                "display_name": source["display_name"],
                "current_level": source["current_level"],
                "lessons_available_in_source": source["lessons_available_in_source"],
            }
            for source in overview
        ]

        return {
            "daily_lesson_cap": settings.daily_lesson_cap,
            "lessons_learned_today": learned_today,
            "remaining_today": remaining_today,
            "sources": sources_payload,
        }


def _select_lesson_batch(conn: Connection, source_id: int, now_aware_utc: datetime) -> List[int]:
    _, current_level = get_source_levels(conn, source_id)
    if current_level <= 0:
        return []

    rows = conn.execute(
        select(source_items.c.item_id)
        .select_from(source_items.join(study_progress, source_items.c.item_id == study_progress.c.item_id))
        .where(
            source_items.c.source_id == source_id,
            source_items.c.is_active.is_(True),
            source_items.c.source_level <= current_level,
            study_progress.c.srs_stage == 0,
        )
    ).all()
    eligible_ids = [r[0] for r in rows]
    random.shuffle(eligible_ids)

    learned_today = lessons_learned_today(conn, now_aware_utc)
    remaining_cap = max(0, settings.daily_lesson_cap - learned_today)
    batch_size = min(len(eligible_ids), settings.lesson_batch_size, remaining_cap)
    return eligible_ids[:batch_size]


def start_lesson_session(engine: Engine, source_id: int) -> dict:
    with engine.begin() as conn:
        source = conn.execute(select(sources).where(sources.c.id == source_id)).mappings().first()
        if source is None:
            raise SourceNotFoundError(f"Source {source_id} not found")

        now = _now_aware()
        batch_item_ids = _select_lesson_batch(conn, source_id, now)
        if not batch_item_ids:
            raise NoEligibleItemsError("No lessons available for this source right now")

        session_id = conn.execute(
            insert(review_sessions).values(started_at=now.replace(tzinfo=None), session_type="lesson_quiz")
        ).inserted_primary_key[0]

        items = [get_item_detail(conn, item_id) for item_id in batch_item_ids]

    return {"session_id": session_id, "items": items}


def _accepted_display_forms(conn: Connection, item_id: int) -> List[str]:
    rows = conn.execute(
        select(item_forms.c.form).where(item_forms.c.item_id == item_id, item_forms.c.form_type == "display")
    ).all()
    return [r[0] for r in rows]


def _accepted_kana_forms(conn: Connection, item_id: int) -> List[str]:
    rows = conn.execute(
        select(item_forms.c.form).where(item_forms.c.item_id == item_id, item_forms.c.form_type == "kana")
    ).all()
    return [r[0] for r in rows]


def _accepted_meanings(conn: Connection, item_id: int) -> List[str]:
    rows = conn.execute(select(item_meanings.c.meaning).where(item_meanings.c.item_id == item_id)).all()
    return [r[0] for r in rows]


def _correctly_answered_prompt_types(conn: Connection, session_id: int, item_id: int) -> Set[str]:
    rows = conn.execute(
        select(review_attempts.c.prompt_type)
        .where(
            review_attempts.c.session_id == session_id,
            review_attempts.c.item_id == item_id,
            review_attempts.c.is_correct.is_(True),
        )
        .distinct()
    ).all()
    return {r[0] for r in rows}


def _activate_if_not_already(conn: Connection, item_id: int, now_naive_utc: datetime) -> bool:
    """Moves srs_stage 0 -> 1 (Apprentice 1) and schedules the first review.
    Guarded by the current stage so a redundant call is a no-op, not a re-activation."""
    current_stage = conn.execute(
        select(study_progress.c.srs_stage).where(study_progress.c.item_id == item_id)
    ).scalar()
    if current_stage != 0:
        return False

    next_review_at = round_down_to_hour(now_naive_utc + timedelta(hours=4))
    conn.execute(
        update(study_progress)
        .where(study_progress.c.item_id == item_id)
        .values(srs_stage=1, learned_at=now_naive_utc, next_review_at=next_review_at)
    )
    return True


def record_lesson_answer(
    engine: Engine, session_id: int, item_id: int, prompt_type: str, submitted_answer: str
) -> dict:
    with engine.begin() as conn:
        session = conn.execute(select(review_sessions).where(review_sessions.c.id == session_id)).mappings().first()
        if session is None or session["session_type"] != "lesson_quiz":
            raise LessonSessionNotFoundError(f"Lesson session {session_id} not found")

        accepted_meanings = _accepted_meanings(conn, item_id)
        if prompt_type == "meaning":
            is_correct = check_meaning_answer(submitted_answer, accepted_meanings)
            correct_answers = accepted_meanings
            normalized_answer = normalize_meaning_answer(submitted_answer)
        else:
            display_forms = _accepted_display_forms(conn, item_id)
            kana_forms = _accepted_kana_forms(conn, item_id)
            is_correct = check_japanese_answer(submitted_answer, display_forms, kana_forms)
            correct_answers = display_forms + kana_forms
            normalized_answer = normalize_japanese(submitted_answer)

        now_naive_utc = _now_aware().replace(tzinfo=None)
        conn.execute(
            insert(review_attempts).values(
                session_id=session_id,
                item_id=item_id,
                prompt_type=prompt_type,
                submitted_answer=submitted_answer,
                normalized_answer=normalized_answer,
                is_correct=is_correct,
                is_typo_warning=False,
                created_at=now_naive_utc,
            )
        )

        item_passed = set(PROMPT_TYPES) <= _correctly_answered_prompt_types(conn, session_id, item_id)

        item_activated = False
        if item_passed:
            item_activated = _activate_if_not_already(conn, item_id, now_naive_utc)

    return {
        "is_correct": is_correct,
        "correct_answers": correct_answers,
        "item_passed": item_passed,
        "item_activated": item_activated,
    }


def complete_lesson_session(engine: Engine, session_id: int) -> dict:
    with engine.begin() as conn:
        session = conn.execute(select(review_sessions).where(review_sessions.c.id == session_id)).mappings().first()
        if session is None or session["session_type"] != "lesson_quiz":
            raise LessonSessionNotFoundError(f"Lesson session {session_id} not found")

        now_naive_utc = _now_aware().replace(tzinfo=None)
        conn.execute(
            update(review_sessions).where(review_sessions.c.id == session_id).values(completed_at=now_naive_utc)
        )

        item_ids = [
            r[0]
            for r in conn.execute(
                select(review_attempts.c.item_id).where(review_attempts.c.session_id == session_id).distinct()
            )
        ]
        activated_item_ids = [
            item_id
            for item_id in item_ids
            if set(PROMPT_TYPES) <= _correctly_answered_prompt_types(conn, session_id, item_id)
        ]

    return {
        "session_id": session_id,
        "completed_at": now_naive_utc,
        "activated_item_ids": activated_item_ids,
    }
