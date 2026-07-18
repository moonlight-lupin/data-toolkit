#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import agent_runtime as ar
import agent_schemas as schemas


def check(name, fn):
    try:
        fn()
        print(f"PASS {name}")
        return True
    except Exception as exc:
        print(f"FAIL {name}: {exc}")
        return False


def valid_payloads():
    return {
        "data-extract": [{"name": "Investor", "labels": ["investor"], "type": "text"}],
        "data-tidy": {"columns": [{"source": "Amount", "target": "Amount", "type": "number"}]},
        "data-reconcile": {"mode": "key", "key": "invoice_no", "amount": "amount"},
        "data-analyse": [
            {"op": "numeric_summary", "column": "Amount"},
            {"op": "period_series", "date_col": "Date", "value": "Amount", "grain": "month"},
            {"op": "concentration", "by": "Customer", "value": "Amount", "top_n": 4},
            {"op": "percentile", "column": "Amount", "q": [0.5, 0.9]},
            {"op": "cohort", "id_col": "Customer", "date_col": "Date", "grain": "month"},
            {"op": "compare_series", "date_col": "Date", "a_value": "Actual", "b_value": "Budget"},
        ],
        "data-visualise": {
            "title": "Status", "blocks": [
                {"type": "kpi_row", "items": [{"label": "Open", "value": 3, "status": "amber"}]},
                {"type": "table", "rows": "$source", "sortable": True},
            ],
        },
        "data-convert": {
            "source": {"expected_columns": ["Date", "Amount"]},
            "target": {"format": "csv", "columns": [{"name": "Date"}, {"name": "Amount"}]},
            "map": {"Date": {"from": "Date", "type": "date"}, "Amount": {"from": "Amount", "type": "number"}},
            "reshape": [{"op": "flatten"}],
        },
    }


def test_schema_documents_are_valid_draft_2020_12():
    catalogue = schemas.schema_catalogue()
    assert len(catalogue) == 6
    for item in catalogue:
        schema = schemas.load_schema(item["skill"])
        assert schema["$schema"].endswith("2020-12/schema")
        Draft202012Validator.check_schema(schema)


def test_valid_payloads_pass():
    for skill, payload in valid_payloads().items():
        assert schemas.validate_payload(skill, payload) == [], skill


def test_analysis_error_has_targeted_pointer():
    issues = schemas.validate_payload("data-analyse", [{"op": "period_series", "value": "Amount"}])
    assert any(item["path"] == "/0" and "date_col" in item["message"] for item in issues), issues


def test_unknown_operation_and_field_are_rejected():
    issues = schemas.validate_payload("data-analyse", [{"op": "forecast", "column": "Amount"}])
    assert issues and any("forecast" in item["message"] for item in issues)
    tidy_issues = schemas.validate_payload("data-tidy", {"columns": [{"source": "A", "target": "B", "type": "money"}]})
    assert tidy_issues and any("money" in item["message"] for item in tidy_issues)


def test_extended_analyse_ops_validate_and_require_fields():
    ok = [
        {"op": "pivot", "rows_col": "Region", "cols_col": "Product", "value": "Amount"},
        {"op": "rolling", "date_col": "Date", "value": "Amount", "window": 3, "func": "mean"},
        {"op": "join_on", "on": ["SKU", "Week"], "how": "left"},
        {"op": "compare_series", "left": {"date_col": "Date", "value": "Amount"},
         "right": {"date_col": "Week", "value": "Price"}},
        {"op": "gini", "column": "Share"},
        {"op": "seasonality", "date_col": "Date", "value": "Amount", "grain": "quarter"},
    ]
    assert schemas.validate_payload("data-analyse", ok) == []
    missing = schemas.validate_payload("data-analyse", [{"op": "concentration"}])
    assert missing and any("column" in item["message"] or "by" in item["message"] for item in missing)
    bad_roll = schemas.validate_payload("data-analyse", [{"op": "rolling", "date_col": "Date"}])
    assert any("window" in item["message"] for item in bad_roll)
    bad_season = schemas.validate_payload(
        "data-analyse", [{"op": "seasonality", "date_col": "Date", "grain": "year"}]
    )
    assert bad_season


def test_plan_validation_runs_schema_before_source():
    plan = {
        "version": 1, "skill": "data-analyse", "input": "missing.csv",
        "operations": [{"op": "ageing", "date_col": "Due date"}],
        "output": "out.json", "approval": {"confirmed": True},
    }
    result = ar.validate_plan(plan, check_sources=False)
    assert result["status"] == "error", result
    assert any("as_of" in error for error in result["errors"]), result
    assert result["details"]["spec_validation"]["schema"].endswith("analysis-plan.schema.json")


def test_conversion_card_validation():
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        card = td / "card.md"
        card.write_text("# Card\n\n```convert-spec\n" + json.dumps(valid_payloads()["data-convert"]) + "\n```\n", encoding="utf-8")
        result = ar.validate_spec_file("data-convert", card, base_dir=td)
        assert result["status"] == "success", result


def test_conversion_card_json_fence_validation():
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        card = td / "card.md"
        card.write_text("# Card\n\n```json\n" + json.dumps(valid_payloads()["data-convert"]) + "\n```\n", encoding="utf-8")
        result = ar.validate_spec_file("data-convert", card, base_dir=td)
        assert result["status"] == "success", result


def test_extract_fields_json_path_validates_and_runs():
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        source = td / "form.txt"
        fields = td / "fields.json"
        output = td / "extracted.xlsx"
        direct_output = td / "direct-extracted.xlsx"
        source.write_text("Investor: Acme Capital\n", encoding="utf-8")
        fields.write_text(json.dumps(valid_payloads()["data-extract"]), encoding="utf-8")
        plan = {
            "version": 1,
            "skill": "data-extract",
            "input": str(source),
            "mode": "fields",
            "fields": str(fields),
            "output": str(output),
            "approval": {"confirmed": True},
        }
        original_fields = plan["fields"]
        validation = ar.validate_plan(plan, base_dir=td)
        assert not validation["errors"], validation
        assert plan["fields"] == original_fields, plan

        direct_plan = {**plan, "output": str(direct_output)}
        direct = ar._run_extract(direct_plan, td, dry_run=False)
        assert direct["status"] == "success", direct
        assert direct_output.exists(), direct
        assert direct_plan["fields"] == original_fields, direct_plan

        result = ar.run_plan(plan, base_dir=td)
        assert result["status"] == "success", result
        assert output.exists(), result
        assert plan["fields"] == original_fields, plan


def test_cli_validate_spec_and_error_code():
    cli = ROOT / "bin" / "data-toolkit"
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        good = td / "analysis.json"
        bad = td / "bad.json"
        good.write_text(json.dumps(valid_payloads()["data-analyse"]), encoding="utf-8")
        bad.write_text(json.dumps([{"op": "period_series"}]), encoding="utf-8")
        ok = subprocess.run([sys.executable, str(cli), "validate-spec", "data-analyse", str(good)], text=True, capture_output=True)
        assert ok.returncode == 0 and json.loads(ok.stdout)["status"] == "success", ok.stderr
        failed = subprocess.run([sys.executable, str(cli), "validate-spec", "data-analyse", str(bad)], text=True, capture_output=True)
        payload = json.loads(failed.stdout)
        assert failed.returncode == 1 and payload["status"] == "error"
        assert any("date_col" in item for item in payload["errors"])


def test_cli_json_report_is_persistent():
    cli = ROOT / "bin" / "data-toolkit"
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        spec = td / "fields.json"
        report = td / "reports" / "validation.json"
        spec.write_text(json.dumps(valid_payloads()["data-extract"]), encoding="utf-8")
        raw = subprocess.check_output([
            sys.executable, str(cli), "validate-spec", "data-extract", str(spec),
            "--json-report", str(report),
        ], text=True)
        stdout_result = json.loads(raw)
        saved = json.loads(report.read_text(encoding="utf-8"))
        assert report.exists() and saved["status"] == "success"
        assert saved["details"]["json_report"] == str(report.resolve())
        assert stdout_result == saved


def test_cli_schema_catalogue_and_document():
    cli = ROOT / "bin" / "data-toolkit"
    catalogue = json.loads(subprocess.check_output([sys.executable, str(cli), "schema"], text=True))
    assert len(catalogue["details"]["catalogue"]) == 6
    assert catalogue["details"]["example"]["version"] == 1
    document = json.loads(subprocess.check_output([sys.executable, str(cli), "schema", "data-tidy"], text=True))
    assert document["details"]["schema"]["title"] == "Data Tidy recipe"


def main():
    tests = [
        ("schema documents", test_schema_documents_are_valid_draft_2020_12),
        ("valid payloads", test_valid_payloads_pass),
        ("targeted analysis pointer", test_analysis_error_has_targeted_pointer),
        ("unknown operation and field", test_unknown_operation_and_field_are_rejected),
        ("plan schema validation", test_plan_validation_runs_schema_before_source),
        ("conversion card", test_conversion_card_validation),
        ("conversion card JSON fence", test_conversion_card_json_fence_validation),
        ("extract fields JSON path", test_extract_fields_json_path_validates_and_runs),
        ("CLI validate-spec", test_cli_validate_spec_and_error_code),
        ("CLI JSON report", test_cli_json_report_is_persistent),
        ("CLI schema catalogue", test_cli_schema_catalogue_and_document),
    ]
    passed = sum(1 for name, fn in tests if check(name, fn))
    print(f"agent schemas: {passed}/{len(tests)} passed")
    if passed != len(tests):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
