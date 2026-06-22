"""Regression suite for the data-toolkit's finance-grade behaviours.

Locks in exactly the guarantees that make the engine safe for finance work — the things that
would silently corrupt a reconciliation or a clean table if they regressed:

  - amounts are exact Decimal (no binary-float drift at the tolerance edge)
  - 100 USD never reconciles against 100 SGD (currencies are compared)
  - strict-currency mode refuses to match an unknown currency
  - a bare "$" is ambiguous, not assumed USD
  - amount/date pairs outside the window are flagged ambiguous, not matched
  - multi-tab workbooks require an explicit sheet (no silent 'active'-sheet guess)
  - form extraction handles next-line and dotted-leader layouts
  - a currency column can be split out via code_target
  - categorical value-map clustering proposes the right canonical
  - PDF tables: best-engine scoring (+ a guarded end-to-end smoke test)

Runs two ways:
    python tests/test_engine.py        # standalone, no pytest needed
    pytest tests/                       # if pytest is installed
"""

from __future__ import annotations

import sys
import tempfile
from decimal import Decimal
from pathlib import Path

# --- make the shared engine + skill scripts importable, standalone or under pytest ---------
_ROOT = Path(__file__).resolve().parents[1]
for _p in (_ROOT / "scripts",
           _ROOT / "skills" / "data-reconcile" / "scripts",
           _ROOT / "skills" / "data-visualise" / "scripts"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import dataclean        # noqa: E402
import extract          # noqa: E402
import ingest           # noqa: E402
import reconcile        # noqa: E402
import viz              # noqa: E402


# --------------------------------------------------------------------------- #
# 1. Decimal tolerance edge
# --------------------------------------------------------------------------- #
def test_decimal_amounts_are_exact():
    n1, _ = dataclean.parse_number("0.1")
    n2, _ = dataclean.parse_number("0.2")
    assert isinstance(n1, Decimal)
    assert n1 + n2 == Decimal("0.3")                       # float would give 0.30000000000000004
    assert reconcile.to_amount("0.1") + reconcile.to_amount("0.2") == reconcile.to_amount("0.3")


def test_reconcile_tolerance_edge_is_exact():
    # a 0.10 spread with default tol 0.01 must be a value difference, not a fuzzy match,
    # and the reported diff must be the exact Decimal, not float dust.
    A = [{"k": "1", "amount": "1000.10"}]
    B = [{"k": "1", "amount": "1000.00"}]
    res = reconcile.match(A, B, key="k", amount="amount")
    assert not res["matched"] and len(res["value_diffs"]) == 1
    assert res["value_diffs"][0]["diff"] == Decimal("0.10")


# --------------------------------------------------------------------------- #
# 2. 100 USD vs 100 SGD must NOT reconcile (currency compared)
# --------------------------------------------------------------------------- #
def test_usd_does_not_match_sgd_on_key():
    A = [{"ref": "R1", "amount": "100.00", "ccy": "USD"}]
    B = [{"ref": "R1", "amount": "100.00", "ccy": "SGD"}]
    res = reconcile.match(A, B, key="ref", amount="amount", currency="ccy")
    assert not res["matched"] and len(res["currency_diffs"]) == 1
    assert any(e["category"] == "currency_mismatch" for e in reconcile.triage(res))


def test_usd_does_not_match_sgd_via_symbol_in_amount_date():
    # no currency column — code is detected from the amount cell's symbol
    res = reconcile.match([{"amount": "US$ 100"}], [{"amount": "S$ 100"}],
                          amount="amount", mode="amount_date")
    assert not res["matched"] and not res["ambiguous"]


# --------------------------------------------------------------------------- #
# 3. bare "$" is ambiguous (never assumed USD)
# --------------------------------------------------------------------------- #
def test_bare_dollar_is_ambiguous():
    (amt, code), note = dataclean.parse_currency("$1,000")
    assert amt == Decimal("1000") and code is None and "ambiguous" in note
    assert reconcile.to_currency("$100") is None
    # an expected currency resolves it
    val, note2, _ = dataclean._convert("$1,000", {"type": "currency", "currency": "SGD"})
    assert val == Decimal("1000") and note2 == ""


def test_disambiguated_dollars_resolve():
    assert dataclean.parse_currency("US$ 50")[0][1] == "USD"
    assert dataclean.parse_currency("S$ 2.5m")[0] == (Decimal("2500000.0"), "SGD")
    assert reconcile.to_currency("A$ 90") == "AUD"


# --------------------------------------------------------------------------- #
# 4. amount/date outside the window -> ambiguous, inside -> matched
# --------------------------------------------------------------------------- #
def test_amount_date_window_constraint():
    A = [{"amount": "500.00", "date": "01 Jun 2026"}]
    B = [{"amount": "500.00", "date": "25 Jun 2026"}]      # 24 days apart
    out = reconcile.match(A, B, amount="amount", date="date",
                          mode="amount_date", date_window_days=5)
    assert not out["matched"] and len(out["ambiguous"]) == 1
    assert any(e["category"] == "ambiguous_match" for e in reconcile.triage(out))
    inside = reconcile.match(A, B, amount="amount", date="date",
                             mode="amount_date", date_window_days=30)
    assert len(inside["matched"]) == 1 and not inside["ambiguous"]


# --------------------------------------------------------------------------- #
# 5. strict-currency mode refuses unknown-currency matches
# --------------------------------------------------------------------------- #
def test_strict_currency_blocks_unknown():
    A = [{"ref": "R1", "amount": "100.00"}]                # currency unknown
    B = [{"ref": "R1", "amount": "100.00"}]
    assert len(reconcile.match(A, B, key="ref", amount="amount")["matched"]) == 1   # permissive
    strict = reconcile.match(A, B, key="ref", amount="amount", strict_currency=True)
    assert not strict["matched"] and len(strict["currency_unknown"]) == 1
    assert any(e["category"] == "currency_unknown" for e in reconcile.triage(strict))


# --------------------------------------------------------------------------- #
# 6. multi-sheet workbook requires explicit selection
# --------------------------------------------------------------------------- #
def _write_xlsx(path, sheets):
    """sheets = [(name, rows_or_None)]; None leaves the sheet empty."""
    from openpyxl import Workbook
    wb = Workbook()
    wb.remove(wb.active)
    for name, rows in sheets:
        ws = wb.create_sheet(name)
        for r in (rows or []):
            ws.append(r)
    wb.save(path)


def test_multisheet_requires_selection():
    d = tempfile.mkdtemp()
    multi = Path(d) / "multi.xlsx"
    _write_xlsx(multi, [("Cover", None),
                        ("Data", [["a", "b"], [1, 2]]),
                        ("Notes", [["x"], ["hi"]])])
    try:
        ingest.read_any(str(multi))
        raise AssertionError("expected SheetSelectionRequired for a multi-data-sheet workbook")
    except ingest.SheetSelectionRequired as e:
        assert "Data" in str(e) and "Notes" in str(e)
    rows, note = ingest.read_any(str(multi), sheet="Data")
    assert rows[0] == ["a", "b"]

    single = Path(d) / "single.xlsx"
    _write_xlsx(single, [("Cover", None), ("TheData", [["k"], [9]])])
    rows, note = ingest.read_any(str(single))
    assert rows[0][0] == "k" and "auto-selected" in note      # picks the only data sheet


def test_viz_rows_from_xlsx_multisheet_safe():
    d = tempfile.mkdtemp()
    multi = Path(d) / "m.xlsx"
    _write_xlsx(multi, [("Cover", None),
                        ("Data", [["k", "v"], [1, 2]]),
                        ("More", [["x"], [9]])])
    try:
        viz.rows_from_xlsx(str(multi))
        raise AssertionError("expected a raise for a multi-data-sheet workbook")
    except Exception as e:                                   # SheetSelectionRequired or ValueError
        assert "sheet" in str(e).lower() or "Data" in str(e)
    assert viz.rows_from_xlsx(str(multi), sheet="Data") == [{"k": 1, "v": 2}]


# --------------------------------------------------------------------------- #
# 7 & 8. form extraction: next-line + dotted-leader layouts
# --------------------------------------------------------------------------- #
_FORM_FIELDS = [
    {"name": "Investor", "labels": ["investor"], "type": "text"},
    {"name": "Settlement bank", "labels": ["settlement bank", "bank"], "type": "text"},
    {"name": "Fee", "labels": ["fee"], "type": "currency", "currency": "GBP"},
]
_FORM_TEXT = ("Subscription confirmation\n"
              "Investor: Acme Pension Fund\n"
              "Settlement bank\n"          # label alone -> value on the next line
              "HSBC London\n"
              "Fee .......... GBP 2,500\n")  # dotted leader


def test_next_line_form_field():
    rec, _ = extract.extract_fields(None, _FORM_FIELDS, text=_FORM_TEXT)
    assert rec["Settlement bank"] == "HSBC London"


def test_dotted_leader_form_field():
    rec, _ = extract.extract_fields(None, _FORM_FIELDS, text=_FORM_TEXT)
    assert rec["Fee"] == Decimal("2500")


def test_next_line_stops_at_following_label():
    # if a field's value is genuinely absent, the next-line search must not grab the next label
    fields = [{"name": "A", "labels": ["field a"], "type": "text"},
              {"name": "B", "labels": ["field b"], "type": "text"}]
    rec, flags = extract.extract_fields(None, fields, text="Field A\nField B\nvalue-b\n")
    assert rec["A"] == "" and rec["B"] == "value-b"
    assert any(f["field"] == "A" for f in flags)


# --------------------------------------------------------------------------- #
# 9. currency code_target splits the code into its own column
# --------------------------------------------------------------------------- #
def test_code_target_currency_split():
    raw = [["Amount"], ["S$ 1,000"], ["US$ 2,000"], ["$ 3,000"]]
    recipe = {"columns": [{"source": "Amount", "target": "Amount", "type": "currency",
                           "currency": "SGD", "code_target": "Currency"}]}
    header, rows, _ = dataclean.apply_recipe(raw, recipe)
    assert header == ["Amount", "Currency"]
    assert [r[1] for r in rows] == ["SGD", "USD", "SGD"]    # bare $ resolved to expected SGD
    assert rows[0][0] == Decimal("1000")


# --------------------------------------------------------------------------- #
# 10. categorical value-map proposal
# --------------------------------------------------------------------------- #
def test_categorical_value_map_proposal():
    clusters = dataclean.propose_value_map(["USA", "U.S.A.", "USA", "usa",
                                            "United States", "Canada", "canada"])
    top = clusters[0]
    assert top["canonical"] == "USA" and set(top["variants"]) >= {"U.S.A.", "usa"}
    vmap = dataclean.value_map_from_clusters(clusters)
    val, note, _ = dataclean._convert("u.s.a.", {"type": "categorical", "value_map": vmap})
    assert val == "USA" and "standardised" in note
    # master list snaps to the master spelling
    cm = dataclean.propose_value_map(["united states", "UNITED STATES"], master=["United States"])
    assert cm[0]["canonical"] == "United States" and cm[0]["from_master"]


# --------------------------------------------------------------------------- #
# 11. PDF table extraction — engine scoring (deterministic) + guarded smoke test
# --------------------------------------------------------------------------- #
def test_pdf_table_scoring_and_selection():
    good = [["A", "B"], ["1", "2"], ["3", "4"]]            # 3x2 consistent
    onecol = [["just text"], ["more text"]]                # not table-shaped
    assert ingest._table_score(good) > 0
    assert ingest._table_score(onecol) == 0
    # better-scoring engine wins; ties go to pdfplumber (preferred for messy tables)
    assert ingest._choose_tables([good], [onecol]) == ([good], "pdfplumber")
    assert ingest._choose_tables([onecol], [good]) == ([good], "pymupdf")
    assert ingest._choose_tables([good], [good]) == ([good], "pdfplumber")
    assert ingest._choose_tables([], []) == ([], None)


def test_pdf_read_smoke():
    try:
        import fitz  # noqa: F401
    except ImportError:
        print("  [skip] PyMuPDF not installed — PDF smoke test skipped")
        return
    import fitz
    d = tempfile.mkdtemp()
    pdf = Path(d) / "t.pdf"
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 100), "Investor    Commitment    Currency")
    page.insert_text((72, 120), "Acme        1000           USD")
    page.insert_text((72, 140), "Beta        2000           SGD")
    doc.save(str(pdf))
    doc.close()
    rows, note = ingest.read_pdf(str(pdf))
    flat = " ".join(str(c) for r in rows for c in r)
    assert "Acme" in flat and "1000" in flat, (note, rows)


# --------------------------------------------------------------------------- #
# Standalone runner (no pytest needed)
# --------------------------------------------------------------------------- #
def _run_all():
    tests = sorted((n, f) for n, f in globals().items()
                   if n.startswith("test_") and callable(f))
    failed = 0
    for name, fn in tests:
        try:
            fn()
            print(f"  PASS  {name}")
        except Exception as e:  # noqa: BLE001
            failed += 1
            print(f"  FAIL  {name}: {type(e).__name__}: {e}")
    print(f"\n{len(tests) - failed}/{len(tests)} passed"
          + (f", {failed} FAILED" if failed else ""))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(_run_all())
