---
name: data-visualise
description: >-
  Orchestrate visual output from tabular data or a data-analyse analysis.json into either
  (1) a brandable self-contained HTML dashboard (print/PDF / artifact) or (2) an Excel
  workbook of native charts for analysts. Use when the user says "build a dashboard",
  "visualise this", "make a chart / KPI cards / scorecard", "Excel charts", "chart this
  in a spreadsheet", "a one-pager of these numbers", "RAG status board", or wants a
  shareable visual summary. HTML path: inline SVG, no CDN. Excel path: openpyxl charts
  with OfficeCLI-aligned chartType names (column/bar/line/pie/doughnut/waterfall).
  Draft for review, not advice. NOT PowerPoint or letters; clean/extract first via
  data-tidy / data-extract; compute metrics via data-analyse when numbers must be exact.
---

# Data Visualise

This skill **orchestrates** which visual artefact to build. Two renderers, one metrics
contract (`analysis.json` or declarative specs):

| Artefact | Engine | Choose when |
|---|---|---|
| **HTML dashboard** (`.html`) | `scripts/viz.py` | Shareable one-pager, print/PDF, branded board, Cowork/Claude artifact |
| **Excel charts** (`.xlsx`) | `scripts/workbook.py` | Analysts will keep working in Excel; native charts matter |

Both are local, offline, and draft-for-review. PowerPoint and letters stay out of scope.

## HTML / Excel parity (treat them as peers)

**Neither path requires data-analyse.** A simple table (CSV / JSON / `.xlsx`) is enough for
both. What differs is only the *renderer* and how you declare the series — not whether the
job is allowed.

| Starting point | HTML | Excel |
|---|---|---|
| Plain table | `input` + block `data` / `"rows": "$source"` | `type: "chart"` with `categories` + `series` (derive from the same table in Python) |
| `analysis.json` | `"blocks": "$analysis"` / `from_analysis` | same shortcut → chart sheets |
| Both artefacts | same numbers → HTML blocks **and** Excel chart specs | |

**Do not** steer every Excel request through analyse first, and **do not** treat HTML as the
only “simple data” path. Build the category/value series once from the table, then:

- HTML → `bar_chart` / `line_chart` / `donut_chart` / `waterfall` / `table`…
- Excel → `chart_type` `column` / `line` / `pie` / `doughnut` / `waterfall`…

Rough block ↔ chart mapping (same story, different file):

| Intent | HTML block | Excel `chart_type` |
|---|---|---|
| Category comparison | `bar_chart` | `column` (or `bar`) |
| Trend over time | `line_chart` / `sparkline` | `line` |
| Share of total | `donut_chart` | `pie` / `doughnut` |
| Bridge / walk | `waterfall` | `waterfall` |
| Correlation / outliers | `scatter_chart` (`trend_line=True` for an OLS fit) | *(HTML only)* |
| Distribution shape | `histogram` (count or explicit bin edges) | *(HTML only)* |
| Composition over time | `stacked_bar` (takes `pivot()` output directly) | *(HTML only)* |
| Detail rows | `table` (`$source`) | (sheet data under the chart; no separate table block) |
| KPI strip | `kpi_row` | omit, or a one-row summary sheet later |

Use **data-analyse** when the brief needs engine-exact metrics (ageing, concentration, MoM,
currency gates) or you want one `analysis.json` to drive HTML and Excel together. For “chart
this column by that column”, skip analyse and declare the series directly on both paths.

## 0 — Pick the artefact (do this first)

Ask (briefly) who reads it and where it will live:

1. **HTML** if they want a branded board, print-to-PDF, or an in-chat artifact.
2. **Excel** if they say “charts in a spreadsheet”, will filter/annotate further, or the
   pack lives in a shared drive as `.xlsx`.
3. **Both** is fine — same table-derived series, or the same `analysis.json` via
   `suggest_blocks_from_analysis` **and** `suggest_charts_from_analysis`.

Infer from the plan when unspoken: `format: "xlsx"` or `output` ending in `.xlsx` → Excel;
otherwise HTML.

> Excel charts use **openpyxl** (toolkit hard dep). Chart prop names follow
> [OfficeCLI / AionUi](https://github.com/iOfficeAI/OfficeCLI/wiki/excel-chart-add)
> (`chartType`, `categories`, `series`, waterfall colours) — OfficeCLI is **not** required
> at runtime. See `references/workbook-charts.md`.

## When to use it

- A weekly **operations / task** one-pager (HTML).
- A **compliance** status board — what's due, overdue, by owner (HTML).
- A **finance / pipeline** scorecard — KPI cards + trend + breakdown (HTML or Excel).
- **Native Excel charts** from a simple export or an analyse run (Excel).

To clean or extract first, run **data-tidy** / **data-extract**. Optional: **data-analyse**
when metrics must be engine-exact or shared across HTML + Excel.

## Workflow

1. **Intent** — purpose, reader, and artefact (HTML vs Excel). Don't render twelve charts
   when four KPIs and one trend answer the question.
2. **Data** — plain table rows, *or* `analysis.json` when you need the analyse engine.
3. **Propose** — derive the same category/value series for either path. HTML: block list
   (or `$analysis`). Excel: `type: chart` list (or `$analysis`). Confirm.
4. **Render & review** — HTML → `dashboard(...)` / open in browser; Excel →
   `write_charts_xlsx` / `charts_from_analysis`. Draft for a qualified person; never auto-send.

## HTML path (`viz.py`)

Brandable, self-contained HTML — inline SVG, no CDN/remote images; prints to PDF. Ships
unbranded (teal / cool-paper) and is fully brandable (`references/brand.md`). Renders as a
live Artifact in Cowork / Claude.ai when handed over as written.

### Building blocks

Each returns an HTML fragment; `dashboard()` assembles them.

| Block | What it makes |
|---|---|
| `kpi_card(label, value, sub, status)` / `kpi_row([...])` | metric cards with a RAG accent (`brand`/`green`/`amber`/`red`/`grey`) |
| `bar_chart(data, title, unit)` | vertical bars (inline SVG); `data` = `[(label, value)]` or dicts |
| `line_chart(series, title, unit, toggle)` | one line `[(label, value)]` or many `{name: [...]}` with a legend; floated y-axis + gridlines; `toggle=True` → click legend to show/hide a series |
| `donut_chart(data, title, centre)` | donut with a centre total; themed slice colours |
| `heatmap(matrix, row_labels, col_labels, …)` | matrix heat map (pivot / cohort / correlation); `scale="sequential"` or `"diverging"` |
| `sparkline(data, …)` | compact trend path for KPI strips; shape over scale |
| `waterfall(steps, …)` | bridge chart (`start` / `delta` / `total`) for period or variance walks |
| `scatter_chart(x, y, …, x_label, y_label, unit_x, unit_y, trend_line=False)` | paired observations for correlation / outlier spotting; both axes float to the data. `trend_line=True` overlays an OLS fit across the observed x-range only — **descriptive, never a forecast**, and omitted entirely when x has no variance |
| `histogram(values, bins=10, …)` | distribution shape; `bins` = a count (equal-width) or explicit edges like `[0,30,60,90,365]`. Edges are `[lo,hi)` except the last, which includes its upper bound. Y-axis forced to 0; bars touch |
| `stacked_bar(data, …)` | composition per category; accepts a `pivot()` result, `{category: [v1, v2]}`, `[(category, [values])]`, `{categories, series}`, or `{segment: [(cat, value)]}`. **Negative segments stack below the zero line** so a credit never inflates the bar it reduces |
| `table(rows, columns, title, rag, sortable, filter_by)` | themed table; `rag={col: value->status}` colours cells (RAG conditional formatting); `sortable=True` → click-to-sort headers; `filter_by=[col]` → a dropdown row-filter |
| `status_pill(text, status)` | a small RAG pill |
| `section(title, *blocks)` / `grid(*blocks, cols)` | titled section / N-column layout |
| `suggest_blocks_from_analysis(analysis.json)` | map a data-analyse metrics payload → editable declarative blocks (no recomputation) |
| `blocks_from_analysis(analysis.json)` | same mapping, already rendered to HTML fragments |
| `dashboard(title, blocks, subtitle, as_of, out_path, footnote, theme)` | full page: header, as-of stamp, print CSS, footer disclaimer; `theme` re-skins the shell |
| `apply_theme(theme)` | rebind the active palette/font/logo so blocks built afterwards use a firm's brand |
| `rows_from_xlsx(path, sheet)` | read a header+rows `.xlsx` → list of dicts (needs `openpyxl`); multi-tab safe — auto-reads the single data sheet, raises if several hold data (pass `sheet=`) |
| `open_in_browser(path)` | open the rendered file for review / print-to-PDF |

Minimal example:

```python
import sys; sys.path.insert(0, "scripts")
from viz import kpi_row, bar_chart, table, section, dashboard, open_in_browser
```
> **Run from the skill directory** (`skills/data-visualise/`). The `scripts` path resolves
> to this skill's `scripts/` subdirectory where `viz.py` lives.

blocks = [
    kpi_row([{"label": "Open", "value": 12, "status": "brand"},
             {"label": "Overdue", "value": 3, "status": "red"}]),
    section("Throughput", bar_chart([("Mon", 4), ("Tue", 7), ("Wed", 5)],
                                    title="Done by day")),
    table(rows, title="Detail", rag={"Days late": lambda v: "red" if v > 7 else "green"}),
]
path = dashboard("Operations dashboard", blocks, as_of="14 Jun 2026",
                 out_path="ops-dashboard.html")
open_in_browser(path)
```

See `references/blocks.md` for the full cookbook and `references/brand.md` for the theming
guide. `examples/operations-dashboard.html` is a built sample.

### From data-analyse (HTML)

```python
from viz import suggest_blocks_from_analysis, blocks_from_analysis, dashboard
specs = suggest_blocks_from_analysis(analysis)   # declarative — show the user
path = dashboard("Insight board", blocks_from_analysis(analysis),
                 as_of="18 Jul 2026", out_path="insight.html")
```

Plan: `"blocks": "$analysis"` or `{"type": "from_analysis", "ops": [...]}` with
`analysis.json` as the input.

## Excel path (`workbook.py`)

Chart-only workbook: one sheet per chart, data in cells, embedded native Excel chart.
Vocabulary aligned with OfficeCLI (`column` / `bar` / `line` / `pie` / `doughnut` /
`waterfall`). Full prop list: `references/workbook-charts.md`.

From a **simple table** (parity with HTML — no analyse):

```python
from workbook import write_charts_xlsx
# same series you'd pass to viz.bar_chart([(lab, val), ...])
write_charts_xlsx("charts.xlsx", [
    {"chart_type": "column", "title": "By region",
     "categories": ["North", "South"],
     "series": [{"name": "Amount", "values": [120, 80]}]},
])
```

Optional — from `analysis.json`:

```python
from workbook import suggest_charts_from_analysis, charts_from_analysis
charts_from_analysis(analysis, "insight-charts.xlsx")
```

Plans (format from `format: "xlsx"` or `.xlsx` output):

```json
{
  "skill": "data-visualise",
  "format": "xlsx",
  "dashboard": {
    "title": "By region",
    "blocks": [{
      "type": "chart", "chart_type": "column", "title": "By region",
      "categories": ["North", "South"],
      "series": [{"name": "Amount", "values": [120, 80]}]
    }]
  },
  "output": "out/charts.xlsx"
}
```

Or `"input": "out/analysis.json"` with `"blocks": "$analysis"` when an analyse run exists.

## Theming (neutral default, fully brandable)

The engine ships a neutral, unbranded default out of the box. To apply a firm's brand, pass
a `theme` dict (any subset overrides the default):

```python
from viz import apply_theme, dashboard
my_theme = {"brand_name": "Acme Co",
            "logo_path": "assets/acme-logo.png",        # transparent PNG; omit → text wordmark
            "colours": {"burgundy": "#0B3D91", "rose": "#1565C0"}}  # token names are historical
apply_theme(my_theme)                                   # re-skins chart colours too
dashboard("Operations dashboard", blocks, theme=my_theme, out_path="dashboard.html")
```

`dashboard(theme=...)` re-skins the page shell (header rule, logo/wordmark, font, footer
brand line); `apply_theme(theme)` (called **before** building blocks) also re-skins the
chart colours. Full guide: `references/brand.md`.

## Interactivity (optional — still print-first)

By default a dashboard is a **static, printable** report. You can opt into light
interactivity with **plain inline JS** (no library, no CDN, no JSX) that the engine adds
only when a block asks for it — the file stays single, self-contained and offline:

- `line_chart(..., toggle=True)` — click a legend item to show/hide that series.
- `table(..., sortable=True)` — click a column header to sort (numeric-aware).
- `table(..., filter_by="City")` — a dropdown that filters rows by that column.

These **degrade cleanly for print**: the current sort order prints, filtered-out rows
stay out, and the controls/print button drop away under `@media print`. Default everything
off for a pure report. This is the deliberate ceiling — for anything heavier, see below.

## Need a React / app-like dashboard?

This skill is **HTML-only by design** (self-contained, offline, printable, and a live
HTML Artifact in Cowork). If a genuine **React/JSX** dashboard is needed — rich state,
cross-filtering, app-like behaviour — that's **out of scope here**. Hand off to the
built-in **`anthropic-skills:web-artifacts-builder`** skill, but **carry this skill's
guidance across**: the theme tokens from `references/brand.md` / `scripts/viz.py`
(`BRAND`/`FONT`), the **data-handling / PII rule** (`../../DATA-HANDLING.md` — a React
artifact runs in the cloud runtime, so gated data must be de-identified first), and the
house style (British English, DD MMM YYYY, *draft not advice*). Keep **this** skill for
the common case: a clean, branded, printable dashboard that also opens as a live artifact.

## House style & boundary

- British English; dates **DD MMM YYYY**; the `as_of` stamp should be real.
- Output is a **draft for a qualified person to review** — the footer says so on every
  page. It is **not advice** and is **never auto-distributed**.
- Don't invent numbers. Visualise what you're given (or what a store holds);
  if a figure is derived, make the derivation obvious.

## Files

- `scripts/viz.py` — HTML engine: theme, blocks, `dashboard()`, analysis→blocks handoff;
  `python viz.py [out.html]` self-test.
- `scripts/workbook.py` — Excel chart engine: OfficeCLI-aligned chart specs, analysis→charts;
  `python workbook.py [out.xlsx]` self-test.
- `references/brand.md` — HTML theming guide.
- `references/blocks.md` — HTML building-block cookbook.
- `references/workbook-charts.md` — Excel chart types, props, analysis mapping.
- `examples/operations-dashboard.html` — built HTML sample.

## Principles

Behavioural charter: `../../PRINCIPLES.md` — drafts not advice, never invent, honesty and
calibration, plain speech, action boundary.

## Data handling
The renderer is **local and offline** — it embeds whatever data you pass directly into the
HTML and never calls out (no CDN/remote images), so the dashboard file itself leaks nothing. (The
AI agent driving the skill does send whatever it reads into its context to your AI provider.) Keep the rendered `.html`/PDF on **your synced or
shared file store**. If the dashboard contains **personal data or confidential business/
financial data** (e.g. named individuals with contact details or IDs, customer/supplier
lists, pricing, unpublished financials), treat the file as gated — don't send it to any
external tool, and only share with entitled recipients. A board built purely from
non-sensitive, aggregated numbers is not gated. Full rule: `../../DATA-HANDLING.md`.

## Feedback

Have an improvement or found a bug in this skill? Capture it with the toolkit's
**shared feedback format** — `../../FEEDBACK.md` — so it reaches the skill author
consistently (skill name, what you did, expected vs actual, severity, suggestion).
Save it as a `.txt` file (`feedback_[skill]_[date].txt`) and hand it to the user to file —
manual, no fixed destination; fix in scope if asked.

## Requirements & mode

Pre-screen before running: see `../../COMPATIBILITY.md` and run
`python ../../scripts/envcheck.py`. **Highly portable** — pure Python stdlib for the HTML
itself (no third-party library needed to render). `rows_from_xlsx` needs `openpyxl` only if
you read an `.xlsx`. `open_in_browser` and print-to-PDF need a desktop browser (any OS);
in a headless/Cowork session the `.html` still builds — open it locally to print. No
network, no MS Office, no credentials.
