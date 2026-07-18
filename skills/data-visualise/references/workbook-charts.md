# Excel chart reference (`workbook.py`)

Chart-only Excel output for **data-visualise**. HTML stays in `viz.py`.

Implementation is **openpyxl** (already a toolkit dependency). Vocabulary follows
[AionUi](https://github.com/iOfficeAI/AionUi) / [OfficeCLI Excel charts](https://github.com/iOfficeAI/OfficeCLI/wiki/excel-chart-add)
where it maps cleanly — so agents that know OfficeCLI prop names can reuse them.
OfficeCLI itself is **not** required at runtime.

## Choose this path when

- The reader will keep working in Excel (filter, annotate, paste into a pack).
- Native Excel charts matter more than a branded printable one-pager.

Prefer `viz.py` HTML for shareable / print / artifact dashboards. The skill
orchestrator (`SKILL.md`) picks the artefact.

**Parity with HTML:** a plain table is enough — you do not need `analysis.json`. Derive
`categories` / `series` from the table (same numbers you’d put in an HTML `bar_chart` /
`line_chart`), or use `$analysis` when an analyse run already exists. See SKILL.md
“HTML / Excel parity”.

## Chart types (OfficeCLI-aligned names)

| `chart_type` | openpyxl mapping | Notes |
|---|---|---|
| `column` | `BarChart` type=col | Default for breakdowns / ageing |
| `bar` | `BarChart` type=bar | Horizontal |
| `line` | `LineChart` | Period series, rolling, compare |
| `pie` | `PieChart` | Share views; keep slice count small |
| `doughnut` | `DoughnutChart` | Same data shape as pie |
| `waterfall` | stacked column bridge | OfficeCLI-style increase/decrease/total colours |

Not implemented here (OfficeCLI-only / cx charts): funnel, treemap, sunburst,
histogram, boxWhisker, combo, pareto. Stay on the types above unless a later
optional OfficeCLI backend is added.

## Spec shape

From a **simple table** (no analyse) — same shape as an HTML bar chart’s data:

```python
# rows = [{"Region": "North", "Amount": 120}, {"Region": "South", "Amount": 80}]
categories = [r["Region"] for r in rows]
values = [r["Amount"] for r in rows]
spec = {
  "chart_type": "column",
  "title": "By region",
  "categories": categories,
  "series": [{"name": "Amount", "values": values}],
}
write_charts_xlsx("by-region.xlsx", [spec])
```

Full fields:

```python
{
  "chart_type": "column",          # or bar | line | pie | doughnut | waterfall
  "title": "By region",
  "categories": ["North", "South"],
  "series": [{"name": "Amount", "values": [120, 80]}],
  "legend": True,
  "colors": ["163F3A", "4FB3A0"],  # optional hex (with or without #)
  "anchor": "E2",
  "width": 15,
  "height": 10,
}
```

Waterfall (bridge) — steps form, same kinds as the HTML waterfall block:

```python
{
  "chart_type": "waterfall",
  "title": "Period bridge",
  "steps": [
    {"label": "Opening", "value": 100, "kind": "start"},
    {"label": "Wins", "value": 30, "kind": "delta"},
    {"label": "Losses", "value": -12, "kind": "delta"},
    {"label": "Closing", "value": 118, "kind": "total"},
  ],
  "increaseColor": "2E7D57",   # OfficeCLI alias also accepted
  "decreaseColor": "9B2226",
  "totalColor": "163F3A",
}
```

Data is always written to sheet cells; the chart references those ranges
(OfficeCLI `dataRange` style), never free-floating series without a table.

## From `analysis.json`

```python
from workbook import suggest_charts_from_analysis, charts_from_analysis
specs = suggest_charts_from_analysis(analysis)          # editable
charts_from_analysis(analysis, "insight-charts.xlsx")   # write
```

| Analyse op | Excel chart(s) |
|---|---|
| `breakdown` | column (+ pie when valued) |
| `period_series` | line + waterfall bridge |
| `ageing` / `seasonality` | column |
| `rolling` / `compare_series` | line |
| others | skipped (KPI-only → use HTML) |

## Agent plan

Infer format from `output` suffix (`.xlsx` → Excel charts, else HTML), or set
`"format": "xlsx"`.

```json
{
  "version": 1,
  "skill": "data-visualise",
  "format": "xlsx",
  "input": "out/analysis.json",
  "dashboard": {"title": "Insight charts", "blocks": "$analysis"},
  "output": "out/insight-charts.xlsx"
}
```

Explicit chart blocks:

```json
"blocks": [
  {
    "type": "chart",
    "chart_type": "column",
    "title": "By customer",
    "categories": ["Acme", "Beta"],
    "series": [{"name": "Amount", "values": [100, 60]}]
  }
]
```

## Optional: render charts to PNG (OfficeCLI)

`openpyxl` can *write* a chart but cannot *draw* one to an image. If the optional
[OfficeCLI](https://github.com/iOfficeAI/OfficeCLI) binary is on PATH, set `render_png` on the
dashboard to also emit **one PNG per chart**, cropped to that chart:

```json
{ "skill": "data-visualise", "format": "xlsx",
  "dashboard": { "title": "Regions", "render_png": true, "blocks": [ … ] },
  "output": "out/charts.xlsx" }
```

The run then returns the `.xlsx` plus a `chart_png` artefact per chart, and records the renderer
version in `details.renderer`.

**It is strictly optional.** With the binary absent the `.xlsx` is written exactly as before and
the run returns `success_with_warnings` — never an error. Nothing else in the toolkit depends on
it, and chart *generation* stays on openpyxl.

| | |
|---|---|
| Install | `brew install officecli` · `scoop install officecli` · `npm i -g @officecli/officecli` · release binary — then ensure `officecli` is on PATH (`python scripts/envcheck.py` reports it) |
| Licence | Apache-2.0, third-party |
| Network | The project documents it as fully local, with no API keys or cloud backend. That is the vendor's statement, relayed here rather than certified by this toolkit. |
| Scope | **Read-only rendering.** openpyxl writes the workbook; OfficeCLI only reads it to produce a picture — it never authors or mutates the numbers. |
| Formats | `.xlsx` renders to **PNG**. OfficeCLI's `svg` view mode is PowerPoint-only, so there is no inline-SVG path for Excel charts. |

**Implementation notes** (`scripts/officecli_render.py`): this is the toolkit's only subprocess —
invoked with an argument list, never `shell=True`, time-boxed, and a non-zero exit or timeout
degrades to "no image" rather than raising. Reading a document starts an OfficeCLI *resident* that
holds an OS file handle, so every render path closes it in a `finally`; without that the workbook
stays locked and cannot be moved, deleted or opened in Excel afterwards.
