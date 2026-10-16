#!/usr/bin/env python3
"""G32B: original 2SS/2US DIAGNO kpt7/8/9 versus independent native G21/G22.

Reuses the *single-station P6D* pinned write-only DGM instrumentation: original
kpt7 USLOPE/VSLOPE, kpt8 UG/VG before slope addition and kpt9 after addition.
G21 = native post-FRADJ pre-SLOPE; G22 = same-hour post-SLOPE.
No original grid/state is fed to C++, no source equations or P6E scientific
tolerance is altered. This is diagnostic evidence, NOT a scientific PASS.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
import math
import struct
from pathlib import Path

from original_internal_state_dump import _walk_dump

NX, NY, NZ = 12, 12, 9
N = NX * NY
COUNT = N * NZ
COLUMNS = {"hour_end_utc_seconds", "k_1based", "j_1based",
           "i_1based", "u_mps_real4", "v_mps_real4"}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def native_csv(path: Path):
    with path.open(newline="") as stream:
        reader = csv.DictReader(stream)
        if set(reader.fieldnames or []) != COLUMNS:
            raise ValueError(f"G32B invalid native stage columns: {path}")
        u, v = [None] * COUNT, [None] * COUNT
        stamps = set()
        for row in reader:
            i, j, k = (int(row[key]) for key in
                       ("i_1based", "j_1based", "k_1based"))
            if not (1 <= i <= NX and 1 <= j <= NY and 1 <= k <= NZ):
                raise ValueError("G32B native source indices out of bounds")
            pos = (k-1)*N + (j-1)*NX + i-1
            if u[pos] is not None:
                raise ValueError("G32B duplicated native stage cell")
            for name, array in (("u_mps_real4", u), ("v_mps_real4", v)):
                value = float(row[name])
                if not math.isfinite(value):
                    raise ValueError("G32B non-finite native stage value")
                # max_digits10 source text roundtrips the actual native REAL*4.
                array[pos] = struct.unpack("<f", struct.pack("<f", value))[0]
            stamps.add(int(row["hour_end_utc_seconds"]))
    if len(stamps) != 1 or any(val is None for val in u+v):
        raise ValueError("G32B incomplete or mixed native physical hour")
    return (u, v), stamps.pop()


def original_dump(path: Path):
    records = _walk_dump(path)
    if [r["kpt"] for r in records] != [7, 8, 9, 10]:
        raise ValueError("G32B original DIAGNO must carry kpt7→8→9→10 once")
    if any((r["nx"], r["ny"], r["nz"]) != (NX, NY, NZ)
           for r in records):
        raise ValueError("G32B actual original DIAGNO geometry changed")
    if len({(r["packed"], r["seconds"]) for r in records}) != 1:
        raise ValueError("G32B original DIAGNO snapshots not same hour")
    result = {}
    with path.open("rb") as stream:
        for record in records[:3]:
            stream.seek(record["offset"] + 32)
            raw = stream.read(COUNT * 8)
            if len(raw) != COUNT * 8:
                raise ValueError("G32B truncated original kpt stage")
            values = struct.unpack("<" + str(2*COUNT) + "f", raw)
            result[record["kpt"]] = (values[:COUNT], values[COUNT:])
    return result, records[0]["packed"], records[0]["seconds"]


def bits(value: float) -> bytes:
    return struct.pack("<f", value)


def compare(name: str, originals, natives):
    levels = []
    mismatch = 0
    significant = 0
    first = None
    for k in range(NZ):
        metrics = []
        for component, x, y in (("U", originals[0], natives[0]),
                                ("V", originals[1], natives[1])):
            errors = [abs(float(x[k*N+c])-float(y[k*N+c]))
                      for c in range(N)]
            unequal = [c for c in range(N)
                       if bits(x[k*N+c]) != bits(y[k*N+c])]
            notable = [c for c, error in enumerate(errors) if error > 1e-3]
            mismatch += len(unequal)
            significant += len(notable)
            if first is None and unequal:
                c = unequal[0]
                first = {"k": k+1, "i": c % NX+1, "j": c // NX+1,
                         "component": component, "original": x[k*N+c],
                         "native": y[k*N+c],
                         "absolute_error": errors[c]}
            metrics.append({"component": component, "bit_mismatches": len(unequal),
                            "above_diagnostic_1e_minus_3_mps": len(notable),
                            "max_abs_mps": max(errors),
                            "rms_mps": math.sqrt(sum(z*z for z in errors)/N)})
        levels.append({"k": k+1, "component_metrics": metrics})
    return {"stage": name, "bit_mismatches": mismatch,
            "above_diagnostic_1e_minus_3_mps": significant,
            "first_bit_difference": first, "by_level": levels}


def difference(before, after):
    return tuple([
        # Cast only the native delta back to REAL*4, without claiming
        # that subtracting rounded native states reproduces SLOPE internals.
        struct.unpack("<f", struct.pack("<f", after[c][i] - before[c][i]))[0]
        for i in range(COUNT)] for c in range(2))


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--original-dump", required=True, type=Path)
    p.add_argument("--untouched-met", required=True, type=Path)
    p.add_argument("--write-only-met", required=True, type=Path)
    p.add_argument("--frozen-verdict", required=True, type=Path)
    p.add_argument("--native-pre-slope", required=True, type=Path)
    p.add_argument("--native-post-slope", required=True, type=Path)
    p.add_argument("--out", required=True, type=Path)
    args = p.parse_args()

    report = {"status": "BLOCKED", "scientific_status": "FAIL_NUMERIC",
              "scope": "G32B trace only: original G31 multisite DIAGNO against source G21/G22"}
    try:
        verdict = json.loads(args.frozen_verdict.read_text())
        if (verdict.get("status") != "FAIL_NUMERIC"
                or verdict.get("fields_per_hour") != 45
                or verdict.get("intervals") != 1
                or verdict.get("total_exceedances", 0) <= 0):
            raise ValueError("G32B requires genuine failed frozen 45-field science")
        if digest(args.untouched_met) != digest(args.write_only_met):
            raise ValueError("G32B write-only instrumentation changed original MET.DAT")
        original, packed, secs = original_dump(args.original_dump)
        native_pre, end_pre = native_csv(args.native_pre_slope)
        native_post, end_post = native_csv(args.native_post_slope)
        if end_pre != end_post or secs != 0:
            raise ValueError("G32B source model hour disagreement")
        source_start = dt.datetime.fromtimestamp(end_pre - 3600, dt.timezone.utc)
        expected_packed = (source_start.year * 100000
                           + source_start.timetuple().tm_yday * 100
                           + source_start.hour)
        if packed != expected_packed or source_start.minute or source_start.second:
            raise ValueError("G32B original kpt and source PREPDI hour differ")

        # kpt7 original SLOPE / kpt8 original pre-addition UG/VG /
        # kpt9 original post-addition UG/VG. Each comparison independently
        # uses real C++ G21/G22 outputs from this G19 source hour.
        stage8 = compare("kpt8_original_UGVG_before_SLOPE_vs_G21_FRADJ",
                         original[8], native_pre)
        stage9 = compare("kpt9_original_UGVG_after_SLOPE_vs_G22_SLOPE",
                         original[9], native_post)
        stage7 = compare("kpt7_original_USLOPE_VSLOPE_vs_native_G22_minus_G21",
                         original[7], difference(native_pre, native_post))
        # Diagnostic cutoffs are NOT the frozen P6E scientific thresholds.
        first_material = ("kpt8_before_slope" if stage8["above_diagnostic_1e_minus_3_mps"]
                          else "kpt9_slope_addition" if stage9["above_diagnostic_1e_minus_3_mps"]
                          else "after_kpt9_pre_kpt10_or_sub_millimeter_drift")
        report.update({
            "status": "PASS_G32B_WRITE_ONLY_SOURCE_FIRST_DIVERGENCE_DIAGNOSIS",
            "scientific_status": "FAIL_NUMERIC",
            "frozen_total_exceedances": verdict["total_exceedances"],
            "untouched_original_met_sha256": digest(args.untouched_met),
            "original_dump_sha256": digest(args.original_dump),
            "source_clock_start_utc": source_start.isoformat(),
            "original_kpt_packed": packed,
            "original_reference_stage_order": ["kpt7 SLOPE", "kpt8 pre-add",
                                                "kpt9 post-add", "kpt10 final"],
            "diagnostic_only_material_difference_mps": 1e-3,
            "first_material_difference_stage": first_material,
            "stage_kpt8": stage8, "stage_kpt9": stage9, "stage_kpt7": stage7,
            "note": "Bitwise mismatches include harmless rounding. Stage-local thresholds "
                    "are for prioritizing investigation only. Full frozen P6E comparator "
                    "remains FAIL; no original field was supplied to native C++.",
            "single_station_precedent":
                "original_internal_state_dump.py pinned kpt7/8/9/10 write-only dump; "
                "P6E_FIRST_NONZERO_WIND_REAL4_FORENSIC_20261013.md "
                "traces READCF effective BIAS, REAL*4 WD, and first differing source stage.",
        })
    except Exception as exc:
        report["blocker"] = str(exc)
        raise
    finally:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(report, indent=2) + "\n")
        print(json.dumps({key: ({"bit_mismatches": val["bit_mismatches"],
                                "above_diagnostic_1e_minus_3_mps":
                                    val["above_diagnostic_1e_minus_3_mps"],
                                "level1": val["by_level"][0]}
                               if key.startswith("stage_kpt") else val)
                          for key, val in report.items()}, indent=2))

if __name__ == "__main__":
    main()
