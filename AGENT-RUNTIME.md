# Agent runtime

`bin/data-toolkit` is the stable machine interface for AI agents. It does not replace the six
skills or their engines; it gives them one entry point, one plan format, one approval model and
one result envelope so an agent does not have to improvise glue code.

```bash
python bin/data-toolkit inspect source.xlsx
python bin/data-toolkit validate-spec data-tidy tidy-recipe.json
python bin/data-toolkit validate plan.json
python bin/data-toolkit run plan.json --dry-run
python bin/data-toolkit run plan.json --json-report run-result.json
# operator shell only, for a concrete secondary approval request:
python bin/data-toolkit approve approval-request.json --by "Reviewer" --allow-drift
```

Every command writes JSON to stdout. `status` is one of:

- `success`
- `success_with_warnings`
- `needs_approval`
- `error`

The same envelope always contains `artifacts`, `warnings`, `errors`,
`approvals_required`, `metrics` and `details`.

`--json-report PATH` is available on every command. It writes the complete final envelope to disk
as well as stdout, including errors and approval requests, so orchestrators can retain a durable
audit record without scraping terminal text.

## Intended use and trust model

This runtime is built for **attended, human-in-the-loop** use: a person driving an AI agent
(Cowork, Claude Code and similar) who reviews and confirms what it proposes. In that setting the
agent-facing guardrails (schema validation, plan confirmation, approval receipts) work *together
with* the operator's judgement — they are not a substitute for it.

- **The approval receipts assume separated duties.** A signed secondary approval is a real control
  only when the signing key is held by an operator process **separate from the agent** — the
  intended production shape. In a single attended session where the same person is both operator
  and approver, the receipts are a convenience and an audit record, **not** a security boundary.
- **Engines are deterministic and local, but the runtime does not sandbox the filesystem.** A plan
  names its own input/output paths; the runtime resolves and reads/writes them with the process's
  privileges. Confinement to a working directory, input-size limits and network isolation are the
  **host's** responsibility, not this module's.
- **For unattended automation, don't drive it with an agent — call the engines directly.** The
  per-skill scripts (`scripts/*.py`, `skills/*/scripts/*.py`) are plain, deterministic Python; a
  real pipeline should invoke them as scripts and add its own controls (a sandbox, a path
  allow-list, size/timeout limits, least privilege). The agent runtime is the *interactive* front
  door, not a hardened automation gateway.

If a deployment needs the runtime itself to enforce a boundary — untrusted plans, or agent and
operator sharing one shell/key — treat filesystem containment and resource limits as prerequisites
to add before that use (see `SECURITY.md`).

## Declarative schemas

The six agent-facing payload families have Draft 2020-12 schemas under `schemas/`. Normal plan
validation loads and validates the relevant inline or referenced payload before source processing.
Use `validate-spec` for a faster edit/repair loop; errors include JSON pointers such as
`/operations/0` or `/columns/2/type`. `schema` prints the catalogue, and `schema data-tidy` prints
one full schema. Conversion-card Markdown is validated from its embedded `convert-spec` block.

For routine execution, agents should start with `AGENT-FAST-PATH.md` rather than loading every
long skill reference into context.

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
    "as_of": "2026-07-15"
  },
  "approval": {
    "confirmed": true,
    "confirmed_by": "user"
  },
  "approval_receipts": []
}
```

Paths in a plan are resolved relative to the plan file. This makes a plan folder portable.

### Local path trust model

This is a same-user local toolkit, not a sandbox. Absolute paths and `..` traversal are allowed
intentionally because finance workflows often span project, synced and network-mounted folders.
The runtime does not claim filesystem isolation: run the agent under an OS account/container with
only the access it should have.

## Approval behaviour

`data-tidy`, `data-extract`, `data-reconcile`, `data-analyse` and `data-convert` require
`approval.confirmed=true` before a normal run writes an artefact. A dry run may execute without
primary approval and never creates output files or directories.

Conversion drift and reconciliation aggregation are **secondary approvals**. Plan booleans or
index lists do not satisfy them. The runtime returns a concrete request containing a `request_id`
bound to the exact plan, source-file SHA-256 hashes and detected drift/proposals. A matching signed
receipt must appear in `approval_receipts`.

- Drift receipts sign `{"allow_drift": true}`. `options.allow_drift` is ignored.
- Aggregation receipts sign the exact `accepted_aggregations` list. An empty list is an explicit
  reviewed decision to reject every proposal. A legacy `accepted_aggregations` plan field may be
  retained as an assertion, but it must match the signed receipt.
- If no aggregation proposals are produced, no receipt is required; a supplied
  `accepted_aggregations` field is reported as a warning.

### Issuing a secondary approval receipt

1. Save the `needs_approval` JSON result as `approval-request.json`.
2. In an **operator-controlled shell**, expose a signing key that the agent process cannot read:

```bash
export DATA_TOOLKIT_APPROVAL_KEY_FILE="$HOME/.config/data-toolkit/operator.key"
python bin/data-toolkit approve approval-request.json --by "Jane Reviewer" --allow-drift
# or: --accept 0,2
# or: --accept none   (reviewed rejection of every aggregation proposal)
```

3. After the interactive challenge, copy `details.receipt` from the command output into the plan's
`approval_receipts` array and rerun. The runtime verifies the HMAC against
`DATA_TOOLKIT_APPROVAL_KEY` or `DATA_TOOLKIT_APPROVAL_KEY_FILE`.

The human-binding property depends on separation of duties: do not expose the signing key to the
agent. In a same-user shell where the agent can read the key or impersonate the operator TTY, no
local software-only mechanism can prove a distinct human approved the decision. Use a separate
operator account, secret-injecting orchestrator or external signer where that distinction matters.

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
`ageing`, `currency_mix`, `concentration`, `pivot`, `distribution`, `trend`, `percentile`,
`cohort`, `correlation_matrix`, `rolling`, `gini`, `seasonality`, `join_on`, `compare_series`,
and `filter_rows`.

- `concentration` / `gini`: pass `by` (+ optional `value`) to aggregate group totals first, or
  `column` when the column is already one value per group.
- `trend` / `rolling` / `seasonality`: built from `date_col` (+ optional `value` / `grain`).
  `seasonality.grain` is `month` or `quarter` only. `rolling` requires `window`.
- `join_on` and two-input `compare_series` (`left` / `right`) require exactly two plan inputs.
  Same-table `compare_series` uses `date_col` + `a_value` + `b_value`.
- Zero and net-zero totals remain zero; concentration shares are `null` where the denominator
  is not meaningful.

`filter_rows` is special: it narrows the table that **downstream operations in the same plan**
see, so a plan can chain `filter_rows` → `breakdown` on the surviving subset. Each filter spec
is `{"col": ..., "op": ..., "value"/"values"/"lo"+"hi"}` with the 12 operators documented in
`data-analyse/SKILL.md`. The filter report (`n_in` / `n_out` / `n_dropped` + per-filter removed
counts) is the analysis result for that op. Example:

```json
{"op": "filter_rows", "name": "Open items only",
 "filters": [{"col": "Status", "op": "==", "value": "Open"},
             {"col": "Amount", "op": ">", "value": 1000}]}
```

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

Supported blocks are `kpi_row`, `bar_chart`, `line_chart`, `donut_chart`, `heatmap`,
`sparkline`, `waterfall`, `table`, `section`, `grid`, `from_analysis`, and `chart`
(Excel-only). `$source` refers to rows read from the plan input. Set
`"blocks": "$analysis"` (or a `from_analysis` block) with an `analysis.json` input from
data-analyse to expand metrics into proposed drawings — the runtime does not recompute
figures.

Format: `"format": "html"` (default) or `"xlsx"`, or infer from the output suffix
(`.xlsx` / `.xlsm` → Excel chart workbook via `workbook.py`; otherwise HTML via `viz.py`).
Excel chart types use OfficeCLI-aligned names (`column`, `bar`, `line`, `pie`, `doughnut`,
`waterfall`).

Parity: a plain table input is enough for HTML (`$source` + block `data`) and for Excel
(explicit `type: "chart"` with `categories` / `series`). `$analysis` is optional on both
paths when an analyse run already exists — it is not a prerequisite for Excel.

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
