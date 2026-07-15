# Onboarding

Get from zero to a real artefact in four short steps. No Claude required for steps
1–3; step 4 is optional if you use Claude Code.

## 1. Install

**Claude Code plugin** (interactive session):

```
/plugin marketplace add moonlight-lupin/data-toolkit
/plugin install data-toolkit@data-toolkit
```

**Or scripts only** — clone this repo and install the one hard dependency:

```bash
pip install openpyxl
```

Optional extras (only for the inputs you use): `PyMuPDF`, `pdfplumber`, `python-docx`,
`extract_msg`, and system Tesseract for OCR. Probe the machine with:

```bash
python scripts/envcheck.py
```

## 2. Run the 10-minute quickstart

From the repo root:

```bash
python examples/run_quickstart.py
```

You get a reconciliation working paper and a dashboard (the neutral default theme) under
`examples/out/`. Prefer to look first?

- [`examples/sample-reconciliation.xlsx`](examples/sample-reconciliation.xlsx)
- [`examples/sample-dashboard.html`](examples/sample-dashboard.html)

## 3. Put your brand on a dashboard (theme + logo)

The toolkit ships **unbranded** (a neutral "Data Toolkit" wordmark, no logo). Your brand
is a `theme` dict — brand name, logo path, fonts, and any colour overrides. Token names
(`burgundy`, `rose`, `pink`) are historical; set `burgundy` to your primary.

```bash
python examples/run_branded_dashboard.py
```

That writes `examples/out/branded-dashboard.html` with a fictional **Acme Co** theme
and the sample mark at [`examples/assets/acme-mark.svg`](examples/assets/acme-mark.svg).
Committed look-first sample:
[`examples/sample-branded-dashboard.html`](examples/sample-branded-dashboard.html).

Minimal pattern (both calls matter — charts + page shell):

```python
from viz import apply_theme, kpi_row, dashboard

MY_THEME = {
    "brand_name": "Acme Co",
    "logo_path": "examples/assets/acme-mark.svg",  # transparent PNG/SVG, < 1 MB, local
    "font": "'Segoe UI','Helvetica Neue',Arial,sans-serif",
    "colours": {
        "burgundy": "#0B3D91",  # primary — header rule, table heads
        "rose":     "#1565C0",  # accent 1
        "pink":     "#42A5F5",  # accent 2
    },
}

apply_theme(MY_THEME)  # chart / KPI colours
blocks = [kpi_row([{"label": "Matched", "value": 42, "status": "green"}])]
dashboard(
    "Weekly scorecard",
    blocks,
    theme=MY_THEME,  # header, CSS, footer, logo
    as_of="14 Jul 2026",
    out_path="acme-dashboard.html",
)
```

**Logo checklist**

- Local file only (no URL) — the engine base64-embeds it so the HTML stays offline
- Prefer transparent PNG; SVG / JPG / GIF also work
- Keep under 1 MB; with no `logo_path` (the default), you get a text wordmark of `brand_name`
- Using the toolkit does **not** grant any right to the Phronesis Applied name or marks in
  your own branding — see [`NOTICE`](NOTICE)

Full palette and status keywords:
[`skills/data-visualise/references/brand.md`](skills/data-visualise/references/brand.md).

## 4. First real job

| You have… | Say / run… |
|---|---|
| Two record sets to match | *"Reconcile these two files"* → `data-reconcile` |
| A junk export | *"Tidy this export"* → `data-tidy` |
| PDFs / Word / `.msg` | *"Extract the table from these"* → `data-extract` |
| A clean sheet + a stakeholder | *"Dashboard this for the controller, Acme brand, logo at …"* → `data-visualise` |
| A dataset to understand | *"What does this data say?"* → `data-analyse` |
| Data for another system's format | *"Convert this to X's import format"* → `data-convert` |

A common chain: extract → tidy → reconcile → analyse exceptions → visualise one-pager.

Standing rules (drafts not advice; data stays local): [`PRINCIPLES.md`](PRINCIPLES.md),
[`DATA-HANDLING.md`](DATA-HANDLING.md).

## Sanity checks

```bash
python bin/data-lint
python tests/test_engine.py
```

More detail: [`examples/README.md`](examples/README.md), [`CONTRIBUTING.md`](CONTRIBUTING.md),
[`COMPATIBILITY.md`](COMPATIBILITY.md).
