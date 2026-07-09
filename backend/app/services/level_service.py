from typing import Dict, List, Tuple

from sqlalchemy import case, func, select
from sqlalchemy.engine import Connection

from app.models import source_items, sources, study_progress

GURU_STAGE_THRESHOLD = 5  # srs_stage >= 5 is Guru 1 or higher


def _max_level(conn: Connection, source_id: int) -> int:
    return (
        conn.execute(
            select(func.max(source_items.c.source_level)).where(
                source_items.c.source_id == source_id
            )
        ).scalar()
        or 0
    )


def _active_stats_by_level(conn: Connection, source_id: int) -> Dict[int, Tuple[int, int]]:
    guru_expr = case((study_progress.c.srs_stage >= GURU_STAGE_THRESHOLD, 1), else_=0)
    rows = conn.execute(
        select(
            source_items.c.source_level,
            func.count().label("active_count"),
            func.sum(guru_expr).label("guru_count"),
        )
        .select_from(source_items.join(study_progress, source_items.c.item_id == study_progress.c.item_id))
        .where(source_items.c.source_id == source_id, source_items.c.is_active.is_(True))
        .group_by(source_items.c.source_level)
    ).all()
    return {level: (active_count, guru_count or 0) for level, active_count, guru_count in rows}


def get_source_levels(conn: Connection, source_id: int) -> Tuple[List[dict], int]:
    """Per-level progress plus the highest currently-unlocked level for a source.

    Level 1 is always unlocked. A level unlocks the next one only if it has at
    least one active item and >=90% of its active items are Guru 1+ (checked via
    integer cross-multiplication to avoid float rounding at the exact boundary).

    A level with zero active items (everything removed) is skipped in the
    cascade rather than treated as a permanent block: it neither unlocks nor
    locks the next level, it just passes through whatever unlocked state it
    inherited.
    """
    max_level = _max_level(conn, source_id)
    stats_by_level = _active_stats_by_level(conn, source_id)

    levels: List[dict] = []
    unlocked_carry = True
    current_unlocked_level = 1 if max_level >= 1 else 0

    for level in range(1, max_level + 1):
        active_count, guru_count = stats_by_level.get(level, (0, 0))
        is_unlocked = unlocked_carry
        percent_guru = round((guru_count / active_count * 100), 1) if active_count > 0 else 0.0

        levels.append(
            {
                "level": level,
                "active_item_count": active_count,
                "guru_or_higher_count": guru_count,
                "percent_guru": percent_guru,
                "is_unlocked": is_unlocked,
            }
        )

        if active_count == 0:
            next_carry = unlocked_carry
        else:
            meets_threshold = guru_count * 100 >= active_count * 90
            next_carry = unlocked_carry and meets_threshold

        unlocked_carry = next_carry
        if unlocked_carry:
            current_unlocked_level = level + 1

    return levels, current_unlocked_level


def lessons_available_in_source(conn: Connection, source_id: int, current_unlocked_level: int) -> int:
    if current_unlocked_level <= 0:
        return 0
    return conn.execute(
        select(func.count(func.distinct(source_items.c.item_id)))
        .select_from(source_items.join(study_progress, source_items.c.item_id == study_progress.c.item_id))
        .where(
            source_items.c.source_id == source_id,
            source_items.c.is_active.is_(True),
            source_items.c.source_level <= current_unlocked_level,
            study_progress.c.srs_stage == 0,
        )
    ).scalar()


def get_sources_overview(conn: Connection) -> List[dict]:
    """List of sources with their per-level progress and lesson-eligible-item count.
    Shared by the sources API, the dashboard, and the lessons-available endpoint."""
    source_rows = conn.execute(select(sources).order_by(sources.c.id)).mappings().all()
    overview = []
    for source in source_rows:
        levels, current_level = get_source_levels(conn, source["id"])
        overview.append(
            {
                "id": source["id"],
                "source_key": source["source_key"],
                "display_name": source["display_name"],
                "is_active": source["is_active"],
                "created_at": source["created_at"],
                "last_imported_at": source["last_imported_at"],
                "current_level": current_level,
                "levels": levels,
                "lessons_available_in_source": lessons_available_in_source(
                    conn, source["id"], current_level
                ),
            }
        )
    return overview
