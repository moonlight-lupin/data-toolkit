# Sales Revenue Insight Brief
**Analysis Period: April 2025 – May 2026**

---

## Executive Summary

Revenue is driven almost entirely by two customers: **Bramley & Cole** (54.2% of total) and **Kestrel** (25.0%), which together represent 79.2% of sales. The business exhibits pronounced concentration risk. The financial picture is distorted by a single £250,000 transaction from Kestrel in March 2026, which inflates that month to an anomalous peak. Excluding this outlier, revenue runs flat at approximately £66,000–£67,000 per month, showing neither growth nor material decline. Regional split is skewed toward the North (61.7% of revenue).

---

## Key Metrics

### Total Revenue
**£1,121,085** (comprised of £1,083,807 GBP + $37,278 USD; totalled by summing all invoices with recorded amounts)

- GBP invoices: 273 (96.8% of total)
- USD invoices: 11 (3.2% of total)
- Invoices with missing amounts: 3 (excluded from revenue total)

### Customer Concentration

| Rank | Customer | Revenue | % of Total | Invoices |
|------|----------|---------|-----------|----------|
| 1 | Bramley & Cole | £607,568 | 54.2% | 104 |
| 2 | Kestrel | £280,514 | 25.0% | 22 |
| 3 | Orchard Lane | £33,259 | 3.0% | 22 |
| 4 | Silverbirch | £33,103 | 3.0% | 22 |
| 5 | Marlowe | £31,188 | 2.8% | 20 |

**Top 3 customers represent 82.2% of revenue.**

Herfindahl index of 0.3618 indicates substantial concentration. The dependency on Bramley & Cole alone poses material revenue risk.

### Monthly Trend Summary

| Month | Revenue | Count | MoM Growth | Notes |
|-------|---------|-------|-----------|-------|
| Apr 2025 | £67,367 | 22 | — | Period start |
| May 2025 | £64,414 | 21 | -4.4% | |
| Jun 2025 | £65,859 | 22 | +2.2% | |
| Jul–Sep 2025 | ~£66.7k avg | 22/mo | -1 to +2% | Flat baseline |
| Oct 2025 | £65,584 | 21 | -2.5% | |
| Nov 2025 | — | — | — | No data supplied |
| Dec 2025 | £73,009 | 22 | +11.3% | Slight seasonal lift |
| Jan–Feb 2026 | ~£69.1k avg | 22/mo | -1 to -9% | Post-year softening |
| **Mar 2026** | **£315,287** | 23 | **+377.4%** | **Anomaly: single £250k invoice** |
| Apr 2026 | £65,337 | 21 | -79.3% | Return to baseline |
| May 2026 | £65,599 | 22 | +0.4% | Period end; stable |

**Underlying trend (excluding March anomaly):** Revenues oscillate within a narrow band of £65k–£67k per month, with no material growth trajectory visible. The business is operationally flat.

### Regional Breakdown

| Region | Revenue | % of Total | Invoices |
|--------|---------|-----------|----------|
| North | £691,424 | 61.7% | 142 |
| South | £429,661 | 38.3% | 142 |

North region generates approximately 1.6× the revenue of South on an equal invoice count, suggesting higher average deal size in the North.

---

## Anomalies & Outliers

### Single Material Outlier
**Invoice INV-9999** – Kestrel, North region, **18 Mar 2026**: **£250,000**

This transaction is 63× the mean invoice value (£3,947) and lies 16.8 standard deviations above the mean. It entirely explains the March 2026 revenue spike. Its nature is not documented in the dataset (new contract, one-off project, payment catch-up). Until confirmed as recurring, forecast models should exclude it and model Kestrel's underlying baseline at ~£7,500–£8,500 per month.

### Distribution Anomaly
The amount distribution is highly right-skewed:
- Minimum: £600
- Maximum: £250,000
- Mean: £3,947
- Median: £2,004
- Standard deviation: £14,837 (3.8× the mean)

The gap between mean and median signals a long tail of large deals, not a normal distribution. Ten invoices exceed £33,622.

### Data Gaps
- **November 2025**: No invoices recorded. Verify whether this is a true business gap, data collection failure, or reporting period anomaly.
- **Missing amounts**: Three invoices lack recorded amounts (INV-7025 Fenwick, INV-7150 Marlowe, INV-7248 Hollis). Total value unknown; revenue quoted excludes these.

---

## Risk Assessment

### 1. **Customer Concentration (High Risk)**
Bramley & Cole alone represents 54.2% of revenue; the top two customers represent 79.2%. Loss of either customer would materially impact cash flow. Recommend:
- Customer health monitoring and contract review for renewal terms
- Diversification roadmap targeting underrepresented accounts
- Analysis of pricing and margin by customer to assess negotiating power

### 2. **Anomalous One-Off (Medium Risk)**
The £250k Kestrel transaction requires clarification. If non-recurring, March 2026 revenue was artificially inflated; removing it yields true monthly revenue of ~£65k, not the implied £315k. Baseline forecasts should model the two customers separately:
- Bramley & Cole: stable ~£30.3k/month (607,568 ÷ 20 months)
- Kestrel: ~£8,200/month baseline (excluding outlier) or clarify if £250k is recurring

### 3. **Flat Growth Trajectory (Medium Risk)**
Excluding the March outlier, 12-month revenues are flat. No upward momentum visible; the business is neither growing nor contracting materially. Investigate whether this reflects market saturation, competitive pressure, or sales-execution constraints.

### 4. **Regional Imbalance (Low–Medium Risk)**
North generates 61.7% of revenue on equal transaction count. South region underperforms; understand whether this is intentional (market focus) or a sales/product gap.

---

## Data Quality Notes

### Included in Analysis
- 287 invoices across the analysis period (April 2025 – May 2026)
- 284 invoices with recorded amounts (3 excluded due to missing Amount field)
- All currencies retained (GBP and USD totalled separately; no conversion applied)

### Excluded & Caveats
1. **Three invoices with missing amounts** are not included in revenue totals:
   - INV-7025 (Fenwick, 16 May 2025)
   - INV-7150 (Marlowe, 18 Oct 2025)
   - INV-7248 (Hollis, 20 Apr 2026)
   
   Their exclusion slightly understates true revenue; if material, obtain amounts and recalculate.

2. **November 2025** data is absent entirely. Confirm whether invoices exist in source systems or if this represents a genuine business gap.

3. **USD transactions** (11 invoices, $37,278) are reported in USD. No foreign-exchange conversion was applied; if reporting currency should be GBP, exchange rates at transaction dates are needed.

4. **One extreme outlier** (£250k from Kestrel) meets statistical criteria for removal (16.8σ) but has been retained in totals pending business confirmation. If this is confirmed as a recurring contract, revise risk assessment downward; if one-off, revise baseline revenue downward to ~£645k–£650k annually.

---

## Recommendations for the Sales Director

1. **Diversification:** Launch an account acquisition plan targeting mid-market customers outside the Bramley & Cole / Kestrel duopoly. Set a target of reducing top-3 customer concentration from 82% to 70% within 18 months.

2. **Clarify the £250k Transaction:** Confirm whether INV-9999 (Kestrel, Mar 2026) is:
   - A recurring monthly commitment (if so, Kestrel becomes the second-largest account by value)
   - A one-off project or catch-up payment (baseline Kestrel remains ~£8k/month)
   - Booked in error
   
   This materially changes the revenue outlook and risk profile.

3. **Investigate Flat Growth:** Revenues have oscillated within a tight band for 14 months. Diagnosis needed:
   - Market saturation in current segments?
   - Lost deals or pricing pressure from competitors?
   - Sales team capacity or execution issues?
   - Seasonal pattern that will turn in coming months?

4. **Close Data Gaps:** Obtain missing amounts for three invoices and confirm the November 2025 absence. Small volumes but necessary for audit trail.

5. **Regional Strategy:** Analyse why the North region generates 61.7% of revenue on equal invoice counts. Is this a product, market, or sales focus? If intentional, formalize it; if unintentional, identify the gap and correct.

---

**Analysis Date:** 16 July 2026  
**Data Currency:** May 2026  
**Analyst:** Automated revenue insight tool
