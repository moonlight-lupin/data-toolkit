# T2 — Subscription Confirmation Extraction: Audit Report

**Date prepared:** 14 Jul 2026
**Source folder:** `fixtures/t2_confirmations` (6 PDFs)
**Output:** `T2_subscription_confirmations.xlsx`
**Method:** Text extracted programmatically from each PDF (PyMuPDF/fitz) and parsed against the label set Investor / Fund / Commitment / Close Date / Reference. No values were inferred or guessed — any field not present in the source text was left blank in the workbook and is flagged below.

## Summary of extraction

| Document | Investor | Fund | Commitment | Close Date | Reference | Issues |
|---|---|---|---|---|---|---|
| confirmation_01.pdf | Meridian Trust Pte Ltd | Harbourline Student Living Fund II | GBP 1,500,000 | 30 Jun 2026 | SC-2026-001 | None |
| confirmation_02.pdf | Calloway Family Office | Harbourline Student Living Fund II | GBP 2,250,000 | 30 Jun 2026 | SC-2026-002 | None |
| confirmation_03.pdf | Ryecroft Pension Scheme | Harbourline Student Living Fund II | GBP 5,000,000 | 15 Jul 2026 | SC-2026-003 | None |
| confirmation_04.pdf | Tanjong Vista Capital | Harbourline Student Living Fund II | SGD 2,000,000 | **BLANK** | SC-2026-004 | Close Date field absent from source document — see below |
| confirmation_05.pdf | Alder & Vane LLC | Harbourline Student Living Fund II | USD 3,100,000 | 15 Jul 2026 | SC-2026-005 | None |
| confirmation_06.pdf | Whitfield Endowment | Harbourline Student Living Fund II | GBP 750,000 | 31 Jul 2026 | SC-2026-006 | None |

## Fields not found (flagged, left blank — never guessed)

- **confirmation_04.pdf — Close Date:** the document contains no "Close Date" label or value anywhere in its extracted text (confirmed by dumping the full text layer). The field has been left blank in the workbook and highlighted. This should be chased with the source/counterparty before the record is relied upon.

## Currency normalisation note

- confirmation_04.pdf states the commitment as "S$ 2,000,000". This has been recorded as currency code **SGD**, amount 2,000,000, on the reasonable assumption that "S$" denotes Singapore dollars in a Singapore-based fund manager's document. This is a formatting normalisation, not an inferred/guessed figure — the underlying amount and the S$ symbol are both explicit in the source. Flagged here for reviewer awareness since the task fields ask for "amount + currency code" and the source used a symbol rather than an ISO code.
- All other documents use explicit ISO currency codes (GBP, USD) as printed in the source — no normalisation was needed.

## Commitment totals by currency (sum of extracted amounts, as drafted — not independently verified)

| Currency | Total Commitment |
|---|---|
| GBP | 9,500,000 |
| USD | 3,100,000 |
| SGD | 2,000,000 |

## Other observations

- All six documents share the same Fund name ("Harbourline Student Living Fund II") and the same document template/structure, so parsing was consistent across all files.
- Close Date values in the source documents are already presented in DD MMM YYYY format; no reformatting was required for confirmation_01, _02, _03, _05, _06.
- No Investor, Fund, Commitment, or Reference fields were missing in any document.

## Caveats

This is a working draft for review. Figures and field values should be checked against the original PDFs (retained in `fixtures/t2_confirmations`) before this extract is relied upon for any fund administration, investor reporting, or regulatory purpose. In particular, please confirm the missing Close Date for confirmation_04.pdf and the SGD currency-code interpretation of "S$" with the deal/fund ops team.
