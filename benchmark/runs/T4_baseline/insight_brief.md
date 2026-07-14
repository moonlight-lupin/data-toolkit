# Sales Insight Brief — Apr 2025 to May 2026

Source: `fixtures/t4_sales.csv` (287 data rows, Invoice/Date/Customer/Region/Amount/Currency; not modified). All figures below are computed directly from this file; workings are shown so they can be checked.

## Headline findings

1. **Revenue is flat, not growing.** Core (GBP) monthly revenue holds in a narrow £58.7k–£72.3k band throughout the 13 months of data, with no meaningful upward or downward trend (first three months averaged £62,093/month vs last three months £62,492/month, a **+0.6%** change).
2. **Severe customer concentration.** Bramley & Cole accounts for **69.7% of clean GBP revenue** (£581,016 of £833,807, from 100 of 272 invoices). No other customer exceeds 4%. This is the single biggest revenue risk in the book.
3. **One invoice is almost certainly a data error, not a sales result.** INV-9999 (Kestrel, 18 Mar 2026, £250,000) is 26× the next-largest invoice and breaks the otherwise unbroken INV-7001–INV-7286 numbering sequence. It has been excluded from all totals and trends below and reported separately.
4. **A full month of invoices is missing.** No invoices are dated in November 2025 at all — the sequence jumps directly from INV-7154 (25 Oct 2025) to INV-7155 (08 Dec 2025) with no gap in invoice numbers. This looks like a reporting/extract gap rather than a genuine trading pause and should be checked against source systems before the trend is relied upon.

## How revenue was totalled (read before quoting a number)

The file mixes currencies (GBP and USD) with no exchange rate supplied, and contains one extreme outlier and three missing amounts. Summing everything as one number would silently blend currencies and let one bad row dominate the total, so revenue is reported **by currency, with the outlier and blanks excluded and separately disclosed**, rather than as a single blended figure.

| Basis | Amount | Invoices | Note |
|---|---|---|---|
| **GBP revenue (clean)** | **£833,807** | 272 | GBP rows only, excluding 3 blank-amount rows and the INV-9999 outlier |
| USD revenue (clean) | $37,278 | 11 | USD rows only, excluding 1 blank-amount row; kept separate as no FX rate is provided in the source |
| GBP total if INV-9999 is included | £1,083,807 | 273 | Shown only to illustrate the distortion — not recommended as the headline figure |
| Excluded — missing Amount | n/a | 3 | INV-7025, INV-7150, INV-7248 — cannot be estimated, so excluded rather than assumed |

No currency conversion has been applied or estimated anywhere in this brief — GBP and USD are never added together.

## Monthly trend (GBP, clean basis)

| Month | Invoices | Revenue (£) |
|---|---|---|
| Apr 2025 | 21 | 65,142 |
| May 2025 | 20 | 62,410 |
| Jun 2025 | 21 | 58,727 |
| Jul 2025 | 21 | 65,363 |
| Aug 2025 | 21 | 64,830 |
| Sep 2025 | 21 | 62,757 |
| Oct 2025 | 21 | 65,584 |
| **Nov 2025** | **0** | **0 — no invoices dated in this month (see data-quality note)** |
| Dec 2025 | 21 | 72,331 |
| Jan 2026 | 21 | 63,147 |
| Feb 2026 | 22 | 66,041 |
| Mar 2026 | 21 | 63,608 |
| Apr 2026 | 20 | 59,505 |
| May 2026 | 21 | 64,362 |

- Mean month (excl. Nov gap): £64,139; range £58,727 (Jun 2025, lowest) to £72,331 (Dec 2025, highest).
- Invoice count per month is remarkably stable at 20–22, consistent with roughly weekly-ish billing across ~10 customers rather than lumpy project billing.
- Region split is close to even: South £429,661 (142 invoices) vs North £404,146 (130 invoices) — no material regional skew.

## Customer breakdown and concentration (GBP, clean basis, sorted by revenue)

| Customer | Invoices | Revenue (£) | Share |
|---|---|---|---|
| **Bramley & Cole** | 100 | 581,016 | **69.7%** |
| Silverbirch | 22 | 33,103 | 4.0% |
| Orchard Lane | 21 | 31,580 | 3.8% |
| Kestrel | 21 | 30,514 | 3.7% |
| Fenwick | 19 | 29,951 | 3.6% |
| Marlowe | 18 | 27,401 | 3.3% |
| Hollis | 19 | 27,221 | 3.3% |
| Northgate | 18 | 25,906 | 3.1% |
| Dunmore | 18 | 25,412 | 3.0% |
| Verity | 16 | 21,703 | 2.6% |

Bramley & Cole also carries 4 of the 11 clean USD invoices ($26,552 of $37,278, 71% of USD revenue) — the same concentration shows up in the USD book too. Kestrel's GBP share above (3.7%, £30,514, 21 invoices) is its figure **excluding** the INV-9999 outlier; including it, Kestrel's total would jump to £280,514 (25.9% of an inflated £1.08m total) purely because of one suspect row — a further reason the outlier must not be blended into concentration analysis.

**Risk read:** roughly 70% of clean revenue sits with one customer. Any disruption to that relationship (non-renewal, dispute, credit event) would remove around two-thirds of GBP revenue — this is the key risk the sales director should weigh alongside the flat top-line trend.

## Anomalies found

- **INV-9999 — Kestrel — 18 Mar 2026 — £250,000 (GBP).** Flagged as a likely data/entry error: (a) it is 26× the next-highest invoice (£9,576) and 122× Kestrel's own average invoice (~£1,453 excl. this row); (b) invoice numbering is otherwise unbroken from INV-7001 to INV-7286, and this row alone uses an out-of-sequence INV-9999 identifier. Recommend the sales/finance team verify this against source billing before it is included in any reporting; it has been excluded from every total, trend and concentration figure above.

## Data-quality notes — what was excluded and why

| Issue | Detail | Treatment |
|---|---|---|
| Mixed currencies | 275 GBP rows, 12 USD rows; no FX rate in the source file | Reported as two separate totals; never summed together or converted using an assumed rate |
| Missing Amount | 3 rows: INV-7025 (Fenwick, 16 May 2025, GBP), INV-7150 (Marlowe, 18 Oct 2025, USD), INV-7248 (Hollis, 20 Apr 2026, GBP) | Excluded from all revenue, trend and customer totals — not estimated or imputed |
| Extreme outlier | INV-9999 (Kestrel, 18 Mar 2026, £250,000) — see Anomalies above | Excluded from headline totals/trend/concentration; shown separately for transparency |
| Missing month | No invoices dated in November 2025, despite an unbroken invoice-number sequence either side of the gap | Reported as a gap rather than zero-filled or interpolated; recommend checking against the source billing system |
| Duplicate invoices | None found (0 of 287 Invoice values repeat) | No action needed |
| Date parsing | Dates supplied as DD/MM/YYYY per the brief; parsed accordingly (e.g. 01/04/2025 = 1 Apr 2025, not 4 Jan) | Confirmed all 287 dates fall within Apr 2025–May 2026 (min 01 Apr 2025, max 27 May 2026) — no out-of-range or ambiguous dates |

## Caveats

- This is a working draft for review before circulation or reliance — a qualified reviewer should sanity-check the INV-9999 and November-2025 gap findings against the underlying billing/ERP system before they are acted on.
- No exchange rate assumption has been made anywhere in this brief; if a blended GBP-equivalent total is required, it should be produced using QIP's actual booking-date FX rates, not an estimate.
- "Clean" totals throughout mean: GBP or USD rows only, blank-Amount rows removed, INV-9999 removed. This basis is used consistently across the revenue, trend and customer sections above so the figures are comparable to one another.
