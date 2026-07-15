---
name: data-convert
description: >-
  Re-express structured data to hit a DIFFERENT target — map a source (system A's export) onto
  another system's import CONTRACT, and/or RESHAPE its structure (wide↔long, nested JSON↔flat
  table, split one file into many, union many into one). Use when the user wants to "convert this
  to X's format", "map these columns to the import template", "get this into the format System B
  needs", "reshape / pivot / unpivot this", "flatten this JSON", "split this file by column",
  "combine these files", or "prepare this for upload/import". Works INTENT-FIRST: proposes the
  target shape from the contract + purpose, you confirm, it applies deterministically and writes
  a reusable **conversion card** (Markdown + an embedded JSON spec) a future agent re-runs after
  sense-checking the source. Delegates cleaning to data-tidy; never invents values; live inputs
  (FX) are pinned/user-approved, not fetched. NOT data cleaning (data-tidy), NOT matching two
  record sets (data-reconcile), NOT raw file-format-only conversion.
---

# Data Convert

Take a **clean-enough** source and re-express it in the **structure or contract a downstream
system requires**. The interoperability counterpart to `data-tidy`: **tidy = quality** (messy →
clean, same-ish shape); **convert = interoperability** (clean → a *different* structure/contract).
If the source is messy, convert **delegates the cleaning to `data-tidy` first**, then converts the
clean result.

> **Two jobs, often combined:**
> 1. **Contract mapping** — map a source onto *another system's* import contract (columns, order,
>    types, required fields), flagging anything unmapped or required-but-missing — never invented.
> 2. **Structural reshape** — `unpivot` (wide→long), `pivot` (long→wide), `flatten`/`nest`
>    (JSON↔table), `split` (one file→many by a key), `union` (many→one with column alignment).

## Workflow

```python
import sys; sys.path.insert(0, "scripts")
from convert import (load_spec, render_card, convert_file, convert_rows,
                     sense_check, render_report)
```

### 1. Intent first — what's the target, and why?
Establish the **source**, the **target contract** (another system's import spec — its columns,
order, required fields, formats) and the **purpose**. Once you understand the purpose you can
**propose the target shape** and the mapping; the user confirms. If you don't have the target
contract, ask for a sample of the destination format or the field list.

### 2. Card-first — reuse before you rebuild
**Always check whether a conversion card already exists** for this source→target (e.g. a
`convert_[name].md` in the working folder). If one does, **do not blind-run it**:
1. Load it (`load_spec`) and read its **Mapping** + **Expected source**.
2. **Sense-check today's source against it** (`sense_check(spec, header, rows)` /
   `convert.py <src> --card card.md --check-only`).
3. **Flag any discrepancy to the user** — a mapped column missing/renamed, a new column, a
   required field now empty, or a **stale pinned rate** — and let them decide: proceed / adjust /
   regenerate. Never apply over drift silently.

### 3. Apply (deterministic)
```python
spec = load_spec("convert_gl_to_journal.md")          # or a dict you just built + confirmed
report = convert_file(spec, "gl_export.xlsx", "journal_import.csv")
print(render_report(report, name=spec["name"]))
```
Or one-shot from the CLI:
`python scripts/convert.py gl_export.xlsx --card convert_gl_to_journal.md -o journal_import.csv`

The engine reads the source (any format via the shared `ingest`), runs any reshape ops, maps to
the target contract, and writes the target format (`csv` / `json` / `xlsx`). It reports rows
in/out, the **sense-check**, unmapped source columns and required-but-missing target fields.

### 4. Save the reusable card
```python
open("convert_gl_to_journal.md", "w", encoding="utf-8").write(render_card(spec))
```
The **card** is the reusable artefact — a Markdown doc a person can read (purpose, target
contract, a Source→Target mapping table, the *Expected source* to verify) **with an embedded
` ```convert-spec ` JSON block that is the machine source of truth.** No per-conversion `.py`
runner: next month an agent reads the card, sense-checks the new export, and re-runs this engine.

## Live inputs (FX and the like) — pinned, never fetched
The **engine never reaches the network** — reproducibility and the data-handling rule both depend
on that. When a conversion needs a live value (e.g. a USD→GBP rate):
- the **agent** may fetch it (web search, on the user's instruction) and **show it**; the **user
  decides** whether to apply it (confirm-first);
- the value is **pinned into the card** (`fx: {pair, rate, as_of, source}`) and applied by the
  engine as a **recorded constant**, so a re-run is deterministic and auditable;
- refreshing is a deliberate act — the sense-check flags a pinned rate that's old for the run.

Fetching a public rate is a public lookup, not egress of the user's data — the dataset never
leaves. Never send the actual rows to an external service to "convert" them.

## Which skill? (avoid overlap)
- **Messy source** (junk rows, mixed dates, dedupe, flagging) → **data-tidy** first, then convert.
- **Matching two record sets** to find breaks → **data-reconcile**, not convert.
- **Insights / metrics** → **data-analyse**. Convert reshapes; it does not aggregate for insight
  (a bounded rollup is a future addition, deliberately out of v1).

## The spec / card format
A declarative spec (`source`, `target` contract, `map`, optional `filter`, `reshape`, `fx`,
`rules`, `expected_columns`). Beyond the core mapping + reshape it also supports: a **row
filter**, a **`lookup`** compute (enrich against a reference table / inline map), **output
validation** on target columns (`allowed` / `pattern` / `max_len` / `check: iban|bic`),
**date-keyed FX** (per-row rate by transaction date), and **fixed-width** / **template** output.
Full schema, every reshape op and compute function: see `references/conversion-spec.md`.
Ready-made example contracts: `references/contracts/journal-import.md`,
`references/contracts/payments-upload.md`.

## Safety
- **Deterministic & human-in-the-loop** — the engine applies a confirmed spec; it never invents a
  value. Output is a **draft for review**, not a posting or an upload — a person submits it.
- **Never blind-applies** — a drifted source is flagged, not force-converted.

## Data handling
The engine runs **on your machine** and makes no network calls; cleaning delegates to `data-tidy`
locally. As with any AI-assisted work, the agent driving the skill sends whatever it reads into
its context to your AI provider — see `../../DATA-HANDLING.md`. Keep sources and outputs on your
synced or shared file store; a target file carrying personal or confidential data is gated — only
share it with the entitled recipient.

## Feedback
Have an improvement or found a bug? Capture it with the toolkit's shared feedback format
(`../../FEEDBACK.md`) and hand it to the user to file; fix in scope if asked.

## Requirements & mode
Pre-screen: `../../COMPATIBILITY.md` + `python ../../scripts/envcheck.py`. Python + `openpyxl`
(for `.xlsx` in/out); reads CSV/PDF/.docx/.msg via the shared engine (same optional deps as
`data-tidy`). Portable — the code needs no network, MS Office, credentials or connector.
