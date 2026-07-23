# data-toolkit benchmark — skills vs baseline, two model tiers, ten tests

**Period:** 14–21 Jul 2026 · **Toolkit under test:** [moonlight-lupin/data-toolkit](https://github.com/moonlight-lupin/data-toolkit), final version **v0.8.5** (six skills + shared deterministic engine; per-test versions in the Appendix) · **Test models:** Claude Sonnet 5 (primary series) and Claude Haiku 4.5 (model-tier companion), each in both arms · **Orchestration & evaluation:** Claude Fable 5 · **Status:** draft for review

---

## 1. Verdict

Ten tests, each run by an agent twice — once following the toolkit's skills (**skill arm**), once with plain Python and no toolkit (**baseline arm**) — against synthetic fixtures with planted traps and recorded ground truth, every deliverable independently verified.

1. **Correctness on a strong model: parity at ordinary sizes.** On Sonnet 5, both arms produced substantively correct outputs on every test. The toolkit's edge is artefact quality — standard reconciliation taxonomy with materiality/RAG, dual-lens analysis disclosure, branded print-ready dashboards, reusable conversion cards — not headline numbers. Quality rubric: skill 50/50 vs baseline 48.5/50 (T1–T5).
2. **On a weaker model the toolkit prevents real failures.** The Haiku baseline blended GBP+USD into a single headline revenue figure (the planted currency trap) and under-triaged reconciliations at scale; the Haiku skill arm, riding the engine's rails, matched Sonnet-quality artefacts nearly check-for-check at ~60% of the cost. Quality gap widened to 50 vs 44.
3. **Economics are size- and task-dependent.** At small sizes the skills cost more (+38% tokens on Sonnet, ~+14% on Haiku — the price of reading the skill docs). At reconciliation scale the trade inverts: ~5,000+ rows runs in a third of the baseline's wall-clock at fewer tokens, flat-cost across a 235× size increase. At analyse scale (250k-row CSV) the deterministic engine is correct but still ~2× dearer than a competent pandas baseline — the audit trail is what the premium buys.
4. **Repeat work is where the design pays.** The conversion skill's reusable card made month-2 conversions a ~1–2 minute, sense-check-then-run exercise for a *fresh* agent, with schema drift flagged (never silently converted) and required-field failures excluded by the engine per the card's recorded policy.
5. **The feedback loop works.** Testing filed seven engine findings across five feedback documents; the maintainer fixed six within days (each fix re-verified here against the original repro fixtures), one remains open. The toolkit's architecture — small composable functions, self-tests, honest docs — made every gap either work-aroundable or quickly fixable.

**Standing caveat:** both arms received the same intent context and integrity rules ("flag, don't guess"; currency discipline; match windows), which is much of what the skills encode — so these results measure the toolkit's *mechanical* floor and likely understate its value on terse real-world prompts.

## 2. Method

- **Paired runs, identical prompts** apart from one block pointing the skill arm at the toolkit's SKILL.md (baseline: standard Python, no skills/toolkits). Same intent context, integrity rules, environment notes, and required report format (RESULTS / EXECUTION LOG / FILES) in both arms.
- **Fresh agent per run** (and per month, for the recurring-conversion test) — no shared conversation state; reuse must happen through artefacts on disk.
- **Synthetic fixtures, deterministic generators, recorded ground truth** (`scripts/`, `ground_truth/`). All data fictional.
- **Independent verification:** every workbook re-summed, every exception category re-counted, every dashboard grepped for external references, every brief checked for the planted findings (`scripts/verify_outputs.py`). Agents' self-reports were not trusted for scoring.
- Environment: Windows 11, Python 3.14, openpyxl / PyMuPDF / pandas / pyarrow et al.; no OCR binary; **no vision API key** (deliberately — see T8).

## 3. The test suite

| Test | Skill under test | Fixture & planted traps |
|---|---|---|
| T1 | data-tidy | 43-row messy payments CSV: junk headers, 3 date formats, duplicates, mid-table TOTAL row, `pending`/blank amounts (flag, never guess), £-embedded amounts, country spelling variants |
| T2 | data-extract | 6 subscription-confirmation PDFs; one missing Close Date (blank + flag, never invent); GBP/S$/USD mix |
| T3 | data-reconcile | Bank CSV (Debit/Credit) vs cashbook XLSX (signed), ~85 rows/side, no shared key: 8 discrepancy types incl. a 12-day equal-amount decoy and an exact-9%-GST gap |
| T4 | data-analyse | 287-row sales CSV: mixed-currency amount column, gap month, 125×-median outlier, 53.6% customer concentration, blank amounts |
| T5 | data-visualise | 3-sheet metrics XLSX → self-contained HTML dashboard: 4 KPIs with known values, RAG table, print CSS, zero external refs |
| T6 | data-reconcile at scale | T3's task at ~5,000 and ~20,000 rows/side (70 and 130 planted exceptions among thousands of matches) |
| T7 | data-convert, repeat | Recurring GL→journal-import conversion, three monthly legs by fresh agents: build+card → clean repeat → drifted repeat (renamed column, new column, blank required field ⇒ exclude) |
| T8 | data-extract, images | A bar chart (2 bars deliberately unlabelled) + a skewed rasterised table, **no vision API key**: tests honest degradation and never-invent on the vision path |
| T9 | data-analyse, large file | 249,905-row / 12.6 MB CSV: concentration, gap month, outlier cluster, currency mix, blanks — plus the large-file ingestion path |
| T10 | data-visualise, orchestrator | One dataset → consistent HTML dashboard **and** native Excel chart workbook (real chart objects, verified at XML level) |

## 4. Results — Sonnet 5 series (all verified against ground truth)

| Test | Skill | Baseline | Notes |
|---|---|---|---|
| T1 | ✓ 10 | ✓ 10 | Identical substance (40 rows, GBP 115,173.00 / USD 5,803.75, dedup, standardisation). Skill carries a reproducible recipe + engine change log; baseline's decisive date-order proof and TOTAL-row tie-back were sharp. |
| T2 | ✓ 10 | ✓ 10 | Identical: all fields exact, missing field blank + flagged in both. |
| T3 | ✓ 10 | ✓ 9.5 | Both classified all 8 planted types incl. the GST hint; both refused the 12-day decoy. Skill working paper is the stronger artefact (standard taxonomy, materiality, RAG). |
| T4 | ✓ 10 | ✓ 9.5 | Both caught every trap; skill reported both outlier-inclusive/exclusive lenses, baseline one (disclosed). |
| T5 | ✓ 10 | ✓ 9.5 | Both correct and fully self-contained; skill branded/print-first. |
| T6 (5k / 20k) | ✓ / ✓ | ✓ / ✓ | All four correct with full taxonomy; baseline needed to patch a force-pairing near-miss at 5k and shipped-then-fixed a summary formula bug at 20k — the hand-rolled risk class the engine removes. |
| T7 (3 legs) | ✓ ✓ ✓ | ✓ ✓ ⚠ | Skill: card with `on_missing_required: exclude` + standing rules; July reuse via sense-check (~1½ min); August drift flagged by the engine, rename re-pointed with disclosure, invalid row engine-excluded (113 rows, −317.85 — exact). Baseline: excellent June runner and 46-second July; August **halted entirely** on the drift (SchemaError, log, no deliverable) — maximally safe, zero output. |
| T8 | ✓ 10 | ✓ 10 | Both: printed values exact (chart 4/4, table 50/50), unlabelled bars estimated by local pixel calibration and **presented as estimates**; nothing sent externally. Skill additionally verified the vision path fails closed without a key. Shared artefact: both "saw" the scan-skew as italics — flagged, not corrected. |
| T9 | ✓ 10 | ✓ 10 | Both found every planted fact (53.1% concentration, gap month, £2m outlier cluster, currencies separated). Economics in §5. |
| T10 | ✓ 10 | ✓ 10 | Both delivered consistent dashboards + **verified native Excel charts** (chart XML, zero embedded images). Skill: 3 themed chart types via the engine; baseline hand-built to the same standard at 45% fewer tokens. |

**Errors across the series:** every error in both arms was self-caught and resolved; no run delivered a known-wrong result and no arm ever invented a value. The baseline's errors were the classic hand-rolled risks (matcher force-pairing, a delivered formula bug, instruction drift toward browsers); the skill arm's were engine-gap discoveries — which became the feedback loop (§8).

## 5. Economics — Sonnet 5

| Test | Tokens skill / base | Wall-clock skill / base | Reading |
|---|---|---|---|
| T1–T5 total | 463.2k / 335.1k (**+38%**) | 16m 45s / 21m 0s † | Fixed doc-reading overhead at small sizes; buys the audit trail, not correctness |
| T6 5k | 105.1k / 140.2k (**−25%**) | 4m 05s / 13m 13s (**0.31×**) | The inversion: engine absorbs scale |
| T6 20k | 158.6k ‡ / 110.7k | ~4m / 10m 34s (**0.38×**) | Skill wall-clock flat across 235× size growth |
| T7 repeat leg (Jul) | 99.2k / 57.6k | 1m 21s / **46s** | Both cheap once a good artefact exists; the card needs no code maintenance |
| T8 | 84.8k / 70.7k | 3m 38s / 3m 56s | Tie |
| T9 250k | 142.6k / 67.2k (**+112%**) | 6m 29s / 3m 02s (**2.1×**) | Engine correct but dearer than pandas at this scale; premium buys exact-Decimal audit trail |
| T10 | 150.5k / 82.8k (**+82%**) | 7m 08s / 6m 59s | New-surface convenience, not cheaper |

† baseline total inflated ~5 min by a self-inflicted browser timeout in one run. ‡ includes a double-counted agent-resume; the clean pre-resume figure was 79.2k.

**Rule of thumb the series supports:** small one-off files — either arm is fine, the toolkit's premium buys standardisation and reviewability; recurring or multi-thousand-row reconciliation work — the toolkit is cheaper, ~3× faster and safer; very large analyse jobs — the toolkit is correct and auditable but a pandas baseline is ~2× cheaper if you don't need the deterministic trail.

## 6. Model-tier companion — Haiku 4.5 (same suite, T1–T7)

1. **The toolkit matters more as the model gets weaker — shown by real failures.** Haiku baseline: blended-currency headline on T4 ("£1,121,085" = GBP + USD, no rate — the planted trap), muddled reconciliation taxonomy at T3, and at T6 scale both baselines dropped the triage the task required ("Unknown" buckets). Haiku skill arm: none of those — its T3/T4 artefacts match Sonnet's skill artefacts nearly check-for-check at ~60% of Sonnet's cost, and its skill overhead vs its own baseline was only ~+14%.
2. **But a weaker model needs operating guard rails at scale.** Unguarded, one Haiku skill run misdrove the reconcile engine (hand-converted signs, lost the date wiring) into a 0%-matched paper and rationalised it. Two sentences of standing rules (use the engine's convention flags; sanity-check the match rate before delivering) fixed it at no extra cost — the canonical guarded run reproduces the ground-truth taxonomy exactly. The rules a stronger model carries as judgement, a weaker model needs written down — ideally in the deterministic layer itself (one such engine guard remains an open feedback item).
3. **Repeat conversion works on the small model** — June card → July reuse (~1 min) → August drift flagged and the invalid row excluded by the engine per the card's recorded policy. With the policy in the machine spec, the outcome stopped depending on the model's memory of the rules.
4. Quality scoreboard: skill 50/50 vs baseline 44/50 (T1–T5); at T6 scale, skill 2/2 correct vs baseline 0/2.

## 7. The August drift spectrum (both models, T7 leg 3)

All four arms flagged the schema drift; **none silently converted** — but the deliverable ranged across a spectrum of defensible conservatism: Sonnet baseline halted entirely (no import file, failure log, ask-first); Sonnet skill delivered with the required-field exclusion enforced and the renamed non-required column held back pending confirmation; Haiku skill re-pointed the rename with disclosure and delivered the complete correct file; Haiku baseline likewise via a code alias. For attended use all four are acceptable; for unattended use, the card's explicit `on_missing_required` policy is what removes the judgement spread on the part that matters.

## 8. The feedback loop — findings filed and their outcomes

Seven engine findings were filed during testing in the toolkit's own feedback format (`feedback/`); each fix was re-verified here against the original repro fixtures:

| Finding | Severity | Outcome |
|---|---|---|
| reconcile: no-date silently disabled the amount+date window (false matches) | Blocker | **Fixed** — warns, holds pairs as ambiguous |
| reconcile: duplicate/sign-flip/amount-mismatch triage missing in amount_date mode | Enhancement | **Fixed** — residue-refinement pass |
| extract: currency fields discarded the detected code | Bug | **Fixed** — `code_target` |
| tidy: unparseable amount lost its Currency value | Bug | **Fixed** — `code_source` |
| convert: `required: true` was report-only; standing rules dropped in hand-off | Enhancement/Bug | **Fixed** — `on_missing_required: exclude/error/flag` + mandatory Standing-rules card section |
| analyse: profiler minutes-slow at 250k rows; large-file path is xlsx-only | Enhancement | **Fixed** (profiling 222s → 6.6s on the repro; CSV scope now documented honestly — feature request stands) |
| analyse: `currency_mix()` blind to stand-alone code columns (safety-gate blind spot) | Bug | **Fixed** — detects bare-code columns |
| reconcile: warn when matched=0 but thousands of equal amounts coincide (absurd-result guard) | Enhancement | **Open** at report date — since **fixed in v0.8.6**, see [Addendum](#addendum--maintainer-status-after-the-report-date) |

The toolkit's other governance change during the period — an opt-in vision-API path for image extraction, its first network-touching feature — is disclosed prominently in its PRINCIPLES/README (opt-in, never implicit, fails closed without a key); T8 confirmed the fail-closed behaviour in practice.

## 9. Limitations

- n = 1 per cell; treat deltas under ~10% as noise. Scaling claims rest on three sizes (reconcile) and two (analyse).
- Prompts scaffolded both arms with the integrity rules the skills encode — the unscaffolded gap likely favours the toolkit further.
- Not covered: the agent-runtime driving mode (`bin/data-toolkit` plans), scanned-PDF OCR, `.pptx`/`.msg` ingest, analyse plan-ops, reuse runners (`emit_runner`), FX-pinned conversions.
- Token figures are harness-reported agent totals (reading + reasoning + output).

## 10. Conclusions

For finance-grade data work driven by agents: **adopt the toolkit for reconciliation (any volume), recurring conversions, and any output a reviewer must sign off** — the deterministic engine, standard taxonomies and recorded policies are worth the modest overhead, and they are what keeps a smaller model safe. For one-off tidy/extract jobs a strong model matches it; for very large ad-hoc analysis a pandas baseline is cheaper when the audit trail isn't required. Pin the version you adopt (upstream ships fast), re-run this suite per adopted version — the fixtures, ground truth and verifier in this bundle make that a one-afternoon regression pass — and route by model tier: strong models for scale and for authoring reusable artefacts; small models for routine attended tasks on the engine's rails, with operating guard rails written into the prompt or, better, the toolkit's deterministic layer.

---

## Appendix — provenance

Canonical runs in this bundle and the toolkit version each skill-arm run executed against: T1–T5 skill, T7 skill, T8, T10 — **v0.8.4**; T9 skill — **v0.8.5**; T6 skill (Sonnet) — **v0.4.3**; Haiku series — **v0.5.3** (T7) / **v0.5.2** (T1–T6, with the two 5k guarded runs as canon). Baseline runs never touch the toolkit. Engine-level fixes listed in §8 were verified on **v0.8.5** against the original repro fixtures. Earlier iterations superseded by upstream fixes or guard-rail adjustments are excluded from this bundle by design; `run_metrics.csv` lists the canonical runs only.

*Draft for review — reproduce any figure from `fixtures/`, `ground_truth/`, `scripts/` and the run artefacts in `runs/` (Sonnet) and `runs_haiku/` (Haiku).*

---

## Addendum — maintainer status after the report date

**Written by the toolkit maintainer, not the benchmark authors.** Everything above is the
independent report as delivered against **v0.8.5**; no measurement, score, verdict or economic
figure in it has been altered. This section records only what changed upstream *afterwards*, so
a reader comparing the report against the current toolkit isn't misled by the §8 status table.
These fixes have **not** been re-scored by a fresh benchmark run — re-running the suite is the
one-afternoon regression pass §10 recommends.

| Version | Change | Verification |
|---|---|---|
| **v0.8.6** | Closes the last open §8 finding — the reconcile **absurd-result guard**. `match()` now records the amount-only pairing potential (as-is and with one side negated); `summarise()` raises `UNRELIABLE RESULT`, leads the warnings with it, stamps `⛔ UNRELIABLE` on the report headline and sets `summary["unreliable"]` when under 20% of that potential reconciled. A much larger negated-match count names the sign convention (`--flip-b` / debit-credit mapping) specifically. Silent on healthy runs and on inputs under 20 potential pairs. | Re-run against the original `t6m` repro fixtures: correct wiring reproduces ground truth (**4,930 matched / 75 exceptions**) with the guard **silent**; the broken wiring that produced the round-3 failure **fires** it. Four self-tests cover healthy / near-zero / sign-inverted / small-input. |
| **v0.8.7** | Unrelated to any §8 finding — found while reviewing the report. `parse_number` stripped every non-digit before parsing, so identifiers became confident wrong numbers *with an empty note*: `SKU-0001` → `-1`, `ACC-100` → `-100`, `REF10000` → `10000`, `100 Program` → `100000000`; it also silently dropped sign-changing markers (`1,234.50 CR` → `1234.50`). It now strips only recognised currency tokens and requires a bare number, else fails with a note. | All money formats unchanged (`£1,234.50`, `(500)`, `US$ 2.5m`, `USD 50`, `15%`, `2.5k`, `$99.99`); `parse_currency` still resolves codes so the T4/T9 currency gate is untouched; `t6m` still reproduces ground truth. 109 tests + all skill self-tests pass. |

**Effect on §8's scoreboard:** seven of seven filed findings are now fixed; none open.

**Two report observations deliberately not actioned.** (1) §8's CSV note — `read_large` remains
Excel-only. The report's own T9 timings show ingestion at 0.42s, so this is a memory-headroom
feature, not a bottleneck; the scope is now stated honestly in
`skills/data-analyse/references/large-file-patterns.md` rather than implied. (2) §5's finding
that large analyse jobs stay ~2× dearer than a pandas baseline stands — that is the cost of the
exact-`Decimal` audit trail, and the v0.8.5 profiler fix (222s → 6.6s on the T9 repro) addressed
the pathological part, not the premium.

*Benchmark bundle synced into this repo at v3 (21 Jul 2026). Per the repo's size policy the
regenerable large fixtures (`t6l_*`, `t6m_*`, `t9_sales_large.csv`) and the T6 run workbooks are
not committed — see `README.md` and `.gitignore`.*
