#!/usr/bin/env python3
"""Independent real NOAA hour3 COMP stage12–15 native/original comparison.

Original sixhour Fortran trace is read only by this separate process.
No source/original intermediate is passed into the native G14 executable.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from pathlib import Path
import struct

from scripts.s4.s4r1c9r_original_hour3_comp_trace import decode, NC, NX, NY, NZ, HEADER
from scripts.s4.s4r1c9s_compare_hour3_comp12 import (
    ORIGINAL_TRACE_SHA, FIELDS as STAGE12_FIELDS, limit, compare as compare12,
)

FIELDS = {
    12: STAGE12_FIELDS,
    13: ("zi", "ziconv"),
    14: ("wstar",),
    15: ("temp3d",),
}


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def native_decode(raw: bytes) -> dict:
    off = 0
    result = {}
    for stage, fields in FIELDS.items():
        if off + HEADER.size > len(raw):
            raise ValueError("truncated native COMP header")
        if HEADER.unpack_from(raw, off) != (4, stage, NX, NY, NZ):
            raise ValueError("native COMP stage clock/grid mismatch")
        off += HEADER.size
        count = NC * (NZ if stage == 15 else len(fields))
        if off + 4 * count > len(raw):
            raise ValueError("truncated native COMP field")
        values = struct.unpack_from("<" + str(count) + "f", raw, off)
        off += 4 * count
        if any(not math.isfinite(x) for x in values):
            raise ValueError("nonfinite native COMP stage")
        result[stage] = values
    if off != len(raw):
        raise ValueError("native COMP trailing data")
    return result


def compare_stage(stage: int, original: tuple, native: tuple) -> dict:
    if stage == 12:
        return compare12(original, native)
    fields = FIELDS[stage]
    expected = NC * (NZ if stage == 15 else len(fields))
    if len(original) != expected or len(native) != expected:
        raise ValueError("original/native COMP stage size mismatch")
    stats = {}
    bitwise = exceed = 0
    for i, name in enumerate(fields):
        count = NC * NZ if stage == 15 else NC
        same = bad = 0
        max_abs = 0.0
        first = None
        for j in range(count):
            a, b = original[i * count + j], native[i * count + j]
            if not math.isfinite(a) or not math.isfinite(b):
                raise ValueError("nonfinite COMP stage original/native")
            if struct.pack("<f", a) == struct.pack("<f", b):
                same += 1
            delta = abs(a - b)
            max_abs = max(max_abs, delta)
            threshold = (2e-4 if stage in (14, 15)
                         else limit(name, a, b))
            if delta > threshold:
                bad += 1
                if first is None:
                    first = {"i": j % NX + 1, "j": (j // NX) % NY + 1,
                             "k": j // NC + 1, "original": a,
                             "native": b, "abs_diff": delta,
                             "frozen_limit": threshold}
        stats[name] = {"count": count, "bitwise_equal": same,
                       "frozen_exceedances": bad, "max_abs": max_abs,
                       "first_frozen_exceedance": first}
        bitwise += same
        exceed += bad
    return {"fields": stats, "compared_real4": expected,
            "bitwise_equal": bitwise, "frozen_exceedances": exceed}


def audit(original_trace: Path, native_trace: Path, native_sha: str) -> dict:
    if original_trace.resolve() == native_trace.resolve():
        raise ValueError("original/native alias")
    if sha(original_trace) != ORIGINAL_TRACE_SHA:
        raise ValueError("original COMP trace SHA drift")
    if len(native_sha) != 64 or sha(native_trace) != native_sha:
        raise ValueError("native COMP trace SHA drift")
    orig = decode(original_trace)
    native = native_decode(native_trace.read_bytes())
    stages = {}
    count = same = bad = 0
    for stage in FIELDS:
        result = compare_stage(stage, orig[(4, stage)], native[stage])
        stages[str(stage)] = result
        count += result["compared_real4"]
        same += result["bitwise_equal"]
        bad += result["frozen_exceedances"]
    return {
        "status": ("PASS_SCOPED_HOUR3_G26B_COMP_STAGE12_15_ORIGINAL_NATIVE"
                   if bad == 0 else
                   "FAIL_HOUR3_G26B_COMP_STAGE12_15_ORIGINAL_NATIVE"),
        "original_trace_sha256": ORIGINAL_TRACE_SHA,
        "native_trace_sha256": native_sha,
        "compared_real4": count,
        "bitwise_equal": same,
        "frozen_exceedances": bad,
        "stages": stages,
        "stage16_p6f": "NOT_RUN",
        "hour3_g14_commit": "NOT_RUN",
        "hours4_6": "NOT_RUN",
        "p6_p7": "NOT_ACCEPTED",
        "independent_science_review": "NOT_RUN",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("original_trace", "native_trace", "report"):
        parser.add_argument("--" + name.replace("_", "-"), type=Path, required=True)
    parser.add_argument("--expected-native-sha256", required=True)
    args = parser.parse_args()
    if args.report.exists():
        raise ValueError("refuse overwriting COMP audit")
    result = audit(args.original_trace, args.native_trace,
                   args.expected_native_sha256)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(result, indent=2) + "\n")
    print(result["status"], result["bitwise_equal"], "/",
          result["compared_real4"], "bitwise; exceedances",
          result["frozen_exceedances"])
    for stage, summary in result["stages"].items():
        for name, f in summary["fields"].items():
            print(stage, name, "exceedances", f["frozen_exceedances"],
                  "max_abs", f["max_abs"])
    if result["frozen_exceedances"]:
        raise SystemExit(3)


if __name__ == "__main__":
    main()
