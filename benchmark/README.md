# data-toolkit benchmark

An independent, reproducible benchmark of the toolkit's skills — **the same model with the
toolkit vs. with plain Python** — across **two model tiers**, all six skills, ten tests
including reconciliation scaling, a large-file analyse test, and a recurring-conversion test.
Scored against recorded ground truth, with every deliverable independently verified (never the
agents' self-reports).

**Start here: [`REPORT.md`](REPORT.md)** — the consolidated report (bundle v3, 21 Jul 2026):
ten tests, both model tiers, economics, scaling, repeat conversion, and the upstream feedback
loop with outcomes.

- **Toolkit under test:** **v0.8.5** final; per-test provenance in the report's Appendix
  (T6 Sonnet ran on v0.4.3, the Haiku series on v0.5.2/v0.5.3)
- **Test models:** Claude Sonnet 5 (primary series, T1–T10) · Claude Haiku 4.5 (companion, T1–T7)
- **Orchestration / evaluation:** Claude Fable 5

[`REPORT_HAIKU.md`](REPORT_HAIKU.md) is the **historical** round-3 Haiku report (v0.5.2), kept
for its per-test detail; its conclusions are folded into REPORT.md §6. Where they differ,
REPORT.md is authoritative.

## Headline

- **Correctness parity on a strong model.** On Sonnet both arms were substantively correct on
  all ten tests — the toolkit's edge is artefact quality and the audit trail, not arithmetic.
  Rubric **50 / 50 vs 48.5 / 50** (T1–T5).
- **On a weaker model the toolkit prevents real failures.** The Haiku baseline blended GBP+USD
  into one headline revenue figure (the planted currency trap) and under-triaged reconciliations
  at scale; the skill arm did neither, at ~60% of Sonnet's cost. Gap widens to **50 vs 44**.
- **Economics are size- and task-dependent.** Small files cost *more* with the skills (+38%
  tokens on Sonnet — the price of reading the docs). At reconciliation scale the trade inverts:
  ~5,000+ rows runs in ~a third of the baseline's wall-clock, flat across a 235× size increase.
  At 250k-row analyse scale the engine is correct but ~2× dearer than a competent pandas
  baseline — the audit trail is what the premium buys.
- **Repeat work is where the design pays.** A recorded conversion card made month-2 conversions
  a ~1–2 minute exercise for a *fresh* agent, with schema drift flagged (never silently
  converted) and required-field failures excluded mechanically.
- **The feedback loop works.** Seven engine findings were filed across five feedback documents
  and **all seven are now fixed** (six during the series, the last in v0.8.6 — see the report's
  Addendum), each re-verified against its original repro fixture.

## Honest limits (read these)

- **n = 1 per cell** — single run per task/arm; treat sub-~10% deltas as noise. Scaling claims
  rest on three sizes (reconcile) and two (analyse).
- **The prompt scaffolding favours the baseline** — both arms get the same integrity rules,
  which are much of what the skills encode; the unscaffolded gap plausibly favours the toolkit
  further.
- **On a weak model at scale, the risk shifts from cost to correctness.** Haiku needs explicit
  operating guard rails, and a wrong 20k-row working paper is invisible to eyeball review — so:
  Sonnet + skills for large / high-stakes work; Haiku + skills for small, attended tasks.
- **The report predates the current toolkit.** It measures v0.8.5; v0.8.6–0.8.7 landed after.
  Those changes are recorded in the report's Addendum and have **not** been re-scored by a fresh
  benchmark run.

## Contents

| Path | What |
|---|---|
| `REPORT.md` | The consolidated report — method, results, economics, scaling, feedback loop, limits, and the maintainer Addendum for post-report fixes. |
| `REPORT_HAIKU.md` | Historical round-3 Haiku detail (v0.5.2); superseded in summary by REPORT.md §6. |
| `run_metrics.csv` | Tokens / tool calls / wall-clock for every canonical run. |
| `fixtures/` | Synthetic inputs, all fictional. T1–T5, T7, T8 committed; the large T6 and T9 inputs are regenerable (below). |
| `ground_truth/` | The planted-trap answer keys the outputs were scored against (t1–t9). |
| `scripts/` | Deterministic fixture generators (`make_fixtures.py`, `_t6`, `_t7`, `_t8t9`) and `verify_outputs.py` (independent re-scoring). |
| `runs/` | Sonnet deliverables, canonical runs only (T1–T10). *T7_baseline has no August CSV by design — its runner halted on schema drift and wrote a `SCHEMA_FAILURE.log`.* |
| `runs_haiku/` | Haiku deliverables, canonical runs only (T1–T7). |
| `feedback/` | The seven findings filed to the maintainer in the toolkit's own template, each with a verified status update. |

## Reproducing

All generators are deterministic — no RNG, so the *data* is identical on every run. Text
outputs (`.csv`, `.json`) regenerate **byte-identically**; binary outputs (`.xlsx`, `.pdf`,
`.png`) do **not**, because those formats embed a creation timestamp or renderer version. Their
content is unchanged, but expect a git diff if you regenerate them — verified, not assumed.

```bash
cd benchmark
python scripts/make_fixtures.py       # T1-T5 fixtures + ground truth
python scripts/make_fixtures_t7.py    # T7 monthly GL exports + ground truth
python scripts/make_fixtures_t6.py    # large T6 scaling fixtures (not committed)
python scripts/make_fixtures_t8t9.py  # T8 images + the 250k-row T9 CSV (not committed)
```

Re-score the committed deliverables against ground truth:

```bash
python scripts/verify_outputs.py                          # Sonnet runs/  -> 38 checks
python scripts/verify_outputs.py runs_haiku skill baseline # Haiku runs_haiku/
```

Expected: the Sonnet series passes every check. The Haiku series shows **three failures, all in
the `baseline` arm** (T4's excl-outlier total and concentration share, T5's SVG charts) — that
is the documented weak-model gap the report describes, reproduced, not a regression.

**Omitted for size** (see `.gitignore`): the T6 scaling fixtures (`fixtures/t6{l,m}_*`), the
12.6 MB T9 CSV (`fixtures/t9_sales_large.csv`), and all T6 run workbooks. All are CSV/XLSX the
generators above recreate on demand — the T9 CSV byte-identically — and the scaling results live
in the report and `run_metrics.csv`.

Do **not** regenerate `fixtures/t8_chart.png`: matplotlib's PNG output is not byte-stable across
versions, and T8 scored pixel-calibrated estimates of two deliberately unlabelled bars against
that exact image. The committed file is canonical.

## Notes

- Prompts were identical between arms except one block pointing the skill arm at the toolkit.
  Runs superseded by upstream fixes or prompt guard-rail adjustments are excluded; the report's
  Appendix states each run's toolkit version and canon choices.
- **Sanitised:** absolute local paths and a test organisation's name (which some agents inferred
  from file paths) were replaced with neutral placeholders. No figures, classifications or
  structure were altered.
- **Maintainer edits to the bundle:** the `scripts/` path base was corrected to resolve to the
  benchmark root (the generators previously wrote to `scripts/fixtures/` and only worked from
  the bundle root), and `verify_outputs.py`'s default arm suffix was corrected from `base` to
  `baseline` so the bare invocation works. No fixture content, ground truth, run artefact or
  reported figure was changed.
