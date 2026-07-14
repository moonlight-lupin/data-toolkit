# T1 — Payments export clean-up: change / audit report

**Source (unmodified):** `fixtures/t1_messy_payments.csv`
**Output:** `T1_clean_payments.xlsx` (this folder)
**Purpose:** list of payments received, for finance team receipts review
**Tool used:** Data Toolkit — `data-tidy` skill (`dataclean.apply_recipe`), run locally; no data left the machine

This is a **cleaned draft for review**, not a certified dataset — please have a qualified person check the flagged cells below before relying on it.

## 1. Target shape (as briefed)
`Ref | Payment date (DD MMM YYYY) | Payer | Country (standardised) | Amount | Currency (ISO code)`

## 2. Recipe applied (proposed → treated as confirmed, per session instructions)
| Source column | → Output | Type | Notes |
|---|---|---|---|
| Ref | Ref | text | required, regex `^P-\d+$`, unique |
| Payment Date | Payment date | date, `dayfirst=True` | output `DD MMM YYYY`; ambiguous D/M readings flagged |
| Payer | Payer | text | whitespace trimmed/collapsed |
| Country | Country | categorical, value-mapped | see §4 |
| Amount | Amount | currency (`Decimal`) | `£` in the amount cell → GBP (per house rule); code also read from the `Currency` column when the amount cell has no symbol, so a "pending"/blank amount doesn't lose its currency |
| Currency | *(emitted alongside Amount, from the logic above)* | — | — |

**Row rules applied:** header auto-detected at line 4 of the raw file (lines 1–3 are an export-banner line, a blank line and a title line — not data); blank rows dropped (none found); total/subtotal rows dropped; exact-duplicate rows (identical across all six output columns) removed; unparseable values kept raw and flagged, never guessed.

**Dedup key:** all six output columns (Ref, Payment date, Payer, Country, Amount, Currency) — i.e. only *exact* duplicate rows are removed, as instructed.

## 3. Row accounting
| Stage | Rows |
|---|---|
| Raw lines in file | 47 |
| Less: banner / blank / title lines before the header, and the header line itself | −4 |
| Data rows after the header | 43 |
| Less: total/subtotal row dropped | −1 |
| Less: exact-duplicate rows removed | −2 |
| **Clean rows delivered** | **40** |

**Rows dropped, with reason:**
- **1 total/subtotal row** — `,,TOTAL,,"48,000.00",,` (sits between P-1020 and P-1021 in the source). Not a payment; dropped per rule. Observation only: its stated total (£48,000.00) does not reconcile to the combined amount of the 20 rows preceding it (P-1001–P-1020 sum to 36,489.25 across their stated currencies — workings: 33,842.25 GBP + 1,186.25 USD + 1,460.75 read off the `£`-prefixed P-1008 cell) — the row carries no Ref/date/payer of its own so there is nothing further to recover; flagged here for awareness only.
- **2 exact duplicate rows removed** (identical Ref, date, payer, country, amount, currency to a row already kept):
  - `P-1015` (Marlowe Estates, 15 Mar 2026, Singapore, 2,421.50, GBP) — second occurrence removed, first kept.
  - `P-1033` (Bramley & Cole LLP, 06 Mar 2026, UK, 4,892.00, GBP) — second occurrence removed, first kept.

## 4. Country standardisation (confirmed recipe)
The raw `Country` column had 7 distinct spellings for 3 countries. The engine's automatic fuzzy-match only merges variants that are the *same letters* under case/punctuation-folding (e.g. `UK`/`U.K.` fold to the same key) — it cannot on its own know that `UK` and `United Kingdom` name the same country, so that abbreviation mapping was supplied explicitly as the proposed recipe:

| Canonical (output) | Variants collapsed | Occurrences in the 40 delivered rows |
|---|---|---|
| United Kingdom | UK, U.K., United Kingdom | 20 |
| United States | USA, U.S.A. | 10 |
| Singapore | Singapore, SINGAPORE | 10 |

Of the 40 delivered rows, 30 had their Country cell **changed** (a `UK`/`U.K.`/`USA`/`U.S.A.`/`SINGAPORE` spelling rewritten to the canonical form) and 10 already matched the canonical spelling used elsewhere in the file, so needed no change. All 30 changed cells are listed in §6d.

## 5. Payment date parsing
Dates arrived in at least three formats: `DD/MM/YYYY`, `YYYY-MM-DD`, and `D Mon YYYY`. All were parsed with a **day-first** convention (UK/SG default, consistent with QIP's core markets) and output as `DD MMM YYYY`.

**Assumption flagged for review:** where a slash-date's two numeric parts are both ≤ 12 (e.g. `07/03/2026`), the date is genuinely ambiguous — it could be 7 Mar or 3 Jul. These were resolved as **day/month** (i.e. `07/03/2026` → 07 Mar 2026) per the day-first convention, and each such cell is individually flagged in §6c for finance to sanity-check against the payer's own record if needed. 7 of the 40 delivered rows fall into this ambiguous bucket; slash-dates where one part is >12 (e.g. `16/04/2026`) are unambiguous and not flagged.

## 6. Cells flagged for review
Hard failures are kept **raw, unconverted**; soft warnings are **converted** but flagged so a human can verify. Rows are identified by **Ref** for safe cross-checking against the source file.

Total in the 40 delivered rows: **38 flagged cells** (7 date + 30 country + 1 amount hard-failure) plus **1 validation failure** (missing Amount). Note: the engine's raw transform log (run before de-duplication) reports 32 Country flags because it also counts the two rows subsequently removed as exact duplicates (P-1015 and P-1033's second occurrences) — those two flags do not appear in the final 40-row table, hence 30 here.

### 6a. Amount — hard failure (not guessed, kept raw)
| Ref | Raw value | Currency kept | Reason |
|---|---|---|---|
| P-1012 | `pending` | GBP | Not a parseable number — kept as the literal text "pending"; do not treat as £0. |

### 6b. Amount — missing, failed required-field validation
| Ref | Issue |
|---|---|
| P-1027 | Amount cell was blank in the source. Kept blank (not guessed); Currency still shows GBP (carried through from the source `Currency` column) so the row isn't silently dropped from the finance review. |

### 6c. Payment date — ambiguous day/month, converted + flagged (7 cells)
| Ref | Raw | Output (day-first reading) |
|---|---|---|
| P-1001 | 01/03/2026 | 01 Mar 2026 |
| P-1007 | 07/03/2026 | 07 Mar 2026 |
| P-1010 | 10/04/2026 | 10 Apr 2026 |
| P-1028 | 01/04/2026 | 01 Apr 2026 |
| P-1031 | 04/03/2026 | 04 Mar 2026 |
| P-1034 | 07/04/2026 | 07 Apr 2026 |
| P-1037 | 10/03/2026 | 10 Mar 2026 |

### 6d. Country — standardised, converted + flagged (30 cells)
| Ref | Raw | → Canonical | Ref | Raw | → Canonical |
|---|---|---|---|---|---|
| P-1001 | UK | United Kingdom | P-1024 | UK | United Kingdom |
| P-1002 | U.K. | United Kingdom | P-1025 | UK | United Kingdom |
| P-1004 | USA | United States | P-1026 | U.K. | United Kingdom |
| P-1005 | U.S.A. | United States | P-1028 | USA | United States |
| P-1007 | SINGAPORE | Singapore | P-1029 | U.S.A. | United States |
| P-1008 | UK | United Kingdom | P-1031 | SINGAPORE | Singapore |
| P-1009 | UK | United Kingdom | P-1032 | UK | United Kingdom |
| P-1010 | U.K. | United Kingdom | P-1033 | UK | United Kingdom |
| P-1012 | USA | United States | P-1034 | U.K. | United Kingdom |
| P-1013 | U.S.A. | United States | P-1036 | USA | United States |
| P-1015 | SINGAPORE | Singapore | P-1037 | U.S.A. | United States |
| P-1016 | UK | United Kingdom | P-1039 | SINGAPORE | Singapore |
| P-1017 | UK | United Kingdom | P-1040 | UK | United Kingdom |
| P-1018 | U.K. | United Kingdom | | | |
| P-1020 | USA | United States | | | |
| P-1021 | U.S.A. | United States | | | |
| P-1023 | SINGAPORE | Singapore | | | |

## 7. Currency — observations (not changed, no guessing applied)
- Two rows carry a **different currency code from the same payer's other payments**, left exactly as sourced (no basis to assume it's an error): `P-1006` (Silverbirch Capital, Singapore) is tagged **USD**, where the same payer's other four payments are GBP; `P-1031` (Marlowe Estates, Singapore) is also tagged **USD**, where the same payer's other four payments are GBP. Worth a quick check with finance that these two are genuinely USD receipts and not a data-entry slip.
- `P-1008` and `P-1023` carried the amount as `£1,460.75` / `£3,519.50` with a **blank** `Currency` cell in the source; per the brief's rule ("£ means GBP") these were read as GBP directly from the `£` symbol — no guessing involved, the symbol is explicit in the amount cell itself.

## 8. Sum of Amount by currency (clean rows only; excludes the 2 rows in §6a/6b with no parseable amount)
| Currency | Sum | Rows included |
|---|---|---|
| GBP | £115,173.00 | 36 |
| USD | $5,803.75 | 2 |
| *(excluded — unparseable/missing)* | — | 2 (P-1012 "pending", P-1027 blank) |

Workings: summed the `Decimal` amount of every delivered row grouped by its resolved `Currency` code (36 + 2 + 2 excluded = 40 total delivered rows); the 2 rows with no numeric amount are excluded from both sums (not zero-filled) and called out separately so finance can chase the source documents for those two receipts.

## 9. Validation summary
- Ref: required ✓, matches `^P-\d+$` ✓ (all 40), unique ✓ (post-dedup).
- Payment date: required ✓ (all 40 parsed to a date).
- Payer: required ✓ (all 40 non-blank).
- Amount: required — **1 failure** (P-1027, blank — see §6b).

## 10. Assumptions made (flagged for sign-off)
1. **Day-first date convention** applied to all ambiguous `DD/MM/YYYY`-shaped dates (UK/SG market default). If any counterparty is known to submit US-style `MM/DD/YYYY`, the 7 rows in §6c should be checked individually against the payer's own remittance record.
2. **Country canonical form** chosen as the full country name (`United Kingdom`, `United States`, `Singapore`) rather than the most-frequent raw spelling, to give one unambiguous value per country as briefed.
3. **`£` in the Amount cell → GBP**, per the explicit house rule, applied to P-1008 and P-1023 where the source `Currency` cell was otherwise blank.
4. No amount was guessed or inferred: `P-1012` ("pending") and `P-1027` (blank) are left exactly as found, with their currency preserved from the source `Currency` column, and are excluded from the currency sums in §8.

## 11. Delivery scope
Treated as a one-off clean-up (a single export, no indication it recurs monthly/weekly), so per the skill's triage step no reusable runner/card bundle was generated — just the clean workbook and this report, as requested.
