from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    UniqueConstraint,
    func,
)

metadata = MetaData()

sources = Table(
    "sources",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("source_key", String, nullable=False, unique=True),
    Column("display_name", String, nullable=False),
    Column("file_path", String, nullable=False),
    Column("is_active", Boolean, nullable=False, default=True, server_default="1"),
    Column("created_at", DateTime, nullable=False, server_default=func.current_timestamp()),
    Column("updated_at", DateTime, nullable=False, server_default=func.current_timestamp()),
    Column("last_imported_at", DateTime, nullable=True),
)

vocab_items = Table(
    "vocab_items",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("item_type", String, nullable=False),
    Column("japanese", String, nullable=False),
    Column("kana", String, nullable=False),
    Column("romaji", String, nullable=False),
    Column("part_of_speech", String, nullable=False),
    Column("normalized_japanese", String, nullable=False),
    Column("normalized_kana", String, nullable=False),
    Column("created_at", DateTime, nullable=False, server_default=func.current_timestamp()),
    Column("updated_at", DateTime, nullable=False, server_default=func.current_timestamp()),
    CheckConstraint("item_type IN ('word','phrase')", name="ck_vocab_items_item_type"),
)

# Exact-identity matching depends on this pair; queried together on every import row.
source_items = Table(
    "source_items",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("source_id", Integer, ForeignKey("sources.id"), nullable=False),
    Column("item_id", Integer, ForeignKey("vocab_items.id"), nullable=False),
    Column("source_level", Integer, nullable=False),
    Column("level_position", Integer, nullable=False),
    Column("is_active", Boolean, nullable=False, default=True, server_default="1"),
    Column("source_note", Text, nullable=True),
    Column("first_seen_at", DateTime, nullable=False, server_default=func.current_timestamp()),
    Column("last_seen_at", DateTime, nullable=False, server_default=func.current_timestamp()),
    UniqueConstraint("source_id", "item_id", name="uq_source_items_source_item"),
    UniqueConstraint("source_id", "source_level", "level_position", name="uq_source_items_slot"),
)

item_meanings = Table(
    "item_meanings",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("item_id", Integer, ForeignKey("vocab_items.id"), nullable=False),
    Column("meaning", String, nullable=False),
    Column("normalized_meaning", String, nullable=False),
    Column("origin", String, nullable=False, default="imported", server_default="imported"),
    Column("created_at", DateTime, nullable=False, server_default=func.current_timestamp()),
    UniqueConstraint("item_id", "normalized_meaning", name="uq_item_meanings_item_meaning"),
    CheckConstraint("origin IN ('imported','merged','user_synonym')", name="ck_item_meanings_origin"),
)

item_forms = Table(
    "item_forms",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("item_id", Integer, ForeignKey("vocab_items.id"), nullable=False),
    Column("form", String, nullable=False),
    Column("normalized_form", String, nullable=False),
    Column("form_type", String, nullable=False),
    Column("created_at", DateTime, nullable=False, server_default=func.current_timestamp()),
    UniqueConstraint("item_id", "normalized_form", "form_type", name="uq_item_forms_item_form"),
    CheckConstraint("form_type IN ('display','kana','alternate')", name="ck_item_forms_type"),
)

examples = Table(
    "examples",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("item_id", Integer, ForeignKey("vocab_items.id"), nullable=False),
    Column("source_id", Integer, ForeignKey("sources.id"), nullable=False),
    Column("japanese_sentence", Text, nullable=False),
    Column("kana_sentence", Text, nullable=False),
    Column("english_translation", Text, nullable=False),
    Column("created_at", DateTime, nullable=False, server_default=func.current_timestamp()),
)

similar_items = Table(
    "similar_items",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("item_id", Integer, ForeignKey("vocab_items.id"), nullable=False),
    Column("similar_text", String, nullable=False),
    Column("created_at", DateTime, nullable=False, server_default=func.current_timestamp()),
)

# Many-to-many: which source(s) contributed a given (deduplicated) meaning/similar-item
# row. Lets exact-match reimport diffing compare a source's row against only what that
# source itself previously contributed, instead of everything any source ever added to
# the shared canonical item (the bug: a merge from source B making source A's unchanged
# reimport look "changed" forever). item_meanings/similar_items themselves stay exactly
# as deduplicated as before -- this only tracks attribution on top.
item_meaning_sources = Table(
    "item_meaning_sources",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("item_meaning_id", Integer, ForeignKey("item_meanings.id"), nullable=False),
    Column("source_id", Integer, ForeignKey("sources.id"), nullable=False),
    Column("created_at", DateTime, nullable=False, server_default=func.current_timestamp()),
    UniqueConstraint("item_meaning_id", "source_id", name="uq_item_meaning_sources"),
)

similar_item_sources = Table(
    "similar_item_sources",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("similar_item_id", Integer, ForeignKey("similar_items.id"), nullable=False),
    Column("source_id", Integer, ForeignKey("sources.id"), nullable=False),
    Column("created_at", DateTime, nullable=False, server_default=func.current_timestamp()),
    UniqueConstraint("similar_item_id", "source_id", name="uq_similar_item_sources"),
)

# Not written to by the import pipeline; exists now so later phases (user notes/mnemonics)
# need no migration, and so reimport logic never has to reason about this table at all.
item_notes = Table(
    "item_notes",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("item_id", Integer, ForeignKey("vocab_items.id"), nullable=False, unique=True),
    Column("note_text", Text, nullable=True),
    Column("mnemonic_text", Text, nullable=True),
    Column("created_at", DateTime, nullable=False, server_default=func.current_timestamp()),
    Column("updated_at", DateTime, nullable=False, server_default=func.current_timestamp()),
)

# srs_stage 0 = imported/unlearned, not yet activated by a lesson quiz (stages 1-9 are
# Apprentice 1 .. Burned per the SRS ladder, assigned starting in a later phase).
study_progress = Table(
    "study_progress",
    metadata,
    Column("item_id", Integer, ForeignKey("vocab_items.id"), primary_key=True),
    Column("srs_stage", Integer, nullable=False, default=0, server_default="0"),
    Column("next_review_at", DateTime, nullable=True),
    Column("learned_at", DateTime, nullable=True),
    Column("burned_at", DateTime, nullable=True),
    Column("total_reviews", Integer, nullable=False, default=0, server_default="0"),
    Column("correct_reviews", Integer, nullable=False, default=0, server_default="0"),
    Column("incorrect_reviews", Integer, nullable=False, default=0, server_default="0"),
    Column("meaning_correct", Integer, nullable=False, default=0, server_default="0"),
    Column("meaning_incorrect", Integer, nullable=False, default=0, server_default="0"),
    Column("japanese_correct", Integer, nullable=False, default=0, server_default="0"),
    Column("japanese_incorrect", Integer, nullable=False, default=0, server_default="0"),
    Column("current_correct_streak", Integer, nullable=False, default=0, server_default="0"),
    Column("longest_correct_streak", Integer, nullable=False, default=0, server_default="0"),
    Column("updated_at", DateTime, nullable=False, server_default=func.current_timestamp()),
)

# Schema only in Phase 1; populated starting with the review engine phase.
review_sessions = Table(
    "review_sessions",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("started_at", DateTime, nullable=False, server_default=func.current_timestamp()),
    Column("completed_at", DateTime, nullable=True),
    Column("session_type", String, nullable=False),
    CheckConstraint("session_type IN ('lesson_quiz','review')", name="ck_review_sessions_type"),
)

review_attempts = Table(
    "review_attempts",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("session_id", Integer, ForeignKey("review_sessions.id"), nullable=False),
    Column("item_id", Integer, ForeignKey("vocab_items.id"), nullable=False),
    Column("prompt_type", String, nullable=False),
    Column("submitted_answer", Text, nullable=False),
    Column("normalized_answer", Text, nullable=False),
    Column("is_correct", Boolean, nullable=False),
    Column("is_typo_warning", Boolean, nullable=False, default=False, server_default="0"),
    Column("created_at", DateTime, nullable=False, server_default=func.current_timestamp()),
    CheckConstraint("prompt_type IN ('meaning','japanese')", name="ck_review_attempts_prompt_type"),
)

import_runs = Table(
    "import_runs",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("started_at", DateTime, nullable=False, server_default=func.current_timestamp()),
    Column("completed_at", DateTime, nullable=True),
    Column("status", String, nullable=False),
    Column("summary_json", Text, nullable=True),
    CheckConstraint("status IN ('running','completed','failed')", name="ck_import_runs_status"),
)

import_run_items = Table(
    "import_run_items",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("import_run_id", Integer, ForeignKey("import_runs.id"), nullable=False),
    Column("source_id", Integer, ForeignKey("sources.id"), nullable=False),
    Column("item_id", Integer, ForeignKey("vocab_items.id"), nullable=True),
    Column("candidate_item_ids_json", Text, nullable=True),
    Column("row_number", Integer, nullable=True),
    Column("status", String, nullable=False),
    Column("message", Text, nullable=True),
    Column("raw_data_json", Text, nullable=True),
    Column("created_at", DateTime, nullable=False, server_default=func.current_timestamp()),
    CheckConstraint(
        "status IN ('new','added_to_source','unchanged','updated_pending_approval',"
        "'duplicate_pending_merge','merged','skipped','error','inactive',"
        "'approved','kept_separate')",
        name="ck_import_run_items_status",
    ),
)

settings_table = Table(
    "settings",
    metadata,
    Column("key", String, primary_key=True),
    Column("value", String, nullable=True),
    Column("updated_at", DateTime, nullable=False, server_default=func.current_timestamp()),
)

# Remembers a manual duplicate-review decision keyed by (source, normalized japanese,
# normalized kana), so a row that only ever partially matches an existing item (and thus
# can never become a plain exact-match reimport) doesn't get re-staged as a fresh
# duplicate_pending_merge -- and its resulting source_items relationship doesn't get
# flipped inactive by the "not seen this run" cleanup -- on every future import.
source_row_resolutions = Table(
    "source_row_resolutions",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("source_id", Integer, ForeignKey("sources.id"), nullable=False),
    Column("normalized_japanese", String, nullable=False),
    Column("normalized_kana", String, nullable=False),
    Column("resolution_type", String, nullable=False),
    Column("resolved_item_id", Integer, ForeignKey("vocab_items.id"), nullable=True),
    Column("created_from_import_run_item_id", Integer, ForeignKey("import_run_items.id"), nullable=True),
    Column("created_at", DateTime, nullable=False, server_default=func.current_timestamp()),
    Column("updated_at", DateTime, nullable=False, server_default=func.current_timestamp()),
    UniqueConstraint(
        "source_id", "normalized_japanese", "normalized_kana", name="uq_source_row_resolutions_row"
    ),
    CheckConstraint(
        "resolution_type IN ('merged','kept_separate','skipped')",
        name="ck_source_row_resolutions_type",
    ),
)
