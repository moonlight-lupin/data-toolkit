# Feedback Brief: Propose-Confirm Mapping for Entity Unification (data-reconcile, data-tidy)

You are implementing a feature in the **data-toolkit** repository at
`/root/projects/data-toolkit`. This brief is self-contained: it contains everything you
need. Work through it in order. Do not invent requirements beyond it.

## Repository facts

- Python 3, stdlib-first. Hard dependency: `openpyxl` only (`requirements.txt`).
  The repo deliberately avoids runtime deps beyond that — **do not add any dependency**.
  `difflib` (stdlib) is the approved similarity engine.
- Money handling uses `Decimal`. Never introduce `float` for money values.
- Run tests:
  - `python3 tests/test_engine.py` (standalone, no pytest)
  - `python3 -m pytest tests/ -q` (full suite, currently 114 passing)
  - `python3 bin/data-lint` (authoring gate — must pass)
- Conventions: read `AGENTS.md` and `PRINCIPLES.md` before writing code. The behavioral
  charter "drafts not advice, never invent, human-in-the-loop" governs design. The
  existing reuse-bundle mechanism is `emit_runner(...)` in `scripts/dataclean.py` —
  study it before building the persistence format (section 3).

## 1. The gap (standalone statement of need)

Finance data arrives with entity/name values that refer to the same real-world thing but
are spelled differently: `DBS Bank` vs `DBS Bk`, `Acme Pte Ltd` vs `ACME PTE. LTD.`,
`Mr Tan` vs `Tan, Ah Kow`. Two existing skills hit this wall:

- **data-reconcile** matches record sets on exact keys or exact amount+date. A one-character
  difference in the counterparty name forces a manual exception that the tool should have
  matched.
- **data-tidy** standardises formats (dates, currencies) but not *identity* — near-duplicate
  entity names pass through as distinct values, and downstream group-by/concentration
  analysis silently splits one counterparty into several.

A mapping from raw values → canonical values, reviewed by a human once and reused after,
removes both failure modes while keeping matching fully deterministic.

## 2. The feature

A new shared helper module **`scripts/namemap.py`** at the toolkit root, plus thin
wiring into the two skills. The core loop:

1. **Cluster** near-duplicate values of a chosen column using `difflib.SequenceMatcher`
   similarity (default threshold 0.85, configurable). Comparison is casefolded and
   whitespace-normalised (punctuation like `.,` `Ltd` suffix handling is NOT in scope —
   raw similarity only; do not hardcode business suffix lists).
2. **Propose** a canonical value per cluster (the longest/most frequent raw value; tie-break
   alphabetically — must be deterministic). Output a **proposed mapping** as an ordered list
   of `{raw, canonical, score, cluster_size}` records. Values with no near-duplicate pass
   through unmapped.
3. **Human confirmation is mandatory.** The mapping file is a *draft* until confirmed.
   The workflow (as with extraction runners today): agent presents the proposal, the user
   edits/confirms, then the mapping is saved and becomes a deterministic lookup. No engine
   function may apply a mapping without an explicit `approved: true` marker in the file.
4. **Apply** the confirmed mapping to rows: exact match on raw value → canonical. Unmatched
   rows are left untouched and counted (never force-fitted).
5. **Reuse**: the confirmed mapping file is the durable artifact. It must run standalone
   through a generated runner (see section 3, acceptance criterion 5).

### Mapping file format

JSON, written to the working folder (not into the repo):

```json
{
  "kind": "namemap",
  "version": 1,
  "field": "Counterparty",
  "approved": false,
  "threshold": 0.85,
  "mapping": [
    {"raw": "DBS Bk", "canonical": "DBS Bank", "score": 0.91},
    {"raw": "ACME PTE. LTD.", "canonical": "Acme Pte Ltd", "score": 0.88}
  ]
}
```

Schema goes in `schemas/namemap.schema.json` (JSON Schema draft 2020-12, matching the
style of the existing six schemas — validate with the same loading approach
`agent_schemas.py` uses today).

### Module API (exact signatures required)

```python
from scripts.namemap import (
    propose_mapping,    # (values: list[str], threshold: float = 0.85) -> dict
    load_mapping,       # (path: str | Path, require_approved: bool = True) -> dict
    apply_mapping,      # (header: list[str], rows: list[list], field: str, mapping: dict) -> tuple[list[str], list[list], dict]
)
```

- `propose_mapping` returns the full mapping-file dict (shape above) with `approved: false`.
- `load_mapping` raises a clear error when `require_approved=True` and `approved` is not
  `true`. This is the enforcement point for the human-in-the-loop rule.
- `apply_mapping` returns `(new_header, new_rows, stats)` where
  `stats = {"field": ..., "total_rows": N, "renamed": n, "distinct_before": b,
  "distinct_after": a}`. If `field` is not in `header`, raise `ValueError` with the
  field name in the message.
- All operations are pure functions — no network, no filesystem except `load_mapping`.
- Self-test block: follow the `--self-test` pattern used by `scripts/dataclean.py`,
  `skills/data-analyse/scripts/analyse.py`, and `skills/data-convert/scripts/convert.py`;
  `bin/data-lint --engine` must stay green.

## 3. Integration points (touch ONLY these)

1. **`data-tidy`** — new optional recipe step `"dedupe_names"`:
   `{"op": "dedupe_names", "field": "Counterparty", "mapping_path": "namemap.json"}`
   (path optional; when absent, the step proposes to `.data-tidy-namemap.json` in the
   working dir and stops for confirmation; when present it applies and reports `stats` in
   the change report). Wire it in the recipe dispatcher wherever `dataclean.apply_recipe`
   dispatches ops — the SKILL.md step tables and the tidy section of `skills/data-tidy/SKILL.md`
   gain one row each.
2. **`data-reconcile`** — new optional pre-step in the reconcile config: canonicalise the
   chosen key field on both sides A and B from the same mapping file before matching.
   Config keys: `"canon_field"` + `"canon_mapping"` (path). When absent, behavior is
   unchanged (backward compatible). Document in `skills/data-reconcile/SKILL.md` (+ its
   `references/` if the matching details live there) and
   `schemas/reconciliation-config.schema.json` (additive optional properties only —
   read that schema first and preserve `additionalProperties: false`).
3. **`scripts/agent_schemas.py` / `agent_runtime.py`** — only where needed to validate
   the new plan keys for the two skills, following the existing per-skill validation
   pattern. Do not restructure anything.

## 4. Acceptance criteria

- [ ] `scripts/namemap.py` exists with the three functions above; pure stdlib; `--self-test` green.
- [ ] `schemas/namemap.schema.json` exists, draft 2020-12, additive style consistent with siblings.
- [ ] Proposing on a mixed list like `["DBS Bank", "DBS Bk", "Acme Pte Ltd", "ACME PTE. LTD.", "Beta LLC"]`
      clusters exactly {DBS Bank, DBS Bk} and {Acme Pte Ltd, ACME PTE. LTD.}, leaves `Beta LLC`
      alone, and is deterministic across runs (assert twice, same output).
- [ ] `load_mapping` on a file with `approved: false` raises; with `approved: true` returns the mapping.
- [ ] `emit_runner`-style reuse: a helper `emit_namemap_runner(folder, name)` (in the same
      module or `dataclean.py`, mirroring the existing runner-emit pattern) writes a
      self-contained `.py` + `.md` card + copies of the needed engine files so the bundle
      runs without the plugin installed.
- [ ] data-tidy: `dedupe_names` recipe step works through `dataclean.apply_recipe`; the
      change report includes the stats dict; unapproved mapping → clear error, no silent apply.
- [ ] data-reconcile: with `canon_field`+`canon_mapping` set, matching improves on the
      near-duplicate fixture (assert a case that only matches after canonicalisation);
      without them, all existing reconcile behavior is unchanged.
- [ ] Reconciliation working-paper output gains no new required columns (canonical label may
      appear as an extra column when the feature is on; when off, output is byte-identical in
      structure to today's).
- [ ] New tests live in `tests/test_engine.py` in the established style (section number,
      standalone-runnable; they must FAIL before the implementation exists — develop test-first).
- [ ] Full suites pass: pytest 114+new, all three standalone runners green, `bin/data-lint` green,
      `examples/run_quickstart.py` still exits 0.
- [ ] No new runtime dependency; no `float` for money; no network calls.
- [ ] `plugin.json` version bump (minor) + CHANGELOG entry in the established voice.

## 5. Optional dependencies (only if trivial)

- A `--dry-run` flag on the runner that prints the proposed mapping without writing.

## 6. General constraints

- **Additive only.** Do not refactor existing functions; do not rename anything; do not
  reorder SKILL.md content beyond adding the documented rows/sections.
- **Deterministic engine, human-in-the-loop.** The engine clusters/counts; the human
  approves identity claims. An unapproved mapping must be unusable, not just warned about.
- **Never invent.** Unmatched values pass through unchanged with a count; nothing is
  force-fitted to a canonical value.
- **Tests required** for every new behavior; tests written before production code.
- **No PII, no live config, no credentials** in any committed file. Fixture data is
  synthetic (DBS/Acme/Beta style).
- Lint (`bin/data-lint`) must pass; LF line endings; no stray HTML-ish tags in `.md` files
  (the linter checks).

## 7. Out of scope

- Fuzzy matching on amounts/dates (reconcile already does exact amount+date).
- Embedding-model similarity, LLM calls, phonetic algorithms (soundex etc.).
- Any UI/Playground work.
- Modifying the other four skills or the agent-runtime approval/receipt machinery beyond
  the two documented integration points.