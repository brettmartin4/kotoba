# KotobaForge Claude Code Prompts

Use these prompts one at a time. Do not paste the whole document as a single instruction. Keep the requirements spec and checklist in the repo so Claude can read them from files.

---

## Prompt 0 — Project onboarding

```text
Read `docs/KotobaForge_Requirements_Spec.md`, `docs/KotobaForge_Phase_Checklist.md`, and `CLAUDE.md`. Do not write code yet.

Summarize the intended V1 architecture, the main constraints, the phase order, and any places where the requirements are ambiguous or risky. Then propose the exact folder structure you recommend for this repo.
```

---

## Prompt 1 — Scaffold plan

```text
We are starting Phase 0 only. Create a concise implementation plan for the initial scaffold.

Target stack:
- Python FastAPI backend
- SQLite database
- React + Vite frontend
- Local Windows-first development

Do not implement yet. Tell me the files you plan to create, the commands you will run, and how you will verify the scaffold works.
```

---

## Prompt 2 — Implement scaffold

```text
Implement Phase 0 from `docs/KotobaForge_Phase_Checklist.md`.

Create the backend, frontend, basic health endpoint, initial README, and local run instructions. Keep changes minimal and reviewable. After implementation, run the backend startup check and frontend build/startup check if possible. Report the exact commands and outputs.
```

---

## Prompt 3 — Phase 1 import/database plan

```text
We are starting Phase 1 only. Read the requirements sections on Excel word banks, import behavior, duplicate handling, source membership, SRS/progress storage, and database schema.

Create a detailed plan for the SQLite schema and Excel import pipeline. Include tables, columns, relationships, validation rules, and tests. Do not implement until I approve the plan.
```

---

## Prompt 4 — Implement database schema

```text
Implement only the database models/migrations/setup needed for Phase 1. Do not build the UI yet.

Add tests or simple verification scripts that prove the database initializes correctly. Run them and report the exact output.
```

---

## Prompt 5 — Implement Excel import

```text
Implement the Excel `.xlsx` import pipeline for Phase 1.

Requirements:
- One Excel file per source.
- Filename determines source identity.
- Required columns: item_type, japanese, kana, meanings, part_of_speech.
- Recommended columns: romaji, example_japanese, example_kana, example_english, similar_items, source_note.
- Semicolon-separated lists.
- Store progress and personal data only in SQLite.
- Validate missing columns and missing row fields.
- Detect duplicates by written form or reading, not meaning.
- Do not delete progress when a word disappears from a source file; mark source membership inactive.

Use `wordbanks/work.xlsx` as the first test file. Write and run tests for parsing and validation.
```

---

## Prompt 6 — Duplicate merge workflow backend

```text
Implement the backend-side duplicate merge workflow for Phase 1.

When a duplicate is detected, the app should stage a merge decision rather than silently overwrite. The merge view will later show imported candidate details and existing item details side by side. For now, implement the data model/API support for staged duplicate decisions and a backend function/API to approve a merge.

Merged duplicates must:
- share global study progress
- merge meanings and examples when approved
- add source membership for the new source
- add the item to the new source's next available level slot

Write tests for this behavior.
```

---

## Prompt 7 — Dashboard and source levels

```text
Implement Phase 2.

Build the backend endpoints and frontend dashboard needed to show:
- source cards
- source display names
- source-specific current level
- lessons available
- reviews available
- SRS distribution

Implement source-specific 20-item level batches and 90% Guru-or-higher level progression. There is no global level. Existing Guru/Burned duplicate items count immediately in every source they belong to.

Run relevant tests and frontend build checks.
```

---

## Prompt 8 — Lessons

```text
Implement Phase 3.

Lessons must:
- be selected by source
- introduce five new items at a time
- respect a daily cap of ten new items
- show item type, Japanese, kana, romaji, meanings, part of speech, examples, user notes, and mnemonics where available
- use pink theme for words and blue theme for phrases
- end with a required lesson quiz
- quiz both Japanese→English and English→Japanese
- repeat failed quiz items until passed
- activate passed items into Apprentice 1 and schedule their first review

Run tests/checks and provide manual test steps.
```

---

## Prompt 9 — Reviews and answer checking

```text
Implement Phase 4 review engine and answer checking.

Reviews must:
- show due items only
- ask both Japanese→English and English→Japanese for each item
- advance only if both prompts are correct
- mark the item wrong if either prompt is wrong
- prevent self-grading
- accept kana or kanji for Japanese answers, but reject romaji
- accept English meanings case-insensitively and punctuation-insensitively
- ignore minor article differences where practical
- accept user synonyms
- provide WaniKani-like near-miss warning/shake behavior without allowing cheating
- schedule next review using the WaniKani-inspired SRS ladder from the spec
- round review times down to the hour

Write unit tests for answer normalization, Japanese answer handling, and SRS transitions.
```

---

## Prompt 10 — Item pages and admin

```text
Implement Phase 5.

Build:
- searchable item list
- item detail page
- source membership display
- examples and translations display
- similar items display as plain text
- personal synonyms editing
- notes editing
- mnemonics editing
- review stats/history display
- import/admin page
- import logs page or section
- inactive items section
- staged duplicate merge side-by-side panels

Do not add full bulk editing or burned-item resurrection in V1.
```

---

## Prompt 11 — Polish and launcher

```text
Implement Phase 6 polish.

Requirements:
- desktop-first layout
- WaniKani-inspired big Lessons and Reviews buttons
- word items use pink theme
- phrase items use blue theme
- correct answers show green feedback
- incorrect answers show red feedback
- near-miss answers shake/warn
- Enter key submits answer and advances after feedback
- minimal distraction-free review screen
- Windows launcher script that starts the local app and opens the browser
- README updated with setup, running, word-bank editing, import refresh, and troubleshooting instructions

Run backend tests, frontend build checks, and provide a manual end-to-end test script.
```

---

## Prompt 12 — Final review

```text
Perform a final V1 readiness review against `docs/KotobaForge_Requirements_Spec.md` and `docs/KotobaForge_Phase_Checklist.md`.

Create a table with:
- requirement
- status: complete / partial / missing
- evidence: file path, test name, or manual test step
- recommended fix if incomplete

Do not implement fixes yet. This is an audit pass only.
```

---

## Prompt 13 — Fix final gaps

```text
Based on the final readiness review, implement only the missing or partial V1 requirements that are safe to complete now. Keep changes focused. Run tests/build checks afterward and report exact results.
```
