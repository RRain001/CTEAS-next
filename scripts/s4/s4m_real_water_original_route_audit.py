#!/usr/bin/env python3
"""Pin literal original WATER/WATERP source route of an actual same-case met.inp.

Original-source decision audit; NOT physical equivalence or native model run.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

PINNED_BLOB = "437f43bb7f0e51a1919e56664663e1a046986ed0"


def code(line: str) -> str:
    if not line or line[0] in ("c", "C", "*", "!"):
        return ""
    return line[6:].strip().lower() if len(line) > 6 else ""


def statement_lines(source: list[str], first: int, last: int) -> list[tuple[int, str]]:
    return [(i + 1, code(line)) for i, line in enumerate(source) if first <= i + 1 <= last]


def single_location(source: list[str], regex: str, first: int, last: int) -> int:
    pattern = re.compile(regex, re.IGNORECASE)
    found = [i for i, line in statement_lines(source, first, last) if pattern.search(line)]
    if len(found) != 1:
        raise ValueError("Original source branch ambiguous " + regex + ": " + repr(found))
    return found[0]


def original_control(met: str, name: str) -> int:
    matches = re.findall(r"!\s*" + re.escape(name) + r"\s*=\s*([-+]?\d+)\s*!", met, re.I)
    if len(matches) != 1:
        raise ValueError(f"missing or duplicate original READCF integer control {name}: {matches}")
    return int(matches[0])


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def audit(vendor: Path, deck: Path, geo: Path) -> dict:
    pinned = subprocess.run(["git", "hash-object", str(vendor)],
                            capture_output=True, check=True, text=True).stdout.strip()
    if pinned != PINNED_BLOB:
        raise ValueError("original CALMET source identity changed")
    lines = vendor.read_text().splitlines()
    comp_start = single_location(lines, r"^subroutine\s+comp\s*\(", 1, len(lines))
    next_sub = min(i for i, text in statement_lines(lines, comp_start + 1, len(lines))
                   if re.match(r"^subroutine\s+\w+\s*\(", text))
    first_comp = statement_lines(lines, comp_start, next_sub - 1)
    heat = [i for i, text in first_comp if re.search(r"\bcall\s+heatfx\s*\(", text)]
    water = [i for i, text in first_comp if re.search(r"\bcall\s+water\s*\(", text)]
    waterp = [i for i, text in first_comp if re.search(r"\bcall\s+waterp\s*\(", text)]
    elustr = [i for i, text in first_comp if re.search(r"\bcall\s+elustr\s*\(", text)]
    if len(heat) != 2 or len(water) != 1 or len(waterp) != 1 or len(elustr) != 2:
        raise ValueError("unchanged original COMP source call graph altered")
    if not max(heat) < min(water) or not max(water + waterp) < min(elustr):
        raise ValueError("original COMP HEATFX/WATER/ELUSTR source order unsupported")
    subwater = single_location(lines, r"^subroutine\s+water\s*\(", 1, len(lines))
    subwaterp = single_location(lines, r"^subroutine\s+waterp\s*\(", 1, len(lines))
    neutral_to = single_location(lines, r"if\s*\(\s*nowsta\s*\.eq\.\s*0\s*\)\s*go\s+to\s+1200",
                                 subwater, subwaterp)
    labels = [i for i in range(subwater, subwaterp) if re.search(r"^\\s*1200\\s+continue\\s*$", lines[i - 1], re.I)]
    if len(labels) != 1:
        raise ValueError("original WATER neutral fixed-form label 1200 missing")
    neutral_start = labels[0]
    neutral_wt_zero = single_location(lines, r"^wt\s*=\s*0\.", neutral_start, subwaterp)
    water_assign = single_location(lines, r"^qh\s*\(\s*i\s*,\s*j\s*\)\s*=\s*wt\s*\*\s*rhocp",
                                   subwater, subwaterp)
    water_cell = single_location(lines, r"^if\s*\(\s*ilandu\(i,j\)\.lt\.iwat1\.or\.",
                                 subwater, subwaterp)
    if not subwater < water_cell < neutral_to < neutral_start < neutral_wt_zero < water_assign:
        raise ValueError("unmodified WATER neutral no-station assignment order drifted")
    inputs = deck.read_text()
    controls = {k: original_control(inputs, k) for k in
                ("NOWSTA", "ITWPROG", "ICOARE", "IMIXH")}
    if controls["NOWSTA"] != 0 or controls["ITWPROG"] != 0:
        raise ValueError("true observed 2SS+1US site is not selected original WATER zero-overwater-station path")
    # Sea station counts and upper station counts are distinct dimensions.
    if original_control(inputs, "NSSTA") != 2 or original_control(inputs, "NUSTA") != 1:
        raise ValueError("source real observed 2SS and true IGRA 1US identity drifted")

    from native_cpp.reference.compare_p3_makegeo_dynamic import parse_geo
    ge = parse_geo(geo, nx=82, ny=85, zone=50, hem="N",
                   x0=426.590, y0=3464.125, dx=1.0)
    water_count = sum(50 <= int(x) <= 55 for x in ge["category"])
    if water_count <= 0 or water_count >= 82*85:
        raise ValueError("actual source GEO must have original water and land cells")

    result = {
        "status": "S4M_REAL_2SS1US_ORIGINAL_NO_WATER_STATION_WATER_ROUTE_AUDIT_PASS_SCOPED",
        "original_calmet_git_blob": pinned,
        "original_calmet_sha256": sha(vendor),
        "real_source_metinp_sha256": sha(deck),
        "real_source_geo_sha256": sha(geo),
        "real_surface_station_count": 2,
        "real_upper_station_count": 1,
        "water_observation_station_count": 0,
        "original_READCF_controls": controls,
        "real_water_grid_cell_count": water_count,
        "original_comp_call_lines": {
            "HEATFX": heat, "WATER": water, "WATERP": waterp,
            "ELUSTR": elustr},
        "original_WATER_source_lines": {
            "start": subwater, "cell_water_branch": water_cell,
            "NOWSTA_zero_go_neutral": neutral_to,
            "neutral_entry": neutral_start,
            "neutral_wt_zero": neutral_wt_zero,
            "QH_equals_wt_times_rhocp": water_assign},
        "selected_original_surface_route": "WATER_NOT_WATERP_ITWPROG_ZERO",
        "selected_no_OW_station_branch": "NEUTRAL_FALLBACK_WT_ZERO_BEFORE_POST_WATER_QH_ASSIGNMENT",
        "water_heatfx_origin": "QSW_ALL_QH_UNCHANGED",
        "water_post_WATER_QH_expected_by_literal_source": "ZERO_BUOYANCY_FLUX",
        "actual_original_water_QH_before_after_hour_instrumentation": "NOT_RUN",
        "actual_2022_native_water_USTAR_EL_ZI_45field_parity": "NOT_RUN",
        "G26_production": "NOT_ACCEPTED",
    }
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vendor", type=Path, required=True)
    parser.add_argument("--met", type=Path, required=True)
    parser.add_argument("--geo", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    a = parser.parse_args()
    r = audit(a.vendor, a.met, a.geo)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(r, indent=2, sort_keys=True) + "\n")
    print("S4M_REAL_NOAA_2SS1US_ORIGINAL_WATER_NOWSTA0_ROUTE=PASS_SOURCE_SCOPED")
    print("S4M_WATER_QH_ORIGINAL_POST_WATER_NEUTRAL_WT_ZERO=",
          r["water_post_WATER_QH_expected_by_literal_source"])
    print("S4M_REAL_SITE_WATER_CELLS", r["real_water_grid_cell_count"])
    print("S4M_WATER_ROUTE_OPTIONS", json.dumps(r["original_READCF_controls"], sort_keys=True))
    print("S4M_NATIVE_WATER_HEATFX_ELUSTR_PARITY=NOT_RUN")


if __name__ == "__main__":
    main()
