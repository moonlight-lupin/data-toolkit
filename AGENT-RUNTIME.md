# Agent runtime

`bin/data-toolkit` is the stable machine interface for AI agents. It does not replace the six
skills or their engines; it gives them one entry point, one plan format, one approval gate and
one result envelope so an agent does not have to improvise glue code.

```bash
python bin/data-toolkit inspect source.xlsx
python bin/data-toolkit validate plan.json
python bin/data-toolkit run plan.json --dry-run
python bin/data-toolkit run plan.json
```

Every command writes JSON to stdout. `status` is one of:

- `success`
- `success_with_warnings`
- `needs_approval`
- `error`

The same envelope always contains `artifacts`, `warnings`, `errors`,
`approvals_required`, `metrics` and `details`.

## Version 1 plan

```json
{
  "version": 1,
  "skill": "data-convert",
  "inputs": [
    {"path": "january.json", "json_path": "records"},
    {"path": "february.json", "json_path": "records"}
  ],
  "spec": "convert_source_to_target.md",
  "output": {"path": "out/target.csv"},
  "options": {
    "as_of": "2026-07-15",
    "allow_drift": false
  },
  "approval": {
    "confirmed": true,
    "confirmed_by": "user"
  }
}
```

Paths in a plan are resolved relative to the plan file. This makes a plan folder portable.

## Approval behaviour

`data-tidy`, `data-extract`, `data-reconcile`, `data-analyse` and `data-convert` require
`approval.confirmed=true` before a normal run writes an artefact. A dry run may execute without
approval and never writes output.

Conversion-card drift is a separate gate. When expected columns, mapped columns or pinned inputs
have drifted, the runtime returns `needs_approval`. Set `options.allow_drift=true` only after the
user has reviewed that specific drift.

Aggregation proposals in reconciliation remain confirm-first. The runtime returns them under
`approvals_required`; accepted proposal indexes are supplied as `accepted_aggregations` in a
subsequent approved run.

## Native JSON input

The runtime accepts `.json` anywhere its table reader is used:

- a list of objects;
- one object, treated as one record;
- a nested list selected with `json_path`, such as `records` or `payload.items`;
- an object with exactly one list-of-objects field, which is auto-selected and disclosed in the
  input note.

Nested values are preserved. A `data-convert` plan can then apply `flatten` deliberately rather
than losing structure during ingestion.

## Multi-source conversion

Supply two or more `inputs` to `data-convert`, plus a union operation in the conversion spec:

```json
{
  "reshape": [
    {"op": "union", "how": "outer"},
    {"op": "flatten"}
  ],
  "target": {"format": "csv"}
}
```

`outer` retains the union of columns; `inner` retains only columns shared by every source. Union
happens before linear reshape and mapping. The report records the number of sources and rows in/out.

## Skill plan shapes

### Tidy

```json
{
  "version": 1,
  "skill": "data-tidy",
  "input": "messy.xlsx",
  "recipe": "tidy-recipe.json",
  "output": "out/clean.xlsx",
  "approval": {"confirmed": true}
}
```

Writes the clean workbook and a sibling `.report.md` change report.

### Extract

Fields mode:

```json
{
  "version": 1,
  "skill": "data-extract",
  "inputs": ["confirmation-1.pdf", "confirmation-2.pdf"],
  "mode": "fields",
  "fields": [
    {"name": "Investor", "labels": ["investor", "name of investor"], "type": "text"},
    {"name": "Commitment", "labels": ["commitment"], "type": "currency", "code_target": "Currency"}
  ],
  "output": "out/confirmations.xlsx",
  "approval": {"confirmed": true}
}
```

Table mode uses one input and supplies `page`, `index`, and optionally a tidy `recipe`.

### Reconcile

```json
{
  "version": 1,
  "skill": "data-reconcile",
  "inputs": ["bank.csv", "cashbook.xlsx"],
  "options": {
    "preset": "bank_vs_ledger",
    "date_window": 5,
    "strict_currency": true,
    "material": 1000,
    "escalate": 10000
  },
  "output": "out/reconciliation.xlsx",
  "approval": {"confirmed": true}
}
```

### Analyse

```json
{
  "version": 1,
  "skill": "data-analyse",
  "input": "sales.json",
  "operations": [
    {"op": "numeric_summary", "column": "Amount"},
    {"op": "breakdown", "by": "Customer", "value": "Amount", "top": 10},
    {"op": "period_series", "date_col": "Date", "value": "Amount", "grain": "month"}
  ],
  "output": "out/analysis.json",
  "approval": {"confirmed": true}
}
```

Supported operations are `numeric_summary`, `outliers_iqr`, `breakdown`, `period_series`,
`ageing`, and `currency_mix`. Zero and net-zero totals remain zero; concentration shares are
`null` where the denominator is not meaningful.

### Visualise

```json
{
  "version": 1,
  "skill": "data-visualise",
  "input": "exceptions.xlsx",
  "dashboard": {
    "title": "Reconciliation status",
    "as_of": "15 Jul 2026",
    "blocks": [
      {"type": "kpi_row", "items": [{"label": "Open", "value": 12, "status": "amber"}]},
      {"type": "table", "title": "Exceptions", "rows": "$source", "sortable": true}
    ]
  },
  "output": "out/dashboard.html"
}
```

Supported blocks are `kpi_row`, `bar_chart`, `line_chart`, `donut_chart`, `table`, `section`
and `grid`. `$source` refers to rows read from the plan input.

### Convert

The conversion plan may use an inline spec, a JSON spec, or a Markdown conversion card. It supports
single or multiple sources, JSON input, union, flatten, nest, split, mapping, lookups, validation,
templates and the existing target formats.

## Agent operating rule

Prefer this runtime when executing a confirmed plan. The skill documents still control intent,
plan design, interpretation, data handling and hand-off. The runtime controls mechanical execution
and reporting.

Do not convert an unresolved `needs_approval` result into success in prose. Show the user the
approval request and wait for the corresponding decision.
