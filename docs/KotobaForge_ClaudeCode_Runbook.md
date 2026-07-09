# KotobaForge Claude Code Runbook

This is the recommended end-to-end process for building KotobaForge with Claude Code.

## 0. Files to put in the project root

Create a new project folder named `kotobaforge`, then place these files in it:

```text
kotobaforge/
  CLAUDE.md
  KotobaForge_Requirements_Spec.md
  KotobaForge_Phase_Checklist.md
  KotobaForge_ClaudeCode_Prompts.md
  wordbanks/
    work.xlsx
```

Use `KotobaForge_Sample_Wordbank.xlsx` as the first `work.xlsx` test file.

## 1. Install prerequisites

Recommended Windows setup:

1. Install Git for Windows.
2. Install Python 3.12 or newer.
3. Install Node.js LTS.
4. Install VS Code.
5. Install the Claude Code VS Code extension.
6. Install the Claude Code CLI if you want to use it from the terminal.

## 2. Create the empty repo

From PowerShell or Git Bash:

```bash
mkdir kotobaforge
cd kotobaforge
git init
mkdir docs wordbanks prompts
```

Copy the documents into the repo:

```text
docs/KotobaForge_Requirements_Spec.md
docs/KotobaForge_Phase_Checklist.md
prompts/KotobaForge_ClaudeCode_Prompts.md
CLAUDE.md
wordbanks/work.xlsx
```

Then commit the starter documents:

```bash
git add .
git commit -m "Add KotobaForge planning docs"
```

## 3. Start Claude Code

In VS Code, open the `kotobaforge` folder.

Preferred workflow:

1. Open the Claude Code panel in VS Code.
2. Ask Claude to read the requirements and phase checklist.
3. Keep tasks small and commit after each phase.

Alternative terminal workflow:

```bash
cd path/to/kotobaforge
claude
```

## 4. Claude Code workflow pattern

For every phase, use this loop:

1. Ask Claude to explore and plan.
2. Review the plan.
3. Ask Claude to implement only that phase.
4. Require it to run tests/build checks.
5. Run the app yourself.
6. Commit working code.
7. Move to the next phase.

Do not ask Claude to build the entire app in one shot.

## 5. Recommended phase order

### Phase 0 — Scaffold

Goal: create FastAPI backend, React/Vite frontend, SQLite config, launch scripts, and README.

Exit criteria:

- Backend starts locally.
- Frontend starts locally.
- README has run commands.
- Git commit exists.

### Phase 1 — Database and import system

Goal: implement SQLite models, Excel import, validation, source detection, duplicate staging, and import logs.

Exit criteria:

- App imports sample Excel file.
- App validates required columns.
- App stores sources and items.
- Progress fields live in SQLite, not Excel.
- Duplicate candidates are detected.
- Tests cover parsing and validation.

### Phase 2 — Dashboard and source levels

Goal: build WaniKani-like local dashboard with source cards, lessons, reviews, source-specific level progress, and SRS distribution.

Exit criteria:

- Dashboard shows available lessons/reviews.
- Sources have independent levels.
- 20-item level batches exist.
- 90% Guru progression works.

### Phase 3 — Lessons and lesson quiz

Goal: implement five-item lessons, lesson pages, notes/mnemonics display, and required lesson quiz.

Exit criteria:

- User can select a source and start lessons.
- Only five new items are introduced per lesson.
- Lesson quiz asks Japanese→English and English→Japanese.
- Failed lesson quiz items repeat until passed.
- Completed lesson items enter SRS.

### Phase 4 — Review engine and answer checking

Goal: implement strict typed reviews, WaniKani-like SRS timings, typo shake behavior, Japanese answer validation, and item advancement/demotion.

Exit criteria:

- Review prompts require both directions.
- Item advances only if both directions are correct.
- Wrong answer marks entire item wrong.
- Romaji is rejected for Japanese answers.
- Kana or kanji accepted when listed.
- English meaning answers are case-insensitive and punctuation-insensitive.
- Typo/near-miss warnings do not let the user self-grade.
- SRS timing matches the spec.

### Phase 5 — Item pages and lightweight admin

Goal: implement item detail pages, source membership, personal synonyms, notes, mnemonics, similar items, review history, inactive items, and import admin screens.

Exit criteria:

- User can search items.
- User can view item details.
- User can add personal synonyms, notes, and mnemonics.
- Admin page shows import logs and inactive items.
- Duplicate merge review is usable.

### Phase 6 — Polish and packaging

Goal: improve WaniKani-like layout, add word/phrase colors, shake animation, keyboard flow, launcher script, README, and final test pass.

Exit criteria:

- `start_kotobaforge.bat` opens backend/frontend or runs the packaged local app.
- UI works on desktop.
- Enter key submits and advances.
- Word items use pink scheme; phrase items use blue scheme.
- Tests pass.
- README explains setup, imports, and usage.

## 6. Suggested git strategy

Use one branch at first:

```bash
git checkout -b main
```

Commit after every phase:

```bash
git status
git add .
git commit -m "Implement Excel import pipeline"
```

Avoid letting Claude make huge uncommitted changes across many unrelated files.

## 7. How to recover when Claude gets stuck

Use this prompt:

```text
Stop coding for now. Summarize what you changed, what is failing, the exact command/output showing the failure, and the smallest next step to fix it. Do not make more edits until I approve the plan.
```

Then paste the failure summary back into ChatGPT or start a fresh Claude Code session.

## 8. Final definition of done

KotobaForge V1 is complete when:

- You can add words/phrases to an Excel source file.
- The app refreshes/imports them without losing progress.
- You can study a source-specific five-item lesson.
- Lesson quiz must be passed.
- Reviews appear on schedule.
- Reviews require Japanese→English and English→Japanese typed answers.
- Items advance/demote according to the WaniKani-inspired SRS ladder.
- Duplicate words across sources share progress and can be merged.
- The app runs locally in a browser on Windows.
- No cloud accounts, online services, audio, AI, JLPT, or external lookups are required.
