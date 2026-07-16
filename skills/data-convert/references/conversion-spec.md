# The conversion spec — declarative, deterministic

A **spec** is a JSON-able dict describing how to re-express a source onto a target contract. It's
what makes convert general (any source→target) *and* auditable + reusable. It lives inside a
**conversion card** (a Markdown doc) in a fenced ` ```convert-spec ` block — the human reads the
prose + tables above it, the engine reads the block. Build it from the target contract + the
user's intent, confirm it, then `convert_file(spec, in, out)`.

```json
{
  "name": "GL export → journal import",
  "purpose": "Monthly journal upload into the accounting system.",
  "source": {
    "format": "xlsx",
    "sheet": "GL Detail",
    "expected_columns": ["Date", "Account", "Debit", "Credit", "Memo"],
    "clean_with_tidy": false,
    "tidy_recipe": null
  },
  "target": {
    "format": "csv",
    "contract": "journal_import",
    "delimiter": ",",
    "encoding": "utf-8",
    "columns": [
      { "name": "JournalDate",  "required": true },
      { "name": "AccountCode",  "required": true },
      { "name": "Amount",       "required": true },
      { "name": "Narration" }
    ]
  },
  "reshape": [],
  "map": {
    "JournalDate": { "from": "Date",             "type": "date", "format": "%Y-%m-%d" },
    "AccountCode": { "from": "Account",          "type": "text" },
    "Amount":      { "from": ["Debit","Credit"], "compute": "debit_minus_credit", "dp": 2 },
    "Narration":   { "from": "Memo",             "type": "text" }
  },
  "fx": null,
  "standing_rules": [
    "Exclude any row whose required target fields are blank from the import file."
  ],
  "rules": { "on_unmapped_source": "report", "on_missing_required": "exclude" }
}
```

## Blocks

- **source** — `format` (auto-detected from the path if omitted), `sheet` (multi-tab `.xlsx`),
  `expected_columns` (the fingerprint the sense-check diffs against). `clean_with_tidy: true` +
  a `tidy_recipe` runs `data-tidy`'s `apply_recipe` before converting; for heavier cleaning, run
  the **data-tidy** skill first and point convert at the clean output.
- **target** — `format` (`csv` / `json` / `xlsx` / `fixedwidth`), `contract` (a name, for the
  card's benefit), and `columns`: the target header **in order**, each with an optional
  `required: true` plus any **validators** (`allowed` / `pattern` / `max_len` / `check`, see
  below). CSV takes `delimiter` / `encoding`. **Fixed-width** columns add `width`, `align`
  (`l`/`r`), `pad`, and the target may set `header: true` to emit a header line. Set
  `template: "file.xlsx"` (or `.csv`) to **populate a provided template** instead of writing a
  fresh file — the template's own header/order is preserved and mapped rows are written under it.
- **map** — `target_column: {…}` (see below). The keys are the target header when there's no
  explicit `target.columns`; when both are given, `columns` drives order and required-checks.
- **reshape** — an ordered list of structure ops (see below), applied to the source **before**
  the map.
- **fx** — a pinned live value. Either a single rate `{ "pair": "USD/GBP", "rate": "0.7861",
  "as_of": "2026-07-15", "source": "<url>" }`, or a **date-keyed table** for per-row conversion
  by transaction date: `{ "pair": "USD/GBP", "rates": [ {"as_of":"2026-01-01","rate":"0.80"},
  {"as_of":"2026-06-01","rate":"0.75"} ] }` — with `compute:"fx_convert"` setting `on_date` to
  the row's date column (the latest rate whose `as_of` ≤ the row date is used). The engine
  **never fetches** — the agent fetches on the user's instruction, the user approves, and it's
  recorded here.
- **standing_rules** — a string list of user confirm-first rules to preserve across sessions.
  `render_card` always emits them as a **Standing rules** section so later agents do not have to
  rediscover policy from chat history.
- **rules** — `on_unmapped_source`: `report` (default) | `drop` | `error`;
  `on_missing_required`: `flag` (default — keep row + warn) | `exclude` (drop row from output) |
  `error` (block writing the file) | `blank` (opt out of required-emptiness checks). Required
  checks are **per row** after mapping.

## Field mappings (`map` entries)

Each target column is produced by one entry:

| Key | Meaning |
|---|---|
| `from` | source column name, or a list of names for multi-input computes |
| `const` | a literal value (instead of `from`) |
| `compute` | `as_is` (default) · `debit_minus_credit` (`from:[debit,credit]`) · `sum` (`from:[…]`) · `concat` (`from:[…]`, `sep`) · `fx_convert` (`from:col`, uses `fx`) · `lookup` (see below) |
| `type` | `text` · `number` · `currency` · `date` — coerced via the shared engine (exact `Decimal`; a bare `$` stays ambiguous) |
| `format` | for `type:"date"`, an `strftime` pattern (default `%d %b %Y`) |
| `dp` | decimal places to quantise a numeric/computed value |
| `sep` | separator for `concat` |

### `lookup` — enrich against a reference table

Translate a source value (e.g. an internal account code → the target chart-of-accounts code)
via a **second file** or an **inline map**:

```json
"AccountCode": { "from": "Account", "compute": "lookup",
                 "table": "coa_map.csv", "key": "internal", "value": "target",
                 "on_missing": "keep" }
```
- `table` (a file, resolved relative to the card) + `key`/`value` columns — **or** `map_values`
  (an inline `{source: target}` dict).
- `on_missing`: `keep` (default — the source value passes through, visible for review) · `blank`
  · `error` (halt rather than emit an untranslated code).

## Row filter (`filter` list)

Drop rows **before** reshape/map — e.g. only posted, non-zero entries. Keep a row when **all**
conditions match:

```json
"filter": [ { "col": "Status", "op": "in", "value": ["Posted"] },
            { "col": "Amount", "op": "gt", "value": "0" } ]
```
Ops: `eq` · `ne` · `in` · `not_in` · `contains` · `blank` · `nonblank` · `gt` · `ge` · `lt` ·
`le` (numeric ops parse via the shared engine). The report shows how many rows were filtered out.

## Reshape ops (`reshape` list)

| `op` | Params | Effect |
|---|---|---|
| `unpivot` | `id_cols`, `value_cols?`, `var_name`, `value_name` | wide → long |
| `pivot` | `index_cols`, `var_col`, `value_col`, `agg?` (`first`/`sum`) | long → wide |
| `flatten` | `sep?` | nested JSON records → flat table |
| `nest` | `key_cols`, `into`, `child_cols` | flat table → nested records (JSON) |
| `split` | `by` | one file → many, partitioned on a column (writes `<stem>_<key>.<ext>`) |
| `union` | (applied when converting **multiple** inputs) | many → one, aligning columns |

`unpivot` / `pivot` / `flatten` run in the `reshape` list before the map. `split` is applied at
write time (it changes the number of outputs). `union` and `nest` are used directly from the API
when composing multi-input or JSON-shaped conversions.

## Output validation (target-column validators)

Beyond `required`, a target column can carry validators; violations surface in the report
(aggregated to one issue per column/rule with a count) **before** the file is relied on:

| Key | Checks |
|---|---|
| `allowed` | value is in the given set (e.g. an ISO currency list) |
| `pattern` | value matches a regex |
| `max_len` | value length ≤ N |
| `check` | `iban` (mod-97 checksum) · `bic` (format) |

```json
{ "name": "IBAN", "required": true, "check": "iban" },
{ "name": "Currency", "required": true, "allowed": ["GBP", "USD", "EUR"] }
```

## How it's reported

- **Sense-check** (run against the card before applying): a mapped source column missing/renamed,
  a new column, an expected column gone, or a **stale pinned rate** → surfaced to the user; the
  engine does **not** auto-apply over drift.
- **Contract issues**: a required target field unmapped → `error`; a required field blank on a
  row → handled by `on_missing_required` (`flag` / `exclude` / `error`); a
  validator violation (`allowed`/`pattern`/`max_len`/`check`) → `error`; a source column the
  mapping never consumed → `info`/`error` per `on_unmapped_source` (nothing is dropped silently).

## Determinism & boundaries

- The engine is deterministic and offline: same spec + same source → same output. Live values are
  pinned constants (above), never fetched here — the agent may fetch a rate on the user's
  instruction, but only a **recorded, user-approved** value is applied.
- **Not (yet) in the engine:** unit conversion (static factors), a bounded rollup (line items →
  totals — deliberately left to `data-analyse`), multi-target fan-out, and contract inference from
  a sample. Everything else on this page — mapping, reshape, filter, lookup, validation,
  date-keyed FX, fixed-width, template population — is implemented.
