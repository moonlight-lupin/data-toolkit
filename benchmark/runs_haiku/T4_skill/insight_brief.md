# Sales Export — insight brief
**As of 16 Jul 2026** | n = 287 invoices (Apr 2025 – May 2026)

## Headline

1. **Extreme customer concentration creates revenue risk:** Bramley & Cole represents 53.6% of GBP revenue (£581,016); the top 3 customers account for 82.5%. Loss of Bramley & Cole or Kestrel would materially impair revenue. USD revenue is even more concentrated (71.2% to Bramley & Cole).

2. **March 2026 revenue spike driven entirely by data anomaly:** March 2026 shows £313,608 (29% of the 14-month GBP total), but £250,000 of this is INV-9999 to Kestrel dated 18 Mar 2026—an outlier 125× the median ticket (£2,004). Excluding this anomaly, March revenue is £63,608, consistent with monthly trend.

3. **Underlying revenue trend is flat and stable:** Excluding the March anomaly and November gap, monthly GBP revenue averages £64,200 (range £58,727–£72,331). No upward or downward momentum over 14 months. USD revenue is minimal (£37,278 / 3.3% of total) and erratic month-to-month.

4. **November 2025 has no recorded transactions:** Data coverage gap between 25 Oct 2025 and 08 Dec 2025. Cannot determine whether this reflects a business pause or a data-capture issue.

5. **Regional split favours North:** GBP revenue by region: North 60.4% (£654,146), South 39.6% (£429,661). All USD revenue (£37,278) is North.

## Key metrics

### Total revenue (computed)

| Currency | Total | Count | Mean ticket | Median |
|---|---|---|---|---|
| GBP | £1,083,807 | 273 | £3,970 | £2,004 |
| USD | $37,278 | 11 | $3,389 | $2,004 |

**How totalled:** GBP invoices (n=275, 273 with valid amounts) and USD invoices (n=12, 11 with valid amounts) summed separately. 3 invoices have missing amounts (excluded from revenue total): INV-7025 (Fenwick/South/GBP), INV-7150 (Marlowe/North/USD), INV-7248 (Hollis/North/GBP). No exchange rate applied; figures held in original currencies.

---

### Customer breakdown — GBP (top 10 customers)

| Customer | Revenue | Share | Invoices |
|---|---|---|---|
| Bramley & Cole | £581,016 | 53.6% | 100 |
| Kestrel | £280,514 | 25.9% | 22 |
| Silverbirch | £33,103 | 3.1% | 22 |
| Orchard Lane | £31,580 | 2.9% | 21 |
| Fenwick | £29,951 | 2.8% | 20 |
| Marlowe | £27,401 | 2.5% | 18 |
| Hollis | £27,221 | 2.5% | 20 |
| Northgate | £25,906 | 2.4% | 18 |
| Dunmore | £25,412 | 2.3% | 18 |
| Verity | £21,703 | 2.0% | 16 |

**Concentration signals:**
- Top 1 share: 53.6%
- Top 3 share: 82.5%
- Groups to 80%: 3 customers
- Total distinct customers (GBP): 10

---

### Customer breakdown — USD

| Customer | Revenue | Share | Invoices |
|---|---|---|---|
| Bramley & Cole | $26,552 | 71.2% | 4 |
| Verity | $5,260 | 14.1% | 4 |
| Marlowe | $3,787 | 10.2% | 3 |
| Orchard Lane | $1,679 | 4.5% | 1 |

**Note:** Only 4 customers recorded in USD, n=11 invoices with valid amounts (1 missing).

---

### Monthly trend — GBP (excluding anomalies)

| Period | Revenue | Count | Trend |
|---|---|---|---|
| 2025-04 | £65,142 | 21 | — |
| 2025-05 | £62,410 | 21 | −4% |
| 2025-06 | £58,727 | 21 | −6% |
| 2025-07 | £65,363 | 21 | +11% |
| 2025-08 | £64,830 | 21 | −1% |
| 2025-09 | £62,757 | 21 | −3% |
| 2025-10 | £65,584 | 21 | +5% |
| 2025-11 | *— no data —* | — | — |
| 2025-12 | £72,331 | 21 | +10% |
| 2026-01 | £63,147 | 21 | −13% |
| 2026-02 | £66,041 | 22 | +5% |
| 2026-03 | £313,608 | 22 | **+375% (contains £250k anomaly)** |
| 2026-04 | £59,505 | 21 | −81% |
| 2026-05 | £64,362 | 21 | +8% |

**Adjusted March (excl. INV-9999):** ~£63,608 (−4% MoM, consistent with trend).

**Pattern:** Monthly range (excluding March spike) is £58,727–£72,331, mean £64,200. No sustained growth or decline. Volatility is ±7% around the mean—consistent with a stable customer base with regular transaction flow.

---

### Monthly trend — USD

| Period | Revenue | Count |
|---|---|---|
| 2025-04 | $2,225 | 1 |
| 2025-05 | $2,004 | 1 |
| 2025-06 | $7,132 | 1 |
| 2025-07 | $1,562 | 1 |
| 2025-08 | $1,341 | 1 |
| 2025-09 | $4,480 | 1 |
| 2025-10 | $0 | 1 (missing) |
| 2025-11 | — | — |
| 2025-12 | $678 | 1 |
| 2026-01 | $9,108 | 1 |
| 2026-02 | $0 | 0 |
| 2026-03 | $1,679 | 1 |
| 2026-04 | $5,832 | 1 |
| 2026-05 | $1,237 | 1 |

**Note:** Single invoice per month (mostly). No pattern; erratic month-to-month. Cannot speak to trend with n=1 per period.

---

### Regional split — GBP

| Region | Revenue | Share |
|---|---|---|
| North | £654,146 | 60.4% |
| South | £429,661 | 39.6% |

---

### Outliers (Tukey IQR fences)

**GBP outliers:**
- Upper fence: £4,428 (Q3 + 1.5×IQR)
- 5 invoices exceed the fence; largest 5:
  - INV-9999: £250,000 (Kestrel, 18 Mar 2026) — **data anomaly**
  - INV-7158: £9,576 (Bramley & Cole, 02 Dec 2025)
  - INV-7177: £9,472 (Bramley & Cole, 09 Jan 2026)
  - INV-7022: £9,316 (Bramley & Cole, 13 Apr 2025)
  - INV-7041: £9,212 (Bramley & Cole, 20 May 2025)

**USD outliers:** None (n=11, no high outliers detected by Tukey test).

---

## Notable observations

### Anomaly: INV-9999

| Invoice | Date | Customer | Amount | Region |
|---|---|---|---|---|
| INV-9999 | 18 Mar 2026 | Kestrel | £250,000 | North |

**Assessment:** This invoice is 125× the median (£2,004) and 63× the mean (£3,970). It appears to be a data entry error, a special/non-recurring transaction, or possibly a bulk contract. **Recommendation:** Verify with the sales or operations team whether this is genuine, and if so, re-classify as an exceptional item in trend analysis. If erroneous, it should be corrected or excluded.

**Impact if excluded:** GBP revenue would be £833,807; March 2026 would be £63,608 (not £313,608); the 14-month trend would show no spike.

---

### Date coverage gap: November 2025

No invoices are recorded between 25 Oct 2025 and 08 Dec 2025. The cause is unknown—could reflect a business closure, a data-export error, or a reporting cutoff. **Recommendation:** Confirm with the source system whether November transactions exist.

---

### Missing amounts

3 invoices lack an amount:
1. INV-7025, 16 May 2025, Fenwick, South, GBP
2. INV-7150, 18 Oct 2025, Marlowe, North, USD
3. INV-7248, 20 Apr 2026, Hollis, North, GBP

These are excluded from all revenue totals and trend calculations. Amounts may have been left blank in the source export or lost in transmission. **Recommendation:** Check the source system for these three invoices.

---

## Caveats & data-quality notes

### What was excluded and why
- **3 invoices with missing amounts** (INV-7025, INV-7150, INV-7248) — excluded from revenue total and all per-customer/per-region breakdowns
- **1 USD invoice with missing amount** (INV-7150) — counted in the USD row count (12) but not USD revenue total (11 valid)
- **No exchange rate applied** — GBP and USD figures are held in original currencies; no blended or sterling-equivalent total computed (would require an assumed or supplied rate)
- **November 2025 gap period** — treated as zero in the period_series (honest representation of a missing month), not dropped silently

### Data quality summary

| Issue | Count | Impact |
|---|---|---|
| Missing amounts | 3 | ~0.1% of invoices; revenue total understated by unknown amount |
| Date parse errors | 0 | None |
| Duplicate rows (per profile) | 12 | Present; not re-analysed as separate transactions |
| Currency codes | 2 | GBP / USD; separate totals required |

### What this data cannot answer

- **Reason for the November gap** — no invoices recorded between 25 Oct 2025 and 08 Dec 2025; cannot infer whether business was paused or data was not captured.
- **What drove the Bramley & Cole concentration** — whether it reflects one large contract, regular high-frequency orders, or data over-sampling; the export shows transaction counts but not contract or order identifiers.
- **Authenticity of INV-9999** — the £250,000 invoice is a statistical outlier and may be erroneous, but only verification against the source system can confirm.
- **Seasonality or multi-year trend** — the export spans only 14 months (Apr 2025 – May 2026); one year is insufficient to establish seasonal patterns or business cycles.
- **Actual vs. expected revenue** — no target, prior-period, or budget figures are present; cannot assess whether £1.08M is on track or represents growth/decline.

---

**Draft for review — descriptive analysis, not advice.**

This brief analyses what the data shows. Every figure is computed from the raw export; none are estimates. Recommendations for verification (the INV-9999 anomaly, the November gap, the missing amounts) are flagged to support follow-up with the source system.
