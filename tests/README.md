# tests/

Regression suites lock the toolkit's **finance-grade engine behaviours** and its
**agent-facing execution contract** — the guarantees that would silently corrupt a result or
cause a weaker agent to improvise unsafe glue if they regressed.

## Run

```bash
python tests/test_engine.py          # shared engines and finance controls
python tests/test_agent_runtime.py   # unified plan/runtime interface
pytest tests/                        # if pytest is installed
```

Both standalone runners print a PASS/FAIL line per test and exit non-zero on failure.

## Engine coverage

| Behaviour | Why it matters |
|---|---|
| Decimal tolerance edge | amounts are exact `Decimal` — no binary-float drift at the tolerance band |
| 100 USD ≠ 100 SGD (key + symbol) | currencies are compared, never matched across units |
| strict-currency mode | audit mode refuses to match an unknown currency (`currency_unknown`) |
| bare `$` is ambiguous | never assumed USD; an expected currency resolves it |
| amount/date window | equal amounts outside the window go to `ambiguous`, not matched |
| multi-sheet workbook | requires explicit sheet selection (no silent active-sheet guess) — engine + visualise |
| next-line and dotted-leader form fields | common document layouts remain extractable |
| `code_target` currency split | currency code is emitted into its own column |
| categorical value-map | clustering proposes the right canonical value (+ master snap) |
| PDF table scoring | best-engine selection (pdfplumber vs PyMuPDF), with guarded read smoke test |
| Debit/Credit columns | signed amount = debit − credit; reconciles against a signed-amount side |
| case-insensitive columns | `amount` finds a bank CSV's `Amount` per side |
| `--flip-b` sign flip | opposite sign conventions reconcile explicitly |
| balance completeness | opening + movement = closing; a truncated extract does not tie |
| ageing (`--as-of`) | one-sided items gain `age_days`; no `as_of` means no ageing |
| GST/net-vs-gross hint | tax-shaped mismatches get an advisory note, not a forced category |
| per-currency summary | mixed-currency recon reports per-currency values, not a blind total |

## Agent runtime coverage

| Behaviour | Why it matters |
|---|---|
| Native JSON records + `json_path` | agents can use JSON without hand-written parsing |
| Sole nested record-list auto-selection | common API-export wrappers work, and the selection is disclosed |
| Versioned plan validation | malformed or wrong-skill plans fail before execution |
| Primary approval gate | an agent cannot silently write confirm-first outputs |
| Signed drift receipt | `allow_drift` alone cannot write; tampered or stale receipts remain blocked |
| Signed aggregation decision | exact accepted indexes, including signed `[]`, are bound to the proposal set |
| Secondary dry-run action | aggregation approval requests correctly report `action: dry-run` |
| Six skill plan shapes | one interface recognises every shipped skill |
| Multi-source union + flatten | advertised conversion paths are reachable without custom glue |
| End-to-end nested JSON output | the reported `.json` artefact is the file actually written |
| Zero/net-zero analysis totals | direct engine and runtime callers both preserve zero; invalid shares stay `null` |
| Dry-run | validation and computation do not write artefacts |
| CLI JSON contract | `inspect` and `schema` remain machine-readable |

## Notes

- Pure Python; `openpyxl` is the only hard dependency.
- The PDF smoke test self-skips if PyMuPDF is absent; PDF scoring remains dependency-free.
- The runtime suite creates temporary JSON/CSV plans and imports `agent_runtime` directly,
  so the CLI and library path exercise the same hardened implementation.
- Approval tests use an injected test key; production keys must be withheld from the agent.
