from sqlalchemy import select
from sqlalchemy.engine import Connection

from app.models import examples as examples_table
from app.models import item_meanings, item_notes
from app.models import similar_items as similar_items_table
from app.models import vocab_items


def get_item_detail(conn: Connection, item_id: int) -> dict:
    """Full display content for a canonical item: used both for lesson cards and
    the review screen's post-answer info panel (meaning/reading/examples/notes/similar)."""
    item = conn.execute(select(vocab_items).where(vocab_items.c.id == item_id)).mappings().first()
    meanings = [
        r[0] for r in conn.execute(select(item_meanings.c.meaning).where(item_meanings.c.item_id == item_id))
    ]
    example_rows = conn.execute(
        select(
            examples_table.c.japanese_sentence,
            examples_table.c.kana_sentence,
            examples_table.c.english_translation,
        ).where(examples_table.c.item_id == item_id)
    ).all()
    similar = [
        r[0]
        for r in conn.execute(
            select(similar_items_table.c.similar_text).where(similar_items_table.c.item_id == item_id)
        )
    ]
    note_row = conn.execute(select(item_notes).where(item_notes.c.item_id == item_id)).mappings().first()

    return {
        "item_id": item["id"],
        "item_type": item["item_type"],
        "japanese": item["japanese"],
        "kana": item["kana"],
        "romaji": item["romaji"],
        "part_of_speech": item["part_of_speech"],
        "meanings": meanings,
        "examples": [
            {"japanese_sentence": ja, "kana_sentence": ka, "english_translation": en}
            for ja, ka, en in example_rows
        ],
        "similar_items": similar,
        "notes": {
            "note_text": note_row["note_text"] if note_row else None,
            "mnemonic_text": note_row["mnemonic_text"] if note_row else None,
        },
    }
