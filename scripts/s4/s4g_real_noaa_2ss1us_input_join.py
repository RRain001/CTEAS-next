#!/usr/bin/env python3
"""S4-G: verify independent genuine NOAA P4+P5 evidence shares ONE exact grid.

This is strictly source-admission evidence. NO P3 GEO, combined G19 parser
or CALMET original-v-native numerical science is run or authorized here.
"""
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

_SURFACE = {"58314099999": "583140", "58321099999": "583210"}
_SHA = re.compile(r"[0-9a-f]{64}\Z")


def require_sha(value: object, role: str) -> str:
    if not isinstance(value, str) or not _SHA.fullmatch(value):
        raise ValueError(f"{role}: invalid SHA256")
    return value


def coadmit(p4: dict, p5: dict) -> dict:
    """Fail closed on grid, source, clock or station-identity mismatch."""
    if p4.get("status") != "G1BB1_REAL_NOAA_ANQING_NATIVE_P4_UP_SOURCE_PASS_SCOPED":
        raise ValueError("P4 must be a genuinely reexecuted NOAA native UP source")
    if (p4.get("calendar_year") != 2022 or
            p4.get("source_station") != "CHM00058424" or
            p4.get("wmo") != "58424" or
            p4.get("model_hours_checked") != 6):
        raise ValueError("P4 WMO/year/sounding six-hour original identity mismatch")
    if (p4.get("negative_wrong_wmo") != "BLOCKED_AS_EXPECTED" or
            p4.get("negative_missing_future_bracket") != "BLOCKED_AS_EXPECTED" or
            "PASS_P6G_REAL_NOAA_UP_SOURCE_TIME_BRACKETS"
                not in p4.get("independent_P6_up_source_parser", "")):
        raise ValueError("P4 actual C++ UP input-bracketing and negative evidence missing")
    upper_sha = require_sha(p4.get("normalized_up_sha256"), "actual P4 UP.DAT")
    require_sha(p4.get("original_noaa_por_sha256"), "original P4 IGRA source")

    if p5.get("status") != "ISSUE56_REAL_NOAA_ORIGINAL_NATIVE_BYTE_PARITY_SCOPED_PASS":
        raise ValueError("P5 actual observed native/original raw SMERGE science missing")
    source = p5.get("scenarios")
    if not isinstance(source, list) or len(source) != 1:
        raise ValueError("P5 must supply only one chosen 2022 real observation scenario")
    p5_case = source[0]
    if p5_case.get("scenario") != "year2022":
        raise ValueError("P5 real 2022 year/source scenario mismatch")
    d4 = p5_case.get("p5_to_issue42_d4_source_handoff")
    if not isinstance(d4, dict) or d4.get("status") != "PASS_SCOPED_SOURCE_ONLY_HANDOFF_NOT_G19":
        raise ValueError("P5 actual SHA-checked published SURF handoff missing")
    grid_p4 = require_sha(p4.get("grid_cmn_sha256"), "actual P4 generated grid.cmn")
    grid_p5 = require_sha(d4.get("grid_cmn_sha256"), "actual P5 generated grid.cmn")
    if grid_p4 != grid_p5 or grid_p5 != require_sha(p5_case.get("grid_cmn_sha256"), "P5 case grid"):
        raise ValueError("P4 and P5 authentic station domains are NOT the same physical grid")
    origin = p4.get("grid_origin_km")
    if (not isinstance(origin, list) or origin != p5["input_provenance"]["grid_origin_km"] or
            len(origin) != 2 or any(not re.fullmatch(r"\d+\.\d{3}", o) for o in origin)):
        raise ValueError("source P4/P5 exact three-decimal UTM origin mismatch")

    if d4.get("hour_ending_records") != 24 or d4.get("hour_semantics") != "(BEGIN,END] SMERGE hour-ending":
        raise ValueError("P5 independently parsed published SURF station-hours mismatch")
    if (d4.get("research_begin_utc") != "20220601-000000" or
            d4.get("research_end_utc") != "20220602-000000"):
        raise ValueError("P5 observed 2022 June time window differs from P4 source")
    start = datetime.strptime(p4.get("model_first_hour", ""), "%Y-%m-%dT%H:%MZ").replace(tzinfo=timezone.utc)
    p5_start = datetime.strptime(d4["research_begin_utc"], "%Y%m%d-%H%M%S").replace(tzinfo=timezone.utc)
    p5_end = datetime.strptime(d4["research_end_utc"], "%Y%m%d-%H%M%S").replace(tzinfo=timezone.utc)
    if not p5_start < start or start + timedelta(hours=5) > p5_end:
        raise ValueError("actual six hourly UP clocks not covered by P5 published SURF")
    aliases = d4.get("ordered_ifstn")
    if not isinstance(aliases, list) or len(aliases) != 2 or set(aliases) != set(_SURFACE.values()):
        raise ValueError("two authentic surface source aliases and order missing")
    if p5_case.get("ordered_ifstn") != aliases or d4.get("P5_TO_G19") != "NOT_RUN":
        raise ValueError("P5 station order or source-only status not preserved")
    annual = d4.get("annual_noaa_selections")
    if not isinstance(annual, list) or len(annual) != 1 or annual[0].get("year") != 2022:
        raise ValueError("P5 source selection years changed")
    s = annual[0].get("stations")
    if (annual[0].get("mode") != "OBSERVED" or not isinstance(s, list) or len(s) != 2 or
            {x.get("source_station_id") for x in s} != set(_SURFACE) or
            any(x.get("relocated") is not False or x.get("ifstn") != _SURFACE[x["source_station_id"]]
                for x in s)):
        raise ValueError("P5 stations are not two distinct true in-grid NOAA observations")
    if len({tuple(x["source_latlon"]) for x in s}) != 2:
        raise ValueError("P5 real observed station coordinates are duplicate")
    for x in s:
        if x.get("source_latlon") != x.get("effective_latlon"):
            raise ValueError("P5 observed station was virtually relocated")
        require_sha(x.get("original_isd_sha256"), "original full NOAA ISD")
        require_sha(x.get("original_isd_lite_sha256"), "original NOAA ISD-Lite")
    r = d4.get("source_reader_coverage_totals")
    if (not isinstance(r, dict) or r.get("hours") != 24 or r.get("nssta") != 2 or
            r.get("ordered_ifstn") != aliases or
            r.get("populated_station_hours", 0)+r.get("missing_station_hours", 0) != 48):
        raise ValueError("P5 original SURF reader station-hour integrity missing")
    require_sha(d4.get("published_surf", {}).get("sha256"), "actual P5 published SURF")
    if (p5_case.get("P5_ORIGINAL_PARITY") != "SCIENCE_ACCEPTED_SCOPED_RAW_SURF_BYTE_IDENTICAL" or
            p5_case.get("P6_NUMERICAL") not in (None, "NOT_RUN")):
        raise ValueError("raw Fortran SMERGE parity missing or source-only scope drifted")
    if (p5.get("P6_NUMERICAL") != "NOT_RUN" or
            p4.get("P3_GEO") != "NOT_PRODUCED"):
        raise ValueError("S4-G cannot accept preclaimed full P6/P3 science")

    return {
        "status": "S4G_REAL_NOAA_2SS1US_INDEPENDENT_INPUT_PAIR_PASS_SOURCE_ONLY",
        "science_45_fields": "NOT_RUN",
        "shared_grid_cmn_sha256": grid_p4,
        "actual_grid_origin_km": origin,
        "2022_original_up_wmo": "58424",
        "noaa_up_sha256": upper_sha,
        "surface_real_sid_to_ifstn": _SURFACE,
        "p5_source_station_order": aliases,
        "noaa_published_surf_sha256": d4["published_surf"]["sha256"],
        "p5_hours": 24,
        "p5_populated_station_hours": r["populated_station_hours"],
        "p5_missing_station_hours": r["missing_station_hours"],
        "p4_six_hour_begin_utc": p4["model_first_hour"],
        "science_limits": "P3 same-grid GEO not produced; G19 combined original source not yet compiled/executed; P6/P7 not run; P5 secondary station sparse",
        "P3_GEO": "NOT_PRODUCED",
        "G19_FULL_SOURCE": "NOT_RUN",
        "G26_NORMAL_SELECTED": "NOT_RUN",
        "CALMET_ORIGINAL_45_FIELD": "NOT_RUN",
        "P7": "NOT_RUN",
        "production_admission": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--p4", type=Path, required=True)
    parser.add_argument("--p5", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.out.exists() or args.out.is_symlink():
            raise ValueError("refusing overwrite/symlink output")
        p4 = json.loads(args.p4.read_text())
        p5 = json.loads(args.p5.read_text())
        report = coadmit(p4,p5)
        args.out.parent.mkdir(parents=True,exist_ok=True)
        args.out.write_text(json.dumps(report, indent=2, sort_keys=True)+"\n")
        print("S4G_REAL_NOAA_2SS1US_SOURCE_PAIR=PASS_SCOPED_NO_GEO_G19_P6")
        return 0
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
        print("S4G_REAL_NOAA_2SS1US_SOURCE_PAIR=BLOCKED "+str(exc))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
