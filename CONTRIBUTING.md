# Contributing

Thanks for considering a contribution to the **Data Toolkit** (Phronesis Applied).

This is a local-first Claude Code plugin: six skills + a small Python engine. Contributions
that keep numbers honest, outputs reviewable, and data on the user's machine are especially
welcome.

## Before you start

1. Skim the [Install](README.md#install-claude-code-plugin) and
   [Try it in ~10 minutes](README.md#try-it-in-10-minutes) sections of the README if you
   are new to the toolkit (incl. theme + logo).
2. Read [`PRINCIPLES.md`](PRINCIPLES.md) — drafts not advice, never invent, stay in lane.
3. Read [`PRINCIPLES.md`](PRINCIPLES.md) — PII / confidential data stays local.
4. Skim the [Mode & environment compatibility](README.md#mode--environment-compatibility)
   section of the README if you touch Claude Code vs Cowork behaviour.

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
python examples/run_quickstart.py          # optional smoke: recon + Phronesis dashboard
python examples/run_branded_dashboard.py   # optional: same data, Acme Co theme + logo
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
- Do not use the Phronesis Applied name or marks in third-party branding — the toolkit ships
  unbranded; white-label via `theme` (see the README's
  [theme + logo](README.md#put-your-brand-on-a-dashboard-theme--logo) section, [`NOTICE`](NOTICE),
  and `skills/data-visualise/references/brand.md`)

## Skill feedback format

When a user wants to suggest an improvement or report a problem with a skill, capture it in
the format below so the skill author gets consistent, on-point, actionable input.

> **Don't just fix it silently and move on** — also record the feedback so the underlying skill
> improves for everyone.

### How to capture it

1. Identify **which skill** the feedback is about (e.g. `data-visualise`).
2. Fill the template below from the conversation — ask only for what's missing.
3. **Write it to a plain text file** named `feedback_[skill]_[YYYY-MM-DD].txt` in the user's
   working/output folder (one file per feedback item).
4. **Hand the `.txt` file to the user** — they file it wherever it needs to go. Collection is
   manual; there's no automated routing.
5. If the user also wants it fixed now and it's in scope, fix it *and* still produce the
   feedback `.txt` so the improvement is recorded for the author.

### Feedback template

```
### [YYYY-MM-DD] — [skill-name] — [one-line title]
- Reporter:        [name / team]
- Type:            Bug | Enhancement | Docs/clarity | New capability
- Severity:        Blocker | Friction | Nice-to-have
- What I was doing: [the task / goal]
- Input / context:  [what was provided — file, values, options]
- What happened:    [actual behaviour or output — quote it, don't paraphrase]
- What I expected:  [the correct / desired behaviour]
- Impact:           [what it cost — time, risk, a wrong output that went out]
- Suggested fix:    [if you have one; optional]
- Example / file:   [path or snippet that reproduces it]
```

### What makes feedback on-point

- **One issue per entry.** Split unrelated points into separate entries.
- **Be specific and reproducible** — name the exact column / cell / section / variable, and the
  exact input that triggers it. "The totals were wrong" is weak; "row-27 GST went to column J
  instead of the Total in K when GST=0" is actionable.
- **Quote the actual output**, don't summarise it.
- **Separate Bug from Enhancement.** A Bug = it did something wrong; an Enhancement = it works
  but could do more. They're triaged differently.
- **State the impact** so severity is clear (a wrong figure on a payment form is a Blocker; a
  phrasing preference is Nice-to-have).

### Severity guide

| Severity | Meaning |
|---|---|
| **Blocker** | Wrong/unsafe output, or the skill can't complete the task — must fix before relying on it. |
| **Friction** | Works but takes extra manual steps, re-prompting, or clean-up. |
| **Nice-to-have** | Polish, wording, an optional extra capability. |

## Questions

Email [hello@phronesis-applied.com](mailto:hello@phronesis-applied.com) or open a GitHub
discussion/issue. Security reports: see [`SECURITY.md`](SECURITY.md) (please email, don't
file a public issue).
