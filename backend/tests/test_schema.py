import pytest
from sqlalchemy import insert, select
from sqlalchemy.exc import IntegrityError

from app.models import item_meanings, metadata, source_items, sources, vocab_items


def test_all_tables_are_created(engine):
    with engine.connect() as conn:
        for name, table in metadata.tables.items():
            conn.execute(select(table).limit(1))


def _insert_source(conn, key="work"):
    return conn.execute(
        insert(sources).values(source_key=key, display_name=key.title(), file_path=f"{key}.xlsx")
    ).inserted_primary_key[0]


def _insert_item(conn, japanese="a", kana="a"):
    return conn.execute(
        insert(vocab_items).values(
            item_type="word",
            japanese=japanese,
            kana=kana,
            romaji="a",
            part_of_speech="noun",
            normalized_japanese=japanese,
            normalized_kana=kana,
        )
    ).inserted_primary_key[0]


def test_source_items_slot_uniqueness_enforced(engine):
    with engine.begin() as conn:
        source_id = _insert_source(conn)
        item1 = _insert_item(conn, "a", "a")
        item2 = _insert_item(conn, "b", "b")
        conn.execute(
            insert(source_items).values(
                source_id=source_id, item_id=item1, source_level=1, level_position=1
            )
        )

    with pytest.raises(IntegrityError):
        with engine.begin() as conn:
            conn.execute(
                insert(source_items).values(
                    source_id=source_id, item_id=item2, source_level=1, level_position=1
                )
            )


def test_source_items_source_item_uniqueness_enforced(engine):
    with engine.begin() as conn:
        source_id = _insert_source(conn)
        item_id = _insert_item(conn)
        conn.execute(
            insert(source_items).values(
                source_id=source_id, item_id=item_id, source_level=1, level_position=1
            )
        )

    with pytest.raises(IntegrityError):
        with engine.begin() as conn:
            conn.execute(
                insert(source_items).values(
                    source_id=source_id, item_id=item_id, source_level=1, level_position=2
                )
            )


def test_item_meanings_dedup_constraint_enforced(engine):
    with engine.begin() as conn:
        item_id = _insert_item(conn)
        conn.execute(
            insert(item_meanings).values(
                item_id=item_id, meaning="confirm", normalized_meaning="confirm", origin="imported"
            )
        )

    with pytest.raises(IntegrityError):
        with engine.begin() as conn:
            conn.execute(
                insert(item_meanings).values(
                    item_id=item_id, meaning="Confirm", normalized_meaning="confirm", origin="imported"
                )
            )


def test_vocab_items_item_type_check_constraint_enforced(engine):
    with pytest.raises(IntegrityError):
        with engine.begin() as conn:
            conn.execute(
                insert(vocab_items).values(
                    item_type="not-a-real-type",
                    japanese="a",
                    kana="a",
                    romaji="a",
                    part_of_speech="noun",
                    normalized_japanese="a",
                    normalized_kana="a",
                )
            )
