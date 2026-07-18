#!/usr/bin/env python3
"""Unified, agent-facing runtime for Data Toolkit.

The runtime gives AI agents one stable interface across the six skills:

    python bin/data-toolkit inspect SOURCE
    python bin/data-toolkit validate PLAN.json
    python bin/data-toolkit run PLAN.json [--dry-run]

Every command writes one JSON envelope to stdout. Engines remain deterministic and
local; this module only normalises plans, source ingestion, approvals, warnings and
artefact reporting so an agent does not need to improvise glue code.
"""
from __future__ import annotations

import argparse
import copy
import datetime as dt
import hashlib
import hmac
import json
import os
import sys
import traceback
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SHARED = ROOT / "scripts"
SKILL_SCRIPTS = {
    "data-reconcile": ROOT / "skills" / "data-reconcile" / "scripts",
    "data-analyse": ROOT / "skills" / "data-analyse" / "scripts",
    "data-visualise": ROOT / "skills" / "data-visualise" / "scripts",
    "data-convert": ROOT / "skills" / "data-convert" / "scripts",
}
SUPPORTED_SKILLS = {
    "data-extract", "data-tidy", "data-reconcile",
    "data-analyse", "data-visualise", "data-convert",
}
PLAN_VERSION = 1

for p in [SHARED, *SKILL_SCRIPTS.values()]:
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))


class PlanError(ValueError):
    pass


@dataclass
class Table:
    header: list[str]
    rows: list[dict[str, Any]]
    note: str
    path: str


def _json_default(value: Any):
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (dt.date, dt.datetime)):
        return value.isoformat()
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, set):
        return sorted(value, key=str)
    if hasattr(value, "__dict__"):
        return value.__dict__
    return str(value)


def _clean_for_json(value: Any):
    return json.loads(json.dumps(value, default=_json_default))


def _canonical_json(value: Any) -> bytes:
    return json.dumps(_clean_for_json(value), sort_keys=True, separators=(",", ":")).encode("utf-8")


def _sha256_json(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value)).hexdigest()


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _approval_key(value: str | bytes | None = None) -> bytes | None:
    """Resolve the verifier/signing key without putting it in the plan.

    Production orchestration should expose the key only to the human/operator approval
    process, not to the agent process. The runtime can verify with an explicitly supplied
    key, ``DATA_TOOLKIT_APPROVAL_KEY``, or ``DATA_TOOLKIT_APPROVAL_KEY_FILE``.
    """
    if isinstance(value, bytes):
        return value
    if isinstance(value, str):
        return value.encode("utf-8")
    env = os.environ.get("DATA_TOOLKIT_APPROVAL_KEY")
    if env:
        return env.encode("utf-8")
    key_file = os.environ.get("DATA_TOOLKIT_APPROVAL_KEY_FILE")
    if key_file:
        return Path(key_file).expanduser().read_bytes().strip()
    return None


def _resolved_source_path(source: str | dict[str, Any], base: Path) -> Path:
    if isinstance(source, str):
        source = {"path": source}
    if not isinstance(source, dict) or not source.get("path"):
        raise PlanError("each input must be a path string or an object containing path")
    path = Path(source["path"])
    return path if path.is_absolute() else (base / path).resolve()


def _approval_plan_view(plan: dict[str, Any]) -> dict[str, Any]:
    """Plan material bound into secondary approval requests.

    Receipts and legacy decision booleans/lists are excluded so an agent cannot change the
    request by merely copying the eventual signed decision into the plan.
    """
    view = copy.deepcopy(plan)
    view.pop("approval_receipts", None)
    view.pop("accepted_aggregations", None)
    options = view.get("options")
    if isinstance(options, dict):
        options.pop("allow_drift", None)
    return view


def _source_evidence(plan: dict[str, Any], base: Path) -> list[dict[str, Any]]:
    evidence = []
    for source in _normalise_inputs(plan):
        path = _resolved_source_path(source, base)
        item = {"path": str(path), "sha256": _file_sha256(path)}
        for key in ("sheet", "json_path"):
            if source.get(key) is not None:
                item[key] = source[key]
        evidence.append(item)
    return evidence


def build_approval_request(*, kind: str, plan: dict[str, Any], base: Path,
                           message: str, context: dict[str, Any],
                           decision_schema: dict[str, Any]) -> dict[str, Any]:
    body = {
        "version": 1,
        "kind": kind,
        "message": message,
        "plan_sha256": _sha256_json(_approval_plan_view(plan)),
        "sources": _source_evidence(plan, base),
        "context": context,
        "decision_schema": decision_schema,
    }
    return {**body, "request_id": _sha256_json(body)}


def sign_approval_receipt(request: dict[str, Any], decision: dict[str, Any], *,
                          approved_by: str, key: str | bytes,
                          issued_at: str | None = None) -> dict[str, Any]:
    """Create a receipt for an external/operator approval process.

    The signing key must be withheld from the AI agent for this to represent a human-bound
    control. The runtime only verifies receipts; plan fields alone never satisfy a secondary
    gate.
    """
    key_bytes = _approval_key(key)
    if not key_bytes:
        raise PlanError("approval signing key is empty")
    receipt = {
        "version": 1,
        "kind": request["kind"],
        "request_id": request["request_id"],
        "decision": _clean_for_json(decision),
        "approved_by": str(approved_by).strip(),
        "issued_at": issued_at or dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
    }
    if not receipt["approved_by"]:
        raise PlanError("approved_by is required")
    receipt["signature"] = hmac.new(key_bytes, _canonical_json(receipt), hashlib.sha256).hexdigest()
    return receipt


def verify_approval_receipt(receipt: dict[str, Any], request: dict[str, Any], *,
                            key: str | bytes | None = None) -> tuple[bool, str]:
    key_bytes = _approval_key(key)
    if not key_bytes:
        return False, "approval verification key is not configured"
    if not isinstance(receipt, dict):
        return False, "receipt is not an object"
    if receipt.get("version") != 1:
        return False, "receipt version must be 1"
    if receipt.get("kind") != request.get("kind") or receipt.get("request_id") != request.get("request_id"):
        return False, "receipt does not match this approval request"
    signature = receipt.get("signature")
    if not isinstance(signature, str):
        return False, "receipt signature is missing"
    unsigned = dict(receipt)
    unsigned.pop("signature", None)
    expected = hmac.new(key_bytes, _canonical_json(unsigned), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(signature, expected):
        return False, "receipt signature is invalid"
    if not receipt.get("approved_by"):
        return False, "receipt approved_by is missing"
    return True, "verified"


def _matching_receipt(plan: dict[str, Any], request: dict[str, Any], *,
                      key: str | bytes | None = None) -> tuple[dict[str, Any] | None, str]:
    receipts = plan.get("approval_receipts") or []
    if not isinstance(receipts, list):
        return None, "approval_receipts must be a list"
    last_reason = "no matching approval receipt supplied"
    for receipt in receipts:
        if isinstance(receipt, dict) and receipt.get("request_id") == request.get("request_id"):
            valid, reason = verify_approval_receipt(receipt, request, key=key)
            if valid:
                return receipt, reason
            last_reason = reason
    return None, last_reason


def envelope(*, status: str, skill: str | None = None, action: str | None = None,
             artifacts: list[dict[str, Any]] | None = None,
             warnings: list[Any] | None = None, errors: list[Any] | None = None,
             approvals_required: list[Any] | None = None,
             metrics: dict[str, Any] | None = None,
             details: dict[str, Any] | None = None) -> dict[str, Any]:
    return _clean_for_json({
        "schema_version": PLAN_VERSION,
        "status": status,
        "skill": skill,
        "action": action,
        "artifacts": artifacts or [],
        "warnings": warnings or [],
        "errors": errors or [],
        "approvals_required": approvals_required or [],
        "metrics": metrics or {},
        "details": details or {},
    })


def _resolve_json_path(value: Any, path: str | None) -> Any:
    if not path:
        return value
    cur = value
    for part in path.split("."):
        if isinstance(cur, list):
            try:
                cur = cur[int(part)]
            except (ValueError, IndexError) as exc:
                raise PlanError(f"JSON path {path!r} failed at list segment {part!r}") from exc
        elif isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            raise PlanError(f"JSON path {path!r} failed at segment {part!r}")
    return cur


def _records_from_json(value: Any, *, json_path: str | None = None) -> tuple[list[str], list[dict[str, Any]], str]:
    value = _resolve_json_path(value, json_path)
    auto_path = None
    if isinstance(value, dict) and json_path is None:
        list_fields = [(k, v) for k, v in value.items() if isinstance(v, list)]
        if len(list_fields) == 1 and all(isinstance(x, dict) for x in list_fields[0][1]):
            auto_path, value = list_fields[0]
    if isinstance(value, dict):
        records = [value]
    elif isinstance(value, list) and all(isinstance(x, dict) for x in value):
        records = value
    else:
        raise PlanError("JSON tabular input must be an object or a list of objects; use json_path for a nested record list")
    header: list[str] = []
    for rec in records:
        for key in rec:
            key = str(key)
            if key not in header:
                header.append(key)
    rows = [{key: rec.get(key, "") for key in header} for rec in records]
    note = f"JSON, {len(rows)} record(s)"
    if json_path:
        note += f" at {json_path}"
    elif auto_path:
        note += f" (auto-selected sole record list {auto_path!r})"
    return header, rows, note


def _raw_to_records(raw: Any) -> tuple[list[str], list[dict[str, Any]]]:
    """Convert shared ingest's raw matrix to header + dict rows."""
    rows = raw[0] if isinstance(raw, tuple) else raw
    rows = list(rows or [])
    if not rows:
        return [], []
    try:
        import dataclean
        header_row = dataclean.detect_header(rows)
    except Exception:
        header_row = 0
    header = ["" if c is None else str(c).strip() for c in rows[header_row]]
    body = []
    for source_row in rows[header_row + 1:]:
        source_row = list(source_row) + [None] * max(0, len(header) - len(source_row))
        body.append({header[i]: source_row[i] for i in range(len(header))})
    return header, body


def read_table(source: str | dict[str, Any], *, base_dir: str | Path | None = None) -> Table:
    if isinstance(source, str):
        source = {"path": source}
    if not isinstance(source, dict) or not source.get("path"):
        raise PlanError("each input must be a path string or an object containing path")
    base = Path(base_dir) if base_dir else Path.cwd()
    path = Path(source["path"])
    if not path.is_absolute():
        path = (base / path).resolve()
    if not path.exists():
        raise PlanError(f"input not found: {path}")
    ext = path.suffix.lower()
    if ext == ".json":
        try:
            value = json.loads(path.read_text(encoding="utf-8-sig"))
        except json.JSONDecodeError as exc:
            raise PlanError(f"invalid JSON in {path}: {exc}") from exc
        header, rows, note = _records_from_json(value, json_path=source.get("json_path"))
    else:
        import ingest
        raw, note = ingest.read_any(str(path), sheet=source.get("sheet"))
        header, rows = _raw_to_records(raw)
    return Table(header=header, rows=rows, note=note, path=str(path))


def table_matrix(table: Table) -> list[list[Any]]:
    return [table.header] + [[row.get(col, "") for col in table.header] for row in table.rows]


def inspect_source(source: str | dict[str, Any], *, base_dir: str | Path | None = None,
                   sample_rows: int = 5) -> dict[str, Any]:
    table = read_table(source, base_dir=base_dir)
    return envelope(
        status="success", action="inspect",
        metrics={"rows": len(table.rows), "columns": len(table.header)},
        details={
            "path": table.path,
            "note": table.note,
            "columns": table.header,
            "sample": table.rows[:max(0, sample_rows)],
        },
    )


def load_plan(path: str | Path) -> tuple[dict[str, Any], Path]:
    plan_path = Path(path).resolve()
    try:
        plan = json.loads(plan_path.read_text(encoding="utf-8-sig"))
    except FileNotFoundError as exc:
        raise PlanError(f"plan not found: {plan_path}") from exc
    except json.JSONDecodeError as exc:
        raise PlanError(f"invalid plan JSON: {exc}") from exc
    if not isinstance(plan, dict):
        raise PlanError("plan root must be a JSON object")
    return plan, plan_path


def _normalise_inputs(plan: dict[str, Any]) -> list[dict[str, Any]]:
    inputs = plan.get("inputs")
    if inputs is None and plan.get("input") is not None:
        inputs = [plan["input"]]
    if not isinstance(inputs, list):
        return []
    return [x if isinstance(x, dict) else {"path": x} for x in inputs]


def _load_json_or_inline(value: Any, *, base_dir: Path) -> Any:
    if isinstance(value, dict) or isinstance(value, list):
        return value
    if not isinstance(value, str):
        raise PlanError("expected an inline object/list or a JSON file path")
    p = Path(value)
    if not p.is_absolute():
        p = (base_dir / p).resolve()
    return json.loads(p.read_text(encoding="utf-8-sig"))


def _load_convert_spec(value: Any, *, base_dir: Path) -> tuple[dict[str, Any], Path]:
    if isinstance(value, dict):
        return copy.deepcopy(value), base_dir
    if not isinstance(value, str):
        raise PlanError("data-convert requires spec as an object, .json path or conversion-card .md path")
    p = Path(value)
    if not p.is_absolute():
        p = (base_dir / p).resolve()
    if p.suffix.lower() == ".md":
        import convert
        return convert.load_spec(str(p)), p.parent
    return json.loads(p.read_text(encoding="utf-8-sig")), p.parent


def validate_plan(plan: dict[str, Any], *, base_dir: str | Path | None = None,
                  check_sources: bool = True) -> dict[str, Any]:
    base = Path(base_dir) if base_dir else Path.cwd()
    errors: list[str] = []
    warnings: list[str] = []
    approvals: list[dict[str, Any]] = []
    version = plan.get("version", plan.get("schema_version"))
    if version != PLAN_VERSION:
        errors.append(f"version must be {PLAN_VERSION}")
    skill = plan.get("skill")
    if skill not in SUPPORTED_SKILLS:
        errors.append(f"skill must be one of {sorted(SUPPORTED_SKILLS)}")
    inputs = _normalise_inputs(plan)
    if skill != "data-visualise" and not inputs:
        errors.append("at least one input is required")
    if skill == "data-reconcile" and len(inputs) != 2:
        errors.append("data-reconcile requires exactly two inputs")
    if skill == "data-convert" and not plan.get("spec"):
        errors.append("data-convert requires spec")
    if skill == "data-analyse" and not isinstance(plan.get("operations"), list):
        errors.append("data-analyse requires an operations list")
    if skill == "data-tidy" and not plan.get("recipe"):
        errors.append("data-tidy requires recipe")
    if skill == "data-extract" and plan.get("mode", "fields") not in ("fields", "table"):
        errors.append("data-extract mode must be fields or table")
    if skill == "data-extract" and plan.get("mode", "fields") == "fields" and not plan.get("fields"):
        errors.append("data-extract fields mode requires fields")
    if skill == "data-visualise" and not isinstance(plan.get("dashboard"), dict):
        errors.append("data-visualise requires dashboard object")
    output = plan.get("output")
    if skill in SUPPORTED_SKILLS and not output:
        errors.append("output is required")
    approval = plan.get("approval") or {}
    if skill in {"data-tidy", "data-extract", "data-reconcile", "data-analyse", "data-convert"} \
            and not approval.get("confirmed"):
        approvals.append({
            "kind": "plan_confirmation",
            "message": "Confirm the proposed plan/spec before the engine writes an output.",
        })
    options = plan.get("options") or {}
    if isinstance(options, dict) and "allow_drift" in options:
        warnings.append("options.allow_drift is ignored; source drift requires a signed approval receipt")
    spec_validation = None
    if not errors:
        try:
            import agent_schemas
            spec_validation = agent_schemas.validate_plan_payload(plan, base_dir=base)
            errors.extend(agent_schemas.render_errors(
                spec_validation.get("skill") or str(skill), spec_validation.get("errors") or []
            ))
        except Exception as exc:
            errors.append(str(exc))
    if check_sources and not errors:
        analysis_input = (
            skill == "data-visualise"
            and _dashboard_needs_analysis((plan.get("dashboard") or {}).get("blocks"))
        )
        for source in inputs:
            try:
                if skill == "data-extract" and plan.get("mode", "fields") == "fields":
                    path = _resolved_source_path(source, base)
                    if not path.exists():
                        raise PlanError(f"input not found: {path}")
                    continue
                if analysis_input:
                    _load_analysis_json(source, base or Path.cwd())
                    continue
                info = read_table(source, base_dir=base)
                if not info.header:
                    warnings.append(f"{info.path}: no columns detected")
                if not info.rows:
                    warnings.append(f"{info.path}: no data rows detected")
            except Exception as exc:
                errors.append(str(exc))
    status = "error" if errors else ("needs_approval" if approvals else ("success_with_warnings" if warnings else "success"))
    schema_details = None
    if spec_validation:
        schema_details = {
            "skill": spec_validation.get("skill"),
            "schema": spec_validation.get("schema"),
            "errors": spec_validation.get("errors") or [],
        }
    return envelope(status=status, skill=skill, action="validate", warnings=warnings,
                    errors=errors, approvals_required=approvals,
                    details={"inputs": inputs, "output": output,
                             "spec_validation": schema_details})


def _output_path(plan: dict[str, Any], base: Path, default_name: str) -> Path:
    output = plan.get("output")
    if isinstance(output, dict):
        output = output.get("path")
    path = Path(output or default_name)
    return path if path.is_absolute() else (base / path).resolve()


def _prepare_write(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def _run_analyse(plan: dict[str, Any], base: Path, dry_run: bool,
              approval_key: str | bytes | None = None) -> dict[str, Any]:
    import analyse
    table = read_table(_normalise_inputs(plan)[0], base_dir=base)
    header = table.header
    rows = [[row.get(c, "") for c in header] for row in table.rows]
    results: list[dict[str, Any]] = []
    warnings: list[str] = []
    allowed = {"numeric_summary", "outliers_iqr", "breakdown", "period_series", "ageing", "currency_mix"}
    for i, op in enumerate(plan.get("operations", [])):
        if not isinstance(op, dict) or op.get("op") not in allowed:
            raise PlanError(f"operations[{i}].op must be one of {sorted(allowed)}")
        name = op["op"]
        if name == "numeric_summary":
            result = analyse.numeric_summary(analyse.column(header, rows, op["column"]))
        elif name == "outliers_iqr":
            result = analyse.outliers_iqr(analyse.column(header, rows, op["column"]),
                                          k=Decimal(str(op.get("k", "1.5"))), cap=int(op.get("cap", 10)))
        elif name == "breakdown":
            result = analyse.breakdown(header, rows, op["by"], value=op.get("value"),
                                       top=int(op.get("top", 10)))
        elif name == "period_series":
            result = analyse.period_series(header, rows, op["date_col"], value=op.get("value"),
                                           grain=op.get("grain", "month"), dayfirst=op.get("dayfirst", True))
        elif name == "ageing":
            result = analyse.ageing(header, rows, op["date_col"], as_of=op["as_of"],
                                    buckets=tuple(op.get("buckets", [30, 60, 90])), value=op.get("value"),
                                    dayfirst=op.get("dayfirst", True))
        else:
            values = analyse.column(header, rows, op["column"])
            result = {"currencies": sorted(x for x in analyse.currency_mix(values) if x is not None)}
        results.append({"name": op.get("name", name), "op": name, "result": result})
    output = _output_path(plan, base, "analysis.json")
    if not dry_run:
        _prepare_write(output)
        output.write_text(json.dumps(_clean_for_json({"source": table.path, "results": results}), indent=2),
                          encoding="utf-8")
    return envelope(status="success_with_warnings" if warnings else "success", skill="data-analyse",
                    action="dry-run" if dry_run else "run",
                    artifacts=[] if dry_run else [{"path": str(output), "kind": "analysis_metrics"}],
                    warnings=warnings, metrics={"rows_in": len(table.rows), "operations": len(results)},
                    details={"source": table.path, "results": results})


def _run_convert(plan: dict[str, Any], base: Path, dry_run: bool,
              approval_key: str | bytes | None = None) -> dict[str, Any]:
    import convert
    spec, spec_base = _load_convert_spec(plan.get("spec"), base_dir=base)
    inputs = _normalise_inputs(plan)
    tables = [read_table(source, base_dir=base) for source in inputs]
    if len(tables) > 1:
        union_op = next((o for o in spec.get("reshape", []) if o.get("op") == "union"), None)
        union_option = (plan.get("options") or {}).get("union")
        if union_op is None and union_option is None:
            raise PlanError("multiple conversion inputs require an explicit union operation or options.union")
        how = (union_op or {}).get("how", union_option or "outer")
        if how not in ("outer", "inner"):
            raise PlanError("union mode must be 'outer' or 'inner'")
        header, rows = convert.union([(t.header, t.rows) for t in tables], how=how)
        source_note = f"union({how}) of {len(tables)} sources"
    else:
        header, rows = tables[0].header, tables[0].rows
        source_note = tables[0].note
    drift = convert.sense_check(spec, header, rows, run_dates_after=(plan.get("options") or {}).get("as_of"))
    if drift:
        request = build_approval_request(
            kind="source_drift", plan=plan, base=base,
            message="Source differs from the conversion card. Approve this exact drift before writing output.",
            context={"source": source_note, "sense_check": drift},
            decision_schema={"allow_drift": True},
        )
        receipt, receipt_reason = _matching_receipt(plan, request, key=approval_key)
        if receipt is None or receipt.get("decision") != {"allow_drift": True}:
            return envelope(status="needs_approval", skill="data-convert",
                            action="dry-run" if dry_run else "run", warnings=drift,
                            approvals_required=[request],
                            details={"source": source_note, "sense_check": drift,
                                     "receipt_status": receipt_reason})
    lookups = convert.load_lookups(spec.get("map", {}), base_dir=str(spec_base))
    target_header, target_rows, report = convert.convert_rows(spec, header, rows, lookups=lookups)
    report["sense_check"] = drift
    issues = report.get("issues") or []
    if not spec.get("map"):
        issues = [x for x in issues if x.get("kind") != "unmapped_source"]
        report["issues"] = issues
    errors = [x for x in issues if x.get("severity") == "error"]
    if errors:
        return envelope(status="error", skill="data-convert", action="dry-run" if dry_run else "run",
                        warnings=drift + [x for x in issues if x.get("severity") != "error"], errors=errors,
                        metrics={"rows_in": report.get("rows_in"), "rows_out": report.get("rows_out")},
                        details={"report": report})
    output = _output_path(plan, base, "converted.csv")
    artifacts: list[dict[str, Any]] = []
    if not dry_run:
        _prepare_write(output)
        split_op = next((o for o in spec.get("reshape", []) if o.get("op") == "split"), None)
        nest_op = next((o for o in spec.get("reshape", []) if o.get("op") == "nest"), None)
        if nest_op:
            kwargs = {k: v for k, v in nest_op.items() if k != "op"}
            nested = convert.nest(target_header, target_rows, **kwargs)
            output = output.with_suffix(".json")
            output.write_text(json.dumps(nested, indent=2, default=_json_default), encoding="utf-8")
            artifacts.append({"path": str(output), "kind": "converted_json"})
        elif split_op:
            for key, (part_header, part_rows) in convert.split(target_header, target_rows, split_op["by"]).items():
                import re
                safe = re.sub(r"[^\w.-]+", "_", str(key)) or "blank"
                part_path = output.with_name(f"{output.stem}_{safe}{output.suffix}")
                written = convert.write_output(part_header, part_rows, spec.get("target"), part_path,
                                               base_dir=str(spec_base))
                artifacts.append({"path": str(written), "kind": "converted_part"})
        else:
            written = convert.write_output(target_header, target_rows, spec.get("target"), output,
                                           base_dir=str(spec_base))
            artifacts.append({"path": str(written), "kind": "converted_output"})
    status = "success_with_warnings" if drift or issues else "success"
    return envelope(status=status, skill="data-convert", action="dry-run" if dry_run else "run",
                    artifacts=artifacts, warnings=drift + issues,
                    metrics={"rows_in": report.get("rows_in"), "rows_out": report.get("rows_out"),
                             "sources": len(tables)}, details={"source": source_note, "report": report})


def _run_tidy(plan: dict[str, Any], base: Path, dry_run: bool,
              approval_key: str | bytes | None = None) -> dict[str, Any]:
    import dataclean
    table = read_table(_normalise_inputs(plan)[0], base_dir=base)
    recipe = _load_json_or_inline(plan["recipe"], base_dir=base)
    masters = plan.get("masters") or {}
    header, rows, log = dataclean.apply_recipe(table_matrix(table), recipe, masters=masters)
    output = _output_path(plan, base, "clean.xlsx")
    report_path = output.with_suffix(".report.md")
    artifacts = []
    if not dry_run:
        _prepare_write(output)
        dataclean.write_xlsx(header, rows, str(output))
        report_path.write_text(dataclean.render_report(log), encoding="utf-8")
        artifacts = [{"path": str(output), "kind": "clean_table"},
                     {"path": str(report_path), "kind": "change_report"}]
    warnings = log.get("flagged", []) if isinstance(log, dict) else []
    return envelope(status="success_with_warnings" if warnings else "success", skill="data-tidy",
                    action="dry-run" if dry_run else "run", artifacts=artifacts, warnings=warnings,
                    metrics={"rows_in": len(table.rows), "rows_out": len(rows)}, details={"log": log})


def _run_extract(plan: dict[str, Any], base: Path, dry_run: bool,
              approval_key: str | bytes | None = None) -> dict[str, Any]:
    import dataclean
    import extract
    inputs = _normalise_inputs(plan)
    mode = plan.get("mode", "fields")
    output = _output_path(plan, base, "extracted.xlsx")
    report_path = output.with_suffix(".report.md")
    artifacts = []
    warnings: list[Any] = []
    if mode == "fields":
        # Resolve fields here (inline list or a .json path) so a run does not depend on a
        # validate-time cache having populated it — mirrors how _run_convert loads its spec.
        fields = _load_json_or_inline(plan["fields"], base_dir=base)
        records, flags_list = [], []
        for source in inputs:
            p = Path(source["path"])
            if not p.is_absolute():
                p = (base / p).resolve()
            record, flags = extract.extract_fields(str(p), fields)
            records.append(record)
            flags_list.append(flags)
            warnings.extend(flags or [])
        header, rows = extract.fields_to_table(records, extract.field_columns(fields))
        report = extract.render_fields_report(records, flags_list)
    else:
        if len(inputs) != 1:
            raise PlanError("table extraction requires exactly one input")
        p = Path(inputs[0]["path"])
        if not p.is_absolute():
            p = (base / p).resolve()
        raw = extract.get_table(str(p), page=int(plan["page"]), index=int(plan.get("index", 0)))
        if plan.get("recipe"):
            recipe = _load_json_or_inline(plan["recipe"], base_dir=base)
            header, rows, log = dataclean.apply_recipe(raw, recipe)
            warnings = log.get("flagged", [])
            report = dataclean.render_report(log)
        else:
            header, dict_rows = _raw_to_records(raw)
            rows = [[r.get(c, "") for c in header] for r in dict_rows]
            report = f"Extracted {len(rows)} row(s) from page {plan['page']}, table {plan.get('index', 0)}."
    if not dry_run:
        _prepare_write(output)
        dataclean.write_xlsx(header, rows, str(output))
        report_path.write_text(report, encoding="utf-8")
        artifacts = [{"path": str(output), "kind": "extracted_table"},
                     {"path": str(report_path), "kind": "extraction_report"}]
    return envelope(status="success_with_warnings" if warnings else "success", skill="data-extract",
                    action="dry-run" if dry_run else "run", artifacts=artifacts, warnings=warnings,
                    metrics={"rows_out": len(rows)}, details={"report": report})


def _run_reconcile(plan: dict[str, Any], base: Path, dry_run: bool,
              approval_key: str | bytes | None = None) -> dict[str, Any]:
    import reconcile
    inputs = _normalise_inputs(plan)
    options = dict(plan.get("options") or {})
    preset = options.get("preset")
    cfg = dict(reconcile.PRESETS.get(preset, {})) if preset else {}
    cfg.update({k: v for k, v in options.items() if v is not None})
    tables = [read_table(source, base_dir=base) for source in inputs]
    rows_a, rows_b = tables[0].rows, tables[1].rows
    result = reconcile.match(
        rows_a, rows_b,
        key=cfg.get("key"), amount=cfg.get("amount", "amount"), date=cfg.get("date"),
        currency=cfg.get("currency"), mode=cfg.get("mode", "key"),
        tol=cfg.get("tol", 0.01),
        date_window_days=cfg.get("date_window", 5),
        strict_currency=cfg.get("strict_currency", False),
        debit=cfg.get("debit"), credit=cfg.get("credit"), flip_b=cfg.get("flip_b", False),
    )
    proposals = []
    if cfg.get("aggregate"):
        proposals = reconcile.propose_aggregations(
            result, group_col=cfg.get("group_col"), party_col=cfg.get("party_col"),
            date_window=cfg.get("date_window"), tol=cfg.get("tol", 0.01),
        )
    a_label = plan.get("a_label", cfg.get("a_label", "A"))
    b_label = plan.get("b_label", cfg.get("b_label", "B"))
    accepted_assertion = plan.get("accepted_aggregations", None)
    aggregation_warning = None
    if proposals:
        public_proposals = [{k: v for k, v in proposal.items() if not str(k).startswith("_")}
                            for proposal in proposals]
        request = build_approval_request(
            kind="aggregation_proposals", plan=plan, base=base,
            message="Review the aggregation proposals and sign the exact accepted index list, including [] to reject all.",
            context={"proposals": public_proposals, "a_label": a_label, "b_label": b_label},
            decision_schema={"accepted_aggregations": "list[int]"},
        )
        receipt, receipt_reason = _matching_receipt(plan, request, key=approval_key)
        decision = receipt.get("decision") if receipt else None
        accepted = decision.get("accepted_aggregations") if isinstance(decision, dict) else None
        valid_selection = (isinstance(accepted, list) and
                           all(isinstance(i, int) and not isinstance(i, bool) for i in accepted) and
                           len(set(accepted)) == len(accepted) and
                           all(0 <= i < len(proposals) for i in accepted))
        if receipt is None or not valid_selection:
            reason = receipt_reason if receipt is None else "receipt decision must contain unique in-range integer indexes"
            return envelope(status="needs_approval", skill="data-reconcile",
                            action="dry-run" if dry_run else "run",
                            approvals_required=[request],
                            details={"proposals": public_proposals,
                                     "proposal_text": reconcile.render_proposals(proposals, a_label=a_label, b_label=b_label),
                                     "receipt_status": reason})
        if accepted_assertion is not None and accepted_assertion != accepted:
            raise PlanError("accepted_aggregations does not match the signed receipt decision")
        reconcile.apply_aggregations(result, proposals, accepted=accepted)
    elif accepted_assertion is not None:
        aggregation_warning = "accepted_aggregations was supplied but no aggregation proposals were generated"
    exceptions, summary = reconcile.finalize(
        result, a_label=a_label, b_label=b_label,
        material=cfg.get("material", 1000), escalate=cfg.get("escalate", 10000),
        as_of=cfg.get("as_of"),
    )
    balances = []
    for label, rows, opening, closing in (
        (a_label, rows_a, cfg.get("opening_a"), cfg.get("closing_a")),
        (b_label, rows_b, cfg.get("opening_b"), cfg.get("closing_b")),
    ):
        if opening is not None or closing is not None:
            balances.append((label, reconcile.check_balance(
                rows, amount=cfg.get("amount", "amount"), debit=cfg.get("debit"),
                credit=cfg.get("credit"), opening=opening, closing=closing,
            )))
    if balances:
        summary["balance_checks"] = balances
    output = _output_path(plan, base, "reconciliation.xlsx")
    artifacts = []
    if not dry_run:
        _prepare_write(output)
        reconcile.write_workpaper(result, exceptions, summary, str(output),
                                  a_label=a_label, b_label=b_label)
        artifacts = [{"path": str(output), "kind": "reconciliation_workpaper"}]
    warnings = list(summary.get("warnings", [])) if isinstance(summary, dict) else []
    if aggregation_warning:
        warnings.append(aggregation_warning)
    return envelope(status="success_with_warnings" if warnings or exceptions else "success",
                    skill="data-reconcile", action="dry-run" if dry_run else "run",
                    artifacts=artifacts, warnings=warnings,
                    metrics={"matched": summary.get("matched"), "exceptions": len(exceptions)},
                    details={"summary": summary, "sources": [t.path for t in tables]})


def _resolve_data(value: Any, source_rows: list[dict[str, Any]]) -> Any:
    if value == "$source":
        return source_rows
    return value


def _rag_callable(rule: dict[str, Any]):
    mapping = rule.get("map", rule)
    default = rule.get("default") if "map" in rule else None
    return lambda value: mapping.get(str(value), default)


def _load_analysis_json(source: dict[str, Any] | str, base: Path) -> dict[str, Any]:
    path = Path(source["path"] if isinstance(source, dict) else source)
    if not path.is_absolute():
        path = (base / path).resolve()
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise PlanError(f"could not read analysis.json at {path}: {exc}") from exc
    if isinstance(payload, dict) and isinstance(payload.get("results"), list):
        return payload
    if isinstance(payload, list):
        return {"results": payload}
    raise PlanError("analysis input must be analysis.json with a results list")


def _dashboard_needs_analysis(blocks: Any) -> bool:
    if blocks == "$analysis":
        return True
    if not isinstance(blocks, list):
        return False
    for block in blocks:
        if isinstance(block, dict) and block.get("type") == "from_analysis":
            return True
        if isinstance(block, dict) and block.get("type") in {"section", "grid"}:
            if _dashboard_needs_analysis(block.get("blocks", [])):
                return True
    return False


def _visualise_format(plan: dict[str, Any]) -> str:
    fmt = str(plan.get("format") or "").strip().lower()
    if fmt in {"html", "xlsx"}:
        return fmt
    output = plan.get("output") or ""
    if isinstance(output, dict):
        output = output.get("path") or ""
    suffix = Path(str(output)).suffix.lower()
    if suffix in {".xlsx", ".xlsm"}:
        return "xlsx"
    return "html"


def _expand_viz_blocks(viz: Any, blocks: Any, analysis: dict[str, Any] | None) -> list[dict[str, Any]]:
    if blocks == "$analysis":
        if analysis is None:
            raise PlanError("blocks=$analysis requires an analysis.json input")
        return viz.suggest_blocks_from_analysis(analysis)
    if not isinstance(blocks, list):
        raise PlanError("dashboard.blocks must be an array or \"$analysis\"")
    expanded: list[dict[str, Any]] = []
    for block in blocks:
        if not isinstance(block, dict):
            raise PlanError("dashboard blocks must be objects")
        if block.get("type") == "from_analysis":
            if analysis is None:
                raise PlanError("from_analysis requires an analysis.json input")
            expanded.extend(viz.suggest_blocks_from_analysis(
                analysis, ops=block.get("ops"), max_groups=int(block.get("max_groups", 10)),
            ))
            continue
        if block.get("type") in {"section", "grid"}:
            child = dict(block)
            child["blocks"] = _expand_viz_blocks(viz, block.get("blocks", []), analysis)
            expanded.append(child)
            continue
        expanded.append(block)
    return expanded


def _expand_chart_specs(workbook: Any, blocks: Any, analysis: dict[str, Any] | None) -> list[dict[str, Any]]:
    """Expand dashboard.blocks into Excel chart specs for workbook.py."""
    if blocks == "$analysis":
        if analysis is None:
            raise PlanError("blocks=$analysis requires an analysis.json input")
        return workbook.suggest_charts_from_analysis(analysis)
    if not isinstance(blocks, list):
        raise PlanError("dashboard.blocks must be an array or \"$analysis\"")
    charts: list[dict[str, Any]] = []
    for i, block in enumerate(blocks):
        if not isinstance(block, dict):
            raise PlanError(f"dashboard.blocks[{i}] must be an object")
        kind = block.get("type")
        if kind == "from_analysis":
            if analysis is None:
                raise PlanError("from_analysis requires an analysis.json input")
            charts.extend(workbook.suggest_charts_from_analysis(
                analysis, ops=block.get("ops"), max_groups=int(block.get("max_groups", 12)),
            ))
            continue
        if kind == "chart":
            spec = {k: v for k, v in block.items() if k != "type"}
            if "chart_type" not in spec and "type" not in spec:
                raise PlanError(f"dashboard.blocks[{i}] chart requires chart_type")
            charts.append(spec)
            continue
        if kind in {"section", "grid"}:
            charts.extend(_expand_chart_specs(workbook, block.get("blocks", []), analysis))
            continue
        raise PlanError(
            f"dashboard.blocks[{i}] type {kind!r} is HTML-only; "
            "use type 'chart' / 'from_analysis' / '$analysis' for format=xlsx"
        )
    return charts


def _viz_block(viz: Any, spec: dict[str, Any], source_rows: list[dict[str, Any]]) -> str:
    kind = spec.get("type")
    if kind == "kpi_row":
        return viz.kpi_row(spec.get("items", []))
    if kind == "bar_chart":
        return viz.bar_chart(_resolve_data(spec.get("data", []), source_rows),
                             title=spec.get("title"), unit=spec.get("unit", ""))
    if kind == "line_chart":
        return viz.line_chart(_resolve_data(spec.get("data", []), source_rows),
                              title=spec.get("title"), unit=spec.get("unit", ""),
                              toggle=spec.get("toggle", False))
    if kind == "donut_chart":
        return viz.donut_chart(_resolve_data(spec.get("data", []), source_rows),
                               title=spec.get("title"), centre=spec.get("centre"))
    if kind == "heatmap":
        return viz.heatmap(spec.get("matrix", []), row_labels=spec.get("row_labels"),
                           col_labels=spec.get("col_labels"), title=spec.get("title"),
                           scale=spec.get("scale", "sequential"), mid=spec.get("mid", 0),
                           unit=spec.get("unit", ""))
    if kind == "sparkline":
        return viz.sparkline(_resolve_data(spec.get("data", []), source_rows),
                             title=spec.get("title"), show_last=spec.get("show_last", True),
                             unit=spec.get("unit", ""))
    if kind == "waterfall":
        return viz.waterfall(spec.get("steps", []), title=spec.get("title"),
                             unit=spec.get("unit", ""))
    if kind == "table":
        rag = {}
        for column_name, rule in (spec.get("rag") or {}).items():
            if callable(rule):
                rag[column_name] = rule
            elif isinstance(rule, dict):
                rag[column_name] = _rag_callable(rule)
            else:
                raise PlanError(f"table RAG rule for {column_name!r} must be a mapping")
        return viz.table(_resolve_data(spec.get("rows", "$source"), source_rows),
                         columns=spec.get("columns"), title=spec.get("title"),
                         rag=rag, sortable=spec.get("sortable", False),
                         filter_by=spec.get("filter_by"))
    if kind == "section":
        children = [_viz_block(viz, child, source_rows) for child in spec.get("blocks", [])]
        return viz.section(spec.get("title", ""), *children)
    if kind == "grid":
        children = [_viz_block(viz, child, source_rows) for child in spec.get("blocks", [])]
        return viz.grid(*children, cols=int(spec.get("cols", 2)))
    raise PlanError(f"unsupported dashboard block type: {kind!r}")


def _run_visualise(plan: dict[str, Any], base: Path, dry_run: bool,
              approval_key: str | bytes | None = None) -> dict[str, Any]:
    import viz
    fmt = _visualise_format(plan)
    inputs = _normalise_inputs(plan)
    dash = plan["dashboard"]
    raw_blocks = dash.get("blocks", [])
    analysis = None
    source_rows: list[dict[str, Any]] = []
    if _dashboard_needs_analysis(raw_blocks):
        if not inputs:
            raise PlanError("$analysis / from_analysis requires an analysis.json input")
        analysis = _load_analysis_json(inputs[0], base)
    elif inputs and fmt == "html":
        source_rows = read_table(inputs[0], base_dir=base).rows

    if fmt == "xlsx":
        import workbook
        chart_specs = _expand_chart_specs(workbook, raw_blocks, analysis)
        if not chart_specs:
            raise PlanError("xlsx visualise produced no charts — provide chart blocks or chartable analysis ops")
        output = _output_path(plan, base, "charts.xlsx")
        artifacts = []
        if not dry_run:
            _prepare_write(output)
            workbook.write_charts_xlsx(
                output, chart_specs, workbook_title=dash.get("title"),
                theme=dash.get("theme"),   # brand the workbook like the HTML dashboard
            )
            artifacts = [{"path": str(output), "kind": "xlsx_charts"}]
        return envelope(
            status="success", skill="data-visualise", action="dry-run" if dry_run else "run",
            artifacts=artifacts,
            metrics={"format": "xlsx", "charts": len(chart_specs),
                     "from_analysis": bool(analysis)},
            details={"title": dash.get("title"),
                     "chart_types": [c.get("chart_type") for c in chart_specs]},
        )

    theme = dash.get("theme")
    viz.apply_theme(theme)
    block_specs = _expand_viz_blocks(viz, raw_blocks, analysis)
    blocks = [_viz_block(viz, block, source_rows) for block in block_specs]
    output = _output_path(plan, base, "dashboard.html")
    artifacts = []
    if not dry_run:
        _prepare_write(output)
        viz.dashboard(dash.get("title", "Dashboard"), blocks,
                      subtitle=dash.get("subtitle"), as_of=dash.get("as_of"),
                      out_path=str(output), footnote=dash.get("footnote"), theme=theme)
        artifacts = [{"path": str(output), "kind": "html_dashboard"}]
    return envelope(status="success", skill="data-visualise", action="dry-run" if dry_run else "run",
                    artifacts=artifacts,
                    metrics={"format": "html", "blocks": len(blocks), "source_rows": len(source_rows),
                             "from_analysis": bool(analysis)},
                    details={"title": dash.get("title"),
                             "block_types": [b.get("type") for b in block_specs]})


RUNNERS = {
    "data-tidy": _run_tidy,
    "data-extract": _run_extract,
    "data-reconcile": _run_reconcile,
    "data-analyse": _run_analyse,
    "data-visualise": _run_visualise,
    "data-convert": _run_convert,
}


def run_plan(plan: dict[str, Any], *, base_dir: str | Path | None = None,
             dry_run: bool = False, approval_key: str | bytes | None = None) -> dict[str, Any]:
    base = Path(base_dir) if base_dir else Path.cwd()
    validation = validate_plan(plan, base_dir=base, check_sources=True)
    if validation["errors"]:
        return validation
    if validation["approvals_required"] and not dry_run:
        return validation
    skill = plan["skill"]
    try:
        result = RUNNERS[skill](plan, base, dry_run, approval_key=approval_key)
        if validation.get("warnings"):
            result["warnings"] = list(validation["warnings"]) + list(result.get("warnings") or [])
            if result.get("status") == "success":
                result["status"] = "success_with_warnings"
        return result
    except Exception as exc:
        details = {"exception": type(exc).__name__}
        if os.environ.get("DATA_TOOLKIT_DEBUG"):
            details["traceback"] = traceback.format_exc()
        return envelope(status="error", skill=skill, action="dry-run" if dry_run else "run",
                        errors=[str(exc)], details=details)


def validate_spec_file(skill: str, spec: str | Path, *,
                       base_dir: str | Path | None = None) -> dict[str, Any]:
    import agent_schemas
    base = Path(base_dir) if base_dir else Path.cwd()
    payload = agent_schemas.load_spec_value(
        str(spec), base_dir=base, conversion_card=(skill == "data-convert")
    )
    issues = agent_schemas.validate_payload(skill, payload)
    errors = agent_schemas.render_errors(skill, issues)
    return envelope(
        status="error" if errors else "success", skill=skill, action="validate-spec",
        errors=errors,
        details={
            "schema": str(agent_schemas.schema_path(skill).relative_to(ROOT)),
            "spec": str(spec),
            "issues": issues,
        },
    )


def schema_catalogue() -> list[dict[str, str]]:
    import agent_schemas
    return agent_schemas.schema_catalogue()


def schema_document(skill: str) -> dict[str, Any]:
    import agent_schemas
    return agent_schemas.load_schema(skill)


def _write_json_report(path: str | Path, value: Any, *, pretty: bool = True) -> Path:
    report = Path(path).expanduser()
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(
        json.dumps(_clean_for_json(value), indent=2 if pretty else None,
                   separators=None if pretty else (",", ":")) + "\n",
        encoding="utf-8",
    )
    return report


def plan_schema() -> dict[str, Any]:
    return {
        "version": PLAN_VERSION,
        "skill": "data-convert",
        "inputs": [{"path": "source.json", "json_path": "records"}],
        "spec": "convert_source_to_target.md",
        "output": {"path": "out/target.csv"},
        "options": {"as_of": "2026-07-15"},
        "approval": {"confirmed": False, "confirmed_by": None},
        "approval_receipts": [],
    }


def _print(value: Any, pretty: bool = True) -> None:
    print(json.dumps(_clean_for_json(value), indent=2 if pretty else None,
                     separators=None if pretty else (",", ":")))


def _approval_request_from_file(path: str | Path) -> dict[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    if isinstance(value, dict) and value.get("request_id") and value.get("kind"):
        return value
    requests = value.get("approvals_required") if isinstance(value, dict) else None
    if isinstance(requests, list):
        concrete = [item for item in requests if isinstance(item, dict) and item.get("request_id")]
        if len(concrete) == 1:
            return concrete[0]
    raise PlanError("approval request file must contain one concrete request with request_id")


def _parse_accepted(value: str) -> list[int]:
    if value.strip().lower() in {"none", "reject", "[]"}:
        return []
    try:
        accepted = [int(part.strip()) for part in value.split(",") if part.strip()]
    except ValueError as exc:
        raise PlanError("--accept must be comma-separated integer indexes or 'none'") from exc
    if len(set(accepted)) != len(accepted):
        raise PlanError("--accept indexes must be unique")
    return accepted


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Unified agent-facing interface for Data Toolkit")
    parser.add_argument("--compact", action="store_true", help="emit compact JSON")
    sub = parser.add_subparsers(dest="command", required=True)
    def add_report_arg(command_parser):
        command_parser.add_argument(
            "--json-report", metavar="PATH",
            help="also write the complete result envelope to PATH",
        )

    p_inspect = sub.add_parser("inspect", help="inspect one source and return structured metadata")
    p_inspect.add_argument("source")
    p_inspect.add_argument("--sheet")
    p_inspect.add_argument("--json-path")
    p_inspect.add_argument("--sample-rows", type=int, default=5)
    add_report_arg(p_inspect)
    p_validate = sub.add_parser("validate", help="validate an agent plan and its declarative spec")
    p_validate.add_argument("plan")
    p_validate.add_argument("--no-source-check", action="store_true")
    add_report_arg(p_validate)
    p_validate_spec = sub.add_parser("validate-spec", help="validate one declarative spec against its skill schema")
    p_validate_spec.add_argument("skill", choices=sorted(SUPPORTED_SKILLS))
    p_validate_spec.add_argument("spec")
    add_report_arg(p_validate_spec)
    p_run = sub.add_parser("run", help="run an approved agent plan")
    p_run.add_argument("plan")
    p_run.add_argument("--dry-run", action="store_true")
    add_report_arg(p_run)
    p_approve = sub.add_parser("approve", help="sign one secondary approval request in an operator shell")
    p_approve.add_argument("request")
    p_approve.add_argument("--by", required=True)
    decision = p_approve.add_mutually_exclusive_group(required=True)
    decision.add_argument("--allow-drift", action="store_true")
    decision.add_argument("--accept", metavar="INDEXES", help="comma-separated aggregation indexes, or 'none'")
    add_report_arg(p_approve)
    p_schema = sub.add_parser("schema", help="print the schema catalogue or one skill schema")
    p_schema.add_argument("skill", nargs="?", choices=sorted(SUPPORTED_SKILLS))
    add_report_arg(p_schema)
    args = parser.parse_args(argv)
    try:
        if args.command == "inspect":
            result = inspect_source({"path": args.source, "sheet": args.sheet, "json_path": args.json_path},
                                    sample_rows=args.sample_rows)
        elif args.command == "schema":
            details = {"example": plan_schema(), "catalogue": schema_catalogue()}
            if args.skill:
                details["skill"] = args.skill
                details["schema"] = schema_document(args.skill)
            result = envelope(status="success", skill=args.skill, action="schema", details=details)
        elif args.command == "validate-spec":
            result = validate_spec_file(args.skill, args.spec, base_dir=Path.cwd())
        elif args.command == "approve":
            if not sys.stdin.isatty():
                raise PlanError("approve requires an interactive operator TTY")
            request = _approval_request_from_file(args.request)
            if args.allow_drift:
                if request.get("kind") != "source_drift":
                    raise PlanError("--allow-drift only applies to a source_drift request")
                decision_value = {"allow_drift": True}
            else:
                if request.get("kind") != "aggregation_proposals":
                    raise PlanError("--accept only applies to an aggregation_proposals request")
                decision_value = {"accepted_aggregations": _parse_accepted(args.accept)}
            challenge = request["request_id"][-8:]
            print(f"Approval: {request.get('message','')}\nRequest: {request['request_id']}", file=sys.stderr)
            typed = input(f"Type APPROVE {challenge}: ").strip()
            if typed != f"APPROVE {challenge}":
                raise PlanError("approval challenge did not match")
            key = _approval_key()
            if not key:
                raise PlanError("set DATA_TOOLKIT_APPROVAL_KEY or DATA_TOOLKIT_APPROVAL_KEY_FILE in the operator shell")
            receipt = sign_approval_receipt(request, decision_value, approved_by=args.by, key=key)
            result = envelope(status="success", action="approve", details={"receipt": receipt})
        else:
            plan, plan_path = load_plan(args.plan)
            if args.command == "validate":
                result = validate_plan(plan, base_dir=plan_path.parent,
                                       check_sources=not args.no_source_check)
            else:
                result = run_plan(plan, base_dir=plan_path.parent, dry_run=args.dry_run)
    except Exception as exc:
        result = envelope(status="error", action=args.command, errors=[str(exc)],
                          details={"exception": type(exc).__name__})
    if getattr(args, "json_report", None):
        try:
            report = _write_json_report(args.json_report, result, pretty=not args.compact)
            result.setdefault("details", {})["json_report"] = str(report.resolve())
            _write_json_report(report, result, pretty=not args.compact)
        except Exception as exc:
            result = envelope(status="error", action=args.command,
                              errors=[f"could not write JSON report: {exc}"],
                              details={"exception": type(exc).__name__, "result": result})
    _print(result, pretty=not args.compact)
    return 0 if result["status"] in {"success", "success_with_warnings", "needs_approval"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
