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
- Duplicate detection: exact normalized `japanese + kana` match is the same canonical item. A match on `japanese` only or `kana` only is a possible duplicate/update requiring user review in the merge UI. A `japanese + kana` pair matching neither is treated as a new item, even if it turns out to be a heavily edited version of an existing row (acceptable V1 limitation; there is no stable row ID).
- Inactive source-item associations are excluded from lesson availability, source-level 20-item denominators, and 90% Guru unlock calculations. The canonical item and its SRS progress are never deleted.

## Lesson rules

- Lesson batches contain 5 new items.
- The daily new-item cap is 10 items per day, resetting at local midnight in the user's system local time, not a rolling 24-hour window.

## Review rules

- Reviews are auto-graded only; no self-grading button.
- Each review item requires both Japanese→English and English→Japanese prompts.
- The item advances only if both prompts are correct in the same review session.
- If either prompt is wrong, the whole item is wrong and the item demotes by exactly one SRS stage for that review, never below Apprentice 1 (stage 1). Prompt-level attempts are recorded in review history, but SRS stage movement is calculated once per item per review session.
- Japanese answers accept kana or kanji listed for that item; romaji is not accepted.
- English meaning answers are case-insensitive, punctuation-insensitive, article-light, and accept manual synonyms.
- Near-miss typo behavior should warn/shake and allow retry without giving a self-grade override.

## Import rules

- Use one Excel file per source.
- Filename determines source identity.
- Source display name can be edited in the app.
- Required columns: `item_type`, `japanese`, `kana`, `romaji`, `meanings`, `part_of_speech`. `romaji` is required because lessons display it, but it must never be accepted as a Japanese review answer.
- Optional columns: `example_japanese`, `example_kana`, `example_english`, `similar_items`, `source_note`.
- Semicolon separates multiple meanings/examples/similar items.
- `example_japanese`, `example_kana`, and `example_english` are paired by position, each may hold multiple semicolon-separated values, and their counts must match whenever any of them are present; mismatched counts block import for that row.
- For kana-only items, `japanese` and `kana` may be the same.
- Missing required fields should block import for affected rows and show clear errors.
- Removed rows should mark items inactive for that source, not delete progress.
- Duplicate merge in V1 is mostly all-or-nothing: show existing vs. imported side-by-side, then let the user merge all non-duplicate meanings/examples and add the new source relationship into the existing canonical item while preserving existing SRS progress. Per-meaning/per-example checkbox selection is deferred to V2.
