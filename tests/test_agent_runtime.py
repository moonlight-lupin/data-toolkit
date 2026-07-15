#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import agent_runtime_api as ar


def check(name, fn):
    try:
        fn()
        print(f"PASS {name}")
        return True
    except Exception as exc:
        print(f"FAIL {name}: {exc}")
        return False


def test_json_ingest():
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "rows.json"
        p.write_text(json.dumps([{"id": 1, "party": {"name": "A"}}, {"id": 2, "party": {"name": "B"}}]), encoding="utf-8")
        table = ar.read_table(str(p))
        assert table.header == ["id", "party"]
        assert table.rows[0]["party"]["name"] == "A"
        assert "2 record" in table.note


def test_json_path_and_auto_list():
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "wrapped.json"
        p.write_text(json.dumps({"meta": {"as_of": "2026-07-15"}, "records": [{"x": 1}, {"x": 2}]}), encoding="utf-8")
        explicit = ar.read_table({"path": str(p), "json_path": "records"})
        auto = ar.read_table(str(p))
        assert len(explicit.rows) == len(auto.rows) == 2
        assert "auto-selected" in auto.note


def test_plan_validation_approval():
    plan = {
        "version": 1,
        "skill": "data-convert",
        "inputs": ["source.csv"],
        "spec": {"target": {}},
        "output": "out.csv",
    }
    result = ar.validate_plan(plan, check_sources=False)
    assert result["status"] == "needs_approval"
    assert result["approvals_required"][0]["kind"] == "plan_confirmation"
    plan["approval"] = {"confirmed": True}
    result = ar.validate_plan(plan, check_sources=False)
    assert result["status"] == "success"


def test_all_skill_plan_shapes_validate():
    common = {"version": 1, "input": "source.csv", "output": "out.bin", "approval": {"confirmed": True}}
    plans = [
        {**common, "skill": "data-tidy", "recipe": {"columns": []}},
        {**common, "skill": "data-extract", "mode": "fields", "fields": [{"name": "X", "labels": ["x"]}]},
        {"version": 1, "skill": "data-reconcile", "inputs": ["a.csv", "b.csv"], "output": "r.xlsx", "approval": {"confirmed": True}},
        {**common, "skill": "data-analyse", "operations": []},
        {"version": 1, "skill": "data-visualise", "inputs": [], "output": "d.html", "dashboard": {"title": "D", "blocks": []}},
        {**common, "skill": "data-convert", "spec": {"target": {}}},
    ]
    for plan in plans:
        result = ar.validate_plan(plan, check_sources=False)
        assert not result["errors"], (plan["skill"], result)


def test_convert_json_flatten_union_and_nest():
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        a = td / "a.json"
        b = td / "b.json"
        a.write_text(json.dumps([{"id": 1, "party": {"name": "A"}, "amount": 10}]), encoding="utf-8")
        b.write_text(json.dumps([{"id": 2, "party": {"name": "B"}, "amount": 20, "extra": "x"}]), encoding="utf-8")
        out = td / "flat.csv"
        plan = {
            "version": 1,
            "skill": "data-convert",
            "inputs": [str(a), str(b)],
            "spec": {
                "reshape": [{"op": "union", "how": "outer"}, {"op": "flatten"}],
                "target": {"format": "csv"},
            },
            "output": str(out),
            "approval": {"confirmed": True},
        }
        result = ar.run_plan(plan, base_dir=td)
        assert result["status"] == "success", result
        text = out.read_text(encoding="utf-8")
        assert "party.name" in text and "extra" in text and "A" in text and "B" in text
        assert result["metrics"]["sources"] == 2

        source = td / "lines.csv"
        source.write_text("id,sku,amount\n1,A,10\n1,B,20\n", encoding="utf-8")
        nested_out = td / "nested.csv"
        nest_plan = {
            "version": 1,
            "skill": "data-convert",
            "inputs": [str(source)],
            "spec": {
                "reshape": [{"op": "nest", "key_cols": ["id"], "into": "lines", "child_cols": ["sku", "amount"]}],
                "target": {"format": "json"},
            },
            "output": str(nested_out),
            "approval": {"confirmed": True},
        }
        nested_result = ar.run_plan(nest_plan, base_dir=td)
        written = Path(nested_result["artifacts"][0]["path"])
        assert written.suffix == ".json" and written.exists(), nested_result
        payload = json.loads(written.read_text(encoding="utf-8"))
        assert len(payload) == 1 and len(payload[0]["lines"]) == 2


def test_multiple_conversion_inputs_require_explicit_union():
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        a = td / "a.json"
        b = td / "b.json"
        a.write_text('[{"x":1}]', encoding="utf-8")
        b.write_text('[{"x":2}]', encoding="utf-8")
        out = td / "new-output-dir" / "out.csv"
        plan = {
            "version": 1, "skill": "data-convert",
            "inputs": [str(a), str(b)],
            "spec": {"target": {"format": "csv"}},
            "output": str(out), "approval": {"confirmed": True},
        }
        result = ar.run_plan(plan, base_dir=td)
        assert result["status"] == "error", result
        assert "explicit union" in result["errors"][0]
        assert not out.exists()


def test_extract_fields_validation_does_not_parse_as_table():
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        document = td / "form.pdf"
        document.write_bytes(b"not a real PDF; validation should only check existence")
        plan = {
            "version": 1, "skill": "data-extract", "input": str(document),
            "mode": "fields", "fields": [{"name": "Name", "labels": ["name"]}],
            "output": str(td / "out.xlsx"), "approval": {"confirmed": True},
        }
        result = ar.validate_plan(plan, base_dir=td)
        assert not result["errors"], result


def test_analysis_zero_total_is_preserved():
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        src = td / "zero.json"
        src.write_text(json.dumps([{"group": "A", "amount": 10}, {"group": "B", "amount": -10}]), encoding="utf-8")
        out = td / "analysis.json"
        plan = {
            "version": 1,
            "skill": "data-analyse",
            "input": str(src),
            "operations": [{"op": "breakdown", "by": "group", "value": "amount"}],
            "output": str(out),
            "approval": {"confirmed": True},
        }
        result = ar.run_plan(plan, base_dir=td)
        assert result["status"] == "success", result
        breakdown = result["details"]["results"][0]["result"]
        assert breakdown["grand_total"] == "0", breakdown
        assert breakdown["top1_share"] is None and breakdown["top3_share"] is None
        assert all(g["share"] is None for g in breakdown["groups"])


def test_tidy_json_runtime():
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        src = td / "messy.json"
        src.write_text(json.dumps([{"Name": " Alice ", "Amount": "1,200.00"}]), encoding="utf-8")
        out = td / "clean.xlsx"
        plan = {
            "version": 1,
            "skill": "data-tidy",
            "input": str(src),
            "recipe": {"columns": [
                {"source": "Name", "target": "Name", "type": "text"},
                {"source": "Amount", "target": "Amount", "type": "number"}
            ]},
            "output": str(out),
            "approval": {"confirmed": True},
        }
        result = ar.run_plan(plan, base_dir=td)
        assert result["status"] in ("success", "success_with_warnings"), result
        assert out.exists() and out.with_suffix(".report.md").exists()


def test_reconcile_json_runtime():
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        a = td / "a.json"
        b = td / "b.json"
        a.write_text(json.dumps([{"invoice_no": "INV-1", "amount": "100", "date": "01 Jul 2026"}]), encoding="utf-8")
        b.write_text(json.dumps([{"invoice_no": "INV-1", "amount": "100", "date": "01 Jul 2026"}]), encoding="utf-8")
        out = td / "recon.xlsx"
        plan = {
            "version": 1,
            "skill": "data-reconcile",
            "inputs": [str(a), str(b)],
            "options": {"preset": "invoice_tracker_vs_ledger"},
            "output": str(out),
            "approval": {"confirmed": True},
        }
        result = ar.run_plan(plan, base_dir=td)
        assert result["status"] == "success", result
        assert result["metrics"]["matched"] == 1 and out.exists()


def test_visualise_declarative_runtime():
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        src = td / "rows.json"
        src.write_text(json.dumps([{"Owner": "A", "Status": "Open"}]), encoding="utf-8")
        out = td / "dashboard.html"
        plan = {
            "version": 1,
            "skill": "data-visualise",
            "input": str(src),
            "dashboard": {
                "title": "Agent runtime dashboard",
                "as_of": "15 Jul 2026",
                "blocks": [
                    {"type": "kpi_row", "items": [{"label": "Open", "value": 1, "status": "amber"}]},
                    {"type": "table", "title": "Rows", "rows": "$source",
                     "rag": {"Status": {"Open": "amber"}}}
                ]
            },
            "output": str(out),
        }
        result = ar.run_plan(plan, base_dir=td)
        assert result["status"] == "success", result
        html = out.read_text(encoding="utf-8")
        assert "Agent runtime dashboard" in html and "Owner" in html and "Open" in html
        assert "border-left:3px solid" in html


def test_dry_run_writes_nothing():
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        src = td / "x.json"
        src.write_text(json.dumps([{"x": 1}]), encoding="utf-8")
        out = td / "new-output-dir" / "out.csv"
        plan = {
            "version": 1,
            "skill": "data-convert",
            "input": str(src),
            "spec": {"target": {"format": "csv"}},
            "output": str(out),
        }
        result = ar.run_plan(plan, base_dir=td, dry_run=True)
        assert result["status"] == "success", result
        assert not out.exists()
        assert not out.parent.exists()


def test_cli_schema_and_inspect():
    cli = ROOT / "bin" / "data-toolkit"
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "x.json"
        p.write_text('[{"a":1}]', encoding="utf-8")
        raw = subprocess.check_output([sys.executable, str(cli), "inspect", str(p)], text=True)
        result = json.loads(raw)
        assert result["status"] == "success" and result["metrics"]["rows"] == 1
        raw = subprocess.check_output([sys.executable, str(cli), "schema"], text=True)
        assert json.loads(raw)["details"]["example"]["version"] == 1


def main():
    tests = [
        ("JSON ingest", test_json_ingest),
        ("JSON path + auto list", test_json_path_and_auto_list),
        ("approval gate", test_plan_validation_approval),
        ("six skill plan shapes", test_all_skill_plan_shapes_validate),
        ("convert JSON/flatten/union/nest", test_convert_json_flatten_union_and_nest),
        ("explicit multi-source union", test_multiple_conversion_inputs_require_explicit_union),
        ("extract fields validation", test_extract_fields_validation_does_not_parse_as_table),
        ("analysis zero total", test_analysis_zero_total_is_preserved),
        ("tidy JSON runtime", test_tidy_json_runtime),
        ("reconcile JSON runtime", test_reconcile_json_runtime),
        ("visualise declarative runtime", test_visualise_declarative_runtime),
        ("dry-run", test_dry_run_writes_nothing),
        ("CLI schema + inspect", test_cli_schema_and_inspect),
    ]
    passed = sum(1 for name, fn in tests if check(name, fn))
    print(f"agent runtime: {passed}/{len(tests)} passed")
    if passed != len(tests):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
