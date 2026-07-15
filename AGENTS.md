# AGENTS.md

## Cursor Cloud specific instructions

This repo is a fully-local Claude Code plugin (data-prep): shared engine scripts in `scripts/`
plus **6** skills (`data-extract`, `data-tidy`, `data-reconcile`, `data-analyse`,
`data-visualise`, `data-convert`). No service runs; "running" means invoking an engine script or
the unified agent runtime, and "testing" means the regression suites.

- Runtime: Python 3 (VM has 3.12). Hard dependency: `openpyxl` (see `requirements.txt`).
  Optional per-input-type extras are `PyMuPDF` (fitz), `pdfplumber`, `python-docx`,
  `extract_msg`, and system Tesseract (OCR) — install only if exercising those paths.
- Prefer the stable agent interface for planned work:
  - `python3 bin/data-toolkit inspect SOURCE`
  - `python3 bin/data-toolkit validate PLAN.json`
  - `python3 bin/data-toolkit run PLAN.json --dry-run`
  - `python3 bin/data-toolkit run PLAN.json`
  See `AGENT-RUNTIME.md`. Do not bypass a `needs_approval` result.
- Run tests with `python3 tests/test_engine.py` and `python3 tests/test_agent_runtime.py`
  (both standalone, no pytest needed), or `python3 -m pytest tests/`.
  Authoring gate: `python3 bin/data-lint`.
- Probe capabilities first with `python3 scripts/envcheck.py`. Note: the `data-extract` skill
  shows BLOCKED without `PyMuPDF`/`fitz`; the other skills are OK with just `openpyxl`
  (`data-visualise` is pure stdlib for rendering).
- Quickstart (no Claude): `python3 examples/run_quickstart.py`.
- CI (`.github/workflows/ci.yml`) runs `bin/data-lint`, both regression suites, and the
  quickstart smoke on Python 3.10–3.12.
