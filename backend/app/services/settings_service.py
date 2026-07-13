from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import insert, select, update
from sqlalchemy.engine import Connection

from app.core.config import settings as default_settings
from app.models import settings_table

DAILY_LESSON_CAP_KEY = "daily_lesson_cap"


class InvalidSettingValueError(Exception):
    pass


def _get_raw_setting(conn: Connection, key: str) -> Optional[str]:
    row = conn.execute(select(settings_table.c.value).where(settings_table.c.key == key)).first()
    return row[0] if row else None


def _upsert_setting(conn: Connection, key: str, value: str) -> None:
    now = datetime.now(timezone.utc)
    existing = conn.execute(select(settings_table.c.key).where(settings_table.c.key == key)).first()
    if existing:
        conn.execute(update(settings_table).where(settings_table.c.key == key).values(value=value, updated_at=now))
    else:
        conn.execute(insert(settings_table).values(key=key, value=value, updated_at=now))


def get_daily_lesson_cap(conn: Connection) -> int:
    """Falls back to the static config default (Settings.daily_lesson_cap)
    until the user explicitly sets a value via the admin panel -- so existing
    dev DBs need no migration/backfill, matching this project's established
    additive-schema pattern."""
    raw = _get_raw_setting(conn, DAILY_LESSON_CAP_KEY)
    if raw is None:
        return default_settings.daily_lesson_cap
    return int(raw)


def set_daily_lesson_cap(conn: Connection, value: int) -> int:
    if value < 1:
        raise InvalidSettingValueError("Daily lesson cap must be at least 1")
    _upsert_setting(conn, DAILY_LESSON_CAP_KEY, str(value))
    return value
