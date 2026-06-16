# Theming guide — colours, font, logo

The Data Toolkit's visualise engine ships with a **clean, neutral default theme** and is
**fully brandable**: a firm sets its own colours, font and logo without touching the code.
Everything lives in `scripts/viz.py` as `DEFAULT_THEME` (with `BRAND` / `FONT` as the active
module-level state). Refer to those tokens, don't hardcode hexes in a caller.

## The default (neutral) palette

A cool slate + blue palette with no firm branding. The colour-token *names* are historical
(kept stable so the rendering code doesn't churn); the **values** are neutral.

| Token | Default hex | Use |
|---|---|---|
| `burgundy` | `#1F3A5F` | primary — header rule, wordmark, table heads, default accent (slate blue) |
| `rose` | `#2E6FB0` | accent 1 — second series, secondary bars (blue) |
| `pink` | `#5B9BD5` | accent 2 — third series (light blue) |
| `pink_lt` | `#A9C7E8` | light tint |
| `pink_vlt` | `#EAF1F8` | very light tint — table zebra striping |
| `ink` | `#1A1C1F` | body text |
| `grey` | `#5F6571` | muted text / labels |
| `grey_lt` | `#E3E6EA` | hairlines / borders |
| `bg` | `#F6F8FA` | page background (cool neutral) |
| `white` | `#FFFFFF` | cards |
| `green` | `#2E7D57` | RAG — good / done / on-track |
| `amber` | `#B26B00` | RAG — warning / due / at-risk |
| `red` | `#9B2226` | RAG — bad / overdue / breach |

## Status keywords

`status=` on cards/pills and the `rag` cell mapper accept friendly synonyms:

- green ← `green`, `ok`, `done`
- amber ← `amber`, `warn`, `due`
- red ← `red`, `bad`, `overdue`
- primary accent ← `brand`, `info`
- grey ← `grey`, `neutral`, or unset

## Chart series order

Multi-series charts and donut slices cycle through:
`primary → accent 1 → accent 2 → green → amber → grey → light tint`
(i.e. `burgundy → rose → pink → green → amber → grey → pink_lt` token names).

## Font

The default `FONT` is a clean geometric/neutral sans with safe fallbacks:

`"'Inter','Segoe UI','Helvetica Neue',Arial,sans-serif"`

No proprietary brand face is assumed. A firm sets its own via the theme's `font` key.

## Logo

The header shows a logo if `assets/logo-sample.png` (or a firm-supplied path) is present;
otherwise it falls back to a **text wordmark** of the brand name. The engine **base64-embeds**
the logo as a data URI, so the file stays self-contained and offline — never a remote URL
(that would break the offline / data-handling guarantee). Use a transparent-background PNG so
it blends onto the page.

> **`assets/logo-sample.png` is a replaceable placeholder.** The toolkit ships a neutral
> sample mark so the header renders out of the box. A firm **swaps it for its own logo** —
> either replace that file in place, or point `theme["logo_path"]` at its own PNG.

## How a firm sets its own brand

Pass a (partial) `theme` dict — any subset overrides the neutral default:

```python
my_theme = {
    "brand_name": "Acme Co",                       # header wordmark fallback + footer
    "logo_path": "assets/acme-logo.png",           # transparent PNG; omit to use the wordmark
    "font": "'Acme Sans','Segoe UI',sans-serif",   # optional
    "colours": {                                   # any subset of the tokens above
        "burgundy": "#0B3D91",   # primary
        "rose":     "#1565C0",   # accent 1
        "pink":     "#42A5F5",   # accent 2
    },
}
```

Two ways to apply it:

- **Per page (shell only):** `dashboard(title, blocks, theme=my_theme)` re-skins the header
  rule, logo/wordmark, fonts and footer brand line for that page.
- **Whole render (incl. chart colours):** call `apply_theme(my_theme)` **before** building the
  blocks, then build and call `dashboard(...)`. `apply_theme` rebinds the module-level
  `BRAND` / `FONT` / series palette so the charts pick up the brand too. `apply_theme(None)`
  resets to the neutral default.

```python
from viz import apply_theme, kpi_row, bar_chart, dashboard
apply_theme(my_theme)                 # charts now use the brand palette
blocks = [kpi_row([...]), bar_chart([...])]
dashboard("Operations dashboard", blocks, theme=my_theme, out_path="dashboard.html")
```
