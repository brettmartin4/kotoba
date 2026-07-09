# KotobaForge Project Instructions

## Project overview

KotobaForge is a local-only Japanese word/phrase SRS application inspired by WaniKani-style lessons and reviews. It is for user-provided Japanese vocabulary and phrases, not radicals/kanji instruction.

Read `docs/KotobaForge_Requirements_Spec.md` before implementing features. Use `docs/KotobaForge_Phase_Checklist.md` to decide what phase we are in.

## Product constraints

- V1 is local-only and runs in a browser on Windows.
- V1 uses Excel `.xlsx` word-bank files only.
- V1 stores progress, SRS state, personal synonyms, notes, mnemonics, review history, and import logs in SQLite.
- Do not store progress back into Excel files.
- Do not implement accounts, cloud sync, external AI, internet lookup, audio, pitch accent, JLPT, CSV import, or burned-item resurrection in V1.
- Do not use WaniKani copyrighted images, text, characters, or branding. Workflow can be inspired by WaniKani, but assets/copy must be original.

## Recommended stack

- Backend: Python FastAPI
- Database: SQLite
- Frontend: React + Vite
- Word-bank import: Excel `.xlsx`
- Local launch: Windows `.bat` script eventually

## Coding workflow

- Before coding a phase, inspect relevant files and produce a concise implementation plan.
- Implement one phase or feature at a time.
- Prefer small, reviewable changes.
- Run relevant tests and build checks after changes.
- Report exact commands run and results.
- Do not claim success unless tests/build checks pass or you clearly state what could not be verified.
- Ask before large architecture changes.

## Testing expectations

Add tests for core backend logic, especially:

- Excel parsing and validation
- duplicate detection and merge staging
- source-specific levels
- SRS advancement/demotion
- answer checking and normalization
- review scheduling

Frontend behavior should be manually testable with clear steps until automated UI tests are added.

## Domain rules

- Items are either `word` or `phrase`.
- Words use the pink visual scheme.
- Phrases use the blue visual scheme.
- Each source has independent 20-item level batches.
- There is no global level.
- A source unlocks the next level when 90% of that source level's items reach Guru or higher.
- Duplicate items across sources share the same global progress/SRS state.
- Duplicate items should be added to the new source's level structure at the next available level slot when merged.
- Existing Guru/Burned duplicate items count immediately toward the new source level's 90% Guru requirement.

## Review rules

- Reviews are auto-graded only; no self-grading button.
- Each review item requires both Japanese→English and English→Japanese prompts.
- The item advances only if both prompts are correct in the same review session.
- If either prompt is wrong, the whole item is wrong.
- Japanese answers accept kana or kanji listed for that item; romaji is not accepted.
- English meaning answers are case-insensitive, punctuation-insensitive, article-light, and accept manual synonyms.
- Near-miss typo behavior should warn/shake and allow retry without giving a self-grade override.

## Import rules

- Use one Excel file per source.
- Filename determines source identity.
- Source display name can be edited in the app.
- Required columns: `item_type`, `japanese`, `kana`, `meanings`, `part_of_speech`.
- Recommended columns: `romaji`, `example_japanese`, `example_kana`, `example_english`, `similar_items`, `source_note`.
- Semicolon separates multiple meanings/examples/similar items.
- For kana-only items, `japanese` and `kana` may be the same.
- Missing required fields should block import for affected rows and show clear errors.
- Removed rows should mark items inactive for that source, not delete progress.
