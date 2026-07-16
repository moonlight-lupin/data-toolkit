# Convert: GL export to journal import

Convert monthly GL export (Debit/Credit) to journal import format with signed amounts for downstream accounting system

- **Source:** xlsx
- **Target:** csv — contract `journal_import`

## Mapping (target ← source)

| Target column | Source | Rule |
|---|---|---|
| JournalRef | Entry No | as_is → text |
| Date | Posting Date | as_is → date |
| AccountCode | Account Code | as_is → text |
| Narrative | Description | as_is → text |
| Amount | Debit, Credit | debit_minus_credit → currency |
| CostCentre | CC Code | as_is → text |
| Source | GLEXPORT | as_is → text |

## Expected source (verify before running)
Columns: `Entry No`, `Posting Date`, `Account Code`, `Account Name`, `Description`, `Debit`, `Credit`, `CC Code`

> Before applying, sense-check today's source against this. Flag any missing, renamed or new columns to the user; don't blind-apply over drift.

## Spec (machine source of truth)

```convert-spec
{
  "name": "GL export to journal import",
  "purpose": "Convert monthly GL export (Debit/Credit) to journal import format with signed amounts for downstream accounting system",
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
    "contract": "journal_import",
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
      "format": "%Y-%m-%d",
      "dayfirst": true
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
      "const": "GLEXPORT",
      "type": "text"
    }
  },
  "rules": {
    "on_unmapped_source": "report"
  }
}
```

> Deterministic conversion — a draft for a qualified person to review. The engine applies this spec; it never invents a value and never fetches (pinned inputs only).