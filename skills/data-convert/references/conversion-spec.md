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
  "rules": { "on_unmapped_source": "report", "on_missing_required": "error" }
}
```

## Blocks

- **source** — `format` (auto-detected from the path if omitted), `sheet` (multi-tab `.xlsx`),
  `expected_columns` (the fingerprint the sense-check diffs against). `clean_with_tidy: true` +
  a `tidy_recipe` runs `data-tidy`'s `apply_recipe` before converting; for heavier cleaning, run
  the **data-tidy** skill first and point convert at the clean output.
- **target** — `format` (`csv` / `json` / `xlsx`), `contract` (a name, for the card's benefit),
  and `columns`: the target header **in order**, each with an optional `required: true`. CSV
  takes `delimiter` / `encoding`.
- **map** — `target_column: {…}` (see below). The keys are the target header when there's no
  explicit `target.columns`; when both are given, `columns` drives order and required-checks.
- **reshape** — an ordered list of structure ops (see below), applied to the source **before**
  the map.
- **fx** — a pinned live value: `{ "pair": "USD/GBP", "rate": "0.7861", "as_of": "2026-07-15",
  "source": "<url>" }`. Applied by `compute: "fx_convert"`. The engine **never fetches** — the
  agent fetches on the user's instruction, the user approves, and it's recorded here.
- **rules** — `on_unmapped_source`: `report` (default) | `drop` | `error`;
  `on_missing_required`: `error` (default) | `blank` | `flag`.

## Field mappings (`map` entries)

Each target column is produced by one entry:

| Key | Meaning |
|---|---|
| `from` | source column name, or a list of names for multi-input computes |
| `const` | a literal value (instead of `from`) |
| `compute` | `as_is` (default) · `debit_minus_credit` (`from:[debit,credit]`) · `sum` (`from:[…]`) · `concat` (`from:[…]`, `sep`) · `fx_convert` (`from:col`, uses `fx.rate`) |
| `type` | `text` · `number` · `currency` · `date` — coerced via the shared engine (exact `Decimal`; a bare `$` stays ambiguous) |
| `format` | for `type:"date"`, an `strftime` pattern (default `%d %b %Y`) |
| `dp` | decimal places to quantise a numeric/computed value |
| `sep` | separator for `concat` |

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

## How it's reported

- **Sense-check** (run against the card before applying): a mapped source column missing/renamed,
  a new column, an expected column gone, or a **stale pinned rate** → surfaced to the user; the
  engine does **not** auto-apply over drift.
- **Contract issues**: a required target field unmapped or empty on every row → `error`; a source
  column the mapping never consumed → `info`/`error` per `on_unmapped_source` (nothing is dropped
  silently).

## Determinism & boundaries

- The engine is deterministic and offline: same spec + same source → same output. Live values are
  pinned constants (above), never fetched here.
- **Currency FX** needs a rate — supported only as a pinned, user-approved value. **Unit
  conversion** (static factors) and richer validation (allowed-value sets, checksums), template
  population and fixed-width output are **v2** — not in this engine yet.
