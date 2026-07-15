#!/usr/bin/env python3
"""Golden plans — run all six skills end-to-end through the agent runtime.

A smoke test AND a worked example of the canonical plan shapes. Each plan is
validated (as an agent would) and then executed via the runtime; artefacts land
under out/ (git-ignored). Exits non-zero if any plan fails.

    python examples/golden-plans/run_golden_plans.py

No optional dependencies: the fixtures are CSV / plain text (openpyxl, the one
hard dependency, is only needed to WRITE the tidy/reconcile/extract xlsx outputs).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import agent_runtime as ar  # noqa: E402

PLANS = sorted(HERE.glob("0*-*.json"))


def main() -> int:
    print(f"Running {len(PLANS)} golden plans through bin/data-toolkit's runtime\n")
    ok = True
    for pf in PLANS:
        plan = json.loads(pf.read_text(encoding="utf-8"))
        # 1) validate exactly as the fast-path tells an agent to
        v = ar.validate_plan(plan, base_dir=HERE, check_sources=True)
        if v["status"] == "error":
            print(f"  FAIL  {pf.name:16}  validate -> {v['errors']}")
            ok = False
            continue
        # 2) run it
        r = ar.run_plan(plan, base_dir=HERE)
        status = r["status"]
        arts = [a["path"] for a in r.get("artifacts", [])]
        wrote = all(Path(a).exists() for a in arts)
        good = status in ("success", "success_with_warnings") and (wrote or not arts)
        ok = ok and good
        flag = "OK  " if good else "FAIL"
        print(f"  {flag}  {pf.name:16}  {status:22}  {len(arts)} artefact(s)")
        if not good:
            print(f"        errors={r.get('errors')} warnings={(r.get('warnings') or [])[:1]}")
    print("\n" + ("All golden plans passed." if ok else "SOME GOLDEN PLANS FAILED."))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
