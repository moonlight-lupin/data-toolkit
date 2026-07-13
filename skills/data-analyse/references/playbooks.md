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
- **Filters are part of the finding** — any metric computed on a subset says so
  ("open items only", "SGD only", "excl. 3 unparseable rows").
