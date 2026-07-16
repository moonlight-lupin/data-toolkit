# Payments Data Cleaning Audit Report

## Overview
- **Source:** t1_messy_payments.csv
- **Purpose:** Payments received for finance team receipts review
- **Processing date:** 16 Jul 2026

## Summary
| Metric | Count |
|--------|-------|
| Input rows | 43 |
| Output rows (clean) | 40 |
| Rows dropped | 3 |
| Cells flagged for review | 2 |

## Rows Dropped
### exact duplicate (2 rows)
Row indices: 15, 35

### total/subtotal row (1 rows)
Row indices: 21

## Cells Flagged for Review
| Row | Column | Value | Issue |
|-----|--------|-------|-------|
| 11 | Amount | `pending` | amount unparseable: 'pending' |
| 28 | Amount | `` | amount missing |
## Amount Summary
| Currency | Total | Count |
|----------|-------|-------|
| GBP | 115173.00 | 38 |
| USD | 5803.75 | 2 |

**Grand total across all currencies:** 120976.75

## Transformations Applied
1. **Duplicate removal:** Exact duplicates identified by Ref + Payer + Amount + Currency
2. **Row filtering:** Removed blank rows and TOTAL/subtotal rows
3. **Date parsing:** Converted dates to DD MMM YYYY format
   - Formats recognised: DD/MM/YYYY, YYYY-MM-DD, D MMM YYYY
4. **Country standardisation:** 
   - UK, U.K. → United Kingdom
   - USA, U.S.A. → United States
   - SINGAPORE, Singapore → Singapore
5. **Amount parsing:** 
   - Stripped £ prefix when present
   - Removed commas from number formatting
6. **Currency standardisation:**
   - Inferred GBP where £ symbol present but currency blank
   - Standardised to ISO codes (GBP, USD)
7. **Validation:**
   - Unparseable values kept raw and flagged (never guessed)
   - Missing required fields flagged for manual review

## Output Schema
| Column | Type | Notes |
|--------|------|-------|
| Ref | Text | Payment reference ID (e.g. P-1001) |
| Payment date | Date | Standardised to DD MMM YYYY |
| Payer | Text | Payer organisation name (whitespace normalised) |
| Country | Text | Standardised country name |
| Amount | Decimal | Parsed numeric value |
| Currency | Text | ISO currency code (GBP, USD) |

## Notes for Finance Team
- Review flagged cells before approving receipts
- Unparseable dates or amounts have been left in raw form for manual interpretation
- Duplicate rows have been removed (2 exact duplicates)
- 1 TOTAL row was removed (not part of transaction data)
- Check any missing currency fields in flagged cells
