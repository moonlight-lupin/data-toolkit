#!/usr/bin/env python3
"""Schema catalogue and validation helpers for agent-facing Data Toolkit specs."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_DIR = ROOT / "schemas"
SCHEMA_FILES = {
    "data-extract": "extraction-fields.schema.json",
    "data-tidy": "tidy-recipe.schema.json",
    "data-reconcile": "reconciliation-config.schema.json",
    "data-analyse": "analysis-plan.schema.json",
    "data-visualise": "dashboard-spec.schema.json",
    "data-convert": "conversion-spec.schema.json",
}


class SchemaSpecError(ValueError):
    pass


def schema_path(skill: str) -> Path:
    try:
        return SCHEMA_DIR / SCHEMA_FILES[skill]
    except KeyError as exc:
        raise SchemaSpecError(f"unsupported schema skill: {skill}") from exc


def load_schema(skill: str) -> dict[str, Any]:
    path = schema_path(skill)
    return json.loads(path.read_text(encoding="utf-8"))


def schema_catalogue() -> list[dict[str, str]]:
    return [
        {"skill": skill, "path": str(schema_path(skill).relative_to(ROOT)),
         "title": load_schema(skill).get("title", skill)}
        for skill in sorted(SCHEMA_FILES)
    ]


def _pointer(parts: list[Any]) -> str:
    if not parts:
        return "/"
    return "/" + "/".join(str(part).replace("~", "~0").replace("/", "~1") for part in parts)


def validate_payload(skill: str, payload: Any) -> list[dict[str, Any]]:
    validator = Draft202012Validator(load_schema(skill))
    errors = []
    for error in sorted(validator.iter_errors(payload), key=lambda e: (list(e.absolute_path), e.message)):
        errors.append({
            "path": _pointer(list(error.absolute_path)),
            "message": error.message,
            "validator": error.validator,
            "schema_path": _pointer(list(error.absolute_schema_path)),
        })
    return errors


def render_errors(skill: str, errors: list[dict[str, Any]]) -> list[str]:
    return [f"{skill} spec {item['path']}: {item['message']}" for item in errors]


def _load_json_file(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except FileNotFoundError as exc:
        raise SchemaSpecError(f"spec not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise SchemaSpecError(f"invalid JSON in spec {path}: {exc}") from exc


def _load_conversion_card(path: Path) -> dict[str, Any]:
    try:
        text = path.read_text(encoding="utf-8-sig")
    except FileNotFoundError as exc:
        raise SchemaSpecError(f"spec not found: {path}") from exc
    match = re.search(r"```(?:convert-spec|json)\s*\n(.*?)\n```", text, flags=re.DOTALL)
    if not match:
        raise SchemaSpecError(f"conversion card has no ```convert-spec (or ```json) block: {path}")
    try:
        value = json.loads(match.group(1))
    except json.JSONDecodeError as exc:
        raise SchemaSpecError(f"invalid embedded conversion spec in {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise SchemaSpecError("embedded conversion spec must be a JSON object")
    return value


def load_spec_value(value: Any, *, base_dir: str | Path | None = None,
                    conversion_card: bool = False) -> Any:
    if isinstance(value, (dict, list)):
        return value
    if not isinstance(value, str):
        raise SchemaSpecError("spec must be an inline object/list or a JSON file path")
    base = Path(base_dir) if base_dir else Path.cwd()
    path = Path(value)
    if not path.is_absolute():
        path = (base / path).resolve()
    if conversion_card and path.suffix.lower() == ".md":
        return _load_conversion_card(path)
    return _load_json_file(path)


def plan_payload(plan: dict[str, Any], *, base_dir: str | Path | None = None) -> tuple[str, Any] | None:
    skill = plan.get("skill")
    if skill == "data-extract":
        if plan.get("mode", "fields") == "fields":
            payload = load_spec_value(plan.get("fields"), base_dir=base_dir)
            # run_plan validates before dispatch. Canonicalise a referenced field list in
            # memory so execution consumes the exact payload that passed schema validation.
            if isinstance(plan.get("fields"), str):
                plan["fields"] = payload
            return skill, payload
        if plan.get("recipe") is not None:
            return "data-tidy", load_spec_value(plan.get("recipe"), base_dir=base_dir)
        return None
    if skill == "data-tidy":
        return skill, load_spec_value(plan.get("recipe"), base_dir=base_dir)
    if skill == "data-reconcile":
        return skill, plan.get("options") or {}
    if skill == "data-analyse":
        return skill, plan.get("operations")
    if skill == "data-visualise":
        return skill, plan.get("dashboard")
    if skill == "data-convert":
        return skill, load_spec_value(plan.get("spec"), base_dir=base_dir, conversion_card=True)
    return None


def validate_plan_payload(plan: dict[str, Any], *, base_dir: str | Path | None = None) -> dict[str, Any]:
    selected = plan_payload(plan, base_dir=base_dir)
    if selected is None:
        return {"skill": plan.get("skill"), "schema": None, "errors": []}
    skill, payload = selected
    errors = validate_payload(skill, payload)
    return {
        "skill": skill,
        "schema": str(schema_path(skill).relative_to(ROOT)),
        "errors": errors,
        "payload": payload,
    }
