# data-toolkit benchmark

An independent, reproducible benchmark of the toolkit's skills — **the same model with the
toolkit vs. with plain Python** — now across **two model tiers**, all six skills, a
reconciliation scaling test, and a recurring-conversion test, scored against recorded ground
truth (deliverables independently verified, never the agents' self-reports).

**Two reports:**
- **[`REPORT.md`](REPORT.md)** — **Claude Sonnet 5** (a strong model): T1–T5, the T6 scaling
  test, and the T7 recurring-conversion addendum.
- **[`REPORT_HAIKU.md`](REPORT_HAIKU.md)** — **Claude Haiku 4.5** (a small, cheap model): the
  full T1–T7 companion, incl. scaling and guard-rail experiments.

- **Toolkit under test:** v0.4.3 (Sonnet T1–T6) · v0.5.2 / v0.5.3 (T7 and the Haiku round)
- **Orchestration / evaluation:** Claude Fable 5

## Headline

- **Correctness parity on a strong model.** On Sonnet, a well-prompted baseline matched the
  toolkit's numbers at ordinary sizes — the value is standardised artefacts + a deterministic
  audit trail, not better arithmetic. Rubric **50 / 50 vs 48.5 / 50**.
- **The value grows as the model gets cheaper — shown, not assumed.** On **Haiku**, the baseline
  fell into a planted currency trap and headlined a blended **£1,121,085** GBP+USD total; the
  skill arm's currency gate held. The arm gap **widens to 50 / 50 vs 44 / 50**, and skill
  overhead nearly vanishes (**+14% tokens vs +45% on Sonnet**).
- **The value grows as the data gets bigger.** On Sonnet's scaling test the engine's cost is
  ~flat across a 235× size increase — from ~5,000 rows the skill arm is **~3× faster** and
  cheaper, while hand-rolled code gets slower *and* riskier (a matcher force-paired unrelated
  items; a formula bug shipped in a workbook).
- **Recurring conversion (T7) is cheap and safe to repeat** — month 2+ costs ~1 minute; on the
  drift month the toolkit **excluded the invalid row mechanically** to exact ground truth where a
  hand-rolled baseline **halted the whole run**.
- **Found → filed → fixed → re-verified, inside the benchmark.** Issues surfaced by testing were
  filed in the toolkit's own feedback format and fixed upstream (v0.4.3, and v0.5.3 / PR #17 for
  the required-field enforcement), then re-verified on the same fixtures. See `feedback/`.

## Honest limits (read these)

- **n = 1 per cell** — single run per task/arm; treat sub-~10% deltas as noise.
- **The prompt scaffolding favours the baseline** — both arms get the same integrity rules, which
  are much of what the skills encode; the unscaffolded gap is plausibly larger in the toolkit's
  favour.
- **On a weak model at scale, the risk shifts from cost to correctness.** Haiku needs explicit
  operating guard rails, and a wrong 20k-row working paper is invisible to eyeball review — so:
  Sonnet + skills for large / high-stakes work; Haiku + skills only for small, attended tasks.
  (Full detail in `REPORT_HAIKU.md` §8.)

## Contents

| Path | What |
|---|---|
| `REPORT.md` / `REPORT_HAIKU.md` | The two reports (method, results, cost, scaling, errors, limits). |
| `run_metrics.csv` | Tokens / tool calls / wall-clock per run. Row suffixes: none = Sonnet r1, `_v2` = Sonnet on v0.4.3, `_sn` = Sonnet T7, `_hk` = Haiku, `_hk_v2` = Haiku canonical re-runs. |
| `fixtures/` | Synthetic inputs (all fictional). T1–T5 + T7 committed; the large T6 scaling inputs are regenerable (below). |
| `ground_truth/` | The planted-trap answer keys the outputs were scored against. |
| `scripts/` | `make_fixtures.py`, `make_fixtures_t6.py`, `make_fixtures_t7.py` (deterministic generators) and `verify_outputs.py` (independent verification). |
| `runs/` | Sonnet deliverables (T1–T5, T7). *T7_baseline has no August CSV by design — its runner halted on drift and wrote a `SCHEMA_FAILURE.log`.* |
| `runs_haiku/` | Haiku deliverables. Canonical markers: `T7_skill_v053_CANON` (the post-fix T7) and, for T6, the `*_guarded_CANON` runs — the unguarded originals are retained as the prompting-for-weaker-models finding. |
| `feedback/` | Issues filed to the maintainer in the toolkit's own template (all fixed upstream: v0.4.3 and v0.5.3 / PR #17). |

## Reproducing

Everything is deterministic — no randomness, all data fictional.

```bash
cd benchmark
python scripts/make_fixtures.py       # T1–T5 fixtures + ground truth
python scripts/make_fixtures_t7.py    # T7 monthly GL exports + ground truth
python scripts/make_fixtures_t6.py    # the large T6 scaling fixtures (omitted from the repo)
python scripts/verify_outputs.py      # re-score the Sonnet T1–T5 deliverables in runs/
```

The **T6 scaling fixtures** (`fixtures/t6{l,m}_*`) and all T6 run workbooks are **omitted for
size**; `make_fixtures_t6.py` regenerates the inputs and the scaling results live in the reports
(§6 / §8) and `run_metrics.csv`.

## Notes

- Prompts were identical between the two arms except for one block pointing the skill arm at the
  toolkit. The Haiku T6 *guarded* runs and the T7 v0.5.3 legs are documented in the reports.
- **Sanitised:** absolute local paths and a test organisation's name (which some agents inferred
  from file paths) were replaced with neutral placeholders. No figures, classifications or
  structure were altered.
