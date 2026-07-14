# T4 sales export — insight brief

(as of 14 Jul 2026, n = 287 invoice rows, period Apr 2025 – May 2026, source: `t4_sales.csv`)

## Headline

1. **One customer drives the business.** Excluding the anomalous invoice below, **Bramley & Cole accounts for 69.7% of GBP revenue** (£581,016 of £833,807, from 100 of 272 GBP invoices) — more than the next nine customers combined. It also has the largest average ticket (£5,810 vs a £3,065 book-wide mean).
2. **Revenue is flat, not growing, over the 14-month window.** Monthly GBP revenue (excluding the anomaly) ranges narrowly between £58,700–£72,300 with no sustained up or down trend: the first month (Apr 2025, £65,142) and the last (May 2026, £64,362) are within 1.2% of each other. The two months with a year-ago comparator are mixed — Apr 2026 is down 8.7% YoY, May 2026 up 3.1% YoY.
3. **A single £250,000 invoice (INV-9999, Kestrel, 18 Mar 2026) is a major anomaly**, not a genuine trend signal — it is 125x the typical (median) GBP invoice, and its invoice number breaks the otherwise-unbroken INV-7001→INV-7286 sequence. Left in, it makes Mar 2026 revenue spike +375% MoM and Kestrel look like the #2 customer (25.9% share); taken out, Mar 2026 reverts to a normal £63,608 and Kestrel drops to a typical 3.7% share, in line with the rest of the tail. **This brief excludes it from all primary totals and flags it for verification** (see Notable).
4. **November 2025 has zero invoices** — a complete one-month gap against an otherwise steady ~21-22 invoices/month cadence. This looks like a missing month in the export rather than a real trading pause, and should be confirmed before it is read as a business event.
5. Currency split: **275 of 287 invoices are GBP, 12 are USD** — the two are never summed together in this brief (no FX rate supplied). GBP is the operating currency; the 12 USD invoices (4.2% of rows) show the same customer concentration pattern (Bramley & Cole = 71.2% of USD value).

## Key metrics

### Revenue total (how it was totalled)
Computed via the toolkit's `analyse.numeric_summary` on the `Amount` column, **split by `Currency` first** (currency gate — 100 GBP ≠ 100 USD, no exchange rate was supplied so no blended figure is invented), then with the anomalous invoice INV-9999 separated out:

| View | Invoices (n) | Total |
|---|---|---|
| GBP, all parseable invoices | 273 | £1,083,807 |
| GBP, **excluding INV-9999 anomaly** (primary view used below) | 272 | **£833,807** |
| USD, all parseable invoices | 11 | $37,278 |

3 invoices have a blank `Amount` cell (2 GBP, 1 USD) and are excluded from every total (see Caveats).

### Monthly trend — GBP, excluding the INV-9999 anomaly (n = 272 invoices, gap periods filled at zero)

| Month | Invoices | Total (GBP) | % change MoM | YoY |
|---|---|---|---|---|
| 2025-04 | 21 | 65,142 | — | — |
| 2025-05 | 21 | 62,410 | -4.2% | — |
| 2025-06 | 21 | 58,727 | -5.9% | — |
| 2025-07 | 21 | 65,363 | 11.3% | — |
| 2025-08 | 21 | 64,830 | -0.8% | — |
| 2025-09 | 21 | 62,757 | -3.2% | — |
| 2025-10 | 21 | 65,584 | 4.5% | — |
| **2025-11** | **0** | **0** | -100.0% | — |
| 2025-12 | 21 | 72,331 | — (from 0) | — |
| 2026-01 | 21 | 63,147 | -12.7% | — |
| 2026-02 | 22 | 66,041 | 4.6% | — |
| 2026-03 | 21 | 63,608 | -3.7% | — |
| 2026-04 | 21 | 59,505 | -6.5% | -8.7% |
| 2026-05 | 21 | 64,362 | 8.2% | 3.1% |

Best real trading month: Dec 2025 (£72,331). Lowest real trading month: Jun 2025 (£58,727). Nov 2025 is excluded from "worst" as it is a data gap, not a trading result (see Caveats).

### Customer breakdown — GBP, excluding the anomaly (n = 272 invoices, £833,807)

| Customer | Invoices | Total (GBP) | Share | Cumulative share |
|---|---|---|---|---|
| Bramley & Cole | 100 | 581,016 | 69.7% | 69.7% |
| Silverbirch | 22 | 33,103 | 4.0% | 73.7% |
| Orchard Lane | 21 | 31,580 | 3.8% | 77.4% |
| Kestrel | 21 | 30,514 | 3.7% | 81.1% |
| Fenwick | 20 | 29,951 | 3.6% | 84.7% |
| Marlowe | 18 | 27,401 | 3.3% | 88.0% |
| Hollis | 20 | 27,221 | 3.3% | 91.2% |
| Northgate | 18 | 25,906 | 3.1% | 94.3% |
| Dunmore | 18 | 25,412 | 3.0% | 97.4% |
| Verity | 16 | 21,703 | 2.6% | 100.0% |

Top-1 share: 69.7%. Top-3 share: 77.4%. 4 of the 10 customers account for 80% of revenue (groups-to-80% = 4). No negative amounts (credit notes) present in the data.

### Region breakdown — GBP, excluding the anomaly

| Region | Invoices | Total (GBP) | Share |
|---|---|---|---|
| South | 143 | 429,661 | 51.5% |
| North | 131 | 404,146 | 48.5% |

Broadly balanced. (Including the anomaly, North appears to lead 60.4/39.6% — an artefact of INV-9999 being coded to North; excluded here for that reason.)

### Currency: USD invoices (n = 11, $37,278) — not combined with GBP

| Customer | Invoices | Total (USD) | Share |
|---|---|---|---|
| Bramley & Cole | 4 | 26,552 | 71.2% |
| Verity | 4 | 5,260 | 14.1% |
| Marlowe | 3 | 3,787 | 10.2% |
| Orchard Lane | 1 | 1,679 | 4.5% |

## Notable — outliers and anomalies

- **INV-9999 (Kestrel, North, 18 Mar 2026, £250,000, GBP)** — the standout anomaly. IQR fence on the GBP amounts (excl. this row) is £[-3,341.5, 9,006.5]; INV-9999 is 27.8x the upper fence value and ~125x the median GBP invoice (£1,991). Its invoice number (9999) is also completely out of sequence against every other invoice in the file (INV-7001–INV-7286, unbroken and gapless otherwise). Two explanations are possible — a genuine one-off large contract, or a data-entry/extraction error (e.g. an extra digit) — this data alone cannot distinguish them; it should be verified against source billing records before being treated as real revenue or as a data error.
- **Five further high-side outliers in the GBP data (all Bramley & Cole, excl. INV-9999):** £9,576 / £9,472 / £9,316 / £9,212 / £9,108 — these sit just above the IQR upper fence (£9,006.5) but are consistent with Bramley & Cole's recurring larger-ticket pattern (its invoices already run ~1.9x the book average) rather than one-off anomalies, so they are not flagged for exclusion.
- No low-side (unusually small) outliers and no negative amounts (credit notes/returns) anywhere in the data.
- No duplicate invoice numbers across the 287 rows.

## Caveats & quality

- **3 blank `Amount` cells excluded from every total/average:** INV-7025 (Fenwick, GBP, 16 May 2025), INV-7150 (Marlowe, USD, 18 Oct 2025), INV-7248 (Hollis, GBP, 20 Apr 2026). These are missing values, not zeros — they are not counted anywhere above (n's shown are already net of them).
- **Currency never blended.** GBP and USD totals are reported separately throughout; no exchange rate was supplied, so no combined "total revenue" figure exists in this brief. If a combined view is wanted, provide the rate(s) to use.
- **INV-9999 (£250,000) is excluded from all primary totals, breakdowns and the trend above**, and reported only in the Notable section, because including it materially distorts every other metric (total revenue +30%, Kestrel's rank, the Mar 2026 trend point, and the North/South regional split). Anyone re-running these numbers with it included will get different, less representative figures — see the two GBP totals quoted above.
- **November 2025 is a genuine gap in the source file** — zero rows of any currency, against a steady ~21-22 invoices/month elsewhere. The engine fills gap periods at zero by construction (an honest trend line), but a true zero should not be assumed without checking the source export/system for a missing month.
- All 287 source rows fall inside the requested Apr 2025 – May 2026 window; none were excluded for being out of range, and no dates failed to parse (dates are DD/MM/YYYY throughout, parsed day-first).
- No duplicate rows or duplicate invoice numbers were found in the profiling pass.
- This brief is **descriptive only** — it does not recommend any pricing, customer, or provisioning action. The customer-concentration and anomaly findings are flagged for the sales director's and finance's judgement, not a decision made here.

---
*Draft for review — descriptive analysis, not financial or investment advice.*
