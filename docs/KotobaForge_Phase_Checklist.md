# KotobaForge Phase Checklist

Use this as the master implementation checklist for Claude Code.

## Phase 0 — Project scaffold

- [x] Create backend folder.
- [x] Create frontend folder.
- [x] Create docs folder.
- [x] Create wordbanks folder.
- [x] Configure Python environment.
- [x] Configure FastAPI app.
- [x] Configure React + Vite app.
- [x] Add SQLite config.
- [x] Add README with run commands.
- [x] Add basic health endpoint.
- [x] Verify backend starts.
- [x] Verify frontend starts.
- [ ] Commit scaffold.

## Phase 1 — Database and Excel import

- [ ] Define SQLite schema/models.
- [ ] Implement source table.
- [ ] Implement vocab item table.
- [ ] Implement source membership / source-level table.
- [ ] Implement accepted meanings table.
- [ ] Implement accepted Japanese forms/readings table.
- [ ] Implement examples table.
- [ ] Implement study progress table.
- [ ] Implement review history table.
- [ ] Implement import log table.
- [ ] Implement Excel parser.
- [ ] Validate required columns.
- [ ] Validate row-level required fields.
- [ ] Parse semicolon-separated meanings/examples.
- [ ] Detect duplicate candidates.
- [ ] Stage duplicate merge decisions.
- [ ] Mark removed source rows inactive.
- [ ] Write tests for import and validation.
- [ ] Commit import system.

## Phase 2 — Dashboard and source levels

- [ ] Implement source list API.
- [ ] Implement source display names.
- [ ] Implement source-specific 20-item level batches.
- [ ] Implement 90% Guru progression logic.
- [ ] Implement dashboard counts.
- [ ] Show lessons available.
- [ ] Show reviews available.
- [ ] Show current source levels.
- [ ] Show SRS distribution.
- [ ] Commit dashboard/level work.

## Phase 3 — Lessons

- [ ] Implement lesson selection by source.
- [ ] Limit lesson batch size to five new items.
- [ ] Enforce daily new lesson cap of ten items.
- [ ] Build lesson item presentation screen.
- [ ] Show word/phrase, reading/romaji, meanings, examples, part of speech, notes/mnemonics.
- [ ] Implement lesson quiz.
- [ ] Ask both Japanese→English and English→Japanese.
- [ ] Repeat failed lesson quiz items until passed.
- [ ] On pass, activate SRS stage Apprentice 1.
- [ ] Commit lesson flow.

## Phase 4 — Reviews and answer checking

- [ ] Implement due review query.
- [ ] Implement review session state.
- [ ] Implement Japanese→English prompt.
- [ ] Implement English→Japanese prompt.
- [ ] Implement auto-grading only.
- [ ] Implement English normalization.
- [ ] Implement Japanese input validation.
- [ ] Reject romaji Japanese answers.
- [ ] Accept kana or kanji forms.
- [ ] Implement near-miss warning/shake behavior.
- [ ] Implement SRS stage advancement.
- [ ] Implement SRS demotion.
- [ ] Implement next-review scheduling.
- [ ] Round review times to the hour.
- [ ] Write tests for answer checking and SRS logic.
- [ ] Commit review engine.

## Phase 5 — Item pages and admin

- [ ] Build searchable item list.
- [ ] Build item detail page.
- [ ] Show source memberships.
- [ ] Show examples and translations.
- [ ] Show similar items as text.
- [ ] Add personal synonyms.
- [ ] Add notes.
- [ ] Add mnemonics.
- [ ] Show review stats/history similar to WaniKani-inspired layout.
- [ ] Build import/admin page.
- [ ] Show import logs.
- [ ] Show inactive items.
- [ ] Show duplicate merge side-by-side panels.
- [ ] Commit admin/item pages.

## Phase 6 — Polish and V1 packaging

- [ ] Apply word pink theme.
- [ ] Apply phrase blue theme.
- [ ] Add correct green / incorrect red feedback.
- [ ] Ensure Enter key submits and advances.
- [ ] Make review screen minimal and desktop-friendly.
- [ ] Add Windows launcher script.
- [ ] Update README.
- [ ] Run backend tests.
- [ ] Run frontend build.
- [ ] Manual end-to-end test with sample word bank.
- [ ] Commit V1 completion.
