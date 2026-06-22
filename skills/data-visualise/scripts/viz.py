"""viz.py — a brandable, self-contained HTML dashboard / visualisation engine.

Turns any tabular data — a list of dicts, or an existing .xlsx — into a
self-contained HTML artefact that opens in a browser and prints cleanly to PDF.
Ships with a clean, neutral default theme (a slate + blue palette) and lets any
firm drop in its own brand (name, colours, logo) without touching the code.

Design principles
-----------------
* **Self-contained & offline.** Pure inline HTML + CSS + **inline SVG** charts.
  NO JavaScript chart libraries, NO CDN, NO remote images. One file, no network.
  This keeps sensitive/confidential data off any cloud (the toolkit's
  data-handling rule) and makes the file print reliably and travel as a single
  attachment.
* **Brandable.** A neutral default theme is built in; pass a `theme` dict (brand
  name, primary/accent colours, optional logo path) to re-skin every artefact.
  See DEFAULT_THEME below.
* **Composable.** Small building blocks (kpi_card, bar_chart, line_chart,
  donut_chart, table, status_pill, section, grid) each return an HTML string;
  `dashboard(...)` assembles them into a full page with a header, an "as-of"
  stamp, a print stylesheet and a footer disclaimer.
* **Drafts, not advice.** Output is an internal artefact for a qualified person
  to review — never auto-distributed.

Quick start
-----------
    from viz import kpi_row, bar_chart, table, dashboard
    blocks = [
        kpi_row([{"label": "Open tasks", "value": 12, "status": "amber"},
                 {"label": "Overdue", "value": 3, "status": "red"}]),
        bar_chart([("Mon", 4), ("Tue", 7), ("Wed", 5)], title="Tasks by day"),
        table(rows, title="Detail"),
    ]
    dashboard("Operations dashboard", blocks, subtitle="Weekly", as_of="14 Jun 2026",
              out_path="dashboard.html")

To apply your own brand, pass a theme (any subset overrides the neutral default):
    my_theme = {"brand_name": "Acme Co",
                "colours": {"burgundy": "#0B3D91", "rose": "#1565C0"},
                "logo_path": "assets/acme-logo.png"}
    dashboard("Operations dashboard", blocks, theme=my_theme, out_path="dashboard.html")

Run `python viz.py` for an offline self-test that builds a demo dashboard.
"""

from __future__ import annotations

import base64 as _b64
import datetime as dt
import html as _html
import os
import sys
import webbrowser
from pathlib import Path

# Windows cp1252 consoles can't print non-ASCII (·, —, ⚠) — guard it.
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


# --------------------------------------------------------------------------- #
# Theme — a neutral, brandable default. The colour-token *names* (burgundy / rose
# / pink …) are kept for stability across the rendering code, but the default hex
# values are a clean slate + blue palette with NO firm branding. A firm re-skins
# every artefact by passing a `theme` dict to dashboard() (or calling apply_theme
# before building blocks). See references/brand.md for the theming guide.
# --------------------------------------------------------------------------- #
DEFAULT_THEME = {
    # A short brand / firm name shown in the header wordmark fallback and footer.
    "brand_name": "Data Toolkit",
    # Optional path to a logo PNG (transparent bg). Ships with a neutral sample
    # the firm swaps for its own; if missing, the header shows a text wordmark.
    "logo_path": str(Path(__file__).resolve().parent.parent / "assets" / "logo-sample.png"),
    # Font stack — a clean geometric/neutral sans. No proprietary brand face.
    "font": "'Inter','Segoe UI','Helvetica Neue',Arial,sans-serif",
    # Palette. Token names are historical; values are a neutral slate + blue.
    "colours": {
        "burgundy": "#1F3A5F",   # primary — header rule, wordmark, table heads, default accent (slate blue)
        "rose":     "#2E6FB0",   # accent 1 — second series (blue)
        "pink":     "#5B9BD5",   # accent 2 — third series (light blue)
        "pink_lt":  "#A9C7E8",   # light tint
        "pink_vlt": "#EAF1F8",   # very light tint (table zebra striping)
        "ink":      "#1A1C1F",   # body text
        "grey":     "#5F6571",   # muted text
        "grey_lt":  "#E3E6EA",   # hairlines / borders
        "bg":       "#F6F8FA",   # page background (cool neutral)
        "white":    "#FFFFFF",
        # status (RAG)
        "green":    "#2E7D57",
        "amber":    "#B26B00",
        "red":      "#9B2226",
    },
}

# Active module-level brand state, initialised from the neutral default. Building
# blocks read these; apply_theme() rebinds them so block colours follow a brand.
BRAND = dict(DEFAULT_THEME["colours"])
FONT = DEFAULT_THEME["font"]
BRAND_NAME = DEFAULT_THEME["brand_name"]
# Path to the header logo (a neutral sample placeholder; the firm replaces it).
LOGO_PATH = Path(DEFAULT_THEME["logo_path"])


def _series_palette() -> list:
    """Sequence used to colour multi-series charts / donut slices, from BRAND."""
    return [BRAND["burgundy"], BRAND["rose"], BRAND["pink"], BRAND["green"],
            BRAND["amber"], BRAND["grey"], BRAND["pink_lt"]]


def _resolve_theme(theme: dict | None) -> dict:
    """Merge a partial `theme` dict over DEFAULT_THEME → a complete theme.
    `theme` may set any of: brand_name, logo_path, font, colours (partial)."""
    t = theme or {}
    colours = dict(DEFAULT_THEME["colours"])
    colours.update(t.get("colours") or {})
    return {
        "brand_name": t.get("brand_name", DEFAULT_THEME["brand_name"]),
        "logo_path": t.get("logo_path", DEFAULT_THEME["logo_path"]),
        "font": t.get("font", DEFAULT_THEME["font"]),
        "colours": colours,
    }


def apply_theme(theme: dict | None) -> dict:
    """Rebind the module-level brand state (BRAND/FONT/BRAND_NAME/LOGO_PATH and the
    chart series palette) from a (partial) `theme` dict, so building blocks built
    afterwards pick up the brand. Returns the fully-resolved theme. Pass None to
    reset to the neutral default. Call this BEFORE composing blocks if you want a
    firm's colours in the charts; dashboard() also accepts `theme=` for the shell."""
    global BRAND, FONT, BRAND_NAME, LOGO_PATH, _SERIES
    rt = _resolve_theme(theme)
    BRAND = rt["colours"]
    FONT = rt["font"]
    BRAND_NAME = rt["brand_name"]
    LOGO_PATH = Path(rt["logo_path"]) if rt["logo_path"] else None
    _SERIES = _series_palette()
    return rt


def _logo_html() -> str:
    """The brand mark for the header: the logo PNG as a base64 data URI if the asset
    is present, else a plain text wordmark of the brand name. The shipped logo is a
    neutral sample placeholder — a firm swaps it for its own (see brand.md)."""
    return _logo_for({"logo_path": str(LOGO_PATH) if LOGO_PATH else "",
                      "brand_name": BRAND_NAME})


def _logo_for(rt: dict) -> str:
    """Logo mark from a resolved theme: the logo PNG as a base64 data URI if present,
    else a plain text wordmark of the brand name."""
    path = rt.get("logo_path")
    name = rt.get("brand_name", "")
    try:
        if path:
            uri = "data:image/png;base64," + _b64.b64encode(Path(path).read_bytes()).decode()
            return f'<img class="logo" src="{uri}" alt="{_e(name)}">'
    except Exception:
        pass
    return f'<span class="mark">{_e(name)}</span>'

# Sequence used to colour multi-series charts / donut slices.
_SERIES = _series_palette()

_STATUS_COLOUR = {
    "green": BRAND["green"], "ok": BRAND["green"], "done": BRAND["green"],
    "amber": BRAND["amber"], "warn": BRAND["amber"], "due": BRAND["amber"],
    "red": BRAND["red"], "bad": BRAND["red"], "overdue": BRAND["red"],
    "brand": BRAND["burgundy"], "info": BRAND["burgundy"],
    "grey": BRAND["grey"], "neutral": BRAND["grey"], None: BRAND["grey"],
}


_UID = [0]


def _next_id() -> str:
    """A render-local unique id (for pairing a filter control to its table)."""
    _UID[0] += 1
    return f"qv{_UID[0]}"


def _e(s) -> str:
    """HTML-escape anything to a safe string."""
    return _html.escape("" if s is None else str(s))


def _status(s) -> str:
    return _STATUS_COLOUR.get(str(s).lower() if s is not None else None, BRAND["grey"])


def _fmt_num(v) -> str:
    """Thousands-separate plain numbers; leave pre-formatted strings alone."""
    if isinstance(v, bool):
        return _e(v)
    if isinstance(v, int):
        return f"{v:,}"
    if isinstance(v, float):
        return f"{v:,.2f}".rstrip("0").rstrip(".") if v % 1 else f"{int(v):,}"
    return _e(v)


# --------------------------------------------------------------------------- #
# Building blocks — each returns a self-contained HTML fragment.
# --------------------------------------------------------------------------- #
def kpi_card(label, value, sub=None, status="brand") -> str:
    """A single metric card: big value, label, optional sub-line, status accent."""
    col = _status(status)
    sub_h = f'<div class="kpi-sub">{_e(sub)}</div>' if sub else ""
    return (f'<div class="kpi" style="border-top-color:{col}">'
            f'<div class="kpi-val" style="color:{col}">{_fmt_num(value)}</div>'
            f'<div class="kpi-lbl">{_e(label)}</div>{sub_h}</div>')


def kpi_row(cards: list[dict]) -> str:
    """A responsive row of KPI cards. Each card: {label, value, sub?, status?}."""
    inner = "".join(kpi_card(c.get("label"), c.get("value"), c.get("sub"),
                             c.get("status", "brand")) for c in cards)
    return f'<div class="kpi-row">{inner}</div>'


def status_pill(text, status="grey") -> str:
    """A small coloured RAG pill."""
    col = _status(status)
    return (f'<span class="pill" style="background:{col}1a;color:{col};'
            f'border:1px solid {col}55">{_e(text)}</span>')


def _norm_pairs(data) -> list[tuple]:
    """Accept [(label, value)] or [{'label':..,'value':..}] -> [(label, value)]."""
    out = []
    for d in data:
        if isinstance(d, dict):
            out.append((d.get("label"), d.get("value", 0)))
        else:
            out.append((d[0], d[1]))
    return out


def _nice_ticks(lo, hi, n=5):
    """A small set of 'nice' axis ticks spanning [lo, hi]. Floats the axis to the
    data range (not forced to 0), so a high-clustered trend line isn't squashed
    against the top. Returns (ticks, axis_lo, axis_hi)."""
    import math
    if hi <= lo:
        hi = lo + 1
    raw = (hi - lo) / n
    mag = 10 ** math.floor(math.log10(raw)) if raw > 0 else 1
    step = next(m * mag for m in (1, 2, 2.5, 5, 10) if raw <= m * mag)
    nlo = math.floor(lo / step) * step
    nhi = math.ceil(hi / step) * step
    ticks, v = [], nlo
    while v <= nhi + step * 1e-6:
        ticks.append(round(v, 6))
        v += step
    return ticks, nlo, nhi


def bar_chart(data, title=None, height=220, unit="") -> str:
    """A horizontal-axis bar chart as inline SVG. data: [(label, value)] or dicts."""
    pairs = _norm_pairs(data)
    if not pairs:
        return _empty_block(title, "No data")
    vals = [float(v or 0) for _, v in pairs]
    vmax = max(vals + [0]) or 1
    n = len(pairs)
    W, pad_l, pad_b, pad_t = 640, 8, 28, 20  # pad_t leaves room for value labels
    plot_h = height - pad_b - pad_t
    gap = 10
    bw = (W - pad_l) / n - gap
    bars = []
    for i, ((lab, _), v) in enumerate(zip(pairs, vals)):
        h = (v / vmax) * plot_h
        x = pad_l + i * (bw + gap)
        y = pad_t + (plot_h - h)
        col = _SERIES[i % len(_SERIES)] if n <= len(_SERIES) else BRAND["burgundy"]
        bars.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{bw:.1f}" height="{h:.1f}" '
            f'rx="3" fill="{col}"><title>{_e(lab)}: {_fmt_num(_strip(v))}{_e(unit)}</title></rect>'
            f'<text x="{x + bw/2:.1f}" y="{y - 4:.1f}" text-anchor="middle" '
            f'class="v">{_fmt_num(_strip(v))}</text>'
            f'<text x="{x + bw/2:.1f}" y="{height - 9:.1f}" text-anchor="middle" '
            f'class="x">{_e(lab)}</text>')
    svg = (f'<svg viewBox="0 0 {W} {height}" class="chart" '
           f'preserveAspectRatio="xMidYMid meet">{"".join(bars)}</svg>')
    return _chart_block(title, svg)


def line_chart(series, title=None, height=240, unit="", toggle=False) -> str:
    """A line chart. `series` is either [(label, value)] for one line, or
    {name: [(label, value)], ...} for several. X labels come from the first series.
    `toggle=True` makes the legend clickable to show/hide each series (inline JS)."""
    if isinstance(series, dict):
        named = list(series.items())
    else:
        named = [("", _norm_pairs(series))]
    named = [(nm, _norm_pairs(s) if not (s and isinstance(s[0], tuple)) else s)
             for nm, s in named]
    first = named[0][1] if named else []
    if not first:
        return _empty_block(title, "No data")
    labels = [l for l, _ in first]
    allv = [float(v or 0) for _, s in named for _, v in s]
    ticks, vmin, vmax = _nice_ticks(min(allv or [0]), max(allv or [0]))
    W, pad_l, pad_b, pad_t, pad_r = 640, 34, 26, 16, 10
    plot_h = height - pad_b - pad_t
    plot_w = W - pad_l - pad_r
    n = len(labels)
    xstep = plot_w / max(n - 1, 1)

    def _y(v):
        rng = (vmax - vmin) or 1
        return pad_t + plot_h - ((float(v or 0) - vmin) / rng) * plot_h

    # horizontal gridlines + y-axis value labels (so the floated scale is legible)
    gridlines = "".join(
        f'<line x1="{pad_l}" y1="{_y(t):.1f}" x2="{W - pad_r}" y2="{_y(t):.1f}" '
        f'stroke="{BRAND["grey_lt"]}" stroke-width="1"/>'
        f'<text x="{pad_l - 5}" y="{_y(t) + 3:.1f}" text-anchor="end" class="x">'
        f'{_fmt_num(_strip(t))}{_e(unit)}</text>' for t in ticks)

    groups, legend = [], []
    for si, (nm, s) in enumerate(named):
        col = _SERIES[si % len(_SERIES)]
        pts = [(pad_l + i * xstep, _y(v)) for i, (_, v) in enumerate(s)]
        d = "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in pts)
        path = f'<path d="{d}" fill="none" stroke="{col}" stroke-width="2.5"/>'
        dots = "".join(
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3" fill="{col}">'
            f'<title>{_e(nm)} {_fmt_num(_strip(v))}{_e(unit)}</title></circle>'
            for (x, y), (_, v) in zip(pts, s))
        groups.append(f'<g data-series="{si}">{path}{dots}</g>')
        if nm:
            legend.append(f'<span class="lg"><i style="background:{col}"></i>{_e(nm)}</span>')
    xlabs = "".join(
        f'<text x="{pad_l + i * xstep:.1f}" y="{height - 8:.1f}" text-anchor="middle" '
        f'class="x">{_e(l)}</text>' for i, l in enumerate(labels))
    svg = (f'<svg viewBox="0 0 {W} {height}" class="chart" '
           f'preserveAspectRatio="xMidYMid meet">{gridlines}{"".join(groups)}{xlabs}</svg>')
    tg = ' data-toggle="1"' if (toggle and legend) else ''
    leg = f'<div class="legend"{tg}>{"".join(legend)}</div>' if legend else ""
    return _chart_block(title, svg + leg)


def donut_chart(data, title=None, height=240, centre=None) -> str:
    """A donut chart. data: [(label, value)] or dicts. `centre` overrides the
    centre label (defaults to the total)."""
    pairs = _norm_pairs(data)
    vals = [max(float(v or 0), 0) for _, v in pairs]
    total = sum(vals)
    if total <= 0:
        return _empty_block(title, "No data")
    cx, cy, r, rin = 120, 120, 100, 62
    import math
    a0 = -math.pi / 2
    arcs, legend = [], []
    for i, ((lab, _), v) in enumerate(zip(pairs, vals)):
        frac = v / total
        a1 = a0 + frac * 2 * math.pi
        large = 1 if frac > 0.5 else 0
        x0, y0 = cx + r * math.cos(a0), cy + r * math.sin(a0)
        x1, y1 = cx + r * math.cos(a1), cy + r * math.sin(a1)
        col = _SERIES[i % len(_SERIES)]
        arcs.append(f'<path d="M{x0:.1f},{y0:.1f} A{r},{r} 0 {large} 1 {x1:.1f},{y1:.1f} '
                    f'L{cx},{cy} Z" fill="{col}"><title>{_e(lab)}: {_fmt_num(_strip(v))} '
                    f'({frac*100:.0f}%)</title></path>')
        legend.append(f'<span class="lg"><i style="background:{col}"></i>'
                      f'{_e(lab)} <b>{_fmt_num(_strip(v))}</b></span>')
        a0 = a1
    hole = f'<circle cx="{cx}" cy="{cy}" r="{rin}" fill="{BRAND["white"]}"/>'
    centre_t = _e(centre) if centre is not None else _fmt_num(_strip(total))
    ctext = (f'<text x="{cx}" y="{cy-2}" text-anchor="middle" class="dn-c">{centre_t}</text>'
             f'<text x="{cx}" y="{cy+16}" text-anchor="middle" class="dn-l">total</text>')
    svg = (f'<svg viewBox="0 0 240 {max(height,240)}" class="chart donut" '
           f'preserveAspectRatio="xMidYMid meet">{"".join(arcs)}{hole}{ctext}</svg>')
    return _chart_block(title, f'<div class="donut-wrap">{svg}'
                               f'<div class="legend col">{"".join(legend)}</div></div>')


def table(rows: list[dict], columns: list[str] | None = None, title=None,
          rag: dict | None = None, sortable=False, filter_by=None) -> str:
    """An on-brand data table. `rows` = list of dicts. `columns` selects/orders
    columns (default: keys of the first row). `rag` maps a column name to a
    function value->status ('green'/'amber'/'red'/...) for a coloured cell.
    `sortable=True` makes column headers click-to-sort; `filter_by=<column>`
    adds a dropdown that filters rows by that column's value. Both are inline JS
    and degrade cleanly for print (sorted order prints; filtered-out rows don't)."""
    if not rows:
        return _empty_block(title, "No rows")
    cols = columns or list(rows[0].keys())
    rag = rag or {}
    head = "".join(f"<th>{_e(c)}</th>" for c in cols)
    body = []
    for r in rows:
        tds = []
        for c in cols:
            val = r.get(c)
            if c in rag:
                try:
                    st = rag[c](val)
                except Exception:
                    st = None
                if st:
                    col = _status(st)
                    tds.append(f'<td style="background:{col}14;'
                               f'border-left:3px solid {col}">{_fmt_num(val)}</td>')
                    continue
            tds.append(f"<td>{_fmt_num(val)}</td>")
        body.append(f"<tr>{''.join(tds)}</tr>")
    tid = _next_id() if filter_by in cols else ""
    sort_attr = ' data-sortable="1"' if sortable else ''
    id_attr = f' id="{tid}"' if tid else ''
    tbl = (f'<table{id_attr} class="grid"{sort_attr}><thead><tr>{head}</tr></thead>'
           f'<tbody>{"".join(body)}</tbody></table>')
    if tid:                                    # filter dropdown bound to this table
        ci = cols.index(filter_by)
        opts = "".join(f'<option value="{_e(o)}">{_e(o)}</option>'
                       for o in sorted({str(r.get(filter_by, "")) for r in rows}))
        bar = (f'<div class="filterbar">{_e(filter_by)}: '
               f'<select data-filter="1" data-col="{ci}" data-target="{tid}">'
               f'<option value="__all">All</option>{opts}</select></div>')
        tbl = bar + tbl
    return _chart_block(title, tbl)


def section(title, *blocks) -> str:
    """A titled section wrapping one or more blocks."""
    return (f'<section class="sec"><h2>{_e(title)}</h2>'
            f'{"".join(blocks)}</section>')


def grid(*blocks, cols=2) -> str:
    """Lay blocks out in an N-column responsive grid."""
    return (f'<div class="lay" style="grid-template-columns:repeat({cols},1fr)">'
            f'{"".join(blocks)}</div>')


# --------------------------------------------------------------------------- #
# Internal layout helpers
# --------------------------------------------------------------------------- #
def _strip(v):
    """Drop a trailing .0 from whole floats so labels read cleanly."""
    return int(v) if isinstance(v, float) and v.is_integer() else v


def _chart_block(title, inner) -> str:
    t = f'<h3 class="bt">{_e(title)}</h3>' if title else ""
    return f'<div class="block">{t}{inner}</div>'


def _empty_block(title, msg) -> str:
    return _chart_block(title, f'<div class="empty">{_e(msg)}</div>')


# --------------------------------------------------------------------------- #
# Page assembly
# --------------------------------------------------------------------------- #
def dashboard(title, blocks, subtitle=None, as_of=None, out_path=None,
              footnote=None, theme=None) -> str:
    """Assemble blocks into a full, self-contained HTML page.

    title     — page heading.
    blocks    — list of HTML fragments from the building blocks above.
    subtitle  — optional sub-heading under the title.
    as_of     — "as-of" stamp shown top-right (e.g. '14 Jun 2026'); defaults to today.
    out_path  — if given, write the file and return its path; else return the HTML.
    footnote  — optional extra line in the footer (above the standard disclaimer).
    theme     — optional (partial) theme dict {brand_name, logo_path, font, colours}
                overriding the neutral default for the page shell (header rule,
                wordmark/logo, fonts, footer brand line). To also re-skin the chart
                colours, call apply_theme(theme) before building the blocks.
    """
    rt = _resolve_theme(theme)
    brand, font = rt["colours"], rt["font"]
    logo_html = _logo_html() if theme is None else _logo_for(rt)
    as_of = as_of or _today_str()
    sub_h = f'<div class="sub">{_e(subtitle)}</div>' if subtitle else ""
    body = "".join(blocks) if isinstance(blocks, (list, tuple)) else str(blocks)
    foot_extra = f'<div>{_e(footnote)}</div>' if footnote else ""
    # the interaction script is inert unless a block opted in (sortable/filter/toggle)
    script = _INTERACT_JS if any(k in body for k in
             ('data-sortable', 'data-filter', 'data-toggle')) else ""
    doc = _PAGE.format(
        title=_e(title), subtitle=sub_h, asof=_e(as_of), body=body,
        foot_extra=foot_extra, brand=brand, font=font, logo=logo_html,
        brand_name=_e(rt["brand_name"]), script=script,
        year=as_of.split()[-1] if as_of and as_of[-1].isdigit() else "")
    if out_path:
        Path(out_path).write_text(doc, encoding="utf-8")
        return str(out_path)
    return doc


def open_in_browser(path) -> None:
    """Open a rendered dashboard in the default browser (for review / print-to-PDF)."""
    webbrowser.open(Path(path).resolve().as_uri())


def _today_str() -> str:
    d = dt.date.today()
    return d.strftime("%d %b %Y")


# The page shell. Note: CSS braces are doubled for str.format; {brand[..]} /
# {font} / {title} etc. are the only single-brace fields.
_PAGE = """<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title><style>
:root{{--burg:{brand[burgundy]};--rose:{brand[rose]};--ink:{brand[ink]};
--grey:{brand[grey]};--line:{brand[grey_lt]};--bg:{brand[bg]}}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--bg);color:var(--ink);font:14px/1.45 {font}}}
.wrap{{max-width:1040px;margin:0 auto;padding:0 20px 40px}}
header{{display:flex;align-items:flex-end;justify-content:space-between;
gap:16px;border-bottom:3px solid var(--burg);padding:22px 0 12px;margin-bottom:18px}}
.brand{{display:flex;align-items:center;gap:13px}}
.brand .logo{{height:46px;width:auto;display:block}}
.mark{{font-weight:700;letter-spacing:2px;color:var(--ink);font-size:24px}}
h1{{font-size:21px;margin:0;font-weight:700}}
.sub{{color:var(--grey);font-size:13px;margin-top:2px}}
.asof{{text-align:right;color:var(--grey);font-size:12px;white-space:nowrap}}
.asof b{{display:block;color:var(--ink);font-size:13px}}
.btn{{margin-top:8px;font:12px {font};background:var(--burg);color:#fff;border:0;
border-radius:5px;padding:6px 12px;cursor:pointer}}
.sec{{margin:22px 0}}
.sec h2{{font-size:15px;color:var(--burg);margin:0 0 10px;
border-left:4px solid var(--burg);padding-left:9px}}
.block{{background:#fff;border:1px solid var(--line);border-radius:9px;
padding:14px 16px;margin:0 0 14px}}
.bt{{font-size:13px;margin:0 0 10px;color:var(--ink)}}
.kpi-row{{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));
gap:14px;margin:0 0 14px}}
.kpi{{background:#fff;border:1px solid var(--line);border-top:4px solid var(--burg);
border-radius:9px;padding:14px 16px}}
.kpi-val{{font-size:30px;font-weight:700;line-height:1.1}}
.kpi-lbl{{color:var(--grey);font-size:12px;margin-top:4px;text-transform:uppercase;
letter-spacing:.4px}}
.kpi-sub{{color:var(--ink);font-size:12px;margin-top:6px}}
.lay{{display:grid;gap:14px}}
.lay .block{{margin:0}}
.chart{{width:100%;height:auto;display:block}}
.chart .v{{font:11px {font};fill:var(--ink)}}
.chart .x{{font:11px {font};fill:var(--grey)}}
.donut-wrap{{display:flex;gap:18px;align-items:center;flex-wrap:wrap}}
.donut{{max-width:240px}}
.dn-c{{font:700 26px {font};fill:var(--burg)}}
.dn-l{{font:11px {font};fill:var(--grey)}}
.legend{{display:flex;flex-wrap:wrap;gap:10px 16px;margin-top:8px;font-size:12px}}
.legend.col{{flex-direction:column;gap:6px}}
.lg{{display:inline-flex;align-items:center;gap:6px;color:var(--ink)}}
.lg i{{width:11px;height:11px;border-radius:2px;display:inline-block}}
.pill{{display:inline-block;padding:2px 9px;border-radius:11px;font-size:11px;
font-weight:600}}
table.grid{{border-collapse:collapse;width:100%;font-size:13px}}
table.grid th{{background:var(--burg);color:#fff;text-align:left;padding:7px 9px;
font-weight:600;font-size:12px}}
table.grid td{{border-bottom:1px solid var(--line);padding:6px 9px}}
table.grid tbody tr:nth-child(even){{background:{brand[pink_vlt]}55}}
table.grid[data-sortable] th{{cursor:pointer;user-select:none}}
.so{{font-size:9px;opacity:.85}}
.legend[data-toggle] .lg{{cursor:pointer}}
.legend[data-toggle] .lg.off{{opacity:.35}}
.filterbar{{font-size:12px;color:var(--grey);margin:0 0 10px}}
.filterbar select{{font:12px {font};padding:3px 7px;border:1px solid var(--line);
border-radius:5px;color:var(--ink);background:#fff}}
.empty{{color:var(--grey);text-align:center;padding:18px;font-style:italic}}
footer{{margin-top:26px;border-top:1px solid var(--line);padding-top:10px;
color:var(--grey);font-size:11px}}
@media print{{
 body{{background:#fff}}
 .btn{{display:none}}
 .wrap{{max-width:none;padding:0}}
 .block,.kpi,.sec{{break-inside:avoid}}
 header{{padding-top:0}}
}}
</style></head><body><div class="wrap">
<header>
 <div>
  <div class="brand">{logo}<h1>{title}</h1></div>
  {subtitle}
 </div>
 <div class="asof">as of<b>{asof}</b>
  <button class="btn" onclick="window.print()">Print / Save&nbsp;PDF</button></div>
</header>
{body}
<footer>{foot_extra}
 {brand_name} — internal. Generated {asof}. A draft for review by a
 qualified person, not advice.</footer>
</div>{script}</body></html>"""


# Optional inline interactivity (vanilla JS, no library/CDN). Injected by
# dashboard() only when a block opted in. Powers: click-to-sort tables,
# click-legend to toggle line series, and a dropdown row-filter. Kept tiny.
_INTERACT_JS = """<script>
(function(){
 document.querySelectorAll('table.grid[data-sortable]').forEach(function(t){
  var ths=t.tHead.rows[0].cells;
  [].forEach.call(ths,function(th,ci){
   th.addEventListener('click',function(){
    var tb=t.tBodies[0],rows=[].slice.call(tb.rows),asc=th.getAttribute('data-asc')!=='1';
    [].forEach.call(ths,function(o){o.removeAttribute('data-asc');var s=o.querySelector('.so');if(s)s.remove();});
    th.setAttribute('data-asc',asc?'1':'0');
    var num=rows.every(function(r){var x=(r.cells[ci].textContent||'').replace(/[^0-9.\\-]/g,'');return x!==''&&!isNaN(x);});
    rows.sort(function(a,b){var x=a.cells[ci].textContent.trim(),y=b.cells[ci].textContent.trim();
     if(num){x=parseFloat(x.replace(/[^0-9.\\-]/g,''))||0;y=parseFloat(y.replace(/[^0-9.\\-]/g,''))||0;}
     return (x>y?1:x<y?-1:0)*(asc?1:-1);});
    rows.forEach(function(r){tb.appendChild(r);});
    var a=document.createElement('span');a.className='so';a.textContent=asc?' \\u25B2':' \\u25BC';th.appendChild(a);
   });
  });
 });
 document.querySelectorAll('.legend[data-toggle]').forEach(function(lg){
  var svg=lg.parentNode.querySelector('svg');
  [].forEach.call(lg.querySelectorAll('.lg'),function(item,i){
   item.addEventListener('click',function(){
    var g=svg.querySelector('[data-series="'+i+'"]');if(!g)return;
    var off=g.getAttribute('data-off')!=='1';
    g.setAttribute('data-off',off?'1':'0');g.style.display=off?'none':'';
    item.classList.toggle('off',off);
   });
  });
 });
 document.querySelectorAll('select[data-filter]').forEach(function(sel){
  var ci=+sel.getAttribute('data-col'),t=document.getElementById(sel.getAttribute('data-target'));
  sel.addEventListener('change',function(){var v=sel.value;
   [].forEach.call(t.tBodies[0].rows,function(r){
    r.style.display=(v==='__all'||r.cells[ci].textContent.trim()===v)?'':'none';});
  });
 });
})();
</script>"""


# --------------------------------------------------------------------------- #
# Optional adapters — feed the engine from existing toolkit .xlsx stores.
# Kept light and dependency-optional so the engine stands alone.
# --------------------------------------------------------------------------- #
def _load_ingest():
    """Import the shared ingest engine (toolkit-root scripts/, or a vendored sibling) if it's
    reachable — for its multi-sheet-safe .xlsx reader. Returns the module or None."""
    import importlib
    from pathlib import Path as _P
    for p in (_P(__file__).resolve().parents[3] / "scripts",   # toolkit-root engine
              _P(__file__).resolve().parent / "scripts"):       # vendored sibling
        if (p / "ingest.py").is_file():
            if str(p) not in sys.path:
                sys.path.insert(0, str(p))
            try:
                return importlib.import_module("ingest")
            except ImportError:
                return None
    return None


def _rows_to_dicts(rows) -> list[dict]:
    if not rows:
        return []
    header = [str(h) if h is not None else "" for h in rows[0]]
    out = []
    for row in rows[1:]:
        if all(c is None or str(c).strip() == "" for c in row):
            continue
        out.append({header[i]: row[i] for i in range(min(len(header), len(row)))})
    return out


def rows_from_xlsx(path, sheet=None) -> list[dict]:
    """Read a simple header+rows .xlsx into a list of dicts (needs openpyxl).
    Use to point the engine at any header+rows .xlsx (e.g. a clean table from
    data-tidy / data-extract).

    Multi-tab safe: it won't silently read the 'active' sheet. When the shared `ingest` engine
    is reachable it uses `ingest.read_xlsx` (auto-selects the single data sheet; raises
    `SheetSelectionRequired` if several tabs hold data). Standalone (ingest absent), the same
    rule is applied locally. Pass `sheet=<name>` to read a specific tab."""
    ing = _load_ingest()
    if ing is not None:
        rows, _ = ing.read_xlsx(path, sheet=sheet)
        return _rows_to_dicts(rows)

    # Standalone fallback — mirror ingest's single-sheet safety without importing it.
    import openpyxl  # optional dependency
    wb = openpyxl.load_workbook(path, data_only=True, read_only=True)
    try:
        def _has_data(ws):
            for r in ws.iter_rows(values_only=True):
                if any(c is not None and str(c).strip() != "" for c in r):
                    return True
            return False
        if sheet is not None:
            ws = wb[sheet]
        else:
            cands = [ws for ws in wb.worksheets
                     if ws.sheet_state == "visible" and _has_data(ws)]
            if len(cands) == 1:
                ws = cands[0]
            elif not cands:
                ws = wb.active
            else:
                names = ", ".join(repr(ws.title) for ws in cands)
                raise ValueError(
                    f"{Path(path).name} has {len(cands)} non-empty sheets ({names}); "
                    f"pass sheet=<name> to choose one.")
        rows = [["" if c is None else c for c in r] for r in ws.iter_rows(values_only=True)]
    finally:
        wb.close()
    return _rows_to_dicts(rows)


# --------------------------------------------------------------------------- #
# Self-test — builds a demo dashboard (no external data, no network).
# --------------------------------------------------------------------------- #
if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "dashboard-selftest.html"
    tasks = [
        {"ID": 1, "Task": "Circulate weekly tracker", "Owner": "Alex", "Days late": 12},
        {"ID": 2, "Task": "Confirm vendor quotes", "Owner": "Jordan", "Days late": 0},
        {"ID": 3, "Task": "Draft planning outline", "Owner": "Sam", "Days late": 0},
    ]
    blocks = [
        kpi_row([
            {"label": "Open tasks", "value": 12, "status": "brand"},
            {"label": "Overdue", "value": 3, "sub": "oldest 12 days", "status": "red"},
            {"label": "Due this week", "value": 5, "status": "amber"},
            {"label": "Done (7d)", "value": 9, "status": "green"},
        ]),
        section("Throughput",
            grid(
                bar_chart([("Mon", 4), ("Tue", 7), ("Wed", 5), ("Thu", 6), ("Fri", 3)],
                          title="Tasks completed by day"),
                donut_chart([("Compliance", 8), ("Finance", 5), ("Marketing", 3),
                             ("Legal", 4)], title="Open tasks by function"),
            )),
        section("Trend",
            line_chart({"Opened": [("W1", 10), ("W2", 14), ("W3", 9), ("W4", 12)],
                        "Closed": [("W1", 8), ("W2", 11), ("W3", 13), ("W4", 10)]},
                       title="Opened vs closed (4 weeks)")),
        section("Detail",
            table(tasks, columns=["ID", "Task", "Owner", "Days late"],
                  title="Outstanding tasks",
                  rag={"Days late": lambda v: "red" if (v or 0) > 7 else
                       ("amber" if (v or 0) > 0 else "green")})),
    ]
    path = dashboard("Operations dashboard", blocks, subtitle="Demo / self-test",
                     as_of="14 Jun 2026", out_path=out)
    print(f"[self-test] built {path} ({Path(path).stat().st_size:,} bytes)")
    print("[self-test] pills:", status_pill("On track", "green"),
          status_pill("At risk", "amber"), status_pill("Breach", "red"))
