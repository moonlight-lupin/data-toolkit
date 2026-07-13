# Data Toolkit

**Firm-agnostic toolkit for turning messy business data into clean, reconciled, analysed and
presentable outputs — entirely on your own machine.** It spans the everyday data lifecycle a
finance or operations team actually runs: pull structured data **out of documents**, **clean**
junk-filled exports into validated tables, **reconcile** two record sets line-by-line,
**analyse** a dataset into an insight brief, and **visualise** the result as a branded
dashboard. Nothing is uploaded; sensitive or confidential business and financial data never
leaves your environment.

Built for the people who spend their week wrestling exports into shape — accountants,
bookkeepers, finance and ops analysts, consultants, and the firms that serve them — and for
anyone who needs the numbers to be **right, reproducible, and confidential**, not just quick.

## Why teams choose it

- **Fully local, fully confidential.** No network calls, no cloud upload, no credentials, no
  connectors. Shared drives (SharePoint / OneDrive / Drive) are read as synced local paths, so
  client and financial data stays on your own machine — the compliance answer is "it never
  left." See [`DATA-HANDLING.md`](DATA-HANDLING.md).
- **Numbers you can defend.** Every transform and every quoted figure is computed by a
  deterministic engine (exact `Decimal`, currency-aware, dates normalised) and logged — not
  free-typed by a model. Money doesn't drift, `100 USD ≠ 100 SGD`, and each run leaves an
  audit trail you can hand to a reviewer.
- **Drafts, not advice.** Every output is a first draft for a qualified person to sign off —
  clearly labelled as such, never presented as a decision or as financial/tax/investment
  advice. See [`PRINCIPLES.md`](PRINCIPLES.md).
- **White-label by design.** Neutral defaults throughout; the dashboard layer takes your
  colours, font and logo without touching code.
- **Standalone.** Needs nothing else to run — plain Python plus a couple of optional libraries
  for non-spreadsheet inputs. It also drops in as a clean data-prep front end for your other
  toolkits when you use them, but depends on none of them.

## What you can do

The five skills cover the arc from raw document to shareable output. Reach for one on its own,
or chain them — each hands the next a clean `.xlsx`.

| You need to… | Skill | You get |
|---|---|---|
| Get structured data **out of documents** (PDFs incl. multi-table & scanned, Word, Outlook `.msg`) | **data-extract** | a clean `.xlsx` + an audit report — form (label → value) and table modes, local OCR for scans |
| **Clean** a junk-filled export, pasted table or PDF table into a validated table | **data-tidy** | a structured, validated `.xlsx` + a change/audit report — profiles the mess, proposes a transform, you confirm, it applies deterministically |
| **Reconcile** two record sets (bank vs ledger, invoice vs statement) | **data-reconcile** | a reconciliation working paper (`.xlsx`) — line-by-line match on a key or on amount + date, every unmatched item triaged; currency-aware, handles Debit/Credit splits, sign flips, ageing and GST hints; never force-fits, never posts |
| **Analyse** a dataset and find what matters | **data-analyse** | an insight brief — headline findings, key metrics tailored to the data type (trends, concentration, outliers, ageing), honest caveats; every number computed by the engine, the narrative only interprets |
| **Present** the numbers to a stakeholder | **data-visualise** | a self-contained, brandable HTML dashboard (KPI cards, SVG charts, RAG tables) that opens in any browser, prints to PDF, and renders as a live Artifact in Cowork / Claude.ai |

**A typical run:** a scanned remittance PDF → `data-extract` → `data-tidy` → `data-reconcile`
against the ledger → `data-analyse` for the exceptions → `data-visualise` one-pager for the
controller. Or pick up at any point with data you already have.

## Under the hood

The data-prep skills share one local engine in **`scripts/`** — `ingest.py` (reads CSV /
multi-sheet `.xlsx` / PDF / `.docx` / `.msg` / pasted text), `dataclean.py` (deterministic
normalisation with a change log), `extract.py` (field/table location), and `envcheck.py` (an
environment prober). `data-analyse` adds a metrics engine
(`skills/data-analyse/scripts/analyse.py`); `data-visualise` renders with pure stdlib
HTML/SVG — no third-party charting library, no CDN, no remote fetches.

## Getting started

Requirements are deliberately light:

- **Python 3** + **`openpyxl`** — the one hard dependency (for `.xlsx` I/O).
- Optional, only for the inputs you actually use: **PyMuPDF** (PDF), **pdfplumber** (messy /
  borderless PDF tables), **python-docx** (`.docx`), **extract_msg** (`.msg`), and a local
  **Tesseract** for scanned-document OCR. Each degrades gracefully when absent.
- `data-visualise` needs no third-party library to render; a desktop browser is only needed to
  preview or print to PDF.

Check what the current machine supports:

```
python scripts/envcheck.py
```

See [`COMPATIBILITY.md`](COMPATIBILITY.md) for the per-skill mode/environment matrix.

## Trust & quality

A focused regression suite locks in the highest-risk behaviours — exact `Decimal` amounts,
currency comparison, the reconciliation date window, multi-sheet selection, form-layout
extraction, and PDF engine scoring. Each engine script also carries an inline self-test.

```
python tests/test_engine.py     # standalone, no pytest needed
pytest tests/                   # if pytest is installed
```

See [`tests/README.md`](tests/README.md) for the full list of covered behaviours.
