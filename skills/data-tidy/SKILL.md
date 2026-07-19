---
name: data-tidy
description: >-
  Clean up messy data into a structured, validated table — from any source (a junk-filled
  .xlsx/CSV, a pasted email/markdown table, a Word table, or an Outlook .msg) to a clean .xlsx
  plus an audit/change report. Use when the user wants to "clean up this data", "tidy this
  spreadsheet", "normalise this list", "structure this messy export", "dedupe this",
  "standardise these dates / currencies", or "turn this into a clean table". (For getting
  data OUT of PDFs — tables, forms, scanned documents — use data-extract, not this skill.)
  Works INTENT-FIRST: it asks what
  the data is for and the expected output up front, then profiles → proposes a transform
  recipe → you confirm → applies it deterministically → reports every change and flags cells
  for review. Never mangles silently; transforms are computed locally by a deterministic engine. Standalone —
  no other toolkit required. NOT deal-document intelligence (lease abstraction,
  model review, comps) — that's out of scope.
---

# Data Tidy

Turn messy data — in whatever shape it arrives — into a clean, validated structured table
(`.xlsx`) plus an **audit/change report**. The design is **intent-first** (ask the purpose
and the wanted output before guessing) and **human-in-the-loop** (propose → confirm →
apply → report). Transforms are deterministic and logged; nothing is changed silently.

> **Self-sufficient & local engine.** Runs on its own — no other toolkit needed. All processing
> (including OCR) happens on your machine: no cloud OCR, no external APIs, no third-party uploads.
> Note the AI agent driving the skill does send whatever it reads into its context to your AI
> provider — "never leaves the machine" is not claimed. See `../../DATA-HANDLING.md`.

## Workflow

### 0 — Intent (ask up front — this is what makes it economical)
Before profiling anything, ask (a short `AskUserQuestion`):
1. **What's this data for?** (the purpose / where it's going)
2. **What output do you want?** — the target columns / shape, e.g. `Investor | Commitment (£) | Close date (DD MMM YYYY)`. A one-line sketch is enough.
3. **Any rules?** — a master list to validate against, required fields, format preferences.

This pins the target, so the profile inspects *against it* and the recipe is proposed
toward a known destination — not guessed. Fewer tokens, fewer wrong turns.

### 1 — Ingest
The engine is **shared** at the plugin-root `scripts/` (with `data-extract`). Add it to
the path, run from this skill directory:
```python
import sys, pathlib
sys.path.insert(0, str(pathlib.Path("../../scripts").resolve()))   # shared dataclean + ingest
import ingest, dataclean
```
> **Run from the skill directory** (`skills/data-tidy/`). The `../../scripts` path resolves
> to the toolkit-root `scripts/` where `dataclean.py` and `ingest.py` live.
`ingest.read_any(path)` handles `.xlsx`/`.csv`/`.tsv`, `.pdf` (ruled tables → text-layout →
**local-OCR** fallback for scans), `.docx` tables, and `.msg`; `ingest.read_paste(text)`
handles a pasted markdown/TSV/CSV table. Returns `(rows, note)`.
For a **multi-tab workbook** it won't guess: `read_any` auto-selects the single data sheet,
but if several tabs hold data it raises `SheetSelectionRequired` — call `ingest.list_sheets(path)`,
show the tabs, then `read_any(path, sheet="<name>")`.

For files with 10k+ rows, use `ingest.read_large` instead of `read_any` to avoid OOM. See
`references/large-file-patterns.md` for vectorised operation guidance.

### 2 — Profile (against the target)
`dataclean.profile_table(header, rows)` / `dataclean.render_profile(...)` — shows columns,
inferred types (incl. **categorical** / **ordinal**), % missing, distinct counts, sample
values, duplicate rows. Read-only; "see the mess" before touching it. Focus on the columns
the target output needs.

For a scored health check, `dataclean.score_quality(header, rows)` /
`render_quality_report(...)` grade each column (completeness A–F, type consistency) and list
issues by severity (missing, won't-parse, standardisation candidates, whitespace/encoding
noise). **Quality-report-only mode:** if the user just wants "a data quality report", run
profile + score, deliver the report, and stop — no recipe, no output table. Re-run after
applying to show the lift (before → after).

### 3 — Propose the recipe
Draft a **recipe** (the declarative transform spec — see `references/recipe-spec.md`):
which source column → which target column, the type/format per column (house defaults:
**dates → DD MMM YYYY**, **amounts → exact `Decimal`**, **currency → amount + code**; a bare
`$` is treated as ambiguous, not assumed USD — give the expected `currency`, or split the code
out with `code_target`), dedup keys, and validation rules. Show it to the user.

For **categorical** columns with inconsistent variants ("USA" / "U.S.A." / "united states"),
propose a value standardisation as part of the recipe: `propose_value_map(col_values,
master=…)` → `render_value_map_proposals(...)` for the user to confirm →
`value_map_from_clusters(clusters, accepted=[...])` baked into the column as `value_map`.
Heuristic, so **never auto-applied** — confirm first, like the rest of the recipe.

### 4 — Confirm → 5 — Apply
On the user's OK:
```python
header, rows, log = dataclean.apply_recipe(raw_rows, recipe, masters={"investors": {...}})
dataclean.write_xlsx(header, rows, "clean.xlsx")
```
Deterministic: header detection, drop blank/total rows, per-column conversion (failures
**kept raw + flagged**, soft warnings **converted + flagged**), exact dedup, fuzzy
near-dups **flagged not merged**, validation (required / regex / master-list / unique).

### 6 — Report
`dataclean.render_report(log)` → a change report: rows in/out, per-column converted/flagged counts,
every flagged cell with its reason, validation failures. Deliver the clean `.xlsx` + the report.

### 7 — Triage: a reusable runner, or just deliver?
**Default: just deliver** the clean `.xlsx` + report and stop — a **one-off or simple**
tidy-up doesn't need runner/card files. **Emit a bundle only when it's worth it:** the source
**recurs** (a monthly/weekly export of the same shape, or the user will reuse it), **or** the
recipe is **complex** (many columns / mappings / validations) so re-deriving is costly. When
borderline, **ask**. If yes:
```python
dataclean.emit_runner("[working-folder]", "investor-commitments", "tidy", recipe)
# -> tidy_investor-commitments.py + .md card + copies of dataclean/ingest/extract
```
It deploys the runner (recipe baked in), the card, **and a copy of the engine into that
folder**, so the bundle runs without the plugin. Keep them together (e.g. in your synced or shared file store).
Reproducible — matters for the audit trail.

## Reuse — when a runner already exists (verify FIRST, then run)
Before re-deriving, **check for a `tidy_[name].{py,md}`** for this source. If one exists,
**don't blind-run it** (a column may have been added/renamed):
1. **Read the `.md` card** — note the expected source columns.
2. **Inspect the current file** and **compare**.
3. **Match → run it:** `python tidy_[name].py [file] [-o out.xlsx]` — deterministic, ~no
   tokens. The runner self-checks and **warns** on missing *or new* columns.
4. **Drifted → adapt:** update the recipe and **regenerate** (`emit_runner`), then run.

## Safety
- **Human-in-the-loop** — always show the profile and the proposed recipe *before* applying,
  and the change report *after*. Never transform financial data silently.
- **Never invents values** — unparseable cells are kept raw and flagged, not guessed.
- A **cleaned draft for review**, not a certified dataset.

## OCR (scanned PDFs)
Only used when a PDF page has **no text layer**, and only via **local Tesseract** — never a
cloud OCR, so no third-party service ever sees your documents. OCR'd content is lower-fidelity and
flagged for review. Tesseract is an external binary (not pip): `envcheck.py` probes for it;
if missing, digital PDFs/spreadsheets still work fully — only scans need it. On Windows it
can be installed via `winget install UB-Mannheim.TesseractOCR` (needs admin rights; on a
managed machine, ask IT to deploy it). See `references/recipe-spec.md` for setup detail.

## Files
- `../../scripts/dataclean.py` *(shared)* — engine: `profile_table`/`render_profile`,
  `score_quality`/`render_quality_report` (health grading), `propose_value_map`/
  `render_value_map_proposals`/`value_map_from_clusters` (categorical standardisation),
  `apply_recipe` (now supports `value_map` + `case`/`strip_specials`/`fix_encoding`),
  `write_xlsx`, `render_report`, **`emit_runner`** (reuse runners/cards); parsers
  (date/number/currency); `--self-test`.
- `../../scripts/ingest.py` *(shared)* — source adapters incl. PDF + local-OCR;
  `read_any`(`sheet=`)/`read_paste`/`read_text`/`list_sheets`/`list_pdf_tables`;
  `ocr_available()`; `--self-test`.
- `scripts/make_samples.py` — writes synthetic messy samples to `examples/`.
- `references/recipe-spec.md` — the recipe format, the intent step, OCR/Tesseract setup.
- `examples/` — synthetic messy samples (no real data) to build/demo against.

## Principles

Behavioural charter: `../../PRINCIPLES.md` — drafts not advice, never invent, honesty and
calibration, plain speech, action boundary.

## Data handling
The engine runs **on your machine** and makes no network calls — messy inputs are often sensitive
or confidential (commitments, schedules, statements). **Never send the data, or OCR of it, to an
external or third-party tool**; the clean `.xlsx` and the recipe stay in your synced or shared
file store. Be aware the AI agent driving this skill sends whatever it reads into its context to
your AI provider, as in any AI-assisted work. A bare list with nothing sensitive attached isn't confidential,
but treat financial exports as sensitive by default. Full rule: `../../DATA-HANDLING.md`. (No
external connector — files are local paths in your synced or shared file store.)

## Feedback
Have an improvement or found a bug in this skill? Capture it with the toolkit's
**shared feedback format** — `../../CONTRIBUTING.md#skill-feedback-format` — so it reaches the skill author
consistently (skill name, what you did, expected vs actual, severity, suggestion).
Save it as a `.txt` file (`feedback_[skill]_[date].txt`) and hand it to the
user to file (e.g. in your synced or shared file store) — manual, no fixed destination; fix in scope if asked.

## Requirements & mode
Pre-screen: see `../../README.md#mode--environment-compatibility` and run `python ../../scripts/envcheck.py`. Needs
Python + `openpyxl`; `PyMuPDF` for PDF input (`pdfplumber` optional — preferred for messy /
borderless PDF tables); `python-docx` for `.docx`; `extract_msg` for `.msg`; **local Tesseract**
only for scanned-PDF OCR (degrades cleanly without it). Mostly portable; OCR is the one
local-binary dependency.
