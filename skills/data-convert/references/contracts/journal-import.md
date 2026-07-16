# Convert: general ledger export → journal import (example contract)

**Example target contract.** A generic double-entry **journal import** — one signed amount per
line (debits positive, credits negative). Copy this card, point `source` at your export, and
adjust the mapping to your GL's column names. Delivered as a **draft for review** — a person
submits the import.

- **Source (example):** a GL export with separate `Debit` / `Credit` columns.
- **Target:** `csv` — the journal-import contract below.

## Standing rules

- Exclude any row whose required target fields are blank from the import file.
- Never invent AccountCode, Date, or Amount values.

## Target contract

| Column | Required | Notes |
|---|---|---|
| `JournalDate` | yes | posting date, `YYYY-MM-DD` |
| `AccountCode` | yes | destination account/nominal code |
| `Amount` | yes | **signed** — debit positive, credit negative |
| `Narration` | no | line description |
| `Reference` | no | source document / voucher ref |

## Mapping (target ← source)

| Target | Source | Rule |
|---|---|---|
| JournalDate | Date | → date (`YYYY-MM-DD`) |
| AccountCode | Account | text |
| Amount | Debit, Credit | debit − credit (2 dp) |
| Narration | Memo | text |
| Reference | Ref | text |

## Expected source (verify before running)
Columns: `Date`, `Account`, `Debit`, `Credit`, `Memo`, `Ref`

> Before applying, sense-check today's export against this (`--check-only`). Flag any missing,
> renamed or new columns to the user; don't blind-apply over drift.

## Spec (machine source of truth)

```convert-spec
{
  "name": "GL export → journal import",
  "purpose": "Monthly journal upload into the accounting system.",
  "standing_rules": [
    "Exclude any row whose required target fields are blank from the import file.",
    "Never invent AccountCode, Date, or Amount values."
  ],
  "source": { "format": "csv",
              "expected_columns": ["Date", "Account", "Debit", "Credit", "Memo", "Ref"] },
  "target": { "format": "csv", "contract": "journal_import",
              "columns": [ { "name": "JournalDate", "required": true },
                           { "name": "AccountCode", "required": true },
                           { "name": "Amount",      "required": true },
                           { "name": "Narration" },
                           { "name": "Reference" } ] },
  "map": {
    "JournalDate": { "from": "Date",              "type": "date", "format": "%Y-%m-%d" },
    "AccountCode": { "from": "Account",           "type": "text" },
    "Amount":      { "from": ["Debit", "Credit"], "compute": "debit_minus_credit", "dp": 2 },
    "Narration":   { "from": "Memo",              "type": "text" },
    "Reference":   { "from": "Ref",               "type": "text" }
  },
  "rules": { "on_unmapped_source": "report", "on_missing_required": "exclude" }
}
```
