#!/usr/bin/env python3
"""Read-only real NOAA sixth-hour G22 original/native stage audit.

Original six-hour Fortran trace is an independent oracle, NEVER native input.
An opt-in research-only G66 candidate must be native hour6 (NHRZ=6) from
committed native hour5 WATER USTAR/EL. Preserve *unchanged* frozen G22 limits.
This does not publish hour6 G14, unlock its production guard, or imply
independent scientific acceptance.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from scripts.s4.s4r1c9n_compare_hour3_g22_trace import (
    NC, NX, NY, NZ, GEO_SHA, ORIGINAL_TRACE_SHA,
    STAGE_ARRAYS, compare, extract, sha,
)

ORIGINAL_HOURS = tuple(range(2, 8))
SIXTH_HOUR_END_UTC = 7


def run(original_path: Path, native_path: Path, geo_path: Path,
        expected_native_sha: str) -> dict:
    if original_path.resolve() == native_path.resolve():
        raise ValueError("original/native trace cannot alias")
    if sha(original_path) != ORIGINAL_TRACE_SHA:
        raise ValueError("original Fortran G22 trace SHA drift")
    if sha(geo_path) != GEO_SHA:
        raise ValueError("authentic NOAA GEO SHA drift")
    if len(expected_native_sha) != 64 or sha(native_path) != expected_native_sha:
        raise ValueError("native hour6 G22 trace SHA drift")
    # Reuse verified source-derived, pre-registered field tolerances and
    # the strict 5-stage trace parser; do not silently rescale tolerance.
    from native_cpp.reference.compare_p3_makegeo_dynamic import parse_geo
    grid = parse_geo(geo_path, nx=NX, ny=NY, zone=50, hem="N",
                     x0=426.590, y0=3464.125, dx=1.)
    water = {i for i, lu in enumerate(grid["category"])
             if 50 <= int(lu) <= 55}
    if len(water) != 63:
        raise ValueError("native/original GEO WATER mask changed")
    original = extract(original_path.read_bytes(), ORIGINAL_HOURS)
    native = extract(native_path.read_bytes(), (SIXTH_HOUR_END_UTC,))
    result = compare(original[SIXTH_HOUR_END_UTC],
                     native[SIXTH_HOUR_END_UTC], water)
    result.pop("native_hour3_g22_production_guard", None)
    result.pop("hour3_g14_state_committed", None)
    result.update({
        "stage": "S4-R1c9ah sixth-hour G22 test-only",
        "original_trace_sha256": ORIGINAL_TRACE_SHA,
        "native_trace_sha256": expected_native_sha,
        "geo_sha256": GEO_SHA,
        "original_hour_end_utc": SIXTH_HOUR_END_UTC,
        "native_hour_end_utc": SIXTH_HOUR_END_UTC,
        "native_previous_hour_p6f_state": "COMMITTED_HOUR5_TEST_ONLY",
        "hour6_g14_committed": False,
        "hour6_g22_production_guard": "UNCHANGED_REJECTS",
        "real_hour6": "G22_ONLY",
        "scientific_independent_review": "NOT_RUN",
    })
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("original_trace", "native_trace", "geo", "report"):
        parser.add_argument("--" + name.replace("_", "-"),
                            type=Path, required=True)
    parser.add_argument("--expected-native-sha256", required=True)
    args = parser.parse_args()
    if args.report.exists():
        raise ValueError("refuse overwrite sixth-hour original/native report")
    result = run(args.original_trace, args.native_trace,
                 args.geo, args.expected_native_sha256)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(result, indent=2) + "\n")
    print(result["status"], result["bitwise_equal"], "/",
          result["compared_real4"], "REAL4",
          "frozen_exceedances", result["frozen_tolerance_exceedances"])
    for key, field in result["fields"].items():
        if field["frozen_tolerance_exceedances"] or (
            key in ("40:ustar", "40:el") and field["water_bitwise_unequal"]
        ):
            print("FIRST_SCIENCE_DIFF", key, field["first_frozen_exceedance"],
                  "WATER_BITWISE", field["water_bitwise_unequal"])
    if result["status"] != "PASS_SCOPED_FROZEN_G22_INTERMEDIATES":
        raise SystemExit(3)


if __name__ == "__main__":
    main()
