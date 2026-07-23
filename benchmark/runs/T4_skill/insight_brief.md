# Sales export (t4_sales.csv) — insight brief
*(as of 27 May 2026 — last invoice date in the file; n = 287 invoice lines, 01 Apr 2025 – 27 May 2026)*

Intent: what is driving revenue, and where the concentration/trend/anomaly risks sit, over Apr 2025 – May 2026. Computed with the toolkit's local Decimal engine (`analyse.py`) — every figure below is a direct engine output or an arithmetic step shown alongside it, never an estimate.

## Headline

1. **Revenue must be read as two separate currencies, not one total.** 275 of 287 lines are GBP (£1,083,807 across 273 parseable amounts) and 12 are USD ($37,278 across 11 parseable amounts). No exchange rate was supplied, so the two are **not** added into a single "total revenue" figure — blending them would silently misstate value (100 USD ≠ 100 GBP).
2. **One customer carries the GBP book: Bramley & Cole is 53.6% of GBP revenue** (£581,016 of £1,083,807, across 100 of 275 GBP invoices — 3 to 6× the invoice count of any peer). It is the only customer billed roughly weekly; the other nine bill roughly monthly. Concentration is high either way it's read: HHI 3,597 ("concentrated"), Gini 0.634 ("extreme inequality", n=10 customers).
3. **A single £250,000 invoice (INV-9999, Kestrel, dated 18 Mar 2026) is a strong, isolated anomaly**, not a trend — see "Notable" below. It inflates the Mar-2026 GBP month 4.9× above normal, and inflates Kestrel's apparent share of revenue by 22 points. Excluding it, GBP revenue is essentially **flat** over the 14-month window (linear-trend slope ≈ –£85/month, R² ≈ 0.00).
4. **November 2025 has zero invoices of any currency** — a genuine gap month (confirmed: no rows dated 11/2025 anywhere in the file), not a parsing artefact.
5. **Regional split flips once the anomaly is removed**: including it, North leads GBP revenue 60.4% to South's 39.6%; excluding it, South is marginally ahead (51.5% vs 48.5%) — the "North leads" read is an artefact of one invoice, not a structural regional pattern.

## Key metrics

### Revenue by currency (all 287 lines)

| Currency | Lines | Parsed | Blank/skipped | Total | Mean | Median | Min | Max |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| GBP | 275 | 273 | 2 | £1,083,807 | £3,969.99 | £2,004.00 | £600 | £250,000 |
| USD | 12 | 11 | 1 | $37,278 | $3,388.91 | $2,004.00 | $678 | $9,108 |

*(3 blank Amount cells in total, none summed or estimated — see Caveats.)*

### GBP monthly trend (`period_series`, month grain, dayfirst dates)

| Month | Total (£) | Δ vs prior | % change |
|---|---:|---:|---:|
| 2025-04 | 65,142 | — | — |
| 2025-05 | 62,410 | −2,732 | −4.2% |
| 2025-06 | 58,727 | −3,683 | −5.9% |
| 2025-07 | 65,363 | +6,636 | +11.3% |
| 2025-08 | 64,830 | −533 | −0.8% |
| 2025-09 | 62,757 | −2,073 | −3.2% |
| 2025-10 | 65,584 | +2,827 | +4.5% |
| 2025-11 | 0 | −65,584 | −100% (genuine gap — see Caveats) |
| 2025-12 | 72,331 | +72,331 | n/a (prior period zero) |
| 2026-01 | 63,147 | −9,184 | −12.7% |
| 2026-02 | 66,041 | +2,894 | +4.6% |
| 2026-03 | 313,608 | +247,567 | +374.9% (anomaly-driven — see Notable) |
| 2026-04 | 59,505 | −254,103 | −81.0% |
| 2026-05 | 64,362 | +4,857 | +8.2% |

- Excluding November 2025 (no trading) and the March 2026 anomaly, ordinary GBP months range **£58,727 (Jun 2025) to £72,331 (Dec 2025)** — a 23.2% spread, consistent with a stable, recurring-billing pattern rather than growth or decline.
- Linear trend (`trend()`, descriptive only, not a forecast) on the 14 monthly totals: **including** the anomaly, slope = +£4,860/month but R² = 0.084 (the fit is weak — one point is doing the work); **excluding** it, slope = –£85/month, R² ≈ 0.00. Both classify as **flat**.
- USD (12 lines across 14 months) is too sparse to read a trend from — several zero-count months, best month $9,108 (Jan 2026). It is a minor secondary line, not material next to GBP.

### GBP customer breakdown (`breakdown` + `concentration`, all 10 customers)

| Customer | Invoices | Total (£) | Share | Cum. share |
|---|---:|---:|---:|---:|
| Bramley & Cole | 100 | 581,016 | 53.6% | 53.6% |
| Kestrel | 22 | 280,514 | 25.9% | 79.5% |
| Silverbirch | 22 | 33,103 | 3.1% | 82.5% |
| Orchard Lane | 21 | 31,580 | 2.9% | 85.5% |
| Fenwick | 20 | 29,951 | 2.8% | 88.2% |
| Marlowe | 18 | 27,401 | 2.5% | 90.8% |
| Hollis | 20 | 27,221 | 2.5% | 93.3% |
| Northgate | 18 | 25,906 | 2.4% | 95.7% |
| Dunmore | 18 | 25,412 | 2.3% | 98.0% |
| Verity | 16 | 21,703 | 2.0% | 100.0% |

- Top-1 share 53.6%; top-3 share 82.5%; **3 of 10 customers cover 80%** of GBP revenue.
- HHI (customer totals, 0–10,000 scale) = **3,597 → "concentrated"**; Gini = **0.634 → "extreme inequality"** (n=10 groups — a small denominator; read as indicative of shape, not a precise population statistic).
- **With the £250,000 anomaly removed**, Bramley & Cole's share actually *rises* to 69.7% (of a smaller £833,807 pool) and Kestrel falls from 25.9% to 3.7% (£30,514, back in line with the other nine customers at 2.6%–4.0%). The headline concentration story — Bramley & Cole dominates — holds either way; Kestrel's apparent #2 position is entirely the anomaly.

### USD customer breakdown (small sample, n=11 parsed lines — indicative only)

| Customer | Invoices | Total ($) | Share |
|---|---:|---:|---:|
| Bramley & Cole | 4 | 26,552 | 71.2% |
| Verity | 4 | 5,260 | 14.1% |
| Marlowe | 3 | 3,787 | 10.2% |
| Orchard Lane | 1 | 1,679 | 4.5% |

### Region (GBP)

| Basis | North | South |
|---|---:|---:|
| Including anomaly | £654,146 (60.4%) | £429,661 (39.6%) |
| **Excluding anomaly** | £404,146 (48.5%) | £429,661 (51.5%) |

## Notable — outliers and anomalies

- **Tukey IQR fences on GBP amounts**: lower −£3,419.50, upper £9,136.50 (from p25 £1,289 / p75 £4,428). 5 values breach the upper fence: **£250,000, £9,576, £9,472, £9,316, £9,212**. The four ~£9.2–9.6k values are ordinary high-end invoices, close to the fence and plausible as Bramley & Cole's largest regular tickets. **£250,000 stands apart** — 26× the overall GBP median ticket (£2,004) and roughly 27× the upper fence's own width above the median.
- **INV-9999 (Kestrel, North, £250,000, 18 Mar 2026)** shows multiple independent anomaly signals, not just size:
  - Every other invoice in the file is sequentially numbered INV-7001–INV-7286 (286 rows); INV-9999 is the sole exception and is appended as the **last row** of the file, out of sequence.
  - It shares its date (18 Mar 2026) with another, unrelated invoice, INV-7222 (Orchard Lane, USD, North) — two invoices dated the same day is not itself unusual, but combined with the numbering break it is a further data-provenance flag.
  - Kestrel's other 21 GBP invoices in the file range £795–£2,199; £250,000 is ~114–314× that customer's own normal range.
  - USD outliers: none detected (n=11 is below/at the threshold where the fence check is meaningful; no value breaches).
- **Recommendation (flag, not a finding this dataset can settle):** verify INV-9999 against the source billing/ERP system before including it in reported GBP revenue, Kestrel's customer standing, or the March 2026 month-end figure. All of the "anomaly-driven" figures above are shown both with and without it so either view is available pending that check.

## Caveats & data-quality notes

- **Profile/quality gate**: `dataclean.score_quality` scores the file 99.9/100 (grade A); 0 duplicate rows; 0 duplicate invoice numbers; all 287 dates parsed cleanly (0 unparseable), all falling inside 01 Apr 2025–27 May 2026 (matches the requested Apr 2025–May 2026 window, DD/MM/YYYY read dayfirst throughout).
- **3 blank Amount cells excluded from every sum/mean/median above** (1.0% of rows) — not zero-filled, not estimated:
  - INV-7025, 16 May 2025, Fenwick, South, GBP
  - INV-7150, 18 Oct 2025, Marlowe, North, USD
  - INV-7248, 20 Apr 2026, Hollis, North, GBP
- **Currency gate applied**: the Currency column carries two ISO codes (GBP, USD) that were never summed together; every total, mean, breakdown and concentration figure above is computed within one currency. No FX rate was supplied or assumed — if a blended GBP-equivalent view is wanted, an agreed rate needs to be supplied first.
- **November 2025 is a genuine zero month**, confirmed by checking the raw file for any `/11/2025` date (none found) — this is a true gap in trading, not a filled/estimated period. `period_series` fills calendar gaps as zero by convention; this is the only such gap in the window.
- **Small-n caveats**: the USD breakdown (11 parsed lines across 4 customers) and the 10-customer GBP concentration figures (HHI, Gini) are all reported with their n so shares aren't over-read; USD in particular is too thin (as few as 0–1 invoices in some months) to support any monthly trend statement.
- **What this data cannot answer**: it is invoice-level revenue only — no cost, margin or profitability data is present, so nothing here should be read as a profitability signal; it cannot confirm *why* INV-9999 exists (system export error vs a genuine one-off transaction) — that requires checking the source system, which is outside this dataset; it cannot attribute the flat GBP trend to any specific driver (pricing, volume, seasonality) — the data supports "flat," not a cause.

---
*Draft for review — descriptive analysis only, not financial or investment advice. Figures should be checked against the source system, particularly INV-9999, before being relied upon.*
