# Changelog

## Unreleased

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
