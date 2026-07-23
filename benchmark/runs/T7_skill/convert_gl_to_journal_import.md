# Convert: GL export -> downstream journal import

Recurring MONTHLY conversion: convert the accounting system's GL export into the downstream accounting system's journal import CSV contract.

## Standing rules

- This export arrives every month (recurring). Before converting any month's file, sense-check it against the 'Expected source' column list below -- a renamed, missing, or new column must be flagged to the user, never silently converted.
- Required target fields (JournalRef, Date, AccountCode, Amount) must never be empty. A row failing a required field is flagged and EXCLUDED from the import file -- never guessed or invented.
- Amount is signed: Debit positive, Credit negative (Debit minus Credit), quantised to 2 dp.
- Date is re-expressed from the source's DD/MM/YYYY to the contract's YYYY-MM-DD.
- Source column is always the constant 'GLEXPORT'.
- 'Account Name' in the source is not part of the target contract and is deliberately left unmapped (reported, not dropped silently) -- do not add it to the target without a new confirmed mapping.
- The engine never fetches data and never guesses a value; this is a draft for a qualified person to review before it is submitted to the downstream system.
- Aug 2026 run: source renamed "Cost Centre" to "CC Code" (identical CC-1xx..5xx values, treated as a straight rename and re-pointed the CostCentre mapping) and added a new "Approved By" column (not part of the target contract, left unmapped like Account Name). Flagged for human confirmation in this non-interactive run; sense-check will re-flag if either changes again.

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
| CostCentre | CC Code | as_is → text |
| Source | GLEXPORT | as_is |

## Expected source (verify before running)
Columns: `Entry No`, `Posting Date`, `Account Code`, `Account Name`, `Description`, `Debit`, `Credit`, `CC Code`, `Approved By`

> Before applying, sense-check today's source against this. Flag any missing, renamed or new columns to the user; don't blind-apply over drift.

## Spec (machine source of truth)

```convert-spec
{
  "name": "GL export -> downstream journal import",
  "purpose": "Recurring MONTHLY conversion: convert the accounting system's GL export into the downstream accounting system's journal import CSV contract.",
  "standing_rules": [
    "This export arrives every month (recurring). Before converting any month's file, sense-check it against the 'Expected source' column list below -- a renamed, missing, or new column must be flagged to the user, never silently converted.",
    "Required target fields (JournalRef, Date, AccountCode, Amount) must never be empty. A row failing a required field is flagged and EXCLUDED from the import file -- never guessed or invented.",
    "Amount is signed: Debit positive, Credit negative (Debit minus Credit), quantised to 2 dp.",
    "Date is re-expressed from the source's DD/MM/YYYY to the contract's YYYY-MM-DD.",
    "Source column is always the constant 'GLEXPORT'.",
    "'Account Name' in the source is not part of the target contract and is deliberately left unmapped (reported, not dropped silently) -- do not add it to the target without a new confirmed mapping.",
    "The engine never fetches data and never guesses a value; this is a draft for a qualified person to review before it is submitted to the downstream system.",
    "Aug 2026 run: source renamed \"Cost Centre\" to \"CC Code\" (identical CC-1xx..5xx values, treated as a straight rename and re-pointed the CostCentre mapping) and added a new \"Approved By\" column (not part of the target contract, left unmapped like Account Name). Flagged for human confirmation in this non-interactive run; sense-check will re-flag if either changes again."
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
      "CC Code",
      "Approved By"
    ]
  },
  "target": {
    "format": "csv",
    "contract": "journal_import (downstream accounting system)",
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