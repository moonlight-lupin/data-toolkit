# Examples — 10-minute path

Prove the toolkit on your machine with one reconciliation and one dashboard. No Claude
required for this path — plain Python.

## Prerequisites

```bash
pip install openpyxl          # the one hard dependency
# optional: already enough for this quickstart
```

From the **repo root**:

```bash
python examples/run_quickstart.py
```

That writes:

| Output | What it is |
|---|---|
| `examples/out/reconciliation.xlsx` | Invoice-tracker vs ledger working paper (matches + triaged exceptions) |
| `examples/out/dashboard.html` | Self-contained branded dashboard (open in any browser; prints to PDF) |

Prefer to look first? Committed samples (same content):

- [`sample-reconciliation.xlsx`](sample-reconciliation.xlsx)
- [`sample-dashboard.html`](sample-dashboard.html)

Open the HTML file in a browser. Open the `.xlsx` in Excel / LibreOffice / Numbers.

## What you just ran

1. **`data-reconcile`** on the shipped sample pair
   (`skills/data-reconcile/examples/sample_invoice_tracker.csv` vs
   `sample_ledger.csv`) with the `invoice_tracker_vs_ledger` preset — deliberate
   mismatches so the triage sheet has something useful to show.
2. **`data-visualise`** with the Phronesis Applied default theme — KPI cards from the
   recon summary plus a small exception breakdown chart.

## Next

- Point the same scripts at your own CSVs / `.xlsx` exports.
- In Claude Code: install the plugin, then say *"reconcile these two files"* or
  *"build a dashboard from this sheet"*.
- White-label the dashboard: see `skills/data-visualise/references/brand.md`.
