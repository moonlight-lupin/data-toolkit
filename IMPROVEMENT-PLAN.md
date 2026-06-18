# Data Toolkit — improvement plan (borrowing from `data-cleaner`)

Source of ideas: the **Data Cleaner** skill (brook-miller, mcpmarket / GitHub). It is a
narrower CSV/Excel-only subset of our `data-tidy`, but it has a few sharper cleaning
primitives worth folding into our shared engine. No new skill, no new dependencies
(stdlib only — `unicodedata` for accent-folding / NFC, a small map for mojibake repair).

## Gap analysis

| `data-cleaner` capability | Our toolkit today | Verdict |
|---|---|---|
| Data quality **scoring** — overall score, per-column completeness **grade**, severity-tiered issues | `profile_table` gives raw stats, no scored report | **Gap (A)** |
| Semantic type detection incl. **categorical + ordinal** | `_infer_type` = text/number/currency/date/bool | **Gap (D)** |
| **Categorical value standardisation** — cluster variants → canonical map | row dedupe + master-list *validation* only | **Gap (B) — highest value** |
| String hygiene — **casing**, special-char strip, encoding/mojibake repair | `text` only trims + collapses whitespace | **Gap (C)** |
| Generates reusable Python scripts | `emit_runner` already does this | ✅ ahead |

Where we are already ahead and must not regress: multi-source ingest (PDF/OCR/docx/.msg/
paste), reconcile/extract/visualise breadth, local-PII posture + egress hooks + principles
charter, intent-first human-in-the-loop confirmation.

## Decisions

- Build all four (A, B, C, D). Deliver A by **extending `data-tidy` in place** — no new skill.
- Keep the charter intact: nothing standardised or merged silently; everything flagged and
  confirmed; no new external deps.

## Work items (sequenced: D → C → B → A)

### D — Semantic type detection  *(foundation for A and B)*
- Extend `dataclean._infer_type` to also return `categorical` (low cardinality vs row count)
  and `ordinal` (values matching a built-in ordered lexicon — Low/Med/High, XS–XL, ratings,
  weekdays; extensible). Advisory only — informs the recipe, never auto-coerces.
- Surface the semantic type in `render_profile`.
- Status: **DONE**

### C — String hygiene options on the `text` type  *(independent, cheap)*
- Add to the `text` type in `_convert`: `case` (lower/upper/title/sentence),
  `strip_specials`, `fix_encoding` (mojibake repair + Unicode NFC). Off by default,
  deterministic, every change logged (soft-flagged for audit).
- Document the new options in `recipe-spec.md`.
- Status: **DONE**

### B — Categorical standardisation  *(highest value)*
- `propose_value_map(values, master=None)` — cluster near-variants (case/punctuation/accent
  folded, optional token-sort), pick a canonical per cluster (most frequent, or snap to a
  master list), return clusters + confidence.
- New recipe op (a `standardise` / `value_map` field on a column) applied only after the
  user confirms the proposed clusters (same HITL pattern as `data-reconcile` aggregation).
  Every value change logged in the change report.
- Update `recipe-spec.md` + `data-tidy/SKILL.md`.
- Status: **DONE** — `propose_value_map` / `render_value_map_proposals` /
  `value_map_from_clusters` + `value_map` recipe op (on text/categorical/ordinal), fold-based
  matching (case/punctuation/accent-insensitive), master-snap, HITL confirm. Verified.

### A — Quality / health report  *(extend `data-tidy` in place)*
- `score_quality(header, rows, prof)` → per-column completeness grade A–F, type-consistency
  %, severity-tagged issues (high-null, mixed-type, near-dup categories, whitespace/encoding
  noise); weighted overall score + grade. `render_quality_report(...)` for text/markdown.
- `data-tidy` gains a quality report before the recipe + a before/after after apply, and a
  documented "just give me a data quality report" mode (profile + score, deliver, stop).
  Optional: feed `data-visualise` for an HTML scorecard.
- Update `data-tidy/SKILL.md`.
- Status: **DONE** — `score_quality` (per-column completeness grade A–F, type consistency,
  severity-tagged issues incl. standardisation candidates + whitespace/encoding noise;
  weighted overall score/grade, duplicate-row penalty) + `render_quality_report`;
  quality-report-only mode documented in `data-tidy/SKILL.md`. Verified.

### Cross-cutting
- Extend `dataclean.py --self-test` for each new function. **DONE** (D, C, B, A self-tests).
- Add a messy categorical sample (country/status variants, mojibake) via `make_samples.py`.
  **DONE** — `categorical_survey_csv()` + `examples/messy_categorical_survey.csv`.
- Update `recipe-spec.md`, `data-tidy/SKILL.md`, `CHANGELOG.md`.
- Final verification: run all self-tests + one worked end-to-end on the new sample.
