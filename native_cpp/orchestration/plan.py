"""Fail-closed, read-only S2-2A1 case contract planner.

Only the frozen Hefei 2022 profile can be described. A valid plan never
authorizes execution: P1/P2->P3, P6 and P7 production adapters remain blocked.
No subprocess, file creation, downloads or legacy backend calls.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Any

import yaml

CASE_ID = "hefei5km_2022_reference_case_20261011"
SOURCE_STAGES = (
    ("p1", (), "TERREL original-compatible writer not integrated"),
    ("p2", (), "CTGPROC original-compatible writer not integrated"),
    ("p3", ("p1", "p2"), "Requires validated TERREL.DAT and LU.DAT from native P1/P2"),
    ("p4", (), "Scoped READ62 path not connected to independent run coordinator"),
    ("p5", (), "Scoped SMERGE writer not connected to independent run coordinator"),
    ("p6", ("p3", "p4", "p5"), "2022 scientific driver is not an accepted production adapter"),
    ("p7", ("p6",), "Scoped original comparison driver is not an accepted production adapter"),
)
EXPECTED_MET = {"npsta": 0, "ifradj": 1, "ikine": 0, "iobr": 0, "noobs": 0}
EXPECTED_PUFF = {"nspec": 2, "nse": 1, "mchem": 0, "idry": 0, "iwet": 0, "ndecay": 0}


class ContractError(ValueError):
    """Invalid, unsupported or ambiguous scientific case."""


def mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ContractError(f"{label}: expected mapping")
    return value


def child(data: dict[str, Any], *keys: str) -> Any:
    node: Any = data
    for key in keys:
        node = mapping(node, ".".join(keys)) .get(key)
        if node is None:
            raise ContractError(f"missing {'.'.join(keys)}")
    return node


def numeric(value: Any, label: str) -> float:
    if isinstance(value, bool):
        raise ContractError(f"{label}: boolean cannot be numeric")
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ContractError(f"{label}: invalid number") from exc
    if not math.isfinite(number):
        raise ContractError(f"{label}: non-finite number")
    return number


def eq_number(value: Any, expected: float, label: str, tolerance: float = 1e-9) -> None:
    if abs(numeric(value, label) - expected) > tolerance:
        raise ContractError(f"{label}: outside frozen Hefei support profile")


def check_relative_case_paths(value: Any) -> dict[str, str]:
    paths = mapping(value, "paths")
    if not paths:
        raise ContractError("paths: empty")
    for key, raw in paths.items():
        if not isinstance(key, str) or not isinstance(raw, str) or "\\" in raw:
            raise ContractError("paths: invalid entry")
        posix = PurePosixPath(raw)
        if (not raw.startswith("project/current/") or posix.is_absolute()
                or ".." in posix.parts or "." in posix.parts or len(posix.parts) < 3):
            raise ContractError(f"paths.{key}: path escapes selected case root")
    return dict(sorted(paths.items()))


def validate_frozen_profile(data: dict[str, Any], location: Path) -> dict[str, Any]:
    if child(data, "schema_version") != 1 or isinstance(data["schema_version"], bool):
        raise ContractError("unsupported case schema_version")
    if child(data, "case_name") != CASE_ID or location.parent.name != CASE_ID:
        raise ContractError("case is not the supported frozen Hefei reference profile")
    if child(data, "settings", "timezone") != "UTC+0000":
        raise ContractError("only frozen UTC case timezone is supported")
    paths = check_relative_case_paths(child(data, "paths"))
    grid = mapping(child(data, "preprocess", "grid"), "preprocess.grid")
    for field, expected in (("length_km", 5), ("width_km", 5)):
        eq_number(child(grid, "domain", field), expected, "preprocess.grid.domain." + field)
    eq_number(child(grid, "resolution_km"), 0.1, "preprocess.grid.resolution_km")
    eq_number(child(grid, "nz"), 9, "preprocess.grid.nz")
    eq_number(child(grid, "center", "longitude"), 117.141610855, "grid center longitude")
    eq_number(child(grid, "center", "latitude"), 31.939774444, "grid center latitude")
    times = mapping(child(data, "preprocess", "research_time"), "research_time")
    begin, end = str(child(times, "begin")), str(child(times, "end"))
    for value in (begin, end):
        try:
            dt = datetime.strptime(value, "%Y%m%d-%H%M%S")
        except ValueError as exc:
            raise ContractError("invalid UTC research_time") from exc
        if dt.minute != 0 or dt.second != 0:
            raise ContractError("research_time must be hourly UTC")
    if (begin, end) != ("20220101-000000", "20220106-230000"):
        raise ContractError("research_time outside frozen reference window")
    if child(data, "preprocess", "upperair", "station_id") != "CHM00058424":
        raise ContractError("unsupported upper-air station policy")
    for key, value in EXPECTED_MET.items():
        eq_number(child(data, "met", "options", key), value, "met.options." + key)
    for key, value in EXPECTED_PUFF.items():
        eq_number(child(data, "puff", "options", key), value, "puff.options." + key)
    if child(data, "puff", "options", "source_mode") != "case_yaml":
        raise ContractError("unsupported puff source authority")
    sources = child(data, "puff", "point_sources")
    if not isinstance(sources, list) or len(sources) != 1:
        raise ContractError("only one validated point-source input allowed")
    source = mapping(sources[0], "point_sources[0]")
    if child(source, "name") != "HTO_STACK":
        raise ContractError("source name does not match frozen source profile")
    for key, expected in (("latitude", 31.939774444), ("longitude", 117.141610855),
                          ("stack_height_m", 70.8), ("stack_diameter_m", 1.6),
                          ("exit_velocity_mps", 17.26), ("exit_temp_k", 298.15)):
        eq_number(child(source, key), expected, "puff.source." + key)
    emissions = child(source, "emissions")
    if not isinstance(emissions, list) or len(emissions) != 2:
        raise ContractError("emissions: two frozen species entries required")
    eq_number(emissions[0], 833967.5291730086, "emissions[0]", tolerance=1e-6)
    eq_number(emissions[1], 0, "emissions[1]")
    return {
        "grid": {"crs": "WGS84_UTM50N", "nx": 50, "ny": 50, "nz": 9, "resolution_m": 100,
                 "center_latitude": 31.939774444, "center_longitude": 117.141610855},
        "utc_interval": {"begin": begin, "end": end,
                         "time_semantics": "configured_inclusive_hour_labels_not_143h_acceptance"},
        "station_policy": {"upperair_station": "CHM00058424", "scope": "FROZEN_SINGLE_STATION"},
        "options": {"met": EXPECTED_MET, "puff": EXPECTED_PUFF},
        "path_contract": paths,
    }


def plan_case(case_yaml: Path) -> dict[str, Any]:
    path = Path(case_yaml).expanduser().resolve()
    if not path.is_file():
        raise ContractError(f"case.yaml missing: {path}")
    if path.name != "case.yaml" or not re.fullmatch(r"[A-Za-z0-9_-]+", path.parent.name):
        raise ContractError("only explicitly named case.yaml is allowed")
    raw = path.read_bytes()
    if len(raw) > 131072:
        raise ContractError("case.yaml exceeds bounded parser size")
    try:
        data = mapping(yaml.safe_load(raw), "case.yaml")
    except yaml.YAMLError as exc:
        raise ContractError("case.yaml invalid YAML") from exc
    selected = validate_frozen_profile(data, path)
    return {
        "contract_version": "S2-2A1-READONLY-1",
        "case_name": CASE_ID,
        "case_yaml_sha256": hashlib.sha256(raw).hexdigest(),
        "selected_profile": "HEFEI_2022_SCOPED_CANDIDATE_ONLY",
        "provenance_role": "read_only_planning_not_science_execution",
        "ready": False,
        "status": "DRY_RUN_ONLY_EXECUTION_BLOCKED",
        "dry_run": True,
        "legacy_fallback": False,
        "network_access": False,
        "outputs_published": False,
        "scientific_acceptance": "NOT_EVALUATED_BY_PLANNER",
        **selected,
        "stages": [{"id": name, "dependencies": list(deps), "status": "BLOCKED",
                    "reason": reason, "execute": False}
                   for name, deps, reason in SOURCE_STAGES],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="CTEAS-next read-only scoped native case planner")
    parser.add_argument("--case-yaml", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        print(json.dumps(plan_case(args.case_yaml), indent=2, ensure_ascii=False))
        return 0
    except (ContractError, OSError, UnicodeError) as exc:
        print(json.dumps({"status": "BLOCKED_INVALID_OR_UNSUPPORTED_CASE",
                          "ready": False, "legacy_fallback": False,
                          "error": str(exc)}, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
