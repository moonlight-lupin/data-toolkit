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

import datetime as dt
import pathlib
import re
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
FILTER_OPS = ("==", "!=", ">", ">=", "<", "<=", "in", "not_in",
              "between", "not_between", "contains", "is_empty", "not_empty")

_NEEDS_VALUE = tuple(op for op in FILTER_OPS if op not in ("is_empty", "not_empty"))


_DATE_HINT = re.compile(
    r"[/]|\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)|\d{4}-\d{1,2}-\d{1,2}", re.I)


def _kind_of(v) -> str:
    """Classify a value for comparison: ``date`` | ``number`` | ``string``.

    Dates are tested **before** numbers, but only for values that actually look like
    a date. Both halves of that rule are load-bearing:

    - `parse_number('15/02/2026')` returns `15022026` — it strips the separators — so
      without date-first a date column compares as huge integers and 15 Feb sorts
      *after* 1 Mar.
    - Without the "looks like a date" guard, a plain integer would be read as an Excel
      serial and silently become a date.
    """
    if isinstance(v, (dt.date, dt.datetime)):
        return "date"
    if isinstance(v, bool):
        return "string"
    if isinstance(v, (int, float, Decimal)):
        return "number"
    s = _s(v)
    if s == "":
        return "string"
    if _DATE_HINT.search(s) and parse_date(s)[0] is not None:
        return "date"
    if parse_number(s)[0] is not None:
        return "number"
    if parse_date(s)[0] is not None:
        return "date"
    return "string"


def _coerce_pair(a, b):
    """Coerce two cells to a shared comparable type. Returns ``(a, b, kind)`` where
    kind is ``date`` | ``number`` | ``string`` | ``mixed``.

    ``mixed`` means the two sides have genuinely different types — a text cell against
    a numeric threshold, say. That is reported, never quietly resolved: falling back to
    a string compare would make `'n/a' > 1000` **true**, which is exactly the kind of
    silent wrong answer this toolkit exists to avoid."""
    ka, kb = _kind_of(a), _kind_of(b)
    if ka == kb == "date":
        return parse_date(a)[0], parse_date(b)[0], "date"
    if ka == kb == "number":
        return parse_number(a)[0], parse_number(b)[0], "number"
    if ka == kb == "string":
        return _s(a).lower(), _s(b).lower(), "string"
    return _s(a).lower(), _s(b).lower(), "mixed"


def _cmp_pass(cell, op, target) -> tuple[bool, bool]:
    """Evaluate one comparison. Returns (passed, comparable).

    `comparable` is False when the operator needed an ordering but the two sides
    would not coerce to a shared comparable type — the row is excluded and counted,
    never quietly treated as passing."""
    if op == "is_empty":
        return _s(cell) == "", True
    if op == "not_empty":
        return _s(cell) != "", True
    if op == "contains":
        return _s(target).lower() in _s(cell).lower(), True
    if op in ("in", "not_in"):
        items = target if isinstance(target, (list, tuple, set)) else [target]
        hit = False
        for t in items:
            a, b, _kind = _coerce_pair(cell, t)   # coerce per item: a list may mix types
            if a == b:
                hit = True
                break
        return (hit if op == "in" else not hit), True
    if op in ("between", "not_between"):
        if not isinstance(target, (list, tuple)) or len(target) != 2:
            raise ValueError(f"{op!r} needs lo/hi (or a two-item value), got {target!r}")
        lo_c, hi_c = target
        a1, lo, k1 = _coerce_pair(cell, lo_c)
        a2, hi, k2 = _coerce_pair(cell, hi_c)
        if k1 != k2 or "mixed" in (k1, k2):
            return False, False           # excluded and counted, never assumed inside
        try:
            inside = lo <= a1 and a2 <= hi        # inclusive of BOTH ends
        except TypeError:
            return False, False
        return (inside if op == "between" else not inside), True

    a, b, kind = _coerce_pair(cell, target)
    # Equality survives a type mismatch — '' == 1000 is simply false, no ambiguity.
    if op == "==":
        return a == b, True
    if op == "!=":
        return a != b, True
    # Ordering does not: a text cell against a numeric threshold has no defensible
    # answer, so the row drops out and the count is reported.
    if kind == "mixed":
        return False, False
    try:
        if op == ">":
            return a > b, True
        if op == ">=":
            return a >= b, True
        if op == "<":
            return a < b, True
        if op == "<=":
            return a <= b, True
    except TypeError:
        return False, False
    raise ValueError(f"unsupported filter op {op!r}; supported: {list(FILTER_OPS)}")


def filter_rows(header, rows, filters):
    """Filter rows declaratively — the standard form of the ad-hoc filtering that
    otherwise gets hand-written differently on every run.

    ``filters`` is a list of ``{"column": ..., "op": ..., "value": ...}``. Filters
    combine with **AND** — a row must pass every one.

    Operator semantics, chosen to match what a finance reader expects:

    - ``== != > >= < <=`` — numeric when both sides parse as numbers (via
      ``parse_number``, so ``'1,200'`` and ``'(500)'`` work), else dates when both
      parse as dates, else case-insensitive string comparison.
    - ``in`` / ``not_in`` — membership, given as ``"values": [...]`` (or ``"value"``).
    - ``between`` / ``not_between`` — ``"lo"``/``"hi"`` (or ``"value": [lo, hi]``),
      **inclusive of both ends**, because finance ranges are quoted inclusively
      ("30–60 days" contains both 30 and 60).
    - ``contains`` — case-insensitive substring.
    - ``is_empty`` / ``not_empty`` — blank or whitespace-only; no value needed.

    The column key may be ``"col"`` or ``"column"``.

    Returns ``(filtered_rows, report)`` with ``n_in`` / ``n_out`` / ``n_dropped`` and,
    per filter, how many rows it removed and how many it could not compare — so a
    filter that silently ate the dataset is visible rather than mysterious.
    Per-filter ``removed`` is attributed in order (each filter sees what survived the
    previous one); the totals are exact either way. The input list is not mutated.

    Unknown columns and unknown operators raise, rather than matching nothing —
    a typo'd column name must not look like "no results".
    """
    kept = list(rows)
    per_filter = []
    for f in (filters or []):
        if not isinstance(f, dict):
            raise ValueError(f"each filter must be a dict, got {f!r}")
        col = f.get("col", f.get("column"))
        op = _s(f.get("op") or "==")
        if op not in FILTER_OPS:
            raise ValueError(f"unsupported filter op {op!r}; supported: {list(FILTER_OPS)}")
        # Each operator family names its payload differently; accept the spec's key
        # and the generic "value" so a caller need not remember which is which.
        if op in ("in", "not_in"):
            target = f["values"] if "values" in f else f.get("value")
            if target is None and "values" not in f and "value" not in f:
                raise ValueError(f"filter on {col!r} with op {op!r} needs 'values'")
        elif op in ("between", "not_between"):
            if "lo" in f or "hi" in f:
                target = [f.get("lo"), f.get("hi")]
            else:
                target = f.get("value")
            if target is None:
                raise ValueError(f"filter on {col!r} with op {op!r} needs 'lo' and 'hi'")
        else:
            target = f.get("value")
            if op in _NEEDS_VALUE and "value" not in f:
                raise ValueError(f"filter on {col!r} with op {op!r} needs a 'value'")
        j = col_index(header, col)                # raises with the real names on a typo
        before = len(kept)
        survivors, incomparable = [], 0
        for r in kept:
            cell = r[j] if j < len(r) else ""
            passed, comparable = _cmp_pass(cell, op, target)
            if not comparable:
                incomparable += 1
            if passed:
                survivors.append(r)
        kept = survivors
        per_filter.append({"column": _s(col), "op": op, "value": target,
                           "removed": before - len(kept), "incomparable": incomparable})
    report = {"n_in": len(rows), "n_out": len(kept),
              "n_dropped": len(rows) - len(kept), "filters": per_filter,
              "incomparable": sum(p["incomparable"] for p in per_filter)}
    return kept, report


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
# Concentration — HHI + top-N share + classification
# --------------------------------------------------------------------------- #
def concentration(values, top_n=4):
    """Revenue/customer/portfolio concentration on a parseable numeric column.

    **Pass pre-aggregated group totals, not raw transaction lines** — e.g. the
    ``total`` column from a ``breakdown(header, rows, by="Customer", value="Revenue")``
    result, or a list of per-customer annual revenues. Passing raw lines (one
    value per transaction) inflates ``n_groups`` and understates concentration.

    Returns the Herfindahl-Hirschman Index (HHI, 0–10000 scale — the standard
    antitrust metric), top-N share, the count of groups needed to reach 80%,
    and a classification: fragmented / moderate / concentrated / highly concentrated.
    HHI uses squared shares; a monopoly (one group = 100%) scores 10000.

    ``values`` is a raw column (like ``numeric_summary``). Negative totals are
    treated as unreliable — HHI and shares return None when negatives net off,
    matching ``breakdown``'s convention.
    """
    dec, skipped = numbers(values)
    if not dec:
        return {"n": 0, "skipped": skipped, "hhi": None, "top_n_share": None,
                "groups_to_80": None, "classification": "no data"}
    if any(v < 0 for v in dec):
        return {"n": len(dec), "skipped": skipped, "hhi": None, "top_n_share": None,
                "groups_to_80": None, "classification": "unreliable (negatives present)"}
    total = sum(dec)
    if total == 0:
        return {"n": len(dec), "skipped": skipped, "hhi": None, "top_n_share": None,
                "groups_to_80": None, "classification": "unreliable (total is zero)"}
    # Each value is one group's total (e.g. one customer's revenue). Share = value / total.
    shares = [(v, Decimal(v) / total) for v in dec]
    shares.sort(key=lambda t: t[1], reverse=True)
    # HHI on the 0–10000 scale: sum of squared percentage shares (share*100)²
    hhi = sum((s * Decimal(100)) ** 2 for _, s in shares)
    top_share = sum(s for _, s in shares[:top_n])
    cum, g80 = Decimal(0), None
    for rank, (_, s) in enumerate(shares, 1):
        cum += s
        if g80 is None and cum >= Decimal("0.8"):
            g80 = rank
    n_groups = len(shares)
    if hhi < Decimal(1500):
        cls = "fragmented"
    elif hhi < Decimal(2500):
        cls = "moderate"
    elif hhi < Decimal(5000):
        cls = "concentrated"
    else:
        cls = "highly concentrated"
    return {"n": len(dec), "skipped": skipped, "n_groups": n_groups,
            "hhi": hhi, "top_n_share": top_share, "groups_to_80": g80,
            "classification": cls}


# --------------------------------------------------------------------------- #
# Pivot / cross-tab — 2D aggregation matrix
# --------------------------------------------------------------------------- #
def pivot(header, rows, rows_col, cols_col, value=None, aggfunc="sum"):
    """Cross-tabulate: group by ``rows_col`` (rows) × ``cols_col`` (columns),
    aggregating ``value`` (or row counts when ``value`` is None).

    ``aggfunc``: ``"sum"`` (default) | ``"count"`` | ``"mean"``.

    Returns a dict with the row keys, column keys (both sorted), the matrix
    (list of lists, aligned to the key order), row/column grand totals, and a
    skipped count (unparseable values). Like ``breakdown``, negative sums make
    shares unreliable — the caller decides whether to show them.

    Blank cells in either dimension group under ``(blank)`` (matching
    ``breakdown``'s convention).
    """
    assert aggfunc in ("sum", "count", "mean")
    if value is None:
        aggfunc = "count"  # no value → always row counts
    ri = col_index(header, rows_col)
    ci = col_index(header, cols_col)
    vi = col_index(header, value) if value else None
    cell = {}  # {(row_key, col_key): [list of Decimal values]}
    row_keys, col_keys = [], []
    skipped = 0
    for r in rows:
        rk = _s(r[ri] if ri < len(r) else "") or "(blank)"
        ck = _s(r[ci] if ci < len(r) else "") or "(blank)"
        if rk not in row_keys:
            row_keys.append(rk)
        if ck not in col_keys:
            col_keys.append(ck)
        if vi is not None:
            raw = r[vi] if vi < len(r) else ""
            n, _ = parse_number(raw)
            if n is None:
                # blank or unparseable — skip this cell, not the whole row
                if _s(raw) != "":
                    skipped += 1
                continue
            cell.setdefault((rk, ck), []).append(n)
        else:
            cell.setdefault((rk, ck), []).append(Decimal(1))
    row_keys.sort()
    col_keys.sort()
    matrix = []
    for rk in row_keys:
        row_vals = []
        for ck in col_keys:
            vals = cell.get((rk, ck), [])
            if not vals:
                row_vals.append(None)
            elif aggfunc == "sum":
                row_vals.append(sum(vals, Decimal(0)))
            elif aggfunc == "count":
                row_vals.append(Decimal(len(vals)))
            else:  # mean
                row_vals.append(sum(vals, Decimal(0)) / Decimal(len(vals)))
        matrix.append(row_vals)
    # Grand totals
    row_totals = []
    for row_vals in matrix:
        nums = [v for v in row_vals if v is not None]
        row_totals.append(sum(nums, Decimal(0)) if nums else None)
    col_totals = []
    for j in range(len(col_keys)):
        nums = [matrix[i][j] for i in range(len(row_keys)) if matrix[i][j] is not None]
        col_totals.append(sum(nums, Decimal(0)) if nums else None)
    grand = sum((t for t in col_totals if t is not None), Decimal(0))
    return {"rows_col": rows_col, "cols_col": cols_col, "measure": value or "rows",
            "aggfunc": aggfunc, "row_keys": row_keys, "col_keys": col_keys,
            "matrix": matrix, "row_totals": row_totals, "col_totals": col_totals,
            "grand_total": grand, "n_rows": len(row_keys), "n_cols": len(col_keys),
            "skipped": skipped}


# --------------------------------------------------------------------------- #
# Distribution shape — skewness + kurtosis
# --------------------------------------------------------------------------- #
def distribution(values):
    """Skewness and (excess) kurtosis on the parseable cells.

    Uses the sample-standardised Fisher-Pearson coefficients (the same
    definitions as Excel's SKEW and KURT). Both are float (shape coefficients,
    not money). Returns a normality classification:

    - ``symmetric`` — |skewness| < 0.5 and |kurtosis| < 1
    - ``moderately skewed`` — 0.5 ≤ |skewness| < 1
    - ``highly skewed`` — |skewness| ≥ 1
    - ``heavy-tailed`` — kurtosis > 3 (excess) regardless of skew

    Needs ≥ 4 points; below that shape metrics are not meaningful.
    """
    dec, skipped = numbers(values)
    n = len(dec)
    if n < 4:
        return {"n": n, "skipped": skipped, "skewness": None, "kurtosis": None,
                "classification": "insufficient data (need ≥4 values)"}
    xs = [float(v) for v in dec]
    mean = sum(xs) / n
    # Sample standard deviation (n-1 denominator)
    var = sum((x - mean) ** 2 for x in xs) / (n - 1)
    sd = var ** 0.5
    if sd == 0:
        return {"n": n, "skipped": skipped, "skewness": None, "kurtosis": None,
                "classification": "constant (no spread)"}
    # Fisher-Pearson skewness (g1)
    z3 = sum(((x - mean) / sd) ** 3 for x in xs)
    g1 = (n / ((n - 1) * (n - 2))) * z3
    # Excess kurtosis (g2)
    z4 = sum(((x - mean) / sd) ** 4 for x in xs)
    g2 = ((n * (n + 1)) / ((n - 1) * (n - 2) * (n - 3))) * z4 \
         - (3 * (n - 1) ** 2) / ((n - 2) * (n - 3))
    abs_skew = abs(g1)
    if g2 > 3:
        cls = "heavy-tailed"
    elif abs_skew >= 1:
        cls = "highly skewed"
    elif abs_skew >= 0.5:
        cls = "moderately skewed"
    else:
        cls = "symmetric"
    return {"n": n, "skipped": skipped, "skewness": round(g1, 3),
            "kurtosis": round(g2, 3), "classification": cls}


# --------------------------------------------------------------------------- #
# Trend — linear regression slope + R² + direction
# --------------------------------------------------------------------------- #
def trend(series):
    """Simple linear trend on an ordered series of ``(key, value)`` tuples.

    Fits y = a + b·x (ordinary least squares) and returns the slope, R², and a
    directional classification. ``series`` is the same shape ``compare_series``
    accepts — e.g. the ``periods`` from ``period_series`` mapped to
    ``[(p["period"], p["total"]) for p in ts["periods"]]``.

    Classification:
    - ``rising`` / ``falling`` — |slope| meaningful and R² ≥ 0.5
    - ``weakly rising`` / ``weakly falling`` — R² 0.25–0.5
    - ``flat`` — |slope| near zero OR R² < 0.25
    - ``insufficient data`` — fewer than 3 points

    Slope is per-period (the unit of the input keys). Descriptive only — never
    a forecast. A trend over 3 periods is "early"; over 2 it is not a trend.
    """
    pts = [(i, float(v)) for i, (_, v) in enumerate(series) if v is not None]
    n = len(pts)
    if n < 3:
        return {"n": n, "slope": None, "r_squared": None,
                "classification": "insufficient data (need ≥3 points)"}
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    mx, my = sum(xs) / n, sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    sxy = sum((xs[i] - mx) * (ys[i] - my) for i in range(n))
    syy = sum((y - my) ** 2 for y in ys)
    if sxx == 0:
        return {"n": n, "slope": 0.0, "r_squared": None,
                "classification": "flat (no variation in x)"}
    slope = sxy / sxx
    r2 = (sxy ** 2) / (sxx * syy) if syy > 0 else None
    r2v = r2 if r2 is not None else 0.0
    if abs(slope) < 1e-12 or r2v < 0.25:
        cls = "flat"
    elif r2v >= 0.5:
        cls = "rising" if slope > 0 else "falling"
    else:
        cls = "weakly rising" if slope > 0 else "weakly falling"
    return {"n": n, "slope": round(slope, 6), "r_squared": round(r2v, 3),
            "classification": cls}


# --------------------------------------------------------------------------- #
# Percentile — arbitrary quantiles with linear interpolation
# --------------------------------------------------------------------------- #
def percentile(values, q):
    """Arbitrary percentile(s) on the parseable cells, with linear interpolation
    between closest ranks (the standard "inclusive" method — matches numpy's
    default and Excel's ``PERCENTILE.INC``).

    ``q`` is a float in [0, 1], or a list of such floats. Returns a dict
    ``{"value": Decimal, "n": int, "skipped": int}`` when ``q`` is a float,
    or a dict ``{q_float: Decimal}`` when ``q`` is a list. Typical uses:
    p90, p95, p99 for VaR / latency SLOs / top-decile.

    Needs ≥1 parseable value; below that returns None (or a dict of Nones).
    """
    single = isinstance(q, (int, float))
    qs = [Decimal(str(q))] if single else [Decimal(str(x)) for x in q]
    dec, skipped = numbers(values)
    if not dec:
        if single:
            return {"value": None, "n": 0, "skipped": skipped}
        return {float(qi): None for qi in qs}
    sv = sorted(dec)
    n = len(sv)
    out = {}
    for qi in qs:
        if qi <= 0:
            out[qi] = sv[0]
        elif qi >= 1:
            out[qi] = sv[-1]
        else:
            # Linear interpolation: position = q * (n - 1)
            pos = qi * Decimal(n - 1)
            lo = int(pos)
            hi = min(lo + 1, n - 1)
            frac = pos - Decimal(lo)
            out[qi] = sv[lo] + frac * (sv[hi] - sv[lo])
    if single:
        return {"value": out[qs[0]], "n": n, "skipped": skipped}
    return {float(qi): v for qi, v in out.items()}


# --------------------------------------------------------------------------- #
# Cohort / retention — group by first-period, track over subsequent periods
# --------------------------------------------------------------------------- #
def cohort(header, rows, id_col, date_col, value=None, grain="month", dayfirst=True):
    """Cohort retention matrix: group entities by their first-active period,
    then track activity over subsequent periods.

    Each row is a cohort (first-period). Each column is "periods since first"
    (0 = first period, 1 = next, etc.).

    - **Count mode** (``value=None``): cells = count of distinct entities active
      in that cohort×period. Retention = active_entities / cohort_size (0–1).
    - **Value mode** (``value=``): cells = sum of ``value`` for active entities.
      Retention is still computed from **entity counts** (active/size), so it
      stays a 0–1 fraction. The value matrix is returned separately as
      ``value_matrix``.

    Returns: cohorts (sorted), ``max_offset``, ``matrix`` (entity counts or value
    sums), ``retention`` (0–1 fractions, always from entity counts),
    ``value_matrix`` (value sums, only in value mode; None otherwise),
    ``cohort_sizes``, and skipped counts.

    All cohort rows are padded to ``max_offset + 1`` (rectangular). An entity is
    "active" in a period if it has ≥1 row with a parseable date in that period.
    """
    assert grain in ("month", "quarter", "year")
    idi = col_index(header, id_col)
    di = col_index(header, date_col)
    vi = col_index(header, value) if value else None
    # Collect per-entity: first period, set of active periods, per-period value sums
    entities = {}  # {id_key: {"first": period_str, "periods": {period: {"count": n, "total": Decimal}}}}
    bad_dates, skipped_vals = 0, 0
    for r in rows:
        eid = _s(r[idi] if idi < len(r) else "")
        if not eid:
            continue
        raw_d = r[di] if di < len(r) else ""
        d, _ = parse_date(raw_d, dayfirst=dayfirst)
        if d is None:
            bad_dates += 1
            continue
        p = _period_key(d, grain)
        ent = entities.setdefault(eid, {"first": None, "periods": {}})
        if ent["first"] is None or p < ent["first"]:
            ent["first"] = p
        slot = ent["periods"].setdefault(p, {"count": 0, "total": Decimal(0)})
        slot["count"] += 1
        if vi is not None:
            raw_v = r[vi] if vi < len(r) else ""
            n, _ = parse_number(raw_v)
            if n is None and _s(raw_v) != "":
                skipped_vals += 1
            elif n is not None:
                slot["total"] += n
    if not entities:
        return {"cohorts": [], "max_offset": -1, "matrix": [], "retention": [],
                "value_matrix": None, "cohort_sizes": [],
                "bad_dates": bad_dates, "skipped": skipped_vals}
    # Group entities by first period
    cohort_groups = {}  # {first_period: [entity dicts]}
    for ent in entities.values():
        cohort_groups.setdefault(ent["first"], []).append(ent)
    cohort_keys = sorted(cohort_groups.keys())
    # First pass: compute max_offset across all cohorts
    max_offset = 0
    per_cohort_offsets = {}
    for ck in cohort_keys:
        ents = cohort_groups[ck]
        offset_activity = {}  # {offset: {"count": n, "total": Decimal}}
        for ent in ents:
            for p, slot in ent["periods"].items():
                offset = _periods_between(ck, p, grain)
                if offset < 0:
                    continue
                acc = offset_activity.setdefault(offset, {"count": 0, "total": Decimal(0)})
                acc["count"] += 1  # one entity active in this period
                acc["total"] += slot["total"]
        per_cohort_offsets[ck] = offset_activity
        if offset_activity:
            max_offset = max(max_offset, max(offset_activity.keys()))
    # Second pass: build padded rectangular matrices
    matrix = []
    value_matrix = [] if vi is not None else None
    retention = []
    cohort_sizes = []
    for ck in cohort_keys:
        ents = cohort_groups[ck]
        size = len(ents)
        cohort_sizes.append(size)
        offset_activity = per_cohort_offsets[ck]
        row = []
        ret_row = []
        vrow = [] if vi is not None else None
        for off in range(max_offset + 1):
            acc = offset_activity.get(off)
            if acc is None:
                row.append(Decimal(0))
                ret_row.append(Decimal(0) / Decimal(size) if size else None)
                if vrow is not None:
                    vrow.append(Decimal(0))
            else:
                if vi is not None:
                    row.append(acc["total"])  # value sum
                    vrow.append(acc["total"])
                else:
                    row.append(Decimal(acc["count"]))  # entity count
                # Retention is ALWAYS entity-count-based (0–1 fraction)
                ret_row.append(Decimal(acc["count"]) / Decimal(size) if size else None)
        matrix.append(row)
        retention.append(ret_row)
        if vrow is not None:
            value_matrix.append(vrow)
    return {"grain": grain, "measure": value or "entities",
            "cohorts": cohort_keys, "max_offset": max_offset,
            "matrix": matrix, "retention": retention,
            "value_matrix": value_matrix,
            "cohort_sizes": cohort_sizes,
            "bad_dates": bad_dates, "skipped": skipped_vals}


def _periods_between(start_key, end_key, grain):
    """Number of periods from start to end (inclusive). Returns 0 for same period."""
    if grain == "year":
        return int(end_key) - int(start_key)
    if grain == "quarter":
        sy, sq = int(end_key.split("-Q")[0]), int(end_key.split("-Q")[1])
        ey, eq = int(start_key.split("-Q")[0]), int(start_key.split("-Q")[1])
        return (sy - ey) * 4 + (sq - eq)
    sy, sm = int(end_key.split("-")[0]), int(end_key.split("-")[1])
    ey, em = int(start_key.split("-")[0]), int(start_key.split("-")[1])
    return (sy - ey) * 12 + (sm - em)


# --------------------------------------------------------------------------- #
# Correlation matrix — pairwise Pearson across N numeric columns
# --------------------------------------------------------------------------- #
def correlation_matrix(header, rows, columns):
    """Pairwise Pearson correlation across ``columns`` (a list of column names).

    Returns a symmetric matrix of coefficients (float, -1 to 1), the column
    labels, and a flag for any constant column (correlation undefined).
    Diagonal is always 1.0. Needs ≥3 rows per column; below that returns None
    for that pair (matching ``_pearson``'s convention).

    Rows are aligned **row-wise**: for each pair of columns, only rows where
    BOTH cells parse as numbers are kept (matching ``compare_series``'s
    align-by-key convention). A junk cell in one column does not shift the
    pairing of later rows.

    Correlation is association, NOT cause — the brief must name confounders.
    """
    col_indices = [col_index(header, c) for c in columns]
    n_cols = len(columns)
    # Pre-parse: for each column, a list of (row_idx, float_value) for parseable cells
    parsed = []
    for ci in col_indices:
        col_vals = []
        for ri, r in enumerate(rows):
            raw = r[ci] if ci < len(r) else ""
            n, _ = parse_number(raw)
            if n is not None:
                col_vals.append((ri, float(n)))
        parsed.append(col_vals)
    matrix = [[None] * n_cols for _ in range(n_cols)]
    for i in range(n_cols):
        for j in range(i, n_cols):
            if i == j:
                matrix[i][j] = 1.0
                continue
            # Align by row index: keep only rows where BOTH columns parsed
            i_by_row = {ri: v for ri, v in parsed[i]}
            j_by_row = {ri: v for ri, v in parsed[j]}
            common_rows = sorted(set(i_by_row) & set(j_by_row))
            if len(common_rows) < 3:
                matrix[i][j] = None
                matrix[j][i] = None
                continue
            xi = [i_by_row[ri] for ri in common_rows]
            yj = [j_by_row[ri] for ri in common_rows]
            r = _pearson(xi, yj)
            matrix[i][j] = r
            matrix[j][i] = r
    return {"columns": list(columns), "matrix": matrix, "n_cols": n_cols}


# --------------------------------------------------------------------------- #
# Rolling / moving average — trailing window aggregates
# --------------------------------------------------------------------------- #
def rolling(series, window, func="mean"):
    """Trailing-window aggregate on an ordered series of ``(key, value)`` tuples.

    ``func``: ``"mean"`` (default) | ``"sum"`` | ``"median"``.

    Returns a list of ``(key, value)`` with the same length as the input. The
    first ``window - 1`` entries have ``None`` (not enough history yet). Pairs
    naturally with ``period_series`` output:

        ts = period_series(header, rows, "Date", value="Amount")
        smoothed = rolling([(p["period"], p["total"]) for p in ts["periods"]], 3)

    Window must be ≥1. Descriptive smoothing only — never a forecast.

    Note: ``None`` values in the input are skipped, so a window containing
    ``None`` effectively shortens to the non-None values within it. The first
    ``window - 1`` entries are always ``None`` (not enough history yet).
    """
    assert func in ("mean", "sum", "median")
    assert window >= 1
    out = []
    for i, (key, val) in enumerate(series):
        if val is None or i < window - 1:
            out.append((key, None))
            continue
        window_vals = [series[j][1] for j in range(i - window + 1, i + 1)
                       if series[j][1] is not None]
        if not window_vals:
            out.append((key, None))
            continue
        if func == "sum":
            agg = sum(Decimal(str(v)) for v in window_vals)
        elif func == "median":
            sv = sorted(Decimal(str(v)) for v in window_vals)
            agg = _median(sv)
        else:  # mean
            agg = sum(Decimal(str(v)) for v in window_vals) / Decimal(len(window_vals))
        out.append((key, agg))
    return out


# --------------------------------------------------------------------------- #
# Gini coefficient — inequality of distribution (0 = equal, 1 = concentrated)
# --------------------------------------------------------------------------- #
def gini(values):
    """Gini coefficient on the parseable cells (0 = perfectly equal,
    1 = perfectly concentrated). Complements ``concentration``'s HHI —
    Gini captures inequality of distribution; HHI captures number + size
    of groups. Both are valid for revenue/customer concentration.

    Uses the standard sorted formula:
        G = (2 * Σ(i * x_i)) / (n * Σ x_i) - (n + 1) / n
    where x_i are sorted ascending and i is 1-indexed.

    Returns float (a coefficient, not money). Negatives make Gini unreliable —
    returns None with a classification, matching ``concentration``'s convention.
    Needs ≥2 values.
    """
    dec, skipped = numbers(values)
    n = len(dec)
    if n < 2:
        return {"n": n, "skipped": skipped, "gini": None,
                "classification": "insufficient data (need ≥2 values)"}
    if any(v < 0 for v in dec):
        return {"n": n, "skipped": skipped, "gini": None,
                "classification": "unreliable (negatives present)"}
    total = sum(dec)
    if total == 0:
        return {"n": n, "skipped": skipped, "gini": None,
                "classification": "unreliable (total is zero)"}
    sv = sorted(dec)
    # G = (2 * Σ i*x_i) / (n * Σ x_i) - (n+1)/n
    weighted_sum = sum(Decimal(i + 1) * sv[i] for i in range(n))
    g = (Decimal(2) * weighted_sum) / (Decimal(n) * total) - Decimal(n + 1) / Decimal(n)
    g_float = float(g)
    if g_float < 0.25:
        cls = "relatively equal"
    elif g_float < 0.45:
        cls = "moderate inequality"
    elif g_float < 0.6:
        cls = "high inequality"
    else:
        cls = "extreme inequality"
    return {"n": n, "skipped": skipped, "gini": round(g_float, 4),
            "classification": cls}


# --------------------------------------------------------------------------- #
# Seasonality — average by month-of-year (or quarter)
# --------------------------------------------------------------------------- #
def seasonality(header, rows, date_col, value=None, grain="month", dayfirst=True):
    """Seasonal pattern: average value (or count) by month-of-year (1–12) or
    quarter (1–4), across all years in the data.

    Returns the average per season, the share of each season, and the
    seasonal index (season average / overall average — 1.0 = average,
    >1.0 = above-average season, <1.0 = below). Surfaces "Q4 is always
    strong" patterns that ``period_series``'s trend line hides.

    Gap periods (months with no data) are included as zero, matching
    ``period_series``'s convention. Needs ≥1 parseable date.
    """
    assert grain in ("month", "quarter")
    dates = column(header, rows, date_col)
    vals = column(header, rows, value) if value else None
    seasons = {i: {"count": 0, "total": Decimal(0)} for i in
               (range(1, 13) if grain == "month" else range(1, 5))}
    bad_dates, skipped_vals = 0, 0
    for i, raw in enumerate(dates):
        if _s(raw) == "":
            bad_dates += 1
            continue
        d, _ = parse_date(raw, dayfirst=dayfirst)
        if d is None:
            bad_dates += 1
            continue
        s = d.month if grain == "month" else (d.month - 1) // 3 + 1
        seasons[s]["count"] += 1
        if vals is not None:
            n, _ = parse_number(vals[i])
            if n is None and _s(vals[i]) != "":
                skipped_vals += 1
            elif n is not None:
                seasons[s]["total"] += n
    measure = "total" if value else "count"
    grand = sum(s[measure] for s in seasons.values())
    n_seasons = len(seasons)
    # Overall average: mean of seasons that have data (not grand/12, which
    # dilutes the index when some months have no rows)
    seasons_with_data = [s for s in seasons.values() if s["count"] > 0]
    overall_avg = (sum(s[measure] for s in seasons_with_data) / Decimal(len(seasons_with_data))
                    if seasons_with_data else Decimal(0))
    out = []
    for s in sorted(seasons):
        val = seasons[s][measure]
        avg = val / Decimal(seasons[s]["count"]) if seasons[s]["count"] else Decimal(0)
        share = val / grand if grand else None
        index = (avg / overall_avg) if overall_avg else None
        out.append({"season": s, "count": seasons[s]["count"], "total": val,
                    "average": avg, "share": share, "index": index})
    return {"grain": grain, "measure": value or "rows", "seasons": out,
            "grand_total": grand, "overall_average": overall_avg,
            "n_seasons_with_data": len(seasons_with_data),
            "bad_dates": bad_dates, "skipped": skipped_vals}


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

    # concentration — HHI + top-N share + classification
    # One dominant customer (90% of revenue) = highly concentrated
    conc = concentration(["900", "50", "30", "20"])
    assert conc["n"] == 4 and conc["n_groups"] == 4, conc
    assert conc["hhi"] is not None and conc["hhi"] > Decimal(5000), conc
    assert conc["classification"] == "highly concentrated", conc
    assert conc["top_n_share"] is not None and conc["top_n_share"] > Decimal("0.9")
    # Fragmented — 10 equal-sized groups → HHI = 10 * (10%)² = 1000
    conc2 = concentration(["10"] * 10)
    assert conc2["hhi"] < Decimal(1500), conc2
    assert conc2["classification"] == "fragmented", conc2
    # Negatives → unreliable
    conc3 = concentration(["100", "-50", "60"])
    assert conc3["hhi"] is None and "negatives" in conc3["classification"], conc3
    # Empty
    conc4 = concentration([])
    assert conc4["hhi"] is None and conc4["classification"] == "no data"

    # pivot — cross-tab Region × Customer by Amount (sum)
    pv = pivot(header, rows, "Region", "Customer", value="Amount")
    assert pv["n_rows"] == 4 and pv["n_cols"] == 5, (pv["n_rows"], pv["n_cols"])  # incl (blank)
    assert "North" in pv["row_keys"] and "Alpha" in pv["col_keys"]
    # North × Alpha = 1000 + 1500 + 9000 = 11500
    ni = pv["row_keys"].index("North")
    ai = pv["col_keys"].index("Alpha")
    assert pv["matrix"][ni][ai] == Decimal("11500"), pv["matrix"][ni][ai]
    assert pv["grand_total"] == Decimal("13250"), pv["grand_total"]
    assert pv["skipped"] == 1  # the "junk" amount
    # count aggfunc (no value)
    pvc = pivot(header, rows, "Region", "Customer")
    assert pvc["aggfunc"] == "count" and pvc["measure"] == "rows"
    # North × Alpha count = 3
    assert pvc["matrix"][pvc["row_keys"].index("North")][pvc["col_keys"].index("Alpha")] == Decimal(3)

    # distribution — skewness + kurtosis
    # Symmetric: [1,2,3,4,5] → skewness ~0, kurtosis ~0 (excess)
    dist = distribution(["1", "2", "3", "4", "5"])
    assert dist["n"] == 5 and dist["skewness"] is not None
    assert abs(dist["skewness"]) < 0.1, dist["skewness"]
    assert dist["classification"] == "symmetric", dist
    # Right-skewed: [1,1,1,1,100] → heavy positive skew, heavy-tailed
    dist2 = distribution(["1", "1", "1", "1", "100"])
    assert dist2["skewness"] > 1.0, dist2
    assert dist2["classification"] in ("highly skewed", "heavy-tailed"), dist2
    # Insufficient data
    dist3 = distribution(["1", "2"])
    assert dist3["skewness"] is None and "insufficient" in dist3["classification"]
    # Constant
    dist4 = distribution(["5", "5", "5", "5"])
    assert dist4["classification"] == "constant (no spread)"

    # trend — linear regression slope + R² + direction
    # Rising: y = 2x → slope=2, R²=1
    rising = [("W1", Decimal("2")), ("W2", Decimal("4")), ("W3", Decimal("6")), ("W4", Decimal("8"))]
    tr = trend(rising)
    assert tr["n"] == 4 and tr["slope"] == 2.0, tr
    assert tr["r_squared"] == 1.0, tr
    assert tr["classification"] == "rising", tr
    # Falling
    falling = [("W1", Decimal("10")), ("W2", Decimal("8")), ("W3", Decimal("6")), ("W4", Decimal("4"))]
    tr2 = trend(falling)
    assert tr2["slope"] == -2.0 and tr2["classification"] == "falling", tr2
    # Flat (constant)
    flat = [("W1", Decimal("5")), ("W2", Decimal("5")), ("W3", Decimal("5"))]
    tr3 = trend(flat)
    assert tr3["classification"] == "flat", tr3
    # Insufficient
    tr4 = trend([("W1", Decimal("1")), ("W2", Decimal("2"))])
    assert tr4["slope"] is None and "insufficient" in tr4["classification"]
    # Noisy / weak (low R²)
    noisy = [("W1", Decimal("1")), ("W2", Decimal("5")), ("W3", Decimal("2")), ("W4", Decimal("4"))]
    tr5 = trend(noisy)
    assert tr5["r_squared"] < 0.5, tr5  # should be weak or flat

    # percentile — arbitrary quantiles with linear interpolation
    vals = ["10", "20", "30", "40", "50", "60", "70", "80", "90", "100"]
    p50 = percentile(vals, 0.5)
    assert p50["value"] == Decimal("55"), p50  # interp between 50 and 60
    p90 = percentile(vals, 0.9)
    assert p90["value"] == Decimal("91"), p90  # interp between 90 and 100
    p0 = percentile(vals, 0.0)
    assert p0["value"] == Decimal("10"), p0
    p100 = percentile(vals, 1.0)
    assert p100["value"] == Decimal("100"), p100
    # List mode
    multi = percentile(vals, [0.25, 0.75])
    assert multi[0.25] == Decimal("32.5") and multi[0.75] == Decimal("77.5"), multi
    # Empty
    pe = percentile([], 0.5)
    assert pe["value"] is None and pe["n"] == 0

    # cohort — retention matrix
    cohort_header = ["Customer", "Date", "Amount"]
    cohort_rows = [
        ["A", "01/01/2026", "100"],
        ["A", "01/02/2026", "50"],   # A active in month 2
        ["A", "01/03/2026", "30"],   # A active in month 3
        ["B", "01/01/2026", "200"],
        ["B", "01/03/2026", "40"],   # B active in month 3 (skipped month 2)
        ["C", "01/02/2026", "150"],  # C starts in month 2
        ["C", "01/03/2026", "60"],
    ]
    ch = cohort(cohort_header, cohort_rows, "Customer", "Date", grain="month")
    assert ch["cohorts"] == ["2026-01", "2026-02"], ch["cohorts"]
    assert ch["cohort_sizes"] == [2, 1], ch["cohort_sizes"]  # Jan: A+B, Feb: C
    # Jan cohort: offset 0 = 2 entities, offset 1 = 1 (A only), offset 2 = 2 (A+B)
    assert ch["matrix"][0][0] == Decimal(2), ch["matrix"][0]  # Jan, month 0
    assert ch["matrix"][0][1] == Decimal(1), ch["matrix"][0]  # Jan, month 1 (A)
    assert ch["matrix"][0][2] == Decimal(2), ch["matrix"][0]  # Jan, month 2 (A+B)
    # Retention: 2/2 = 1.0, 1/2 = 0.5, 2/2 = 1.0
    assert ch["retention"][0][0] == Decimal(1), ch["retention"][0]
    assert ch["retention"][0][1] == Decimal("0.5"), ch["retention"][0]
    # Feb cohort: 1 entity, offset 0 = 1, offset 1 = 1
    assert ch["matrix"][1][0] == Decimal(1), ch["matrix"][1]
    assert ch["retention"][1][0] == Decimal(1), ch["retention"][1]
    # With value
    chv = cohort(cohort_header, cohort_rows, "Customer", "Date", value="Amount", grain="month")
    assert chv["measure"] == "Amount"
    # Jan cohort, offset 0: A(100) + B(200) = 300
    assert chv["matrix"][0][0] == Decimal("300"), chv["matrix"][0]

    # correlation_matrix — pairwise Pearson
    corr_header = ["Revenue", "Headcount", "Spend"]
    corr_rows = [
        ["100", "10", "30"],
        ["150", "12", "40"],
        ["200", "15", "50"],
        ["250", "18", "60"],
        ["300", "20", "70"],
    ]
    cm = correlation_matrix(corr_header, corr_rows, ["Revenue", "Headcount", "Spend"])
    assert cm["n_cols"] == 3
    assert cm["matrix"][0][0] == 1.0  # diagonal
    assert cm["matrix"][0][1] is not None and cm["matrix"][0][1] > 0.95  # strongly correlated
    assert cm["matrix"][1][0] == cm["matrix"][0][1]  # symmetric
    # Too few rows → None
    cm2 = correlation_matrix(["A", "B"], [["1", "2"], ["3", "4"]], ["A", "B"])
    assert cm2["matrix"][0][1] is None  # only 2 rows, need ≥3

    # rolling — moving average / sum / median
    series = [("W1", Decimal("10")), ("W2", Decimal("20")), ("W3", Decimal("30")),
              ("W4", Decimal("40")), ("W5", Decimal("50"))]
    r3 = rolling(series, 3, func="mean")
    assert r3[0] == ("W1", None) and r3[1] == ("W2", None)  # not enough history
    assert r3[2] == ("W3", Decimal("20")), r3[2]  # (10+20+30)/3
    assert r3[3] == ("W4", Decimal("30")), r3[3]  # (20+30+40)/3
    assert r3[4] == ("W5", Decimal("40")), r3[4]  # (30+40+50)/3
    # Sum
    rs = rolling(series, 2, func="sum")
    assert rs[1] == ("W2", Decimal("30")), rs[1]  # 10+20
    # Median
    rm = rolling(series, 3, func="median")
    assert rm[2] == ("W3", Decimal("20")), rm[2]  # median of [10,20,30]
    # Window=1 (no smoothing)
    r1 = rolling(series, 1)
    assert r1[0] == ("W1", Decimal("10")), r1[0]

    # gini — inequality coefficient
    # Perfectly equal: [10,10,10,10] → Gini = 0
    g_equal = gini(["10", "10", "10", "10"])
    assert g_equal["gini"] == 0.0, g_equal
    assert g_equal["classification"] == "relatively equal", g_equal
    # Highly unequal: [0, 0, 0, 1000] → Gini near 0.75
    g_unequal = gini(["0", "0", "0", "1000"])
    assert g_unequal["gini"] > 0.7, g_unequal
    assert g_unequal["classification"] == "extreme inequality", g_unequal
    # Negatives → unreliable
    g_neg = gini(["100", "-50", "60"])
    assert g_neg["gini"] is None and "negatives" in g_neg["classification"]
    # Insufficient
    g_one = gini(["100"])
    assert g_one["gini"] is None and "insufficient" in g_one["classification"]

    # seasonality — month-of-year averages
    seas_header = ["Date", "Revenue"]
    seas_rows = [
        ["15/01/2025", "100"],   # Jan 2025
        ["15/01/2026", "120"],   # Jan 2026
        ["15/07/2025", "200"],   # Jul 2025
        ["15/07/2026", "220"],   # Jul 2026
        ["15/10/2025", "300"],   # Oct 2025
    ]
    sm = seasonality(seas_header, seas_rows, "Date", value="Revenue", grain="month")
    assert sm["grain"] == "month" and len(sm["seasons"]) == 12
    jan = [s for s in sm["seasons"] if s["season"] == 1][0]
    jul = [s for s in sm["seasons"] if s["season"] == 7][0]
    oct_s = [s for s in sm["seasons"] if s["season"] == 10][0]
    assert jan["count"] == 2 and jan["total"] == Decimal("220"), jan
    assert jan["average"] == Decimal("110"), jan  # 220/2
    assert jul["total"] == Decimal("420"), jul
    assert oct_s["count"] == 1 and oct_s["total"] == Decimal("300"), oct_s
    # Overall average: mean of seasons WITH data (Jan, Jul, Oct = 3 seasons)
    assert sm["overall_average"] == Decimal("940") / Decimal(3), sm["overall_average"]
    assert sm["n_seasons_with_data"] == 3
    # Quarter grain
    sq = seasonality(seas_header, seas_rows, "Date", value="Revenue", grain="quarter")
    assert sq["grain"] == "quarter" and len(sq["seasons"]) == 4
    q1 = [s for s in sq["seasons"] if s["season"] == 1][0]
    assert q1["total"] == Decimal("220"), q1  # Jan only
    # Count measure (no value)
    sc = seasonality(seas_header, seas_rows, "Date", grain="month")
    assert sc["measure"] == "rows"
    assert [s for s in sc["seasons"] if s["season"] == 1][0]["count"] == 2

    print("analyse.py self-test OK")


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        _self_test()
    else:
        print(__doc__)
