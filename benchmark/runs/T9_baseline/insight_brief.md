# Sales Insight Brief — T9 Sales Export (Jan 2025 – Jun 2026)

**Source file:** `fixtures/t9_sales_large.csv` (249,905 rows, 12.6 MB, columns: Invoice, Date, Customer, Region, Amount, Currency)
**Prepared:** 20 Jul 2026
**Status:** Working draft for review — descriptive analysis only, not financial or investment advice.

---

## How the file was handled (ingestion)

- **File size:** 12.6 MB, 249,905 data rows — small enough to load entirely into memory; no chunking, sampling, or streaming was required.
- **Ingestion path:** single-pass `pandas.read_csv()` (C engine) into an in-memory DataFrame, with `Invoice`/`Customer`/`Region`/`Currency` forced to string dtype to avoid mixed-type inference.
- **Timing:** full read completed in **0.26 seconds**; resulting DataFrame occupies **~70 MB** in memory (well within normal working-memory limits).
- Dates were parsed explicitly as `DD/MM/YYYY` (`pd.to_datetime(..., format='%d/%m/%Y')`) to avoid the US/UK date ambiguity risk in this format.
- No sampling or truncation was applied anywhere in this analysis — every figure below is computed over the full row set (minus the exclusions documented below).

---

## Headline findings

1. **Revenue is reported in two currencies that were kept separate, not summed.** 249,605 rows (99.88%) are in GBP; 300 rows (0.12%) are in USD. No FX rate was supplied in the source or the task brief, so GBP and USD were **not** added together (doing so would silently misstate revenue). All trend and concentration figures below use the GBP book, which is the overwhelming majority of the business.
2. **Total clean GBP revenue: £446,463,727** across 249,555 GBP invoices with a valid amount and date.
   - Of this, **£10,000,000 (2.2% of the GBP total) comes from five suspect invoices** (see Anomalies below). Excluding those five rows, underlying GBP revenue is **£436,463,727**.
3. **Total USD revenue: $524,670** across 300 invoices (immaterial in scale next to the GBP book, and not convertible to GBP without a specified rate).
4. **One customer, "Kestrel Group," accounts for 53.1% of GBP revenue** — a material single-customer concentration risk.
5. **September 2025 has zero invoices of any kind** — a complete one-month gap in an otherwise dense, near-daily dataset. This looks like a data-extract or system issue rather than a genuine trading gap and should be checked with the source system before this export is relied upon for a trend narrative.

---

## Revenue — how it was totalled

| Currency | Invoices (valid amount & date) | Sum |
|---|---:|---:|
| GBP | 249,555 | £446,463,727 |
| USD | 300 | $524,670 |

- "Valid amount & date" excludes 50 rows with a blank `Amount` (see Data Quality) and 0 rows with an unparseable date (all dates parsed cleanly).
- All 249,905 rows fall inside the stated Jan 2025 – Jun 2026 period (actual range in file: 01 Jan 2025 to 27 Jun 2026); no out-of-period rows were found or excluded.
- **Do not add the GBP and USD figures together** — that would require an FX rate, which is not in scope here and was not assumed.

---

## Monthly trend (GBP, £)

| Month | Revenue (£) | Invoices |
|---|---:|---:|
| 2025-01 | 25,659,005 | 14,679 |
| 2025-02 | 25,665,995 | 14,679 |
| 2025-03 | 25,674,389 | 14,680 |
| 2025-04 | 25,661,333 | 14,679 |
| 2025-05 | 25,670,223 | 14,679 |
| 2025-06 | 25,674,897 | 14,680 |
| 2025-07 | 25,666,625 | 14,679 |
| 2025-08 | 25,672,315 | 14,679 |
| **2025-09** | **— (no invoices at all)** | **0** |
| 2025-10 | 25,677,713 | 14,680 |
| 2025-11 | 25,673,317 | 14,679 |
| 2025-12 | 25,676,707 | 14,679 |
| 2026-01 | 25,686,247 | 14,680 |
| 2026-02 | 25,671,945 | 14,679 |
| 2026-03 | 35,681,835 | 14,684 |
| 2026-04 | 25,687,681 | 14,680 |
| 2026-05 | 25,676,837 | 14,679 |
| 2026-06 | 25,686,663 | 14,681 |

**Reading the trend:** excluding the September gap and the March 2026 spike (both explained below), monthly GBP revenue is remarkably flat — roughly £25.66–25.69M and ~14,679–14,684 invoices every month, i.e. essentially **no organic growth or decline** over the 17 reporting months. The March 2026 figure (£35.68M) is not real growth: it is the flat ~£25.68M baseline plus exactly £10,000,000 from the five anomalous invoices flagged below. **Underlying month-on-month growth over the period is effectively 0%.**

USD volumes are steady at 17–18 invoices and ~$28,500–$32,500/month throughout, with no equivalent gap or spike.

---

## Customer concentration (GBP book)

- 41 unique customers in the GBP book.
- **Top customer — Kestrel Group: £236,978,261, 53.08% of GBP revenue**, from 83,184 invoices (33.3% of GBP transaction count, average invoice ~£2,849 vs. an overall average of ~£1,789).
- Top 5 customers: 59.79% of revenue.
- Top 10 customers: 65.39% of revenue.
- **Herfindahl-Hirschman Index (HHI): 2,877** — by conventional competition-analysis thresholds (>2,500 = "highly concentrated"), this book is highly concentrated, driven almost entirely by the single Kestrel Group relationship. Losing or downgrading that one account would remove roughly half of GBP revenue.
- The remaining 40 customers each sit in a narrow band of roughly £4.96M–£5.0M (before the Customer AA anomaly, see below) — i.e. a fairly even "long tail" apart from Kestrel Group.

| Rank | Customer | Revenue (£) | Invoices | Share |
|---|---|---:|---:|---:|
| 1 | Kestrel Group | 236,978,261 | 83,184 | 53.08% |
| 2 | Customer AA | 14,962,136 (see note) | 4,157 | 3.35% |
| 3 | Customer CB | 5,005,926 | 4,162 | 1.12% |
| 4 | Customer DE | 5,003,567 | 4,165 | 1.12% |
| 5 | Customer CE | 5,001,334 | 4,163 | 1.12% |
| 6 | Customer AD | 5,000,286 | 4,154 | 1.12% |
| 7 | Customer DC | 4,999,589 | 4,165 | 1.12% |
| 8 | Customer FC | 4,999,480 | 4,160 | 1.12% |
| 9 | Customer HA | 4,999,081 | 4,155 | 1.12% |
| 10 | Customer EC | 4,998,142 | 4,163 | 1.12% |

**Note on rank 2:** Customer AA's £14.96M includes the £10.0M in anomalous invoices below. Strip those out and Customer AA's underlying revenue is **£4.96M** — in line with the rest of the "long tail," not a genuine #2 relationship. Ranks 3–10 are unaffected by the anomaly.

---

## Region split (GBP)

| Region | Revenue (£) | Invoices |
|---|---:|---:|
| North | 228,235,569 | 124,780 |
| South | 218,228,158 | 124,775 |

Split is close to even (51.1% North / 48.9% South) — no material regional concentration.

---

## Anomalies

1. **Five suspect £2,000,000 invoices — the single biggest data-quality concern in this file.**
   - Invoices `INV-349901` to `INV-349905`, all to **Customer AA**, all in the **North** region, dated on **five consecutive days, 10–14 Mar 2026**.
   - Each is exactly £2,000,000.00 — a round number roughly **700x** the overall mean GBP invoice (£1,789) and far above the extreme-outlier threshold (Q3 + 3×IQR = £7,424).
   - Consecutive invoice numbers, consecutive dates, identical round amount, single customer: this pattern is far more consistent with a test/placeholder batch or a data-entry/system error than genuine sales activity.
   - **Effect if not corrected:** overstates GBP revenue by £10.0M (2.2% of total), overstates March 2026 by 39%, and would misrepresent Customer AA as the #2 customer by revenue.
   - **Recommendation:** verify these five invoices against the source system before using this export for revenue reporting or forecasting. All revenue figures above are shown both including and excluding this £10.0M so the brief is usable either way once verified.
2. **No other extreme outliers.** Applying the same IQR-based test (upper bound = Q3 + 3×IQR = £7,424; lower bound = Q1 − 3×IQR = −£3,776) to the rest of the GBP book found no other rows above threshold, and no negative or zero-amount invoices anywhere in the file.
3. **No duplicate invoice numbers.** All 249,905 invoice numbers are unique, and the numeric sequence (INV-100001 to INV-349905) is fully contiguous with no gaps — the file does not appear to be missing whole invoices from the numbering sequence.

---

## Data-quality notes — what was excluded and why

| Issue | Rows affected | Treatment |
|---|---:|---|
| Blank `Amount` | 50 (0.02% of rows) | Excluded from all revenue, trend, and concentration figures. Spread evenly (~3/month) across the period, GBP only, no single customer or month disproportionately affected (16 belong to Kestrel Group, consistent with its 33% share of transaction volume — not a targeted gap). |
| Unparseable `Date` | 0 | None found; all dates parsed cleanly under DD/MM/YYYY. |
| Rows outside stated Jan 2025 – Jun 2026 period | 0 | None found; file's actual date range (01 Jan 2025 – 27 Jun 2026) matches the stated period. |
| Missing `Customer` / `Region` | 0 | None found. |
| Duplicate `Invoice` numbers | 0 | None found; all 249,905 invoice IDs unique. |
| Negative or zero `Amount` | 0 | None found. |
| **Complete data gap: September 2025** | 0 rows in the file for that month | Not an exclusion made by this analysis — the source file itself contains no September 2025 invoices at all, against a background of ~14,679 invoices/month every other month. Flagged as a likely extract or system issue; recommend confirming with the source system whether September 2025 data exists elsewhere and was omitted from this export. |
| Mixed currencies (GBP / USD) | 300 USD rows (0.12%) | Kept as a separate USD total rather than converted or summed with GBP, since no FX rate was provided. 6 of the 41 GBP customers (including Kestrel Group, 100 rows) also transact in USD in small volume; this does not change the GBP-based concentration ranking materially. |
| Five £2,000,000 invoices to Customer AA (Mar 2026) | 5 (0.002% of rows, 2.2% of GBP revenue value) | **Not excluded from the headline total** (shown as "including"), but flagged prominently and a second "excluding" figure is given throughout, since these look like data errors pending verification. |

**Bottom line for the sales director:** the underlying business is flat (~£25.7M/month, no growth) and heavily dependent on one customer (Kestrel Group, ~53% of revenue) — a concentration risk worth addressing regardless of the anomalies. Before circulating externally, get the source system to (a) confirm or correct the five £2M Customer AA invoices and (b) explain the missing September 2025 data.
