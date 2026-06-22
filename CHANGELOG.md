# Changelog

## 0.2.0 — 2026-06-22

Finance-grade hardening (correctness fixes across the shared engine):

- **PDF tables: two engines, best result per page.** `ingest` now prefers **pdfplumber**
  (optional dep; better on messy / borderless tables) and falls back to **PyMuPDF**, scoring
  each page's extraction and keeping the better one; PyMuPDF + local Tesseract stays the OCR
  path for scans. `list_pdf_tables` / `extract_pdf_table` report and accept the `engine`.
- **Strict currency mode for reconciliation.** `match(..., strict_currency=True)` (CLI
  `--strict-currency`) refuses to reconcile when a side's currency is unknown — those pairs go
  to a `currency_unknown` bucket / triage category instead of matching. Default stays permissive
  (unknown treated as compatible); strict mode is for audit/finance work.
- **Currency-aware reconciliation.** `match` takes a `currency` column (else the code is
  detected from the amount cell's symbol) and **compares currencies** — 100 USD no longer
  matches 100 SGD. A key match in different currencies goes to a new `currency_diffs` bucket /
  `currency_mismatch` triage category; in amount_date mode incompatible currencies don't match.
  Wired through `reconcile_files` and the CLI (`--currency`).
- **Visualise reads multi-tab workbooks safely.** `viz.rows_from_xlsx` no longer silently reads
  the 'active' sheet — it reuses `ingest.read_xlsx` when reachable (auto-select single data
  sheet, raise on several), with a matching standalone fallback when ingest isn't on the path.

- **Exact `Decimal` amounts (was float).** `dataclean.parse_number` / `parse_currency` and
  `reconcile.to_amount` now return `Decimal`, so sums, tolerances and currency tables don't
  drift by binary-float dust — a genuine tie no longer splits at the tolerance edge.
  `write_xlsx` writes them as real numbers. Matches the FP&A toolkit's choice.
- **`amount_date` reconciliation honours the date window as a hard constraint.** Equal-amount
  pairs only match when their dates are within `date_window_days` (default ±5); an equal-amount
  pair *outside* the window is no longer silently booked as a timing difference — it goes to a
  new `ambiguous` bucket / `ambiguous_match` triage category for the reviewer to confirm. The
  window is now wired through `reconcile_files` and the CLI (`--date-window`).
- **Safer currency handling.** Amount and currency code are kept distinct: a `currency` column
  can emit its code into its own column via `code_target`. A **bare `$` is treated as ambiguous**
  (could be USD/SGD/AUD/HKD…), not silently assumed USD — flagged unless an expected `currency`
  is given (which then resolves it). Disambiguated dollars (`US$`/`S$`/`A$`/`HK$`/`NZ$`/`C$`) and
  ISO codes resolve directly; the sign table is expanded for SG/AU/HK/NZ/CA/CH/CN/IN.
- **Richer form extraction.** `extract._find_value` now also reads dotted-leader lines
  (`Label .... value`) and the **next-line layout** (label alone, value on the following line),
  stopping at the next field's label so it never grabs a neighbour. (Genuine 2-D box/grid forms
  still need table mode — documented.)
- **Excel sheet discovery + selection.** `ingest.list_sheets()` enumerates tabs; `read_xlsx` /
  `read_any` auto-select the single non-empty sheet and **raise `SheetSelectionRequired`** when
  several tabs hold data (instead of guessing the 'active' sheet). `reconcile_files` gains
  `sheet_a` / `sheet_b` (CLI `--sheet-a` / `--sheet-b`).

Engine improvements (borrowing sharper cleaning primitives from the `data-cleaner` skill):

- **Semantic type detection (D):** `_infer_type` / `profile_table` now also tag `categorical`
  (low-cardinality repeating values) and `ordinal` (values matching a built-in ordered lexicon,
  `ORDINAL_SCALES`). Advisory only — informs the recipe, never auto-coerces.
- **String hygiene (C):** opt-in `case`, `strip_specials` and `fix_encoding` (mojibake repair +
  Unicode NFC) options on the `text` type; off by default, every change logged/flagged.
- **Categorical value standardisation (B):** `propose_value_map` clusters inconsistent variants
  of a category (case/punctuation/accent-insensitive, optional master-list snap) and proposes a
  canonical; confirmed clusters bake into the recipe as a `value_map` op on text/categorical/
  ordinal columns. Propose → confirm → apply (never auto-applied); every change logged.
- **Quality/health report (A):** `score_quality` + `render_quality_report` grade a dataset
  (per-column completeness A–F, type consistency, severity-tagged issues, weighted overall
  score) before and after cleaning; `data-tidy` gains a quality-report-only mode.

## 0.1.0 — YYYY-MM-DD

Initial release: extract, tidy, reconcile, visualise skills + shared local data engine (de-branded from internal toolkit).
