"""S2-G0: non-Hefei case + genuine-selector manifest handoff (read-only).

This is a scientific *input contract*, NOT a CALMET/CALPUFF executor or
authenticity proof of raw NOAA observations. P6 and P7 remain blocked.
Never mutates project/current, downloads data, or starts a subprocess.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import yaml

from engine.run_met.station_grid import load_strict_utm_grid, lon_lat_in_utm_grid
from .plan import (
    CASE_ID, ContractError, FROZEN_MET_CONTROLS, FROZEN_PUFF_CONTROLS,
    child, mapping, numeric,
)

DAG = (
    ("p1", (), "BLOCKED_NO_GENERAL_TERRAIN_PRODUCER"),
    ("p2", (), "BLOCKED_NO_GENERAL_LANDUSE_PRODUCER"),
    ("p3", ("p1", "p2"), "BLOCKED_NO_GENERAL_GEO_PRODUCER"),
    ("p4", (), "STATION_SELECTION_MANIFEST_SCHEMA_VERIFIED_ONLY"),
    ("p5", (), "STATION_SELECTION_MANIFEST_SCHEMA_VERIFIED_ONLY"),
    ("p6", ("p3", "p4", "p5"), "BLOCKED_FIXED_58424_50X50X9_DRIVER"),
    ("p7", ("p6",), "BLOCKED_NO_GENERAL_PRODUCTION_CONCENTRATION_EXECUTOR"),
)


def _load(path: Path, limit: int = 131072) -> tuple[Any, bytes]:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > limit:
        raise ContractError(f"missing, symlink or oversized input: {path}")
    raw = path.read_bytes()
    try:
        result = yaml.safe_load(raw) if path.suffix in (".yaml", ".yml") else json.loads(raw)
    except (yaml.YAMLError, UnicodeError, ValueError) as exc:
        raise ContractError(f"invalid document: {path}") from exc
    return result, raw


def _finite(value: Any, label: str, minimum: float | None = None) -> float:
    n = numeric(value, label)
    if minimum is not None and n < minimum:
        raise ContractError(f"{label}: below minimum")
    return n


def _int(value: Any, label: str, low: int, high: int) -> int:
    if type(value) is not int or not low <= value <= high:
        raise ContractError(f"{label}: expected integer {low}..{high}")
    return value


def _coords(lat: Any, lon: Any, label: str) -> tuple[float, float]:
    la, lo = _finite(lat, label + ".lat"), _finite(lon, label + ".lon")
    if not -80 <= la <= 84 or not -180 <= lo <= 180:
        raise ContractError(f"{label}: outside WGS84 UTM bounds")
    return la, lo


def _same(a: float, b: float, label: str, tol: float = 1e-7) -> None:
    if abs(a - b) > tol:
        raise ContractError(f"{label}: mismatch with published numeric authority")


def _time(s: Any) -> datetime:
    if not isinstance(s, str) or not re.fullmatch(r"\d{8}-\d{6}", s):
        raise ContractError("research_time must be YYYYMMDD-HHMMSS UTC string")
    try:
        value = datetime.strptime(s, "%Y%m%d-%H%M%S")
    except ValueError as exc:
        raise ContractError("research_time calendar invalid") from exc
    if value.minute != 0 or value.second != 0:
        raise ContractError("research_time must use whole UTC hours")
    return value


def _options(given: Any, expected: dict[str, Any], label: str) -> None:
    data = mapping(given, label)
    if set(data) != set(expected):
        raise ContractError(f"{label}: unsupported option keys or missing controls")
    for key, v in expected.items():
        val = data[key]
        if isinstance(v, bool):
            valid = val is v
        elif isinstance(v, str):
            valid = type(val) is str and val == v
        else:
            valid = type(val) in (int, float) and math.isfinite(val) and val == v
        if not valid:
            raise ContractError(f"{label}.{key}: outside already validated dry/no-chem option profile")


def _geography(case: dict[str, Any], case_yaml: Path):
    grid_file = case_yaml.parent / "grid/grid.cmn"
    if grid_file.is_symlink():
        raise ContractError("grid.cmn symlink forbidden")
    published = grid_file.read_text(encoding="utf-8")
    for label in ("XREFKM", "YREFKM"):
        matches = re.findall(r"!\s*" + label + r"\s*=\s*([^!\s]+)\s*!", published)
        if len(matches) != 1 or re.fullmatch(r"-?\d+\.\d{3}", matches[0]) is None:
            raise ContractError(f"grid.{label} requires precisely 3 decimal places, units km")
    try:
        grid = load_strict_utm_grid(grid_file, context="S2-G0")
    except (ValueError, OSError) as exc:
        raise ContractError(f"grid.cmn invalid: {exc}") from exc
    defined = mapping(child(case, "preprocess", "grid"), "preprocess.grid")
    _int(child(defined, "utm_zone"), "utm_zone", 1, 60)
    if defined["utm_zone"] != grid.iutmzn or child(defined, "hemisphere") != grid.lsohem:
        raise ContractError("case.yaml/grid.cmn UTM hemisphere or zone disagreement")
    _int(child(defined, "nz"), "nz", 1, 100)
    if defined["nz"] != grid.nz:
        raise ContractError("case.yaml/grid.cmn NZ mismatch")
    spacing = _finite(child(defined, "resolution_km"), "resolution_km", 1e-6)
    _same(spacing, grid.dgridkm, "grid spacing")
    x = _finite(child(defined, "domain", "length_km"), "length_km", 1e-6)
    y = _finite(child(defined, "domain", "width_km"), "width_km", 1e-6)
    _same(x, grid.nx * grid.dgridkm, "grid width")
    _same(y, grid.ny * grid.dgridkm, "grid height")
    center = mapping(child(defined, "center"), "preprocess.grid.center")
    lat, lon = _coords(child(center, "latitude"), child(center, "longitude"), "grid.center")
    if not lon_lat_in_utm_grid(lon, lat, grid):
        raise ContractError("grid.center outside authoritative UTM grid")
    return grid, grid_file


def _year_slots(year: int) -> int:
    leap = year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)
    return 732 if leap else 730


def _year_hours(year: int) -> int:
    return _year_slots(year) * 12


def _selection(
    years: list[int], grid: Any, p4_dir: Path, p5_dir: Path,
    stack_lat: float, stack_lon: float,
) -> dict[str, Any]:
    output: dict[str, Any] = {"p4": [], "p5": []}
    alias_index: dict[str, str] = {}
    for year in years:
        p4file = p4_dir / str(year) / "p4_station_selection_audit.json"
        p4, raw4 = _load(p4file, 2_000_000)
        p4 = mapping(p4, "P4 audit")
        if "year" in p4 and p4["year"] != year:
            raise ContractError("P4 audit year mismatch")
        selected4 = child(p4, "selected")
        if not isinstance(selected4, list) or not selected4:
            raise ContractError(f"P4 {year}: no selected station")
        seen4: set[str] = set()
        for s in selected4:
            s = mapping(s, "P4 station")
            sid = child(s, "id")
            if not isinstance(sid, str) or not re.fullmatch(r"[A-Z0-9]{8,20}", sid):
                raise ContractError("P4 station ID malformed")
            if sid in seen4:
                raise ContractError("P4 duplicated selected station identity")
            seen4.add(sid)
            valid = _int(child(s, "valid_original_slots"), "P4 source slots", 0, _year_slots(year))
            if valid * 5 <= 4 * _year_slots(year):
                raise ContractError(f"P4 {year}/{sid}: original source coverage <=80%")
            _same(_finite(child(s, "coverage"), "P4 coverage"),
                  valid / _year_slots(year), "P4 original coverage", 1e-6)
            src = _coords(child(s, "source_lat"), child(s, "source_lon"), "P4 source")
            eff = _coords(child(s, "effective_lat"), child(s, "effective_lon"), "P4 effective")
            kind = child(s, "site_type")
            if kind == "OBSERVED":
                if not lon_lat_in_utm_grid(src[1], src[0], grid):
                    raise ContractError("P4 observed station outside domain")
                _same(src[0], eff[0], "P4 observed lat")
                _same(src[1], eff[1], "P4 observed lon")
            elif kind == "VIRTUAL_RELOCATED":
                if lon_lat_in_utm_grid(src[1], src[0], grid):
                    raise ContractError("P4 virtual source unexpectedly in domain")
                if lon_lat_in_utm_grid(eff[1], eff[0], grid) is False:
                    raise ContractError("P4 relocated effective station outside domain")
                _same(eff[0], stack_lat, "P4 virtual station not at physical stack")
                _same(eff[1], stack_lon, "P4 virtual station not at physical stack")
            else:
                raise ContractError("P4 site_type unsupported")
        output["p4"].append({
            "year": year, "station_ids": sorted(seen4),
            "source_slots": {s["id"]: s["valid_original_slots"] for s in selected4},
            "audit_sha256": hashlib.sha256(raw4).hexdigest(),
        })

        p5file = p5_dir / f"station_selection_{year}.json"
        p5, raw5 = _load(p5file, 2_000_000)
        p5 = mapping(p5, "P5 manifest")
        if child(p5, "year") != year:
            raise ContractError("P5 wrong manifest year")
        mode5 = child(p5, "mode")
        kind5 = child(p5, "station_selection_case")
        selected5 = child(p5, "stations")
        if not isinstance(selected5, list) or not selected5:
            raise ContractError(f"P5 {year}: no selected station")
        expected = _year_hours(year)
        seen5: set[str] = set()
        primaries = 0
        ranks = []
        for s in selected5:
            s = mapping(s, "P5 station")
            sid = child(s, "sid")
            if not isinstance(sid, str) or not re.fullmatch(r"[A-Z0-9]{11}", sid):
                raise ContractError("P5 source station identity invalid")
            if sid in seen5:
                raise ContractError("P5 duplicate station")
            seen5.add(sid)
            alias = child(s, "ifstn")
            if not isinstance(alias, str) or not re.fullmatch(r"\d{6,7}", alias):
                raise ContractError("P5 IFSTN alias malformed")
            if sid in alias_index and alias_index[sid] != alias:
                raise ContractError("P5 IFSTN alias changed between calendar years")
            alias_index[sid] = alias
            count_full = _int(child(s, "full_isd_raw_hours"), "full ISD annual hours", 0, expected)
            count_lite = _int(child(s, "isd_lite_raw_hours"), "ISD-Lite annual hours", 0, expected)
            if child(s, "expected_hours") != expected:
                raise ContractError("P5 original UTC calendar denominator mismatch")
            _same(_finite(child(s, "full_isd_coverage"), "full coverage"),
                  count_full / expected, "P5 original full coverage", 1e-6)
            _same(_finite(child(s, "isd_lite_coverage"), "lite coverage"),
                  count_lite / expected, "P5 original Lite coverage", 1e-6)
            src = _coords(child(s, "source_lat"), child(s, "source_lon"), "P5 source")
            eff = _coords(child(s, "lat"), child(s, "lon"), "P5 effective")
            relocated = child(s, "relocated")
            if type(relocated) is not bool:
                raise ContractError("P5 relocated flag must be boolean")
            if relocated:
                if (lon_lat_in_utm_grid(src[1], src[0], grid)
                        or not lon_lat_in_utm_grid(eff[1], eff[0], grid)
                        or count_full * 10 <= expected * 9
                        or count_lite * 10 <= expected * 9):
                    raise ContractError("P5 virtual fallback invalid location or <=90% original hours")
                _same(eff[0], stack_lat, "P5 virtual station not at physical stack")
                _same(eff[1], stack_lon, "P5 virtual station not at physical stack")
            else:
                if not lon_lat_in_utm_grid(src[1], src[0], grid):
                    raise ContractError("P5 observed source outside domain")
                _same(src[0], eff[0], "P5 in-domain lat")
                _same(src[1], eff[1], "P5 in-domain lon")
            role = child(s, "wind_treatment")
            if role not in ("COMPLETE_FILL_AND_CALM_REPLACE", "RAW_SPARSE_STANDARDIZE_ONLY"):
                raise ContractError("P5 wind treatment invalid")
            if role == "COMPLETE_FILL_AND_CALM_REPLACE":
                primaries += 1
            ranks.append((-count_lite, -count_full, sid))
        if primaries != 1:
            raise ContractError("P5 must have one and only one annual primary")
        primary = child(p5, "primary_sid")
        if not isinstance(primary, str) or primary not in seen5:
            raise ContractError("P5 primary_sid absent from station list")
        if primary != min(ranks)[2]:
            raise ContractError("P5 primary ranking differs from original NOAA Lite/full/ID policy")
        for s in selected5:
            if (s["wind_treatment"] == "COMPLETE_FILL_AND_CALM_REPLACE") != (s["sid"] == primary):
                raise ContractError("P5 primary role and primary_sid inconsistent")
        if len(set(alias_index.values())) != len(alias_index):
            raise ContractError("P5 different real stations share same IFSTN alias")
        if len(selected5) > 1 and any(s["relocated"] for s in selected5):
            raise ContractError("P5 multi-station selection must not include virtual sites")
        if mode5 == "OBSERVED":
            if any(s["relocated"] for s in selected5):
                raise ContractError("P5 observed mode cannot contain virtual stations")
            if kind5 != ("IN_DOMAIN_SINGLE" if len(selected5) == 1 else "IN_DOMAIN_MULTIPLE"):
                raise ContractError("P5 observed-mode station count mismatch")
        elif mode5 == "VIRTUAL_RELOCATED":
            if len(selected5) != 1 or kind5 != "EXTERNAL_SINGLE_VIRTUAL" or not selected5[0]["relocated"]:
                raise ContractError("P5 virtual-mode selection is not one external station")
        else:
            raise ContractError("P5 mode unsupported")
        output["p5"].append({
            "year": year, "station_ids": sorted(seen5), "primary": primary,
            "source_hours": {s["sid"]: {
                "full": s["full_isd_raw_hours"], "lite": s["isd_lite_raw_hours"]}
                for s in selected5},
            "ifstn": {s["sid"]: s["ifstn"] for s in selected5},
            "manifest_sha256": hashlib.sha256(raw5).hexdigest(),
        })
    return output


def plan_site(
    case_yaml: Path, p4_selection_root: Path, p5_selection_root: Path,
) -> dict[str, Any]:
    path = Path(case_yaml).absolute()
    if path.name != "case.yaml" or not re.fullmatch(r"[A-Za-z0-9_-]+", path.parent.name):
        raise ContractError("site contract requires /<case_name>/case.yaml")
    data, raw = _load(path)
    data = mapping(data, "case.yaml")
    if child(data, "schema_version") != 1 or type(data["schema_version"]) is not int:
        raise ContractError("unsupported schema_version")
    case_name = child(data, "case_name")
    if not isinstance(case_name, str) or case_name != path.parent.name or case_name == CASE_ID:
        raise ContractError("non-Hefei case_name must agree with case directory")
    if child(data, "settings", "timezone") != "UTC+0000":
        raise ContractError("time zone must be UTC+0000")
    grid, grid_file = _geography(data, path)
    start = _time(child(data, "preprocess", "research_time", "begin"))
    end = _time(child(data, "preprocess", "research_time", "end"))
    if end < start or end - start > timedelta(days=731):
        raise ContractError("invalid/too-long UTC research_time interval")
    years = list(range(start.year, end.year + 1))
    # Year-level selectors cover whole calendar years, never just a partial
    # research window, even when simulations use shorter time windows.
    _options(child(data, "met", "options"), FROZEN_MET_CONTROLS, "met.options")
    _options(child(data, "puff", "options"), FROZEN_PUFF_CONTROLS, "puff.options")
    upper = mapping(child(data, "preprocess", "upperair"), "upperair")
    if upper.get("station_id") not in (None, "auto"):
        raise ContractError("new site must not pin the historical 58424 station")
    pstop = _finite(child(upper, "pstop_hpa"), "pstop_hpa", 0.01)
    if pstop > 1500:
        raise ContractError("pstop_hpa outside P4 accepted source parser")
    sources = child(data, "puff", "point_sources")
    if not isinstance(sources, list) or len(sources) != 1:
        raise ContractError("only single-point-source dry pathway accepted for planning")
    stack = mapping(sources[0], "point source")
    slat, slon = _coords(child(stack, "latitude"), child(stack, "longitude"), "stack")
    if not lon_lat_in_utm_grid(slon, slat, grid):
        raise ContractError("emission stack outside UTM footprint")
    for k in ("stack_height_m", "stack_diameter_m", "exit_velocity_mps", "exit_temp_k"):
        if _finite(child(stack, k), k, 0.01) <= 0:
            raise ContractError("nonpositive stack geometry/physics")
    emissions = child(stack, "emissions")
    if (not isinstance(emissions, list) or len(emissions) != 2
            or any(_finite(v, "emissions", 0) < 0 for v in emissions)):
        raise ContractError("exactly two nonnegative species emissions required")
    if sum(emissions) <= 0:
        raise ContractError("all-zero source is not an acceptable physical acceptance fixture")
    selected = _selection(years, grid, Path(p4_selection_root), Path(p5_selection_root),
                          slat, slon)
    return {
        "contract_version": "S2-G0-NONHEFEI-METADATA-ONLY-1",
        "status": "SITE_STATION_INPUTS_VERIFIED_P6_P7_BLOCKED",
        "case_name": case_name,
        "case_yaml_sha256": hashlib.sha256(raw).hexdigest(),
        "grid_cmn_sha256": hashlib.sha256(grid_file.read_bytes()).hexdigest(),
        "grid": {
            "crs": f"WGS84_UTM{grid.iutmzn}{grid.lsohem}",
            "nx": grid.nx, "ny": grid.ny, "nz": grid.nz,
            "dgridkm": grid.dgridkm, "xrefkm": f"{grid.xrefkm:.3f}",
            "yrefkm": f"{grid.yrefkm:.3f}",
        },
        "research_time": {"begin": start.isoformat(), "end": end.isoformat(),
                          "calendar_years_with_source_selection": years},
        "selector_manifest_evidence": selected,
        "selector_source_authenticity": "NOT_AUTHENTICATED_BY_THIS_INPUT_MANIFEST_VALIDATOR",
        "scientific_acceptance": "NOT_EVALUATED",
        "ready": False, "dry_run": True, "model_executed": False,
        "network_access": False, "legacy_fallback": False, "outputs_published": False,
        "stages": [{"id": name, "dependencies": list(dep), "status": status,
                    "execute": False} for name, dep, status in DAG],
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="S2-G0 new-site case and P4/P5 handoff contract, NO P6/P7")
    p.add_argument("--case-yaml", required=True, type=Path)
    p.add_argument("--p4-selection-root", required=True, type=Path)
    p.add_argument("--p5-selection-root", required=True, type=Path)
    a = p.parse_args(argv)
    try:
        print(json.dumps(plan_site(a.case_yaml, a.p4_selection_root, a.p5_selection_root),
                         ensure_ascii=False, indent=2))
        return 0
    except (ContractError, OSError, ValueError, TypeError, OverflowError, UnicodeError) as exc:
        print(json.dumps({"status": "BLOCKED_NONHEFEI_INPUT_CONTRACT",
                          "model_executed": False, "ready": False,
                          "legacy_fallback": False, "error": str(exc)},
                         ensure_ascii=False))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
