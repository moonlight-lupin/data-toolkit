"""Shared data-cleanup engine — deterministic primitives used by `data-tidy` and
`data-extract`. Lives at the toolkit-root `scripts/` (with `ingest.py`/`envcheck.py`);
skills import it by adding `../../scripts` to sys.path (run from the skill directory).

Design: INTENT (asked upfront, in the skill) -> INGEST (see ingest.py) -> PROFILE ->
PROPOSE a recipe -> CONFIRM -> APPLY (here, deterministic + logged) -> REPORT + save recipe.

The transforms here are **deterministic and logged** — the model's job is to read the
profile and propose the recipe, not to rewrite cells. Conversion failures are KEPT RAW and
FLAGGED for human review, never silently nulled. House output: dates DD MMM YYYY; currency
amount + code.

    from dataclean import profile_table, apply_recipe, render_report, write_xlsx
    prof = profile_table(header, rows)                       # understand the mess
    clean_h, clean_rows, log = apply_recipe(raw_rows, recipe)  # source -> declared target
    write_xlsx(clean_h, clean_rows, "clean.xlsx"); print(render_report(log))

DATA HANDLING: runs fully local; your data never leaves the machine. If the data is sensitive
or confidential business/financial data, keep it on your synced or shared file store — never
send it, or OCR of it, to an external tool. See ../DATA-HANDLING.md.
"""

from __future__ import annotations

import re
import sys
import datetime as dt
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except (AttributeError, ValueError):
    pass

from openpyxl import Workbook, load_workbook  # noqa: F401 (load_workbook used by ingest)

DATE_OUT = "%d %b %Y"  # house format: 13 Jun 2026

CURRENCY_SIGNS = {"£": "GBP", "$": "USD", "¥": "JPY", "€": "EUR",
                  "S$": "SGD", "US$": "USD", "SGD": "SGD", "GBP": "GBP",
                  "JPY": "JPY", "USD": "USD", "EUR": "EUR"}

_DATE_FORMATS = ["%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y", "%d %b %Y", "%d %B %Y",
                 "%b %d, %Y", "%B %d, %Y", "%d/%m/%y", "%Y/%m/%d"]
_AMBIGUOUS = re.compile(r"^\s*(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{2,4})\s*$")


# --------------------------------------------------------------------------- #
# Parsers — each returns (value_or_None, note). note != "" means flag it.
# --------------------------------------------------------------------------- #
def _s(v) -> str:
    return "" if v is None else str(v).strip()


def parse_number(v):
    """'£1,234.50' '(500)' '1.2m' '15%' -> float. Returns (float|None, note)."""
    s = _s(v)
    if s == "":
        return None, "empty"
    neg = s.startswith("(") and s.endswith(")")
    s2 = s.strip("()")
    mult = 1.0
    low = s2.lower()
    if low.endswith("m"):
        mult, s2 = 1_000_000.0, s2[:-1]
    elif low.endswith("k"):
        mult, s2 = 1_000.0, s2[:-1]
    pct = s2.rstrip().endswith("%")
    s2 = re.sub(r"[^\d.\-]", "", s2.replace(",", ""))
    if s2 in ("", "-", ".", "-."):
        return None, f"not a number: {s!r}"
    try:
        n = float(s2) * mult
    except ValueError:
        return None, f"not a number: {s!r}"
    if neg:
        n = -abs(n)
    if pct:
        n /= 100.0
    return n, ""


def parse_currency(v):
    """'£1,000,000' 'S$ 2.5m' -> (amount, code). Returns ((amount, code)|None, note)."""
    s = _s(v)
    if s == "":
        return None, "empty"
    code = None
    for sign in ("S$", "US$", "SGD", "GBP", "JPY", "USD", "EUR", "£", "$", "¥", "€"):
        if sign in s:
            code = CURRENCY_SIGNS[sign]
            break
    amt, note = parse_number(s)
    if amt is None:
        return None, note
    return (amt, code), ("" if code else "no currency symbol — code unknown")


def _excel_serial(s):
    if re.fullmatch(r"\d{5}(\.\d+)?", s):
        try:
            base = dt.date(1899, 12, 30)
            return base + dt.timedelta(days=int(float(s)))
        except (ValueError, OverflowError):
            return None
    return None


def parse_date(v, dayfirst=True):
    """Many formats + Excel serial + datetime -> date. Returns (date|None, note).
    Ambiguous dd/mm vs mm/dd is resolved by `dayfirst` (UK/SG default) and flagged."""
    if isinstance(v, (dt.datetime, dt.date)):
        return (v.date() if isinstance(v, dt.datetime) else v), ""
    s = _s(v)
    if s == "":
        return None, "empty"
    ser = _excel_serial(s)
    if ser:
        return ser, "parsed from Excel serial"
    m = _AMBIGUOUS.match(s)
    note = ""
    if m:
        a, b, _ = (int(x) for x in m.groups())
        if a <= 12 and b <= 12 and a != b:
            note = f"ambiguous date {s!r} — read as {'day/month' if dayfirst else 'month/day'}"
    fmts = _DATE_FORMATS if dayfirst else (["%m/%d/%Y", "%m-%d-%Y", "%m/%d/%y"] + _DATE_FORMATS)
    for fmt in fmts:
        try:
            return dt.datetime.strptime(s, fmt).date(), note
        except ValueError:
            continue
    return None, f"unrecognised date: {s!r}"


# --------------------------------------------------------------------------- #
# Structure
# --------------------------------------------------------------------------- #
def detect_header(rows, scan=15):
    """Best guess at the real header row index: the row (in the first `scan`) with the most
    non-empty, mostly-textual, distinct cells. Junk/title/banner rows score low."""
    best, best_score = 0, -1.0
    for i, row in enumerate(rows[:scan]):
        cells = [_s(c) for c in row]
        filled = [c for c in cells if c]
        if len(filled) < 2:
            continue
        texty = sum(1 for c in filled if not parse_number(c)[0] and not parse_date(c)[0])
        score = len(filled) + texty + 0.5 * len(set(filled)) - 0.3 * (len(cells) - len(filled))
        if score > best_score:
            best, best_score = i, score
    return best


def _is_blank(row):
    return all(_s(c) == "" for c in row)


def _looks_total(row):
    return any(_s(c).lower() in ("total", "totals", "subtotal", "grand total") for c in row)


# --------------------------------------------------------------------------- #
# Profile (read-only) — inspect ONLY against what the target needs is the skill's job;
# this gives the full picture the recipe is proposed from.
# --------------------------------------------------------------------------- #
def _infer_type(values):
    nonempty = [v for v in values if _s(v) != ""]
    if not nonempty:
        return "empty"
    def frac(fn):
        return sum(1 for v in nonempty if fn(_s(v))) / len(nonempty)
    if frac(lambda s: parse_date(s)[0] is not None) > 0.8:
        return "date"
    if frac(lambda s: parse_currency(s)[0] is not None and any(k in s for k in CURRENCY_SIGNS)) > 0.5:
        return "currency"
    if frac(lambda s: parse_number(s)[0] is not None) > 0.8:
        return "number"
    if frac(lambda s: s.lower() in ("yes", "no", "true", "false", "y", "n")) > 0.8:
        return "bool"
    return "text"


def profile_table(header, rows):
    cols = []
    n = len(rows)
    for j, name in enumerate(header):
        vals = [r[j] if j < len(r) else "" for r in rows]
        nonempty = [v for v in vals if _s(v) != ""]
        seen, samples = set(), []
        for v in nonempty:
            sv = _s(v)
            if sv not in seen:
                seen.add(sv)
                if len(samples) < 4:
                    samples.append(sv)
        cols.append({"name": _s(name) or f"(col {j+1})", "type": _infer_type(vals),
                     "missing_pct": round(100 * (n - len(nonempty)) / n, 1) if n else 0.0,
                     "distinct": len(seen), "samples": samples})
    keyed = ["|".join(_s(c) for c in r) for r in rows]
    dups = len(keyed) - len(set(keyed))
    return {"rows": n, "columns": cols, "duplicate_rows": dups}


def render_profile(prof):
    out = [f"## Profile — {prof['rows']} rows, {len(prof['columns'])} columns",
           f"_duplicate rows: {prof['duplicate_rows']}_", "",
           "| Column | Type | Missing | Distinct | Samples |", "|---|---|---|---|---|"]
    for c in prof["columns"]:
        out.append(f"| {c['name']} | {c['type']} | {c['missing_pct']}% | {c['distinct']} | "
                   f"{'; '.join(c['samples'])} |")
    return "\n".join(out)


# --------------------------------------------------------------------------- #
# Apply a recipe (deterministic) -> (header, rows, log)
# --------------------------------------------------------------------------- #
def _col_index(header, name):
    norm = [_s(h).lower() for h in header]
    n = _s(name).lower()
    if n in norm:
        return norm.index(n)
    for i, h in enumerate(norm):  # loose contains-match
        if n and (n in h or h in n):
            return i
    return None


def apply_recipe(raw_rows, recipe, masters=None):
    """recipe = {header_row?, drop?, columns:[{source,target,type,trim,currency,format}],
    dedup_keys?, validate?:[{col,required?,regex?,in_master?,unique?}]}. masters = {name:set}."""
    masters = masters or {}
    log = {"header": None, "dropped": {}, "transforms": [], "flagged": [],
           "duplicates": [], "validation": [], "rows_in": len(raw_rows), "rows_out": 0}

    hr = recipe.get("header_row")
    if hr is None:
        hr = detect_header(raw_rows)
    log["header"] = hr
    header_src = [_s(c) for c in raw_rows[hr]]
    body = raw_rows[hr + 1:]

    drop = recipe.get("drop", {"blank": True, "totals": True})
    kept = []
    nb = nt = 0
    for r in body:
        if drop.get("blank", True) and _is_blank(r):
            nb += 1
            continue
        if drop.get("totals", True) and _looks_total(r):
            nt += 1
            continue
        kept.append(r)
    log["dropped"] = {"blank": nb, "totals": nt}

    cols = recipe.get("columns")
    if not cols:  # passthrough: keep all source columns as text
        cols = [{"source": h, "target": h, "type": "text"} for h in header_src]
    out_header = [c["target"] for c in cols]
    idx = [(_col_index(header_src, c["source"]), c) for c in cols]

    out_rows = []
    conv = {c["target"]: {"ok": 0, "flagged": 0} for c in cols}
    for ri, r in enumerate(kept):
        out = []
        for j, spec in idx:
            raw = "" if j is None or j >= len(r) else r[j]
            val, note, kept_raw = _convert(raw, spec)  # kept_raw=True only on hard failure
            if _s(raw) != "":
                if not kept_raw:
                    conv[spec["target"]]["ok"] += 1     # value converted (may also warn)
                if note:
                    conv[spec["target"]]["flagged"] += 1
                    log["flagged"].append({"row": ri + 1, "column": spec["target"],
                                           "value": _s(raw), "reason": note})
            out.append(val)
        out_rows.append(out)
    log["transforms"] = [{"column": t, "converted": conv[t]["ok"], "flagged": conv[t]["flagged"]}
                         for t in conv]

    keys = recipe.get("dedup_keys")
    if keys:
        out_rows, dlog = _dedup(out_header, out_rows, keys)
        log["duplicates"] = dlog

    for rule in recipe.get("validate", []):
        log["validation"].extend(_validate_rule(out_header, out_rows, rule, masters))

    log["rows_out"] = len(out_rows)
    return out_header, out_rows, log


def _convert(raw, spec):
    """-> (value, note, kept_raw). kept_raw=True means a HARD failure (raw kept for review);
    a note with kept_raw=False is a soft WARNING (value converted, but flag it too)."""
    if spec.get("trim", True) and isinstance(raw, str):
        raw = raw.strip()
    t = spec.get("type", "text")
    if _s(raw) == "":
        return "", "", False
    if t == "text":
        return re.sub(r"\s+", " ", _s(raw)), "", False
    if t == "number":
        n, note = parse_number(raw)
        return (n, "", False) if n is not None else (_s(raw), note, True)
    if t == "currency":
        res, note = parse_currency(raw)
        if res is None:
            return _s(raw), note, True
        amt, code = res
        want = spec.get("currency")
        if want and code and code != want:
            note = (note + f"; currency {code} != expected {want}").strip("; ")
        return amt, note, False
    if t == "date":
        d, note = parse_date(raw, dayfirst=spec.get("dayfirst", True))
        if d is None:
            return _s(raw), note, True
        return d.strftime(spec.get("format", DATE_OUT)), note, False
    if t == "bool":
        return (_s(raw).lower() in ("yes", "true", "y", "1")), "", False
    return _s(raw), "", False


def _norm_key(v):
    return re.sub(r"[^a-z0-9]", "", _s(v).lower())


def _dedup(header, rows, keys):
    ki = [_col_index(header, k) for k in keys]
    seen, out, log = {}, [], []
    for ri, r in enumerate(rows):
        sig = tuple(_s(r[i]) if i is not None and i < len(r) else "" for i in ki)
        fuzzy = tuple(_norm_key(s) for s in sig)
        if sig in seen:
            log.append({"row": ri + 1, "kind": "exact", "key": " | ".join(sig),
                        "kept_row": seen[sig]})
            continue
        # flag fuzzy near-dup but KEEP it (never auto-merge)
        for s2, kr in seen.items():
            if tuple(_norm_key(x) for x in s2) == fuzzy and s2 != sig:
                log.append({"row": ri + 1, "kind": "possible (review)",
                            "key": " | ".join(sig), "kept_row": kr})
                break
        seen[sig] = ri + 1
        out.append(r)
    return out, log


def _validate_rule(header, rows, rule, masters):
    j = _col_index(header, rule["col"])
    if j is None:
        return [{"col": rule["col"], "issue": "column not found"}]
    fails = []
    seen = set()
    rgx = re.compile(rule["regex"]) if rule.get("regex") else None
    master = masters.get(rule.get("in_master"))
    for ri, r in enumerate(rows):
        v = _s(r[j]) if j < len(r) else ""
        if rule.get("required") and v == "":
            fails.append({"row": ri + 1, "col": rule["col"], "issue": "required, empty"})
        if v and rgx and not rgx.search(v):
            fails.append({"row": ri + 1, "col": rule["col"], "issue": f"fails regex {rule['regex']}"})
        if v and master is not None and _norm_key(v) not in {_norm_key(m) for m in master}:
            fails.append({"row": ri + 1, "col": rule["col"], "issue": "not in master list"})
        if rule.get("unique"):
            if v in seen and v:
                fails.append({"row": ri + 1, "col": rule["col"], "issue": "duplicate (not unique)"})
            seen.add(v)
    return fails


# --------------------------------------------------------------------------- #
# Output + report
# --------------------------------------------------------------------------- #
def write_xlsx(header, rows, out_path, sheet="Clean"):
    wb = Workbook()
    ws = wb.active
    ws.title = sheet
    ws.append([_s(h) for h in header])
    for r in rows:
        ws.append([(_s(c) if isinstance(c, str) else c) for c in r])
    wb.save(out_path)
    return out_path


def render_report(log):
    out = ["# Data-tidy change report",
           f"- Rows in: **{log['rows_in']}** → out: **{log['rows_out']}**",
           f"- Header row used: index {log['header']}",
           f"- Dropped: {log['dropped'].get('blank', 0)} blank, "
           f"{log['dropped'].get('totals', 0)} total/subtotal"]
    if log["duplicates"]:
        ex = sum(1 for d in log["duplicates"] if d["kind"] == "exact")
        pos = len(log["duplicates"]) - ex
        out.append(f"- Duplicates: {ex} exact removed, {pos} possible (kept, flagged for review)")
    out.append("\n## Column transforms")
    out.append("| Column | Converted | Flagged |\n|---|---|---|")
    for t in log["transforms"]:
        out.append(f"| {t['column']} | {t['converted']} | {t['flagged']} |")
    if log["flagged"]:
        out.append(f"\n## ⚑ Cells flagged for review ({len(log['flagged'])}) — "
                   "hard failures kept raw; warnings converted, please verify")
        out.append("| Row | Column | Value | Reason |\n|---|---|---|---|")
        for f in log["flagged"][:50]:
            out.append(f"| {f['row']} | {f['column']} | {f['value']} | {f['reason']} |")
        if len(log["flagged"]) > 50:
            out.append(f"_…and {len(log['flagged']) - 50} more_")
    if log["validation"]:
        out.append(f"\n## ⚑ Validation failures ({len(log['validation'])})")
        out.append("| Row | Column | Issue |\n|---|---|---|")
        for v in log["validation"][:50]:
            out.append(f"| {v.get('row', '-')} | {v.get('col', '-')} | {v['issue']} |")
    return "\n".join(out)


# --------------------------------------------------------------------------- #
# Reuse: emit a runner (.py) + card (.md) for a recurring doc type, so the next
# agent re-runs the same extraction/cleanup with ~no reasoning tokens. The card
# is read FIRST (verify the source still matches) before the .py is executed.
# --------------------------------------------------------------------------- #
_RUNNER_TEMPLATE = '''#!/usr/bin/env python
"""data-@@KIND@@ reusable runner — @@TITLE@@
Doc type: @@DOCTYPE@@.  Generated @@DATE@@ by data-@@KIND@@.

REUSE — do NOT blind-run on new files. FIRST read the companion card "@@CARD@@", inspect the
source, and confirm it still matches the baked spec. This runner self-checks and WARNS on
mismatch (missing fields / new columns), but a human/agent should verify first. If the
layout changed (e.g. a column was added), update SPEC or regenerate via data-@@KIND@@.

Usage:  python @@PYNAME@@ <doc1> [doc2 ...] [-o out.xlsx]
"""
import sys
import pathlib

MODE = "@@KIND@@"
SPEC = @@SPEC_REPR@@
EXPECTED = @@EXPECTED_REPR@@

# The engine (dataclean.py / ingest.py / extract.py) is deployed ALONGSIDE this runner in the
# working folder, so this folder is self-contained — no dependency on the plugin install.
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
try:
    import dataclean   # noqa: E402
    import ingest      # noqa: E402
    import extract     # noqa: E402
except ModuleNotFoundError as e:
    raise SystemExit("Engine file missing next to this runner (%s). This folder should also "
                     "contain dataclean.py, ingest.py and extract.py — regenerate the runner "
                     "via data-extract / data-tidy." % e.name)


def _args(argv):
    out, paths, it = "extracted.xlsx", [], iter(argv)
    for a in it:
        if a == "-o":
            out = next(it)
        else:
            paths.append(a)
    if not paths:
        raise SystemExit("Usage: python @@PYNAME@@ <doc...> [-o out.xlsx]")
    return paths, out


def main(argv):
    paths, out = _args(argv)
    if MODE == "extract":
        records, flags_all = [], []
        for p in paths:
            text, _ = ingest.read_text(p)
            low = text.lower()
            missing = [f["name"] for f in SPEC
                       if not any(l.lower() in low for l in f.get("labels", [f["name"]]))]
            if missing:
                print("[WARN] %s: expected fields not found -> %s; source may have changed "
                      "- verify before trusting output." % (p, missing))
            rec, flags = extract.extract_fields(p, SPEC)
            records.append(rec)
            flags_all.append(flags)
        header, rows = extract.fields_to_table(records, [f["name"] for f in SPEC])
        dataclean.write_xlsx(header, rows, out)
        print(extract.render_fields_report(records, flags_all))
    else:
        rows, note = ingest.read_any(paths[0])
        print("ingest:", note)
        hi = SPEC.get("header_row")
        if hi is None:
            hi = dataclean.detect_header(rows)
        srccols = [str(c).strip() for c in rows[hi]]
        exp = EXPECTED.get("columns", [])
        miss = [c for c in exp if c not in srccols]
        new = [c for c in srccols if c and c not in exp]
        if miss:
            print("[WARN] %s: expected columns missing -> %s; verify before trusting output."
                  % (paths[0], miss))
        if new:
            print("[WARN] %s: NEW columns not in the recipe -> %s; a column may have been "
                  "added - verify / regenerate." % (paths[0], new))
        header, clean, log = dataclean.apply_recipe(rows, SPEC)
        dataclean.write_xlsx(header, clean, out)
        print(dataclean.render_report(log))
    print("\\nWrote %s" % out)


if __name__ == "__main__":
    main(sys.argv[1:])
'''


def _build_card(mode, doctype, title, date, pyname, spec):
    L = [f"# data-{mode} runner — {title}", "",
         f"**Doc type:** {doctype}  ", f"**Generated:** {date} (by data-{mode})  ",
         f"**Runner:** `{pyname}`", "",
         "## Before you run it — DO THIS FIRST",
         "1. **Read this card.**",
         "2. **Inspect the current source file(s)** (open / preview them).",
         "3. **Compare to *Expected source* below** — layouts drift (a column/field added, "
         "renamed or moved).",
         f"4. If it **matches**, run the runner (cheap, deterministic). If it **changed**, "
         f"update the baked spec or **regenerate** via data-{mode} — do NOT blind-run a "
         "stale spec.", "", "## Expected source (verify this)"]
    if mode == "extract":
        L += ["Fields pulled (output ← labels searched):", "",
              "| Output field | Type | Source labels |", "|---|---|---|"]
        L += [f"| {f['name']} | {f.get('type', 'text')} | {', '.join(f.get('labels', [f['name']]))} |"
              for f in spec]
        outcols = [f["name"] for f in spec]
    else:
        L += [f"Source columns the recipe maps (header row {spec.get('header_row', 'auto')}):", "",
              "| Source column | → Output | Type |", "|---|---|---|"]
        L += [f"| {c.get('source')} | {c.get('target')} | {c.get('type', 'text')} |"
              for c in spec.get("columns", [])]
        outcols = [c.get("target") for c in spec.get("columns", [])]
    L += ["", "## Output",
          f"A clean `.xlsx` with columns: {', '.join(str(c) for c in outcols)}; plus a flag/change report.",
          "", "## Usage", "```", f"python {pyname} <doc1> [doc2 ...] [-o out.xlsx]", "```",
          "The runner self-checks and warns on mismatch (missing fields / new columns), but verify first.",
          "", "## Self-contained folder",
          "`dataclean.py`, `ingest.py` and `extract.py` are bundled in this folder alongside the "
          "runner — it runs standalone, with nothing else installed. Keep them together (e.g. on "
          "your synced or shared file store). Regenerating refreshes these engine copies.",
          "", "## Data handling",
          "Runs fully local; your data (and any OCR) never leaves the machine. See the "
          "toolkit's `DATA-HANDLING.md`.",
          "", "## Maintenance", "Regenerate if the source layout changes materially."]
    return "\n".join(L) + "\n"


ENGINE_FILES = ("dataclean.py", "ingest.py", "extract.py")


def emit_runner(out_dir, doctype, mode, spec, title=None, date=None):
    """Write a SELF-CONTAINED reuse bundle for a recurring doc type into out_dir (the user's
    working folder): the runner (.py), the card (.md), AND a copy of the engine
    (dataclean/ingest/extract) so the runner imports from its own folder — no dependency on
    the plugin install. mode 'extract' (spec = field dicts) or 'tidy' (spec = recipe dict)."""
    import shutil
    assert mode in ("extract", "tidy"), mode
    out = Path(out_dir).resolve()
    out.mkdir(parents=True, exist_ok=True)
    title = title or doctype
    date = date or dt.date.today().strftime(DATE_OUT)
    safe = re.sub(r"[^A-Za-z0-9._-]+", "-", doctype).strip("-") or "doc"
    pyname, cardname = f"{mode}_{safe}.py", f"{mode}_{safe}.md"
    if mode == "extract":
        expected = {"fields": [{"name": f["name"], "labels": f.get("labels", [f["name"]])}
                               for f in spec]}
    else:
        expected = {"columns": [c.get("source") for c in spec.get("columns", [])],
                    "header_row": spec.get("header_row")}
    # deploy the engine into the working folder (skip if out_dir IS the engine source dir)
    engine_src = Path(__file__).resolve().parent
    deployed = []
    if out != engine_src:
        for f in ENGINE_FILES:
            src = engine_src / f
            if src.exists():
                shutil.copy2(src, out / f)
                deployed.append(f)
    py = (_RUNNER_TEMPLATE
          .replace("@@KIND@@", mode).replace("@@TITLE@@", title)
          .replace("@@DOCTYPE@@", doctype).replace("@@DATE@@", date)
          .replace("@@PYNAME@@", pyname).replace("@@CARD@@", cardname)
          .replace("@@SPEC_REPR@@", repr(spec)).replace("@@EXPECTED_REPR@@", repr(expected)))
    (out / pyname).write_text(py, encoding="utf-8")
    (out / cardname).write_text(_build_card(mode, doctype, title, date, pyname, spec),
                                encoding="utf-8")
    return {"runner": str(out / pyname), "card": str(out / cardname), "engine": deployed}


if __name__ == "__main__":
    raw = [
        ["ABC Capital — investor commitments", "", ""],
        ["CONFIDENTIAL", "", ""],
        ["Inv. Name", "Commit", "Close"],
        ["Acme Pension  ", "£1,000,000", "12/06/2026"],
        ["Beta Family Office", "S$ 2.5m", "2026-06-13"],
        ["acme pension", "£1,000,000", "5 Jun 2026"],          # fuzzy dup of Acme
        ["Gamma Trust", "not provided", "soon"],               # two bad cells -> flagged
        ["", "", ""],                                          # blank
        ["TOTAL", "£3,500,000", ""],                           # totals row
    ]
    recipe = {
        "columns": [
            {"source": "Inv. Name", "target": "Investor", "type": "text"},
            {"source": "Commit", "target": "Commitment", "type": "currency", "currency": "GBP"},
            {"source": "Close", "target": "Close date", "type": "date"},
        ],
        "dedup_keys": ["Investor"],
        "validate": [{"col": "Investor", "required": True}],
    }
    h, rows, log = apply_recipe(raw, recipe)
    print(render_profile(profile_table(["Inv. Name", "Commit", "Close"], raw[3:])))
    print("\n" + render_report(log))
    out = Path(__file__).resolve().parent / "_selftest_clean.xlsx"
    write_xlsx(h, rows, out)
    print("\n[self-test] clean rows:", rows)
    out.unlink()
