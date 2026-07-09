from datetime import date, datetime, timezone
from typing import Optional


def start_of_local_day_utc(reference_utc: Optional[datetime] = None) -> datetime:
    """Local midnight (server's system timezone), expressed as a naive UTC datetime
    so it can be compared directly against columns stored via datetime.now(timezone.utc)
    (which SQLAlchemy's SQLite DateTime type stores with tzinfo stripped)."""
    reference = reference_utc or datetime.now(timezone.utc)
    local_now = reference.astimezone()
    local_midnight = local_now.replace(hour=0, minute=0, second=0, microsecond=0)
    return local_midnight.astimezone(timezone.utc).replace(tzinfo=None)


def utc_to_local_date(naive_utc: datetime) -> date:
    """Converts a naive-UTC-stored timestamp to the local calendar date it falls on."""
    aware_utc = naive_utc.replace(tzinfo=timezone.utc)
    return aware_utc.astimezone().date()


def today_local_date() -> date:
    return datetime.now(timezone.utc).astimezone().date()
