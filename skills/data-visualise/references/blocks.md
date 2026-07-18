# Building-block cookbook

Every block is a function in `scripts/viz.py` returning an HTML string. Compose a
list of them and pass it to `dashboard(...)`. Import once:

```python
import sys; sys.path.insert(0, "scripts")   # or the path to viz.py
from viz import (kpi_card, kpi_row, bar_chart, line_chart, donut_chart,
                 heatmap, sparkline, waterfall, table, status_pill, section, grid,
                 suggest_blocks_from_analysis, blocks_from_analysis, dashboard,
                 apply_theme, rows_from_xlsx, open_in_browser)
```

## KPI cards

```python
kpi_row([
    {"label": "Open tasks", "value": 12, "status": "brand"},
    {"label": "Overdue", "value": 3, "sub": "oldest 12 days", "status": "red"},
    {"label": "Due this week", "value": 5, "status": "amber"},
    {"label": "Done (7d)", "value": 9, "status": "green"},
])
```

`value` may be a number (auto thousands-separated) or a pre-formatted string
(e.g. `"S$1.2m"`, `"98%"`). `sub` is an optional second line. `status` sets the accent.

## Bar chart

```python
bar_chart([("Mon", 4), ("Tue", 7), ("Wed", 5)], title="Tasks done by day", unit="")
# dict form also works: [{"label": "Mon", "value": 4}, ...]
```

Bars cycle the theme series colours when there are few categories; many categories all
use the primary colour. Value labels sit above each bar; hover shows a tooltip.

## Line chart

```python
# one line
line_chart([("W1", 10), ("W2", 14), ("W3", 9), ("W4", 12)], title="Weekly volume")

# several lines (gets a legend); x labels come from the first series
line_chart({"Opened": [("W1", 10), ("W2", 14), ("W3", 9), ("W4", 12)],
            "Closed": [("W1", 8),  ("W2", 11), ("W3", 13), ("W4", 10)]},
           title="Opened vs closed")
```

## Donut chart

```python
donut_chart([("Compliance", 8), ("Finance", 5), ("Marketing", 3), ("Legal", 4)],
            title="Open tasks by function")          # centre shows the total
donut_chart(data, title="Mix", centre="FY26")        # override the centre label
```

## Heat map

```python
heatmap([[12, 4], [3, 9]],
        row_labels=["North", "South"], col_labels=["Retail", "Wholesale"],
        title="Region × channel")
heatmap(corr_matrix, row_labels=cols, col_labels=cols,
        title="Correlation", scale="diverging", mid=0)
```

`scale="sequential"` (default) maps magnitude tint→primary. `diverging` centres on `mid`
(use for correlations / signed gaps).

## Sparkline

```python
sparkline([("W1", 10), ("W2", 14), ("W3", 9), ("W4", 12)], title="Volume shape")
```

A compact path for “is it rising?” — no axis ticks. Prefer `line_chart` when the scale must
be readable.

## Waterfall (bridge)

```python
waterfall([
    {"label": "Opening", "value": 100, "kind": "start"},
    {"label": "Wins", "value": 30, "kind": "delta"},
    {"label": "Losses", "value": -12, "kind": "delta"},
    {"label": "Closing", "value": 118, "kind": "total"},
], title="Pipeline bridge")
```

If `kind` is omitted: first step is `start`, last is `total`, middle steps are `delta`.

## From data-analyse (`analysis.json`)

```python
specs = suggest_blocks_from_analysis(analysis)           # editable block dicts
specs = suggest_blocks_from_analysis(analysis, ops=["breakdown", "period_series"])
html_blocks = blocks_from_analysis(analysis)             # already rendered
```

Mapping is intentional, not a dump: breakdown→bar/donut, period_series→line+sparkline+waterfall
bridge, pivot/cohort/correlation→heatmap, concentration/trend/…→KPI rows. Numbers are not
recomputed.

Agent plan shortcuts: `"blocks": "$analysis"` or `{"type": "from_analysis", "ops": ["ageing"]}`.

## Table with RAG conditional formatting

```python
rows = [{"ID": 1, "Task": "Circulate tracker", "Owner": "MH", "Days late": 12},
        {"ID": 2, "Task": "Vendor quotes", "Owner": "Jordan", "Days late": 0}]
table(rows,
      columns=["ID", "Task", "Owner", "Days late"],   # optional: select / order
      title="Outstanding tasks",
      rag={"Days late": lambda v: "red" if (v or 0) > 7 else
           ("amber" if (v or 0) > 0 else "green")})
```

`rag` maps a column name to a function `value -> status`; matching cells get a coloured
tint and left border. Columns without a rule render plain. Omit `rag` for a plain table.

## Status pill

```python
status_pill("On track", "green")   # inline RAG chip — drop into any HTML or a section
```

## Layout — sections & grids

```python
section("Throughput",
        grid(bar_chart(...), donut_chart(...), cols=2))   # two side by side

section("Detail", table(...))                              # a titled block
```

`grid(*blocks, cols=N)` lays blocks in N responsive columns; `section(title, *blocks)`
adds a heading ruled in the theme's primary colour.

## Assemble the page

```python
path = dashboard(
    "Operations dashboard",          # page title (beside the logo)
    blocks,                          # the list of fragments above
    subtitle="Weekly — team",        # optional
    as_of="14 Jun 2026",             # stamp (defaults to today, DD MMM YYYY)
    footnote="Source: task tracker", # optional extra footer line
    out_path="ops-dashboard.html")
open_in_browser(path)                # review; Ctrl-P → Save as PDF for a PDF
```

`dashboard()` with no `out_path` returns the HTML string instead of writing a file.

## Feeding from a toolkit store

```python
rows = rows_from_xlsx("tasks.xlsx")              # header+rows .xlsx -> list of dicts
# Multi-tab workbook? It won't guess: it auto-reads the single data sheet, but raises if
# several tabs hold data — pass rows_from_xlsx("book.xlsx", sheet="Q2") to choose.
open_ = [r for r in rows if str(r.get("Status", "")).lower() != "done"]
overdue = sum(1 for r in open_ if _is_overdue(r))   # compute KPIs in plain Python
# ...then build kpi_row / charts / table from open_ as above.
```

## Interactivity (optional — off by default)

Opt in per block; the engine injects a tiny vanilla-JS bundle only when used (no library,
no CDN, no JSX). The file stays self-contained and **prints cleanly** (sort order prints,
filtered-out rows stay out, controls drop under `@media print`).

```python
line_chart(series, title="Trend", toggle=True)             # click legend to show/hide a line
table(rows, title="Detail", sortable=True)                 # click a header to sort
table(rows, title="Detail", sortable=True, filter_by="City")  # + a City dropdown filter
```

Default everything off for a pure printable report. For React/app-like dashboards this
skill intentionally stops here — hand off to `anthropic-skills:web-artifacts-builder` and
carry the theme tokens + data-handling guidance across (see SKILL.md "Need a React /
app-like dashboard?").

## Theming — your own colours / logo

Both shown above use the neutral default theme. To brand the output, pass a `theme` dict
(re-skins the page shell) and/or call `apply_theme(theme)` before building blocks (also
re-skins chart colours). See `references/brand.md` for the full theming guide.

```python
my_theme = {"brand_name": "Acme Co", "logo_path": "assets/acme-logo.png",
            "colours": {"burgundy": "#0B3D91", "rose": "#1565C0"}}
apply_theme(my_theme)                                  # charts pick up the brand
dashboard("Operations dashboard", blocks, theme=my_theme, out_path="dashboard.html")
```

## Recipe — a quick weekly ops one-pager

KPI row (open / overdue / due-this-week / done) → a `grid` of bar (by day) + donut
(by function) → a trend `line_chart` (opened vs closed) → a RAG `table` of the
outstanding items. That's the shape of `examples/operations-dashboard.html`.
