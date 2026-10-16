#!/usr/bin/env python3
"""G32D: isolate original full-CALMET US/VS station profiles vs native G23.

Reads G32C's pinned write-only original post-STHEOR/DIAGI US(k,site) and
VS(k,site), then compares actual 2SS+2US nine-layer station columns with the
G23 observed_after_diagi profiles which feed the independent native INTER2.
The native stage files are C++-generated, NOT original reference backfill.
This is forensic-only: frozen 45-field original science continues to fail.
"""
from __future__ import annotations
import argparse
import datetime as dt
import hashlib
import json
import math
import struct
from pathlib import Path

NST = 4
NZ = 9
NXY = 12


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_original(path: Path, start_hour: dt.datetime):
    raw = path.read_bytes()
    if len(raw) != 24 + 2*NST*NZ*4:
        raise ValueError("G32D missing or malformed original station profile binary")
    marker, packed, seconds, nst, nz, extra = struct.unpack_from("<6i", raw)
    expected_packed = (start_hour.year * 100000
                       + start_hour.timetuple().tm_yday * 100
                       + start_hour.hour)
    if (marker, packed, seconds, nst, nz, extra) != (
            17, expected_packed, 0, NST, NZ, 0):
        raise ValueError("G32D original station sites/date/depth changed")
    values = struct.unpack_from("<" + str(2*NST*NZ) + "f", raw, 24)
    return (values[:NST*NZ], values[NST*NZ:]), packed


def read_native_stage(path: Path):
    lines = path.read_text().splitlines()
    # Exact source-authentic INTER2 synthetic stage generator G23:
    # 4 READCF metadata lines; 12 GEO ILANDU rows; 9 station lines;
    # 108 first-guess rows; 108 observation weights.
    if len(lines) != 4 + NXY + NZ + 2*NZ*NXY:
        raise ValueError("G32D native INTER2 stage count changed")
    head = lines[0].split()
    if len(head) != 10 or int(head[0]) != NST:
        raise ValueError("G32D native station count/control schema changed")
    for index in (2, 3):
        if len(lines[index].split()) != NST:
            raise ValueError("G32D native station UTM geometry incomplete")
    values = []
    for k in range(NZ):
        line = [float(x) for x in lines[4+NXY+k].split()]
        if len(line) != NST or not all(math.isfinite(x) for x in line):
            raise ValueError("G32D native upper/SS profile malformed")
        values.extend(struct.unpack("<"+str(NST)+"f",
                                    struct.pack("<"+str(NST)+"f", *line)))
    return values


def source_numeric_comparison(original, candidate, component: str):
    station_report = []
    first_material = None
    full_max = 0.0
    n_bit_different = 0
    n_missing_mismatch = 0
    for station in range(NST):
        cells = []
        for k in range(NZ):
            index = k*NST + station
            left, right = original[index], candidate[index]
            missing_left = abs(left) >= 998
            missing_right = abs(right) >= 998
            if missing_left != missing_right:
                n_missing_mismatch += 1
            comparable = not (missing_left or missing_right)
            gap = abs(left-right) if comparable else None
            if struct.pack("<f", left) != struct.pack("<f", right):
                n_bit_different += 1
            if gap is not None:
                full_max = max(full_max, gap)
                if first_material is None and gap > 1e-3:
                    first_material = {"station": station+1, "level": k+1,
                                      "original": left, "native": right,
                                      "abs_mps": gap}
            cells.append({"level": k+1, "original": left, "native": right,
                          "abs_mps": gap, "original_missing": missing_left,
                          "native_missing": missing_right})
        station_report.append({
            "site": ["SS1", "SS2", "US1", "US2"][station],
            "first_layer": cells[0],
            "all_levels": cells,
        })
    return {"component": component, "station_profiles": station_report,
            "bit_differences": n_bit_different,
            "valid_max_abs_mps": full_max,
            "missing_semantic_mismatches": n_missing_mismatch,
            "first_diagnostic_over_1e_minus_3_mps": first_material}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--original-stations", type=Path, required=True)
    p.add_argument("--untouched-met", type=Path, required=True)
    p.add_argument("--instrumented-met", type=Path, required=True)
    p.add_argument("--frozen-verdict", type=Path, required=True)
    p.add_argument("--native-u-stage", type=Path, required=True)
    p.add_argument("--native-v-stage", type=Path, required=True)
    p.add_argument("--source-clock", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    report = {"status": "BLOCKED", "scientific_status": "FAIL_NUMERIC",
              "scope": "G32D genuine original 4-station pre-INTER2 source profiles"}
    try:
        verdict = json.loads(args.frozen_verdict.read_text())
        if (verdict.get("status") != "FAIL_NUMERIC"
                or verdict.get("fields_per_hour") != 45
                or verdict.get("intervals") != 1):
            raise ValueError("G32D needs actual original frozen P6E fail")
        if sha(args.untouched_met) != sha(args.instrumented_met):
            raise ValueError("G32D write-only source instrumented MET.DAT not byte-identical")
        from g32b_trace_original_multisite_slope_first_divergence import native_csv
        _source_wind, hour_end = native_csv(args.source_clock)
        clock = dt.datetime.fromtimestamp(hour_end - 3600, dt.timezone.utc)
        if clock.minute or clock.second:
            raise ValueError("G32D original hourly clock invalid")
        (source_u, source_v), packed = read_original(args.original_stations, clock)
        native_u = read_native_stage(args.native_u_stage)
        native_v = read_native_stage(args.native_v_stage)
        compare_u = source_numeric_comparison(source_u, native_u, "U")
        compare_v = source_numeric_comparison(source_v, native_v, "V")
        report.update({
            "status": "PASS_G32D_ORIGINAL_STATION_PROFILE_FIRST_DIFFERENCE_DIAGNOSTIC",
            "source_hour_start_utc": clock.isoformat(),
            "source_original_packed": packed,
            "untouched_original_met_sha256": sha(args.untouched_met),
            "original_station_dump_sha256": sha(args.original_stations),
            "native_u_stage_sha256": sha(args.native_u_stage),
            "native_v_stage_sha256": sha(args.native_v_stage),
            "profile_U": compare_u, "profile_V": compare_v,
            "diagnostic_only_cutoff_mps": 0.001,
            "scientific_status": "FAIL_NUMERIC",
            "diagnostic_priority": (
                "If native SS1/SS2 level1 diverge: G23 ELUSTR2/MIXHTST/SIMILT "
                "and source surface observation assembly; if all station "
                "profiles match: inspect original INTER2 READCF radii/weights "
                "and original transient first WINDBC inputs."
            ),
        })
    except Exception as exc:
        report["blocker"] = str(exc)
        raise
    finally:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(report, indent=2) + "\n")
        print(json.dumps({
            key: ({"bit_differences": value["bit_differences"],
                   "valid_max_abs_mps": value["valid_max_abs_mps"],
                   "missing_semantic_mismatches":
                       value["missing_semantic_mismatches"],
                   "first_diagnostic_over_1e_minus_3_mps":
                       value["first_diagnostic_over_1e_minus_3_mps"],
                   "level1_by_station": [
                       {"site": x["site"], **x["first_layer"]}
                       for x in value["station_profiles"]]}
                  if key.startswith("profile_") else value)
            for key, value in report.items()}, indent=2))


if __name__ == "__main__":
    main()
