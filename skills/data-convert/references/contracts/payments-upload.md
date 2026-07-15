# Convert: AP payment run → payments upload (example contract)

**Example target contract.** A generic **payments upload** for a bank/payment portal — one
payment per row. Copy this card, point `source` at your payment run, and adjust the mapping to
your source's column names. Delivered as a **draft for review** — a person authorises and submits
the actual payment file.

- **Source (example):** an approved AP payment run.
- **Target:** `csv` — the payments-upload contract below.

## Target contract

| Column | Required | Notes |
|---|---|---|
| `BeneficiaryName` | yes | payee legal name |
| `IBAN` | yes | beneficiary account / IBAN |
| `Amount` | yes | positive value, 2 dp |
| `Currency` | yes | ISO code |
| `ValueDate` | yes | requested settlement date, `YYYY-MM-DD` |
| `Reference` | no | remittance reference (payer + invoice) |

## Mapping (target ← source)

| Target | Source | Rule |
|---|---|---|
| BeneficiaryName | Vendor | text |
| IBAN | BankAccount | text |
| Amount | GrossAmount | number (2 dp) |
| Currency | Ccy | text |
| ValueDate | PaymentDate | → date (`YYYY-MM-DD`) |
| Reference | Vendor, Invoice | concat (`" – "`) |

## Expected source (verify before running)
Columns: `Vendor`, `BankAccount`, `GrossAmount`, `Ccy`, `PaymentDate`, `Invoice`

> Before applying, sense-check today's run against this (`--check-only`). Flag any missing,
> renamed or new columns to the user; don't blind-apply over drift. A payments file is
> confidential — keep it on your synced/shared store and share only with the entitled recipient.

## Spec (machine source of truth)

```convert-spec
{
  "name": "AP payment run → payments upload",
  "purpose": "Turn the approved payment run into the bank portal's upload format.",
  "source": { "format": "csv",
              "expected_columns": ["Vendor", "BankAccount", "GrossAmount", "Ccy", "PaymentDate", "Invoice"] },
  "target": { "format": "csv", "contract": "payments_upload",
              "columns": [ { "name": "BeneficiaryName", "required": true },
                           { "name": "IBAN",            "required": true },
                           { "name": "Amount",          "required": true },
                           { "name": "Currency",        "required": true },
                           { "name": "ValueDate",       "required": true },
                           { "name": "Reference" } ] },
  "map": {
    "BeneficiaryName": { "from": "Vendor",              "type": "text" },
    "IBAN":            { "from": "BankAccount",         "type": "text" },
    "Amount":          { "from": "GrossAmount",         "type": "number", "dp": 2 },
    "Currency":        { "from": "Ccy",                 "type": "text" },
    "ValueDate":       { "from": "PaymentDate",         "type": "date", "format": "%Y-%m-%d" },
    "Reference":       { "from": ["Vendor", "Invoice"], "compute": "concat", "sep": " – " }
  },
  "rules": { "on_unmapped_source": "report", "on_missing_required": "error" }
}
```
