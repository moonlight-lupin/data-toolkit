# data-toolkit benchmark

An independent, reproducible benchmark of the toolkit's skills — **Claude Sonnet 5 with the
toolkit vs. the same model with plain Python** — across all five skills plus a reconciliation
scaling test, scored against recorded ground truth.

**Start here → [`REPORT.md`](REPORT.md).**

- **Date:** 14 Jul 2026 · **Toolkit under test:** data-toolkit **v0.4.3**
- **Test model:** Claude Sonnet 5 (both arms) · **Orchestration / evaluation:** Claude Fable 5

## Headline

- **Correctness:** parity on the headline numbers — a well-prompted Sonnet 5 without the toolkit
  matched the toolkit's figures at ordinary sizes.
- **Quality:** the skill arm produced the stronger, more standardised artefacts — **50 / 50 vs
  48.5 / 50** on the rubric.
- **Cost inverts at scale:** the toolkit costs more on small one-off files (+45% tokens here),
  but from ~5,000 rows the deterministic engine is **~25% cheaper on tokens and ~3× faster**,
  and its cost is essentially **flat** across a 235× size increase.
- **Risk:** the hand-rolled baseline's error surface grows with data size (a matcher that began
  force-pairing unrelated items; a real formula bug in a delivered workbook) — the failure class
  a tested deterministic engine removes.

## Contents

| Path | What |
|---|---|
| [`REPORT.md`](REPORT.md) | The benchmark report — method, results, cost, scaling, errors, limitations. |
| [`run_metrics.csv`](run_metrics.csv) | Tokens / tool calls / wall-clock per run, as reported by the agent harness. |
| `fixtures/` | Synthetic test inputs (all data fictional). T1–T5 committed; the large T6 scaling inputs are regenerable (below). |
| `ground_truth/` | The planted-trap answer keys the outputs were scored against (incl. T6). |
| `scripts/` | `make_fixtures.py`, `make_fixtures_t6.py` (deterministic generators) and `verify_outputs.py` (independent output verification). |
| `runs/` | The deliverables from the T1–T5 benchmark runs, `_skill` vs `_baseline`. |

T1–T5 = tidy / extract / reconcile / analyse / visualise. T6 = the reconcile scaling test at
~5,000 (T6M) / ~20,000 (T6L) rows per side.

## Reproducing

Everything is deterministic — no randomness, all data fictional.

```bash
cd benchmark
python scripts/make_fixtures.py       # regenerate the T1–T5 fixtures + ground truth
python scripts/make_fixtures_t6.py    # regenerate the large T6 scaling fixtures + ground truth
python scripts/verify_outputs.py      # re-score deliverables in runs/ against ground_truth/
```

The large **T6 scaling fixtures** (`fixtures/t6{l,m}_*` — ~5,000 / ~20,000 rows/side) and their
run workbooks are **omitted from the committed folder for size**; `make_fixtures_t6.py`
regenerates the inputs byte-for-byte, and the scaling results live in [`REPORT.md`](REPORT.md)
§6 and `run_metrics.csv`.

## Notes

- Prompts were identical between the two arms except for one block pointing the skill arm at the
  toolkit; both arms received the same intent context and integrity rules, so this measures the
  toolkit's *mechanical* value floor (see the report's §1 caveat and §9 limitations — including
  n = 1 per cell).
- Deliverables were scored by independent verification against ground truth, not by trusting the
  agents' self-reports.
- One redaction: `runs/T5_baseline/dashboard.html` had a header line removed (the agent had
  inferred the test organisation's name from a file path). Nothing else was altered.
