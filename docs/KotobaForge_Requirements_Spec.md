# KotobaForge Requirements & Vibe-Coding Specification

**Project name:** KotobaForge  
**Document version:** V1.0 draft  
**Target release:** Local-only V1 MVP  
**Primary user:** Brett Martin  
**Purpose:** Build a local WaniKani-inspired Japanese vocabulary/phrase SRS app using user-supplied word banks.

---

## 1. Executive Summary

KotobaForge is a local browser-based Japanese vocabulary and phrase learning application. It is inspired by the strict lesson/review structure of WaniKani, but it focuses exclusively on user-provided Japanese words and phrases rather than radicals, kanji, or prebuilt vocabulary.

The core use case is sentence-mining or source-mining from work, manga, anime, visual novels, and other personally meaningful sources. The user maintains one Excel word-bank file per source. The app imports these files into a local SQLite database, preserves study progress across imports, detects duplicates, supports source-specific levels, and schedules strict typed reviews using a WaniKani-like SRS ladder.

V1 should be fully usable without accounts, cloud sync, internet services, audio, AI, JLPT metadata, pitch accent, or external lookups.

---

## 2. Product Goals

KotobaForge must:

1. Let the user manually maintain Japanese vocabulary and phrase word banks in Excel files.
2. Import and refresh those word banks into a local database without losing study progress.
3. Organize study by source, such as `Work`, `Fate/Stay Night`, or a specific manga/VN/anime.
4. Provide WaniKani-inspired lessons, lesson quizzes, typed reviews, SRS stages, and level progression.
5. Be strict enough to avoid Anki-style self-grading temptation.
6. Support both Japanese-to-English meaning recall and English-to-Japanese production recall.
7. Accept kana or kanji for Japanese answers, but not romaji.
8. Support user-added accepted meanings/synonyms, notes, and mnemonics.
9. Run locally from a Windows machine in a browser.
10. Be architected so a future web/account-based version would not require a total rewrite.

---

## 3. Non-Goals for V1

V1 must **not** include:

1. User accounts.
2. Cloud sync.
3. Online deployment.
4. External AI services.
5. Required internet access.
6. Audio playback.
7. Listening quizzes.
8. Pitch accent diagrams.
9. JLPT levels.
10. Automatic frequency ranking.
11. External dictionary lookup.
12. CSV import.
13. Mobile-first layout.
14. Mac-specific support.
15. Burned-item resurrection.
16. Full admin bulk editing.
17. WaniKani copyrighted images, text, or branding assets.

The app may be WaniKani-inspired in workflow and visual structure, but it should use its own name, styling, copy, and assets.

---

## 4. Recommended Tech Stack

### 4.1 Backend

**Python FastAPI**

Rationale:

- User is most comfortable with Python.
- FastAPI provides a clean API layer.
- Easier future migration to account-based web deployment than a fully local-only script.
- Good compatibility with SQLite and Excel parsing.

### 4.2 Frontend

**React + Vite**

Rationale:

- Review and lesson screens need fast UI state changes.
- Easier to implement Enter-key behavior, answer feedback, shake animation, color-coded prompts, modal dialogs, and dashboard widgets.
- More suitable for WaniKani-like UX than a purely server-rendered Flask/Jinja app.

### 4.3 Database

**SQLite**

Rationale:

- Local, portable, simple.
- No separate database server required.
- Good for V1 and still useful for future migration to PostgreSQL/Supabase.

### 4.4 Word Bank Format

**Excel `.xlsx` only for V1**

Rationale:

- Better than CSV for manually editing Japanese text, example sentences, multiple meanings, and notes.
- Avoids CSV quoting issues with commas in example sentences.
- Easier to expand later with multiple sheets if needed.

### 4.5 Local Launcher

V1 should include a Windows launch script, for example:

```bat
Start KotobaForge.bat
```

Expected behavior:

1. Start the backend server.
2. Start or serve the frontend.
3. Open the browser automatically to the local app URL.

A later version may package this into a proper executable or installer.

---

## 5. User Model

### 5.1 Primary User

A Japanese learner who wants to study personally encountered vocabulary from specific sources.

### 5.2 User Stories

1. As a learner, I want to add words from work so that I can study language I actually encounter in my professional life.
2. As a learner, I want to add words from a visual novel so that I can improve comprehension of that specific story.
3. As a learner, I want the app to use strict reviews so that I cannot cheat by manually marking an answer correct.
4. As a learner, I want words grouped by source so that I can study only words from a specific source.
5. As a learner, I want duplicate words across sources to share progress so that I do not relearn a word from scratch just because it appears in a new source.
6. As a learner, I want typed Japanese answers to accept kana or kanji but reject romaji.
7. As a learner, I want to add accepted synonyms so that reasonable alternative English meanings can be accepted in future reviews.
8. As a learner, I want imports to preserve existing progress so that refreshing a word bank never resets my study history.
9. As a learner, I want the app to warn me about duplicates so that I can merge meanings/examples instead of creating redundant entries.
10. As a learner, I want lessons and reviews to resemble WaniKani’s strict workflow so that the experience feels familiar and motivating.

---

## 6. Core Concepts

### 6.1 Item

An `item` is either a Japanese word or a Japanese phrase.

Allowed item types:

1. `word`
2. `phrase`

V1 must not support grammar-only entries or full sentence cards, except very short phrase-like expressions such as `しょうがない`.

### 6.2 Source

A `source` is where the item came from.

Examples:

- Work
- Fate/Stay Night
- Manga title
- Anime title
- Visual novel title

In V1, each Excel file represents one source.

### 6.3 Source Level

A `source level` is a WaniKani-inspired level within one source. There is no global account level.

Example:

- `Work Level 1`
- `Work Level 2`
- `Fate/Stay Night Level 1`
- `Fate/Stay Night Level 2`

Each source has its own independent level structure.

### 6.4 Review Item

Each review item has two required prompt types:

1. **Meaning prompt:** Japanese → English meaning.
2. **Japanese production prompt:** English meaning/context → Japanese word or phrase.

The item advances only if both prompt types are answered correctly during that review session.

### 6.5 Burned Item

A burned item has completed the SRS ladder and no longer appears in normal reviews.

V1 must not include resurrect/unburn functionality.

---

## 7. Word Bank File Specification

### 7.1 File Organization

The app should allow the user to select a word-bank folder.

Example:

```text
wordbanks/
  work.xlsx
  fate_stay_night.xlsx
  yotsuba.xlsx
```

Each `.xlsx` file represents one source.

### 7.2 Source Display Name

The source key may come from the filename, but the user must be able to edit the display name inside the app.

Example:

- Filename: `fate_stay_night.xlsx`
- Display name: `Fate/Stay Night`

### 7.3 Required Sheet

V1 should expect a sheet named:

```text
items
```

If the sheet is missing, the import validator should show a clear error.

### 7.4 Required Columns

The `items` sheet must include these columns:

| Column | Required | Description |
|---|---:|---|
| `item_type` | Yes | Must be `word` or `phrase`. |
| `japanese` | Yes | Main display form. May include kanji or kana. |
| `kana` | Yes | Kana reading/accepted kana form. If kana-only, same as `japanese`. |
| `romaji` | Yes | Romaji display for lessons only. Never accepted in reviews. |
| `meanings` | Yes | Semicolon-separated accepted English meanings. |
| `part_of_speech` | Yes | Noun, verb, adjective, expression, etc. |
| `example_japanese` | No | Semicolon-separated Japanese example sentences. Strongly recommended. |
| `example_kana` | No | Semicolon-separated kana readings for each example, paired by position with `example_japanese`. |
| `example_english` | No | Semicolon-separated English translations, paired by position with `example_japanese`. |
| `similar_items` | No | Plain-text similar words/phrases. |
| `source_note` | No | Free-text note about this item's use in this source. |

### 7.5 Optional Future Columns

These may be supported later but are not required for V1:

| Column | Description |
|---|---|
| `verb_type` | Optional metadata such as ichidan/godan. |
| `transitivity` | Optional transitive/intransitive marker. |
| `formality` | Optional notes such as casual, polite, slang, business. |
| `extra_forms` | Additional accepted kanji/kana spellings. |

### 7.6 Meanings Format

Meanings are semicolon-separated.

Example:

```text
confirm; verify; check
```

All listed meanings are treated equally. There is no required primary meaning in V1.

### 7.7 Example Format

Examples are stored across three separate columns: `example_japanese`, `example_kana`, and `example_english`.

Each column may contain multiple semicolon-separated values, and examples are paired by position across the three columns.

Example:

```text
example_japanese: 確認してください。; メールを確認しました。
example_kana:     かくにんしてください。; メールをかくにんしました。
example_english:  Please check it.; I checked the email.
```

Rules:

1. Separate multiple example entries within a column using semicolons.
2. `example_japanese`, `example_kana`, and `example_english` must have matching counts whenever any of them are present for a row.
3. The importer must reject (block with a clear error) a row where the counts do not match.
4. Examples are strongly recommended but not required.

### 7.8 Similar Items Format

Similar items are plain text in V1.

Example:

```text
確認; 確かめる; 調べる
```

V1 may display these as plain text. A later version may automatically link them to existing entries.

---

## 8. Import and Refresh Requirements

### 8.1 Import Modes

The app must support:

1. **Automatic startup scan** of the selected word-bank folder.
2. **Manual Refresh Word Bank** button.

### 8.2 Import Staging

Imports should be staged before changes are committed.

The import screen should show:

1. New items.
2. Changed items.
3. Potential duplicates.
4. Removed/inactive items.
5. Validation errors.

### 8.3 Validation Rules

The importer must validate:

1. File is `.xlsx`.
2. Required sheet exists.
3. Required columns exist.
4. Required fields are not empty.
5. `item_type` is either `word` or `phrase`.
6. `meanings` contains at least one valid meaning.
7. `japanese` and `kana` are valid Japanese text fields.
8. `romaji` is present (required) but is never used for answer validation; it is for lesson display only.
9. `example_japanese`, `example_kana`, and `example_english` have matching semicolon-separated counts whenever any of them are present.
10. Source can be derived from filename.

### 8.4 Duplicate Detection

V1 has no stable per-row identity key in the `.xlsx` format (no ID column). Identity is inferred from the normalized `japanese` and `kana` fields on each import:

1. **Exact match on normalized `japanese` + `kana`:** treated as the same canonical item. No merge review needed; the row is applied as an update/refresh of the existing item (subject to the changed-item approval flow in §8.7).
2. **Match on `japanese` only, or `kana` only (not both):** treated as a possible duplicate/update requiring user review through the duplicate merge UI. This also covers kana-only homophone collisions, since Japanese has many homophones and an automatic merge would be unsafe.
3. **No match on either `japanese` or `kana`:** treated as a new item.

Duplicate detection must **not** be based on English meaning.

This is a known V1 limitation: if a user edits both the `japanese` and `kana` fields for an existing row enough that neither matches any existing item, the importer will treat it as a brand-new item rather than an edit, and the old item/progress will remain as a separate entry. This is acceptable for V1; a stable row ID is a candidate V2 improvement.

### 8.5 Duplicate Merge UI

When a duplicate is detected, the app must show side-by-side panels:

Left panel:

- Existing item details.
- Existing meanings.
- Existing examples.
- Existing sources.
- Existing SRS stage/progress.

Right panel:

- New imported item details.
- New meanings.
- New examples.
- New source.
- New source-level placement preview.

Actions (mostly all-or-nothing for V1; per-meaning/per-example checkbox selection is deferred to V2):

1. Merge all non-duplicate meanings and examples into the existing canonical item, and add the new source relationship, while preserving existing SRS progress.
2. Add source association only, without merging meanings/examples.
3. Skip imported item.
4. Mark as separate item only if the user explicitly confirms that it is not the same word/phrase.

### 8.6 Cross-Source Duplicate Behavior

If the same item appears in multiple sources:

1. It should exist as one canonical item in the database.
2. It should share the same SRS stage and review statistics across all sources.
3. It should appear in each relevant source’s level structure.
4. If it is already Guru/Burned from another source, it counts toward the new source’s 90% Guru threshold immediately.

### 8.7 Changed Items

If a row's normalized `japanese` + `kana` still matches an existing canonical item (per §8.4, rule 1) but other fields (meanings, examples, part of speech, romaji, etc.) differ from the stored values:

1. The app should ask for approval before applying the change.
2. Existing progress must be preserved.
3. Personal synonyms, notes, mnemonics, and review history must be preserved.

If a row matches on only `japanese` or only `kana`, it is not treated as a simple "changed item" — it goes through the duplicate merge UI (§8.4 rule 2, §8.5) instead, since the app cannot be sure it is the same item.

### 8.8 Removed Items

If an item is removed from a source file:

1. The app should mark that source-item association inactive.
2. The canonical item and progress should remain in the database.
3. Inactive items should appear only in the admin/import page in V1, not on the dashboard.

### 8.9 Import Log

The app must keep an import log.

The import log should track:

1. Import timestamp.
2. Files scanned.
3. New items added.
4. Duplicates detected.
5. Merges approved.
6. Changes approved.
7. Items marked inactive.
8. Validation errors.

The dashboard may show a small summary such as:

```text
12 words and phrases added within the last 7 days.
```

---

## 9. Source-Specific Level System

### 9.1 Level Size

Each source level should contain exactly **20 items** by default.

### 9.2 Level Assignment

Items are assigned to source levels in import order.

When an item is added to a source:

1. Place it in the next available level slot for that source.
2. If the current level has fewer than 20 items, fill that level first.
3. If the current level has 20 items, create the next level.

### 9.3 Level Unlocking

Level 1 is unlocked by default.

Level N+1 unlocks when at least **90%** of Level N items have reached **Guru 1 or higher**.

For a 20-item level, 18 items must be Guru 1 or higher.

Items whose source-item association is marked inactive (§8.8) are excluded from both the level's denominator and the numerator of this calculation — they do not count as part of the level for unlock purposes at all.

### 9.4 No Global Level

The app must not show a global level.

It should show source-specific levels only.

Example:

```text
Work: Level 3
Fate/Stay Night: Level 1
```

### 9.5 Duplicate Items in Source Levels

If a duplicate item is added to a new source and the item is already Guru/Burned:

1. It should still be assigned to that source’s level structure.
2. It should count as already Guru/Burned for source-level progression.
3. It should not reset or duplicate review progress.

---

## 10. Lesson System

### 10.1 Lesson Availability

A lesson is available when:

1. The item belongs to an unlocked source level.
2. The item has not yet been learned.
3. The user has not exceeded the daily new-item cap.
4. The item's source-item association is active (inactive/removed source items are excluded from lesson availability).

### 10.2 Lesson Batch Size

Each lesson batch should contain **5 new items**.

### 10.3 Daily New-Item Cap

The default daily cap is **10 new items per day**, resetting at local midnight using the user's system local time. It is not a rolling 24-hour window.

The app must not block lessons due to review backlog.

### 10.4 Source Selection

The user should be able to choose lessons from a specific source.

Within that source and unlocked level, lesson items should be randomly shuffled.

### 10.5 Lesson Content

Each lesson item should show:

1. Japanese display form.
2. Kana reading.
3. Romaji.
4. English meanings.
5. Part of speech.
6. Examples with translations, if available.
7. Similar items, if available.
8. User notes.
9. Mnemonic, if available.

### 10.6 Editable During Lesson

During the lesson, the user may edit:

1. User synonyms/accepted meanings.
2. General notes.
3. Mnemonic.

The user should not edit source-of-truth fields such as Japanese, kana, romaji, part of speech, or imported examples from the lesson screen.

### 10.7 Lesson Quiz

After lessons, the app must run an immediate lesson quiz.

Requirements:

1. Quiz all 5 newly learned items.
2. Ask both prompt types:
   - Japanese → English meaning.
   - English → Japanese word/phrase.
3. Quiz failures require repeating failed prompts until all items pass.
4. Lesson quiz performance should not count toward normal long-term review statistics, except that passing the quiz activates the item in Apprentice 1.
5. After passing the lesson quiz, each item enters SRS stage Apprentice 1 and receives its first scheduled review.

---

## 11. Review System

### 11.1 Review Availability

Reviews become available based on the item’s `next_review_at` timestamp.

Review times should be rounded down to the start of the hour.

### 11.2 Prompt Types

Each review item requires two prompts:

1. **Meaning prompt:** show Japanese, ask for English.
2. **Japanese production prompt:** show English/context, ask for Japanese.

The item advances only if both prompts are correct in the same review session.

### 11.3 Review Ordering

Review prompts should be randomized.

The two prompts for the same item may appear separated from each other to prevent short-term answer chaining.

### 11.4 Strict Auto-Grading

The app must use automatic grading only.

V1 must not include:

1. “I got it right” button.
2. “Mark correct” button.
3. Self-grading override.
4. Manual answer correction during reviews.

### 11.5 Review Feedback

After submitting an answer:

Correct answer:

1. Show green feedback.
2. Allow Enter to proceed.

Incorrect answer:

1. Show red feedback.
2. Show the correct answer.
3. Allow Enter to proceed.

Near typo / close answer:

1. Show shake animation.
2. Show “Close, but not quite. Try again.”
3. Do not count as wrong unless the user submits a non-close wrong answer.

### 11.6 Post-Answer Information Panel

After answering, the bottom half of the review screen should include tabs similar in spirit to WaniKani item detail sections.

Suggested tabs:

1. Meaning.
2. Reading / Japanese.
3. Examples.
4. Notes.
5. Similar.

---

## 12. Answer Checking Requirements

### 12.1 English Meaning Answers

English meaning answers should be normalized before checking.

Normalization should:

1. Trim leading/trailing whitespace.
2. Collapse repeated spaces.
3. Ignore capitalization.
4. Ignore punctuation.
5. Ignore common articles such as `a`, `an`, and `the`.
6. Optionally handle simple plural/singular forms locally.

Accepted English answers include:

1. Imported meanings.
2. User-added synonyms.
3. Approved merged meanings from duplicate imports.

### 12.2 English Typo Handling

The app should support conservative typo tolerance.

Recommended approach:

1. Normalize the submitted answer and accepted meanings.
2. If exact normalized match: correct.
3. If close edit-distance match to an accepted meaning: show typo warning and let the user retry.
4. If not close: mark incorrect.

V1 should not allow the user to override an incorrect answer as correct.

### 12.3 Japanese Production Answers

Japanese answer checking should:

1. Accept the `japanese` display form.
2. Accept the `kana` form.
3. Accept manually added alternate Japanese forms if supported.
4. Reject romaji.
5. Normalize Unicode width where appropriate.
6. Treat hiragana and katakana as interchangeable for kana-only comparison where practical.

Examples:

| Prompt answer | Expected behavior |
|---|---|
| `確認` | Accepted if listed form. |
| `かくにん` | Accepted if kana reading. |
| `kakunin` | Rejected. |
| `カクニン` | Accepted if kana normalization determines it matches `かくにん`. |

### 12.4 Multiple Meanings

All imported meanings are treated equally.

Example:

```text
confirm; verify; check
```

Any of those should be accepted.

### 12.5 Multiple Japanese Forms

V1 must support at least:

1. Main display form.
2. Kana form.

Future versions may add a dedicated `extra_forms` field for additional accepted spellings.

---

## 13. SRS System

### 13.1 SRS Stage Groups

The app should use a WaniKani-like nine-stage SRS system:

| Stage | Label |
|---:|---|
| 1 | Apprentice 1 |
| 2 | Apprentice 2 |
| 3 | Apprentice 3 |
| 4 | Apprentice 4 |
| 5 | Guru 1 |
| 6 | Guru 2 |
| 7 | Master |
| 8 | Enlightened |
| 9 | Burned |

### 13.2 SRS Timings

After an item is learned, it starts at Apprentice 1.

| Current stage | Next review interval after correct answer |
|---|---:|
| Apprentice 1 | 4 hours |
| Apprentice 2 | 8 hours |
| Apprentice 3 | 1 day |
| Apprentice 4 | 2 days |
| Guru 1 | 1 week |
| Guru 2 | 2 weeks |
| Master | 1 month |
| Enlightened | 4 months |
| Burned | No further normal reviews |

### 13.3 Correct Review Behavior

If both prompt types are answered correctly during a review session:

1. Increment SRS stage by 1.
2. Schedule next review based on the new stage interval.
3. If the item reaches stage 9, mark it Burned.

### 13.4 Incorrect Review Behavior

Each review item has two prompts (meaning and Japanese production). The item advances one SRS stage only if both prompts are answered correctly in that review. If either prompt is wrong, the whole item counts as incorrect for that review session:

1. The item review is considered failed.
2. The SRS stage decreases by exactly one stage, never below stage 1 (Apprentice 1).
3. The item is rescheduled based on its new stage.
4. The item cannot advance during that review session.

V1 demotion logic:

```text
if any prompt for the item was answered incorrectly this review session:
    new_srs_stage = max(1, current_srs_stage - 1)
else:
    new_srs_stage = current_srs_stage + 1
```

Prompt-level attempts (which specific prompt was right/wrong) are still recorded per-prompt in review history for statistics, but SRS stage movement itself is calculated once per item per review session, not per prompt.

Near-typo warnings do not count as a wrong answer unless the answer is ultimately submitted as incorrect.

### 13.5 Burned Items

Burned items:

1. Do not appear in normal reviews.
2. Remain visible on item pages and admin pages.
3. Cannot be resurrected in V1.
4. May be included in a later optional burned-item extra-study mode.

---

## 14. Dashboard Requirements

The dashboard should resemble a WaniKani-like home page while using original styling and copy.

### 14.1 Required Dashboard Elements

The dashboard must show:

1. Large Lessons button.
2. Large Reviews button.
3. Review count available now.
4. Lesson count available now.
5. Source-specific level list.
6. Source-specific level progress.
7. Current SRS distribution.
8. Daily streak.
9. Short import summary, such as words added in the last 7 days.

### 14.2 Optional V1 Dashboard Elements

If simple to implement:

1. Accuracy summary.
2. Words/phrases learned.
3. Words/phrases burned.
4. Upcoming review counts by day.

### 14.3 Deferred Dashboard Elements

Move to V2 unless easy:

1. Troublesome words chart.
2. Detailed accuracy graphs.
3. Review heatmap.
4. Burned extra study.

---

## 15. UI / Visual Design Requirements

### 15.1 General Style

The UI should be:

1. Desktop-first.
2. Minimal.
3. Clean.
4. WaniKani-inspired but not asset-copying.
5. Light mode only in V1.

### 15.2 Color Scheme

Item type determines the color scheme:

1. `word` items use a pink background/accent.
2. `phrase` items use a blue background/accent.

Correct/incorrect feedback:

1. Correct answers use green.
2. Incorrect answers use red.
3. Near-typo warnings should use shake animation and neutral/warning styling.

### 15.3 Keyboard Behavior

The Enter key should:

1. Submit an answer when the input field is active.
2. Proceed to the next prompt after feedback is shown.
3. Not require mouse clicks during normal reviews.

### 15.4 Review Screen Layout

The review screen should include:

1. Large centered prompt.
2. Clear question label.
3. Single typed input field.
4. Item-type color background.
5. Feedback state after answer.
6. Bottom information panel with tabs.

### 15.5 Lesson Screen Layout

The lesson screen should include:

1. Item display.
2. Reading/kana/romaji.
3. Meanings.
4. Examples.
5. Notes.
6. Mnemonic.
7. Similar words.
8. Button to continue.
9. Indicator for progress through the 5-item lesson batch.

---

## 16. Item Page Requirements

Each item should have a detail page showing:

1. Japanese display form.
2. Kana.
3. Romaji.
4. Item type.
5. Meanings.
6. User synonyms.
7. Part of speech.
8. Examples and translations.
9. Source membership.
10. Source levels.
11. Current SRS stage.
12. Next review date/time.
13. Accuracy summary.
14. Review count.
15. Incorrect count.
16. Consecutive correct review count.
17. Notes.
18. Mnemonic.
19. Similar items.
20. Limited review history summary.

Editable on item page:

1. User synonyms.
2. Notes.
3. Mnemonic.
4. Source display name, if on source settings page.

Not editable on item page in V1:

1. Imported Japanese form.
2. Imported kana.
3. Imported romaji.
4. Imported part of speech.
5. Imported examples.
6. Imported meanings, except through duplicate merge or approved source-file change.

---

## 17. Admin / Import Page Requirements

The V1 admin page should be lightweight but functional.

### 17.1 Required Features

1. Select word-bank folder.
2. Refresh word bank.
3. Show current import status.
4. Show validation errors.
5. Show duplicate merge queue.
6. Show changed item approval queue.
7. Show inactive source items.
8. Show import history link/page.
9. Show source list and source display names.

### 17.2 Not Required in V1

1. Full spreadsheet-like editing.
2. Bulk editing meanings.
3. Bulk deleting items.
4. Manual database editing.
5. CSV import.
6. Cloud backup/export.

---

## 18. Search and Browse Requirements

The app should include a searchable word-bank browser.

Search should cover:

1. Japanese display form.
2. Kana.
3. Romaji.
4. English meanings.
5. Notes.
6. Mnemonics.
7. Source.
8. Source note.
9. Similar items.

Filters should include:

1. Source.
2. Item type.
3. SRS stage group.
4. Learned/unlearned.
5. Burned.
6. Inactive source associations.

---

## 19. Statistics Requirements

### 19.1 Per-Item Stats

Track:

1. Current SRS stage.
2. Next review time.
3. Total review sessions.
4. Total correct review sessions.
5. Total incorrect review sessions.
6. Meaning prompt correct/incorrect count.
7. Japanese prompt correct/incorrect count.
8. Current consecutive successful review sessions.
9. Longest correct streak.
10. Burned date, if burned.

### 19.2 Dashboard Stats

Show:

1. Reviews available now.
2. Lessons available now.
3. Source level progress.
4. SRS distribution.
5. Daily streak.
6. New items added within last 7 days.

### 19.3 V2 Stats

Defer:

1. Troublesome words chart.
2. Correct/incorrect bar charts.
3. Review heatmap.
4. Long-term forecast charts.
5. Detailed analytics page.

---

## 20. Suggested Database Schema

This is a suggested starting point. The coding agent may refine it, but it should preserve the same concepts.

### 20.1 `sources`

Stores source files and display names.

Fields:

```text
id
source_key
display_name
file_path
is_active
created_at
updated_at
last_imported_at
```

### 20.2 `vocab_items`

Canonical item table. One item may belong to multiple sources.

Fields:

```text
id
item_type
japanese
kana
romaji
part_of_speech
is_active
created_at
updated_at
```

### 20.3 `source_items`

Many-to-many relationship between sources and items.

Fields:

```text
id
source_id
item_id
source_level
level_position
is_active
first_seen_at
last_seen_at
```

### 20.4 `item_meanings`

Imported accepted meanings.

Fields:

```text
id
item_id
meaning
normalized_meaning
origin
created_at
```

`origin` values:

```text
imported
merged
user_synonym
```

### 20.5 `item_forms`

Accepted Japanese forms.

Fields:

```text
id
item_id
form
normalized_form
form_type
created_at
```

`form_type` examples:

```text
display
kana
alternate
```

### 20.6 `examples`

Example sentences.

Fields:

```text
id
item_id
japanese_sentence
english_translation
source_id
created_at
```

### 20.7 `item_notes`

User notes and mnemonics.

Fields:

```text
id
item_id
note_text
mnemonic_text
created_at
updated_at
```

### 20.8 `similar_items`

Plain-text similar item entries.

Fields:

```text
id
item_id
similar_text
created_at
```

### 20.9 `study_progress`

One row per canonical item.

Fields:

```text
item_id
srs_stage
next_review_at
learned_at
burned_at
total_reviews
correct_reviews
incorrect_reviews
meaning_correct
meaning_incorrect
japanese_correct
japanese_incorrect
current_correct_streak
longest_correct_streak
updated_at
```

### 20.10 `review_sessions`

Fields:

```text
id
started_at
completed_at
session_type
```

`session_type` examples:

```text
lesson_quiz
review
```

### 20.11 `review_attempts`

Fields:

```text
id
session_id
item_id
prompt_type
submitted_answer
normalized_answer
is_correct
is_typo_warning
created_at
```

### 20.12 `import_runs`

Fields:

```text
id
started_at
completed_at
status
summary_json
```

### 20.13 `import_run_items`

Fields:

```text
id
import_run_id
source_id
item_id
row_number
status
message
raw_data_json
```

Statuses:

```text
new
updated_pending_approval
duplicate_pending_merge
merged
skipped
error
inactive
```

### 20.14 `settings`

Fields:

```text
key
value
updated_at
```

Example settings:

```text
wordbank_folder
daily_lesson_cap
lesson_batch_size
```

---

## 21. Suggested API Endpoints

### 21.1 Dashboard

```text
GET /api/dashboard
```

Returns lesson counts, review counts, source levels, SRS distribution, streak, and import summary.

### 21.2 Sources

```text
GET /api/sources
PATCH /api/sources/{source_id}
```

### 21.3 Import

```text
POST /api/import/refresh
GET /api/import/runs
GET /api/import/runs/{run_id}
POST /api/import/duplicates/{duplicate_id}/merge
POST /api/import/changes/{change_id}/approve
POST /api/import/changes/{change_id}/reject
```

### 21.4 Items

```text
GET /api/items
GET /api/items/{item_id}
PATCH /api/items/{item_id}/notes
POST /api/items/{item_id}/synonyms
DELETE /api/items/{item_id}/synonyms/{synonym_id}
```

### 21.5 Lessons

```text
GET /api/lessons/available
POST /api/lessons/start
POST /api/lessons/{session_id}/answer
POST /api/lessons/{session_id}/complete
```

### 21.6 Reviews

```text
GET /api/reviews/available
POST /api/reviews/start
POST /api/reviews/{session_id}/answer
POST /api/reviews/{session_id}/complete
```

---

## 22. Screen-by-Screen UI Specification

### 22.1 Dashboard

Purpose:

Provide immediate access to lessons and reviews.

Required components:

1. App title: KotobaForge.
2. Lessons button.
3. Reviews button.
4. Available review count.
5. Available lesson count.
6. Source-level progress cards.
7. SRS distribution.
8. Daily streak.
9. Recent import summary.
10. Navigation to Browse, Admin, and Import Log.

### 22.2 Lessons Available Screen

Purpose:

Let the user choose which source to study.

Required components:

1. List of sources.
2. Current level for each source.
3. Number of available lessons.
4. Start 5-item lesson button.
5. Daily lesson cap display.

### 22.3 Lesson Screen

Purpose:

Teach 5 new words/phrases.

Required components:

1. Large item display.
2. Color based on word/phrase.
3. Kana and romaji.
4. Meanings.
5. Part of speech.
6. Examples.
7. Notes.
8. Mnemonic.
9. Similar items.
10. Continue button.
11. Progress indicator.

### 22.4 Lesson Quiz Screen

Purpose:

Require initial active recall before an item enters SRS.

Required components:

1. Prompt.
2. Typed answer input.
3. Enter-to-submit behavior.
4. Correct/incorrect/typo feedback.
5. Repeat failed prompts until all passed.

### 22.5 Review Screen

Purpose:

Strict scheduled SRS review.

Required components:

1. Large prompt.
2. Prompt type label.
3. Typed input.
4. Word/phrase color background.
5. Correct/incorrect feedback.
6. Shake animation for close typo.
7. Bottom information tabs after answer.
8. Enter-to-submit and Enter-to-continue behavior.

### 22.6 Item Detail Page

Purpose:

View item information and edit personal learning aids.

Required components:

1. Item heading.
2. All imported item details.
3. Meanings.
4. User synonyms.
5. Notes.
6. Mnemonic.
7. Similar items.
8. Source memberships.
9. SRS status.
10. Review summary.

### 22.7 Browse/Search Page

Purpose:

Search the full local word bank.

Required components:

1. Search input.
2. Source filter.
3. SRS filter.
4. Item type filter.
5. Results table.
6. Link to item detail pages.

### 22.8 Admin / Import Page

Purpose:

Manage word-bank import and validation.

Required components:

1. Word-bank folder selector.
2. Refresh button.
3. Current import status.
4. Validation errors.
5. Duplicate merge queue.
6. Changed item approval queue.
7. Inactive items section.
8. Source display name editor.
9. Import log link.

### 22.9 Duplicate Merge Screen

Purpose:

Resolve duplicates safely.

Required components:

1. Existing item side-by-side with imported item.
2. Show meanings/examples/sources/progress.
3. Merge meanings/examples button.
4. Add source only button.
5. Skip button.
6. Keep separate button with confirmation.

### 22.10 Import Log Page

Purpose:

View previous import activity.

Required components:

1. Import run list.
2. Timestamp.
3. Files scanned.
4. New/merged/changed/error counts.
5. Detailed row-level messages.

---

## 23. Acceptance Criteria

### 23.1 Word-Bank Import

V1 is acceptable when:

1. The app can import `.xlsx` files from a selected folder.
2. Each file becomes a source.
3. Required columns are validated.
4. New items are added to SQLite.
5. Existing item progress is preserved on re-import.
6. Missing files/removed rows mark source associations inactive.
7. Duplicates trigger a merge UI instead of silently duplicating items.

### 23.2 Lessons

V1 is acceptable when:

1. The user can select a source.
2. The app shows available lessons from unlocked source levels.
3. Lessons are delivered in batches of 5.
4. Daily lesson cap defaults to 10 new items.
5. Lesson quiz asks both English meaning and Japanese production.
6. Failed lesson quiz prompts repeat until passed.
7. Passing lesson quiz activates items at Apprentice 1.

### 23.3 Reviews

V1 is acceptable when:

1. Reviews become available according to SRS timing.
2. Each review item asks both prompt types.
3. The item advances only if both prompt types are correct.
4. Incorrect answers demote the item.
5. Typo warnings do not count as incorrect.
6. There is no self-grade/manual override.
7. Enter key can drive the full review flow.

### 23.4 Answer Checking

V1 is acceptable when:

1. English answers are case-insensitive.
2. English punctuation is ignored.
3. Articles are ignored.
4. User synonyms are accepted.
5. Japanese kana and kanji forms are accepted.
6. Romaji answers are rejected for Japanese production prompts.
7. Close English typos trigger a retry warning.

### 23.5 Source Levels

V1 is acceptable when:

1. Each source has independent levels.
2. Each level contains 20 items.
3. Level 2 unlocks after 90% of Level 1 items reach Guru 1 or above.
4. Duplicates already Guru/Burned count toward the new source’s level progress.

### 23.6 Dashboard

V1 is acceptable when:

1. Lessons and Reviews buttons are visible.
2. Counts are accurate.
3. Source levels are shown.
4. SRS distribution is shown.
5. Daily streak is shown.
6. Recent import summary is shown.

---

## 24. Implementation Phases

### Phase 0: Project Setup

1. Create FastAPI backend.
2. Create React + Vite frontend.
3. Add SQLite database.
4. Add local development scripts.
5. Add Windows launcher script.

### Phase 1: Database and Import Foundation

1. Implement schema.
2. Implement Excel parser.
3. Implement word-bank folder setting.
4. Implement import validation.
5. Implement source creation.
6. Implement item creation.
7. Implement source-level assignment.

### Phase 2: Admin and Import UI

1. Build admin/import page.
2. Show validation errors.
3. Show import summaries.
4. Add source display name editing.
5. Add import log page.

### Phase 3: Duplicate and Change Handling

1. Implement duplicate detection.
2. Build side-by-side duplicate merge UI.
3. Implement merge meanings/examples.
4. Implement changed item approval.
5. Implement inactive item handling.

### Phase 4: Lessons

1. Build lesson availability API.
2. Build lesson UI.
3. Implement 5-item lesson batches.
4. Implement lesson quiz.
5. Activate items at Apprentice 1 after quiz pass.

### Phase 5: Reviews and SRS

1. Implement review availability.
2. Implement review sessions.
3. Implement meaning answer checking.
4. Implement Japanese answer checking.
5. Implement typo warning.
6. Implement SRS advancement/demotion.
7. Implement burned behavior.

### Phase 6: Dashboard and Browse

1. Build dashboard.
2. Add source-level cards.
3. Add SRS distribution.
4. Add streak tracking.
5. Add browse/search page.
6. Add item detail pages.

### Phase 7: Polish and Testing

1. Add Enter-key review flow.
2. Add shake animation.
3. Add color themes for word/phrase.
4. Add tests for SRS logic.
5. Add tests for import logic.
6. Add tests for answer checking.
7. Fix desktop layout.

---

## 25. V2 / Future Features

Potential V2 features:

1. CSV import.
2. Troublesome words chart.
3. Correct/incorrect bar charts.
4. Burned extra study.
5. Burned item resurrection.
6. Subtitle-to-wordbank converter.
7. Visual novel text-to-wordbank converter.
8. Full admin editor.
9. Bulk tagging.
10. Export/backup.
11. Cloud sync.
12. User accounts.
13. Mobile layout.
14. Linux launcher.
15. Optional local-only LLM helper, if explicitly approved later.
16. Clickable linked similar items.
17. True furigana rendering above kanji.
18. Extra accepted Japanese forms column.

---

## 26. Coding Agent Master Prompt

Use this prompt to start a coding-agent session.

```text
You are helping me build KotobaForge, a local-only Japanese vocabulary and phrase SRS web app inspired by WaniKani's strict lessons/reviews workflow.

Use this requirements document as the source of truth.

Build V1 as:
- Backend: Python FastAPI
- Frontend: React + Vite
- Database: SQLite
- Word-bank format: Excel .xlsx files
- Local target: Windows first, Linux later
- No accounts, cloud sync, external AI, audio, pitch accent, JLPT metadata, external dictionary lookup, or required internet services in V1.

Core V1 behavior:
- The user selects a word-bank folder.
- Each .xlsx file in the folder is one source.
- Each source has independent 20-item levels.
- Source levels unlock when 90% of the previous level reaches Guru 1 or higher.
- Lesson batches contain 5 new items.
- Daily lesson cap is 10 new items.
- Reviews are strict typed reviews with no manual override.
- Each item requires both Japanese-to-English meaning recall and English-to-Japanese production recall.
- Items advance only if both prompts are correct in the same review session.
- Japanese answers accept kana or kanji, but not romaji.
- English answers are case-insensitive, ignore punctuation/articles, and accept imported meanings and user synonyms.
- Close typos should trigger a shake/warning and retry, not an immediate wrong answer.
- SRS stages and timings should follow the WaniKani-like 9-stage ladder defined in the requirements document.
- Progress, notes, mnemonics, synonyms, review history, and import logs are stored in SQLite, not in the Excel files.
- Refreshing word banks must never reset existing progress.
- Duplicates across sources should merge into one canonical item with shared SRS progress.

Before writing code, propose the initial file/folder structure and implementation plan. Then implement the app phase by phase with tests for import, SRS, and answer checking.
```

---

## 27. Phase-Specific Coding Prompts

### 27.1 Project Setup Prompt

```text
Set up the KotobaForge project using FastAPI for the backend, React + Vite for the frontend, and SQLite for local storage. Create a clean monorepo structure with backend, frontend, scripts, and docs folders. Add a Windows .bat launcher that will eventually start the backend and open the local browser app. Do not implement features yet. Focus on scaffold, dependency files, and a minimal health-check page.
```

### 27.2 Database Prompt

```text
Implement the SQLite schema for KotobaForge based on the requirements document. Include tables for sources, vocab_items, source_items, item_meanings, item_forms, examples, item_notes, similar_items, study_progress, review_sessions, review_attempts, import_runs, import_run_items, and settings. Add migration/init logic and basic tests that confirm the schema can be created from scratch.
```

### 27.3 Import Prompt

```text
Implement Excel .xlsx word-bank import for KotobaForge. The app should scan a selected word-bank folder, treat each .xlsx file as a source, read the items sheet, validate required columns, parse meanings and examples, create new items, preserve existing progress, mark removed source associations inactive, and create import log records. Do not silently merge duplicates yet; stage potential duplicates for a later duplicate-resolution UI.
```

### 27.4 Duplicate Merge Prompt

```text
Implement duplicate detection and merge handling. Potential duplicates should be detected by matching Japanese display form, kana form, or accepted Japanese forms, but not English meaning. Show existing and imported items side-by-side in the admin UI. Let the user merge meanings/examples, add the new source association, skip the import, or explicitly keep separate. Cross-source duplicates must share one canonical study_progress row.
```

### 27.5 Lesson Prompt

```text
Implement the lesson system. Lessons should be source-selectable, source-level aware, randomized within the unlocked source level, limited to 5 new items per batch, and capped at 10 new items per day. Lesson screens should show Japanese, kana, romaji, meanings, part of speech, examples, notes, mnemonic, and similar items. After lessons, implement a required lesson quiz with both meaning and Japanese production prompts. Failed prompts repeat until passed. Passing the quiz activates each item at Apprentice 1.
```

### 27.6 Review/SRS Prompt

```text
Implement the review system and SRS engine. Reviews become available by next_review_at. Each item requires both a Japanese-to-English meaning prompt and an English-to-Japanese production prompt. The item advances one SRS stage only if both are correct in the same session; if either is wrong, the item demotes by exactly one SRS stage (never below Apprentice 1). Burned items no longer appear in normal reviews. Add tests for correct advancement, incorrect demotion, burned behavior, and review scheduling.
```

### 27.7 Answer Checking Prompt

```text
Implement strict answer checking. English meaning answers should be case-insensitive, ignore punctuation, ignore common articles, collapse whitespace, optionally handle simple singular/plural variants locally, and accept imported meanings plus user synonyms. Japanese answers should accept the item's Japanese display form, kana form, and approved alternate Japanese forms, while rejecting romaji. Add conservative typo detection for English answers that triggers a retry warning and shake animation without counting as wrong. Add unit tests for all normalization behavior.
```

### 27.8 Dashboard/UI Prompt

```text
Build the KotobaForge dashboard and core UI screens. The dashboard should have large Lessons and Reviews buttons, available counts, source-specific level cards, SRS distribution, daily streak, and recent import summary. The review and lesson screens should be desktop-first, light mode, minimal, and WaniKani-inspired without using WaniKani assets. Use pink backgrounds for word items and blue backgrounds for phrase items. Correct feedback should be green, incorrect feedback red, and close-typo feedback should shake the input.
```

---

## 28. Testing Checklist

### 28.1 Import Tests

1. Imports valid `.xlsx`.
2. Rejects missing `items` sheet.
3. Rejects missing required columns.
4. Rejects invalid `item_type`.
5. Parses semicolon-separated meanings.
6. Parses paired examples.
7. Creates source from filename.
8. Allows source display name editing.
9. Preserves progress after re-import.
10. Marks removed source item inactive.
11. Stages duplicates.

### 28.2 SRS Tests

1. Lesson quiz completion creates Apprentice 1 progress.
2. Apprentice 1 correct schedules review in 4 hours.
3. Apprentice 2 correct schedules review in 8 hours.
4. Guru stages schedule weekly/two-week intervals.
5. Correct review advances one stage.
6. Incorrect review demotes stage.
7. Stage cannot drop below 1.
8. Burned item no longer appears in normal reviews.
9. Duplicate across sources shares progress.

### 28.3 Answer Checking Tests

1. `House` equals `house`.
2. Punctuation ignored.
3. Articles ignored.
4. User synonyms accepted.
5. Romaji rejected for Japanese production.
6. Kana accepted.
7. Kanji accepted.
8. Katakana/hiragana normalization works where practical.
9. Close typo triggers retry warning.
10. Non-close wrong answer counts as incorrect.

### 28.4 UI Tests

1. Enter submits answer.
2. Enter advances after feedback.
3. Word items use pink.
4. Phrase items use blue.
5. Correct answer feedback is green.
6. Incorrect answer feedback is red.
7. Typo warning shakes input.
8. Review screen is usable without mouse.

---

## 29. Development Priorities

The most important implementation areas are:

1. Correct SRS behavior.
2. Strict answer checking.
3. Safe imports that preserve progress.
4. Duplicate merge behavior.
5. Smooth review UX.

The app is only useful if trust in the SRS/progress data is high. Therefore, database integrity and test coverage for SRS/import logic matter more than visual polish.

---

## 30. Final V1 Scope Statement

KotobaForge V1 is complete when the user can:

1. Put `.xlsx` word-bank files into a selected folder.
2. Refresh/import those files into the app.
3. Resolve duplicates safely.
4. Study source-specific 5-item lessons.
5. Pass required lesson quizzes.
6. Complete strict scheduled reviews.
7. Progress items through a WaniKani-like SRS ladder.
8. Preserve all progress across word-bank refreshes.
9. View source levels, SRS distribution, and basic study stats.
10. Add personal synonyms, notes, and mnemonics.

Everything else should be considered V2 or later.
