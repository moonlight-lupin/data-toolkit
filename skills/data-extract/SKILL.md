---
name: data-extract
description: >-
  Get STRUCTURED data OUT of documents — PDFs (incl. multi-table/scanned via local OCR), Word,
  PowerPoint (.pptx), and Outlook .msg — into a clean .xlsx plus an audit report. Use when the user wants to "extract
  data from this PDF/document", "pull the table out of this report", "get the figures from these
  statements/certificates", "turn these confirmations into a table", "read the fields off this
  form", or "extract these line items". Two modes: key-value/FORM extraction (label → value, one
  record per document — certificates, confirmations, cover sheets) and TABLE extraction (list a
  document's tables, pick one, pull it). Intent-first; normalises via the shared engine (dates →
  DD MMM YYYY, currency → amount + code) and flags anything unfound or uncertain — never invents
  values. Extraction is computed locally (local OCR only). NOT for already-tabular data (use data-tidy) or deal-document
  intelligence like lease abstraction/model review (out of scope).
---

# Data Extract

Pull structured data **out of documents** and into a clean `.xlsx` + an audit report. The
counterpart to `data-tidy`: **tidy** cleans data that's already roughly tabular;
**extract** locates and pulls data from document-shaped sources (forms, multi-table PDFs,
scans). Both share one engine, so extracted data is normalised and reported the same way.

> **Self-sufficient & local engine.** No other toolkit needed. All processing — including OCR —
> happens on your machine: no cloud OCR, no external APIs, no third-party uploads. Note the AI
> agent driving the skill does send whatever it reads into its context to your AI provider;
> "never leaves the machine" is not claimed. See `../../PRINCIPLES.md#data-handling--pii-policy`.
>
> **Shared engine.** The cleanup primitives live at the plugin-root `scripts/`
> (`dataclean.py`, `ingest.py`); this skill's `scripts/extract.py` adds them to the path.

## Which mode?

| You have… | Mode | Use |
|---|---|---|
| a **form / certificate / confirmation** (label: value) | **fields** | `extract_fields` → one record per doc |
| a **document with one or more tables** | **table** | `list_tables` → `get_table` → the rows |
| **many documents, same shape** (e.g. 30 confirmations) | **fields, batched** | one record each → `fields_to_table` → one `.xlsx` |

## Workflow

### 0 — Intent (ask up front)
What's the document, and **which fields / which table** do you want out? For forms, the
**field list** (name + the labels to look for + type). For tables, the **target columns**.
This pins extraction to a target — economical, no guessing.

### 1 — Set up (run from the skill directory)
First, **check for an existing runner/card for this doc type** (see *Reuse* below) — if one
exists, follow that flow instead of re-deriving. Otherwise:
```python
import sys, pathlib
sys.path.insert(0, str(pathlib.Path("../../scripts").resolve()))   # shared engine
import extract, dataclean      # extract, dataclean, ingest all live in ../../scripts
```
> **Run from the skill directory** (`skills/data-extract/`). The `../../scripts` path resolves
> to the toolkit-root `scripts/` where `extract.py`, `dataclean.py` and `ingest.py` live.

### 2 — Extract

**Form / key-value** — one record per document:
```python
FIELDS = [
  {"name": "Investor",   "labels": ["investor", "name of investor"], "type": "text"},
  # mixed-currency batch: keep the code beside the amount with code_target (amount + code)
  {"name": "Commitment", "labels": ["commitment", "amount"], "type": "currency",
   "code_target": "Commitment ccy"},
  {"name": "Close date", "labels": ["close date", "closing"], "type": "date"},
]
record, flags = extract.extract_fields("subscription.pdf", FIELDS)
```
For a **currency** field, add `code_target` to keep the detected code in its own key on the
record (mirrors the tidy recipe) — essential for **mixed-currency batches** (GBP / SGD / USD in
one run) so the amount isn't delivered stripped of its code. Give an expected `currency` instead
(or as well) only when the documents are single-currency and you want a bare `$` resolved to it.
`extract_fields` finds `Label: value` / `Label[tab]value` / `Label   value` / `Label .... value`
(dotted leader), **and the next-line layout** (label alone, value on the line below — common on
confirmations/certificates), stopping at the next field's label so it won't grab a neighbouring
label. Converts by type (amounts as exact `Decimal`; bare `$` ambiguous → give expected
`currency`) and **flags** anything not found or uncertain (kept raw, never invented). Genuinely
2-D box/grid layouts still need **table mode** instead.

**Tables** — pick, then pull:
```python
for c in extract.list_tables("report.pdf"):   # {page, index, rows, cols, preview}
    ...                                        # show candidates, let the user choose
rows = extract.get_table("report.pdf", page=1, index=0)
```

**Scanned docs** — handled automatically: a page with no text layer falls back to **local
Tesseract OCR** (`ingest.ocr_available()` to check). OCR use is noted in the ingest/read_text
note as lower-fidelity; it is not tagged per row.

### Image inputs — charts, table screenshots, diagrams
When the source is a **chart, table screenshot, UI capture, or diagram image** (`.png` /
`.jpg` / `.jpeg` / `.gif` / `.webp` / `.bmp`), use `scripts/image_extract.py` to extract
structured data via a vision model — **not** Tesseract (Tesseract mangles tables and cannot
read chart data points):

```bash
python scripts/image_extract.py chart.png -o extracted.xlsx
python scripts/image_extract.py ./screenshots/ -o batch.xlsx   # one sheet per image + combined
```

Classification + prompts: `references/image-prompts.md`. Requires a vision-capable
OpenAI-compatible endpoint (`VISION_API_KEY` / `OPENAI_API_KEY`, optional `VISION_BASE_URL` /
`VISION_MODEL`). Without a key the script exits clearly — it does not silently fall back to
OCR. Results are cached by file+prompt hash; large images (>5MB / >2048px) are compressed
before the API call.

**PowerPoint decks (`.pptx`)** — `ingest.read_any` / `ingest.read_pptx` extracts
**tables** from all slides (same row contract as `.docx`). Slide titles/bullets are
summarised in the ingest note, not mixed into the table rows. Image-only slides are
flagged for manual review or vision-model extraction. Legacy `.ppt` is not supported —
convert to `.pptx` first.

### 3 — Normalise, output, report
For tables, pass the rows through the shared recipe just like tidy
(`dataclean.apply_recipe`). For batched forms:
```python
header, rows = extract.fields_to_table(records, extract.field_columns(FIELDS))
dataclean.write_xlsx(header, rows, "extracted.xlsx")
print(extract.render_fields_report(records, flags_list))
```
`extract.field_columns(FIELDS)` gives the column order and inserts each currency field's
`code_target` column right after its amount — so the workbook keeps *amount + code*. (A plain
`[f["name"] for f in FIELDS]` would drop the code columns.)
Deliver the `.xlsx` + the report (unfound / verify flags).

### 4 — Triage: a reusable runner, or just deliver?
**Default: just deliver the result** (the `.xlsx` + report) and stop — for a **one-off or
simple** extraction, don't create runner/card files; they'd only be clutter.

**Emit a self-contained reuse bundle only when it's worth it:**
- **Recurring** — the same doc type will come again (monthly statements, batches of the same
  confirmation), or the user says they'll reuse it; **or**
- **Complex** — many fields / fiddly label matching / multi-table, so re-deriving next time
  is genuinely costly.

When it's borderline, **ask the user**. If yes:
```python
dataclean.emit_runner("[working-folder]", "subscription-confirmation", "extract", FIELDS)
# -> extract_subscription-confirmation.py + .md card + copies of dataclean/ingest/extract
```
It deploys the runner (`.py`, spec baked in), the card (`.md`), **and a copy of the engine**
into that folder — so the bundle runs *without the plugin installed*. Keep them together
(e.g. in your synced or shared file store, beside the docs). Pass the real working-folder path, not the skill folder.

## Reuse — when a runner already exists (verify FIRST, then run)
If a `extract_[doctype].{py,md}` exists for this document, **do not blind-run it** —
slight drift (a renamed label, an added column) would otherwise pass silently:
1. **Read the `.md` card** — note the expected fields/labels.
2. **Inspect the current source** (`ingest.read_text` / open it).
3. **Compare** to the card's *Expected source*.
4. **Match → run it:** `python extract_[doctype].py [doc...] [-o out.xlsx]` — deterministic,
   ~no reasoning tokens. The runner also self-checks and **warns** on missing fields.
5. **Drifted → adapt:** update the spec for the change and **regenerate** the runner
   (`emit_runner`), then run. Don't run a stale spec.

## Safety
- **Human-in-the-loop** — show what was extracted and the flags; let the user verify before
  it's relied on. A **draft extraction for review**, not a certified dataset.
- **Never invents** — an unfound field is blank + flagged; OCR/ambiguous values are flagged.

## OCR (scanned documents)
Local **Tesseract** only — never a cloud OCR, so no third-party service ever sees your documents. External
binary (not pip): `python ../../scripts/envcheck.py` probes for it. Without it, digital PDFs,
Word and `.msg` still work; only image/scanned pages need it. Windows install:
`winget install UB-Mannheim.TesseractOCR` (admin rights; on a managed machine, ask IT to deploy).

## Files
- `../../scripts/extract.py` *(shared)* — `extract_fields`, `fields_to_table`, `list_tables`,
  `get_table`, `render_fields_report`; reuses `dataclean` + `ingest`; `--self-test`.
- `../../scripts/dataclean.py` *(shared)* — the engine + **`emit_runner`** (reuse runners/cards).
- `../../scripts/ingest.py` *(shared)* — source adapters incl. `read_text` + local-OCR.
- `scripts/image_extract.py` — vision-model extraction for chart / table / UI / diagram images;
  `parse_markdown_table`, batch → styled `.xlsx`.
- `references/extraction-guide.md` — field-list spec, table selection, extract-vs-tidy, reuse.
- `references/image-prompts.md` — image-type → prompt strategy table.
- `examples/sample_subscription_confirmation.pdf` — a synthetic form to try `extract_fields`.

## Principles

Behavioural charter: `../../PRINCIPLES.md` — drafts not advice, never invent, honesty and
calibration, plain speech, action boundary.

## Data handling
The engine runs **on your machine** and makes no network calls for PDF/form/table extraction
(local OCR only). **Image/chart extraction** (`image_extract.py`) is the exception: it sends
the (possibly compressed) image to a user-configured vision API — treat that like any other
external tool under `PRINCIPLES.md#data-handling--pii-policy` (de-identify first when the image holds PII or
confidential figures). The documents are often sensitive or confidential (subscription
confirmations, statements, certificates name parties and amounts). **Never send a document,
its text, or OCR of it to an external or third-party tool** unless the user has explicitly
chosen vision extraction for an image; the extracted `.xlsx` stays in your synced or shared
file store. Be aware the AI agent driving this skill sends whatever it reads into its context
to your AI provider, as in any AI-assisted work. Full rule: `../../PRINCIPLES.md#data-handling--pii-policy`.
(No external connector — files are local paths in your synced or shared file store.)

## Feedback
Have an improvement or found a bug in this skill? Capture it with the toolkit's
**shared feedback format** — `../../CONTRIBUTING.md#skill-feedback-format` — so it reaches the skill author
consistently (skill name, what you did, expected vs actual, severity, suggestion).
Save it as a `.txt` file (`feedback_[skill]_[date].txt`) and hand it to the
user to file (e.g. in your synced or shared file store) — manual, no fixed destination; fix in scope if asked.

## Requirements & mode
Pre-screen: see `../../README.md#mode--environment-compatibility` and run `python ../../scripts/envcheck.py`. Needs
Python + `PyMuPDF` (PDF), `openpyxl` (output); `pdfplumber` (optional — preferred for messy /
borderless PDF tables), `python-docx` for `.docx`, `python-pptx` for `.pptx`, `extract_msg` for
`.msg`; **local Tesseract** only for scanned-document OCR (degrades cleanly without it).
**Image/chart extraction** needs a vision-capable OpenAI-compatible API endpoint + key
(`Pillow`, `requests`, `pandas` optional helpers) — without it `image_extract.py` exits
clearly and does not fall back to Tesseract.
