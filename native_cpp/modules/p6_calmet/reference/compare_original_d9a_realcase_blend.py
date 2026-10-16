#!/usr/bin/env python3
"""Numeric verdict for the real-case INTER2 blend against the *unchanged*
original CALMET INTER2 subroutine.

Reuses the independently verified INTER2 harness
(`compare_original_inter2`) to compile the frozen original routine, replays its
driver on every INTER2 fixture emitted by
`cteas_p6_realcase_wind_field --fixtures` and compares cell by cell against the
producer's `blend_u/v_<label>.f32` arrays.
"""
import argparse
import hashlib
import json
import math
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import compare_original_inter2 as inter2

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
    values = []
    for n, row in enumerate(rows):
        parts = row.split()
        expected = (n % NX + 1, (n // NX) % NY + 1, n // N + 1)
        if len(parts) != 4 or tuple(map(int, parts[:3])) != expected:
            raise RuntimeError(f"{path.name}: row order mismatch at {expected}")
        values.append(float(parts[3]))
    return values

def report_windows(windows):
    return {label: {**stats,
                    "status": "PASS" if stats["worst_abs_error_mps"] <= ABS_TOL
                    else "FAIL"}
            for label, stats in windows.items()}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--vendor", required=True, type=Path)
    parser.add_argument("--fields", required=True, type=Path)
    parser.add_argument("--fixtures", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    sources = inter2.extract_original(args.vendor, args.out)
    driver = args.out / "driver.for"
    driver.write_text(inter2.DRIVER)
    binary = args.out / "original_inter2_blend"
    inter2.run(["gfortran", "-std=legacy", "-O0", "-fno-automatic",
                "-ffixed-line-length-none", "-fallow-argument-mismatch",
                "-I" + str(args.vendor)] +
               [str(path) for path, _ in sources] +
               [str(driver), "-o", str(binary)])

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
        hour_abs = 0.0
        hour_rel = 0.0
        for component, name in ((0, "u"), (1, "v")):
            fixture = args.fixtures / f"inter2_{name}_{label}.inp"
            reference = args.out / f"original_inter2_{name}_{label}.txt"
            if not fixture.exists():
                raise RuntimeError(f"missing fixture {fixture.name}")
            inter2.run([binary, fixture, reference])
            original = read_original(reference)
            # This comparator anchors the pre-tail INTER2 stage; the closed
            # DIAGNO field (after SMOOTH/DIVCEL) lives in blend_*.f32.
            candidate = read_f32(args.fields / f"inter2_{name}_{label}.f32")
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
        # This verdict is about the pre-tail INTER2 stage (inter2_u/v_*.f32);
        # the closed DIAGNO field's own verdict lives in metadata.blend.verification.
        "status": ("PASS_REALCASE_BLEND_ORIGINAL_INTER2" if passed else "FAIL"),
        "scope": ("real Hefei 2022 5 km case tree, 143 hourly labels; the "
                  "unchanged original INTER2 is fed the same station values, "
                  "step-one field, landuse and unit observation weights as the "
                  "C++ producer"),
        "original_vendor_blob_sha1": inter2.BLOB,
        "original_sources": [{"path": path.name,
                              "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
                             for path, _ in sources],
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
    (args.out / "realcase-blend-parity.json").write_text(
        json.dumps(report, indent=2) + "\n")
    print(json.dumps({k: v for k, v in report.items() if k != "hours"},
                     indent=2))
    if not passed:
        raise SystemExit(1)

if __name__ == "__main__":
    main()
