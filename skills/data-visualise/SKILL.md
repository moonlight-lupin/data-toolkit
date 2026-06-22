---
name: data-visualise
description: >-
  Turn data into a brandable, self-contained HTML dashboard / visualisation that opens
  in a browser and prints cleanly to PDF. Use when the user says "build a dashboard",
  "visualise this", "make a chart / KPI cards / scorecard", "a one-pager of these
  numbers", "turn this spreadsheet into a dashboard", "RAG status board", or wants a
  shareable visual summary of tasks, compliance, pipeline, finance or any tabular data.
  Composes KPI cards, bar / line / donut charts (inline SVG — no JavaScript, no CDN, no
  remote images), tables with RAG conditional formatting, status pills, sections and
  grids into a single HTML file. Ships with a clean, neutral default theme and is fully
  brandable (colours, font, logo). Output is an internal draft for review, not advice;
  nothing is auto-distributed. NOT for PowerPoint decks or letters; for cleaning /
  extracting the underlying data first, see data-tidy / data-extract.
---

# Data Visualise

Build a **self-contained HTML dashboard** from tabular data — KPI cards, charts, RAG
tables — in **one self-contained file** that opens in a browser and prints straight to PDF.

It ships with a **clean, neutral default theme** (a slate + blue palette) and is **fully
brandable**: a firm sets its own colours, font and logo without touching the code (see
`references/brand.md`).

> **Self-contained & offline by design.** Pure HTML + CSS + **inline SVG** charts —
> no JavaScript chart libraries, no CDN, no remote images. The file works with no
> network, prints reliably, travels as a single attachment, and keeps sensitive data
> off any cloud (the toolkit's data-handling rule). The only script is a one-line
> "Print / Save PDF" button (inline, no dependency).

> **Renders as a live Artifact in Cowork / Claude.ai.** Because the output is a
> *single-page, dependency-free* HTML document, it is exactly what Claude treats as a
> live HTML **Artifact** — it runs and previews in the artifact panel (interactive
> charts, hover tooltips), and can be edited, published and shared there. Hand over the
> `.html` **as the skill writes it** — no transform needed (the embedded base64 logo +
> inline SVG mean nothing to fetch, so the sandboxed artifact iframe renders it in full;
> anything CDN-loaded would be blocked). In **Claude Code** (local terminal) there is no
> artifact panel — open the file in a browser instead.

## When to use it

- A weekly **operations / task** one-pager.
- A **compliance** status board — what's due, overdue, by owner.
- A **finance / pipeline** scorecard — KPI cards + a trend line + a breakdown donut.
- Any time someone hands you numbers and wants a **shareable visual**, not a raw table.

To clean or extract the underlying data first, run **data-tidy** / **data-extract** —
their clean `.xlsx` feeds straight in via `rows_from_xlsx`. PowerPoint decks and letters
are out of scope for this skill.

## Workflow

1. **Ask intent first** (economical, like the other data skills): what's the dashboard
   *for*, who reads it, and what are the few numbers that matter? Don't render twelve
   charts when four KPI cards and one trend answer the question.
2. **Get the data** — a list of dicts, or point `rows_from_xlsx(path)` at any header+rows
   `.xlsx` (e.g. a clean table from data-tidy / data-extract). Compute the KPIs/series in
   plain Python.
3. **Compose blocks** with the engine (see Building blocks), then `dashboard(...)` to
   assemble the page. Pick an honest `as_of` stamp. To brand the output, pass a `theme`
   (and call `apply_theme(theme)` first to re-skin chart colours) — see Theming below.
4. **Render & review** — write the `.html`, `open_in_browser(path)`, eyeball it, then
   the user prints to PDF from the browser (Ctrl-P → Save as PDF) if they want a PDF.
   It's a **draft for a qualified person**; never auto-send it.

## Building blocks

All in `scripts/viz.py`; each returns an HTML fragment, `dashboard()` assembles them.

| Block | What it makes |
|---|---|
| `kpi_card(label, value, sub, status)` / `kpi_row([...])` | metric cards with a RAG accent (`brand`/`green`/`amber`/`red`/`grey`) |
| `bar_chart(data, title, unit)` | vertical bars (inline SVG); `data` = `[(label, value)]` or dicts |
| `line_chart(series, title, unit, toggle)` | one line `[(label, value)]` or many `{name: [...]}` with a legend; floated y-axis + gridlines; `toggle=True` → click legend to show/hide a series |
| `donut_chart(data, title, centre)` | donut with a centre total; themed slice colours |
| `table(rows, columns, title, rag, sortable, filter_by)` | themed table; `rag={col: value->status}` colours cells (RAG conditional formatting); `sortable=True` → click-to-sort headers; `filter_by=[col]` → a dropdown row-filter |
| `status_pill(text, status)` | a small RAG pill |
| `section(title, *blocks)` / `grid(*blocks, cols)` | titled section / N-column layout |
| `dashboard(title, blocks, subtitle, as_of, out_path, footnote, theme)` | full page: header, as-of stamp, print CSS, footer disclaimer; `theme` re-skins the shell |
| `apply_theme(theme)` | rebind the active palette/font/logo so blocks built afterwards use a firm's brand |
| `rows_from_xlsx(path, sheet)` | read a header+rows `.xlsx` → list of dicts (needs `openpyxl`); multi-tab safe — auto-reads the single data sheet, raises if several hold data (pass `sheet=`) |
| `open_in_browser(path)` | open the rendered file for review / print-to-PDF |

Minimal example:

```python
import sys; sys.path.insert(0, "scripts")
from viz import kpi_row, bar_chart, table, section, dashboard, open_in_browser

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

## Theming (neutral by default, fully brandable)

The engine ships a clean, neutral default theme — it renders out of the box with no
branding. To apply a firm's brand, pass a `theme` dict (any subset overrides the default):

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
- Output is an **internal draft for a qualified person to review** — the footer says
  so on every page. It is **not advice** and is **never auto-distributed**.
- Don't invent numbers. Visualise what you're given (or what a store holds);
  if a figure is derived, make the derivation obvious.

## Files

- `scripts/viz.py` — the engine: default theme + `apply_theme`, building blocks,
  `dashboard()`, `rows_from_xlsx`, `open_in_browser`; `python viz.py [out.html]` builds an
  offline self-test dashboard (no data, no network).
- `references/brand.md` — the theming guide: the neutral default palette/font/logo and how
  a firm sets its own brand.
- `references/blocks.md` — the building-block cookbook with worked snippets.
- `assets/logo-sample.png` — a **neutral sample logo (placeholder)**, base64-embedded into
  the header so the artefact stays self-contained. A firm **swaps it for its own** (replace
  the file or point `theme["logo_path"]` at its PNG). If absent, the header shows a text
  wordmark of the brand name.
- `examples/operations-dashboard.html` — a built sample (the self-test output).

## Data handling

This skill is **local and offline** — it embeds whatever data you pass directly into the
HTML and never calls out (no CDN/remote images), which is exactly why it suits sensitive or
confidential business/financial data. Keep the rendered `.html`/PDF on **your synced or
shared file store**. If the dashboard contains **sensitive or confidential business or
financial data** (e.g. counterparty/asset data tied to a deal, named parties with holdings,
tenant/valuation data, personal data), treat the file as gated — don't send it to any
external tool, and only share with entitled recipients. A firm-level operations/compliance
board with no such data is not gated. Full rule: `../../DATA-HANDLING.md`.

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
