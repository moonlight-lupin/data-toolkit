# data-toolkit benchmark — Claude Sonnet 5, with vs without skills

**Date:** 14 Jul 2026 · **Toolkit under test:** [moonlight-lupin/data-toolkit](https://github.com/moonlight-lupin/data-toolkit) **v0.4.3** (Apache-2.0, Phronesis Applied) · **Test model:** Claude Sonnet 5 (`claude-sonnet-5`) · **Orchestration/evaluation:** Claude Fable 5 · **Status:** published 16 Jul 2026

---

## 1. Verdict up front

Six tasks, each run by a Sonnet 5 agent twice — once following the toolkit's skills, once with plain Python — against synthetic fixtures with planted traps and recorded ground truth.

1. **Correctness: parity on headline numbers.** Both arms produced substantively correct outputs on every task. A well-prompted Sonnet 5 without the toolkit matched the toolkit's figures at ordinary sizes.
2. **Quality: the skill arm produced the stronger artefacts** — a reconciliation working paper in a standard taxonomy with materiality/RAG grading, an insight brief with dual-lens disclosure, a branded print-ready dashboard — where the baseline produced good but bespoke one-off formats. Rubric: 50/50 vs 48.5/50.
3. **Cost at ordinary sizes: the toolkit costs more** — +45% tokens on the five small-data tasks, driven by reading skill documentation and engine source before working.
4. **Cost at scale: the economics invert.** On the scaling test (the same reconciliation at ~85 / ~5,000 / ~20,000 rows per side), the skill arm's cost is essentially **flat** across a 235× size increase, while the baseline's grows: from ~5,000 rows the skill arm is **~25% cheaper on tokens and ~3× faster**.
5. **Risk: the baseline's error surface grows with data size; the engine's doesn't.** Every baseline error was self-caught in these runs, but they included a matcher that began force-pairing unrelated items and a real formula bug in a delivered workbook — precisely the failure class a tested deterministic engine removes.

**One caveat before generalising:** to keep the comparison fair, both arms received the same intent context and integrity rules ("flag, don't guess"; "be careful how you total"; the ±5-day window). Those rules are much of what the skills encode, so this design measures the toolkit's *mechanical* value floor and likely **understates** its value in everyday unscaffolded use, where the skills carry that discipline by default.

---

## 2. Method

- One task per skill (T1–T5) plus a scaling test (T6). Each task ran twice: **WITH-SKILL** (agent pointed at the toolkit's `SKILL.md`, told to follow its workflow and engine) and **BASELINE** (standard Python only; skills/toolkits forbidden).
- **Identical prompts** between arms apart from that one instruction block. Both arms got the same intent/context (audience, purpose, target shape — standing in for the skills' "intent-first" questions, since runs were non-interactive), the same integrity rules, the same environment note, and the same required output format (RESULTS / EXECUTION LOG / FILES) so error reporting was comparable.
- Agents ran in parallel from shared read-only fixtures into isolated output folders.
- Every deliverable was **independently verified** against ground truth by the orchestrator (`verify_outputs.py` — re-summing workbooks, re-counting exception categories, grepping dashboards for external references, checking briefs for the planted findings). Agents' self-reports were not trusted for scoring.
- Environment: Windows 11, Python 3.14, openpyxl / PyMuPDF / python-docx / extract_msg installed (pandas also present; one baseline run used it). pdfplumber and Tesseract absent (not needed). Toolkit lint and engine self-tests green before testing.
- During early testing, four engine issues were found, reported upstream in the toolkit's own feedback format, and **fixed by the maintainer in v0.4.3** (commit `4e6e266`, with self-tests added for the exact repro scenarios). All results below are against v0.4.3; the fixes were independently verified against the repro fixtures.

## 3. Fixtures — synthetic, with planted traps and recorded ground truth

All data fictional, generated deterministically (`make_fixtures.py`, `make_fixtures_t6.py`); ground truth in `ground_truth/*.json`.

| Test | Skill | Fixture | Planted traps |
|---|---|---|---|
| T1 | data-tidy | 43-row messy payments CSV | 3 junk header rows; 3 mixed date formats; 2 exact duplicates; a mid-table TOTAL row; `pending`/blank amounts (must flag, never guess); £ embedded in Amount with blank Currency; country spelling variants; stray whitespace |
| T2 | data-extract | 6 subscription-confirmation PDFs | One document has **no Close Date** (must be left blank + flagged); mixed GBP / S$ / USD commitments; label-value layout |
| T3 | data-reconcile | Bank CSV (Debit/Credit) vs cashbook XLSX (signed), ~85 rows/side | No shared key (amount+date matching); 33 exact matches; 3 timing differences (3–5 days); 1 equal-amount pair **12 days** apart (must be flagged, not matched); 1 sign flip; 1 cashbook duplicate; 2 bank-only; 2 cashbook-only; 1 amount gap of exactly **9% GST** |
| T4 | data-analyse | 287-row sales CSV, 14 months | Mixed GBP/USD amount column (must not be blindly summed); zero-invoice **gap month**; a 250,000 outlier (~125× median); 53.6% single-customer concentration; 3 blank amounts |
| T5 | data-visualise | Clean 3-sheet metrics XLSX | Self-containment (no CDN/external refs), 4 KPIs with known values, RAG status table, print CSS, as-of stamp, draft footer |
| T6 | data-reconcile (scaling) | Same task as T3 at **~5,000** and **~20,000 rows/side** | Same taxonomy scaled: 70 exceptions hidden among 4,910 matchable pairs (5k); 130 among 19,880 (20k) |

## 4. Results — correctness and quality

Rubric per task (max 10): correctness vs ground truth (5) · traps caught (2) · auditability/transparency (2) · deliverable polish (1).

| Test | WITH skill | BASELINE | Quality edge | Notes |
|---|---|---|---|---|
| T1 tidy | 10 | 10 | Tie | Identical row counts, per-currency sums, dedup, standardisation in both. Baseline proved DD/MM date order from an unambiguous date and reconciled the planted TOTAL row against the true sum; skill arm carried a reproducible recipe + engine change log. |
| T2 extract | 10 | 10 | Tie | Identical substance: all fields correct, the missing Close Date blank + flagged in both, S$→SGD normalised in both. |
| T3 reconcile | 10 | 9.5 | **Skill** | Both classified all eight planted discrepancy types, including the 9% GST hint and refusing the 12-day "match". The skill working paper is the stronger artefact: standard taxonomy, materiality bands, RAG, value-matched statistics. Baseline's control-total tie-out was excellent practice. |
| T4 analyse | 10 | 9.5 | **Skill** | Both caught concentration, outlier, gap month, currency mix, blanks. The skill brief reported both outlier-inclusive and exclusive totals/shares; the baseline led with one lens (disclosed). |
| T5 visualise | 10 | 9.5 | **Skill** | Both dashboards pass every check (correct KPIs, zero external references, print CSS, stamp, footer). The skill output is branded and print-first; the baseline burned ~5 minutes attempting a browser preview against an explicit instruction. |
| **Total** | **50/50** | **48.5/50** | | |

Headline numbers were identical between arms on every task (e.g. T1: GBP 115,173.00 / USD 5,803.75; T3: 37 matched with the same eight exception classifications; T5: all four KPI values).

## 5. Time and token spend (T1–T5, ordinary sizes)

Figures as reported by the agent harness (subagent tokens ≈ total tokens consumed by that agent; duration = wall-clock).

| Test | Tokens WITH | Tokens BASE | Δ tokens | Time WITH | Time BASE | Δ time |
|---|---|---|---|---|---|---|
| T1 tidy | 141,236 | 67,230 | +110% | 7m 12s | 3m 04s | +135% |
| T2 extract | 71,594 | 55,330 | +29% | 2m 27s | 1m 59s | +23% |
| T3 reconcile | 78,182 | 81,757 | **−4%** | 3m 23s | 5m 28s | **−38%** |
| T4 analyse | 100,550 | 70,881 | +42% | 4m 31s | 3m 12s | +41% |
| T5 visualise | 94,696 | 59,932 | +58% | 2m 37s | 7m 14s † | −64% † |
| **Total** | **486,258** | **335,130** | **+45%** | 20m 10s | 20m 57s † | −4% † |

† The T5 baseline includes a ~300 s self-inflicted browser-preview timeout; excluding T5, the skill arm was ~28% slower overall on these small datasets.

**Where the overhead goes:** reading `SKILL.md` + references + engine source before starting, and environment pre-checks. The overhead is a fixed per-task cost — which is exactly why it amortises at scale (§6).

## 6. Scaling test (T6) — the gap inverts as data grows

**Hypothesis:** the skill arm's overhead should shrink and eventually invert as datasets grow, because the deterministic engine's cost is fixed while hand-rolled matching logic gets harder to design, debug and verify as the data grows.

Same reconciliation task at three sizes, both arms. All six runs produced substantively correct working papers — every planted category recovered at every size, no force-fitted matches, row accounting tying out exactly (130 planted discrepancies among 40,000 rows all found and classified).

| Rows/side | Tokens: skill | Tokens: base | skill ÷ base | Time: skill | Time: base | skill ÷ base |
|---|---|---|---|---|---|---|
| ~85 | 78,182 | 81,757 | 0.96 | 3m 23s | 5m 28s | 0.62 |
| ~5,000 | 105,060 | 140,162 | **0.75** | 4m 05s | 13m 13s | **0.31** |
| ~20,000 | 158,618 ‡ (79,159 pre-stop) | 110,683 | 1.43 ‡ (≈0.72 excl. anomaly) | ≈4m 00s active ‡ | 10m 34s | **0.38** |

‡ The 20k skill agent hit a process anomaly unrelated to the toolkit: it backgrounded the engine run and stopped its turn to "wait", needing an orchestrator resume that re-reads its whole transcript (double-counting context tokens). Its pre-stop figure — with the engine run already complete — is the cleaner estimate; both are reported.

**Findings:**

1. **Time: confirmed, strongly.** Skill wall-clock is essentially flat across a 235× size increase (3.4 → 4.1 → ~4.0 min): the engine absorbs the scaling inside one command (123 s of compute at 20k×20k). Baseline time roughly doubles (5.5 → 13.2 → 10.6 min), spent building and debugging bespoke matchers. From ~5,000 rows the skill arm runs in roughly a third of the baseline's time.
2. **Tokens: confirmed with a caveat.** Parity at 85 rows (0.96) → clear skill advantage at 5k (0.75); the 20k point is contaminated by the anomaly, though the pre-stop figure suggests ~0.72. The mechanism is visible either way: skill-arm tokens are **size-independent** (the agent reads the same docs and writes the same ~10-line driver whether n = 85 or 20,000), while baseline tokens buy matcher-building that grows with the data.
3. **The unplanned third finding: the baseline's error surface grows with size.** Skill arm: zero engine errors at every size. Baseline arm: 1 self-caught bug at 85 rows → 3 at 5k — including a near-miss where a fuzzy amount-mismatch heuristic began **force-pairing unrelated items** (~1.3% apart by coincidence) and had to be patched with a bespoke narrative-token check → 2 at 20k, including a **real formula bug in the delivered summary sheet**, caught only on self-review. Bigger data means more coincidental near-collisions — the failure class a tested deterministic engine removes.
4. Baseline effort is visible in tool calls too: 16 → 40 → 27 across the sizes, vs the skill arm's stable 18–24.

## 7. Errors encountered and how the agents resolved them

Every error in both arms was self-diagnosed and resolved; no run failed or delivered a known-wrong result, and no arm ever invented a value to get unstuck.

**With-skill arm (v0.4.3):** zero engine/toolkit errors across all eight runs. Remaining incidents were minor agent-side slips: one agent's report draft mis-stated flag counts and was corrected against the raw data before delivery (T1); two trivial probe mistakes (a read-only worksheet attribute; a module import path) fixed in seconds (T6L); and the T6L premature stop described in §6.

**Baseline arm:** the errors were the classic hand-rolled-logic risks — a matcher pass that paired leftovers by nearest date regardless of amount (T3, caught via a control-total tie-out); the T6M force-pairing near-miss and the T6L summary-sheet formula bug (§6); plus environment friction (a `python3` Windows Store stub; console codepage mangling of `£`/`±`, display-only) and the T5 browser-preview detour.

**Toolkit issues found and fixed during testing:** four engine findings from early runs — a silent date-window bypass in reconcile's amount_date mode when no date column resolves (the one silent-wrong-answer path found); missing duplicate/sign-flip/amount-mismatch triage in that mode; a currency-typed extract field discarding the detected code; and a tidy recipe losing a row's Currency when its Amount was unparseable — were reported upstream and fixed in v0.4.3, which now warns / triages / carries the code through. The fixes were verified directly against the repro fixtures. That the maintainer turned filed findings into a released, self-tested fix the same day is a good signal for the toolkit as a dependency; that the test agents diagnosed and worked around every gap using the engine's own primitives speaks well of its architecture (small, composable, readable functions).

## 8. Ranked quality of outputs (T1–T5)

1. **T3 skill** — working paper in a standard taxonomy with materiality, RAG, probable causes, value statistics; an artefact a reviewer could sign off against policy.
2. **T4 skill** — dual-lens totals and concentration, calibrated language, engine-computed figures, honest note that the automated quality score cannot catch outliers/concentration.
3. **T3 base** — same classifications plus an exact control-total tie-out; formatting a notch simpler.
4. **T4 base** — all findings present; single-lens headline (disclosed).
5. **T5 skill** — branded, print-first, self-contained, correct.
6. **T5 base** — correct and self-contained; plainer, with a process wobble.
7. **T1 skill / T1 base** (near-tie) — both flawless on substance; pick by what you value: sharp one-off insight (base) or a reproducible recipe + engine log (skill).
9. **T2 skill / T2 base** (tie) — identical substance; both flagged the missing field rather than inventing it.

## 9. Limitations

- **n = 1 per cell.** Single run per task/arm; agent variance is real (visible in T1/T5). Treat deltas under ~10% as noise; the scaling *trend* rests on three points per arm.
- **Prompt scaffolding favoured the baseline** (§1 caveat). The unscaffolded gap is plausibly larger and in the toolkit's favour.
- **Sonnet 5 is a strong baseline model.** On a weaker model the deterministic engine should matter more; this benchmark cannot confirm that extrapolation.
- **No scanned-PDF/OCR, `.msg` or `.docx` inputs tested** (Tesseract absent; scope kept to the common paths).
- **Token figures** are harness-reported subagent totals (reading + thinking + output). The T6L 20k skill token figure carries the anomaly noted in §6.
- Reuse runners (`emit_runner`), aggregation proposals, presets and the white-label theming were not exercised.

## 10. Conclusion

For small one-off files, a strong model with a careful prompt matches the toolkit's correctness, and the toolkit's fixed overhead (+45% tokens here) buys artefact standardisation, fuller disclosure and a deterministic audit trail rather than better numbers. **From roughly 5,000 rows the trade inverts: the skills are cheaper, ~3× faster, and flat-cost as data grows, while the hand-rolled alternative gets slower and — more importantly — riskier, with an error surface that grows with the data.** For recurring or high-volume data work, the deterministic engine is both the cheaper and the safer path; the skills' reuse bundles (not tested here) would push the marginal cost lower still.

---

## 11. Addendum — T7: repeat conversion (data-convert), closing off the Sonnet rounds

The toolkit later added a sixth skill, **data-convert** (v0.5.x), tested with a three-leg recurring-conversion design: **June** builds a GL-export → journal-import conversion to a defined contract and saves a reusable artefact with standing rules; **July** is a clean repeat run by a *fresh* agent told only "convert as June was done — check the working folder first"; **August** is a drifted repeat (renamed column, new column, one blank required AccountCode; ground truth: drift flagged, 113 rows, sum −317.85). Run on toolkit **v0.5.3**, which added `on_missing_required: exclude/error/flag` enforcement and mandatory Standing-rules card sections — both added by the maintainer in response to feedback from this benchmark's smaller-model round (see REPORT_HAIKU.md §5).

| Leg | Skill | Baseline |
|---|---|---|
| June (build) | ✓ 120 rows, sum 0.00; card carries the exclusion policy in the machine spec (96.3k tok / 3m 21s) | ✓ 120 rows; self-built runner enforcing required-exclusion in code (58.0k / 2m 22s) |
| July (repeat) | ✓ card reused unchanged; 118 rows (60.6k / 1m 55s) | ✓ runner reused unchanged; 118 rows (57.6k / **46s** — cheapest leg of the benchmark) |
| August (drift) | ✓ drift flagged; invalid row **excluded by the engine** — 113 rows, sum −317.85, exact ground truth; renamed non-required column conservatively left blank pending confirmation (83.6k / 2m 59s) | ⚠ runner **halted the entire run** (SchemaError, failure log, no CSV) and deferred to human confirmation (64.0k / 3m 13s) |

Findings: repeat conversions cost ~1–2 minutes in both arms once a good artefact exists; the August drift produced a spectrum of *defensible* conservatism (halt entirely → deliver-with-exclusions-and-questions → deliver-with-disclosed-remap on the smaller-model round) with **no run on any tier silently converting**; and the v0.5.3 card policy makes the required-field rule mechanical rather than judgement-dependent — which is what makes the repeat legs safe to delegate.

A full companion round on **Claude Haiku 4.5** (same T1–T7 including scaling, plus guard-rail experiments and two further found→filed→fixed toolkit issues) is in **REPORT_HAIKU.md** in this bundle.

*All figures are reproducible from the artefacts in this folder: fixtures, ground-truth JSON, the deterministic generators and `verify_outputs.py`, per-run metrics, and the T1–T5 / T7 deliverables. The large T6 scaling fixtures and workbooks are omitted for size — regenerate the inputs with `scripts/make_fixtures_t6.py` (see [`README.md`](README.md)).*
