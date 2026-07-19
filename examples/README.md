# Examples — 10-minute path

Prove the toolkit on your machine with one reconciliation and one dashboard. No Claude
required for this path — plain Python. Broader walkthrough (install → brand → first
job): see the README's [Install](../README.md#install-claude-code-plugin) and
[Try it in ~10 minutes](../README.md#try-it-in-10-minutes) sections.

## Prerequisites

```bash
pip install openpyxl          # the one hard dependency
# optional: already enough for this quickstart
```

From the **repo root**:

```bash
python examples/run_quickstart.py
python examples/run_branded_dashboard.py   # optional — white-label demo
```

That writes:

| Output | What it is |
|---|---|
| `examples/out/reconciliation.xlsx` | Invoice-tracker vs ledger working paper (matches + triaged exceptions) |
| `examples/out/dashboard.html` | Self-contained dashboard with the **neutral default** theme |
| `examples/out/branded-dashboard.html` | Same recon summary, **Acme Co** theme + sample logo |

Prefer to look first? Committed samples (same content):

- [`sample-reconciliation.xlsx`](sample-reconciliation.xlsx)
- [`sample-dashboard.html`](sample-dashboard.html) — neutral default
- [`sample-branded-dashboard.html`](sample-branded-dashboard.html) — Acme Co white-label

Open the HTML file in a browser. Open the `.xlsx` in Excel / LibreOffice / Numbers.

## What you just ran

1. **`data-reconcile`** on the shipped sample pair
   (`skills/data-reconcile/examples/sample_invoice_tracker.csv` vs
   `sample_ledger.csv`) with the `invoice_tracker_vs_ledger` preset — deliberate
   mismatches so the triage sheet has something useful to show.
2. **`data-visualise`** — KPI cards from the recon summary plus a small exception
   breakdown chart. `run_quickstart.py` uses the neutral default;
   `run_branded_dashboard.py` passes an Acme `theme` (colours +
   [`assets/acme-mark.svg`](assets/acme-mark.svg)).

## White-label in one minute

```python
apply_theme(MY_THEME)                         # chart colours
dashboard(title, blocks, theme=MY_THEME, ...) # header, CSS, footer, logo
```

Both calls matter. Full palette / logo rules:
[`../skills/data-visualise/references/brand.md`](../skills/data-visualise/references/brand.md).

## Next

- Point the same scripts at your own CSVs / `.xlsx` exports.
- Swap `logo_path` and the three primary colour tokens for your firm.
- In Claude Code: install the plugin, then say *"reconcile these two files"* or
  *"build a dashboard from this sheet using our brand"*.
