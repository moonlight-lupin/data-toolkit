"""Data Analyse — deterministic descriptive-metrics engine.

Computes the numbers the data-analyse skill quotes: numeric summaries, category
breakdowns with concentration, period series with deltas/YoY, ageing buckets and
IQR outliers. Pure stdlib + Decimal; reuses the shared toolkit parsers
(``scripts/dataclean.py``) so amounts, currencies and dates behave exactly like
the rest of the toolkit (exact Decimal, no float drift, dayfirst dates).

The division of labour: **this module computes, the assistant interprets.**
Every figure the insight brief quotes should come from here (or be an obvious
derivation shown in the brief) — never a number produced free-form.

    python analyse.py --self-test
"""

import pathlib
import sys
from collections import OrderedDict
from decimal import Decimal

_ROOT = pathlib.Path(__file__).resolve().parents[3]          # plugin root
sys.path.insert(0, str(_ROOT / "scripts"))
import dataclean                                             # noqa: E402  shared parsers/profiler
from dataclean import parse_currency, parse_date, parse_number  # noqa: E402


# --------------------------------------------------------------------------- #
# Column access + parsing
# --------------------------------------------------------------------------- #
def _s(v) -> str:
    return "" if v is None else str(v).strip()


def col_index(header, name):
    """Resolve a column by name, case-insensitively. Raises with the real names
    on a miss so the caller never silently analyses the wrong column."""
    wanted = _s(name).lower()
    for j, h in enumerate(header):
        if _s(h).lower() == wanted:
            return j
    raise KeyError(f"column {name!r} not found; columns are: {[_s(h) for h in header]}")


def column(header, rows, name):
    j = col_index(header, name)
    return [r[j] if j < len(r) else "" for r in rows]


def numbers(values):
    """Parse a raw column to Decimals. Returns (decimals, skipped) where skipped
    counts non-empty cells that would not parse — report it, never hide it."""
    out, skipped = [], 0
    for v in values:
        if _s(v) == "":
            continue
        n, _ = parse_number(v)
        if n is None:
            skipped += 1
        else:
            out.append(n)
    return out, skipped


def currency_mix(values):
    """Distinct currency codes detected in a column (None = code unknown).
    More than one real code means the column must NOT be summed as-is —
    100 USD != 100 SGD (same rule as data-reconcile)."""
    codes = set()
    for v in values:
        if _s(v) == "":
            continue
        parsed, _ = parse_currency(v)
        if parsed is not None:
            codes.add(parsed[1])
    return codes


# --------------------------------------------------------------------------- #
# Numeric summary + outliers
# --------------------------------------------------------------------------- #
def _median(sorted_vals):
    n = len(sorted_vals)
    mid = n // 2
    if n % 2:
        return sorted_vals[mid]
    return (sorted_vals[mid - 1] + sorted_vals[mid]) / 2


def numeric_summary(values):
    """values: raw column. Deterministic descriptive stats on the parseable cells.
    Quartiles use the median-of-halves convention (exact on Decimals)."""
    nonempty = sum(1 for v in values if _s(v) != "")
    dec, skipped = numbers(values)
    if not dec:
        return {"n": 0, "missing": len(values) - nonempty, "skipped": skipped}
    sv = sorted(dec)
    n = len(sv)
    lower = sv[: n // 2]
    upper = sv[(n + 1) // 2:]
    total = sum(sv)
    return {
        "n": n,
        "missing": len(values) - nonempty,
        "skipped": skipped,                       # non-empty but unparseable
        "total": total,
        "mean": total / n,
        "min": sv[0], "p25": _median(lower) if lower else sv[0],
        "median": _median(sv),
        "p75": _median(upper) if upper else sv[-1], "max": sv[-1],
        "negatives": sum(1 for v in sv if v < 0),
    }


def outliers_iqr(values, k=Decimal("1.5"), cap=10):
    """Tukey fences on the parseable cells. Returns fences plus the outlying
    values (each capped at `cap` for display; counts are exact)."""
    dec, _ = numbers(values)
    if len(dec) < 4:
        return {"n": len(dec), "low": [], "high": [], "low_count": 0, "high_count": 0}
    s = numeric_summary(values)
    iqr = s["p75"] - s["p25"]
    lo_f, hi_f = s["p25"] - k * iqr, s["p75"] + k * iqr
    low = sorted(v for v in dec if v < lo_f)
    high = sorted((v for v in dec if v > hi_f), reverse=True)
    return {"n": len(dec), "lower_fence": lo_f, "upper_fence": hi_f,
            "low": low[:cap], "high": high[:cap],
            "low_count": len(low), "high_count": len(high)}


# --------------------------------------------------------------------------- #
# Category breakdown + concentration
# --------------------------------------------------------------------------- #
def breakdown(header, rows, by, value=None, top=10):
    """Group by `by`; measure = row count, or the sum of `value` where given.
    Returns the groups sorted largest-first with shares, plus concentration
    signals (top-1 / top-3 share, and how many groups cover 80%)."""
    keys = column(header, rows, by)
    vals = column(header, rows, value) if value else None
    groups = OrderedDict()
    skipped = 0
    for i, k in enumerate(keys):
        key = _s(k) or "(blank)"
        g = groups.setdefault(key, {"count": 0, "total": Decimal(0)})
        g["count"] += 1
        if vals is not None:
            n, _ = parse_number(vals[i])
            if n is None and _s(vals[i]) != "":
                skipped += 1
            elif n is not None:
                g["total"] += n
    measure = "total" if value else "count"
    items = sorted(groups.items(), key=lambda kv: kv[1][measure], reverse=True)
    grand = sum((g[measure] for _, g in items), Decimal(0))
    has_neg = any(g[measure] < 0 for _, g in items)
    shares_valid = grand > 0 and not has_neg
    out, cum, cum80 = [], Decimal(0), None
    for rank, (key, g) in enumerate(items, 1):
        if shares_valid:
            share = Decimal(g[measure]) / Decimal(grand)
            cum += share
            if cum80 is None and cum >= Decimal("0.8"):
                cum80 = rank
            cum_share = cum
        else:
            share = None
            cum_share = None
        out.append({"key": key, "count": g["count"],
                    **({"total": g["total"]} if value else {}),
                    "share": share, "cum_share": cum_share})
    top1_share = out[0]["share"] if out else None
    if not out or not shares_valid:
        top3_share = None
    else:
        top3_share = sum(g["share"] for g in out[:3] if g["share"] is not None) or None
    return {"by": by, "measure": value or "rows", "groups": out[:top],
            "n_groups": len(out), "grand_total": grand if value else sum(g["count"] for _, g in items),
            "top1_share": top1_share,
            "top3_share": top3_share,
            "groups_to_80pct": cum80, "skipped": skipped,
            "has_negatives": has_neg}   # shares are unreliable when negatives net off


# --------------------------------------------------------------------------- #
# Period series (trend)
# --------------------------------------------------------------------------- #
def _period_key(d, grain):
    if grain == "year":
        return str(d.year)
    if grain == "quarter":
        return f"{d.year}-Q{(d.month - 1) // 3 + 1}"
    return f"{d.year}-{d.month:02d}"                         # month (default)


def _next_period(key, grain):
    if grain == "year":
        return str(int(key) + 1)
    if grain == "quarter":
        y, q = key.split("-Q")
        y, q = int(y), int(q) + 1
        return f"{y + (q > 4)}-Q{1 if q > 4 else q}"
    y, m = (int(x) for x in key.split("-"))
    m += 1
    return f"{y + (m > 12)}-{1 if m > 12 else m:02d}"


def _prior_year(key, grain):
    if grain == "year":
        return str(int(key) - 1)
    if grain == "quarter":
        y, q = key.split("-Q")
        return f"{int(y) - 1}-Q{q}"
    y, m = key.split("-")
    return f"{int(y) - 1}-{m}"


def period_series(header, rows, date_col, value=None, grain="month", dayfirst=True):
    """Aggregate by calendar period. Gap periods are filled with zeros so a
    quiet month reads as zero, not skipped (an honest trend line). Returns the
    ordered periods with deltas and YoY where the prior year exists."""
    assert grain in ("month", "quarter", "year")
    dates = column(header, rows, date_col)
    vals = column(header, rows, value) if value else None
    agg, bad_dates, skipped_vals = {}, 0, 0
    for i, raw in enumerate(dates):
        if _s(raw) == "":
            bad_dates += 1
            continue
        d, _ = parse_date(raw, dayfirst=dayfirst)
        if d is None:
            bad_dates += 1
            continue
        g = agg.setdefault(_period_key(d, grain), {"count": 0, "total": Decimal(0)})
        g["count"] += 1
        if vals is not None:
            n, _ = parse_number(vals[i])
            if n is None and _s(vals[i]) != "":
                skipped_vals += 1
            elif n is not None:
                g["total"] += n
    if not agg:
        return {"periods": [], "bad_dates": bad_dates, "skipped": skipped_vals}
    keys = sorted(agg)
    filled, k = [], keys[0]
    while True:                                              # fill calendar gaps
        filled.append(k)
        if k == keys[-1]:
            break
        k = _next_period(k, grain)
    measure = "total" if value else "count"
    periods, prev, gaps = [], None, 0
    for k in filled:
        g = agg.get(k)
        if g is None:
            gaps += 1
            g = {"count": 0, "total": Decimal(0)}
        m = g[measure]
        delta = None if prev is None else m - prev
        pct = None if prev in (None, 0) else (m - prev) / prev
        yoy_base = agg.get(_prior_year(k, grain))
        yoy = None
        if yoy_base is not None and yoy_base[measure] != 0:
            yoy = (m - yoy_base[measure]) / yoy_base[measure]
        periods.append({"period": k, "count": g["count"],
                        **({"total": g["total"]} if value else {}),
                        "delta": delta, "pct_change": pct, "yoy": yoy})
        prev = m
    vals_by_p = [(p["period"], p[measure if value else "count"]) for p in periods]
    best = max(vals_by_p, key=lambda t: t[1])
    worst = min(vals_by_p, key=lambda t: t[1])
    return {"grain": grain, "measure": value or "rows", "periods": periods,
            "first": vals_by_p[0], "last": vals_by_p[-1],
            "best": best, "worst": worst, "gap_periods": gaps,
            "bad_dates": bad_dates, "skipped": skipped_vals}


# --------------------------------------------------------------------------- #
# Ageing
# --------------------------------------------------------------------------- #
def ageing(header, rows, date_col, as_of, buckets=(30, 60, 90), value=None, dayfirst=True):
    """Bucket rows by days elapsed from `date_col` to `as_of` (a date or a
    parseable string — the caller must pass it explicitly and quote it in the
    brief). Future-dated and unparseable rows get their own buckets, never
    silently dropped."""
    if not hasattr(as_of, "year"):
        as_of, _ = parse_date(as_of, dayfirst=dayfirst)
        if as_of is None:
            raise ValueError("as_of did not parse as a date")
    labels = []
    lo = 0
    for b in buckets:
        labels.append(f"{lo}–{b}")
        lo = b + 1
    labels.append(f"{buckets[-1]}+")
    order = ["future"] + labels + ["unparsed"]
    out = OrderedDict((lab, {"count": 0, "total": Decimal(0)}) for lab in order)
    dates = column(header, rows, date_col)
    vals = column(header, rows, value) if value else None
    for i, raw in enumerate(dates):
        d, _ = parse_date(raw, dayfirst=dayfirst)
        if d is None:
            lab = "unparsed"
        else:
            days = (as_of - d).days
            if days < 0:
                lab = "future"
            else:
                lab = labels[-1]
                lo = 0
                for j, b in enumerate(buckets):
                    if days <= b:
                        lab = labels[j]
                        break
        out[lab]["count"] += 1
        if vals is not None:
            n, _ = parse_number(vals[i])
            if n is not None:
                out[lab]["total"] += n
    return {"as_of": as_of, "buckets": [{"bucket": k, **v} for k, v in out.items()
                                        if v["count"] or k not in ("future", "unparsed")]}


# --------------------------------------------------------------------------- #
# Cross-domain — relate TWO datasets on a shared key (join + compare)
# --------------------------------------------------------------------------- #
def _join_key(v):
    """Normalise a key cell for matching: numbers/dates by value, text case/space-folded.
    So '  Widget A ' matches 'widget a', and 1,000 matches '1000'."""
    n, _ = parse_number(v)
    if n is not None and _s(v).replace(",", "").replace(".", "").lstrip("-").isdigit():
        return ("n", n)
    d, _ = parse_date(v)
    if d is not None:
        return ("d", d.isoformat())
    return ("t", " ".join(_s(v).lower().split()))


def join_on(l_header, l_rows, r_header, r_rows, on, how="inner"):
    """Join two tables on a shared key (`on` = one column name in both, or a list for a
    composite key). Text keys match case/whitespace-insensitively. Right-side non-key columns
    are carried across, prefixed `r_` on a name clash. Returns (header, rows, report) where
    report counts matched / left-only / right-only / duplicate-key rows — cross-set coverage
    is a finding, never silently dropped. how='inner' | 'left'."""
    keys = [on] if isinstance(on, str) else list(on)
    li = [col_index(l_header, k) for k in keys]
    ri = [col_index(r_header, k) for k in keys]

    def keyof(row, idx):
        return tuple(_join_key(row[j] if j < len(row) else "") for j in idx)

    r_index, r_dupe = {}, 0
    for row in r_rows:
        kk = keyof(row, ri)
        if kk in r_index:
            r_dupe += 1
        else:
            r_index[kk] = row
    r_carry = [j for j in range(len(r_header)) if j not in ri]      # right cols except the key(s)
    lset = {_s(h).lower() for h in l_header}
    out_header = list(l_header) + [
        (f"r_{r_header[j]}" if _s(r_header[j]).lower() in lset else r_header[j]) for j in r_carry]

    out_rows, matched, left_only, used = [], 0, 0, set()
    for row in l_rows:
        kk = keyof(row, li)
        rr = r_index.get(kk)
        if rr is not None:
            matched += 1
            used.add(kk)
            out_rows.append(list(row) + [rr[j] if j < len(rr) else "" for j in r_carry])
        else:
            left_only += 1
            if how == "left":
                out_rows.append(list(row) + ["" for _ in r_carry])
    right_only = sum(1 for kk in r_index if kk not in used)
    report = {"matched": matched, "left_only": left_only, "right_only": right_only,
              "right_dup_keys": r_dupe, "on": keys, "how": how}
    return out_header, out_rows, report


def _pearson(xs, ys):
    """Pearson r on two equal-length numeric sequences. float (a coefficient, not money);
    None if < 3 points or a side is constant."""
    pts = [(float(a), float(b)) for a, b in zip(xs, ys) if a is not None and b is not None]
    n = len(pts)
    if n < 3:
        return None
    mx = sum(p[0] for p in pts) / n
    my = sum(p[1] for p in pts) / n
    sxy = sum((p[0] - mx) * (p[1] - my) for p in pts)
    sxx = sum((p[0] - mx) ** 2 for p in pts)
    syy = sum((p[1] - my) ** 2 for p in pts)
    if sxx == 0 or syy == 0:
        return None
    return round(sxy / (sxx * syy) ** 0.5, 3)


def compare_series(a, b, a_label="A", b_label="B"):
    """Align two ORDERED series of (key, value) — e.g. two `period_series`, or our-price vs
    competitor-price by week — and read the relationship. Per shared key: gap (a−b), ratio,
    % diff. Overall: Pearson correlation, plus a ±1 lead/lag scan (does b at t−1 track a at t?).
    Correlation is association, NOT cause — the brief must name confounders. Values stay exact;
    only the coefficient is float."""
    da = OrderedDict((k, v) for k, v in a)
    db = dict(b)
    keys = [k for k in da if k in db]
    points = []
    for k in keys:
        av, bv = da[k], db[k]
        points.append({"key": k, a_label: av, b_label: bv, "gap": av - bv,
                       "ratio": (av / bv) if bv != 0 else None,
                       "pct_diff": ((av - bv) / bv) if bv != 0 else None})
    xs = [p[a_label] for p in points]
    ys = [p[b_label] for p in points]
    corr = _pearson(xs, ys)
    lead_lag = {"same": corr,
                "b_leads_1": _pearson(xs[1:], ys[:-1]),     # b at t-1 vs a at t
                "a_leads_1": _pearson(xs[:-1], ys[1:])}
    best = max(((k, v) for k, v in lead_lag.items() if v is not None),
               key=lambda kv: abs(kv[1]), default=(None, None))
    return {"a_label": a_label, "b_label": b_label, "points": points, "n": len(points),
            "a_only": [k for k in da if k not in db], "b_only": [k for k in db if k not in da],
            "correlation": corr, "lead_lag": lead_lag, "best_alignment": best[0]}


# --------------------------------------------------------------------------- #
# Shape detection (advisory — suggests the playbook, never decides silently)
# --------------------------------------------------------------------------- #
def suggest_playbook(header, rows):
    """Profile the table (shared profiler) and map columns to analysis roles.
    Advisory: the skill shows this to the user and confirms the question first."""
    prof = dataclean.profile_table(header, rows)
    roles = {"dates": [], "amounts": [], "categories": [], "ids": [], "other": []}
    n = prof["rows"] or 1
    for c in prof["columns"]:
        t = c["type"]
        if t == "date":
            roles["dates"].append(c["name"])
        elif t in ("number", "currency"):
            roles["amounts"].append(c["name"])
        elif t in ("categorical", "ordinal", "bool"):
            roles["categories"].append(c["name"])
        elif t == "text" and c["distinct"] >= 0.9 * n:
            roles["ids"].append(c["name"])                   # near-unique text = identifier
        else:
            roles["other"].append(c["name"])
    suggested = []
    if roles["amounts"]:
        suggested.append("numeric summary + outliers on: " + ", ".join(roles["amounts"]))
    if roles["categories"] and roles["amounts"]:
        suggested.append("breakdown/concentration by: " + ", ".join(roles["categories"]))
    elif roles["categories"]:
        suggested.append("count breakdown by: " + ", ".join(roles["categories"]))
    if roles["dates"]:
        suggested.append("period trend on: " + ", ".join(roles["dates"])
                         + (" (with amount)" if roles["amounts"] else " (counts)"))
        if roles["amounts"]:
            suggested.append("ageing from: " + ", ".join(roles["dates"]) + " (if these are due/open dates)")
    return {"profile": prof, "roles": roles, "suggested": suggested}


# --------------------------------------------------------------------------- #
# Rendering helpers
# --------------------------------------------------------------------------- #
def fmt(v, places=2):
    """Decimal -> display string with thousands separators; trims trailing zeros
    on whole numbers. None -> em-dash (a visible blank, never an invented 0)."""
    if v is None:
        return "—"
    if isinstance(v, Decimal):
        q = v.quantize(Decimal(10) ** -places) if places else v
        s = f"{q:,.{places}f}"
        if places and s.endswith("0" * places) and "." in s:
            s = s.split(".")[0]
        return s
    return str(v)


def pct(x, places=1):
    return "—" if x is None else f"{x * 100:.{places}f}%"


def render_md(title, header, table_rows):
    """A small, dependency-free markdown table for the insight brief."""
    lines = [f"### {title}", "", "| " + " | ".join(header) + " |",
             "|" + "|".join("---" for _ in header) + "|"]
    for r in table_rows:
        lines.append("| " + " | ".join(_s(c) if not isinstance(c, Decimal) else fmt(c)
                                       for c in r) + " |")
    return "\n".join(lines) + "\n"


def write_metrics_xlsx(sections, out_path):
    """sections = [(sheet_name, header, rows)] -> one workbook, one sheet each.
    Optional deliverable alongside the brief; needs openpyxl."""
    from openpyxl import Workbook
    wb = Workbook()
    wb.remove(wb.active)
    for name, header, rows in sections:
        ws = wb.create_sheet(title=str(name)[:31])
        ws.append([_s(h) for h in header])
        for r in rows:
            ws.append([float(c) if isinstance(c, Decimal) else c for c in r])
    wb.save(out_path)
    return out_path


# --------------------------------------------------------------------------- #
# Self-test
# --------------------------------------------------------------------------- #
def _self_test():
    header = ["Date", "Customer", "Region", "Amount"]
    rows = [
        ["05/01/2026", "Alpha", "North", "1,000"],
        ["12/01/2026", "Beta", "South", "2,000"],
        ["20/01/2026", "Alpha", "North", "1,500"],
        ["15/03/2026", "Gamma", "South", "(500)"],           # note: Feb is a gap month
        ["18/03/2026", "Alpha", "North", "9,000"],           # planted outlier
        ["25/03/2026", "Delta", "East", "junk"],             # unparseable amount
        ["", "Echo", "", "250"],                              # blank date + blank region
    ]

    s = numeric_summary(column(header, rows, "Amount"))
    assert s["n"] == 6 and s["skipped"] == 1, s
    assert s["total"] == Decimal("13250"), s["total"]         # exact Decimal, ( ) = negative
    assert s["median"] == Decimal("1250"), s["median"]
    assert s["negatives"] == 1

    o = outliers_iqr(column(header, rows, "Amount"))
    assert o["high"] == [Decimal("9000")] and o["high_count"] == 1, o

    b = breakdown(header, rows, "Customer", value="Amount")
    assert b["groups"][0]["key"] == "Alpha" and b["groups"][0]["total"] == Decimal("11500"), b
    assert b["skipped"] == 1
    assert b["has_negatives"] is True                                     # (500) = negative
    # shares are None when negatives are present (unreliable)
    assert all(g["share"] is None for g in b["groups"]), b
    br = breakdown(header, rows, "Region")                    # count measure + (blank) key
    assert any(g["key"] == "(blank)" for g in br["groups"])
    bz = breakdown(["Group", "Amount"], [["A", "10"], ["B", "-10"]],
                   "Group", value="Amount")
    assert bz["grand_total"] == Decimal(0), bz
    assert bz["top1_share"] is None and bz["top3_share"] is None, bz

    ts = period_series(header, rows, "Date", value="Amount")
    keys = [p["period"] for p in ts["periods"]]
    assert keys == ["2026-01", "2026-02", "2026-03"], keys    # gap month filled
    assert ts["periods"][1]["total"] == Decimal(0) and ts["gap_periods"] == 1
    assert ts["periods"][0]["total"] == Decimal("4500")
    assert ts["periods"][2]["delta"] == Decimal("8500"), ts["periods"][2]
    assert ts["bad_dates"] == 1                               # the blank date

    ag = ageing(header, rows, "Date", as_of="31/03/2026", value="Amount")
    by = {b["bucket"]: b for b in ag["buckets"]}
    assert by["0–30"]["count"] == 3 and by["61–90"]["count"] == 3, by
    assert by["unparsed"]["count"] == 1

    sp = suggest_playbook(header, rows)
    assert "Date" in sp["roles"]["dates"] and "Amount" in sp["roles"]["amounts"], sp["roles"]

    assert fmt(Decimal("1234.50")) == "1,234.50" and fmt(None) == "—"
    assert pct(Decimal("0.825")) == "82.5%"
    md = render_md("t", ["a"], [[Decimal("1000")]])
    assert "| 1,000 |" in md

    mix = currency_mix(["S$100", "SGD 50", "S$ 20"])
    assert mix == {"SGD"}, mix

    # join_on — cross-domain: our weekly sales vs scraped competitor prices on week x product
    lh = ["Week", "Product", "Units", "Our price"]
    lr = [["2026-W01", "Widget A", "100", "10.00"],
          ["2026-W01", "Widget B", "40", "20.00"],
          ["2026-W02", "widget a", "90", "10.50"],           # case-fold key match
          ["2026-W03", "Widget A", "70", "11.00"]]           # no competitor row → left_only
    rh = ["Week", "Product", "Comp price"]
    rr = [["2026-W01", "Widget A", "9.50"],
          ["2026-W01", "Widget B", "21.00"],
          ["2026-W02", "Widget A", "9.80"],
          ["2026-W04", "Widget A", "9.90"]]                  # no sales row → right_only
    jh, jrows, rep = join_on(lh, lr, rh, rr, on=["Week", "Product"])
    assert rep["matched"] == 3 and rep["left_only"] == 1 and rep["right_only"] == 1, rep
    assert "Comp price" in jh
    # our price - competitor price on the matched rows (exact Decimal)
    gaps = [parse_number(column(jh, jrows, "Our price")[i])[0]
            - parse_number(column(jh, jrows, "Comp price")[i])[0] for i in range(len(jrows))]
    assert gaps == [Decimal("0.50"), Decimal("-1.00"), Decimal("0.70")], gaps

    # compare_series — position + correlation + lead/lag
    ours = [("W1", Decimal("10")), ("W2", Decimal("11")), ("W3", Decimal("12")), ("W4", Decimal("13"))]
    comp = [("W1", Decimal("9")), ("W2", Decimal("10")), ("W3", Decimal("11")), ("W4", Decimal("12"))]
    cmp = compare_series(ours, comp, "Ours", "Comp")
    assert cmp["n"] == 4 and cmp["points"][0]["gap"] == Decimal("1")
    assert cmp["correlation"] == 1.0, cmp["correlation"]      # perfectly co-moving
    assert cmp["points"][1]["pct_diff"] == Decimal("11") / Decimal("10") - 1

    print("analyse.py self-test OK")


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        _self_test()
    else:
        print(__doc__)
