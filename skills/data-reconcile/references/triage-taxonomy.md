# Reconciliation — Discrepancy Triage taxonomy

The classification logic behind the working paper. **A best-practice draft — finance/compliance
to confirm** against your own reconciliation and materiality policy. Edit `TRIAGE`,
`PRESETS` and the materiality defaults in `scripts/reconcile.py`; this reference describes them.

> A reconciliation is a **working paper for a qualified person**, not a posting. The skill
> classifies and proposes; a person investigates and (if needed) adjusts. Unmatched items are
> **flagged, never force-fitted** into a match.

## Stage 1 — match outcomes

Each row of A is matched to B, producing one of:

| Outcome | When |
|---|---|
| **matched** | key (or amount+date) found on both sides, amounts within tolerance |
| **value differs** | matched, but amounts differ by more than tolerance → goes to triage |
| **in A only** | no counterpart in B |
| **in B only** | no counterpart in A |
| **duplicate** | the same key appears more than once on one side (extra occurrences) |
| **ambiguous** | equal amount on both sides but dates beyond the matching window — a possible match held back for confirmation |
| **currency differs** | matched on key, but the two sides are in different currencies → goes to triage (not amount-compared) |
| **currency unknown** | amounts tie but a side's currency can't be determined — held back in **strict-currency** mode (`--strict-currency`) instead of assumed compatible |

Match strategy is chosen **per run**:

- **Key** — a shared reference exists on both sides (invoice no, payment ref, transaction id).
- **Amount + date** — no clean key; match on amount (within tolerance) and nearest date **inside
  the date window** (default ±5 days). A pair within the window that differs on date is a
  **timing difference**, not a true exception. An equal-amount pair *outside* the window is held
  back as **ambiguous** (not reconciled) — so items weeks apart aren't silently tied together.

Amounts parse as exact **`Decimal`**, so a genuine tie is never split by binary-float dust at
the tolerance edge.

## Stage 2 — Discrepancy Triage

Every unreconciled item is classified on four dimensions.

### Category → probable cause → suggested action

| Category | Probable cause | Suggested action |
|---|---|---|
| **missing_in_B** | In A, not in B — unrecorded/omitted in B, or a timing/cut-off item | Investigate; record in B or chase |
| **missing_in_A** | In B, not in A — unrecorded/omitted in A, or a timing/cut-off item | Investigate; record in A or query |
| **amount_mismatch** | Matched item, amounts differ | Investigate; correct the wrong side |
| **rounding** | Differ within the rounding / FX tolerance | Accept within tolerance (note only) |
| **sign_flip** | Equal magnitude, opposite sign — debit/credit or direction error | Correct the sign / side |
| **duplicate** | Appears more than once on one side | Confirm and remove the duplicate |
| **timing_difference** | Matches on amount, dates differ but within the window — in-transit / cut-off | Monitor — expected to clear next period |
| **ambiguous_match** | Equal amount, dates differ beyond the window — possibly the same item, possibly coincidental | Confirm it's the same item before reconciling; else treat as separate |
| **currency_mismatch** | Same item on both sides, but the currencies differ — amounts not comparable as-is | Investigate; convert at the correct rate, or fix the mis-booked currency |
| **currency_unknown** | Amounts tie but a side's currency is unknown — can't confirm same money (strict-currency mode) | Establish the currency on both sides, then re-run |

*What `missing_in_B` / `missing_in_A` mean in context (set by the preset):*
- **invoice tracker vs ledger** — `missing_in_B` = invoiced-not-booked; `missing_in_A` = booked-not-tracked.
- **payments vs bank** — `missing_in_B` = approved-not-paid; `missing_in_A` = **paid-without-approval** (flag).
- **bank vs cashbook** — typically `timing_difference` (in transit) until the item clears.

### Materiality bands (set the thresholds to your policy)

| Band | Rule (default) | Treatment |
|---|---|---|
| within tolerance | ≤ rounding tolerance (default 0.05) | auto — not raised as an exception (rounding only) |
| immaterial | < material threshold (default 1,000) | note; clear in bulk |
| material | ≥ material, < escalate (default 1,000–10,000) | investigate before sign-off |
| escalate | ≥ escalate threshold (default 10,000) | escalate to the reviewer / FD |

Exceptions are sorted **escalate → material → immaterial**, largest first, so the reds surface.
The overall RAG is **GREEN** (nothing open), **AMBER** (only immaterial open) or **RED** (any
material/escalate open).

## Aggregation matching (sum-to-one / sum-to-sum) — confirm-first

A **second pass** over what's still unmatched after 1:1, for when one item ties to a *sum* of
items on the other side, or a *batch* ties total-to-total:

- **one_to_many / many_to_one** — one item = a subset of items on the other side (a bank receipt
  = several invoices). Found by bounded subset-sum.
- **many_to_many** — a group on each side ties sum-to-sum (a payment run, a batch).

**Heuristic → never auto-accepted.** A subset can sum to a total by coincidence, so the engine
**proposes**; a person **confirms**; only confirmed proposals become *matched (aggregated)*. The
rest stay as exceptions. The search is **bounded** — by a shared reference/batch key, a date
window (±N days), and/or counterparty, plus a subset-size cap — both to stay tractable and to cut
coincidental matches. The tighter the constraints, the fewer false proposals to review.

## Presets (common recurring reconciliations)

Generated from `PRESETS` in the script — `python scripts/reconcile.py --catalogue`:

| Preset | A vs B | Default match | Note |
|---|---|---|---|
| `invoice_tracker_vs_ledger` | Tracker vs Ledger | key on invoice no | completeness: tracked ↔ booked both ways |
| `bank_vs_ledger` | Bank vs Cashbook | amount + date | un-cleared = timing until it clears |
| `fa_vs_internal` | FA vs Internal | key | outsourced-admin check; sensitive data — keep local |
| `payments_vs_bank` | Approved vs Bank | key on payment ref | approved-not-paid / paid-without-approval |

All presets are **defaults only** — override the key, columns, mode and thresholds per run.
Anything not listed is handled generically (specify the columns and match strategy).

## Out of scope (by design)

- **Budget / variance** — no headroom, over-budget or budget-vs-actual analysis. A budget is
  only ever reconciled as another record set (does each line match), never assessed for variance.
- **Deal / asset analysis** — development monitoring, capex returns and the like are
  **out of scope**; this skill reconciles finance records to finance records.
