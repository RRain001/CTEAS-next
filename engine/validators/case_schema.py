from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from engine.core.paths import config_path


SCHEMA_PATH = config_path("case.schema.yaml")


class CaseSchemaError(ValueError):
    pass


def _require_mapping(value: Any, field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise CaseSchemaError(f"{field} must be a mapping")
    return value


def validate_case_config(config: dict[str, Any]) -> None:
    schema = yaml.safe_load(SCHEMA_PATH.read_text(encoding="utf-8")) or {}

    for key in schema.get("required_top_level", []):
        if key not in config:
            raise CaseSchemaError(f"Missing top-level field: {key}")

    schema_version = config.get("schema_version")
    if schema_version != schema.get("schema_version"):
        raise CaseSchemaError(
            f"schema_version mismatch: got {schema_version}, expected {schema.get('schema_version')}"
        )

    paths = _require_mapping(config.get("paths"), "paths")
    settings = _require_mapping(config.get("settings"), "settings")
    preprocess = _require_mapping(config.get("preprocess"), "preprocess")
    met = _require_mapping(config.get("met"), "met")
    puff = _require_mapping(config.get("puff"), "puff")

    for key in schema.get("required_paths", []):
        if key not in paths:
            raise CaseSchemaError(f"Missing paths.{key}")
    for key in schema.get("required_settings", []):
        if key not in settings:
            raise CaseSchemaError(f"Missing settings.{key}")
    for key in schema.get("required_preprocess", []):
        if key not in preprocess:
            raise CaseSchemaError(f"Missing preprocess.{key}")
    for key in schema.get("required_met", []):
        if key not in met:
            raise CaseSchemaError(f"Missing met.{key}")
    for key in schema.get("required_puff", []):
        if key not in puff:
            raise CaseSchemaError(f"Missing puff.{key}")


def validate_case_yaml(path: Path) -> dict[str, Any]:
    config = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(config, dict):
        raise CaseSchemaError(f"case.yaml must be a mapping: {path}")
    validate_case_config(config)
    return config
