# Data-extract report — 6 document(s)
- Flags across all documents: **1** (unfound / verify)

## Flag — confirmation_04.pdf (Document 4)
| Field | Issue | Value |
|---|---|---|
| Close Date | label not found |  |

## Commitment totals by currency
- GBP: 9,500,000
- SGD: 2,000,000
- USD: 3,100,000

## Extracted records (summary)
| Source | Investor | Fund | Commitment | Ccy | Close Date | Reference |
|---|---|---|---|---|---|---|
| confirmation_01.pdf | Meridian Trust Pte Ltd | Harbourline Student Living Fund II | 1,500,000 | GBP | 30 Jun 2026 | SC-2026-001 |
| confirmation_02.pdf | Calloway Family Office | Harbourline Student Living Fund II | 2,250,000 | GBP | 30 Jun 2026 | SC-2026-002 |
| confirmation_03.pdf | Ryecroft Pension Scheme | Harbourline Student Living Fund II | 5,000,000 | GBP | 15 Jul 2026 | SC-2026-003 |
| confirmation_04.pdf | Tanjong Vista Capital | Harbourline Student Living Fund II | 2,000,000 | SGD | *(blank)* | SC-2026-004 |
| confirmation_05.pdf | Alder & Vane LLC | Harbourline Student Living Fund II | 3,100,000 | USD | 15 Jul 2026 | SC-2026-005 |
| confirmation_06.pdf | Whitfield Endowment | Harbourline Student Living Fund II | 750,000 | GBP | 31 Jul 2026 | SC-2026-006 |

## Method
- Extracted locally via the data-toolkit `data-extract` skill (`extract.extract_fields`, key-value/next-line label matching); no OCR was required (all 6 PDFs carry a native text layer).
- Dates normalised to DD MMM YYYY; currency amounts kept as exact figures with the detected ISO code held in a separate column (mixed-currency batch: GBP, SGD, USD).
- A field not found in a document is left blank and flagged below — never guessed.
