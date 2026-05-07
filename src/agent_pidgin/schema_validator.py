from __future__ import annotations

import json
from pathlib import Path
from typing import Any

try:
    from jsonschema import Draft202012Validator, FormatChecker
    from jsonschema.exceptions import ValidationError
except ImportError as exc:  # pragma: no cover - exercised only in incomplete environments
    raise RuntimeError("jsonschema is required for Agent Pidgin schema validation.") from exc

SCHEMA_ROOT = Path(__file__).resolve().parents[2] / "schemas"


def _load_schema(schema_name: str) -> dict[str, Any]:
    with (SCHEMA_ROOT / schema_name).open(encoding="utf-8") as schema_file:
        return json.load(schema_file)


def _validate(payload: dict[str, Any], schema_name: str) -> None:
    validator = Draft202012Validator(_load_schema(schema_name), format_checker=FormatChecker())
    errors = sorted(validator.iter_errors(payload), key=lambda error: list(error.path))
    if errors:
        raise ValueError(_format_error(errors[0])) from errors[0]


def _format_error(error: ValidationError) -> str:
    path = ".".join(str(part) for part in error.path)
    location = path or "<root>"
    return f"Schema validation failed at {location}: {error.message}"


def validate_pidgin_message(payload: dict[str, Any]) -> None:
    _validate(payload, "pidgin-message.schema.json")


def validate_pidgin_handshake(payload: dict[str, Any]) -> None:
    _validate(payload, "pidgin-handshake.schema.json")


def validate_catalog(catalog: dict[str, Any]) -> None:
    _validate(catalog, "pidgin-catalog.schema.json")


def validate_pidgin_trace(payload: dict[str, Any]) -> None:
    _validate(payload, "pidgin-trace.schema.json")
