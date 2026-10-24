#!/usr/bin/env python3
"""Read-only original/native real NOAA hour5 COMP stage12-15 audit.

The Fortran trace and native trace must be independent files. All thresholds
are inherited unchanged from the validated hour3 stage12-15 comparator.
This tool does not grant G14 commit, production P6 or science admission.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import struct

from scripts.s4.s4r1c9r_original_hour3_comp_trace import (
    decode, NC, NX, NY, NZ, HEADER
)
from scripts.s4.s4r1c9t_compare_hour3_comp15 import (
    FIELDS, compare_stage, sha
)
from scripts.s4.s4r1c9s_compare_hour3_comp12 import ORIGINAL_TRACE_SHA

HOUR5_END_UTC = 6


def native_decode(raw: bytes, *, stage_count: int = 4) -> dict:
    if stage_count not in (1, 4):
        raise ValueError("only stage12 or ordered stage12-15 supported")
    result = {}
    offset = 0
    stages = (12,) if stage_count == 1 else (12, 13, 14, 15)
    for stage in stages:
        if offset + HEADER.size > len(raw):
            raise ValueError("truncated native hour5 COMP header")
        if HEADER.unpack_from(raw, offset) != (
            HOUR5_END_UTC, stage, NX, NY, NZ
        ):
            raise ValueError("native hour5 COMP clock/grid/stage mismatch")
        offset += HEADER.size
        n = NC * (NZ if stage == 15 else len(FIELDS[stage]))
        if offset + 4 * n > len(raw):
            raise ValueError("truncated native hour5 COMP field")
        values = struct.unpack_from("<" + str(n) + "f", raw, offset)
        if any(not math.isfinite(value) for value in values):
            raise ValueError("nonfinite native hour5 COMP field")
        result[stage] = values
        offset += n * 4
    if offset != len(raw):
        raise ValueError("trailing native hour5 COMP data")
    return result


def audit(original_trace: Path, native_trace: Path, expected_native_sha: str,
          *, stage_count: int = 4) -> dict:
    if original_trace.resolve() == native_trace.resolve():
        raise ValueError("forbid original/native trace alias")
    if sha(original_trace) != ORIGINAL_TRACE_SHA:
        raise ValueError("frozen original six-hour COMP trace SHA drift")
    if len(expected_native_sha) != 64 or sha(native_trace) != expected_native_sha:
        raise ValueError("native hour5 COMP SHA drift")
    original = decode(original_trace)
    native = native_decode(native_trace.read_bytes(), stage_count=stage_count)
    stages = {}
    compared = equal = exceeded = 0
    for stage, values in native.items():
        result = compare_stage(stage, original[(HOUR5_END_UTC, stage)], values)
        stages[str(stage)] = result
        compared += result["compared_real4"]
        equal += result["bitwise_equal"]
        exceeded += result["frozen_exceedances"]
    return {
        "status": ("PASS_SCOPED_HOUR5_G26B_COMP_" +
                   ("STAGE12" if stage_count == 1 else "STAGE12_15")
                   if exceeded == 0 else "FAIL_HOUR5_G26B_COMP"),
        "source": "REAL_NOAA_82x85_2SS_1US",
        "hour_end_utc": HOUR5_END_UTC,
        "original_trace_sha256": ORIGINAL_TRACE_SHA,
        "native_trace_sha256": expected_native_sha,
        "frozen_thresholds_from": "scripts/s4/s4r1c9t_compare_hour3_comp15.py",
        "compared_real4": compared,
        "bitwise_equal": equal,
        "frozen_exceedances": exceeded,
        "stages": stages,
        "fifth_hour_g14_committed": False,
        "fifth_hour_p6f": "NOT_RUN",
        "hour6": "NOT_RUN",
        "s4_p6_p7": "NOT_ACCEPTED",
        "independent_science_review": "NOT_RUN",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("original_trace", "native_trace", "report"):
        parser.add_argument("--" + name.replace("_", "-"),
                            type=Path, required=True)
    parser.add_argument("--expected-native-sha256", required=True)
    parser.add_argument("--stage-count", type=int, choices=(1, 4), default=4)
    args = parser.parse_args()
    if args.report.exists():
        raise ValueError("refuse overwrite of existing science report")
    report = audit(args.original_trace, args.native_trace,
                   args.expected_native_sha256, stage_count=args.stage_count)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + "\n")
    print(report["status"], report["bitwise_equal"], "/",
          report["compared_real4"], "frozen_exceedances",
          report["frozen_exceedances"])
    if report["frozen_exceedances"]:
        for stage, stats in report["stages"].items():
            for name, field in stats["fields"].items():
                if field["frozen_exceedances"]:
                    print("FIRST_DIFF", stage, name,
                          field["first_frozen_exceedance"])
        raise SystemExit(3)


if __name__ == "__main__":
    main()
