from datetime import datetime, timedelta, timezone
from typing import Dict, List

from dateutil.relativedelta import relativedelta
from sqlalchemy import insert, select, update
from sqlalchemy.engine import Connection, Engine

from app.models import item_forms, item_meanings, review_attempts, review_sessions, study_progress
from app.services.answer_checking import (
    check_japanese_answer,
    grade_meaning_answer,
    normalize_meaning_answer,
)
from app.services.item_detail import get_item_detail
from app.services.text_normalization import normalize_japanese
from app.services.time_utils import round_down_to_hour

PROMPT_TYPES = ("meaning", "japanese")

# Keyed by the *new* stage a correct/incorrect answer lands on (matches spec 13.4's
# pseudocode literally: whichever stage you end up at determines the next interval,
# whether you got there by advancing or by demoting). Stages 7/8 use calendar months
# via dateutil rather than fixed-day approximations, per spec 13.2.
SRS_INTERVALS = {
    1: timedelta(hours=4),
    2: timedelta(hours=8),
    3: timedelta(days=1),
    4: timedelta(days=2),
    5: timedelta(weeks=1),
    6: timedelta(weeks=2),
    7: relativedelta(months=1),
    8: relativedelta(months=4),
}


class NoDueItemsError(Exception):
    pass


class ReviewSessionNotFoundError(Exception):
    pass


def _now_aware() -> datetime:
    return datetime.now(timezone.utc)


def select_due_item_ids(conn: Connection, now_naive_utc: datetime) -> List[int]:
    rows = conn.execute(
        select(study_progress.c.item_id).where(
            study_progress.c.srs_stage.between(1, 8),
            study_progress.c.next_review_at.is_not(None),
            study_progress.c.next_review_at <= now_naive_utc,
        )
    ).all()
    return [r[0] for r in rows]


def get_reviews_available(engine: Engine) -> dict:
    with engine.connect() as conn:
        now_naive_utc = _now_aware().replace(tzinfo=None)
        return {"reviews_available": len(select_due_item_ids(conn, now_naive_utc))}


def start_review_session(engine: Engine) -> dict:
    with engine.begin() as conn:
        now_naive_utc = _now_aware().replace(tzinfo=None)
        due_item_ids = select_due_item_ids(conn, now_naive_utc)
        if not due_item_ids:
            raise NoDueItemsError("No reviews available right now")

        session_id = conn.execute(
            insert(review_sessions).values(started_at=now_naive_utc, session_type="review")
        ).inserted_primary_key[0]

        items = [get_item_detail(conn, item_id) for item_id in due_item_ids]

    return {"session_id": session_id, "items": items}


def _accepted_meanings(conn: Connection, item_id: int) -> List[str]:
    rows = conn.execute(select(item_meanings.c.meaning).where(item_meanings.c.item_id == item_id)).all()
    return [r[0] for r in rows]


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


def _resolved_attempts(conn: Connection, session_id: int, item_id: int) -> Dict[str, bool]:
    """Maps prompt_type -> is_correct for attempts that actually resolved that prompt
    (is_typo_warning=False). A typo-warning attempt never appears here."""
    rows = conn.execute(
        select(review_attempts.c.prompt_type, review_attempts.c.is_correct).where(
            review_attempts.c.session_id == session_id,
            review_attempts.c.item_id == item_id,
            review_attempts.c.is_typo_warning.is_(False),
        )
    ).all()
    return {prompt_type: is_correct for prompt_type, is_correct in rows}


def _increment_prompt_counter(conn: Connection, item_id: int, prompt_type: str, is_correct: bool) -> None:
    if prompt_type == "meaning":
        column = study_progress.c.meaning_correct if is_correct else study_progress.c.meaning_incorrect
    else:
        column = study_progress.c.japanese_correct if is_correct else study_progress.c.japanese_incorrect
    conn.execute(update(study_progress).where(study_progress.c.item_id == item_id).values({column: column + 1}))


def _apply_srs_result(conn: Connection, item_id: int, item_passed: bool, now_naive_utc: datetime) -> dict:
    current_stage = conn.execute(
        select(study_progress.c.srs_stage).where(study_progress.c.item_id == item_id)
    ).scalar()

    raw_new_stage = current_stage + 1 if item_passed else max(1, current_stage - 1)
    new_stage = min(raw_new_stage, 9)

    values = {
        "srs_stage": new_stage,
        "total_reviews": study_progress.c.total_reviews + 1,
        "correct_reviews": study_progress.c.correct_reviews + (1 if item_passed else 0),
        "incorrect_reviews": study_progress.c.incorrect_reviews + (0 if item_passed else 1),
        "current_correct_streak": (study_progress.c.current_correct_streak + 1) if item_passed else 0,
        "updated_at": now_naive_utc,
    }

    if new_stage == 9:
        values["burned_at"] = now_naive_utc
        values["next_review_at"] = None
    else:
        values["next_review_at"] = round_down_to_hour(now_naive_utc + SRS_INTERVALS[new_stage])

    conn.execute(update(study_progress).where(study_progress.c.item_id == item_id).values(**values))

    current_streak, longest_streak = conn.execute(
        select(study_progress.c.current_correct_streak, study_progress.c.longest_correct_streak).where(
            study_progress.c.item_id == item_id
        )
    ).first()
    if current_streak > longest_streak:
        conn.execute(
            update(study_progress)
            .where(study_progress.c.item_id == item_id)
            .values(longest_correct_streak=current_streak)
        )

    final_stage, final_next_review = conn.execute(
        select(study_progress.c.srs_stage, study_progress.c.next_review_at).where(
            study_progress.c.item_id == item_id
        )
    ).first()
    return {"new_stage": final_stage, "next_review_at": final_next_review}


def _accepted_answers_for_display(conn: Connection, item_id: int, prompt_type: str) -> List[str]:
    if prompt_type == "meaning":
        return _accepted_meanings(conn, item_id)
    return _accepted_display_forms(conn, item_id) + _accepted_kana_forms(conn, item_id)


def record_review_answer(
    engine: Engine, session_id: int, item_id: int, prompt_type: str, submitted_answer: str
) -> dict:
    with engine.begin() as conn:
        session = conn.execute(select(review_sessions).where(review_sessions.c.id == session_id)).mappings().first()
        if session is None or session["session_type"] != "review":
            raise ReviewSessionNotFoundError(f"Review session {session_id} not found")

        resolved_before = _resolved_attempts(conn, session_id, item_id)
        if prompt_type in resolved_before:
            # Already resolved earlier this session -- idempotent no-op, no re-grading,
            # no re-counting. SRS fields are omitted since they were applied at the time.
            is_correct = resolved_before[prompt_type]
            item_resolved = set(PROMPT_TYPES) <= resolved_before.keys()
            return {
                "status": "correct" if is_correct else "incorrect",
                "correct_answers": [] if is_correct else _accepted_answers_for_display(conn, item_id, prompt_type),
                "item_resolved": item_resolved,
                "item_passed": all(resolved_before.values()) if item_resolved else None,
                "new_srs_stage": None,
                "next_review_at": None,
                "burned": False,
            }

        if prompt_type == "meaning":
            accepted_meanings = _accepted_meanings(conn, item_id)
            grade = grade_meaning_answer(submitted_answer, accepted_meanings)
            is_correct = grade == "correct"
            is_typo_warning = grade == "typo_warning"
            correct_answers = accepted_meanings
            normalized_answer = normalize_meaning_answer(submitted_answer)
        else:
            display_forms = _accepted_display_forms(conn, item_id)
            kana_forms = _accepted_kana_forms(conn, item_id)
            is_correct = check_japanese_answer(submitted_answer, display_forms, kana_forms)
            grade = "correct" if is_correct else "incorrect"
            is_typo_warning = False
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
                is_typo_warning=is_typo_warning,
                created_at=now_naive_utc,
            )
        )

        if grade == "typo_warning":
            return {
                "status": "typo_warning",
                "correct_answers": [],
                "item_resolved": False,
                "item_passed": None,
                "new_srs_stage": None,
                "next_review_at": None,
                "burned": False,
            }

        _increment_prompt_counter(conn, item_id, prompt_type, is_correct)

        resolved_after = _resolved_attempts(conn, session_id, item_id)
        item_resolved = set(PROMPT_TYPES) <= resolved_after.keys()

        result = {
            "status": grade,
            "correct_answers": [] if is_correct else correct_answers,
            "item_resolved": item_resolved,
            "item_passed": None,
            "new_srs_stage": None,
            "next_review_at": None,
            "burned": False,
        }

        if item_resolved:
            item_passed = all(resolved_after.values())
            srs_result = _apply_srs_result(conn, item_id, item_passed, now_naive_utc)
            result.update(
                {
                    "item_passed": item_passed,
                    "new_srs_stage": srs_result["new_stage"],
                    "next_review_at": srs_result["next_review_at"],
                    "burned": srs_result["new_stage"] == 9,
                }
            )

    return result


def complete_review_session(engine: Engine, session_id: int) -> dict:
    with engine.begin() as conn:
        session = conn.execute(select(review_sessions).where(review_sessions.c.id == session_id)).mappings().first()
        if session is None or session["session_type"] != "review":
            raise ReviewSessionNotFoundError(f"Review session {session_id} not found")

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
        results = []
        for item_id in item_ids:
            resolved = _resolved_attempts(conn, session_id, item_id)
            if set(PROMPT_TYPES) <= resolved.keys():
                stage = conn.execute(
                    select(study_progress.c.srs_stage).where(study_progress.c.item_id == item_id)
                ).scalar()
                results.append({"item_id": item_id, "passed": all(resolved.values()), "new_srs_stage": stage})

    return {"session_id": session_id, "completed_at": now_naive_utc, "results": results}
