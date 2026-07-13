import pytest

from app.core.config import settings as default_settings
from app.services.settings_service import (
    InvalidSettingValueError,
    get_daily_lesson_cap,
    set_daily_lesson_cap,
)


def test_get_daily_lesson_cap_falls_back_to_config_default_when_unset(engine):
    with engine.connect() as conn:
        assert get_daily_lesson_cap(conn) == default_settings.daily_lesson_cap


def test_set_then_get_daily_lesson_cap_persists(engine):
    with engine.begin() as conn:
        set_daily_lesson_cap(conn, 5)

    with engine.connect() as conn:
        assert get_daily_lesson_cap(conn) == 5


def test_set_daily_lesson_cap_updates_existing_value(engine):
    with engine.begin() as conn:
        set_daily_lesson_cap(conn, 5)
    with engine.begin() as conn:
        set_daily_lesson_cap(conn, 20)

    with engine.connect() as conn:
        assert get_daily_lesson_cap(conn) == 20


@pytest.mark.parametrize("bad_value", [0, -1, -100])
def test_set_daily_lesson_cap_rejects_non_positive(engine, bad_value):
    with engine.begin() as conn:
        with pytest.raises(InvalidSettingValueError):
            set_daily_lesson_cap(conn, bad_value)
