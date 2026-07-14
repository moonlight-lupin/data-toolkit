# Data Toolkit

You know the file. `Q4_sales_FINAL_v3(2).xlsx` — three header rows, a "Total" row hiding in
the middle, dates in four formats, amounts in two currencies (one of them just `$`, good
luck), and a column someone typed "pending" into. Somebody needs the real numbers by 4pm.

**Data Toolkit is the fix: it turns messy business data into clean, reconciled, analysed and
presentable outputs — entirely on your own machine, nothing uploaded.** It covers the whole
grubby lifecycle a finance or ops team actually runs: pull structured data **out of
documents**, **tidy** junk exports into validated tables, **reconcile** two record sets
line-by-line, **analyse** a dataset into an insight brief, and **visualise** the result as a
branded dashboard.

Built for the people who spend their week wrestling exports into shape — accountants,
bookkeepers, finance and ops analysts, consultants, and the firms that serve them — and for
anyone who needs the numbers to be **right, reproducible, and confidential**, not just fast.

**From [Phronesis Applied](https://www.phronesis-applied.com)** — practical AI and automation
for real businesses. The open front door of the Phronesis Applied finance toolkit suite.

## Install (Claude Code plugin)

The toolkit ships as a self-installing Claude Code plugin. In an interactive Claude Code
session:

```
/plugin marketplace add moonlight-lupin/data-toolkit
/plugin install data-toolkit@data-toolkit
```

That's it — the five skills light up and trigger themselves when you describe the job
("analyse this export", "reconcile these two files"). No config, no keys.

**Letting an agent do it.** A Claude Code agent can install the toolkit for you — just ask it
to *"install the data-toolkit plugin from `moonlight-lupin/data-toolkit`"* and it will run the
non-interactive CLI equivalents:

```bash
claude plugin marketplace add moonlight-lupin/data-toolkit
claude plugin install data-toolkit@data-toolkit
```

The repo is its own marketplace (`.claude-plugin/marketplace.json`), so `owner/repo` is all
either form needs. Prefer to run the scripts directly instead? Clone the repo and skip to
[Getting started](#getting-started) — the toolkit is happily standalone.

## Try it in ~10 minutes

No Claude required. From a clone of this repo:

```bash
pip install openpyxl
python examples/run_quickstart.py
```

That writes a reconciliation working paper and a branded HTML dashboard under
`examples/out/`. Pre-built samples are also committed as
[`examples/sample-reconciliation.xlsx`](examples/sample-reconciliation.xlsx) and
[`examples/sample-dashboard.html`](examples/sample-dashboard.html) if you just want to look.
Full notes: [`examples/README.md`](examples/README.md).

## Why teams choose it

- **Fully local, fully confidential.** No network calls, no cloud upload, no credentials, no
  connectors. Shared drives (SharePoint / OneDrive / Drive) are read as synced local paths, so
  client and financial data stays on your own machine — the compliance answer is "it never
  left." See [`DATA-HANDLING.md`](DATA-HANDLING.md).
- **Numbers you can defend.** Every transform and every quoted figure is computed by a
  deterministic engine (exact `Decimal`, currency-aware, dates normalised) and logged — not
  free-typed by a model that's having a creative afternoon. Money doesn't drift, `100 USD ≠
  100 SGD`, and each run leaves an audit trail you can hand to a reviewer.
- **Drafts, not advice.** Every output is a first draft for a qualified person to sign off —
  clearly labelled as such, never dressed up as a decision or as financial/tax/investment
  advice. See [`PRINCIPLES.md`](PRINCIPLES.md).
- **White-label ready.** Phronesis Applied defaults out of the box; the dashboard layer takes
  your colours, font and logo without touching a line of code.
- **Standalone.** Needs nothing exotic to run — plain Python plus a couple of optional
  libraries for non-spreadsheet inputs. It also slots in as a clean data-prep front end for
  the rest of the Phronesis Applied suite, but depends on none of them.

## What you can do

Five skills, one arc: raw document → shareable output. Use one on its own, or chain them —
each hands the next a clean `.xlsx`.

| You need to… | Skill | You get |
|---|---|---|
| Get structured data **out of documents** (PDFs incl. multi-table & scanned, Word, Outlook `.msg`) | **data-extract** | a clean `.xlsx` + an audit report — form (label → value) and table modes, local OCR for scans |
| **Tidy** a junk-filled export, pasted table or PDF table into a validated table | **data-tidy** | a structured, validated `.xlsx` + a change/audit report — profiles the mess, proposes a transform, you confirm, it applies deterministically |
| **Reconcile** two record sets (bank vs ledger, invoice vs statement) | **data-reconcile** | a reconciliation working paper (`.xlsx`) — line-by-line match on a key or on amount + date, every unmatched item triaged; currency-aware, handles Debit/Credit splits, sign flips, ageing and GST hints; never force-fits, never posts |
| **Analyse** a dataset and find what actually matters | **data-analyse** | an insight brief — headline findings, key metrics tailored to the data type (trends, concentration, outliers, ageing), honest caveats; every number computed by the engine, the narrative only interprets |
| **Present** the numbers to a stakeholder | **data-visualise** | a self-contained, brandable HTML dashboard (KPI cards, SVG charts, RAG tables) that opens in any browser, prints to PDF, and renders as a live Artifact in Cowork / Claude.ai |

**A typical run:** a scanned remittance PDF → `data-extract` → `data-tidy` → `data-reconcile`
against the ledger → `data-analyse` for the exceptions → `data-visualise` one-pager for the
controller. Or jump in at any point with data you already have.

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

See what the current machine supports:

```
python scripts/envcheck.py
```

See [`COMPATIBILITY.md`](COMPATIBILITY.md) for the per-skill mode/environment matrix.

## Benchmark

We benchmarked the toolkit the honest way: the **same model (Claude Sonnet 5) with the toolkit
vs. with plain Python**, across all five skills plus a reconciliation scaling test, against
synthetic fixtures with planted traps and recorded ground truth. Every deliverable was scored by
independent verification, not the agents' self-reports.

- **Correctness — parity.** A well-prompted Sonnet 5 without the toolkit matched the toolkit's
  headline numbers at ordinary sizes. The value isn't "better arithmetic."
- **Quality — the skills win.** Standard reconciliation taxonomy with materiality/RAG, dual-lens
  analysis disclosure, print-ready branded dashboards: **50 / 50 vs 48.5 / 50** on the rubric.
- **The economics invert at scale.** On the same reconciliation at ~85 → ~5,000 → ~20,000
  rows/side, the deterministic engine's cost is essentially **flat**; from ~5,000 rows the skill
  arm is **~25% cheaper on tokens and ~3× faster** than hand-rolled code.
- **And so does the risk.** The baseline's error surface grew with data size — a matcher that
  began force-pairing unrelated items, a real formula bug in a delivered workbook — exactly the
  failure class a tested deterministic engine removes.

| Reconciliation, rows/side | Skill ÷ baseline tokens | Skill ÷ baseline time |
|---|---|---|
| ~85 | 0.96 | 0.62 |
| ~5,000 | **0.75** | **0.31** |
| ~20,000 | ~0.72 * | **0.38** |

\* The 20k token point excludes a process anomaly (an agent turn-stop that double-counted
context) — the raw figure is reported alongside it in the report.

Full method, per-task results, cost tables, error analysis and limitations (incl. n = 1 per
cell) — with the fixtures, ground truth, generator + verification scripts and every T1–T5
deliverable — are in **[`benchmark/`](benchmark/)** ([report](benchmark/REPORT.md)).

## Trust & quality

Two fast gates keep the toolkit honest:

```
python bin/data-lint            # descriptions, manifests & engine self-tests are clean
python tests/test_engine.py     # regression suite — standalone, no pytest needed
```

`bin/data-lint` is the authoring gate — it checks the plugin manifest and every skill
description (single-line, non-empty, within the host's length limit), guards against truncated
sections and stray tags, and runs the engine self-tests. The regression suite locks in the
highest-risk behaviours: exact `Decimal` amounts, currency comparison, the reconciliation date
window, multi-sheet selection, form-layout extraction, and PDF engine scoring. See
[`tests/README.md`](tests/README.md) for the full list. GitHub Actions runs the same lint +
suite (plus the quickstart smoke) on every push/PR to `main`.

## Contributing & security

- How to set up, run checks, and open a PR: [`CONTRIBUTING.md`](CONTRIBUTING.md)
- How to report a vulnerability: [`SECURITY.md`](SECURITY.md)
- Standing behavioural / data rules: [`PRINCIPLES.md`](PRINCIPLES.md), [`DATA-HANDLING.md`](DATA-HANDLING.md)

## License

Licensed under the [Apache License 2.0](LICENSE) — use it, fork it, build on it, commercially
or otherwise. See [`NOTICE`](NOTICE) for attribution and brand-mark notes.

---

Built and maintained by **[Phronesis Applied](https://www.phronesis-applied.com)** · Singapore ·
[hello@phronesis-applied.com](mailto:hello@phronesis-applied.com)
