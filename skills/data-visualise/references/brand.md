# Theming guide — colours, font, logo

The Data Toolkit's visualise engine ships a **neutral, unbranded default** (no logo, a
teal/paper palette, a clean type pairing) and is **fully white-labelable**: a firm sets its
own name, colours, fonts and logo without touching the code. Everything lives in
`scripts/viz.py` as `DEFAULT_THEME` (with `BRAND` / `FONT` as the active module-level state).
Refer to those tokens, don't hardcode hexes in a caller.

## The default palette

The toolkit's neutral default scheme — a teal accent on cool paper. Colour-token *names* are
historical (kept stable so the rendering code doesn't churn); refer to the names, not the hexes.

| Token | Default hex | Use |
|---|---|---|
| `burgundy` | `#163F3A` | primary — header rule, wordmark, table heads (deep teal) |
| `rose` | `#4FB3A0` | accent 1 — bright teal |
| `pink` | `#20574F` | accent 2 — soft teal |
| `pink_lt` | `#A7D9CF` | light teal tint |
| `pink_vlt` | `#E7EBE9` | very light tint — table zebra striping |
| `ink` | `#14171A` | body text |
| `grey` | `#565C63` | muted text / labels |
| `grey_faint` | `#8C9298` | faintest text |
| `grey_lt` | `#D9DEDB` | hairlines / borders |
| `bg` | `#F1F3F2` | page background (paper) |
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

## Fonts

Two stacks — a **geometric-display heading** over a **neutral sans body**:

| Theme key | Default | Applies to |
|---|---|---|
| `font` | `'Inter','Segoe UI','Helvetica Neue',Arial,sans-serif` | body, tables, labels |
| `font_heading` | `'Space Grotesk','Inter','Segoe UI',system-ui,sans-serif` | `h1`, section `h2`, KPI values, the text wordmark |

Dashboards are **self-contained (no CDN)**, so a font only renders if the reader has it
installed — otherwise it falls back down its stack. The pairing is therefore a progressive
enhancement, never a dependency.

**CJK and other scripts:** when any label/title contains Chinese, Japanese, Korean (or
Arabic, Hebrew, Thai, Indic, Cyrillic, …), `dashboard()` **conditionally** inserts a
browser font-fallback chain (e.g. Microsoft YaHei / PingFang / Noto Sans CJK) before the
generic family so glyphs render instead of □□□. English-only dashboards are unchanged. No
fonts are shipped or looked up on disk — the viewer's OS supplies them. Arabic/Hebrew also
set `dir="rtl"` on the page.

A firm sets its own via the theme's `font` / `font_heading` keys. **Setting only `font`
applies it to headings too** — so a white-label brand never inherits Space Grotesk by
accident. Set `font_heading` explicitly only if you want a distinct display face.

## Logo

**No logo ships by default** — the header shows a **text wordmark** of the brand name
(`"Data Toolkit"` unless a theme overrides it). A firm supplies its own by pointing
`theme["logo_path"]` at a transparent PNG or SVG; the engine **base64-embeds** it as a data
URI, so the file stays self-contained and offline — never a remote URL (that would break the
offline / data-handling guarantee).

> **White-label:** set `theme["logo_path"]` to your own transparent PNG/SVG (and
> `theme["brand_name"]` to your name). Using the toolkit does not grant any right to the
> Phronesis Applied name or marks in your own branding — see `NOTICE`.

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
