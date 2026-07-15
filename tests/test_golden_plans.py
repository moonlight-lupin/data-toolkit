"""Golden-plan smoke test + the extract fields-as-a-file-path regression.

Runs the committed golden plans through the runtime (so a break in the runtime or any skill
engine fails CI), and locks the fix that lets `_run_extract` resolve a `fields` file path at
run time without depending on a prior validate() call.
"""
import importlib.util
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import agent_runtime as ar  # noqa: E402

GOLDEN = ROOT / "examples" / "golden-plans"


def test_golden_plans_all_pass():
    spec = importlib.util.spec_from_file_location("run_golden", GOLDEN / "run_golden_plans.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert mod.main() == 0, "one or more golden plans failed"


def test_extract_fields_from_file_path_at_run_time():
    # `fields` given as a .json PATH must work at run time on its own — not only after validate()
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        (td / "doc.txt").write_text("Investor: Acme\nAmount: GBP 100\n", encoding="utf-8")
        (td / "fields.json").write_text(
            json.dumps([{"name": "Investor", "labels": ["investor"], "type": "text"}]),
            encoding="utf-8",
        )
        plan = {
            "version": 1, "skill": "data-extract", "input": "doc.txt",
            "mode": "fields", "fields": "fields.json",
            "output": "out.xlsx", "approval": {"confirmed": True},
        }
        result = ar.run_plan(plan, base_dir=td)   # deliberately no validate() first
        assert result["status"] in ("success", "success_with_warnings"), result
        assert (td / "out.xlsx").exists()
