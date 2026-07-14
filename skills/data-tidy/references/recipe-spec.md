# The recipe — declarative transform spec

A **recipe** is a JSON-able dict mapping a messy source to the declared target output. It's
what makes the skill general (any source) *and* auditable + reusable (save it, re-run it on
the same recurring source). Build it from the profile + the user's intent, confirm it, then
`apply_recipe(raw_rows, recipe, masters=...)`.

```json
{
  "header_row": 4,
  "drop": { "blank": true, "totals": true },
  "columns": [
    { "source": "Inv. Name", "target": "Investor",       "type": "text" },
    { "source": "Commit",    "target": "Commitment (£)", "type": "currency", "currency": "GBP" },
    { "source": "Close",     "target": "Close date",     "type": "date", "dayfirst": true },
    { "source": "Status",    "target": "Status",         "type": "text" }
  ],
  "dedup_keys": ["Investor"],
  "validate": [
    { "col": "Investor", "required": true },
    { "col": "Investor", "in_master": "investors" },
    { "col": "Email",    "regex": "^[^@\\s]+@[^@\\s]+\\.[^@\\s]+$" }
  ]
}
```

## Fields
- **header_row** — 0-based index of the real header in the raw rows. Omit to auto-detect
  (`detect_header` skips title/banner/junk rows).
- **drop** — `blank` drops empty rows; `totals` drops total/subtotal rows. Both default on.
- **columns** — the output, in order. Each: `source` (source column name; loose/contains
  match, case-insensitive), `target` (output name), `type`, and options:
  - `type`: `text` (trim + collapse whitespace) · `number` (handles `1,234`, `(500)`,
    `1.2m`, `15%`) · `currency` (amount + detected code) · `date` (→ DD MMM YYYY; `dayfirst`
    default true for UK/SG) · `bool`.
    - **Amounts are parsed as `Decimal`, not float** — exact for finance (sums, reconciliation
      and currency tables don't drift by 1e-17). `write_xlsx` writes them as real numbers.
  - **Currency options** (on a `currency` column):
    - `currency`: the **expected** ISO code (e.g. `"SGD"`). A detected code that differs is
      flagged; a bare/ambiguous `$` is **resolved to this expected code**.
    - `code_target`: emit the detected currency code into its **own column** (named here),
      placed right after the amount — keep the currency for multi-market data instead of
      collapsing it into a bare number.
    - `code_source`: name a **separate source column** (e.g. a `Currency` column) to read the
      code from when the amount cell carries no symbol. The code is then resolved independently
      of the amount, so a **blank or unparseable amount** (`"pending"`) keeps its currency — the
      flag costs the row its *amount*, never its *currency* — and a symbol-less amount whose code
      comes from this column is no longer flagged "code unknown". Pair with `code_target` to emit
      the carried code.
    - A **bare `$`** is treated as **ambiguous** (could be USD/SGD/AUD/HKD…) and is *not*
      silently assumed to be USD — it is flagged unless an expected `currency` is given.
      Disambiguated dollars (`US$`, `S$`, `A$`, `HK$`, `NZ$`, `C$`) and ISO codes resolve
      directly.
  - `trim` (default true).
  - **String hygiene (opt-in, `text` type only — off by default, every change logged/flagged):**
    - `case`: `lower` | `upper` | `title` | `sentence` — normalise casing.
    - `strip_specials`: `true` removes symbols outside word chars / whitespace / common
      business punctuation (`.,;:&@/()-+%'"£$€`); or pass a regex string of chars to remove.
    - `fix_encoding`: `true` repairs common mojibake (e.g. `FranÃ§aise` → `Française`) via the
      UTF-8/Latin-1 round-trip, then applies Unicode NFC normalisation.
  - **Value standardisation (`value_map`)** — collapse inconsistent variants of the same
    category to one canonical value. Works on `text`/`categorical`/`ordinal` columns. Two
    accepted shapes: `{canonical: [variant, ...]}` (readable) or `{variant: canonical}` (flat).
    Matching is fold-insensitive (case / punctuation / accents ignored), so listing one
    representative variant catches the rest. **Propose-then-confirm:** never hand-write this
    blind — call `propose_value_map(column_values, master=…)` to get clusters, show them with
    `render_value_map_proposals(...)`, let the user accept, then bake the accepted map in with
    `value_map_from_clusters(clusters, accepted=[...])`. Every replacement is logged/flagged.
- **dedup_keys** — columns forming the identity. Exact duplicates removed; fuzzy near-dups
  (same after lowercasing/stripping punctuation) **flagged, never auto-merged**.
- **validate** — per rule: `required`, `regex`, `in_master` (name of a set passed in
  `masters={name: {...}}`), `unique`. Failures are reported, not dropped.

## How conversion is reported
- **Hard failure** (can't parse, e.g. `"soon"` as a date) → cell **kept raw** + flagged.
- **Soft warning** (parsed but check it: ambiguous `12/06/2026`, Excel serial, currency ≠
  expected) → **converted** + flagged. Nothing is silently changed or nulled.

## Semantic types in the profile (advisory)
`profile_table` also tags text-like columns as **`categorical`** (few distinct values that
repeat — low cardinality, distinct ≤ rows/2) or **`ordinal`** (values fit a known ordered
scale — Low/Med/High, XS–XL, ratings, weekdays; see `ORDINAL_SCALES` in `dataclean.py`).
Advisory only: they inform the recipe (e.g. flag columns that are candidates for value
standardisation) and never auto-coerce a value.

## Masters
Pass validation/reference lists as `masters={"investors": {"Acme Pension", ...}}` — load
from the local entity/supplier list. Matching is punctuation/case-insensitive.

## Saving & reuse — runner + card (token-saving, verify-first)
**Triage first:** a **one-off / simple** tidy-up → just deliver the result, don't create
files. Emit a bundle only when the source **recurs** or the recipe is **complex**; ask if
borderline. When it's worth it, emit a self-contained **bundle** into the user's working folder:
```python
dataclean.emit_runner("<working-folder>", "<name>", "tidy", recipe)
# -> tidy_<name>.py + .md + copies of dataclean/ingest/extract
```
- **`.py`** bakes the recipe and imports the engine from its own folder (the copies above), so
  it runs **without the plugin**: `python tidy_<name>.py <file>` re-cleans next month's
  export in one deterministic step (~no tokens), with a fresh report.
- **`.md` card** documents the expected source columns + how to verify.
- **engine copies** sit beside the runner so the folder travels as a unit; regenerating refreshes them.

**On reuse, verify before executing:** read the card → inspect the file → compare. The runner
self-checks and **warns** on missing columns *and on new columns not in the recipe* (a column
may have been added) — if drifted, update the recipe and regenerate. Reproducible for the
audit trail; keep both with the source (e.g. in your synced or shared file store).

## OCR / Tesseract setup (scanned PDFs only)
- Digital PDFs, spreadsheets and pastes need **no** Tesseract. OCR is only for image/scanned
  pages with no text layer, and runs via **local Tesseract** — never a cloud OCR (sensitive data stays local).
- Probe: `python ../../scripts/envcheck.py` reports whether Tesseract is available.
- Install (where permitted): Windows `winget install UB-Mannheim.TesseractOCR` (admin rights;
  on a managed machine, hand IT the package id to deploy centrally). PyMuPDF finds
  it via PATH + `TESSDATA_PREFIX`. English ships by default.
- OCR output is lower-fidelity (`0/O`, `1/l`, broken cells) → always flagged for review.
