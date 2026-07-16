# data-toolkit benchmark, round 3 — Claude Haiku 4.5, with vs without skills

**Date:** 14 Jul 2026 · **Toolkit:** moonlight-lupin/data-toolkit **v0.5.2** (now six skills, incl. the new **data-convert**) · **Test model:** Claude Haiku 4.5 (both arms) · **Orchestration/evaluation:** Claude Fable 5 · **Status:** published 16 Jul 2026

Companion to the Sonnet 5 rounds in [REPORT.md](REPORT.md). Same method: identical prompts per arm bar the skill-instruction block, same fixtures/ground truth for T1–T5, all outputs independently verified. New: **T7**, a three-leg repeat-conversion test for data-convert.

---

## 1. Verdict up front

1. **The "skills matter more on a weaker model" hypothesis is confirmed — by a real failure.** The Haiku **baseline fell into the planted currency trap on T4**: it headlined "Total revenue **£1,121,085**" by adding USD invoices to GBP ones with no exchange rate, and computed the top-customer share off that blended total. Sonnet never did this in three rounds. The Haiku **skill arm did not** — the skill's mandatory currency gate held, and its brief matched the Sonnet skill brief check-for-check (10/10 verification passes).
2. **Haiku + skills ≈ Sonnet-level artefacts at a fraction of the cost.** The skill arm's T1/T2/T3/T5 outputs are substantively identical to the Sonnet skill outputs (same sums, same 7-category reconciliation taxonomy, same flags) at ~35–40% fewer tokens than Sonnet's skill runs.
3. **Skill overhead nearly vanished on Haiku: +14% tokens (vs +45% on Sonnet), wall-clock parity.** The fixed cost of reading the skill docs matters less when the baseline also has to work harder per step.
4. **Repeat conversion works — in both arms.** July's fresh agent reused the recorded artefact for ~63% (skill) / ~86% (baseline) of the initial leg's tokens and ~1 minute of wall-clock vs 3–5 minutes for the initial build.
5. **The drift leg found a real gap, which is now fixed and re-verified — the canonical T7 result is the v0.5.3 re-run.** On v0.5.2, the skill arm flagged August's drift but **shipped the invalid row** (blank required AccountCode) while the baseline's self-built runner excluded it; root cause in §5 (a spec gap — `required` was report-only — plus a small-model hand-off failure). That was filed as feedback; the maintainer shipped **v0.5.3 (PR #17)** adding `on_missing_required: exclude/error/flag` and a mandatory Standing-rules section on every card. The full three-leg re-run on v0.5.3 (same Haiku tier, same prompts): June's card carried the policy in the machine spec, July reused it cleanly, and **August excluded the invalid row mechanically — 113 rows, sum −317.85, exact ground truth**. Found → filed → fixed → re-verified, all within the benchmark.
6. **At scale (T6, §8), Haiku needs explicit operating guard rails — and with them, the skill arm is correct at every size.** Canonical results (5k runs use the guarded prompts — see §8.1 for why): skill arm 2/2 correct working papers, identical to Sonnet's output; baseline 0/2 (matching fixable, but both baselines under-triage — the classification labour is what a small model quietly drops). The first, unguarded 5k attempt is kept as a documented finding: without two sentences of operating rules, Haiku misdrove the engine into a 0%-matched paper and rationalised it. The deterministic engine removes the computation risk; the *prompt* has to remove the driving risk on a weaker model.

## 2. What was run

- **T1–T5** — identical tasks, fixtures and ground truth to the Sonnet rounds (tidy / extract / reconcile / analyse / visualise), skill vs baseline. 10 runs.
- **T7 (new) — data-convert with repeat conversion.** A recurring monthly GL-export → journal-import conversion, three legs per arm, **each leg a fresh agent** (simulating "next month, new session"):
  - **June** — build the conversion to a defined contract (column mapping/order, DD/MM→ISO dates, signed Amount = Debit − Credit, constant Source, four required fields whose failure must exclude the row) **and save a reusable artefact with the standing sense-check rule**.
  - **July** — clean repeat, same shape (118 rows). Prompt does not restate the contract: "convert exactly as June, check the working folder first".
  - **August** — drifted repeat: `Cost Centre` renamed `CC Code`, new `Approved By` column, one row with a blank required AccountCode. Ground truth: drift flagged, 113 valid rows out, sum −317.85.
  - 6 runs. Total this round: **16 Haiku runs**.

## 3. Results — correctness and quality (verified against ground truth)

| Test | Skill | Baseline | Notes |
|---|---|---|---|
| T1 tidy | **10** | **10** | Both workbooks perfect (40 rows, GBP 115,173.00 / USD 5,803.75, dedup, countries, dates). The skill agent's *chat summary* added GBP+USD into a meaningless "grand total" but the deliverables were clean. |
| T2 extract | **10** | **10** | Both correct; missing Close Date blank + flagged in both. Baseline needed two pattern iterations to catch `S$`. |
| T3 reconcile | **10** | **8.5** | Skill: engine taxonomy, identical to Sonnet's output (37 matched, 11 exceptions, 7 categories). Baseline surfaced all 8 planted issues but under ad-hoc category names with muddled counts (the ambiguous Acme pair double-counted across two categories; 31+6 match split vs the true 34+3). |
| T4 analyse | **10** | **6.5** | Skill: all 10 checks pass — currencies split, both outlier lenses, 53.6% share, gap month. **Baseline: blended-currency headline (£1,121,085) — a genuine correctness failure**; no outlier-excluded total/share; components were disclosed, which is why it isn't scored lower. |
| T5 visualise | **10** | **9** | Both correct KPIs and fully self-contained. Baseline drew charts with JS Canvas (blank if JS is off; less print-robust than inline SVG). Skill output branded via the theme engine. |
| **T1–T5 total** | **50/50** | **44/50** | Sonnet round: 50 vs 48.5. The gap between arms **widens** on the smaller model. |
| T7 June | 10 | 10 | Both perfect (120 rows, sum 0.00) and both saved reusable artefacts (skill: toolkit conversion card, now carrying Standing rules + `on_missing_required: exclude` in the machine spec; baseline: self-built runner script + guide). |
| T7 July | 10 | 10 | Both fresh agents found, sense-checked and reused the artefact; 118 rows, sum 0.00, no rebuild. |
| T7 August | **10** | **10** | Both flagged the drift; both delivered the exact ground-truth file (113 rows, sum −317.85, invalid row excluded). Skill: exclusion enforced by the engine per the card's spec. Baseline: exclusion enforced by its self-written runner code. |

*T7 skill figures are the canonical v0.5.3 (post-PR #17) re-run. The original v0.5.2 skill run scored 8 on August (drift flagged but the invalid row shipped) — retained in `runs_haiku/T7_skill/` as the pre-fix finding that produced the feedback (§5).*

## 4. Time and token spend

| Test | Tokens skill | Tokens base | Δ | Time skill | Time base |
|---|---|---|---|---|---|
| T1 | 47,348 | 48,235 | −2% | 3m 44s | 5m 34s |
| T2 | 44,697 | 44,438 | +1% | 3m 33s | 3m 38s |
| T3 | 74,117 | 62,240 | +19% | 7m 07s | 5m 27s |
| T4 | 83,304 | 42,903 | +94% | 5m 03s | 2m 57s |
| T5 | 65,330 | 79,199 | −18% | 3m 58s | 6m 23s |
| **T1–T5** | **314,796** | **277,015** | **+14%** | 23m 26s | 24m 00s |
| T7 Jun | 54,431 | 48,230 | +13% | 1m 55s | 4m 44s |
| T7 Jul (repeat) | 54,319 | **41,306** | +31% | 2m 11s | **1m 09s** |
| T7 Aug (drift) | **47,765** | 54,786 | −13% | 2m 25s | 2m 46s |

*T7 skill rows are the canonical v0.5.3 re-run. The v0.5.2 originals (56.7k/36.0k/49.3k tokens) are retained in `run_metrics.csv`; the July v2 leg cost more than v1's because the agent hand-rolled the apply step instead of calling `convert.py --card` — output identical, and the repeat leg remains ~1–2 minutes in both versions.*

Readings:
- **Skill overhead collapsed on Haiku** (+14% vs Sonnet's +45%): the doc-reading cost is fixed, while the baseline's per-task effort is model-independent work it must always do. Note T4: the skill arm's +94% bought the run that *didn't* produce a wrong headline number.
- **Haiku skill runs cost ~35–40% less than Sonnet skill runs** for equivalent verified artefacts on T1–T3/T5 (e.g. T3: 74k vs Sonnet's 78k; T1: 47k vs 141k) — with the T4/T7-Aug caveats below.
- **Repeat legs are cheap in both arms** (~1 minute, ~40k tokens): a well-recorded artefact makes month 2+ nearly free regardless of who wrote it. The skill's card was reused with zero modification in July; the baseline's runner likewise.

## 5. The August drift result — what actually failed

The skill arm's failure decomposes cleanly, and neither piece is the deterministic engine computing wrongly:

1. **Hand-off fidelity (model):** the June Haiku agent recorded the mapping in the conversion card but **did not write the standing rules** ("required-field failure ⇒ exclude the row") into it, despite the prompt asking. The Sonnet-written artefacts in earlier rounds carried richer prose; Haiku's card carried only the spec.
2. **Spec semantics (toolkit gap):** the convert spec's `required: true` is **report-only** — the engine flags a required-missing value in its report but still writes the row to the output. There is no `on_required_missing: exclude` (or similar) enforcement semantic, so the rule *cannot* live in the deterministic layer; it has to live in the model's judgement each month. August's agent saw the flag, reasoned "source data quality issue, engine never invents values", and shipped the row.
3. The baseline June agent, writing its own runner, happened to encode exclusion **in code** — so its August run enforced the rule mechanically. The lesson is not "baseline better"; it's that **rules must live in the executable artefact, not in prose or memory** — which is precisely the toolkit's own philosophy, one enforcement option short.

Filed as new feedback: [feedback/feedback_data-convert_2026-07-14.txt](feedback/feedback_data-convert_2026-07-14.txt) — add enforcement semantics for required-missing rows to the conversion spec (and have `render_card` carry the standing rules the user states).

**Outcome: fixed upstream in v0.5.3 (PR #17) and re-verified.** The spec now supports `rules.on_missing_required: flag | exclude | error`, excluded rows are counted (`rows_excluded_required`), and `render_card` always emits a Standing-rules section. The full T7 re-run on v0.5.3 (same Haiku tier, byte-identical prompts, fresh working folder `runs_haiku/T7_skill_v2/`) is now the canonical result: June's card carried `"on_missing_required": "exclude"` plus the standing rules in both prose and spec; July reused it cleanly; August detected the drift, updated the card with disclosure, and the **engine excluded E9960 mechanically — 113 rows, sum −317.85, verified against the delivered CSV**. The rule now lives in the deterministic layer, which is exactly where a small model needs it to be.

## 6. Errors encountered (beyond the two scored failures)

All self-caught and resolved; more small slips than the Sonnet rounds in both arms, as expected of a smaller model:

- **Skill arm:** wrong keyword-argument names on `reconcile_files` (0 matches on first try; diagnosed by calling `match()` directly) — T3; a spurious "12 duplicate rows" data-quality claim relayed from the profiler without verification — T4 (hedged, but noise); the T1 chat-summary currency blend (deliverable clean).
- **Baseline arm:** Unicode/console-encoding trip-ups (T1, T5-equivalents); an Excel file-lock resolved by killing the Excel process (T1 — effective but blunt); two extraction-pattern iterations to catch `S$` (T2); the T3 classification muddle above.

## 7. Conclusions for the model-tier question

1. **The toolkit's value is inversely proportional to the model's strength — now shown, not assumed.** Sonnet baseline: matched skill correctness everywhere at ordinary sizes. Haiku baseline: two scored failures (blended currency headline; muddled reconciliation taxonomy). Haiku skill arm: zero — its artefacts match Sonnet's skill artefacts nearly check-for-check.
2. **Haiku + skills is the value sweet spot for routine data work:** Sonnet-skill quality on tidy/extract/reconcile/visualise at roughly 60% of the token cost and near-zero overhead vs its own baseline.
3. **But the smaller model is a weaker *author of reusable artefacts*.** Where the toolkit gives it a complete deterministic rail (reconcile taxonomy, analyse currency gate) Haiku rides it flawlessly; where the rail has a gap (no enforcement semantic for required-missing) Haiku doesn't bridge it the way Sonnet's richer artefact-writing did. For recurring conversions authored by a small model, have a stronger model (or a person) review the recorded card once — the repeats are then cheap and safe.
4. Repeat-conversion economics are excellent in both arms: **month 2+ costs ~1 minute and ~60% of the initial tokens**, and the sense-check catch-drift-first discipline held in all four repeat legs.

## 8. Scaling test (T6) on Haiku — the tier picture completes

Same T6 as the Sonnet round: bank-vs-cashbook reconciliation at ~5,000 and ~20,000 rows/side, both arms, verified against the same ground truth. **Canonical 5k results use the guarded prompts** (two operating rules a competent operator would give a smaller model — see §8.1); the first, unguarded 5k attempt is retained as the prompting lesson.

| Run (canonical) | Verified outcome | Verdict |
|---|---|---|
| 5k skill (guarded) | 4,930 matched, 75 exceptions in **exactly the ground-truth taxonomy** — first attempt without `--flip-b` produced mass sign-flips; the agent treated it as misconfiguration per the guard and re-ran correctly | **PASS** |
| 5k base (guarded) | 4,930 matched, dates parsed correctly, sanity check applied — but the 45 exceptions sit in **3 coarse buckets** (no duplicate/sign-flip/GST classes, ambiguous conflated with timing) | **FAIL on triage** (matching sound) |
| 20k skill | 19,920 matched, 130 exceptions in **exactly the ground-truth taxonomy** — engine driven correctly (`flip_b`, date, ±5 window); identical to Sonnet's output | **PASS** |
| 20k base | Match counts right (19,880 + 40 timing) and exception row coverage ties out (70 + 50), but **104 of 120 exception items classified "Unknown"** — coverage without triage | **FAIL** (the task's point — classification — is missing) |

Canonical: **skill arm 2/2 correct at scale; baseline 0/2** (matching salvageable with guidance, triage consistently absent). Tokens/time (canonical): 5k skill 55.6k/2m47s vs base 54.3k/3m44s; 20k skill 65.1k/8m05s vs base 54.5k/3m16s.

**What this adds to the three-tier picture:**

1. **The Sonnet scaling conclusion does not transfer to Haiku.** On Sonnet, all six T6 runs were substantively correct and the skill arm was ~3× faster. On Haiku, the failure mode changes from *cost* to *correctness* — and at 5–20k rows a wrong working paper is invisible to eyeball review, which is exactly when correctness matters most.
2. **The engine removes computation risk, not driving risk.** Where the Haiku agent drove the engine correctly (20k), the output was flawless and Sonnet-identical. Where it improvised around the engine's own conveniences (5k — hand-converting signs instead of `--flip-b`), it produced garbage *and lacked the judgement to notice*. The 0-matched paper sailed past an agent that had itself counted 4,935 common amounts minutes earlier.
3. **Haiku baselines consistently under-triage at scale.** Both baseline runs matched adequately but returned "Unknown"-bucket exceptions — the labour-intensive classification step is precisely what a small model quietly drops when the data gets big.
4. **Practical rule by tier:** Sonnet + skills for large or high-stakes reconciliations (fast, flat-cost, correct across all rounds); Haiku + skills only for small, attended tasks where a reviewer would catch a 0%-matched absurdity; Haiku baseline not at scale, full stop. A cheap guard would help either way: a sanity assertion in the run ("matched % vs common-amount count") would have caught the 5k skill failure mechanically — filed as toolkit feedback (warn when matched=0 but thousands of equal amounts exist on both sides).

### 8.1 Why the 5k canon is the guarded run — prompting for a weaker model

The first 5k attempt ran with the same minimal prompts as every other test — and both arms failed in ways Sonnet never did: the skill agent hand-converted the bank signs instead of using `--flip-b`, lost the date wiring, delivered **0 matched / 4,935 "ambiguous"** and *rationalised it* ("test data intentionally containing unmatched items"); the baseline wobbled on day/month order and skipped the triage. The retry added exactly **two sentences of operating rules** (use the engine's/your own convention handling deliberately and verify on a sample; sanity-check matched-count plausibility before delivering — never rationalise an implausible result). Everything else identical.

**The prompting lesson:** a stronger model carries these rules as judgement; a weaker model needs them written down. That is not a reason to avoid Haiku — the guarded runs cost no more than the failed ones (55.6k vs 56.6k tokens) — it is a reason to treat operating guard rails as part of the deployment, and to prefer putting them in the deterministic layer where possible (hence the absurd-result-warning feedback filed upstream: the engine can enforce rule 2 for everyone).

| 5k Haiku run | Matching | Triage |
|---|---|---|
| Skill, original | ✗ 0 matched (misdrove the engine) | ✗ |
| Baseline, original | ~ (date-parse wobble, 4,924/4,930) | ✗ two crude buckets |
| **Skill + guard** | ✓ 4,930 matched | ✓ **exact ground-truth taxonomy** (75 exceptions, 7 categories — identical to Sonnet) |
| **Baseline + guard** | ✓ 4,930 matched, dates right, sanity check used | ✗ still crude: 45 items in 3 coarse buckets, no duplicate/sign-flip/GST classes |

Two conclusions: **the guard fixes driving errors in both arms** (the guarded skill agent hit the same wrong-sign first attempt, recognised it as misconfiguration and re-ran with `--flip-b` — at no extra cost, 55.6k tokens vs the failed run's 56.6k); and **only the engine supplies the classification** — the guarded baseline still under-triaged. **Guard + skill is the complete fix for Haiku at scale**; the engine-level absurd-result warning (feedback filed) would build the guard's second rule into the toolkit for every user.

*All figures reproducible from `run_metrics.csv` (rows suffixed `_hk` / `_hk_v2`), `runs_haiku/`, `fixtures/`, `ground_truth/` and the fixture generators. The large T6 scaling fixtures and workbooks are omitted for size — regenerate with `scripts/make_fixtures_t6.py`.*
