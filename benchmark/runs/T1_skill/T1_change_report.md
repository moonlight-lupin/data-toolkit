# T1 — Payments export clean-up: change & audit report

**Source (unmodified):** `data-toolkit-benchmark/fixtures/t1_messy_payments.csv`
**Output:** `T1_clean_payments.xlsx`
**Purpose:** payments-received list for the finance team's receipts review.
**Tool used:** data-toolkit `data-tidy` skill (deterministic `dataclean` engine — no cell is
guessed; unparseable values are kept raw and flagged).

## Target shape (as briefed)
Ref | Payment Date (DD MMM YYYY) | Payer | Country (standardised) | Amount | Currency (ISO code)

## Recipe applied (proposed → treated as confirmed, per non-interactive session instructions)
| Source column | → Output | Type | Notes |
|---|---|---|---|
| Ref | Ref | text | trimmed |
| Payment Date | Payment Date | date | `dayfirst=True` (UK/SG convention); output `DD MMM YYYY` |
| Payer | Payer | text | trimmed, whitespace collapsed |
| Country | Country | categorical | standardised via value map (see below) |
| Amount | Amount | currency (Decimal) | code carried from the amount symbol (e.g. `£`) or, if the amount carries no symbol, from the source `Currency` column |
| *(derived)* | Currency | — | ISO code resolved as above |

- **Dedup key:** full row (Ref, Payment Date, Payer, Country, Amount, Currency) — exact
  duplicate rows removed; near-duplicates would be flagged, not merged (none found).
- **Drop rules:** blank rows and total/subtotal rows are not data — dropped before conversion.
- **Country standardisation (confirmed map)** — the engine's automatic fold-matching only
  merges punctuation/case variants (e.g. `UK`/`U.K.`); it does **not** know `United Kingdom`
  is the same country as `UK`, or `USA`/`U.S.A.` is `United States`, so those groupings were
  supplied by hand and applied as a `value_map` (every replacement logged/flagged, not silent):
  - `United Kingdom` ← `UK`, `U.K.`, `United Kingdom`
  - `United States` ← `USA`, `U.S.A.`
  - `Singapore` ← `Singapore`, `SINGAPORE`
- **£ symbol rule:** where the Amount cell carried a `£` and the source Currency cell was
  blank (`P-1008`, `P-1023`), the code was read off the `£` symbol itself → `GBP`, per the
  house rule "£ means GBP". No guessing was needed since the symbol was present.
- Two rows (`P-1006`, `P-1031`) carry `Currency = USD` in the source despite a Singapore
  payer/country — this was **not** altered; the source's stated currency was kept as-is
  (standardising currency inference is not the same as inventing a currency).

## Rows: in → out
- Raw rows in source file (incl. banner/blank/header rows before the data): 47
- Header row detected at (0-based) index 3 (`Ref, Payment Date, Payer, Country, Amount,
  Currency, Notes` — the `Notes` column was not required by the target shape and was dropped).
- Rows dropped as **not data**:
  - 1 total/subtotal row (`TOTAL,,,"48,000.00"` — a running total, not a payment)
  - 0 blank rows
- Rows removed as **exact duplicates** (2):
  - `P-1015` (15 Mar 2026, Marlowe Estates, Singapore, 2,421.50, GBP) — duplicate of the row
    immediately above it; second copy removed.
  - `P-1033` (06 Mar 2026, Bramley & Cole LLP, United Kingdom, 4,892.00, GBP) — duplicate of
    the row immediately above it; second copy removed.
- **Clean rows delivered: 40** (one row per unique `Ref`, P-1001 through P-1040).

## Cells flagged for review (40 total)
Nothing was silently changed; every conversion the engine wasn't 100% certain about is
flagged in the workbook's source log and summarised here.

| Reason | Count | Detail |
|---|---|---|
| Ambiguous DD/MM vs MM/DD date | 7 | Dates written as `DD/MM/YYYY`-or-`MM/DD/YYYY` with both parts ≤12 are genuinely ambiguous. Resolved **day-first** (UK/SG house convention) and flagged for a sanity check: `P-1001` (01/03/2026), `P-1007` (07/03/2026), `P-1010` (10/04/2026), `P-1028` (01/04/2026), `P-1031` (04/03/2026), `P-1034` (07/04/2026), `P-1037` (10/03/2026). |
| Country standardised | 32 | Every `UK`/`U.K.` → `United Kingdom`, `USA`/`U.S.A.` → `United States`, `SINGAPORE` → `Singapore` replacement is logged (32 of the 40 country cells were a non-canonical variant). |
| Amount unparseable — kept raw | 1 | `P-1012`: Amount cell contained the text `"pending"` — **not a number, kept raw and flagged**, not guessed or zeroed. |
| Amount missing (validation) | 1 | `P-1027`: Amount cell was blank — flagged as a required-field failure; **no value invented**. |

**Rows needing finance's attention before relying on the totals:** `P-1012` (amount unknown —
"pending") and `P-1027` (amount missing). Both are included in the 40 clean rows with their
Amount cell blank/raw so they aren't silently dropped from the receipts list, but they should
be chased for the real figure before the total is used.

## Sum of Amount by currency (excludes the 2 unparseable/missing-amount rows below)
| Currency | Sum | Rows |
|---|---|---|
| GBP | £115,173.00 | 36 |
| USD | $5,803.75 | 2 |
| *(unknown — flagged, excluded from both sums)* | P-1012 "pending" (currency GBP, amount unreadable); P-1027 (currency GBP, amount blank) | 2 |

36 GBP + 2 USD + 2 excluded = 40 clean rows, reconciling exactly.

## Not done / left for a qualified reviewer
- This is a **cleaned draft for review**, not a certified/reconciled ledger. The two
  flagged amount cells should be resolved against the source ledger before the total is
  reported onward.
- No FX conversion was applied — GBP and USD rows are shown separately, not combined into one
  total, since combining them would require an FX rate the source doesn't provide.
