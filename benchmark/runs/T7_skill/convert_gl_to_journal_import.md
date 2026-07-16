# Convert: GL export -> downstream accounting system journal import

Monthly journal upload of the GL export into the downstream accounting system's import format. Recurring (runs every month on that month's GL export).

## Standing rules

- Each month's source must be sense-checked against the Expected source (below) before converting.
- Any discrepancy versus the Expected source -- a renamed, missing or new column -- must be flagged to the user and never silently converted.
- Required target fields (JournalRef, Date, AccountCode, Amount) must never be empty. A row failing a required field must be flagged and EXCLUDED from the import file, never guessed or defaulted.
- Never invent JournalRef, Date, AccountCode or Amount values.
- Source column is a constant 'GLEXPORT' -- it is the fixed identifier for this feed, not a per-row source value.

- **Source:** xlsx (sheet `GL Export`)
- **Target:** csv — contract `journal_import (downstream accounting system)`

## Mapping (target ← source)

| Target column | Source | Rule |
|---|---|---|
| JournalRef | Entry No | as_is → text |
| Date | Posting Date | as_is → date |
| AccountCode | Account Code | as_is → text |
| Narrative | Description | as_is → text |
| Amount | Debit, Credit | debit_minus_credit |
| CostCentre | Cost Centre | as_is → text |
| Source | GLEXPORT | as_is → text |

## Expected source (verify before running)
Columns: `Entry No`, `Posting Date`, `Account Code`, `Account Name`, `Description`, `Debit`, `Credit`, `Cost Centre`

> Before applying, sense-check today's source against this. Flag any missing, renamed or new columns to the user; don't blind-apply over drift.

## Spec (machine source of truth)

```convert-spec
{
  "name": "GL export -> downstream accounting system journal import",
  "purpose": "Monthly journal upload of the GL export into the downstream accounting system's import format. Recurring (runs every month on that month's GL export).",
  "standing_rules": [
    "Each month's source must be sense-checked against the Expected source (below) before converting.",
    "Any discrepancy versus the Expected source -- a renamed, missing or new column -- must be flagged to the user and never silently converted.",
    "Required target fields (JournalRef, Date, AccountCode, Amount) must never be empty. A row failing a required field must be flagged and EXCLUDED from the import file, never guessed or defaulted.",
    "Never invent JournalRef, Date, AccountCode or Amount values.",
    "Source column is a constant 'GLEXPORT' -- it is the fixed identifier for this feed, not a per-row source value."
  ],
  "source": {
    "format": "xlsx",
    "sheet": "GL Export",
    "expected_columns": [
      "Entry No",
      "Posting Date",
      "Account Code",
      "Account Name",
      "Description",
      "Debit",
      "Credit",
      "Cost Centre"
    ],
    "dayfirst": true
  },
  "target": {
    "format": "csv",
    "contract": "journal_import (downstream accounting system)",
    "delimiter": ",",
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
        "name": "Narrative"
      },
      {
        "name": "Amount",
        "required": true
      },
      {
        "name": "CostCentre"
      },
      {
        "name": "Source"
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
      "dp": 2
    },
    "CostCentre": {
      "from": "Cost Centre",
      "type": "text"
    },
    "Source": {
      "const": "GLEXPORT",
      "type": "text"
    }
  },
  "rules": {
    "on_unmapped_source": "report",
    "on_missing_required": "exclude"
  }
}
```

> Deterministic conversion — a draft for a qualified person to review. The engine applies this spec; it never invents a value and never fetches (pinned inputs only).