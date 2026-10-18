"""#56 P5 D1-A: read-only offline admission of a staged NOAA surface archive.

This is *not* the generic SMERGE producer. It validates source custody and
the existing annual selector's scientific contract before D1-B executes that
selector/preprocessor in a new isolated case. No download, source rewrite,
surface interpolation, or SURF.DAT production occurs in this module.

The #42 B-0 case/grid/time admission remains the sole shared authority.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta
import hashlib
import json
from pathlib import Path
import re
import sys

from engine.run_met.station_grid import load_strict_utm_grid, lon_lat_in_utm_grid
from native_cpp.orchestration.case_admission import admit_case, verify_immutable
from native_cpp.orchestration.plan import ContractError
from .isd_lite_wind import filename as lite_filename
from .station_identity import numeric_station_ids

STATION_ID = re.compile(r"[A-Za-z0-9]{11}\Z")
GEOMETRY = "STRICT_WGS84_UTM_GRID_CMN_SW_CORNER_CLOSED_EDGES"
PRIMARY = "COMPLETE_FILL_AND_CALM_REPLACE"
AUXILIARY = "RAW_SPARSE_STANDARDIZE_ONLY"


def _sha_file(path: Path, *, limit: int | None = None) -> str:
    if path.is_symlink() or not path.is_file():
        raise ContractError(f"P5 missing or symlinked input: {path}")
    size = path.stat().st_size
    if size == 0 or (limit is not None and size > limit):
        raise ContractError(f"P5 empty or oversized input: {path}")
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _path_inside_case(root: Path, raw: Path) -> None:
    expected = root / "met" / "surface" / "isd_raw"
    if raw.absolute() != expected.absolute():
        raise ContractError("P5 D1-A source archive must be staged in this case's met/surface/isd_raw")
    for item in (root / "met", root / "met/surface", raw, raw / "isd_lite"):
        if item.is_symlink() or not item.is_dir():
            raise ContractError(f"P5 staged archive directory missing or symlinked: {item}")


def _year_hours(year: int) -> int:
    start, end = datetime(year, 1, 1), datetime(year + 1, 1, 1)
    return int((end - start).total_seconds() // 3600)


def _coordinate(row: dict, field: str) -> float:
    value = row.get(field)
    if type(value) not in (int, float):
        raise ContractError(f"P5 invalid {field} in station manifest")
    import math
    if not math.isfinite(value):
        raise ContractError(f"P5 nonfinite {field}")
    return float(value)


def _selection(path: Path, year: int, grid, raw: Path) -> tuple[dict, list[dict]]:
    _sha_file(path, limit=3_000_000)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, UnicodeError) as exc:
        raise ContractError(f"P5 invalid annual selection JSON: {path}") from exc
    if not isinstance(payload, dict) or type(payload.get("year")) is not int or payload["year"] != year:
        raise ContractError(f"P5 station manifest year mismatch: {year}")
    if payload.get("selection_geometry") != GEOMETRY:
        raise ContractError("P5 selected geometry is not the approved UTM algorithm")
    if payload.get("utm_zone") != grid.iutmzn or payload.get("utm_hemisphere") != grid.lsohem:
        raise ContractError("P5 station selection grid zone/hemisphere mismatch")
    if payload.get("mode") not in ("OBSERVED", "VIRTUAL_RELOCATED"):
        raise ContractError("P5 station selection mode unsupported")
    rows = payload.get("stations")
    if not isinstance(rows, list) or not rows:
        raise ContractError(f"P5 no selected surface station for year {year}")
    if payload["mode"] == "VIRTUAL_RELOCATED" and len(rows) != 1:
        raise ContractError("P5 zero-in-domain fallback must select exactly one virtual station")
    expected_hours = _year_hours(year)
    sids: set[str] = set()
    aliases: set[str] = set()
    evidence: list[dict] = []
    for row in rows:
        if not isinstance(row, dict):
            raise ContractError("P5 invalid station record")
        sid, alias = row.get("sid"), str(row.get("ifstn", ""))
        if not isinstance(sid, str) or not STATION_ID.fullmatch(sid):
            raise ContractError("P5 invalid original NOAA station identity")
        if sid in sids or not alias.isdecimal() or alias in aliases:
            raise ContractError("P5 duplicate NOAA identity or IFSTN alias")
        sids.add(sid)
        aliases.add(alias)
        if type(row.get("expected_hours")) is not int or row["expected_hours"] != expected_hours:
            raise ContractError(f"P5 calendar-hour denominator mismatch in {year}")
        full, lite = row.get("full_isd_raw_hours"), row.get("isd_lite_raw_hours")
        if (type(full) is not int or type(lite) is not int or
                not (0 < full <= expected_hours and 0 < lite <= expected_hours)):
            raise ContractError(f"P5 invalid original ISD/ISD-Lite coverage for {sid}")
        relocated = row.get("relocated")
        if relocated is not (payload["mode"] == "VIRTUAL_RELOCATED"):
            raise ContractError("P5 source/effective relocation flag inconsistent with selection")
        lat, lon = _coordinate(row, "lat"), _coordinate(row, "lon")
        source_lat = _coordinate(row, "source_lat")
        source_lon = _coordinate(row, "source_lon")
        if not lon_lat_in_utm_grid(lon, lat, grid):
            raise ContractError(f"P5 effective location outside approved grid for {sid}")
        if not relocated and (lat != source_lat or lon != source_lon):
            raise ContractError(f"P5 physical station coordinates were silently relocated: {sid}")
        if relocated:
            if lon_lat_in_utm_grid(source_lon, source_lat, grid):
                raise ContractError("P5 virtual source is in-domain; invalid fallback")
            if 10 * full <= 9 * expected_hours or 10 * lite <= 9 * expected_hours:
                raise ContractError("P5 virtual station requires strictly >90% of BOTH original sources")
        source = raw / f"{sid}-{year}.csv"
        wind = raw / "isd_lite" / lite_filename(sid, year)
        full_sha, lite_sha = _sha_file(source), _sha_file(wind)
        declared_wind = row.get("wind_isd_lite")
        if (not isinstance(declared_wind, dict) or
                declared_wind.get("sha256") != lite_sha or
                declared_wind.get("filename") != wind.name):
            raise ContractError(f"P5 ISD-Lite bytes or station/year manifest changed: {sid}")
        evidence.append({
            "sid": sid, "ifstn": alias,
            "role": row.get("wind_treatment"),
            "relocated": relocated,
            "source_latlon": [source_lat, source_lon],
            "effective_latlon": [lat, lon],
            "expected_hours": expected_hours,
            "full_isd_raw_hours_reported": full,
            "isd_lite_raw_hours_reported": lite,
            "full_isd": {"path": str(source), "sha256": full_sha},
            "isd_lite": {"path": str(wind), "sha256": lite_sha},
        })
    primary_sid = payload.get("primary_sid")
    ranked = min(rows, key=lambda row: (
        -row["isd_lite_raw_hours"], -row["full_isd_raw_hours"], row["sid"]))
    if primary_sid not in sids or primary_sid != ranked["sid"]:
        raise ContractError(f"P5 original annual primary ranking mismatch in {year}")
    for row in rows:
        role = PRIMARY if row["sid"] == primary_sid else AUXILIARY
        if row.get("wind_treatment") != role:
            raise ContractError(f"P5 primary/sparse auxiliary wind policy mismatch in {year}")
    return payload, evidence


def admit_p5_archive(case_yaml: Path, raw_dir: Path, history_file: Path) -> dict:
    """Validate staged, immutable case and already-selected authentic-source *claims*.

    Hashes establish present bytes. Selector counts are checked for consistency,
    not independently re-counted from raw hourly records (reserved for D1-B).
    """
    admission = admit_case(case_yaml)
    root = admission.case_path.parent
    _path_inside_case(root, raw_dir)
    history_sha = _sha_file(history_file)
    grid = load_strict_utm_grid(admission.grid_path, context="P5 D1-A")
    begin = datetime.strptime(admission.research_begin, "%Y%m%d-%H%M%S")
    end = datetime.strptime(admission.research_end, "%Y%m%d-%H%M%S")
    years = list(range(begin.year, end.year + 1))
    previous_ids: set[str] | None = None
    all_sids: set[str] = set()
    stable: dict[str, tuple] = {}
    selected: list[dict] = []
    for year in years:
        path = raw_dir / f"station_selection_{year}.json"
        payload, stations = _selection(path, year, grid, raw_dir)
        ids = {station["sid"] for station in stations}
        # A single original SMERGE SURF header cannot encode changing membership.
        # Different memberships require explicit future segmented delivery.
        if previous_ids is not None and ids != previous_ids:
            raise ContractError("P5 across-year station membership changed: segmented SURF required")
        previous_ids = ids
        all_sids.update(ids)
        for station in stations:
            sid = station["sid"]
            identity = (station["ifstn"], tuple(station["source_latlon"]),
                        tuple(station["effective_latlon"]), station["relocated"])
            if sid in stable and stable[sid] != identity:
                raise ContractError(f"P5 across-year identity/effective position conflict: {sid}")
            stable[sid] = identity
        selected.append({
            "year": year, "mode": payload["mode"], "primary_sid": payload["primary_sid"],
            "selection_manifest": {"path": str(path), "sha256": _sha_file(path)},
            "stations": stations,
        })
    aliases = numeric_station_ids(sorted(all_sids))
    for year in selected:
        for row in year["stations"]:
            if row["ifstn"] != aliases[row["sid"]]:
                raise ContractError("P5 IFSTN does not match global cross-year identity reconciliation")
    verify_immutable(admission)
    return {
        "producer_issue": 56, "status": "INPUT_CHECKED",
        "scope": "OFFLINE_SOURCE_CUSTODY_AND_SELECTOR_MANIFEST_CONTRACT_ONLY",
        "case_name": admission.case_name,
        "case_sha256": admission.case_sha256, "grid_sha256": admission.grid_sha256,
        "research_time_sha256": admission.time_sha256,
        "research_begin_utc": admission.research_begin,
        "research_end_utc": admission.research_end,
        "requested_hour_labels_inclusive": int((end - begin) / timedelta(hours=1)) + 1,
        "grid": {"utm_zone": admission.utm_zone, "hemisphere": admission.hemisphere,
                 "nx": admission.nx, "ny": admission.ny, "dgridkm": admission.dgridkm,
                 "xrefkm": admission.xrefkm_text, "yrefkm": admission.yrefkm_text},
        "history": {"path": str(history_file), "sha256": history_sha},
        "years": selected, "global_ifstn": aliases,
        "coverage_note": "reported original UTC coverage; not independently re-counted in D1-A",
        "P5_SOURCE_SELECTION": "MANIFEST_CHECKED_NOT_REPLAYED",
        "P5_NATIVE_SURF": "NOT_RUN",
        "P5_GENERIC_CASE_EXECUTION": "NOT_RUN",
        "P5_ORIGINAL_PARITY": "NOT_RUN",
        "P5_TO_G19": "NOT_RUN",
        "science_acceptance": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Read-only staged P5 ISD/ISD-Lite source admission")
    parser.add_argument("--case-yaml", required=True, type=Path)
    parser.add_argument("--raw-dir", required=True, type=Path)
    parser.add_argument("--history-file", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        result = admit_p5_archive(args.case_yaml, args.raw_dir, args.history_file)
    except (ContractError, OSError, ValueError, KeyError, TypeError) as exc:
        print(f"P5_D1A_ARCHIVE_ADMISSION=BLOCKED reason={exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print("P5_D1A_ARCHIVE_ADMISSION=INPUT_CHECKED P5_NATIVE_SURF=NOT_RUN", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
