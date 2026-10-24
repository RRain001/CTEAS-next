#!/usr/bin/env python3
"""Independent original-vs-native third-hour G26B stage12 audit, test-only.

No original MET, trace, source or intermediate arrays enter native C++.
Existing frozen MIXHT/G22 limits are used without tuning to current results.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from pathlib import Path
import struct

from scripts.s4.s4r1c9r_original_hour3_comp_trace import decode, NC, NX, NY, NZ, HEADER

ORIGINAL_TRACE_SHA = "4851f7be2d19df7a6e5e2cf5d73653c282cfea579b9c0b2444365a842d27a02e"
FIELDS = ("zi", "ziconv", "qh", "temp2d", "rho", "ustar", "el")


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for part in iter(lambda: stream.read(1 << 20), b""):
            h.update(part)
    return h.hexdigest()


def native_decode(raw: bytes) -> tuple[float, ...]:
    if len(raw) != HEADER.size + len(FIELDS) * NC * 4:
        raise ValueError("native G26B stage12 byte shape invalid")
    if HEADER.unpack_from(raw, 0) != (4, 12, NX, NY, NZ):
        raise ValueError("native G26B stage12 source clock/grid invalid")
    values = struct.unpack_from("<" + str(len(FIELDS) * NC) + "f", raw, HEADER.size)
    if any(not math.isfinite(x) for x in values):
        raise ValueError("native G26B stage12 nonfinite")
    return values


def limit(name: str, original: float, native: float) -> float:
    if name in ("zi", "ziconv"):
        return 0.005 + 5e-5 * max(abs(original), abs(native))
    if name == "qh":
        return 0.25
    if name == "temp2d":
        return 0.001
    if name == "rho":
        return 0.0001
    if name == "ustar":
        return 0.005
    if name == "el":
        return max(0.5, 0.01 * abs(original))
    raise ValueError("unregistered original COMP field tolerance")


def compare(original: tuple[float, ...], native: tuple[float, ...]) -> dict:
    if len(original) != NC * len(FIELDS) or len(native) != len(original):
        raise ValueError("COMP original/native field count mismatch")
    results = {}
    total = bitwise = exceed = 0
    for field, name in enumerate(FIELDS):
        same = bad = 0
        max_abs = 0.0
        first = None
        for cell in range(NC):
            a, b = original[field * NC + cell], native[field * NC + cell]
            if not math.isfinite(a) or not math.isfinite(b):
                raise ValueError("nonfinite original/native COMP")
            if struct.pack("<f", a) == struct.pack("<f", b):
                same += 1
            delta = abs(a - b)
            max_abs = max(max_abs, delta)
            if delta > limit(name, a, b):
                bad += 1
                if first is None:
                    first = {"i": cell % NX + 1, "j": cell // NX + 1,
                             "original": a, "native": b,
                             "abs_diff": delta, "frozen_limit": limit(name, a, b)}
        results[name] = {"count": NC, "bitwise_equal": same,
                         "frozen_exceedances": bad, "max_abs": max_abs,
                         "first_frozen_exceedance": first}
        total += NC
        bitwise += same
        exceed += bad
    return {
        "status": ("PASS_SCOPED_HOUR3_G26B_STAGE12_ORIGINAL_NATIVE"
                   if exceed == 0 else "FAIL_HOUR3_G26B_STAGE12_ORIGINAL_NATIVE"),
        "fields": results,
        "compared_real4": total,
        "bitwise_equal": bitwise,
        "frozen_exceedances": exceed,
        "original_source": "CALMET_6.5.0_SIXHOUR_COMP_STAGE12",
        "hour3_g14_commit": "NOT_RUN",
        "hour3_g26b_stage13_16": "NOT_RUN",
        "s4_p6_p7": "NOT_ACCEPTED",
        "independent_science_review": "NOT_RUN",
    }


def audit(original_trace: Path, native_trace: Path, native_sha: str) -> dict:
    if original_trace.resolve() == native_trace.resolve():
        raise ValueError("original/native paths alias")
    if sha(original_trace) != ORIGINAL_TRACE_SHA:
        raise ValueError("original COMP trace SHA drift")
    if len(native_sha) != 64 or sha(native_trace) != native_sha:
        raise ValueError("native G26B stage12 trace SHA drift")
    original = decode(original_trace)[(4, 12)]
    native = native_decode(native_trace.read_bytes())
    result = compare(original, native)
    result["original_trace_sha256"] = ORIGINAL_TRACE_SHA
    result["native_trace_sha256"] = native_sha
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("original_trace", "native_trace", "report"):
        parser.add_argument("--" + name.replace("_", "-"), type=Path, required=True)
    parser.add_argument("--expected-native-sha256", required=True)
    args = parser.parse_args()
    if args.report.exists():
        raise ValueError("refuse overwrite existing COMP stage12 report")
    result = audit(args.original_trace, args.native_trace,
                   args.expected_native_sha256)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(result, indent=2) + "\n")
    print(result["status"], result["bitwise_equal"], "/",
          result["compared_real4"], "bitwise; exceedances",
          result["frozen_exceedances"])
    for name, field in result["fields"].items():
        print(name, "frozen_exceedances", field["frozen_exceedances"],
              "max_abs", field["max_abs"])
    if result["frozen_exceedances"]:
        raise SystemExit(3)


if __name__ == "__main__":
    main()
