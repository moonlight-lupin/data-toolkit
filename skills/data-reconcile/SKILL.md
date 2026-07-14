---
name: data-reconcile
description: >-
  Reconcile any two record sets (A vs B) and triage the discrepancies — match
  line-by-line on a shared key, or heuristically on amount + date, then classify every
  unreconciled item (category, materiality, probable cause, suggested action) into a
  reconciliation working paper (.xlsx). Use whenever the user wants to "reconcile A to B",
  "reconcile the bank to the ledger", "reconcile the invoice tracker to the accounts", "tie
  out", "match these two lists/exports", "find the differences between", "what doesn't match",
  "reconciliation working paper", or "discrepancy triage". Ships presets for common recurring
  reconciliations (invoice tracker vs accounting records, bank vs cashbook, fund administrator
  vs internal records, payments/PRF vs bank); generic for anything else. Deterministic and
  local-only — it never force-fits a match and never posts an adjustment; it produces a working
  paper for finance to review and sign off. NOT budget/variance analysis, and NOT deal/asset
  analysis (that is out of scope).
---

# Finance Reconciliation

Reconcile **A (ours) against B (theirs)** and — the point of the skill — **triage** the
differences: every unreconciled item is *classified*, not just listed, so finance can act on
the few that matter. Produces a reconciliation **working paper** for a qualified person to
review and sign off.

> **Working paper, not a posting.** It matches and flags; it does **not** adjust the ledger,
> post a correction, or write to any system. Unmatched items stay flagged — **never
> force-fitted** into a match. It runs **fully local** (no external egress), so it's safe for
> bank, payment and sensitive account data.

## Workflow

```python
import sys; sys.path.insert(0, "scripts")
from reconcile import (reconcile_files, propose_aggregations, apply_aggregations,
                       finalize, render_proposals, write_workpaper, render_report, PRESETS)
```

### 1. Intent first — what are we reconciling, and against what?
Establish **A** (e.g. our invoice tracker / cashbook / internal records) and **B** (e.g. the
ledger / bank statement / fund administrator). Pick the **preset** if it's a recurring one
(`python scripts/reconcile.py --catalogue`), else go generic.

### 2. Pick the match strategy (per run — it's a mix)
- **Key** — a shared reference exists on both sides (invoice no, payment ref): `--mode key --key <col>`.
- **Amount + date** — no clean key (typical for bank vs cashbook): `--mode amount_date` — matches
  on amount within tolerance, nearest date **within the date window** (`--date-window N`, default
  ±5 days). A small in-window gap is a **timing difference** (likely in-transit), not a true
  exception. An equal-amount pair *outside* the window is **not** reconciled — it's flagged
  `ambiguous_match` for you to confirm, so transactions weeks apart aren't passed off as timing.
  - **Always pass `--date <col>` in this mode** — the date window is the safety rail. With no
    resolvable date column the window can't apply, so equal-amount pairs are held as
    `ambiguous_match` ("matched on amount alone — confirm") and the run **warns** rather than
    matching on amount alone.
  - A **second pass** over the one-sided residue recovers `duplicate`, `sign_flip` and
    `amount_mismatch` (e.g. a double-entered cashbook line, a debit booked as a credit, a
    net-vs-gross **GST** gap) that key mode gets from the key — so they're classified, not left as
    bare `missing_in_A/B`. Conservative and confirm-first (see `references/triage-taxonomy.md`).

Amounts are parsed as exact **`Decimal`** — ties don't break on binary-float dust.
**Currencies are compared**, so 100 USD never matches 100 SGD: name a currency column with
`--currency <col>` (else the code is read from the amount cell's symbol — `US$`/`S$`/`£`/…; a
bare `$` is treated as ambiguous). A key match whose currencies differ is flagged
`currency_mismatch`; in amount_date mode incompatible currencies simply don't match. For
audit/finance work add `--strict-currency` (`strict_currency=True`): an **unknown** currency on
either side won't match either — it's routed to `currency_unknown` rather than assumed
compatible (default mode stays permissive).
Multi-tab `.xlsx`? Pass `sheet_a=` / `sheet_b=` (CLI `--sheet-a/--sheet-b`); otherwise ingest
auto-picks the single data sheet, or asks you to choose.

**Day-to-day bank/GL conveniences** (column names resolve case-insensitively, so `amount`
finds a bank CSV's `Amount`):
- **Separate Debit / Credit columns** (the usual bank/GL export layout): `--debit <col>
  --credit <col>` — signed amount = debit − credit; a side without those columns just uses
  its amount column, so a debit/credit file reconciles against a signed-amount file.
- **Opposite sign conventions** (bank statement vs the GL cash account): `--flip-b` negates
  B's amounts before comparing.
- **Statement completeness**: `--opening-a/--closing-a` (and `-b`) checks opening + net
  movement = stated closing — catching a truncated or filtered export *before* it silently
  "reconciles". Result is reported in the header of the working paper.
- **Ageing**: `--as-of <date>` ages every one-sided exception with a parsed date
  (`age_days`), so stale unbanked receipts / uncleared payments rank visibly.
- An `amount_mismatch` whose gap is a common GST/VAT/WHT rate of the smaller side gets an
  advisory *net-vs-gross* hint in its probable cause (never a category change).

Messy inputs? Tidy them with **data-tidy** first, then reconcile the clean outputs.

### 3. Run it
```python
res, exceptions, summary, _ = reconcile_files(
    "tracker.xlsx", "ledger.xlsx", preset="invoice_tracker_vs_ledger",
    material=1000, escalate=10000)            # materiality thresholds (set to your policy)
write_workpaper(res, exceptions, summary, "reconciliation_[name]_[date].xlsx",
                a_label="Tracker", b_label="Ledger")
```
Or one-shot from the CLI:
`python scripts/reconcile.py A B --preset bank_vs_ledger --mode amount_date --out wp.xlsx`

### 3a. (Optional) Aggregation — sum-to-one / sum-to-sum, **confirm-first**
When one item ties to a *sum* of items on the other side (a bank receipt = several invoices), or
a *batch* on each side ties total-to-total, run a second pass over what's still unmatched. It is
**heuristic, so proposals are never auto-accepted** — present them, get the user's confirmation,
then apply only the confirmed ones. Bound the search by a **shared key + date window +
counterparty** (a subset-size cap applies underneath) to stay accurate.
```python
res, exceptions, summary, proposals = reconcile_files(
    "bank.xlsx", "ledger.xlsx", preset="bank_vs_ledger", aggregate=True,
    group_col="batch", party_col="counterparty", date_window=7)   # the constraints
print(render_proposals(proposals, a_label="Bank", b_label="Cashbook"))   # show the user
# ... the user confirms which to accept, e.g. [0, 2] ...
apply_aggregations(res, proposals, accepted=[0, 2])
exceptions, summary = finalize(res, a_label="Bank", b_label="Cashbook", material=1000)
```
Confirmed proposals become *matched (aggregated)*; the rest stay as exceptions. **Never confirm
on the user's behalf** — surface the proposed groupings (constituents + how they tie) and let them
decide. (CLI: add `--aggregate --group-col … --party-col … --date-window N`; it prints the
proposals for review — `--auto-confirm` exists for headless/testing only, not normal use.)

### 4. Read the triage, act on the reds
The working paper leads with the **answer** (RAG, % reconciled, value matched vs in exception),
then the exceptions **sorted by materiality** (escalate → material → immaterial) within category.
Each carries a **probable cause** and a **suggested action** — but the action is for a person to
take; the skill proposes, it doesn't post.

## Discrepancy Triage (the categories)

Full taxonomy + the materiality bands in `references/triage-taxonomy.md` (the artifact for
finance to red-line). In short:

| Category | Means | Typical action |
|---|---|---|
| `missing_in_B` | in A, not B (e.g. invoiced-not-booked; approved-not-paid) | investigate / post / chase |
| `missing_in_A` | in B, not A (e.g. booked-not-tracked; paid-without-approval) | investigate / record / query |
| `amount_mismatch` | matched, amounts differ | investigate the difference |
| `rounding` | differ within the rounding / FX tolerance | accept (note) |
| `sign_flip` | equal magnitude, opposite sign | correct the sign/side |
| `duplicate` | appears more than once on one side | confirm + remove |
| `timing_difference` | matches on amount, dates differ but **within** the window — in-transit / cut-off | monitor — clears next period |
| `ambiguous_match` | equal amount, dates differ **beyond** the window — possible match, possibly coincidental | confirm same item before reconciling |
| `currency_mismatch` | matched item, but the currencies differ — amounts not comparable as-is | investigate; convert at rate / fix mis-booked currency |
| `currency_unknown` | amounts tie but a side's currency is unknown (strict mode only) | establish the currency both sides, then re-run |

Materiality grades each by value: **within tolerance → immaterial → material → escalate**
(thresholds you set per run).

## Files

- `scripts/reconcile.py` — engine. Pure `match()` / `triage()` (work on parsed rows — offline,
  testable); aggregation: `propose_aggregations()` (read-only; sum-to-one + sum-to-sum, bounded
  by key/date/party), `apply_aggregations()` (applies only **confirmed** proposals),
  `render_proposals()`, `finalize()` (triage + summarise after confirmation); `reconcile_files()`
  (reads A and B in any format via the shared `ingest`/`dataclean` engine), `summarise()`,
  `render_report()`, `write_workpaper()` (.xlsx — Summary/Exceptions/Matched/Aggregations),
  `redact()` (mask parties/amounts before any artefact leaves entitled use), `catalogue_md()`,
  `PRESETS`. `--self-test` runs offline; `--catalogue` lists the presets.
- `references/triage-taxonomy.md` — the discrepancy taxonomy, materiality bands and presets —
  **read this; it's the artifact for finance to confirm against your own policy.**
- `examples/` — a worked invoice-tracker vs ledger pair (fictional) + the reconciliation output.

## Boundaries

- **Reconciliation only** — records ↔ records. **Not budget/variance** (no headroom or
  over-budget analysis), and **not deal/asset analysis** (development monitoring, capex returns
  → out of scope). It won't depend on another toolkit.
- **Drafts, not advice; never invents.** An unmatched or ambiguous item is flagged, never
  guessed into a match. The output is a first-pass working paper for a qualified person.

## Data handling

Runs **fully local** — A, B and the working paper stay in your synced or shared file store;
**nothing is sent to any external tool**. Reconciliations routinely touch bank details and
sensitive account data (esp. the fund-administrator preset) — keep it local, and
`redact()` parties/amounts before any reconciliation artefact leaves its entitled use. Full
rule: `../../DATA-HANDLING.md`.

## Feedback

Found a bug or an improvement (a new preset, a triage category)? Capture it with the toolkit's
shared format — `../../FEEDBACK.md` — and save as `feedback_data-reconcile_[date].txt`.

## Requirements & mode

Pre-screen: `../../COMPATIBILITY.md` + `python ../../scripts/envcheck.py`. Python + `openpyxl`
(for the `.xlsx` working paper and to read `.xlsx` sources); reads CSV/PDF/.docx/.msg via the
shared engine (same optional deps as `data-tidy`). Portable, fully local — no network, no
MS Office, no credentials, no connector.
