# AGENTS.md

## Cursor Cloud specific instructions

This repo is a fully-local Claude Code plugin (data-prep): shared engine scripts in `scripts/`
plus **6** skills (`data-extract`, `data-tidy`, `data-reconcile`, `data-analyse`,
`data-visualise`, `data-convert`). No service runs; "running" means invoking an engine script, and "testing"
means the regression suite.

- Runtime: Python 3 (VM has 3.12). Hard dependency: `openpyxl` (see `requirements.txt`).
  Optional per-input-type extras are `PyMuPDF` (fitz), `pdfplumber`, `python-docx`,
  `extract_msg`, and system Tesseract (OCR) — install only if exercising those paths.
- Run tests with `python3 tests/test_engine.py` (standalone, no pytest needed) or
  `python3 -m pytest tests/`. Authoring gate: `python3 bin/data-lint`.
- Probe capabilities first with `python3 scripts/envcheck.py`. Note: the `data-extract` skill
  shows BLOCKED without `PyMuPDF`/`fitz`; the other skills are OK with just `openpyxl`
  (`data-visualise` is pure stdlib for rendering).
- Quickstart (no Claude): `python3 examples/run_quickstart.py`.
- CI (`.github/workflows/ci.yml`) runs `bin/data-lint`, `tests/test_engine.py`, and the
  quickstart smoke on Python 3.10–3.12.
