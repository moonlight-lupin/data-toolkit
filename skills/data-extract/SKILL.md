---
name: data-extract
description: >-
  Get STRUCTURED data OUT of documents — PDFs (incl. multi-table/scanned via local OCR), Word,
  and Outlook .msg — into a clean .xlsx plus an audit report. Use when the user wants to "extract
  data from this PDF/document", "pull the table out of this report", "get the figures from these
  statements/certificates", "turn these confirmations into a table", "read the fields off this
  form", or "extract these line items". Two modes: key-value/FORM extraction (label → value, one
  record per document — certificates, confirmations, cover sheets) and TABLE extraction (list a
  document's tables, pick one, pull it). Intent-first; normalises via the shared engine (dates →
  DD MMM YYYY, currency → amount + code) and flags anything unfound or uncertain — never invents
  values. Runs fully local. NOT for already-tabular data (use data-tidy) or deal-document
  intelligence like lease abstraction/model review (out of scope).
---

# Data Extract

Pull structured data **out of documents** and into a clean `.xlsx` + an audit report. The
counterpart to `data-tidy`: **tidy** cleans data that's already roughly tabular;
**extract** locates and pulls data from document-shaped sources (forms, multi-table PDFs,
scans). Both share one engine, so extracted data is normalised and reported the same way.

> **Self-sufficient & local.** No other toolkit needed. All processing is local; sensitive
> or confidential business/financial data and any OCR of it never leave the machine.
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

### 2 — Extract

**Form / key-value** — one record per document:
```python
FIELDS = [
  {"name": "Investor",   "labels": ["investor", "name of investor"], "type": "text"},
  {"name": "Commitment", "labels": ["commitment", "amount"], "type": "currency", "currency": "GBP"},
  {"name": "Close date", "labels": ["close date", "closing"], "type": "date"},
]
record, flags = extract.extract_fields("subscription.pdf", FIELDS)
```
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
Tesseract OCR** (`ingest.ocr_available()` to check). OCR'd content is lower-fidelity and flagged.

### 3 — Normalise, output, report
For tables, pass the rows through the shared recipe just like tidy
(`dataclean.apply_recipe`). For batched forms:
```python
header, rows = extract.fields_to_table(records, [f["name"] for f in FIELDS])
dataclean.write_xlsx(header, rows, "extracted.xlsx")
print(extract.render_fields_report(records, flags_list))
```
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
Local **Tesseract** only — never a cloud OCR (sensitive data must not leave the machine). External
binary (not pip): `python ../../scripts/envcheck.py` probes for it. Without it, digital PDFs,
Word and `.msg` still work; only image/scanned pages need it. Windows install:
`winget install UB-Mannheim.TesseractOCR` (admin rights; on a managed machine, ask IT to deploy).

## Files
- `../../scripts/extract.py` *(shared)* — `extract_fields`, `fields_to_table`, `list_tables`,
  `get_table`, `render_fields_report`; reuses `dataclean` + `ingest`; `--self-test`.
- `../../scripts/dataclean.py` *(shared)* — the engine + **`emit_runner`** (reuse runners/cards).
- `../../scripts/ingest.py` *(shared)* — source adapters incl. `read_text` + local-OCR.
- `references/extraction-guide.md` — field-list spec, table selection, extract-vs-tidy, reuse.
- `examples/sample_subscription_confirmation.pdf` — a synthetic form to try `extract_fields`.

## Data handling
Runs **fully local**; your data never leaves the machine. The documents are often sensitive
or confidential (subscription confirmations, statements, certificates name parties and
amounts). Process locally; **never send a document, its text, or OCR of it to an external or
third-party tool**; the extracted `.xlsx` stays in your synced or shared file store. Full
rule: `../../DATA-HANDLING.md`. (No external connector — files are local paths in your synced
or shared file store.)

## Feedback
Have an improvement or found a bug in this skill? Capture it with the toolkit's
**shared feedback format** — `../../FEEDBACK.md` — so it reaches the skill author
consistently (skill name, what you did, expected vs actual, severity, suggestion).
Save it as a `.txt` file (`feedback_[skill]_[date].txt`) and hand it to the
user to file (e.g. in your synced or shared file store) — manual, no fixed destination; fix in scope if asked.

## Requirements & mode
Pre-screen: see `../../COMPATIBILITY.md` and run `python ../../scripts/envcheck.py`. Needs
Python + `PyMuPDF` (PDF), `openpyxl` (output); `pdfplumber` (optional — preferred for messy /
borderless PDF tables), `python-docx` for `.docx`, `extract_msg` for `.msg`; **local Tesseract**
only for scanned-document OCR (degrades cleanly without it).
