# AGENTS.md

## Cursor Cloud specific instructions

This repo is a fully-local Claude Code plugin (data-prep): shared engine scripts in `scripts/`
plus 4 markdown skills. No service runs; "running" means invoking an engine script, and "testing"
means the pytest suite.

- Runtime: Python 3 (VM has 3.12). There is **no `requirements.txt`**; the only hard dependency is
  `openpyxl` (installed by the update script). Optional per-input-type extras are `PyMuPDF` (fitz),
  `pdfplumber`, `python-docx`, `extract_msg`, and system Tesseract (OCR) — install only if
  exercising those paths.
- `pytest` is at `~/.local/bin` (not on PATH). Run tests with `python3 tests/test_engine.py`
  (standalone, no pytest needed) or `python3 -m pytest tests/`.
- Probe capabilities first with `python3 scripts/envcheck.py`. Note: the `data-extract` skill shows
  BLOCKED without `PyMuPDF`/`fitz`; the other 3 skills (`data-tidy`, `data-reconcile`,
  `data-visualise`) are OK with just `openpyxl` (`data-visualise` is pure stdlib).
