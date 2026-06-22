# tests/

Regression suite locking in the toolkit's **finance-grade** behaviours — the guarantees that
would silently corrupt a reconciliation or a clean table if they ever regressed.

## Run

```bash
python tests/test_engine.py     # standalone, no pytest needed
pytest tests/                   # if pytest is installed
```

Both run the same checks; the standalone runner prints a PASS/FAIL line per test and exits
non-zero on any failure.

## What's covered

| Behaviour | Why it matters |
|---|---|
| Decimal tolerance edge | amounts are exact `Decimal` — no binary-float drift at the tolerance band |
| 100 USD ≠ 100 SGD (key + symbol) | currencies are compared, never matched across units |
| strict-currency mode | audit mode refuses to match an unknown currency (`currency_unknown`) |
| bare `$` is ambiguous | never assumed USD; an expected currency resolves it |
| amount/date window | equal amounts outside the window go to `ambiguous`, not matched |
| multi-sheet workbook | requires explicit sheet selection (no silent 'active'-sheet guess) — engine + visualise |
| next-line form fields | label alone, value on the following line |
| dotted-leader form fields | `Label .......... value` |
| `code_target` currency split | currency code emitted into its own column |
| categorical value-map | clustering proposes the right canonical (+ master snap) |
| PDF table scoring | best-engine selection (pdfplumber vs PyMuPDF), ties to pdfplumber; + a guarded read smoke test |

## Notes

- Pure-Python; needs `openpyxl` (already a toolkit dep). The PDF smoke test self-skips if
  PyMuPDF isn't installed; the PDF **scoring** test is dependency-free.
- The suite imports the shared engine (`scripts/`) and the skill scripts directly via `sys.path`
  — no install step.
