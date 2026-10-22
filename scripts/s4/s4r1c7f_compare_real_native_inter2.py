#!/usr/bin/env python3
"""Independent first-hour full-grid original CALMET INTER2 vs shared native G16.

The original post-INTER2 field is consumed by this COMPARATOR only. It is
never supplied to native G16/G17C3/G42/G47 physics or the native executable.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import struct

NX, NY, NZ = 82, 85, 9
CELLS = NX * NY
PER_COMPONENT = CELLS * NZ
TOTAL = 2 * PER_COMPONENT
TOLERANCE_MPS = 2e-4
HEADER = struct.Struct("<6i")
PAYLOAD = struct.Struct("<" + str(TOTAL) + "f")
CLOCK = datetime(2022, 6, 1, 1, tzinfo=timezone.utc)
EXPECTED_PACKED = CLOCK.year * 100000 + CLOCK.timetuple().tm_yday * 100 + CLOCK.hour
NATIVE_MARKER = "S4R1C7F_GENUINE_82X85X9_NATIVE_G16_INTER2=PRODUCED_UNVERIFIED"

def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def compare(original: Path, native: Path, source_receipt: Path,
            native_log: Path, report: Path) -> bool:
    receipt = json.loads(source_receipt.read_text())
    if (receipt.get("status") != "PASS_ORIGINAL_REAL_SPARSE_INTER2_PRE_POST_REFERENCE_ONLY"
            or receipt.get("original_met_byte_identical") is not True
            or receipt.get("six_distinct_hours") != 6
            or receipt.get("original_station_columns") != 3
            or receipt.get("grid_shape") != [NX, NY, NZ]
            or sha(original) != receipt.get("original_post_inter2_trace_sha256")):
        raise ValueError("original genuine NOAA source reference is not valid")
    log = native_log.read_text()
    if NATIVE_MARKER not in log or "NO_ORIGINAL_WIND_INJECTION=TRUE" not in log:
        raise ValueError("source-only native diagnostic gate missing")
    original_raw = original.read_bytes()
    if len(original_raw) != 6 * (HEADER.size + PAYLOAD.size):
        raise ValueError("six-hour original post-INTER2 file corrupted")
    tag, packed, secs, nx, ny, nz = HEADER.unpack_from(original_raw)
    if (tag, packed, secs, nx, ny, nz) != (52, EXPECTED_PACKED, 0, NX, NY, NZ):
        raise ValueError("original source first model hour/geometry mismatch")
    obs = PAYLOAD.unpack_from(original_raw, HEADER.size)
    if native.stat().st_size != PAYLOAD.size:
        raise ValueError("native first-hour G16 INTER2 125460 U/V values absent")
    calculated = PAYLOAD.unpack(native.read_bytes())
    if not all(math.isfinite(x) for x in obs + calculated):
        raise ValueError("nonfinite original or native source INTER2 U/V")
    per_level = []
    maximum_u = maximum_v = 0.0
    exceedances = 0
    weighted_sum = 0.0
    worst = None
    for component, label in enumerate(("U", "V")):
        for k in range(NZ):
            biggest = 0.0
            exceeded = 0
            level_offset = component * PER_COMPONENT + k * CELLS
            for i in range(CELLS):
                p = level_offset + i
                delta = abs(calculated[p] - obs[p])
                weighted_sum += delta
                if delta > biggest:
                    biggest = delta
                if delta > (maximum_u if label == "U" else maximum_v):
                    if label == "U":
                        maximum_u = delta
                    else:
                        maximum_v = delta
                    worst = {"field": label, "level_1based": k + 1,
                             "i_1based": i % NX + 1,
                             "j_1based": i // NX + 1,
                             "native_mps": calculated[p],
                             "original_mps": obs[p],
                             "abs_residual_mps": delta}
                if delta > TOLERANCE_MPS:
                    exceeded += 1
            exceedances += exceeded
            per_level.append({"field": label, "level_1based": k+1,
                              "max_abs_mps": biggest,
                              "above_tolerance": exceeded})
    passed = exceedances == 0
    result = {
        "status": "PASS_SOURCE_SCOPED_REAL_NOAA_NATIVE_G16_INTER2" if passed
                  else "FAIL_NUMERIC_SOURCE_SCOPED_REAL_NOAA_NATIVE_G16_INTER2",
        "scope": "FIRSTHOUR_DIAGNO_PRE_WINDBC_TAIL_NOT_G26",
        "original_sha256": sha(original),
        "native_candidate_sha256": sha(native),
        "original_byte_identical_pristine_vs_instrumented": True,
        "native_payload_source": "G42_G47_G17C3_SHARED_G16_CPP",
        "native_original_wind_injected": False,
        "native_source_station_count": 3,
        "native_firsthour_model_start_utc": CLOCK.isoformat(),
        "land_water_grid": {"nx": NX, "ny": NY, "nz": NZ},
        "independent_numerical_tolerance_mps": TOLERANCE_MPS,
        "full_grid_uv_float_comparisons": TOTAL,
        "abs_residual_mean_mps": weighted_sum / TOTAL,
        "max_abs_u_mps": maximum_u,
        "max_abs_v_mps": maximum_v,
        "above_tolerance": exceedances,
        "worst_residual": worst,
        "level_comparison": per_level,
        "original_station_columns_provenance": "S4-R1c7c_PINNED_FORTRAN_ONLY",
        "g24_g26_p7_scientific_acceptance": "NOT_ACCEPTED",
    }
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print("S4R1C7F_ORIGINAL_NATIVE_FIRSTHOUR_INTER2_REPORT=" + result["status"])
    print("S4R1C7F_WORST_RESIDUAL=" + json.dumps(worst, sort_keys=True))
    print("S4R1C7F_ABOVE_2E_MINUS4_MPS=" + str(exceedances))
    print("S4R1C7F_G24_G26_P7=NOT_ACCEPTED")
    return passed

def main() -> None:
    p=argparse.ArgumentParser()
    for name in ("original", "native", "source-receipt", "native-log", "report"):
        p.add_argument("--" + name, required=True, type=Path)
    args=p.parse_args()
    if not compare(args.original, args.native, args.source_receipt,
                   args.native_log, args.report):
        raise SystemExit(3)

if __name__ == "__main__":
    main()
