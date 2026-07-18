---
name: data-analyse
description: >-
  Analyse a dataset and deliver the insights and key metrics that matter for it — an
  insight brief with headline findings, trends, breakdowns, concentration, outliers and
  ageing, tailored to the type of data (transactions, receivables, pipeline, survey, task
  list, any table). Use when the user says "analyse this data", "what are the key
  metrics", "any insights from this spreadsheet", "summarise this export", "what's
  driving the numbers", "who are the top customers", or hands over a table and asks what
  it says. Works INTENT-FIRST: asks what question the data should answer, profiles it,
  proposes a plan → you confirm → computes every metric deterministically (local engine,
  exact Decimal, currency-aware) → writes a calibrated brief separating observation from
  interpretation. Metrics computed locally by the engine. NOT data cleaning (data-tidy),
  NOT matching two datasets (data-reconcile), NOT a dashboard (data-visualise — natural
  next step); descriptive analysis only, never financial or investment advice.
---

# Data Analyse

Take a dataset — a clean(ish) `.xlsx`/CSV, a pasted table, or the output of another
toolkit skill — and deliver an **insight brief**: the headline findings, the key metrics
for that *type* of data, and honest caveats. The design is **intent-first** (ask what
question the data should answer before computing anything) and **compute-then-interpret**
(every quoted number comes from the deterministic local engine; the narrative interprets,
it never generates figures).

> **Self-sufficient & local engine.** All computation runs on your machine via
> `scripts/analyse.py` (+ the shared toolkit engine) — no network calls. Note the AI agent
> driving the skill does send whatever it reads into its context to your AI provider;
> "never leaves" is not claimed. See `../../DATA-HANDLING.md`.

## Workflow

### 0 — Intent (ask up front)
Before computing anything, ask (a short `AskUserQuestion`):
1. **What question should this data answer?** ("are sales growing?", "where's the risk
   in receivables?", "which segment matters?") — or is it an open "tell me what you see"?
2. **Who's it for and what decision does it feed?** — a partner one-pager reads
   differently from a working analysis.
3. **Anything known already?** — targets, prior-period figures, or a hypothesis to test.

An open-ended "just analyse it" is fine — then the playbook (step 3) drives the metric
selection, and the brief says so.

### 1 — Ingest
Same shared engine as the other skills (`../../scripts/`):
```python
import sys, pathlib
sys.path.insert(0, str(pathlib.Path("../../scripts").resolve()))
import ingest
header_rows, note = ingest.read_any(path)     # xlsx/csv/pdf/docx/msg; read_paste for pasted tables
```
> **Run from the skill directory** (`skills/data-analyse/`). The `../../scripts` path resolves
> to the toolkit-root `scripts/` where `ingest.py` and `dataclean.py` live. The analysis
> engine (`analyse.py`) is in this skill's own `scripts/` subdirectory.
Multi-tab workbooks: `read_any` raises `SheetSelectionRequired` if several tabs hold data —
list the sheets and ask, don't guess.

For files with 10k+ rows, use `ingest.read_large` instead of `read_any` to avoid OOM. See
`references/large-file-patterns.md` for vectorised operation guidance.

### 2 — Profile & quality gate
`dataclean.profile_table(header, rows)` / `score_quality(...)` — column types, missing %,
duplicates. **If the data is too messy to analyse honestly** (columns that won't parse,
heavy duplication, mixed junk), stop and route to **data-tidy** first — analysing dirty
data produces confident-looking nonsense. A little noise is fine: the engine counts every
skipped/unparseable cell and the brief must disclose those counts.

**Currency gate:** `analyse.currency_mix(col)` — if a value column carries more than one
currency code, never sum it as-is (100 USD ≠ 100 SGD). Split by currency or ask.

### 3 — Propose the analysis plan (confirm before computing)
`analyse.suggest_playbook(header, rows)` maps columns to roles (dates, amounts,
categories, ids) and suggests analyses. Combine that with the intent and the data-type
playbook (`references/playbooks.md` — transactions, receivables/ageing, pipeline,
survey/categorical, task/ops list, general ledger, inventory, spend/AP, time series,
cross-domain, generic) into a short plan:
*"I'll look at: monthly trend of Amount, breakdown by Customer with concentration,
outliers, and ageing from Due date as of 12 Jul 2026 — sound right?"* Show it; confirm.

**Two datasets provided?** If the user hands over *two* files that share a dimension
(sales vs competitor prices, actual vs budget), that's the **cross-domain** playbook —
`join_on` to relate them on the shared key (report coverage), then `compare_series` to read
position and co-movement. It **relates**, it does not match line-by-line — reconciling two
sets to find breaks is **data-reconcile**. Nail the join key and grain before computing.

### 4 — Compute (deterministic, engine only)
All metrics come from `scripts/analyse.py` — exact `Decimal`, dayfirst dates, reusing the
shared parsers:

| Function | What it computes |
|---|---|
| `numeric_summary(col)` | n, missing, skipped, total, mean, median, quartiles, min/max, negatives |
| `outliers_iqr(col)` | Tukey fences + the outlying values (exact counts) |
| `breakdown(header, rows, by, value=)` | groups sorted largest-first with shares, top-1/top-3 share, groups-to-80% |
| `period_series(header, rows, date_col, value=, grain=)` | month/quarter/year totals with gap periods **filled as zero**, deltas, % change, YoY |
| `ageing(header, rows, date_col, as_of=, value=)` | 0–30/31–60/61–90/90+ buckets (configurable); future & unparsed bucketed visibly |
| `join_on(l_header, l_rows, r_header, r_rows, on=)` | **two-dataset** join on a shared key (case/space-folded); returns the joined table + a matched/left-only/right-only coverage report |
| `compare_series(a, b, a_label=, b_label=)` | relate two ordered series (gap / ratio / % diff per key, Pearson correlation, ±1 lead/lag) — for cross-domain & actual-vs-budget |
| `concentration(values, top_n=4)` | HHI (0–10000 antitrust scale), top-N share, groups-to-80%, classification (fragmented/moderate/concentrated/highly concentrated) — for revenue/customer concentration |
| `pivot(header, rows, rows_col, cols_col, value=, aggfunc=)` | 2D cross-tab matrix (rows × columns) with sum/count/mean aggregation + row/column grand totals |
| `distribution(values)` | skewness + excess kurtosis (Fisher-Pearson, Excel-compatible) + classification (symmetric/moderately skewed/highly skewed/heavy-tailed) |
| `trend(series)` | linear regression slope + R² + direction (rising/falling/weakly/flat) on an ordered (key, value) series — descriptive, not a forecast |
| `percentile(values, q)` | arbitrary quantile(s) with linear interpolation (Excel PERCENTILE.INC-compatible); single float → `{value, n, skipped}`, list → `{q: value}` — p90/p95/p99 for VaR/latency |
| `cohort(header, rows, id_col, date_col, value=, grain=)` | retention matrix: group by first-active period, track over subsequent periods. Count mode: retention = active/size (0–1). Value mode: matrix = value sums, retention still entity-count-based, `value_matrix` separate. All rows padded rectangular. |
| `correlation_matrix(header, rows, columns)` | pairwise Pearson across N numeric columns (symmetric matrix). Row-wise alignment — only rows where BOTH cells parse are paired (junk in one column doesn't shift others). Association, not cause. |
| `rolling(series, window, func=)` | trailing-window aggregate (mean/sum/median) on an ordered series — smoothing, pairs with `period_series`. `None` values in a window are skipped. |
| `gini(values)` | Gini coefficient (0=equal, 1=concentrated) + classification — inequality of distribution, complements HHI |
| `seasonality(header, rows, date_col, value=, grain=)` | average by month-of-year (1–12) or quarter (1–4) + seasonal index. Overall average = mean of seasons WITH data (not grand/12). |
| `currency_mix(col)` / `numbers(col)` | currency codes present / parsed Decimals + skipped count |
| `fmt` / `pct` / `render_md(...)` | house-style formatting + markdown tables for the brief |
| `write_metrics_xlsx(sections, path)` | optional metrics workbook (one sheet per analysis) |

Run computations in a script (not mental arithmetic) so the analysis is reproducible;
keep the script in the working folder as the audit trail. The engine ships tested — don't
re-run its `--self-test` or `envcheck.py` as part of a normal analysis (that's setup
overhead the user pays every run); reach for them only when an import fails or the
environment is genuinely uncertain.

### 5 — Write the insight brief
ALWAYS this structure (markdown; British English, dates DD MMM YYYY, currency with code):

```
# [Dataset] — insight brief                      (as of [date], n = [rows])
## Headline            3–5 findings, most consequential first, each with its number
## Key metrics         the tables from the engine (render_md)
## Notable             outliers, concentration, anomalies — with the specific rows/values
## Caveats & quality   skipped cells, missing %, gap periods, currency notes, what this
                       data CANNOT answer
[footer: draft for review — descriptive analysis, not advice]
```

Deliver the brief as a `.md` (plus the optional metrics `.xlsx`). Keep it to one page of
reading unless asked for depth.

### 6 — Offer the next step
- **Visual one-pager wanted?** → hand the computed series/breakdowns to **data-visualise**
  (its `rows_from_xlsx` reads the metrics workbook directly).
- **Numbers look wrong vs another source?** → that's **data-reconcile**, not this skill.

## Insight discipline (what makes the brief trustworthy)

- **Every number is computed.** If a figure appears in the brief, it came out of the
  engine or is an arithmetic step shown in the brief. No free-form estimates.
- **Observation ≠ interpretation.** "March revenue fell 40% MoM" is an observation;
  "likely the contract gap" is an interpretation — label it as a possible explanation and
  say what would confirm it. Never present correlation as cause.
- **Calibrated language.** "Verified" vs "likely" vs "couldn't confirm" (PRINCIPLES.md #4).
  A trend over 3 periods is "early"; over 2 it is not a trend.
- **Disclose the denominators.** Shares, averages and trends state n and what was
  excluded (skipped cells, unparsed dates, filled gap periods).
- **Ratios and multiples are computed too.** "20× the typical ticket" is only meaningful
  with the comparator named — compute it from engine figures and say what the base is
  (median, mean, next-largest). An eyeballed multiple is a free-form estimate in disguise.
- **Never invent a conversion.** No exchange rates, deflators or per-unit factors the
  user didn't supply — a blended figure built on an assumed rate is an invented number,
  however clearly footnoted. Report per-currency (per-unit) and, if a combined view is
  wanted, ask for the rate to use.
- **Descriptive, not advisory.** The brief describes what the data shows. It never
  recommends buying/selling/pricing/provisioning — flag the decision to the qualified
  owner (drafts, not advice).

## Files

- `scripts/analyse.py` — the metric engine (see table above); reuses the shared parsers
  in `../../scripts/dataclean.py`; `python analyse.py --self-test`.
- `references/playbooks.md` — per-data-type metric menus: which analyses matter for
  transactions, receivables, pipeline, survey, ops-list, time-series and generic tables.
- `examples/sample_sales.csv` — a synthetic sales export (no real data) to demo against.

## Principles

Behavioural charter: `../../PRINCIPLES.md` — drafts not advice, never invent, honesty and
calibration, plain speech, action boundary.

## Data handling

Metrics are computed **on your machine** — the data, the metrics and the brief stay on your synced
or shared file store, and the engine uploads nothing. (The AI agent driving the skill does send
whatever it reads into its context to your AI provider.) A brief that names individuals or quotes
confidential figures is gated on any egress. Full rule: `../../DATA-HANDLING.md`.

## Feedback

Improvement or bug? Use the toolkit's shared format — `../../FEEDBACK.md` — save as
`feedback_data-analyse_[date].txt` and hand it to the user to file; fix in scope if asked.

## Requirements & mode

Portable: Python + `openpyxl` for `.xlsx` in/out; PDF/.docx/.msg inputs use the same
optional libraries as data-tidy (degrade per-source). No network, no Office, no
credentials. If an import fails or the environment is uncertain, pre-screen with
`python ../../scripts/envcheck.py` and see `../../COMPATIBILITY.md` — otherwise just
start analysing.
