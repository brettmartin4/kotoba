from datetime import datetime, timedelta, timezone

from app.services.time_utils import start_of_local_day_utc, today_local_date, utc_to_local_date


def test_start_of_local_day_utc_is_local_midnight():
    reference = datetime.now(timezone.utc)
    result = start_of_local_day_utc(reference)

    assert result.tzinfo is None
    local_repr = result.replace(tzinfo=timezone.utc).astimezone()
    assert (local_repr.hour, local_repr.minute, local_repr.second) == (0, 0, 0)


def test_start_of_local_day_utc_is_within_the_last_24_hours():
    reference = datetime.now(timezone.utc)
    result = start_of_local_day_utc(reference)

    assert result <= reference.replace(tzinfo=None)
    assert reference.replace(tzinfo=None) - result < timedelta(days=1)


def test_utc_to_local_date_matches_today_local_date_for_now():
    now_naive_utc = datetime.now(timezone.utc).replace(tzinfo=None)
    assert utc_to_local_date(now_naive_utc) == today_local_date()


def test_utc_to_local_date_consistent_with_start_of_local_day():
    reference = datetime.now(timezone.utc)
    midnight = start_of_local_day_utc(reference)
    assert utc_to_local_date(midnight) == today_local_date()
