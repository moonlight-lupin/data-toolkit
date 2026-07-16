# Convert: GL Export to Journal Import

Monthly GL export conversion to journal import format for downstream accounting system.

## Standing rules

- Each month's source must be sense-checked against the expected shape before converting.
- Any discrepancy (renamed/missing/new column, required field empty) must be flagged and excluded.
- A row failing a required field must be flagged and EXCLUDED from the import file, never guessed.
- Amount is signed: Debit positive, Credit negative (Debit - Credit), formatted to 2 decimal places.
- Date must be re-expressed as YYYY-MM-DD from DD/MM/YYYY.
- Source is the constant 'GLEXPORT' for all rows.
- **Schema note (August 2026+):** GL export column 'Cost Centre' renamed to 'CC Code'; both are functionally equivalent cost centre codes (CC-100, CC-200, etc.). Extra column 'Approved By' is ignored.

- **Source:** xlsx
- **Target:** csv

## Mapping (target ← source)

| Target column | Source | Rule |
|---|---|---|
| JournalRef | Entry No | as_is → text |
| Date | Posting Date | as_is → date |
| AccountCode | Account Code | as_is → text |
| Narrative | Description | as_is → text |
| Amount | Debit, Credit | debit_minus_credit → currency |
| CostCentre | Cost Centre | as_is → text |
| Source | GLEXPORT | as_is |

## Expected source (verify before running)
Columns: `Entry No`, `Posting Date`, `Account Code`, `Account Name`, `Description`, `Debit`, `Credit`, `Cost Centre` (or `CC Code` in August 2026+)

Optional/extra columns ignored: `Approved By`

> Before applying, sense-check today's source against this. Flag any missing, renamed or new columns to the user; don't blind-apply over drift.

## Spec (machine source of truth)

```convert-spec
{
  "name": "GL Export to Journal Import",
  "purpose": "Monthly GL export conversion to journal import format for downstream accounting system.",
  "standing_rules": [
    "Each month's source must be sense-checked against the expected shape before converting.",
    "Any discrepancy (renamed/missing/new column, required field empty) must be flagged and excluded.",
    "A row failing a required field must be flagged and EXCLUDED from the import file, never guessed.",
    "Amount is signed: Debit positive, Credit negative (Debit - Credit), formatted to 2 decimal places.",
    "Date must be re-expressed as YYYY-MM-DD from DD/MM/YYYY.",
    "Source is the constant 'GLEXPORT' for all rows.",
    "Schema note (August 2026+): GL export column 'Cost Centre' renamed to 'CC Code'; both are functionally equivalent cost centre codes. Extra column 'Approved By' is ignored."
  ],
  "source": {
    "format": "xlsx",
    "expected_columns": [
      "Entry No",
      "Posting Date",
      "Account Code",
      "Account Name",
      "Description",
      "Debit",
      "Credit",
      "CC Code"
    ]
  },
  "target": {
    "format": "csv",
    "encoding": "utf-8",
    "columns": [
      {
        "name": "JournalRef",
        "required": true
      },
      {
        "name": "Date",
        "required": true
      },
      {
        "name": "AccountCode",
        "required": true
      },
      {
        "name": "Narrative",
        "required": false
      },
      {
        "name": "Amount",
        "required": true
      },
      {
        "name": "CostCentre",
        "required": false
      },
      {
        "name": "Source",
        "required": false
      }
    ]
  },
  "map": {
    "JournalRef": {
      "from": "Entry No",
      "type": "text"
    },
    "Date": {
      "from": "Posting Date",
      "type": "date",
      "dayfirst": true,
      "format": "%Y-%m-%d"
    },
    "AccountCode": {
      "from": "Account Code",
      "type": "text"
    },
    "Narrative": {
      "from": "Description",
      "type": "text"
    },
    "Amount": {
      "from": [
        "Debit",
        "Credit"
      ],
      "compute": "debit_minus_credit",
      "type": "currency",
      "dp": 2
    },
    "CostCentre": {
      "from": "CC Code",
      "type": "text"
    },
    "Source": {
      "const": "GLEXPORT"
    }
  },
  "rules": {
    "on_unmapped_source": "report",
    "on_missing_required": "exclude"
  }
}
```

> Deterministic conversion — a draft for a qualified person to review. The engine applies this spec; it never invents a value and never fetches (pinned inputs only).