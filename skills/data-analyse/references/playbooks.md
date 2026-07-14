# Data Analyse — per-data-type playbooks

Which metrics matter depends on what the data *is*. `analyse.suggest_playbook()` guesses
the shape from column roles; this file says what to compute once you (and the user) know
it. Pick the playbook, drop what the intent doesn't need, and add anything the user's
question demands — these are menus, not scripts. Everything below maps onto the engine
functions in `scripts/analyse.py`.

All examples are **fictional**. Metrics with a ★ are the usual headline for that type.

## Transactions / sales / revenue
*(date + amount + a party/category — invoices, sales lines, bookings, donations)*

- ★ `period_series(grain="month")` on the amount — trend, MoM deltas, YoY where >12 months.
- ★ `breakdown(by=customer/product/region, value=amount)` — top contributors,
  top-1/top-3 share, groups-to-80% (the 80/20 read).
- `numeric_summary` + `outliers_iqr` on the amount — typical ticket size, the odd ones.
- `currency_mix` first if amounts carry symbols — split by code before summing.
- Watch for: credit notes/negatives (report them, don't net silently — `has_negatives`),
  duplicate rows (from the profile), a partial first/last month distorting the trend.

## Receivables / payables / open items
*(due or invoice date + amount + counterparty — the "where's the risk" question)*

- ★ `ageing(date_col=due date, as_of=…)` — count AND value per bucket; 90+ is the
  headline. `as_of` is stated in the brief, never implicit.
- ★ `breakdown(by=counterparty, value=amount)` — concentration of what's owed.
- Cross the two: the oldest bucket's largest counterparties (filter rows, re-run breakdown).
- Watch for: future-dated items (the engine buckets them as "future" — say so),
  credits mixed with invoices, and whether the date is *invoice* or *due* date — ask.
- Boundary: matching these against the bank/GL is **data-reconcile**, not this skill.

## Pipeline / CRM
*(stage/status + value + owner + expected close date)*

- ★ `breakdown(by=stage, value=amount)` — the funnel by value and count.
- `breakdown(by=owner)` — coverage per person; `period_series` on expected-close month —
  where the pipeline lands in time.
- `numeric_summary` on deal size; stale deals via `ageing` on last-activity date if present.
- Watch for: weighted vs unweighted value (only compute weighted if a probability column
  exists — never invent probabilities), stages that are really "closed" in disguise.

## Survey / categorical
*(mostly categorical/ordinal columns, low-cardinality answers)*

- ★ `breakdown(by=each question column)` — counts + shares per answer.
- Ordinal columns (the profiler tags them): present in scale order, not by frequency;
  a top-2-box share (e.g. agree + strongly agree) is often the headline.
- Cross-cuts on request: filter rows by one answer, re-run the breakdown on another.
- Watch for: small n (state it; shares on n<30 are indicative only), blank = "(blank)"
  not silently dropped, leading-question caveats belong to the reader, not the data.

## Task / operations list
*(status + owner + dates — trackers, tickets, compliance registers)*

- ★ `breakdown(by=status)` and `breakdown(by=owner)` — load and where it sits.
- ★ Overdue: `ageing(date_col=due date, as_of=today)` on open items only (filter first);
  "future" bucket = not yet due, the rest = overdue by age.
- Throughput if a completed-date exists: `period_series` on completions per week/month.
- Natural next step: this shape is exactly **data-visualise**'s RAG one-pager.

## General ledger / trial balance
*(account + date + debit/credit or signed amount + journal source/user + description)*

- ★ Net movement & turnover by account: `breakdown(by=account, value=signed amount)` for the
  net move, and by **absolute** amount for turnover (activity). Rank accounts on both.
- ★ Unusual postings: `outliers_iqr` on amount, plus flag round-number amounts, weekend/holiday
  dates, and period-end clustering (`period_series` by day/month → spikes at close).
- Concentration: `breakdown(by=journal source or user)` — what/who posts the most; one user
  behind most manual journals is a control **signal**, not a verdict.
- **Integrity check**: total debits must equal total credits — compute both and report any
  imbalance / suspense. A ledger that doesn't balance can't be read as one.
- Watch for: the debit/credit sign convention (build signed = debit − credit, as data-reconcile
  does); reversing entries (equal-and-opposite pairs — report, don't net silently); opening
  balances counted as activity.
- Boundary: matching the GL to the bank or a sub-ledger is **data-reconcile** — this reads the
  ledger itself.

## Inventory / stock
*(SKU + category + on-hand qty + unit cost/value + last-movement date)*

- ★ ABC concentration: `breakdown(by=SKU, value=stock value)` → top-1/top-3 share and
  groups-to-80% — the 80/20 of capital tied up in a few SKUs.
- ★ Slow-movers / ageing: `ageing(date_col=last-movement date, as_of=today, value=stock value)`
  — value sitting 90+ days without movement is the write-down risk; state the as-of.
- Turnover by SKU/category where a usage/COGS column exists (usage ÷ average stock), and
  cover-days (on-hand ÷ daily usage) for stockout risk.
- Watch for: snapshot (stock) vs flow (movements) — say which the file is; negative on-hand
  (data error or backorder — flag, don't average away); zero-value / obsolete lines.

## Spend / AP analysis
*(vendor + category + date + amount, optional contract/PO flag)*

- ★ Concentration: `breakdown(by=vendor, value=amount)` and `by=category` — top-N,
  groups-to-80%. A few vendors holding most spend is both leverage and risk.
- ★ Duplicate-payment risk: same vendor + same amount within a short date window — surface as a
  **flag list for review**, never a conclusion (genuine recurring charges look identical).
- Maverick / off-contract spend where a contract or PO flag exists: `breakdown` of flagged vs not.
- Trend: `period_series` on amount by month; `outliers_iqr` for unusually large invoices.
- Watch for: `currency_mix` (one currency per sum), credit notes / refunds (negatives), and
  threshold-splitting (many just-under-approval-limit invoices to one vendor).

## Cross-domain / relational (TWO datasets)
*(two tables sharing a dimension — time, product, geography, account: our weekly sales vs
scraped competitor prices, actual vs budget, marketing spend vs revenue)*

The one playbook that takes **two datasets**. It **relates** them — it does not match them
line-by-line to find breaks (that's **data-reconcile**). The question is "how does A move with /
compare against B?", and the discipline is **association, never cause**.

- **Nail the join key + grain FIRST** — the #1 failure. Both sides must share the same grain
  (weekly-to-weekly, product-to-product). A *daily* competitor scrape vs *weekly* sales must be
  rolled to a common grain before joining. Confirm the key with the user.
- **Join**: `join_on(l_header, l_rows, r_header, r_rows, on=[keys])` → the joined table plus a
  coverage report (matched / left-only / right-only). **Coverage is a headline finding** —
  "competitor prices cover 78% of our SKU-weeks" — never a silent drop.
- **Position** (levels): per key, A vs B — index (A ÷ B), gap (A − B), % difference. "We're 4.2%
  above the competitor on Widget A, 5% below on Widget B."
- **Co-movement**: a `period_series` per side on the shared grain, then `compare_series(a, b)` →
  Pearson correlation + a ±1 **lead/lag** scan (does a competitor cut *precede* our volume move
  by a week?). Report r with n, and **name the confounders** (promotions, stock-outs,
  seasonality, the scrape's own gaps). Correlation is a prompt to investigate, not a cause.
- **Actual vs budget/forecast** is the same shape: `compare_series(actual, budget)` → variance
  (gap), % variance; whether a variance is favourable or adverse is the user's call, not the
  engine's.
- Watch for: unaligned keys (spelling — 'Widget A' vs 'WIDGET-A'; the join folds case/space but
  not spelling); external-data staleness/coverage on the scraped side (disclose it); and one
  currency per sum if the two sides differ.

## Time series / measurements
*(date + one or more numeric readings — balances, headcount, usage, KPIs)*

- ★ `period_series` per metric — level, deltas, YoY; state whether values are flows
  (sum per period is right) or **stocks/balances** (sums are wrong — use last-in-period;
  filter to period-end rows first, and say which convention was used).
- `outliers_iqr` for spikes; gap periods filled as zero are right for flows but
  misleading for stocks — for stocks report the gap, don't fill it.

## Generic / unknown table

- Start from `suggest_playbook` + the profile; confirm the intent question.
- Default set: `numeric_summary` on each amount column, `breakdown` on each categorical
  (top 10), `period_series` if a date exists, duplicates/missing from the profile.
- Say plainly what the table *can't* answer — often the most useful line in the brief.

## Cross-playbook rules

- **One currency per sum** (`currency_mix` gate) — split or ask, never blend.
- **Negatives are information** — report the count and gross vs net where they matter.
- **Small denominators** — quote n next to any share or average where n < 30.
- **Two datasets → relate, don't reconcile.** If the goal is "how does A compare with B" use the
  cross-domain playbook (`join_on` / `compare_series`) and report join **coverage**; if it's "do
  these two match, what's unexplained", that's **data-reconcile**.
- **Filters are part of the finding** — any metric computed on a subset says so
  ("open items only", "SGD only", "excl. 3 unparseable rows").
