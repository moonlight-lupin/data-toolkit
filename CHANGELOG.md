# Changelog

## 0.4.2 — 2026-07-14

Pre-release polish:

- Changelog `0.1.0` date filled in; removed unfinished “de-branded from internal toolkit”
  wording from history.
- Visualise docs and footer aligned with Phronesis Applied defaults (no more “slate + blue
  neutral” / “— internal” on public artefacts).
- `.gitignore` tightened (`.env`, self-test workbooks); `AGENTS.md` skill count corrected;
  minimal `requirements.txt` added for public installers.
- Added [`SECURITY.md`](SECURITY.md), [`CONTRIBUTING.md`](CONTRIBUTING.md), and a GitHub
  Actions CI workflow (`bin/data-lint` + `tests/test_engine.py` + quickstart smoke on
  Python 3.10–3.12).

## 0.4.1 — 2026-07-14

Open lander under **Phronesis Applied** (on top of 0.4.0):

- **Apache-2.0 license** (`LICENSE` + `NOTICE`) — free to use, fork, and build on commercially.
- **Phronesis Applied branding** — marketplace/plugin author and README footer point at
  [phronesis-applied.com](https://www.phronesis-applied.com); visualise defaults use the
  site mark (from the published favicon geometry) and teal/bronze/paper palette. Still
  fully white-labelable via `theme`.
- **10-minute path** — `examples/run_quickstart.py` builds a sample recon working paper and
  branded dashboard; committed look-first samples at `examples/sample-reconciliation.xlsx`
  and `examples/sample-dashboard.html`.

## 0.4.0 — 2026-07-14

`data-analyse` — four new playbooks and a two-dataset capability:

- **Cross-domain / relational** — relate **two** datasets on a shared key (sales vs competitor
  prices, actual vs budget, spend vs revenue). New engine primitives `join_on` (key-join with a
  matched / left-only / right-only **coverage** report) and `compare_series` (gap / ratio / %
  diff per key, Pearson correlation, ±1 lead/lag). Discipline: association, never cause — the
  brief names the confounders. Distinct from `data-reconcile` (which matches to find breaks).
- **General ledger / trial balance** — net movement & turnover by account, unusual postings
  (large/round/period-end), posting concentration by user/source, debit=credit integrity check.
- **Inventory / stock** — ABC concentration (80/20 by value), slow-mover ageing (write-down
  risk), turnover, negative/zero-stock flags.
- **Spend / AP analysis** — vendor/category concentration, duplicate-payment risk flags,
  maverick (off-contract) spend, threshold-splitting.
- Five synthetic example datasets (incl. the sales/competitor pair) under
  `skills/data-analyse/examples/`, each seeded with the findings its playbook surfaces and
  verified end-to-end against the engine.

## 0.3.0 — 2026-07-13

New skill, generic data-handling, and toolkit tooling:

- **New skill `data-analyse`.** Analyse a dataset into an insight brief — headline findings,
  key metrics tailored to the data type (trends, breakdowns/concentration, outliers, ageing),
  honest caveats. Compute-then-interpret: every quoted figure comes from a deterministic local
  engine (`skills/data-analyse/scripts/analyse.py`, exact `Decimal`, currency-aware); the
  narrative only interprets. Benchmarked 100% vs 83% against a no-skill baseline over four
  evals (incl. a 4,042-row messy mixed-currency stress file), with zero numeric errors.
- **Generic PII data-handling.** `DATA-HANDLING.md` now gates the two classes a white-label
  toolkit should gate — personal data (PII) and confidential business/financial data —
  instead of a firm-specific model. The egress architecture (tokenise-on-egress, local token
  map, deliberate-purpose carve-out) is unchanged; the egress-guard hook was generalised to
  match (adds email/phone/ID detection).
- **`bin/data-lint`.** A fast, dependency-free authoring gate: checks the plugin manifest and
  every skill description (single-line, non-empty, ≤ 1024 chars), guards against truncated
  sections and stray tags, and runs the engine self-tests.
- **Installable as a plugin.** Added `.claude-plugin/marketplace.json` so the repo is its own
  marketplace — `/plugin marketplace add moonlight-lupin/data-toolkit` then
  `/plugin install data-toolkit@data-toolkit`. Pinned LF via `.gitattributes`.

## 0.2.1 — 2026-07-05

Day-to-day finance strengthening (reconciliation):

- **Separate Debit / Credit columns.** `match(..., debit=, credit=)` (CLI `--debit/--credit`)
  builds the signed amount as debit − credit — the standard bank/GL export layout. A side
  without those columns falls back to its amount column, so a debit/credit file reconciles
  directly against a signed-amount file.
- **Case-insensitive column resolution.** Configured column names now resolve against each
  side's actual headers case- and whitespace-insensitively (`amount` finds `Amount `), per
  side — no more everything-lands-in-a_only because a bank CSV capitalises its headers.
- **Opposite sign conventions.** `flip_b=True` (CLI `--flip-b`) negates B's amounts before
  comparing, for pairs that book the same money with opposite signs (bank statement vs the
  GL cash account).
- **Statement completeness check.** `check_balance()` (CLI `--opening-a/--closing-a`,
  `--opening-b/--closing-b`) verifies opening + net movement = stated closing and reports
  TIES / DOES NOT TIE in the working paper header — catching truncated/filtered extracts
  before they silently "reconcile".
- **Ageing of open items.** `triage(..., as_of=)` (CLI `--as-of`) stamps `age_days` on every
  one-sided exception with a parsed date, surfaced in the report and the Exceptions sheet.
- **GST/VAT/WHT hint.** An `amount_mismatch` whose gap is a common tax rate (5/7/8/9/10/15/20%)
  of the smaller side gains an advisory net-vs-gross note in its probable cause. Advisory
  only — never a category or materiality change.
- **Per-currency summary.** `summarise()` adds `by_currency`; a mixed-currency recon renders
  a per-currency value table and marks the cross-currency headline totals as indicative.
  The Exceptions sheet gains Currency and Age (days) columns.

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

## 0.1.0 — 2026-06-16

Initial release: extract, tidy, reconcile, visualise skills + shared local data engine.
