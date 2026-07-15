# Agent fast path

Use this page first. Open the longer skill document only when the route below says to.

1. Identify the job:
   - document or form → `data-extract`
   - messy table → `data-tidy`
   - two record sets that must tie → `data-reconcile`
   - metrics or insight → `data-analyse`
   - HTML dashboard → `data-visualise`
   - target-system mapping or reshape → `data-convert`
2. Ask only for missing intent: purpose, expected output, and any governing rules.
3. Inspect the source: `python bin/data-toolkit inspect SOURCE`.
4. Reuse an existing confirmed plan/card when its expected source still matches.
5. Otherwise create a version-1 plan using `python bin/data-toolkit schema` as the catalogue.
6. Validate the declarative payload while drafting:
   `python bin/data-toolkit validate-spec SKILL SPEC.json`.
7. Validate the complete plan:
   `python bin/data-toolkit validate PLAN.json --no-source-check` while editing, then without that flag.
8. Repair schema errors at the reported JSON pointer. Do not guess around them.
9. Show the plan/spec and obtain primary confirmation for confirm-first skills.
10. Dry-run: `python bin/data-toolkit run PLAN.json --dry-run`.
11. If `needs_approval`, stop. Surface the concrete request; never manufacture a receipt.
12. Run the approved plan and retain a machine report:
    `python bin/data-toolkit run PLAN.json --json-report run-result.json`.
13. Deliver every listed artefact plus warnings, exceptions and caveats.

Open the skill's `SKILL.md` when intent is ambiguous, the source is messy or unusual, interpretation
is required, a reusable card/runner is being designed, or recovery below does not resolve the issue.

Recovery:
- schema error → fix the exact pointer, revalidate;
- missing/multi-sheet source → inspect/list and ask, never choose silently;
- dirty input for analyse/convert/reconcile → route through `data-tidy`;
- drift or aggregation approval → return the approval request unchanged;
- engine/import failure → run `scripts/envcheck.py`, then consult `COMPATIBILITY.md`;
- unsupported job → state the boundary and route to the appropriate non-data skill.
