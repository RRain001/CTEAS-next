#!/usr/bin/env python3
"""Independent read-only hour5 NOAA G23/G24 stage90/100/110 comparison.

Original six-hour Fortran trace is read only by THIS script. Never native C++.
Frozen 2e-4 m/s wind tolerance is imported unchanged from R1c9q.
"""
import argparse
import json
from pathlib import Path

from scripts.s4.s4r1c9q_compare_hour3_windtail import (
    ORIGINAL_SHA, FROZEN_WIND_ABS_TOL, compare, decode, sha
)

STAGES = (90, 100, 110)
HOUR5_UTC_END = 6


def audit(original_path: Path, native_path: Path, expected_native_sha: str):
    if original_path.resolve() == native_path.resolve():
        raise ValueError("original/native trace cannot alias")
    if sha(original_path) != ORIGINAL_SHA:
        raise ValueError("frozen original six-hour windtail SHA drift")
    if len(expected_native_sha) != 64 or sha(native_path) != expected_native_sha:
        raise ValueError("native hour5 windtail SHA drift")
    original = decode(original_path.read_bytes(), tuple(range(2, 8)), STAGES)
    native = decode(native_path.read_bytes(), (HOUR5_UTC_END,), STAGES)
    field_stats = {}
    total = equal = exceeded = 0
    for stage in STAGES:
        stat = compare(original[(HOUR5_UTC_END, stage)],
                       native[(HOUR5_UTC_END, stage)], stage)
        for field, result in stat.items():
            field_stats[f"{stage}:{field}"] = result
            total += result["count"]
            equal += result["bitwise_equal"]
            exceeded += result["frozen_exceedances"]
    return dict(
        status=("PASS_SCOPED_HOUR5_G23_G24_STAGE90_100_110"
                if not exceeded else "FAIL_HOUR5_G23_G24_STAGE90_100_110"),
        source="REAL_NOAA_82x85x9_2SS_1US",
        hour_end_utc=HOUR5_UTC_END,
        original_trace_sha256=ORIGINAL_SHA,
        native_trace_sha256=expected_native_sha,
        frozen_tolerance_mps=FROZEN_WIND_ABS_TOL,
        frozen_authority="scripts/s4/s4r1c9q_compare_hour3_windtail.py",
        compared_real4=total, bitwise_equal=equal,
        frozen_exceedances=exceeded, fields=field_stats,
        fifth_hour_g14_committed=False,
        fifth_hour_comp_p6f="NOT_RUN", real_hour6="NOT_RUN",
        s4_p6_p7="NOT_ACCEPTED",
        scientific_independent_review="NOT_RUN",
        native_original_data_injection=False,
        g23_default_hour_gt1_guard="UNCHANGED_REJECTS",
    )


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for key in ("original_trace", "native_trace", "report"):
        p.add_argument("--" + key.replace("_", "-"), type=Path, required=True)
    p.add_argument("--expected-native-sha256", required=True)
    ns = p.parse_args()
    if ns.report.exists():
        raise ValueError("refuse overwrite scoped windtail audit")
    report = audit(ns.original_trace, ns.native_trace,
                   ns.expected_native_sha256)
    ns.report.parent.mkdir(parents=True, exist_ok=True)
    ns.report.write_text(json.dumps(report, indent=2) + "\n")
    print(report["status"], report["bitwise_equal"], "/",
          report["compared_real4"], "REAL4",
          "frozen_exceedances", report["frozen_exceedances"])
    if report["frozen_exceedances"]:
        for name, field in report["fields"].items():
            if field["frozen_exceedances"]:
                print("FIRST_DIFF", name, field["first_exceedance"])
        raise SystemExit(3)


if __name__ == "__main__":
    main()
