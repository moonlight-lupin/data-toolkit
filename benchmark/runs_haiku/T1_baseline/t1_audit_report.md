# T1 Payments Data Cleaning Audit Report
Generated: 16 Jul 2026 14:30
## Summary Statistics
- **Rows cleaned:** 40
- **Rows dropped:** 3
- **Cells flagged:** 2

## Currency Totals (cleaned data)
- **GBP:** 115,173.00
- **USD:** 5,803.75

## Data Quality Issues

### Dropped Rows
- Row 20 (Ref: P-1015): Exact duplicate
- Row 26 (Ref: ): Total/subtotal row
- Row 40 (Ref: P-1033): Exact duplicate

### Flagged Cells (highlighted in yellow in Excel)
- Row 13 (Ref: P-1012):
  - Amount: Non-numeric value: pending
- Row 28 (Ref: P-1027):
  - Amount: Missing amount

## Data Transformations Applied

### Date Standardisation
- Converted all date formats to DD MMM YYYY (e.g. 01 Jan 2026)
- Supported input formats: DD/MM/YYYY, YYYY-MM-DD, D Mon YYYY

### Country Standardisation
- UK, U.K., United Kingdom → United Kingdom
- USA, U.S.A. → United States
- Singapore, SINGAPORE → Singapore
- Unrecognised formats flagged for review

### Amount and Currency Handling
- Removed commas from numeric values
- Extracted currency from amount field when prefixed with £ (mapped to GBP)
- Values with £ symbol and missing currency assigned GBP
- Non-numeric values (e.g. 'pending') flagged and kept raw

### Duplicate Removal
- Removed exact duplicate rows (same Ref, date, payer, country, amount, currency)

### Total/Subtotal Rows
- Removed rows identified as totals or subtotals

## Rules Applied

1. **Exact duplicates removed**: P-1015 and P-1033 had duplicate entries
2. **Total rows removed**: One TOTAL row removed (row 26 in source)
3. **Unparseable values flagged**: Non-numeric amounts kept raw with flag
4. **£ symbol handling**: Treated as GBP currency indicator
5. **Country standardisation**: Single standardised value per country
