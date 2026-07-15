# Changelog

## 0.5.0 — 2026-07-15

**New skill: `data-convert`** — the toolkit's sixth skill, and the **interoperability**
counterpart to `data-tidy` (tidy = quality; convert = interoperability). It re-expresses a
clean-enough source in the structure or contract a *different* system needs, and delegates any
cleaning back to `data-tidy`.

- **Contract mapping** — map a source onto another system's import contract (columns, order,
  types, required fields), flagging unmapped source columns and required-but-missing target
  fields — never invented. Computes: `debit_minus_credit`, `sum`, `concat`, `fx_convert`,
  `lookup`, `const`, `as_is`.
- **Structural reshape** — `unpivot` (wide→long), `pivot` (long→wide), `flatten`/`nest`
  (JSON↔table), `split` (one file→many), `union` (many→one, column-aligned).
- **Enrich (`lookup`)** — translate a source value via a reference file or inline map (internal
  code → target chart-of-accounts code), with `on_missing` = keep/blank/error.
- **Output validation** — per-target-column `allowed` / `pattern` / `max_len` / `check`
  (IBAN mod-97, BIC format), surfaced before delivery.
- **Row filter** — drop rows (e.g. only posted, non-zero) before mapping.
- **Pinned FX** — a single user-approved rate, or a **date-keyed rate table** for per-row
  conversion by transaction date. The engine **never fetches**; the agent fetches on the user's
  instruction and the value is recorded in the card.
- **Output formats** — CSV / JSON / XLSX / fixed-width, or **populate a provided template**.
- **The reusable artefact is a Markdown conversion card** with an embedded `convert-spec` JSON
  block (no per-conversion `.py`). **Card-first sense-check** flags source drift (renamed/missing/
  new columns, a stale pinned rate) before applying — never blind-applies.
- Ships two example contracts (`journal-import`, `payments-upload`). `convert.py --self-test`
  (14 checks) is now part of the `bin/data-lint` engine gate.

Docs updated for the sixth skill: README (arc + skill table + flow), `COMPATIBILITY.md`,
`references/conversion-spec.md`.

## 0.4.6 — 2026-07-15

Ship **unbranded by default** — the Phronesis Applied theme is no longer the toolkit's default
(so forks/white-label users don't inherit someone else's identity):

- **`data-visualise` `DEFAULT_THEME` is now neutral** — `brand_name` `"Data Toolkit"` and **no
  default logo** (the header shows a text wordmark). The teal/paper palette and the type pairing
  stay as a generic default; token names are unchanged, so existing white-label themes keep
  working. `logo_path` may now be `None` (handled everywhere).
- **Removed the Phronesis brand assets** (`logo-phronesis*.{png,svg}`, `logo-sample.png`); no
  brand mark ships, and there is **no Phronesis theme preset** in the repo.
- Reworded the theming docs/docstrings (`viz.py`, `brand.md`, `blocks.md`, the visualise
  `SKILL.md`, the README white-label bullet, `NOTICE`, `CONTRIBUTING.md`) from "Phronesis
  defaults" to the neutral-default / white-label framing.
- **Authorship is unchanged** — "From Phronesis Applied" stays as the author/maintainer credit in
  the README, plugin/marketplace metadata and the LICENSE/NOTICE copyright.
- Sample dashboards regenerated on the neutral default (content unchanged; styling/wordmark only).

## 0.4.5 — 2026-07-15

Brand refresh — `data-visualise` defaults track the revised Phronesis Applied identity
([phronesis-applied.com](https://www.phronesis-applied.com)):

- **Palette went cool; bronze is retired.** The warm cream/bronze scheme is replaced by the
  site's teal / cool-paper scheme. Values taken from the site's CSS custom properties:
  `rose` → `#4FB3A0` (bright teal, was bronze `#A9722F`), `ink` → `#14171A`, `grey` →
  `#565C63`, `grey_lt` → `#D9DEDB`, `bg` → `#F1F3F2`, `pink_vlt` → `#E7EBE9`, plus a new
  `grey_faint` (`#8C9298`). `burgundy` (`#163F3A`) and `pink` (`#20574F`) are unchanged.
  Token *names* are unchanged, so existing white-label themes keep working.
- **Type pairing.** New `font_heading` theme key — Space Grotesk headings over the Inter body,
  as on the site, applied to `h1`, section `h2`, KPI values and the text wordmark. Dashboards
  stay self-contained (no CDN), so the faces are a progressive enhancement that falls back
  down the stack. A theme that sets only `font` gets it for headings too, so a white-label
  brand never inherits Space Grotesk by accident.
- **Mark recoloured** to the current identity (dark-ink tile, cool-paper glyph, bright-teal
  square) across `logo-phronesis-mark.svg` and the lockup/mark PNGs.
- Committed samples (`examples/sample-dashboard.html`, the visualise example dashboard)
  regenerated on the new brand; content unchanged, styling only. `brand.md` documents the
  palette against the site variables.

## 0.4.4 — 2026-07-15

Honest data-handling claims (correctness fix to the docs):

- **Removed the "your data never leaves the machine" / "nothing uploaded" assertions.** They were
  not defensible: these skills are driven by an AI agent, and whatever the agent reads into its
  context is sent to the AI provider, as in any AI-assisted work. Claiming otherwise was wrong,
  and a compliance answer built on it would have been wrong too.
- **Replaced with what is actually true**, consistently across the README, `DATA-HANDLING.md`,
  `SECURITY.md`, `COMPATIBILITY.md`, all five `SKILL.md` files, the plugin/marketplace
  descriptions and the engine docstrings:
  - the **engine** runs on your machine and makes **no network calls** — no cloud OCR (local
    Tesseract only), no CDN or remote images, no external APIs, no credentials, no connectors,
    no third-party uploads;
  - the **AI agent driving it is not local** — what it reads into context goes to your AI
    provider, and the toolkit says so plainly;
  - no **third party** beyond the AI provider you have already chosen ever sees the data, and
    because the deterministic engine does the heavy lifting the agent generally works with
    samples, profiles and summaries rather than streaming whole datasets through the model.
- `DATA-HANDLING.md` gains a "What is local — and what is not" section as the single source of
  this rule. A generated reuse runner's card still (correctly) states that running it sends
  nothing anywhere — it is plain Python with no model in the loop.

## 0.4.3 — 2026-07-14

Bug fixes and an enhancement surfaced in toolkit testing:

- **`data-reconcile` — amount_date no longer matches on amount alone (Blocker).** In
  `--mode amount_date` with **no resolvable date column** the date window (the mode's safety
  rail) silently short-circuited — equal-amount pairs whose dates were weeks apart passed as
  in-window matches. Now such pairs are held as `ambiguous_match` ("matched on amount alone —
  confirm") and the run **warns** (surfaced in the summary/report); the window is only ever
  applied when a date column resolves.
- **`data-reconcile` — duplicate / sign_flip / amount_mismatch now triaged in amount_date mode.**
  A second pass (`_refine_residues`) over the one-sided residue classifies the bank-vs-cashbook
  staples that key mode gets for free — a double-entered cashbook line (`duplicate`), a debit
  booked as a credit (`sign_flip`), a net-vs-gross GST gap (`amount_mismatch`) — instead of
  leaving them as bare `missing_in_A/B`. Conservative and confirm-first (opposite-equal amounts,
  a common tax ratio, or an exact amount+date twin of an already-matched line).
- **`data-extract` — currency fields keep the code.** A `currency`-typed field now supports
  `code_target`, emitting the detected ISO code into its own key on the record (and column, via
  the new `extract.field_columns(FIELDS)` helper) — so mixed-currency batches (GBP/SGD/USD) are
  no longer delivered as amounts stripped of their code.
- **`data-tidy` — a separate Currency column survives an unparseable amount.** A `currency`
  column may now name a `code_source` column; the code is resolved independently of the amount,
  so a blank/`"pending"` amount keeps its currency (the flag costs the row its *amount*, not its
  *currency*), and a symbol-less amount whose code comes from that column is no longer flagged
  "code unknown".
- Engine self-tests extended to cover each case; `bin/data-lint` green.

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
