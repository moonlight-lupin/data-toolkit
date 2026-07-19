# Data Toolkit

You know the file. `Q4_sales_FINAL_v3(2).xlsx` — three header rows, a "Total" row
hiding in the middle, dates in four formats, amounts in two currencies (one of them
just `$`, good luck), and a column someone typed "pending" into. Somebody needs the
real numbers by 4pm.

**Data Toolkit is the fix.** It turns messy business data into clean, reconciled,
analysed, presentable outputs — every number computed by a deterministic engine that
runs on your own machine.

Six skills. Five make one arc — **extract → tidy → reconcile → analyse → visualise** — and
**convert** re-expresses clean data in another system's format. Use one, or chain them.

Built for the people who spend their week wrestling exports into shape — accountants,
bookkeepers, finance and ops analysts, consultants, and the firms that serve them —
and for anyone who needs the numbers **right, reproducible, and confidential**, not
just fast.

> **Same task. Toolkit vs. plain Python.** On a reproducible **two-model** benchmark, a strong
> model (Claude Sonnet 5) matched the toolkit's numbers by hand at small sizes — then the toolkit
> pulled ahead on two axes: **as the data grew** (from ~5,000 rows/side, ~3× faster and flat-cost)
> and **as the model got cheaper** (on Claude Haiku 4.5 the plain-Python arm blended currencies
> into a **£1.1M** wrong total; the skill arm's currency gate held). Full write-up in
> [`benchmark/`](benchmark/).

**From [Phronesis Applied](https://www.phronesis-applied.com)** — practical AI and
automation for real businesses. The open front door of the Phronesis Applied finance
toolkit suite.

**Skip the pitch — open a sample:**
[`sample-dashboard.html`](examples/sample-dashboard.html) ·
[`sample-branded-dashboard.html`](examples/sample-branded-dashboard.html)
(Acme Co white-label) ·
[`sample-reconciliation.xlsx`](examples/sample-reconciliation.xlsx)

New here? Start with the [Install](#install-claude-code-plugin) and
[Try it in ~10 minutes](#try-it-in-10-minutes) sections below — install, quickstart, then
**theme + logo** in one sitting.

---

## Install (Claude Code plugin)

In an interactive Claude Code session:

```
/plugin marketplace add moonlight-lupin/data-toolkit
/plugin install data-toolkit@data-toolkit
```

That’s it. The six skills light up and trigger when you describe the job
("analyse this export", "reconcile these two files"). No config, no keys.

**Letting an agent do it.** Ask Claude Code to
*"install the data-toolkit plugin from `moonlight-lupin/data-toolkit`"* — it will run:

```bash
claude plugin marketplace add moonlight-lupin/data-toolkit
claude plugin install data-toolkit@data-toolkit
```

The repo is its own marketplace (`.claude-plugin/marketplace.json`), so `owner/repo`
is all either form needs. Prefer scripts over the plugin? Clone the repo and skip to
[Getting started](#getting-started) — the toolkit is happily standalone.

## Try it in ~10 minutes

No Claude required:

```bash
pip install openpyxl
python examples/run_quickstart.py          # neutral default dashboard
python examples/run_branded_dashboard.py   # same data, Acme Co theme + logo
```

That writes working papers and HTML dashboards under `examples/out/`. Full notes:
[`examples/README.md`](examples/README.md).

### Put your brand on a dashboard (theme + logo)

The toolkit ships **unbranded** (a neutral "Data Toolkit" wordmark, no logo). Your brand
is a `theme` dict — brand name, logo path, fonts, and any colour overrides. Token names
(`burgundy`, `rose`, `pink`) are historical; set `burgundy` to your primary.

Minimal pattern (both calls matter — charts + page shell):

```python
from viz import apply_theme, kpi_row, dashboard

MY_THEME = {
    "brand_name": "Acme Co",
    "logo_path": "examples/assets/acme-mark.svg",  # transparent PNG/SVG, < 1 MB, local
    "font": "'Segoe UI','Helvetica Neue',Arial,sans-serif",
    "colours": {
        "burgundy": "#0B3D91",  # primary — header rule, table heads
        "rose":     "#1565C0",  # accent 1
        "pink":     "#42A5F5",  # accent 2
    },
}

apply_theme(MY_THEME)  # chart / KPI colours
blocks = [kpi_row([{"label": "Matched", "value": 42, "status": "green"}])]
dashboard(
    "Weekly scorecard",
    blocks,
    theme=MY_THEME,  # header, CSS, footer, logo
    as_of="14 Jul 2026",
    out_path="acme-dashboard.html",
)
```

**Logo checklist:** local file only (no URL — the engine base64-embeds it so the HTML stays
offline); prefer transparent PNG (SVG/JPG/GIF also work); keep under 1 MB; with no
`logo_path` you get a text wordmark of `brand_name`. Using the toolkit does **not** grant
any right to the Phronesis Applied name or marks in your own branding — see
[`NOTICE`](NOTICE). Full palette and status keywords:
[`skills/data-visualise/references/brand.md`](skills/data-visualise/references/brand.md).

### First real job

| You have… | Say / run… |
|---|---|
| Two record sets to match | *"Reconcile these two files"* → `data-reconcile` |
| A junk export | *"Tidy this export"* → `data-tidy` |
| PDFs / Word / `.msg` | *"Extract the table from these"* → `data-extract` |
| A clean sheet + a stakeholder | *"Dashboard this for the controller, Acme brand, logo at …"* → `data-visualise` |
| A dataset to understand | *"What does this data say?"* → `data-analyse` |
| Data for another system's format | *"Convert this to X's import format"* → `data-convert` |

A common chain: extract → tidy → reconcile → analyse exceptions → visualise one-pager.

Standing rules (drafts not advice; data stays local): [`PRINCIPLES.md`](PRINCIPLES.md)
([behaviour](PRINCIPLES.md#the-principles) · [data handling / PII](PRINCIPLES.md#data-handling--pii-policy)).

## Why teams choose it

- **Local engine, no third-party services.** No network calls in the core path, no
  cloud OCR, no CDN, no connectors. One opt-in exception, stated plainly: image/chart
  extract calls a vision API *you* configure, and is the only feature that needs a key.
  Shared drives (SharePoint / OneDrive / Drive) are
  read as synced local paths, so nothing is pushed through a cloud connector. And to
  be straight about the limit: an AI agent drives these skills, so whatever it reads
  into its context goes to your AI provider — we don't claim "it never left." What we
  do claim: the processing is local, no *third party* beyond the provider you already
  chose sees your data, and because the engine does the heavy lifting the agent works
  with samples and summaries rather than streaming whole datasets through the model.
  See [`PRINCIPLES.md` — Data handling & PII](PRINCIPLES.md#data-handling--pii-policy).
- **Numbers you can defend.** Every transform and every quoted figure is computed by
  a deterministic engine (exact `Decimal`, currency-aware, dates normalised) and
  logged — not free-typed by a model having a creative afternoon. Money doesn’t
  drift, `100 USD ≠ 100 SGD`, and each run leaves an audit trail a reviewer can
  follow.
- **Flat cost when the file gets serious.** On the same reconciliation at ~85 →
  ~5,000 → ~20,000 rows/side, skill wall-clock stayed ~flat while hand-rolled Python
  got slower and riskier. Recurring / high-volume work is where the toolkit stops
  being “nice” and starts being cheaper. See [Benchmark](#benchmark).
- **Drafts, not advice.** Every output is a first draft for a qualified person to
  sign off — clearly labelled, never dressed up as a decision or as financial / tax /
  investment advice. See [`PRINCIPLES.md`](PRINCIPLES.md).
- **White-label ready.** Ships unbranded — a neutral default; pass a `theme` dict
  (brand name, colours, fonts, local logo) to re-skin HTML dashboards **and** Excel
  chart workbooks from the same palette. See
  [theme + logo](#put-your-brand-on-a-dashboard-theme--logo).
- **Agent-stable interface.** Plans validate against schemas, dry-run before write,
  confirm-first for irreversible work — `bin/data-toolkit` is the stable entry point
  (`RUNTIME.md`).
- **Standalone.** Plain Python plus optional libraries for non-spreadsheet inputs. It
  also slots in as a data-prep front end for the rest of the Phronesis Applied suite,
  but depends on none of them.

## When it shines

| Situation | What to expect |
|---|---|
| Small one-off file, strong model, careful prompt | Correctness parity — you’re buying standardised artefacts and an audit trail, not magic arithmetic |
| Recurring exports, multi-thousand-row reconciles, reviewable working papers | Cheaper, faster, flatter cost — and a smaller error surface than hand-rolled agent code |
| Large spreadsheets (10k–100k+ rows) | Streaming / Parquet path via `ingest.read_large` (optional `pandas` + `pyarrow`) so you don’t OOM the tidy/analyse step |
| Client / financial data that must not reach third-party services | Local engine by design — no cloud OCR, no connectors, no uploads (your own AI provider still sees what the agent reads; opt-in image/chart extract calls a vision API you configure) |
| Stakeholder one-pager by end of day | Brandable HTML dashboard → browser → print to PDF — **or** a native Excel chart workbook when the reader wants to keep poking at the numbers |

## What you can do

```mermaid
flowchart LR
  A[Documents / exports] --> B[extract]
  B --> C[tidy]
  C --> D[reconcile]
  D --> E[analyse]
  E --> F[HTML dashboard / Excel charts]
  C --> G[convert → other system]
```

Use one skill on its own, or chain them — each hands the next a clean `.xlsx`
(and analyse can also hand visualise a machine `analysis.json`).

| You need to… | Skill | You get |
|---|---|---|
| Get structured data **out of documents** (PDFs incl. multi-table & scanned, Word, PowerPoint `.pptx`, Outlook `.msg`, and chart/table images via vision) | **data-extract** | a clean `.xlsx` + audit report — form (label → value) and table modes, local OCR for scans; image/chart extract is opt-in (vision API) and never silently falls back to Tesseract for chart data |
| **Tidy** a junk-filled export, pasted table or PDF table into a validated table | **data-tidy** | a structured, validated `.xlsx` + change/audit report — profiles the mess, proposes a transform, you confirm, it applies deterministically; large files route through `ingest.read_large` |
| **Reconcile** two record sets (bank vs ledger, invoice vs statement) | **data-reconcile** | a reconciliation working paper (`.xlsx`) — match on a key or amount + date; every unmatched item triaged; currency-aware; Debit/Credit, sign flips, ageing, GST hints; never force-fits, never posts |
| **Analyse** a dataset and find what actually matters | **data-analyse** | an insight brief — headline findings and type-aware playbooks (sales, AR, GL, inventory, cross-domain…); engine metrics include trends, concentration (HHI), ageing, pivot, cohort retention, seasonality, correlation, and more; narrative only interprets; optional machine `analysis.json` for the next step |
| **Present** the numbers to a stakeholder | **data-visualise** | **HTML** — self-contained brandable dashboard (KPI cards, SVG charts incl. heatmap / sparkline / waterfall, RAG tables) → browser / print-to-PDF / live Artifact; **or Excel** — native chart workbook (`.xlsx`, cell-backed editable charts, same theme palette); plain table or `analysis.json` on either path; optional OfficeCLI PNGs of each chart when you want pictures too |
| **Convert** a clean dataset to another system's format, or reshape it | **data-convert** | the target file (CSV / JSON / XLSX / fixed-width, or a filled template) + a reusable conversion card — maps onto an import **contract** (flags unmapped / required-missing, validates), reshapes (long↔wide, nested JSON↔flat, split, merge), enriches via lookup; deterministic, never invents |

**A typical run:** scanned remittance PDF → `data-extract` → `data-tidy` →
`data-reconcile` against the ledger → `data-analyse` for the exceptions →
`data-visualise` HTML one-pager *and/or* Excel charts for the controller. Or jump
in mid-arc with a table you already have — visualise does not require analyse.

## Benchmark

The honest comparison: **the same model with the toolkit vs. with plain Python**,
across all six skills, a reconciliation **scaling** test, and a recurring-conversion
test — now on **two model tiers**. Synthetic fixtures, planted traps, recorded ground
truth; every deliverable scored by independent verification, not the agents’ self-reports.

**It isn’t “better arithmetic.”** On a strong model (Sonnet 5) a well-prompted baseline
matched the toolkit’s headline numbers. The value shows up on two axes — and it *compounds*:

**As the data grows → cheaper and faster.** The engine’s cost stays flat while hand-rolled
matching gets slower *and* riskier (it force-paired unrelated rows; shipped a formula bug in a
delivered workbook — the failure class a tested engine removes).

```mermaid
xychart-beta
    title "Reconcile wall-clock (skill ÷ baseline) — lower is better for the toolkit"
    x-axis ["~85 rows", "~5k rows", "~20k rows"]
    y-axis "Skill ÷ baseline time" 0 --> 1
    bar [0.62, 0.31, 0.38]
```

| Reconciliation, rows/side | Skill ÷ baseline time | What happened |
|---|---|---|
| ~85 | 0.62 | Already faster; token spend near parity |
| ~5,000 | **0.31** | ~3× faster; ~25% fewer tokens |
| ~20,000 | **0.38** | Still ~2.6× faster; skill cost stays flat |

**As the model gets cheaper → correctness.** Re-run on **Haiku 4.5** (a small, cheap model), the
plain-Python arm fell into a planted trap and headlined a blended **£1,121,085** — GBP + USD added
with no exchange rate. The skill arm’s currency gate held. The gap between arms **widens** (50 vs
**44** on Haiku, vs 50 vs 48.5 on Sonnet), while skill overhead nearly vanishes (**+14% tokens**,
vs +45%). *Haiku + skills ≈ Sonnet-quality artefacts at a fraction of the cost.*

And **recurring conversion repeats cheaply and safely** — month 2+ costs ~1 minute, and on a
drifted month the toolkit **excluded the bad row** to exact ground truth where the hand-rolled
baseline **halted the whole run**. Issues surfaced by testing were filed and fixed upstream, then
re-verified — inside the benchmark.

Both full reports (Sonnet + Haiku), per-task scores, cost tables and honest limits (**n = 1** per
cell; on a weak model *at scale* the risk shifts to correctness — see the limits) live in
**[`benchmark/`](benchmark/)**.

## Mode & environment compatibility

Some skills only run properly in the **right mode / environment** because of how they're
built. Pre-screen before running a skill so the user isn't surprised by a broken or
degraded result.

### The two modes

- **Claude Code (local)** — runs on the user's own machine. Can execute the bundled Python
  helpers, read/write the local filesystem, and (on **Windows with Microsoft Office**
  installed) use **Word/Excel via COM** where a skill wants the highest-fidelity PDF.
  **This is the toolkit's primary/intended mode.**
- **Cowork (cloud)** — runs in Anthropic's hosted sandbox. No MS Office / COM (PDF would
  fall back to **LibreOffice**, which can render slightly differently); uses its own file
  paths and **connectors (MCP)** for integrations. Fine for portable skills, but the
  Office-fidelity and local-path assumptions don't all hold.

### How to pre-screen

1. **Know the current mode** — Claude Code (local) vs Cowork.
2. **Run the prober:** `python scripts/envcheck.py` — reports OS, Python libs, MS
   Office-COM vs LibreOffice availability, and the relevant env vars, then prints a
   per-skill readiness line.
3. **Compare to the skill's row below.** If the skill is **blocked or degraded** in the
   current mode, **tell the user up front** and offer the workaround — don't just produce
   a degraded output silently.

### Capability matrix

| Skill | Hard needs | Degrades / blocks without |
|---|---|---|
| data-tidy | Python + `openpyxl` | `PyMuPDF` for PDF input, `python-docx` for .docx, `python-pptx` for .pptx (legacy `.ppt` not supported), `extract_msg` for .msg (each optional, degrade per-source); scanned-PDF OCR needs local Tesseract; large files (10k+ rows): `pyarrow` + `pandas` optional — without them `ingest.read_large` falls back to direct openpyxl read with a warning |
| data-extract | Python + `PyMuPDF`, `openpyxl` | `pdfplumber` (optional — preferred for messy PDF tables), `python-docx`, `python-pptx`, `extract_msg` (each optional); scanned-document OCR needs local Tesseract; **image/chart extraction** needs a **vision API endpoint + key** plus `Pillow` and `requests` (optional — degrades by exiting clearly, never silently falls back to Tesseract for chart data) |
| data-reconcile | Python + `openpyxl` | reads CSV/PDF/.docx/.pptx/.msg via the shared engine (same optional deps as `data-tidy`); no network/Office/connector; produces a working paper (.xlsx) — never posts; aggregation matches are confirm-first |
| data-analyse | Python + `openpyxl` | reads CSV/PDF/.docx/.pptx/.msg via the shared engine; metric engine is pure stdlib + `Decimal`; no network/Office/connector; **descriptive analysis, never advice**; large files: `pyarrow` + `pandas` optional |
| data-visualise | Python (stdlib) for HTML; `openpyxl` for Excel chart-workbook output | optional `officecli` (third-party binary on PATH) to render each xlsx chart to PNG — absent → the `.xlsx` is still written and the run warns, never fails; a desktop browser to `open_in_browser` / print-to-PDF; **CJK / Arabic / Indic / Thai / Cyrillic / Hebrew labels** get a conditional browser font-fallback stack (no fonts shipped); in Cowork/Claude.ai the output doubles as a live HTML Artifact |
| data-convert | Python + `openpyxl` | reads CSV/PDF/.docx/.pptx/.msg via the shared engine; maps onto a target import contract + reshapes; writes CSV/JSON/XLSX/fixed-width or fills a template; delegates cleaning to `data-tidy`; **live inputs (FX) are pinned/user-approved, never engine-fetched**; output is a draft for review, never an upload |

**Rule of thumb:** the whole toolkit is **portable and runs on your machine** — pure Python
plus a few optional libraries for non-spreadsheet inputs and local OCR. None of the *code*
needs the network or credentials. (The AI agent driving it does, of course, send whatever
it reads into its context to your AI provider — see [`PRINCIPLES.md` — Data handling & PII](PRINCIPLES.md#data-handling--pii-policy).) The only mode-specific wrinkle is `data-visualise`'s
preview: in a headless/Cowork session it still builds the `.html` (and it doubles as a live
Artifact there) — open it in a desktop browser to print to PDF.

### Shared stores & connectors

- **No Microsoft 365 connector is assumed.** The toolkit does not reach a shared file store
  through an M365 MCP.
- **Shared stores are reached as synced local files.** A SharePoint / OneDrive / Drive
  library that syncs into the file system is reached as an ordinary **local path**, not a
  connector. This is why the toolkit is built around local file I/O — and it keeps PII on
  the local/synced store rather than pushing it through a cloud connector. See
  [`PRINCIPLES.md` — Data handling & PII](PRINCIPLES.md#data-handling--pii-policy).

### Not auto-detectable

`envcheck.py` can see installed Python libraries and OS/Office availability, but it **can't**
see whether the current session is headless or has an artifact panel — that depends on the
mode/runtime, not the machine. Confirm that from the runtime context.

### Hooks (Claude Code only)

The bundled `hooks/` fire in **Claude Code (local)**, where `${CLAUDE_PLUGIN_ROOT}`
resolves: a PreToolUse **PII-egress reminder** on web / external-connector calls, and a
PostToolUse **SKILL.md hygiene** check. They are **fail-open and self-resolving** — in
**Cowork** they **no-op rather than block**, and they **never intercept local sandbox
tools**. So in Cowork the egress reminder does not run — [`PRINCIPLES.md` — Data handling & PII](PRINCIPLES.md#data-handling--pii-policy)
is the actual control, and it applies in **every** mode regardless of the hook.

## Under the hood

Shared local engines in **`scripts/`**:

- `ingest.py` — CSV / multi-sheet `.xlsx` / PDF / `.docx` / `.pptx` / `.msg` / paste;
  `read_large` for 10k+ row files (optional Parquet streaming)
- `dataclean.py` — deterministic normalisation + change log
- `extract.py` — field / table location
- `streaming.py` — row-count gate, Excel→Parquet chunks, dtype downcasting
- `agent_runtime.py` + `agent_schemas.py` — plan validate / dry-run / run, confirm-first
  approvals, declarative specs (`bin/data-toolkit`)
- `envcheck.py` — capability probe (incl. optional OfficeCLI)

Per-skill engines:

- **data-analyse** — `skills/data-analyse/scripts/analyse.py` (exact `Decimal` metrics)
- **data-visualise** — `viz.py` (stdlib HTML/SVG, no CDN) and `workbook.py` (native
  Excel charts via `openpyxl`); optional `officecli_render.py` for chart→PNG
- **data-extract** — `image_extract.py` for vision chart/table images when configured

Agent-facing docs: [`RUNTIME.md`](RUNTIME.md) (fast path + full runtime).

## Getting started

Requirements stay light:

- **Python 3** + **`openpyxl`** — the one hard dependency (`.xlsx` I/O, incl. Excel chart
  workbooks from visualise).
- Optional, only for the inputs / modes you use:
  - **PyMuPDF** (PDF), **pdfplumber** (messy / borderless PDF tables)
  - **python-docx**, **python-pptx**, **extract_msg**
  - local **Tesseract** for scanned-document OCR
  - **pandas** + **pyarrow** for large-file Parquet streaming
  - vision API + **Pillow** for image/chart extract
  - **[OfficeCLI](https://github.com/iOfficeAI/OfficeCLI)** on `PATH` only if you want
    optional PNG renders of Excel charts (`dashboard.render_png`) — absent → workbook
    still writes, run warns, never fails
- HTML dashboards need no third-party library to render; a browser is only for preview /
  print to PDF. CJK and other non-Latin labels get a conditional browser font fallback
  (no fonts shipped).

```
python scripts/envcheck.py
```

Per-skill mode/environment matrix: [Mode & environment compatibility](#mode--environment-compatibility).

## Trust & quality

```
python bin/data-lint                 # manifests, descriptions & engine self-tests
python tests/test_engine.py          # engine regression — standalone, no pytest needed
python tests/test_agent_runtime.py   # plan / approval / visualise / analyse runtime
python tests/test_agent_schemas.py   # declarative schema catalogue
```

`bin/data-lint` is the authoring gate. The suites lock the highest-risk behaviours:
exact `Decimal` amounts, currency comparison, reconciliation date window, multi-sheet
selection, form-layout extraction, PDF engine scoring, analyse metrics, HTML/Excel
visualise paths (incl. fail-soft OfficeCLI). See [`tests/README.md`](tests/README.md).
GitHub Actions runs lint + suite + quickstart smoke on every push/PR to `main`.

## Contributing & security

- Setup, checks, PRs: [`CONTRIBUTING.md`](CONTRIBUTING.md)
- Vulnerabilities: [`SECURITY.md`](SECURITY.md)
- Behaviour / data rules: [`PRINCIPLES.md`](PRINCIPLES.md) ([behaviour](PRINCIPLES.md#the-principles) · [data handling / PII](PRINCIPLES.md#data-handling--pii-policy))

## License

[Apache License 2.0](LICENSE) — use it, fork it, build on it, commercially or
otherwise. See [`NOTICE`](NOTICE) for attribution and brand-mark notes.

---

Built and maintained by **[Phronesis Applied](https://www.phronesis-applied.com)** ·
Singapore · [hello@phronesis-applied.com](mailto:hello@phronesis-applied.com)
