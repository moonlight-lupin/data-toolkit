# Data Toolkit

A standalone, **fully-local** data-prep toolkit. It takes messy data — junk-filled
spreadsheets, PDFs, Word tables, Outlook `.msg`, pasted text — and turns it into clean,
validated, audit-ready tables, then reconciles and visualises them. Everything runs on the
machine; nothing is uploaded, and sensitive or confidential business/financial data stays
on your synced or shared file store.

White-label by design: neutral defaults throughout, and the dashboard layer is fully
brandable (colours, font, logo).

## The four skills

- **data-extract** — pull *structured* data **out of documents** (PDFs incl.
  multi-table/scanned via local OCR, Word, Outlook `.msg`) into a clean `.xlsx` + an audit
  report. Form (label → value) and table-extraction modes.
- **data-tidy** — clean *already-tabular-ish* data (junk `.xlsx`/CSV, pasted tables, PDF
  tables) into a structured, validated `.xlsx` + a change/audit report. Intent-first:
  profiles → proposes a transform recipe → you confirm → applies it deterministically.
- **data-reconcile** — reconcile any two record sets (A vs B), match line-by-line on a key
  or heuristically on amount + date (within a hard date window), and triage every unmatched
  item into a reconciliation working paper (`.xlsx`). **Currency-aware** (100 USD ≠ 100 SGD;
  optional strict mode for audit work). Handles the daily bank/GL realities: separate
  Debit/Credit columns, opposite sign conventions (`--flip-b`), statement-completeness
  balance checks, ageing of open items, and GST/net-vs-gross hints on amount mismatches.
  Never force-fits a match; never posts an adjustment.
- **data-visualise** — turn data into a self-contained, brandable **HTML dashboard** (KPI
  cards, bar/line/donut charts as inline SVG, RAG tables) that opens in a browser, prints to
  PDF, and doubles as a live HTML Artifact in Cowork / Claude.ai.

## Shared engine

The three data-prep skills share one local engine in **`scripts/`**:

- `ingest.py` — read CSV / `.xlsx` (multi-sheet aware) / PDF / `.docx` / `.msg` / pasted text
  (optional libs per source). PDF tables use the best of pdfplumber + PyMuPDF per page.
- `dataclean.py` — deterministic normalisation (dates → DD MMM YYYY; amounts as exact
  **`Decimal`**; currency amounts, with a separable code when `code_target` is configured;
  dedupe, type coercion) with a change log.
- `extract.py` — locate and pull fields/tables out of documents.
- `envcheck.py` — environment prober: reports OS, Python libraries, OCR availability, and a
  per-skill readiness line.

`data-visualise` carries its own engine (`skills/data-visualise/scripts/viz.py`) — pure
stdlib HTML/SVG, no third-party library needed to render.

## Local-first data posture

- **Fully local / offline.** No network calls, no cloud upload, no credentials. The
  toolkit is built around local file I/O; shared stores (SharePoint / OneDrive / Drive) are
  reached as **synced local paths**, not connectors.
- **Gated PII never leaves the machine.** Deal-specific and holder-specific data is
  de-identified before any external/third-party egress; a local token map allows
  re-identification. Full rule: [`DATA-HANDLING.md`](DATA-HANDLING.md).
- **Drafts, not advice.** Every output is a first draft for a qualified person to review —
  see [`PRINCIPLES.md`](PRINCIPLES.md).

## Requirements

- **Python 3** + **`openpyxl`** (the one hard dependency, for `.xlsx` I/O).
- Optional, per input type: **PyMuPDF** (PDF), **pdfplumber** (preferred for messy /
  borderless PDF tables), **python-docx** (`.docx`), **extract_msg** (`.msg`), and a local
  **Tesseract** install for scanned-document OCR. Each degrades gracefully — you only need the
  library for the inputs you actually use.
- `data-visualise` needs no third-party library to render (pure stdlib HTML/SVG); a desktop
  browser is only needed to preview / print to PDF.

Run the prober to see exactly what's available in the current environment:

```
python scripts/envcheck.py
```

See [`COMPATIBILITY.md`](COMPATIBILITY.md) for the per-skill mode/environment matrix.

## Tests

A focused regression suite locks in the highest-risk behaviours (exact Decimal amounts,
currency comparison, the date window, multi-sheet selection, form-layout extraction, PDF
engine scoring, and recent review fixes). Each engine script also has an inline self-test.

```
python tests/test_engine.py     # standalone, no pytest needed
pytest tests/                   # if pytest is installed
```

See [`tests/README.md`](tests/README.md) for the full list of covered behaviours.

## Part of the firm's toolkit suite

The Data Toolkit is a standalone product and needs nothing else to run. It also serves as a
clean data-prep front end for the firm's other toolkits when they're in use — the clean
`.xlsx` it produces feeds straight into downstream work — but it does not depend on them.
