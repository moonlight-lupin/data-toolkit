#!/usr/bin/env python3
"""White-label quickstart — same recon summary, Acme Co theme + logo.

Run from the repo root:

    python examples/run_branded_dashboard.py

Writes examples/out/branded-dashboard.html. Compare with the Phronesis-default
dashboard from examples/run_quickstart.py.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(__file__).resolve().parent / "out"
ASSETS = Path(__file__).resolve().parent / "assets"
OUT.mkdir(parents=True, exist_ok=True)

sys.path.insert(0, str(ROOT / "skills" / "data-reconcile" / "scripts"))
sys.path.insert(0, str(ROOT / "skills" / "data-visualise" / "scripts"))
sys.path.insert(0, str(ROOT / "scripts"))

from reconcile import PRESETS, reconcile_files  # noqa: E402
from viz import apply_theme, bar_chart, dashboard, kpi_row, section, table  # noqa: E402

# Fictional firm — copy this pattern and point logo_path at your own mark.
ACME_THEME = {
    "brand_name": "Acme Co",
    "logo_path": str(ASSETS / "acme-mark.svg"),
    "font": "'Segoe UI','Helvetica Neue',Arial,sans-serif",
    "colours": {
        "burgundy": "#0B3D91",  # primary
        "rose": "#1565C0",      # accent 1
        "pink": "#42A5F5",      # accent 2
        "bg": "#F5F7FB",
        "ink": "#0F172A",
        "grey": "#475569",
        "grey_lt": "#DBE2EA",
        "pink_vlt": "#E8EEF7",
    },
}


def main() -> int:
    a = ROOT / "skills" / "data-reconcile" / "examples" / "sample_invoice_tracker.csv"
    b = ROOT / "skills" / "data-reconcile" / "examples" / "sample_ledger.csv"
    if not a.exists() or not b.exists():
        print(f"missing sample inputs:\n  {a}\n  {b}", file=sys.stderr)
        return 1
    if not Path(ACME_THEME["logo_path"]).exists():
        print(f"missing sample logo: {ACME_THEME['logo_path']}", file=sys.stderr)
        return 1

    print("1/2  Reconciling sample invoice tracker vs ledger …")
    res, exc, summary, _ = reconcile_files(
        str(a), str(b), preset="invoice_tracker_vs_ledger",
        material="1000", escalate="10000",
    )

    print("2/2  Building Acme-branded dashboard …")
    # Both calls required for a full re-skin: apply_theme → chart colours;
    # dashboard(theme=…) → header, CSS vars, footer, logo.
    apply_theme(ACME_THEME)
    n_matched = int(summary.get("matched") or 0)
    n_exc = int(summary.get("exceptions") or len(exc or []))
    by_cat = {
        cat: int(info.get("n") or 0)
        for cat, info in (summary.get("by_category") or {}).items()
    }

    blocks = [
        kpi_row([
            {"label": "Matched (1:1)", "value": n_matched, "status": "green"},
            {"label": "Exceptions", "value": n_exc,
             "status": "red" if n_exc else "green"},
            {"label": "Value matched", "value": summary.get("value_matched", "—"),
             "status": "brand"},
            {"label": "Value in exception",
             "value": summary.get("value_in_exception", "—"),
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

    dash = OUT / "branded-dashboard.html"
    dashboard(
        "Sample reconciliation",
        blocks,
        subtitle="Invoice tracker vs ledger — Acme Co white-label demo",
        as_of="14 Jul 2026",
        theme=ACME_THEME,
        out_path=str(dash),
    )
    print(f"dashboard -> {dash}")
    print("Open in a browser and compare with examples/out/dashboard.html")
    print("(Phronesis defaults from run_quickstart.py).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
