# Golden plans

Six worked **agent plans** — one per skill — that run end-to-end through the unified runtime
(`bin/data-toolkit`). They serve two purposes:

1. **A worked example.** Canonical, known-good plan shapes an agent (or a person) can copy.
   Pair each with its skill's schema (`python bin/data-toolkit schema <skill>`) and the
   [`AGENT-FAST-PATH.md`](../../AGENT-FAST-PATH.md) workflow.
2. **A smoke test.** One command exercises all six skills through validation + execution, so a
   change that breaks the runtime or a skill's engine is caught immediately.

## Run them

```bash
python examples/golden-plans/run_golden_plans.py
```

Every plan is validated (as the fast path instructs) and then executed; artefacts land under
`out/` (git-ignored). The runner exits non-zero if any plan fails. Expected output:

```
  OK    01-tidy.json      success_with_warnings   2 artefact(s)
  ...
  All golden plans passed.
```

`success_with_warnings` is normal and intended — the fixtures carry deliberate imperfections
(an ambiguous date, a rounding break, an unmapped source column) so the reports have something
real to show.

## What each plan demonstrates

| Plan | Skill | Shows |
|---|---|---|
| `01-tidy.json` | data-tidy | recipe: date normalisation + number parsing + trim |
| `02-extract.json` | data-extract | key-value fields from a document, currency **amount + code** |
| `03-reconcile.json` | data-reconcile | key match + triaged exceptions (match / rounding / one-sided) |
| `04-analyse.json` | data-analyse | a breakdown + IQR outlier detection |
| `05-visualise.json` | data-visualise | KPI row + a RAG-coloured table (neutral default theme) |
| `06-convert.json` | data-convert | map a GL export onto a journal-import contract (signed amount) |

## Notes

- **Self-contained.** Fixtures live in `fixtures/` (CSV / plain text). No optional dependency
  is needed — `openpyxl` (the one hard dependency) only writes the `.xlsx` outputs.
- **Paths resolve relative to each plan file**, which is how `bin/data-toolkit run PLAN.json`
  behaves — so inputs are `fixtures/…` and outputs are `out/…`.
- These plans set `approval.confirmed: true` to run unattended for the smoke test. In real use
  an agent surfaces the plan and gets that confirmation from you first (see the fast path).
