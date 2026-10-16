#!/usr/bin/env python3
"""Numeric verdict for the real-case step-one wind field against the
*unchanged* original CALMET WIND1 + SIMILT sources.

Reuses the independently verified WIND1 harness (`compare_original_wind1_firstguess`)
to compile the frozen original routines, then replays the driver for every
hourly fixture emitted by `cteas_p6_realcase_wind_field --fixtures` and
compares cell by cell against the producer's `wind1_u/v_<label>.f32` arrays.
"""
import argparse
import hashlib
import json
import math
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import compare_original_wind1_firstguess as wind1

NX = NY = 50
NZ = 9
N = NX * NY
COMPONENTS = N * NZ
ABS_TOL = 2.0e-4

def read_f32(path):
    raw = path.read_bytes()
    if len(raw) != COMPONENTS * 4:
        raise RuntimeError(f"{path.name}: expected {COMPONENTS} float32 values")
    return list(struct.unpack(f"<{COMPONENTS}f", raw))

def read_original(path):
    rows = path.read_text().splitlines()
    if len(rows) != COMPONENTS:
        raise RuntimeError(f"{path.name}: expected {COMPONENTS} original rows")
    u = []
    v = []
    for n, row in enumerate(rows):
        parts = row.split()
        expected = (n % NX + 1, (n // NX) % NY + 1, n // N + 1)
        if len(parts) != 5 or tuple(map(int, parts[:3])) != expected:
            raise RuntimeError(f"{path.name}: row order mismatch at {expected}")
        u.append(float(parts[3]))
        v.append(float(parts[4]))
    return u, v

def report_windows(windows):
    return {label: {**stats,
                    "status": "PASS" if stats["worst_abs_error_mps"] <= ABS_TOL
                    else "FAIL"}
            for label, stats in windows.items()}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--vendor", required=True, type=Path)
    parser.add_argument("--fields", required=True, type=Path,
                        help="producer output directory")
    parser.add_argument("--fixtures", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    sources = wind1.extract(args.vendor, args.out)
    driver = args.out / "driver.for"
    driver.write_text(wind1.DRIVER)
    binary = args.out / "original_wind1_step_one"
    wind1.run("gfortran", "-std=legacy", "-O0", "-fno-automatic",
              "-ffixed-line-length-none", "-fallow-argument-mismatch",
              "-I" + str(args.vendor), *sources, driver, "-o", binary)

    labels = (args.fields / "produced_hours.txt").read_text().split()
    if not labels:
        raise RuntimeError("producer emitted no hourly labels")
    per_hour = {}
    per_level_abs = [0.0] * NZ
    per_level_rel = [0.0] * NZ
    windows = {label: {"components": 0, "worst_abs_error_mps": 0.0,
                       "worst_rel_error": 0.0}
               for label in ("1h", "6h", "143h")}
    total = 0
    worst_abs = 0.0
    worst_rel = 0.0
    failures = []
    window_for = lambda index: ("1h" if index < 1 else
                                "6h" if index < 6 else "143h")
    for hour_index, label in enumerate(labels):
        fixture = args.fixtures / f"wind1_driver_{label}.inp"
        reference = args.out / f"original_{label}.txt"
        if not fixture.exists():
            raise RuntimeError(f"missing fixture {fixture.name}")
        wind1.run(binary, fixture, reference)
        original_u, original_v = read_original(reference)
        cpp_u = read_f32(args.fields / f"wind1_u_{label}.f32")
        cpp_v = read_f32(args.fields / f"wind1_v_{label}.f32")
        hour_abs = 0.0
        hour_rel = 0.0
        for name, original, candidate in (("u", original_u, cpp_u),
                                          ("v", original_v, cpp_v)):
            for index, (a, b) in enumerate(zip(original, candidate)):
                if not (math.isfinite(a) and math.isfinite(b)):
                    raise RuntimeError(f"{label}: nonfinite {name} at {index}")
                error = abs(a - b)
                if error > hour_abs:
                    hour_abs = error
                level = index // N
                per_level_abs[level] = max(per_level_abs[level], error)
                if abs(a) > 1.0e-3:
                    ratio = error / abs(a)
                    hour_rel = max(hour_rel, ratio)
                    per_level_rel[level] = max(per_level_rel[level], ratio)
                for window in ("1h", "6h", "143h"):
                    if window == "1h" and hour_index >= 1:
                        continue
                    if window == "6h" and hour_index >= 6:
                        continue
                    stats = windows[window]
                    stats["components"] += 1
                    stats["worst_abs_error_mps"] = max(
                        stats["worst_abs_error_mps"], error)
                    if abs(a) > 1.0e-3:
                        stats["worst_rel_error"] = max(
                            stats["worst_rel_error"], error / abs(a))
                if error > ABS_TOL and len(failures) < 12:
                    failures.append({"hour": label, "component": name,
                                     "index": index, "original": a,
                                     "cpp": b, "error": error})
        total += 2 * COMPONENTS
        worst_abs = max(worst_abs, hour_abs)
        worst_rel = max(worst_rel, hour_rel)
        per_hour[label] = {"max_abs_error_mps": hour_abs,
                           "max_rel_error": hour_rel}
    passed = not failures and all(
        stats["status"] == "PASS" for stats in report_windows(windows).values())
    report = {
        "status": ("PASS_REALCASE_STEP_ONE_ORIGINAL_WIND1_PLUS_SIMILT"
                   if passed else "FAIL"),
        "scope": ("real Hefei 2022 5 km case tree, 143 hourly labels; the "
                  "unchanged original WIND1+SIMILT driver is fed the same "
                  "station fixtures as the C++ producer"),
        "original_vendor_blob_sha1": wind1.SOURCE_SHA,
        "original_sources": [{"path": path.name,
                              "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
                             for path in sources],
        "abs_tolerance_mps": ABS_TOL,
        "hours_compared": len(labels),
        "components_compared": total,
        "worst_abs_error_mps": worst_abs,
        "worst_rel_error": worst_rel,
        "hours": per_hour,
        "levels": [{"level": k + 1,
                    "max_abs_error_mps": per_level_abs[k],
                    "max_rel_error": per_level_rel[k]}
                   for k in range(NZ)],
        "windows": report_windows(windows),
        "first_failures": failures,
    }
    (args.out / "realcase-step-one-parity.json").write_text(
        json.dumps(report, indent=2) + "\n")
    print(json.dumps({k: v for k, v in report.items() if k != "hours"},
                     indent=2))
    if not passed:
        raise SystemExit(1)

if __name__ == "__main__":
    main()
