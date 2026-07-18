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
import json
import subprocess
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


def test_amount_date_missing_dates_do_not_match():
    A = [{"amount": "100.00", "date": ""}]
    B = [{"amount": "100.00", "date": "01 Jun 2026"}]
    res = reconcile.match(A, B, amount="amount", date="date", mode="amount_date")
    assert not res["matched"] and not res["ambiguous"]
    assert len(res["a_only"]) == 1 and len(res["b_only"]) == 1

    bad = reconcile.match([{"amount": "100.00", "date": "not a date"}], B,
                          amount="amount", date="date", mode="amount_date")
    assert not bad["matched"] and len(bad["a_only"]) == 1 and len(bad["b_only"]) == 1


def test_key_mode_missing_amount_flagged():
    res = reconcile.match([{"ref": "R1", "amount": ""}],
                          [{"ref": "R1", "amount": "0.00"}],
                          key="ref", amount="amount")
    assert not res["matched"] and not res["value_diffs"]
    assert len(res["parse_errors"]) == 1
    assert any(e["category"] == "parse_error" for e in reconcile.triage(res))


def test_aggregation_currency_mismatch_rejected():
    one = {
        "matched": [], "value_diffs": [], "currency_diffs": [], "currency_unknown": [],
        "parse_errors": [], "dup_a": [], "dup_b": [], "ambiguous": [],
        "a_only": [{"a": {"row": {"batch": "B1"}, "amt": Decimal("100"), "dt": None, "ccy": "USD"}}],
        "b_only": [{"b": {"row": {"batch": "B1"}, "amt": Decimal("40"), "dt": None, "ccy": "USD"}},
                   {"b": {"row": {"batch": "B1"}, "amt": Decimal("60"), "dt": None, "ccy": "SGD"}}],
    }
    assert reconcile.propose_aggregations(one, group_col="batch") == []

    many = {
        "matched": [], "value_diffs": [], "currency_diffs": [], "currency_unknown": [],
        "parse_errors": [], "dup_a": [], "dup_b": [], "ambiguous": [],
        "a_only": [{"a": {"row": {"batch": "B2"}, "amt": Decimal("100"), "dt": None, "ccy": "USD"}}],
        "b_only": [{"b": {"row": {"batch": "B2"}, "amt": Decimal("100"), "dt": None, "ccy": "SGD"}},
                   {"b": {"row": {"batch": "B2"}, "amt": Decimal("0"), "dt": None, "ccy": "SGD"}}],
    }
    assert reconcile.propose_aggregations(many, group_col="batch") == []


def test_apply_recipe_empty_input():
    header, rows, log = dataclean.apply_recipe([], {"columns": []})
    assert header == [] and rows == []
    assert log["rows_out"] == 0 and "empty input" in log["message"]


def test_col_index_ambiguous_short_name():
    assert dataclean._col_index(["Invoice date", "Payment date"], "date") is None
    assert dataclean._col_index(["Amount", "Payment date"], "date") == 1


def test_bool_unrecognised_kept_raw():
    raw = [["Active"], ["maybe"], ["N/A"], ["yes"], ["0"]]
    recipe = {"columns": [{"source": "Active", "target": "Active", "type": "bool"}]}
    _, rows, log = dataclean.apply_recipe(raw, recipe)
    assert rows == [["maybe"], ["N/A"], [True], [False]]
    assert [f["value"] for f in log["flagged"]] == ["maybe", "N/A"]


def test_md_escape_pipe_in_value():
    log = {"header": 0, "dropped": {"blank": 0, "totals": 0}, "transforms": [],
           "flagged": [{"row": 1, "column": "A|B", "value": "x|y", "reason": "bad|value"}],
           "duplicates": [], "validation": [], "rows_in": 1, "rows_out": 1}
    report = dataclean.render_report(log)
    assert "A\\|B" in report and "x\\|y" in report and "bad\\|value" in report

    rreport = reconcile.render_report(
        {"rag": "AMBER", "pct_reconciled": 0, "matched": 0, "aggregated": 0,
         "exceptions": 1, "material_or_escalate": 0, "value_matched": Decimal("0"),
         "value_in_exception": Decimal("1"), "by_category": {"x|y": {"n": 1, "val": Decimal("1")}}},
        [{"category": "x|y", "magnitude": Decimal("1"), "materiality": "immaterial",
          "probable_cause": "a|b", "suggested_action": "c|d"}])
    assert "x\\|y" in rreport and "a\\|b" in rreport


def test_currency_code_case_insensitive():
    assert dataclean.parse_currency("sgd 100")[0] == dataclean.parse_currency("SGD 100")[0]
    assert dataclean.parse_currency("sgd 100")[0][1] == "SGD"
    assert reconcile.to_currency("sgd 100") == "SGD"


def test_european_number_format_flagged():
    n, note = dataclean.parse_number("1.234,56")
    assert n is None and "European" in note
    res, cnote = dataclean.parse_currency("EUR 1.234,56")
    assert res is None and "European" in cnote


def test_get_table_engine_param():
    old = ingest.extract_pdf_table
    calls = []

    def fake(path, page, index=0, engine=None):
        calls.append((path, page, index, engine))
        return [["ok"]]

    ingest.extract_pdf_table = fake
    try:
        assert extract.get_table("sample.pdf", page=2, index=3, engine="pdfplumber") == [["ok"]]
        assert calls == [("sample.pdf", 2, 3, "pdfplumber")]
    finally:
        ingest.extract_pdf_table = old


def test_logo_restricted_to_images():
    d = tempfile.mkdtemp()
    txt = Path(d) / "logo.txt"
    txt.write_text("not image", encoding="utf-8")
    html = viz._logo_for({"logo_path": str(txt), "brand_name": "Acme"})
    assert "<img" not in html and "Acme" in html


def test_pii_egress_nric_pattern():
    hook = _ROOT / "hooks" / "pii_egress_guard.py"
    payload = {"tool_input": {"query": "Can you search S1234567D payment status?"}}
    proc = subprocess.run([sys.executable, str(hook)], input=json.dumps(payload),
                          text=True, capture_output=True, check=False)
    assert proc.returncode == 0
    out = json.loads(proc.stdout)
    assert out["hookSpecificOutput"]["permissionDecision"] == "ask"


# --------------------------------------------------------------------------- #
# Day-to-day finance strengthening (v0.2.1): debit/credit columns, case-insensitive
# column names, flip_b, balance completeness, ageing, tax hint, per-currency summary
# --------------------------------------------------------------------------- #
def test_column_names_resolved_case_insensitively():
    # a bank CSV says "Amount" / "Date"; the config says amount/date — must still match
    A = [{"Amount": "100.00", "Date": "01/06/2026"}]
    B = [{"amount": "100.00", "date": "01/06/2026"}]
    res = reconcile.match(A, B, amount="amount", date="date", mode="amount_date")
    assert len(res["matched"]) == 1, res


def test_debit_credit_columns_make_signed_amount():
    # bank export splits Debit/Credit; ledger holds one signed amount — they must reconcile
    bank = [{"Date": "01/06/2026", "Debit": "", "Credit": "1,000.00"},
            {"Date": "02/06/2026", "Debit": "250.00", "Credit": ""}]
    ledger = [{"date": "01/06/2026", "amount": "-1,000.00"},
              {"date": "02/06/2026", "amount": "250.00"}]
    res = reconcile.match(bank, ledger, amount="amount", debit="debit", credit="credit",
                          date="date", mode="amount_date")
    assert len(res["matched"]) == 2, res


def test_flip_b_reconciles_opposite_sign_conventions():
    A = [{"k": "1", "amount": "100.00"}]
    B = [{"k": "1", "amount": "-100.00"}]
    assert not reconcile.match(A, B, key="k", amount="amount")["matched"]
    res = reconcile.match(A, B, key="k", amount="amount", flip_b=True)
    assert len(res["matched"]) == 1, res


def test_balance_completeness_check():
    rows = [{"amount": "1,000.00"}, {"amount": "-250.00"}]
    ok = reconcile.check_balance(rows, amount="amount", opening="100.00", closing="850.00")
    assert ok["ties"] is True and ok["movement"] == Decimal("750.00")
    # a truncated extract must NOT tie
    bad = reconcile.check_balance(rows[:1], amount="amount", opening="100.00", closing="850.00")
    assert bad["ties"] is False
    assert "DOES NOT TIE" in reconcile.render_balance_check(bad, "Bank")


def test_aging_of_one_sided_items():
    res = reconcile.match([{"amount": "500.00", "date": "01 Jun 2026"}], [],
                          amount="amount", date="date", mode="amount_date")
    exc = reconcile.triage(res, as_of="30 Jun 2026")
    assert exc[0]["age_days"] == 29
    assert "aged 29d" in exc[0]["probable_cause"]
    # no as_of -> no ageing (deterministic default)
    assert reconcile.triage(res)[0]["age_days"] is None


def test_tax_hint_on_net_vs_gross_mismatch():
    res = reconcile.match([{"k": "1", "amount": "1000.00"}],
                          [{"k": "1", "amount": "1090.00"}], key="k", amount="amount")
    exc = reconcile.triage(res)
    assert exc[0]["category"] == "amount_mismatch"
    assert "GST/VAT/WHT" in exc[0]["probable_cause"]
    # a non-tax-shaped difference gets no hint
    res2 = reconcile.match([{"k": "1", "amount": "1000.00"}],
                           [{"k": "1", "amount": "1234.00"}], key="k", amount="amount")
    assert "GST/VAT/WHT" not in reconcile.triage(res2)[0]["probable_cause"]


def test_summary_per_currency_breakdown():
    A = [{"ref": "R1", "amount": "100.00", "ccy": "USD"},
         {"ref": "R2", "amount": "50.00", "ccy": "SGD"},
         {"ref": "R3", "amount": "70.00", "ccy": "SGD"}]
    B = [{"ref": "R1", "amount": "100.00", "ccy": "USD"},
         {"ref": "R2", "amount": "50.00", "ccy": "SGD"}]
    res = reconcile.match(A, B, key="ref", amount="amount", currency="ccy")
    exc = reconcile.triage(res)
    s = reconcile.summarise(res, exc)
    assert s["by_currency"]["USD"]["matched_val"] == Decimal("100.00")
    assert s["by_currency"]["SGD"]["matched_val"] == Decimal("50.00")
    assert s["by_currency"]["SGD"]["exception_val"] == Decimal("70.00")
    report = reconcile.render_report(s, exc)
    assert "Mixed currencies" in report


# --------------------------------------------------------------------------- #
# 16. Large-file streaming (scripts/streaming.py + ingest.read_large)
# --------------------------------------------------------------------------- #
def test_streaming_count_rows():
    """Row counts via read_only iter_rows; strategy gate for a small sheet is direct."""
    import streaming
    d = tempfile.mkdtemp()
    path = Path(d) / "rows.xlsx"
    rows = [["id", "amount", "ccy"]] + [[i, i * 1.5, "USD"] for i in range(1, 501)]
    _write_xlsx(path, [("Ledger", rows), ("Empty", None)])
    counts = streaming.count_rows(str(path))
    assert counts["sheets"]["Ledger"] == 501          # header + 500 data
    assert counts["sheets"]["Empty"] == 0
    assert counts["total"] == 501
    one = streaming.count_rows(str(path), sheet="Ledger")
    assert one["sheets"] == {"Ledger": 501}
    assert streaming.choose_strategy(str(path), sheet="Ledger") == "direct"


def test_streaming_excel_to_parquet_and_read_large():
    import streaming
    if not streaming.pyarrow_available():
        print("  SKIP  test_streaming_excel_to_parquet_and_read_large (no pyarrow/pandas)")
        return
    import pandas as pd
    d = tempfile.mkdtemp()
    path = Path(d) / "stream_me.xlsx"
    n = 2500
    rows = [["txn_id", "amount", "region"]] + [
        [f"T{i}", float(i), "APAC" if i % 2 == 0 else "EMEA"] for i in range(n)
    ]
    _write_xlsx(path, [("Data", rows)])
    pq = Path(d) / "out.parquet"
    written = streaming.stream_excel_to_parquet(str(path), str(pq), sheet="Data", chunk_size=800)
    assert written == n
    df = pd.read_parquet(pq)
    assert len(df) == n
    assert list(df.columns) == ["txn_id", "amount", "region"]

    # Force stream strategy via threshold monkeypatch for ingest.read_large
    old_d, old_p = streaming.DIRECT_THRESHOLD, streaming.PARQUET_CACHE_THRESHOLD
    streaming.DIRECT_THRESHOLD = 10
    streaming.PARQUET_CACHE_THRESHOLD = 100
    try:
        assert streaming.choose_strategy(str(path), sheet="Data") == "stream"
        frame, note = ingest.read_large(str(path), sheet="Data", cache_dir=d)
        assert "stream" in note
        assert len(frame) == n
    finally:
        streaming.DIRECT_THRESHOLD = old_d
        streaming.PARQUET_CACHE_THRESHOLD = old_p


def test_parquet_cache_preserves_none_and_nan_literals():
    """parquet_cache must not null real string values 'None' / 'nan' (review M1)."""
    import streaming
    if not streaming.pyarrow_available():
        print("  SKIP  test_parquet_cache_preserves_none_and_nan_literals (no pyarrow/pandas)")
        return
    d = tempfile.mkdtemp()
    path = Path(d) / "names.xlsx"
    # 12 data rows → force parquet_cache with lowered thresholds
    rows = [["customer", "note"]] + [
        ["None Corp", "nan handling pending"],
        ["Acme", "ok"],
    ] * 6
    _write_xlsx(path, [("Data", rows)])
    old_d, old_p = streaming.DIRECT_THRESHOLD, streaming.PARQUET_CACHE_THRESHOLD
    streaming.DIRECT_THRESHOLD = 2
    streaming.PARQUET_CACHE_THRESHOLD = 10_000
    try:
        assert streaming.choose_strategy(str(path), sheet="Data") == "parquet_cache"
        frame, note = ingest.read_large(str(path), sheet="Data", cache_dir=d)
        assert "parquet_cache" in note
        assert "None Corp" in set(frame["customer"].astype(str))
        assert "nan handling pending" in set(frame["note"].astype(str))
        # Second read hits cache — still preserved
        frame2, note2 = ingest.read_large(str(path), sheet="Data", cache_dir=d)
        assert "cache hit" in note2
        assert "None Corp" in set(frame2["customer"].astype(str))
    finally:
        streaming.DIRECT_THRESHOLD = old_d
        streaming.PARQUET_CACHE_THRESHOLD = old_p


def test_optimize_dtypes_saves_memory():
    import streaming
    try:
        import pandas as pd
        import numpy as np
    except ImportError:
        print("  SKIP  test_optimize_dtypes_saves_memory (no pandas/numpy)")
        return
    n = 50_000
    # Mixed finance-shaped frame: wide int64/float64 + long repeated object labels.
    # Category conversion on long strings is where most of the saving comes from.
    regions = np.array(
        ["Asia-Pacific regional coverage office"] * (n // 4)
        + ["Europe Middle East Africa desk"] * (n // 4)
        + ["Americas institutional coverage"] * (n // 4)
        + ["Global multi-strategy allocation"] * (n // 4),
        dtype=object,
    )
    statuses = np.array(
        ["open - pending settlement review"] * (n // 2)
        + ["closed - archived prior period"] * (n // 2),
        dtype=object,
    )
    df = pd.DataFrame({
        "id": np.arange(n, dtype="int64"),
        "flag": np.zeros(n, dtype="int64"),
        "amt": np.linspace(0.0, 1.0, n).astype("float64"),
        "region": regions,
        "status": statuses,
    })
    before = df.memory_usage(deep=True).sum()
    out = streaming.optimize_dtypes(df)
    after = out.memory_usage(deep=True).sum()
    saved = (1 - after / before) * 100
    assert saved >= 40, f"expected ≥40% memory save, got {saved:.1f}%"
    assert str(out["region"].dtype) == "category"
    assert str(out["status"].dtype) == "category"


# --------------------------------------------------------------------------- #
# 17. Image / chart extraction (skills/data-extract/scripts/image_extract.py)
# --------------------------------------------------------------------------- #
def _load_image_extract():
    import importlib.util
    mod_path = _ROOT / "skills" / "data-extract" / "scripts" / "image_extract.py"
    spec = importlib.util.spec_from_file_location("image_extract", mod_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_parse_markdown_table_numeric_cleanup():
    ie = _load_image_extract()
    text = """
Here is the table:

| Region | Revenue | Growth | Fee |
|---|---|---|---|
| APAC | $1,234.50 | 12.5% | £90 |
| EMEA | US$2,000 | 8% | €1,100 |
| AMER | (500) | -3.2% | S$250 |

Done.
"""
    df = ie.parse_markdown_table(text)
    assert df is not None
    assert list(df.columns) == ["Region", "Revenue", "Growth", "Fee"]
    assert len(df) == 3
    # Works with pandas DataFrame or the no-pandas stand-in
    row0 = df.iloc[0] if hasattr(df, "iloc") else dict(zip(df.columns, df._data[0]))
    row1 = df.iloc[1] if hasattr(df, "iloc") else dict(zip(df.columns, df._data[1]))
    row2 = df.iloc[2] if hasattr(df, "iloc") else dict(zip(df.columns, df._data[2]))
    assert row0["Revenue"] == 1234.5
    assert abs(row0["Growth"] - 0.125) < 1e-9
    assert row1["Revenue"] == 2000
    assert row2["Revenue"] == -500
    assert row1["Fee"] == 1100


def test_image_extract_chart_and_table_mocked():
    ie = _load_image_extract()
    try:
        from PIL import Image
    except ImportError:
        print("  SKIP  test_image_extract_chart_and_table_mocked (no Pillow)")
        return

    d = Path(tempfile.mkdtemp())
    chart = d / "sales_bar_chart.png"
    table = d / "ledger_table.png"
    Image.new("RGB", (320, 200), color=(40, 80, 160)).save(chart)
    Image.new("RGB", (400, 240), color=(240, 240, 240)).save(table)

    chart_md = """
| Category | Value |
|---|---|
| Q1 | 120 |
| Q2 | 150 |
| Q3 | 90 |
| Q4 | 200 |
"""
    table_md = """
| Investor | Commit | Close |
|---|---|---|
| Acme Pension | 1000000 | 12 Jun 2026 |
| Beta FO | 2500000 | 13 Jun 2026 |
| Gamma LP | 750000 | 14 Jun 2026 |
"""

    class _Resp:
        def __init__(self, text, status=200):
            self.status_code = status
            self.text = text
            self._text = text

        def json(self):
            return {
                "choices": [{"message": {"content": self._text}}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 20},
                "model": "mock-vision",
            }

    calls = {"n": 0}

    def fake_post(url, headers=None, json=None, timeout=None):
        calls["n"] += 1
        # Route by which prompt was used
        prompt = json["messages"][0]["content"][0]["text"]
        if "chart title" in prompt.lower() or "data point" in prompt.lower():
            return _Resp(chart_md)
        return _Resp(table_md)

    cache = d / "cache"
    r1 = ie.extract_image(
        str(chart), api_key="test-key", model="mock-vision",
        cache_dir=cache, _request=fake_post,
    )
    assert r1.get("error") is None, f"chart extract error: {r1.get('error')}"
    assert r1["cached"] is False
    assert r1["type"] == "chart"
    assert r1["dataframe"] is not None and len(r1["dataframe"]) == 4
    cats = list(r1["dataframe"]["Category"])
    assert set(cats) == {"Q1", "Q2", "Q3", "Q4"}
    vals = [float(v) for v in r1["dataframe"]["Value"]]
    assert sum(vals) == 560

    # Cache hit on second call
    r1b = ie.extract_image(
        str(chart), api_key="test-key", model="mock-vision",
        cache_dir=cache, _request=fake_post,
    )
    assert r1b["cached"] is True
    assert calls["n"] == 1

    r2 = ie.extract_image(
        str(table), api_key="test-key", model="mock-vision",
        cache_dir=cache, _request=fake_post,
    )
    assert r2.get("error") is None, f"table extract error: {r2.get('error')}"
    assert r2["type"] == "table"
    assert r2["dataframe"] is not None
    assert list(r2["dataframe"].columns) == ["Investor", "Commit", "Close"]
    assert len(r2["dataframe"]) == 3
    assert int(r2["dataframe"].iloc[0]["Commit"]) == 1_000_000


def test_image_extract_batch_and_compress():
    ie = _load_image_extract()
    try:
        from PIL import Image
    except ImportError:
        print("  SKIP  test_image_extract_batch_and_compress (no Pillow)")
        return

    d = Path(tempfile.mkdtemp())
    imgs = d / "shots"
    imgs.mkdir()
    # Five small images + one oversized to exercise compression
    for i in range(5):
        Image.new("RGB", (64, 64), color=(i * 40, 100, 120)).save(imgs / f"table_{i}.png")
    big = imgs / "huge_photo.png"
    # Oversized on the long edge — compression path must resize (byte shrink is not
    # guaranteed for already-tiny solid-colour PNGs).
    Image.new("RGB", (2200, 1600), color=(200, 100, 50)).save(big, compress_level=1)

    md = "| A | B |\n|---|---|\n| 1 | 2 |\n| 3 | 4 |\n"

    class _Resp:
        status_code = 200
        text = md

        def json(self):
            return {
                "choices": [{"message": {"content": md}}],
                "usage": {},
                "model": "mock-vision",
            }

    def fake_post(url, headers=None, json=None, timeout=None):
        return _Resp()

    out = d / "batch.xlsx"
    summary = ie.extract_batch(
        str(imgs), str(out),
        api_key="test-key", model="mock-vision",
        cache_dir=d / "cache", _request=fake_post,
    )
    assert out.is_file(), "batch xlsx was not written"
    assert summary["count"] == 6, f"expected 6 images, got {summary['count']}"
    assert "combined" in summary["sheets"]

    import io
    compressed_bytes, mime, was_compressed = ie.compress_image(
        big, max_bytes=50_000, max_px=1024,
    )
    assert was_compressed is True
    out_img = Image.open(io.BytesIO(compressed_bytes))
    assert max(out_img.size) <= 1024
    assert max(Image.open(big).size) > 1024
# 17. PowerPoint ingest (read_pptx) + CJK / i18n fonts (viz)
# --------------------------------------------------------------------------- #
def _write_sample_pptx(path, *, with_image_only=True):
    """Build a multi-slide deck: tables on slides 1–2, optional image-only slide 3."""
    from pptx import Presentation
    from pptx.util import Inches
    import io
    prs = Presentation()
    blank = prs.slide_layouts[6]

    s1 = prs.slides.add_slide(blank)
    box = s1.shapes.add_textbox(Inches(0.5), Inches(0.2), Inches(5), Inches(0.4))
    box.text_frame.text = "Q2 commitments"
    t1 = s1.shapes.add_table(3, 2, Inches(0.5), Inches(0.8), Inches(4), Inches(1.4)).table
    t1.cell(0, 0).text, t1.cell(0, 1).text = "Investor", "Commit"
    t1.cell(1, 0).text, t1.cell(1, 1).text = "Acme", "1000000"
    t1.cell(2, 0).text, t1.cell(2, 1).text = "Beta", "2500000"
    # Second table on the same slide (multi-table)
    t1b = s1.shapes.add_table(2, 2, Inches(0.5), Inches(2.5), Inches(3), Inches(0.9)).table
    t1b.cell(0, 0).text, t1b.cell(0, 1).text = "Region", "Share"
    t1b.cell(1, 0).text, t1b.cell(1, 1).text = "APAC", "60%"

    s2 = prs.slides.add_slide(blank)
    t2 = s2.shapes.add_table(2, 2, Inches(0.5), Inches(0.5), Inches(3), Inches(0.9)).table
    t2.cell(0, 0).text, t2.cell(0, 1).text = "Metric", "Value"
    t2.cell(1, 0).text, t2.cell(1, 1).text = "AUM", "3.5bn"

    if with_image_only:
        s3 = prs.slides.add_slide(blank)
        try:
            from PIL import Image
            buf = io.BytesIO()
            Image.new("RGB", (24, 24), color=(200, 40, 40)).save(buf, format="PNG")
            buf.seek(0)
            s3.shapes.add_picture(buf, Inches(1), Inches(1), width=Inches(1))
        except ImportError:
            # Still image-only if we add nothing — empty slide counts as image-only too.
            pass

    prs.save(path)


def test_pptx_multi_slide_tables_and_read_any():
    try:
        import pptx  # noqa: F401
    except ImportError:
        print("  SKIP  test_pptx_multi_slide_tables_and_read_any (no python-pptx)")
        return
    d = tempfile.mkdtemp()
    path = Path(d) / "deck.pptx"
    _write_sample_pptx(path, with_image_only=True)
    rows, note = ingest.read_pptx(str(path))
    # Table rows only — title text frames must NOT pollute the row list (review M1)
    assert any(r == ["Investor", "Commit"] for r in rows)
    assert any(r == ["Acme", "1000000"] for r in rows)
    assert any(r == ["Region", "Share"] for r in rows)
    assert any(r == ["Metric", "Value"] for r in rows)
    assert not any(r == ["Q2 commitments"] for r in rows)
    assert all(len(r) >= 2 for r in rows), "text frames must not create 1-col rows"
    assert "tables on slide(s) 1, 2" in note
    assert "image-only slide(s) 3" in note
    assert "Q2 commitments" in note          # titles live in the note
    # read_any dispatches
    rows2, note2 = ingest.read_any(str(path))
    assert rows2 == rows and "pptx" in note2


def test_pptx_legacy_ppt_rejected_and_image_only_note():
    try:
        import pptx  # noqa: F401
    except ImportError:
        print("  SKIP  test_pptx_legacy_ppt_rejected_and_image_only_note (no python-pptx)")
        return
    try:
        ingest.read_any("legacy.ppt")
        assert False, "expected ValueError for .ppt"
    except ValueError as e:
        assert "Legacy .ppt not supported" in str(e)
        assert "convert to .pptx" in str(e)

    d = tempfile.mkdtemp()
    path = Path(d) / "pics.pptx"
    _write_sample_pptx(path, with_image_only=True)
    _, note = ingest.read_pptx(str(path))
    assert "image-only" in note
    assert "vision-model" in note


def test_has_cjk_detection():
    assert viz._has_cjk("Hello") is False
    assert viz._has_cjk("销售额") is True
    assert viz._has_cjk("Q2 売上") is True          # CJK ideograph + kana
    assert viz._has_cjk("안녕하세요") is True       # Hangul
    assert viz._has_cjk("") is False
    assert "arabic" in viz._detect_scripts("الإيرادات")
    assert "thai" in viz._detect_scripts("ยอดขาย")
    assert viz._needs_i18n_fonts("Hello world 2026") is False


def test_cjk_font_stack_conditional():
    # English-only: theme fonts unchanged (no CJK names injected)
    en = viz.dashboard("Operations dashboard",
                       [viz.bar_chart([("Mon", 4), ("Tue", 7)], title="Tasks by day")],
                       subtitle="Weekly")
    assert "Microsoft YaHei" not in en
    assert "Noto Sans CJK" not in en
    assert 'lang="en"' in en
    assert 'dir="ltr"' in en
    # Default body font still present
    assert "Inter" in en or "Segoe UI" in en

    # Chinese labels: CJK fallback stack applied; SVG chart text inherits via CSS
    zh = viz.dashboard("销售仪表板",
                       [viz.bar_chart([("一月", 4), ("二月", 7)], title="销售额")],
                       subtitle="季度回顾")
    assert "Microsoft YaHei" in zh or "Noto Sans CJK" in zh or "PingFang SC" in zh
    assert "销售额" in zh
    # Chart CSS uses the (augmented) font stack — SVG <text> inherits
    assert ".chart .v{font:11px" in zh.replace(" ", "") or "font:11px" in zh

    # Fully Arabic page → RTL + Arabic font names
    ar = viz.dashboard("لوحة القيادة", [viz.kpi_row([{"label": "الإيرادات", "value": 12}])])
    assert 'dir="rtl"' in ar
    assert "Noto Naskh Arabic" in ar or "Noto Sans Arabic" in ar

    # Mostly English with one Arabic label must NOT flip the whole page (review m2)
    mixed = viz.dashboard(
        "Operations dashboard",
        [viz.kpi_row([{"label": "Open tasks", "value": 12},
                      {"label": "الإيرادات", "value": 3}])],
        subtitle="Weekly",
    )
    assert 'dir="ltr"' in mixed
    assert "Noto Naskh Arabic" in mixed or "Noto Sans Arabic" in mixed


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
