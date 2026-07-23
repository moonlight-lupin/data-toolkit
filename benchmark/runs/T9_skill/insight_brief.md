# Sales export (t9_sales_large.csv) — insight brief
*(as of 21 Jul 2026, n = 249,905 invoice lines, 01 Jan 2025 – 27 Jun 2026)*

## Headline

1. **GBP revenue totals £446,463,727** across 249,555 parsed GBP lines (249,605 GBP rows; 50 have a blank Amount and are excluded from the total). A separate, immaterial **USD book totals $524,670** across 300 lines — the two currencies are never summed together (see Data-quality note on currency).
2. **One customer, "Kestrel Group", is 53.1% of GBP revenue** (£236,978,261 of £446,463,727, from 83,200 of 249,555 lines) — concentration is genuinely high (HHI 2,877, classed **"concentrated"**; 24 of 41 customers are needed to reach 80% of revenue).
3. **Underlying monthly revenue is flat, not growing.** The GBP monthly series runs £25.66–25.69m every active month (trend slope ≈ £141k/month, R² = 0.013 — not a meaningful trend over 18 periods); Jan 2025 (£25,659,005) vs Jun 2026 (£25,686,663) is +0.1% over the whole 18-month window.
4. **A £10.0m anomaly in March 2026 is the only real spike in the data.** Five invoices of exactly £2,000,000 each, all to "Customer AA", dated 10–14 Mar 2026, North region (invoice numbers INV-349901 to INV-349905), pushed that month to £35,681,835 (+39.0% MoM) before reverting -28.0% the next month. These 5 lines are also the *only* statistical outliers in the entire GBP file (IQR fences: normal range −£1,376 to £5,024; all 5 sit at £2,000,000, the rest of the data is clean).
5. **September 2025 recorded zero invoices** — confirmed in the raw file (not a parsing gap): every other active month has almost exactly 14,700 lines; Sep 2025 has none. This is either a genuine business pause or a missing extract for that month; the file alone cannot tell which.

## Key metrics

### GBP — numeric summary (Amount, n = 249,555; 50 blank cells excluded)
| Metric | Value |
|---|---|
| Total | £446,463,727 |
| Mean | £1,789.04 |
| Median | £1,548 |
| P25 / P75 | £1,024 / £2,624 |
| Min / Max | £500 / £2,000,000 |
| Negatives | 0 |

### GBP — customer concentration (breakdown by Customer, value = Amount)
| Rank | Customer | Total (£) | Share | Lines |
|---|---|---|---|---|
| 1 | Kestrel Group | 236,978,261 | 53.1% | 83,200 |
| 2 | Customer AA | 14,962,136 | 3.4% | 4,158 |
| 3 | Customer CB | 5,005,926 | 1.1% | 4,162 |
| 4 | Customer DE | 5,003,567 | 1.1% | 4,166 |
| 5 | Customer CE | 5,001,334 | 1.1% | 4,164 |

Concentration engine (`concentration`, all 41 customers): **HHI 2,877** (0–10,000 antitrust scale) → classification **"concentrated"** (2,500–5,000 band); top-1 share 53.1%; top-4 share 58.7%; 24 of 41 customers needed for 80% of revenue.

**Caveat on rank #2:** Customer AA's £14.96m is inflated by the £10.0m March 2026 anomaly (finding 4). Strip those 5 lines and Customer AA's total falls to ~£4.96m — below the ~£5.0m "second tier" of 20+ customers that sit in a tight band, not a genuine #2 by revenue.

### GBP — region split
| Region | Total (£) | Share | Lines |
|---|---|---|---|
| North | 228,235,569 | 51.1% | 124,805 |
| South | 218,228,158 | 48.9% | 124,800 |

Region is not a meaningful driver — an almost exact 50/50 split.

### GBP — monthly trend (period_series, grain = month; gap periods filled as £0)
| Month | Total (£) | MoM % |
|---|---|---|
| 2025-01 | 25,659,005 | — |
| 2025-02 – 2025-08 | 25,661,333 – 25,674,897 | ±0.05% |
| **2025-09** | **0** | **−100%** (no invoices — see Headline #5) |
| 2025-10 – 2026-02 | 25,671,945 – 25,686,247 | back to baseline |
| **2026-03** | **35,681,835** | **+39.0%** (anomaly — see Headline #4) |
| 2026-04 | 25,687,681 | −28.0% (reverts to baseline) |
| 2026-05 – 2026-06 | 25,676,837 – 25,686,663 | ±0.04% |

Trend (linear regression on the 18 monthly totals): slope +£141,235/month, R² = 0.013, classified **"flat"** — the regression finds no real growth once the single anomalous month is in the mix; excluding March 2026 the series is essentially a flat £25.66–25.69m every active month.

### GBP — outliers (Tukey IQR, k = 1.5)
Fences: £−1,376 (low) to £5,024 (high). **5 high-side outliers, 0 low-side.** All 5 outliers are the £2,000,000 Customer AA lines from Headline #4 — there are no other statistical outliers in 249,555 parsed amounts.

### USD book (secondary, 300 lines / 0.12% of the file — reported separately, never summed with GBP)
| Metric | Value |
|---|---|
| Total | $524,670 |
| Top customer | Kestrel Group, $285,089 (54.3%) |
| Outliers | none (0 high, 0 low) |
| Trend | flat (R² = 0.0) |

## Notable

- **The March 2026 anomaly explains essentially the entire month-on-month swing that month**: the £10,009,890 delta vs February is 99.9% accounted for by the 5×£2,000,000 Customer AA invoices (£10,000,000). Recommend the sales director's team confirm these five invoices (INV-349901–349905) with the account before treating March 2026 as organic growth — as filed, it reads as a single large one-off booking, a data-entry duplication, or a bulk pre-payment, not a trend.
- **Kestrel Group's dominance is a genuine pattern, not noise.** It carries 83,200 of 249,555 GBP lines (33.3% of transaction volume) at a broad range of distinct recurring amounts each repeated ~85–99 times across the period — consistent with a large subscription/recurring-billing account, not duplicate postings. It is flagged here only as a concentration and key-account-risk point, not a data-quality issue.
- **No duplicate invoice numbers** were found among the 249,905 invoice IDs (all unique) — the file's transactional integrity (at the invoice-number level) is clean.

## Caveats & quality

- **Ingestion / file-size handling:** the source is a 12.6 MB, 249,905-row **CSV**. Per the toolkit's large-file guidance, `ingest.read_large` (the Parquet-cache/streaming path) is **Excel-only** and does not accept CSV; a CSV of this size is read through the standard `ingest.read_any` single-pass `csv.reader`, which is the documented, appropriate path at this scale (not memory-bound). Actual ingest time measured on this machine: **0.70 seconds** for all 249,906 raw rows (header + data). No chunking, sampling, or pre-splitting was needed or used; every row in the file was read and every metric below is computed over the full dataset, not an estimate from a sample.
- **Currency mix:** the file carries two currency codes (GBP 249,605 rows / 99.88%, USD 300 rows / 0.12%). Per the toolkit's currency gate, these are never summed together — GBP and USD are reported and analysed as two separate totals throughout this brief.
- **Missing values:** 50 of 249,605 GBP rows (0.02%) have a blank Amount cell — excluded from every monetary total, mean, and outlier calculation shown above; still counted in row/customer/region counts. Spread evenly across the period and across ~20 different customers — not concentrated in one account or month.
- **No unparsed dates, no negative amounts, no duplicate invoice numbers** anywhere in the file (profiler quality score 100/100, grade A on every column).
- **September 2025 has zero invoices** (both currencies) — confirmed directly against the raw file, not a date-parsing artefact. Flagged as a data gap the brief cannot explain; worth confirming with the source system.
- **Five clustered £2,000,000 GBP invoices to "Customer AA" (10–14 Mar 2026)** are the only outliers in the file and materially affect the March 2026 trend figure and Customer AA's concentration rank — see Notable and Headline #2/#4 above. Treat customer-concentration rank #2 and the March 2026 "growth" as unconfirmed until this cluster is verified against source records.
- **What this data cannot answer:** why September 2025 has no invoices, whether the March 2026 Customer AA cluster is genuine revenue or an error/duplicate, or anything about margin, cost, or profitability — the file contains only Invoice, Date, Customer, Region, Amount and Currency.

*Draft for review — descriptive analysis only, not financial or investment advice. All figures above were computed by the data-analyse skill's deterministic Decimal engine (`scripts/analyse.py`) over the full 249,905-row file; none are estimated.*
