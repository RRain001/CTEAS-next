#!/usr/bin/env python3
"""Independent, fail-closed CALMET third-hour G23/G24 wind-stage audit.

Reads immutable sixhour original Fortran stage90/100/110 and separately
produced native third-hour stage90/100/110; original never enters native G14.
Stage100 is observed in the same native SMOOTH invocation before DIVCEL.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from pathlib import Path
import struct

NX, NY, NZ = 82, 85, 9
NC = NX * NY
HEADER = struct.Struct("<5i")
ORIGINAL_SHA = "755fe44499ac8a53f3f959f29cdb28c1515ba6da1d719f198a78813fe9016995"
FROZEN_WIND_ABS_TOL = 2e-4  # s4r1c8i_compare_noaa_43_real_p6f.py
COUNTS = {90: 2 * NZ * NC, 100: 2 * NZ * NC, 110: (2 * NZ + NZ + 1) * NC}


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def decode(raw: bytes, hours: tuple[int, ...], stages: tuple[int, ...]) -> dict:
    offset = 0
    result = {}
    for hour in hours:
        for stage in stages:
            if offset + HEADER.size > len(raw):
                raise ValueError("truncated wind-tail header")
            header = HEADER.unpack_from(raw, offset)
            offset += HEADER.size
            if header != (hour, NX, NY, NZ, stage):
                raise ValueError(f"wrong source hour/grid/stage: {header}")
            size = COUNTS[stage] * 4
            if offset + size > len(raw):
                raise ValueError("truncated wind-tail REAL4 data")
            data = raw[offset:offset + size]
            offset += size
            result[(hour, stage)] = data
    if offset != len(raw):
        raise ValueError("unexpected trailing wind-tail data")
    return result


def compare(original: bytes, native: bytes, stage: int) -> dict:
    if len(original) != len(native) or len(original) != COUNTS[stage] * 4:
        raise ValueError("wind-tail stage shape mismatch")
    result = {}
    fields = ("u", "v") if stage != 110 else ("u", "v", "w")
    for field in fields:
        count = NZ * NC if field != "w" else (NZ + 1) * NC
        offset = 0 if field != "w" else 2 * NZ * NC
        stride = 2 if field != "w" else 1
        channel = 0 if field == "u" else (1 if field == "v" else 0)
        same = exceed = 0
        max_abs = 0.0
        first = None
        for i in range(count):
            index = (offset + stride * i + channel) * 4
            lhs, rhs = original[index:index + 4], native[index:index + 4]
            a, = struct.unpack("<f", lhs)
            b, = struct.unpack("<f", rhs)
            if not math.isfinite(a) or not math.isfinite(b):
                raise ValueError("nonfinite original/native wind field")
            if lhs == rhs:
                same += 1
            delta = abs(a - b)
            if delta > max_abs:
                max_abs = delta
            if delta > FROZEN_WIND_ABS_TOL:
                exceed += 1
                if first is None:
                    first = {"i": i % NX + 1, "j": (i // NX) % NY + 1,
                             "k": i // NC + 1, "original": a,
                             "native": b, "abs_diff": delta}
        result[field] = {"count": count, "bitwise_equal": same,
                         "frozen_exceedances": exceed, "max_abs": max_abs,
                         "first_exceedance": first}
    return result


def audit(original_path: Path, native_path: Path, expected_native_sha: str) -> dict:
    if original_path.resolve() == native_path.resolve():
        raise ValueError("original/native paths cannot alias")
    if sha(original_path) != ORIGINAL_SHA:
        raise ValueError("original wind-tail trace SHA drift")
    if len(expected_native_sha) != 64 or sha(native_path) != expected_native_sha:
        raise ValueError("native wind-tail trace SHA drift")
    original = decode(original_path.read_bytes(), tuple(range(2, 8)), (90, 100, 110))
    native = decode(native_path.read_bytes(), (4,), (90, 100, 110))
    fields = {}
    total = equal = exceed = 0
    for stage in (90, 100, 110):
        stats = compare(original[(4, stage)], native[(4, stage)], stage)
        for name, stat in stats.items():
            fields[f"{stage}:{name}"] = stat
            total += stat["count"]
            equal += stat["bitwise_equal"]
            exceed += stat["frozen_exceedances"]
    return {
        "status": ("PASS_SCOPED_HOUR3_G23_G24_STAGE90_100_110" if exceed == 0
                   else "FAIL_HOUR3_G23_G24_STAGE90_100_110"),
        "original_trace_sha256": ORIGINAL_SHA,
        "native_trace_sha256": expected_native_sha,
        "source": "REAL_NOAA_82x85x9_2SS_1US",
        "hour_end_utc": 4,
        "stage90_inter2": "COMPARED",
        "stage100_smooth": "COMPARED",
        "stage110_divcel_w": "COMPARED",
        "frozen_tolerance_mps": FROZEN_WIND_ABS_TOL,
        "frozen_tolerance_authority":
            "scripts/s4/s4r1c8i_compare_noaa_43_real_p6f.py",
        "fields": fields,
        "compared_real4": total,
        "bitwise_equal": equal,
        "frozen_exceedances": exceed,
        "native_original_data_injection": False,
        "g23_default_hour_gt1_guard": "UNCHANGED_REJECTS",
        "hour3_g14_commit": "NOT_RUN",
        "hour3_comp_p6f": "NOT_RUN",
        "s4_p6_p7": "NOT_ACCEPTED",
        "independent_science_review": "NOT_RUN",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("original_trace", "native_trace", "report"):
        parser.add_argument("--" + name.replace("_", "-"), type=Path, required=True)
    parser.add_argument("--expected-native-sha256", required=True)
    args = parser.parse_args()
    if args.report.exists():
        raise ValueError("refuse overwriting existing scientific evidence")
    result = audit(args.original_trace, args.native_trace, args.expected_native_sha256)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(result, indent=2) + "\n")
    print(result["status"], result["bitwise_equal"], "/", result["compared_real4"],
          "bitwise, exceedances", result["frozen_exceedances"])
    for name, stat in result["fields"].items():
        print(name, stat["frozen_exceedances"], stat["max_abs"])
    if result["frozen_exceedances"]:
        raise SystemExit(3)


if __name__ == "__main__":
    main()
