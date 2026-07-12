from sqlalchemy import insert, update

from app.models import source_items, sources, study_progress, vocab_items
from app.services.level_service import get_source_levels, lessons_available_in_source


def _make_source(conn, key="work"):
    return conn.execute(
        insert(sources).values(source_key=key, display_name=key.title(), file_path=f"{key}.xlsx")
    ).inserted_primary_key[0]


def _make_item(conn, japanese, kana, srs_stage=0, item_type="word"):
    item_id = conn.execute(
        insert(vocab_items).values(
            item_type=item_type,
            japanese=japanese,
            kana=kana,
            romaji="r",
            part_of_speech="noun",
            normalized_japanese=japanese,
            normalized_kana=kana,
        )
    ).inserted_primary_key[0]
    conn.execute(insert(study_progress).values(item_id=item_id, srs_stage=srs_stage))
    return item_id


def _place(conn, source_id, item_id, level, position, active=True):
    conn.execute(
        insert(source_items).values(
            source_id=source_id,
            item_id=item_id,
            source_level=level,
            level_position=position,
            is_active=active,
        )
    )


def _fill_level(conn, source_id, level, count, guru_count, prefix, active=True, item_type="word", start_position=1):
    for i in range(count):
        stage = 5 if i < guru_count else 0
        item_id = _make_item(conn, f"{prefix}{i}", f"{prefix}kana{i}", srs_stage=stage, item_type=item_type)
        _place(conn, source_id, item_id, level, start_position + i, active=active)


def test_no_items_yet_has_no_levels(engine):
    with engine.begin() as conn:
        source_id = _make_source(conn)

    with engine.connect() as conn:
        levels, current_level = get_source_levels(conn, source_id)

    assert levels == []
    assert current_level == 0


def test_exact_90_percent_unlocks_next_level(engine):
    with engine.begin() as conn:
        source_id = _make_source(conn)
        _fill_level(conn, source_id, 1, count=20, guru_count=18, prefix="a")
        _fill_level(conn, source_id, 2, count=20, guru_count=0, prefix="b")

    with engine.connect() as conn:
        levels, current_level = get_source_levels(conn, source_id)

    assert levels[0]["percent_guru"] == 90.0
    assert levels[0]["is_unlocked"] is True
    assert levels[1]["is_unlocked"] is True
    assert current_level == 2


def test_89_percent_does_not_unlock_next_level(engine):
    with engine.begin() as conn:
        source_id = _make_source(conn)
        _fill_level(conn, source_id, 1, count=20, guru_count=17, prefix="a")
        _fill_level(conn, source_id, 2, count=20, guru_count=0, prefix="b")

    with engine.connect() as conn:
        levels, current_level = get_source_levels(conn, source_id)

    assert levels[1]["is_unlocked"] is False
    assert current_level == 1


def test_empty_level_is_skipped_and_does_not_block(engine):
    with engine.begin() as conn:
        source_id = _make_source(conn)
        # level 1 has items but all are inactive (removed) -> 0 active items
        _fill_level(conn, source_id, 1, count=5, guru_count=0, prefix="a", active=False)
        _fill_level(conn, source_id, 2, count=20, guru_count=0, prefix="b")

    with engine.connect() as conn:
        levels, current_level = get_source_levels(conn, source_id)

    assert levels[0]["active_item_count"] == 0
    assert levels[0]["is_unlocked"] is True  # level 1 always unlocked by default
    assert levels[1]["is_unlocked"] is True  # empty level 1 does not block level 2
    assert current_level == 2  # level 2 is treated as the first meaningful level


def test_empty_level_does_not_retroactively_unlock_after_real_failure(engine):
    with engine.begin() as conn:
        source_id = _make_source(conn)
        _fill_level(conn, source_id, 1, count=20, guru_count=10, prefix="a")  # 50%, fails
        _fill_level(conn, source_id, 2, count=5, guru_count=0, prefix="b", active=False)  # empty
        _fill_level(conn, source_id, 3, count=20, guru_count=20, prefix="c")  # fully mastered

    with engine.connect() as conn:
        levels, current_level = get_source_levels(conn, source_id)

    assert levels[0]["is_unlocked"] is True
    assert levels[1]["is_unlocked"] is False
    assert levels[2]["is_unlocked"] is False
    assert current_level == 1


def test_duplicate_item_shared_progress_counts_immediately_in_every_source(engine):
    with engine.begin() as conn:
        source_a = _make_source(conn, "work")
        source_b = _make_source(conn, "manga")

        shared_item = _make_item(conn, "shared", "shared_kana", srs_stage=0)
        _place(conn, source_a, shared_item, level=1, position=1)
        _place(conn, source_b, shared_item, level=1, position=1)

        # pad each source's level 1 to 10 items total: 8 already Guru + 1 non-Guru filler,
        # so it's 8/10 (80%, locked) before the shared item is bumped, 9/10 (90%) after
        for i in range(8):
            item_id = _make_item(conn, f"a_pad{i}", f"a_pad_kana{i}", srs_stage=5)
            _place(conn, source_a, item_id, level=1, position=i + 2)
        filler_a = _make_item(conn, "a_filler", "a_filler_kana", srs_stage=0)
        _place(conn, source_a, filler_a, level=1, position=10)

        for i in range(8):
            item_id = _make_item(conn, f"b_pad{i}", f"b_pad_kana{i}", srs_stage=5)
            _place(conn, source_b, item_id, level=1, position=i + 2)
        filler_b = _make_item(conn, "b_filler", "b_filler_kana", srs_stage=0)
        _place(conn, source_b, filler_b, level=1, position=10)

    with engine.connect() as conn:
        levels_a, current_a = get_source_levels(conn, source_a)
        levels_b, current_b = get_source_levels(conn, source_b)

    # 8/10 = 80%: not yet unlocked in either source since the shared item isn't Guru
    assert current_a == 1
    assert current_b == 1

    with engine.begin() as conn:
        conn.execute(update(study_progress).where(study_progress.c.item_id == shared_item).values(srs_stage=5))

    with engine.connect() as conn:
        levels_a, current_a = get_source_levels(conn, source_a)
        levels_b, current_b = get_source_levels(conn, source_b)

    # bumping the shared item's progress once should unlock level 2 in BOTH sources immediately
    assert levels_a[0]["guru_or_higher_count"] == 9
    assert levels_b[0]["guru_or_higher_count"] == 9
    assert current_a == 2
    assert current_b == 2


# --- per-level word/phrase breakdown (by_type) --------------------------------------


def test_level_by_type_breakdown_splits_word_and_phrase_counts(engine):
    with engine.begin() as conn:
        source_id = _make_source(conn)
        _fill_level(conn, source_id, 1, count=5, guru_count=3, prefix="w", item_type="word", start_position=1)
        _fill_level(conn, source_id, 1, count=5, guru_count=1, prefix="p", item_type="phrase", start_position=6)

    with engine.connect() as conn:
        levels, _current_level = get_source_levels(conn, source_id)

    level_1 = levels[0]
    # Blended totals (used by the unlock threshold) stay combined across both types.
    assert level_1["active_item_count"] == 10
    assert level_1["guru_or_higher_count"] == 4

    assert level_1["by_type"]["word"] == {
        "active_item_count": 5,
        "guru_or_higher_count": 3,
        "percent_guru": 60.0,
    }
    assert level_1["by_type"]["phrase"] == {
        "active_item_count": 5,
        "guru_or_higher_count": 1,
        "percent_guru": 20.0,
    }


def test_level_by_type_breakdown_zero_for_absent_type(engine):
    with engine.begin() as conn:
        source_id = _make_source(conn)
        _fill_level(conn, source_id, 1, count=4, guru_count=2, prefix="w", item_type="word")

    with engine.connect() as conn:
        levels, _current_level = get_source_levels(conn, source_id)

    assert levels[0]["by_type"]["word"]["active_item_count"] == 4
    assert levels[0]["by_type"]["phrase"] == {
        "active_item_count": 0,
        "guru_or_higher_count": 0,
        "percent_guru": 0.0,
    }


def test_lessons_available_in_source_excludes_learned_locked_and_inactive_items(engine):
    with engine.begin() as conn:
        source_id = _make_source(conn)
        unlearned_unlocked = _make_item(conn, "a", "a", srs_stage=0)
        _place(conn, source_id, unlearned_unlocked, level=1, position=1)

        already_learned = _make_item(conn, "b", "b", srs_stage=3)
        _place(conn, source_id, already_learned, level=1, position=2)

        inactive_unlearned = _make_item(conn, "c", "c", srs_stage=0)
        _place(conn, source_id, inactive_unlearned, level=1, position=3, active=False)

        locked_level_item = _make_item(conn, "d", "d", srs_stage=0)
        _place(conn, source_id, locked_level_item, level=2, position=1)

    with engine.connect() as conn:
        levels, current_level = get_source_levels(conn, source_id)
        count = lessons_available_in_source(conn, source_id, current_level)

    assert current_level == 1  # level 1 is far below 90% guru, level 2 stays locked
    assert count == 1
