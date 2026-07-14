# Theming guide — colours, font, logo

The Data Toolkit's visualise engine ships with **Phronesis Applied** defaults (mark and
palette from [phronesis-applied.com](https://www.phronesis-applied.com)) and is **fully
white-labelable**: a firm sets its own colours, font and logo without touching the code.
Everything lives in `scripts/viz.py` as `DEFAULT_THEME` (with `BRAND` / `FONT` as the active
module-level state). Refer to those tokens, don't hardcode hexes in a caller.

## The default (Phronesis Applied) palette

Colour-token *names* are historical (kept stable so the rendering code doesn't churn); the
**values** match the Phronesis Applied site.

| Token | Default hex | Use | Site variable |
|---|---|---|---|
| `burgundy` | `#163F3A` | primary — header rule, wordmark, table heads (deep teal) | `--accent` |
| `rose` | `#4FB3A0` | accent 1 — bright teal | `--accent-bright` |
| `pink` | `#20574F` | accent 2 — soft teal | `--accent-soft` |
| `pink_lt` | `#A7D9CF` | light teal tint | — |
| `pink_vlt` | `#E7EBE9` | very light tint — table zebra striping | `--paper-2` |
| `ink` | `#14171A` | body text | `--ink` |
| `grey` | `#565C63` | muted text / labels | `--ink-soft` |
| `grey_faint` | `#8C9298` | faintest text | `--ink-faint` |
| `grey_lt` | `#D9DEDB` | hairlines / borders | `--line` |
| `bg` | `#F1F3F2` | page background (paper) | `--paper` |
| `white` | `#FFFFFF` | cards | `--surface` |
| `green` | `#2E7D57` | RAG — good / done / on-track | — |
| `amber` | `#B26B00` | RAG — warning / due / at-risk | — |
| `red` | `#9B2226` | RAG — bad / overdue / breach | — |

> The palette follows the **revised** Phronesis Applied identity: a cool teal/paper scheme.
> The former bronze accent is retired — `rose` is now the site's bright teal.

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

## Fonts

Two stacks, mirroring the site's **Space Grotesk headings / Inter body** pairing:

| Theme key | Default | Applies to |
|---|---|---|
| `font` | `'Inter','Segoe UI','Helvetica Neue',Arial,sans-serif` | body, tables, labels |
| `font_heading` | `'Space Grotesk','Inter','Segoe UI',system-ui,sans-serif` | `h1`, section `h2`, KPI values, the text wordmark |

Dashboards are **self-contained (no CDN)**, so a font only renders if the reader has it
installed — otherwise it falls back down its stack. The pairing is therefore a progressive
enhancement, never a dependency.

A firm sets its own via the theme's `font` / `font_heading` keys. **Setting only `font`
applies it to headings too** — so a white-label brand never inherits Space Grotesk by
accident. Set `font_heading` explicitly only if you want a distinct display face.

## Logo

The header shows a logo if `assets/logo-sample.png` (or a firm-supplied path) is present;
otherwise it falls back to a **text wordmark** of the brand name. The engine **base64-embeds**
the logo as a data URI, so the file stays self-contained and offline — never a remote URL
(that would break the offline / data-handling guarantee). Use a transparent-background PNG so
it blends onto the page.

Shipped assets:

| File | What it is |
|---|---|
| `assets/logo-sample.png` | Default header lockup (Phronesis mark + wordmark) — what `DEFAULT_THEME` points at |
| `assets/logo-phronesis.png` | Same lockup, named copy |
| `assets/logo-phronesis-mark.png` | Square mark only |
| `assets/logo-phronesis-mark.svg` | Source SVG of the mark (from the site favicon geometry) |

> **White-label:** swap `assets/logo-sample.png` or point `theme["logo_path"]` at your own
> transparent PNG. Replacing the file for client work does not grant rights to use the
> Phronesis Applied name or mark in your own branding — see `NOTICE`.

## How a firm sets its own brand

Pass a (partial) `theme` dict — any subset overrides the Phronesis default:

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
  resets to the Phronesis default.

```python
from viz import apply_theme, kpi_row, bar_chart, dashboard
apply_theme(my_theme)                 # charts now use the brand palette
blocks = [kpi_row([...]), bar_chart([...])]
dashboard("Operations dashboard", blocks, theme=my_theme, out_path="dashboard.html")
```
