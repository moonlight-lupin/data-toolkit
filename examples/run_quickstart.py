#!/usr/bin/env python3
"""10-minute quickstart — one recon working paper + one branded dashboard.

Run from the repo root:

    python examples/run_quickstart.py

Writes examples/out/reconciliation.xlsx and examples/out/dashboard.html.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(__file__).resolve().parent / "out"
OUT.mkdir(parents=True, exist_ok=True)

# Skill scripts live under skills/*/scripts/ — put both on the path.
sys.path.insert(0, str(ROOT / "skills" / "data-reconcile" / "scripts"))
sys.path.insert(0, str(ROOT / "skills" / "data-visualise" / "scripts"))
sys.path.insert(0, str(ROOT / "scripts"))  # shared ingest/dataclean if needed

from reconcile import (  # noqa: E402
    PRESETS,
    reconcile_files,
    render_report,
    write_workpaper,
)
from viz import (  # noqa: E402
    apply_theme,
    bar_chart,
    dashboard,
    kpi_row,
    section,
    table,
)


def main() -> int:
    a = ROOT / "skills" / "data-reconcile" / "examples" / "sample_invoice_tracker.csv"
    b = ROOT / "skills" / "data-reconcile" / "examples" / "sample_ledger.csv"
    if not a.exists() or not b.exists():
        print(f"missing sample inputs:\n  {a}\n  {b}", file=sys.stderr)
        return 1

    preset = "invoice_tracker_vs_ledger"
    p = PRESETS[preset]
    al, bl = p["a_label"], p["b_label"]

    print("1/2  Reconciling sample invoice tracker vs ledger …")
    res, exc, summary, _ = reconcile_files(
        str(a), str(b), preset=preset, material="1000", escalate="10000"
    )
    wp = OUT / "reconciliation.xlsx"
    write_workpaper(res, exc, summary, str(wp), a_label=al, b_label=bl)
    print(render_report(
        summary, exc, a_label=al, b_label=bl, title=p["label"]
    ))
    print(f"\nworking paper -> {wp}")

    print("\n2/2  Building branded dashboard from the recon summary …")
    apply_theme(None)  # Phronesis Applied defaults
    n_matched = int(summary.get("matched") or 0)
    n_exc = int(summary.get("exceptions") or len(exc or []))
    by_cat = {
        cat: int(info.get("n") or 0)
        for cat, info in (summary.get("by_category") or {}).items()
    }
    val_matched = summary.get("value_matched", "—")
    val_exc = summary.get("value_in_exception", "—")

    blocks = [
        kpi_row([
            {"label": "Matched (1:1)", "value": n_matched, "status": "green"},
            {"label": "Exceptions", "value": n_exc,
             "status": "red" if n_exc else "green"},
            {"label": "Value matched", "value": val_matched, "status": "brand"},
            {"label": "Value in exception", "value": val_exc,
             "status": "amber" if n_exc else "green"},
        ]),
        section(
            "Exception mix",
            bar_chart(
                sorted(by_cat.items(), key=lambda kv: -kv[1]) or [("none", 0)],
                title="Exceptions by triage category",
            ),
        ),
        section(
            "Top exceptions",
            table(
                [
                    {
                        "Category": e.get("category", ""),
                        "Magnitude": e.get("magnitude", ""),
                        "Materiality": e.get("materiality", ""),
                        "Action": (e.get("action") or e.get("suggested_action") or "")[:80],
                    }
                    for e in (exc or [])[:8]
                ],
                columns=["Category", "Magnitude", "Materiality", "Action"],
                title="Highest-priority items (sample)",
            ),
        ),
    ]
    dash = OUT / "dashboard.html"
    dashboard(
        "Sample reconciliation",
        blocks,
        subtitle="Invoice tracker vs ledger — quickstart demo",
        as_of="14 Jul 2026",
        out_path=str(dash),
    )
    print(f"dashboard    -> {dash}")
    print("\nOpen the HTML in a browser. Open the .xlsx in Excel.")
    print("Done — ~10 minutes of setup, a few seconds of compute.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
