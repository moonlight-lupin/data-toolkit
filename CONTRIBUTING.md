# Contributing

Thanks for considering a contribution to the **Data Toolkit** (Phronesis Applied).

This is a local-first Claude Code plugin: five skills + a small Python engine. Contributions
that keep numbers honest, outputs reviewable, and data on the user's machine are especially
welcome.

## Before you start

1. Read [`PRINCIPLES.md`](PRINCIPLES.md) — drafts not advice, never invent, stay in lane.
2. Read [`DATA-HANDLING.md`](DATA-HANDLING.md) — PII / confidential data stays local.
3. Skim [`COMPATIBILITY.md`](COMPATIBILITY.md) if you touch Claude Code vs Cowork behaviour.

By contributing, you agree your work is licensed under the same [Apache License 2.0](LICENSE)
as the rest of the project (see also [`NOTICE`](NOTICE)).

## Setup

```bash
git clone https://github.com/moonlight-lupin/data-toolkit.git
cd data-toolkit
python3 -m venv .venv && source .venv/bin/activate   # optional but recommended
pip install -r requirements.txt                      # openpyxl
# optional, only if you need them:
#   pip install PyMuPDF pdfplumber python-docx extract-msg
```

Probe the machine:

```bash
python scripts/envcheck.py
```

## Checks to run before opening a PR

```bash
python bin/data-lint            # plugin manifest + SKILL.md hygiene + engine self-tests
python tests/test_engine.py     # finance-grade regression suite (no pytest required)
python examples/run_quickstart.py   # optional smoke: recon + dashboard
```

CI runs the first two on every push/PR to `main`.

## How to contribute

### Bugs and small fixes

1. Open an issue (or reference an existing one) unless the fix is obvious.
2. Branch from `main`, keep the change focused.
3. Add or extend a regression in `tests/test_engine.py` when the bug is about money,
   matching, currency, or sheet selection.
4. Run the checks above; open a PR with a short "what / why".

### New engine behaviour

Prefer **deterministic Python** for anything numeric. Keep the LLM on the orchestration /
narrative side. Match existing patterns: exact `Decimal`, logged transforms, never silent
coercion of unparseable values.

### New or changed skills

- One folder under `skills/<name>/` with a `SKILL.md` front matter (`name` == folder name)
- Description: **single line**, non-empty, ≤ 1024 characters (enforced by `bin/data-lint`)
- Point at `PRINCIPLES.md` and `DATA-HANDLING.md` rather than restating them
- State a clear **"does NOT do"** boundary
- Add a tiny synthetic example under `examples/` when it helps reviewers

### Docs / examples

Welcome. Keep British English, dates as **DD MMM YYYY**, and the "draft for review" posture
in any sample output.

## Pull request tips

- Prefer small PRs over large ones
- Do not commit `.env`, real client data, or generated `examples/out/` artefacts
- Do not use the Phronesis Applied mark in third-party branding — white-label via `theme`
  (see [`NOTICE`](NOTICE) and `skills/data-visualise/references/brand.md`)
- Feedback from using a skill in the wild can also be captured with the template in
  [`FEEDBACK.md`](FEEDBACK.md)

## Questions

Email [hello@phronesis-applied.com](mailto:hello@phronesis-applied.com) or open a GitHub
discussion/issue. Security reports: see [`SECURITY.md`](SECURITY.md) (please email, don't
file a public issue).
