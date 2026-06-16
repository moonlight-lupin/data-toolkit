# Data Toolkit — Skill Feedback

Shared feedback format for **every** skill in this plugin. When a user wants to
suggest an improvement or report a problem with a skill, capture it in this format
so the skill author gets consistent, on-point, actionable input.

> This file is referenced by every skill's "Feedback" section. Keep it as the
> single source of the feedback convention.

## When to use this

A user says something like "this skill should…", "it got X wrong", "it'd be
better if…", "can it also…", or explicitly asks to give feedback on a skill.
**Don't just fix it silently and move on** — also record the feedback in this
format so the underlying skill improves for everyone.

## How to capture it (what Claude should do)

1. Identify **which skill** the feedback is about (e.g. `data-visualise`).
2. Fill the template below from the conversation — ask only for what's missing.
3. **Write it to a plain text file** named
   `feedback_[skill]_[YYYY-MM-DD].txt` in the user's working/output folder
   (one file per feedback item; the template content is the file body).
4. **Hand the `.txt` file to the user** — they file it wherever it needs to go
   (e.g. the team's shared store). Collection is manual and the user handles it;
   there's no automated routing and no path to configure here.
5. If the user also wants it fixed now and it's in scope, fix it *and* still
   produce the feedback `.txt` so the improvement is recorded for the author.

## Feedback template

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

## What makes feedback on-point

- **One issue per entry.** Split unrelated points into separate entries.
- **Be specific and reproducible** — name the exact column / cell / section /
  variable, and the exact input that triggers it. "The totals were wrong" is
  weak; "row-27 GST went to column J instead of the Total in K when GST=0"
  is actionable.
- **Quote the actual output**, don't summarise it.
- **Separate Bug from Enhancement.** A Bug = it did something wrong; an
  Enhancement = it works but could do more. They're triaged differently.
- **State the impact** so severity is clear (a wrong figure on a payment form is a
  Blocker; a phrasing preference is Nice-to-have).
- **Suggest the fix** if you know it — but the symptom + repro matters most.
- **Attach the artefact** (the generated file / the exact text) where possible.

## Severity guide

| Severity | Meaning |
|---|---|
| **Blocker** | Wrong/unsafe output, or the skill can't complete the task — must fix before relying on it. |
| **Friction** | Works but takes extra manual steps, re-prompting, or clean-up. |
| **Nice-to-have** | Polish, wording, an optional extra capability. |

## Example entry

```
### 2026-06-12 — data-tidy — Dates in DD/MM/YYYY mis-parsed as US M/D
- Reporter:        Ops team
- Type:            Bug
- Severity:        Blocker
- What I was doing: Tidying a contacts export with UK-format dates.
- Input / context:  tidy(..., date column "Joined", values like 03/04/2026)
- What happened:    03/04/2026 was read as 4 Mar 2026 instead of 3 Apr 2026.
- What I expected:  DD/MM/YYYY honoured (or a prompt when the format is ambiguous).
- Impact:           ~40 rows had the day/month swapped silently — wrong output went out.
- Suggested fix:    Detect locale or ask up front when day ≤ 12 makes it ambiguous.
- Example / file:   messy_contacts.txt, "Joined" column.
```
