#!/usr/bin/env python3
"""Public, hardened agent API layered over :mod:`agent_runtime`.

`agent_runtime` contains the six engine adapters. This module is the stable surface used by
the CLI and integration suite; it tightens source validation, dry-run filesystem semantics,
explicit multi-source conversion and declarative dashboard RAG rules without changing the
legacy skill engines.
"""
from __future__ import annotations

import copy
import os
import traceback
from pathlib import Path
from typing import Any

import agent_runtime as _base

PLAN_VERSION = _base.PLAN_VERSION
SUPPORTED_SKILLS = _base.SUPPORTED_SKILLS
PlanError = _base.PlanError
Table = _base.Table
envelope = _base.envelope
read_table = _base.read_table
table_matrix = _base.table_matrix
inspect_source = _base.inspect_source
load_plan = _base.load_plan
plan_schema = _base.plan_schema

_BASE_VALIDATE = _base.validate_plan
_BASE_RUN_CONVERT = _base._run_convert
_BASE_VIZ_BLOCK = _base._viz_block


def _resolve_source_path(source: str | dict[str, Any], base: Path) -> Path:
    if isinstance(source, str):
        source = {"path": source}
    if not isinstance(source, dict) or not source.get("path"):
        raise PlanError("each input must be a path string or an object containing path")
    path = Path(source["path"])
    return path if path.is_absolute() else (base / path).resolve()


def _set_validation_status(result: dict[str, Any]) -> dict[str, Any]:
    if result.get("errors"):
        result["status"] = "error"
    elif result.get("approvals_required"):
        result["status"] = "needs_approval"
    elif result.get("warnings"):
        result["status"] = "success_with_warnings"
    else:
        result["status"] = "success"
    return result


def validate_plan(plan: dict[str, Any], *, base_dir: str | Path | None = None,
                  check_sources: bool = True) -> dict[str, Any]:
    """Validate shape/approval, then inspect sources using the correct source semantics.

    Fields-mode extraction consumes document-shaped inputs. Its validation therefore checks
    existence only; the extraction engine performs PDF/DOCX/MSG capability and OCR checks.
    Other skills retain table-aware validation.
    """
    base = Path(base_dir) if base_dir else Path.cwd()
    result = _BASE_VALIDATE(plan, base_dir=base, check_sources=False)
    if not check_sources or result.get("errors"):
        return result

    skill = plan.get("skill")
    inputs = _base._normalise_inputs(plan)
    warnings = list(result.get("warnings") or [])
    errors = list(result.get("errors") or [])
    for source in inputs:
        try:
            if skill == "data-extract" and plan.get("mode", "fields") == "fields":
                path = _resolve_source_path(source, base)
                if not path.exists():
                    raise PlanError(f"input not found: {path}")
                continue
            info = read_table(source, base_dir=base)
            if not info.header:
                warnings.append(f"{info.path}: no columns detected")
            if not info.rows:
                warnings.append(f"{info.path}: no data rows detected")
        except Exception as exc:
            errors.append(str(exc))
    result["warnings"] = warnings
    result["errors"] = errors
    return _set_validation_status(result)


def _output_path_without_side_effect(plan: dict[str, Any], base: Path, default_name: str) -> Path:
    output = plan.get("output")
    if isinstance(output, dict):
        output = output.get("path")
    path = Path(output or default_name)
    return path if path.is_absolute() else (base / path).resolve()


# Engine adapters call this helper before deciding whether they are in a dry run. Removing the
# implicit mkdir lets the public run_plan control exactly when a filesystem change is allowed.
_base._output_path = _output_path_without_side_effect


def _load_convert_spec_for_guard(plan: dict[str, Any], base: Path) -> dict[str, Any]:
    spec, _ = _base._load_convert_spec(plan.get("spec"), base_dir=base)
    return spec


def _run_convert(plan: dict[str, Any], base: Path, dry_run: bool) -> dict[str, Any]:
    spec = _load_convert_spec_for_guard(plan, base)
    inputs = _base._normalise_inputs(plan)
    if len(inputs) > 1:
        union_op = next((op for op in spec.get("reshape", []) if op.get("op") == "union"), None)
        union_option = (plan.get("options") or {}).get("union")
        if union_op is None and union_option is None:
            raise PlanError("multiple conversion inputs require an explicit union operation or options.union")
        how = (union_op or {}).get("how", union_option or "outer")
        if how not in ("outer", "inner"):
            raise PlanError("union mode must be 'outer' or 'inner'")

    result = _BASE_RUN_CONVERT(plan, base, dry_run)
    # A reshape-only job deliberately passes every source column through. The legacy contract
    # checker reports those columns as informationally "unmapped" because no mapping exists;
    # remove that noise while retaining all genuine mapping warnings and errors.
    if not spec.get("map"):
        result["warnings"] = [item for item in (result.get("warnings") or [])
                              if not (isinstance(item, dict) and item.get("kind") == "unmapped_source")]
        report = (result.get("details") or {}).get("report")
        if isinstance(report, dict):
            report["issues"] = [item for item in (report.get("issues") or [])
                                if item.get("kind") != "unmapped_source"]
        if result.get("status") == "success_with_warnings" and not result["warnings"]:
            result["status"] = "success"
    return result


_base.RUNNERS["data-convert"] = _run_convert


def _rag_callable(rule: dict[str, Any]):
    mapping = rule.get("map", rule)
    default = rule.get("default") if "map" in rule else None
    return lambda value: mapping.get(str(value), default)


def _viz_block(viz: Any, spec: dict[str, Any], source_rows: list[dict[str, Any]]) -> str:
    if spec.get("type") == "table" and spec.get("rag"):
        adjusted = copy.copy(spec)
        rag: dict[str, Any] = {}
        for column, rule in spec["rag"].items():
            if callable(rule):
                rag[column] = rule
            elif isinstance(rule, dict):
                rag[column] = _rag_callable(rule)
            else:
                raise PlanError(f"table RAG rule for {column!r} must be a mapping")
        adjusted["rag"] = rag
        return _BASE_VIZ_BLOCK(viz, adjusted, source_rows)
    return _BASE_VIZ_BLOCK(viz, spec, source_rows)


# section/grid recursion in the base renderer resolves this global at call time.
_base._viz_block = _viz_block


def _prepare_output_parent(plan: dict[str, Any], base: Path) -> None:
    output = plan.get("output")
    if isinstance(output, dict):
        output = output.get("path")
    if not output:
        return
    path = Path(output)
    if not path.is_absolute():
        path = (base / path).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)


def run_plan(plan: dict[str, Any], *, base_dir: str | Path | None = None,
             dry_run: bool = False) -> dict[str, Any]:
    """Run a plan with approval, source-warning and filesystem guarantees."""
    base = Path(base_dir) if base_dir else Path.cwd()
    validation = validate_plan(plan, base_dir=base, check_sources=True)
    if validation.get("errors"):
        return validation
    if validation.get("approvals_required") and not dry_run:
        return validation
    skill = plan["skill"]
    try:
        if not dry_run:
            _prepare_output_parent(plan, base)
        result = _base.RUNNERS[skill](plan, base, dry_run)
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


# base.main resolves these names in its own module globals.
_base.validate_plan = validate_plan
_base.run_plan = run_plan
main = _base.main


if __name__ == "__main__":
    raise SystemExit(main())
