#!/usr/bin/env python3
"""Independent genuine NOAA hour-three original CALMET vs native G64 P6F.

Original MET is a read-only comparator oracle; never an input to native G14.
All 45 fields (43 REAL4, 2 INT32) use frozen earlier scientific thresholds.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from pathlib import Path
import struct

from scripts.s4.s4r1c8i_compare_noaa_43_real_p6f import (
    F32, INT, LABELS, NC, NX, NY, NZ, fortran_records, tol
)

ORIGINAL_MET_SHA = "a7004fbf780212d58536be3957306c2aecc53abe2e58bfec870571b12d8b8e14"
FIRST_UTC = 202215201
THIRD_UTC = 202215203
FIELD_BYTES = 24 + 4 * NC


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def decode(raw: bytes, original: bool) -> dict:
    records = fortran_records(raw)
    if len(records) < 3 or len(records[0]) != 96:
        raise ValueError("CALMET 2.1 declaration malformed")
    if records[0][:16].decode("ascii").strip() != "CALMET.DAT":
        raise ValueError("foreign CALMET format")
    if len(records[1]) != 4:
        raise ValueError("CALMET NCOM missing")
    ncom, = struct.unpack("<i", records[1])
    if not 0 <= ncom <= 10000 or len(records) < ncom + 3:
        raise ValueError("CALMET comment count malformed")
    header = records[ncom + 2]
    if len(header) != 176:
        raise ValueError("CALMET OUTHD extent malformed")
    meta = (struct.unpack_from("<5i", header, 48) +
            struct.unpack_from("<4i", header, 80))
    expected = ((6 if original else 1), 1, NX, NY, NZ, 1, 2, 1, 0)
    if meta != expected:
        raise ValueError("CALMET original/native header identity drift")
    hourly = []
    for rec in records[ncom + 3:]:
        if len(rec) < 24:
            raise ValueError("CALMET hourly record truncated")
        a, asec, b, bsec = struct.unpack_from("<4i", rec, 8)
        if a == 0 and b == 0:
            continue
        if len(rec) != FIELD_BYTES:
            raise ValueError("CALMET 45-field hourly payload shape drift")
        hourly.append((rec[:8].decode("ascii"), (a, asec, b, bsec), rec[24:]))
    nh = 6 if original else 1
    if len(hourly) != 45 * nh:
        raise ValueError("CALMET original/native hourly cardinality drift")
    groups = [hourly[i * 45:(i + 1) * 45] for i in range(nh)]
    for i, group in enumerate(groups):
        when = FIRST_UTC + i if original else THIRD_UTC
        if [entry[0] for entry in group] != LABELS:
            raise ValueError("CALMET 45-field order/labels drift")
        if {entry[1] for entry in group} != {(when, 0, when, 3600)}:
            raise ValueError("CALMET original/native UTC clock drift")
    selected = groups[2] if original else groups[0]
    return {name: payload for name, _, payload in selected}


def compare(original: dict, native: dict) -> dict:
    if set(original) != set(LABELS) or set(native) != set(LABELS):
        raise ValueError("CALMET missing 45-field labels")
    fields = {}
    total = bitwise = exceed = 0
    first_differences = []
    for name in LABELS:
        lhs, rhs = original[name], native[name]
        if name in ("IPGT    ", "IRH     "):
            a, b = INT.unpack(lhs), INT.unpack(rhs)
            mismatch = sum(x != y for x, y in zip(a, b, strict=True))
            fields[name.strip()] = {"count": NC, "unequal_int32": mismatch}
            exceed += mismatch
            bitwise += NC - mismatch
            total += NC
        else:
            a, b = F32.unpack(lhs), F32.unpack(rhs)
            same = bad = 0
            maximum = 0.0
            first = None
            for k, (x, y) in enumerate(zip(a, b, strict=True)):
                if not math.isfinite(x) or not math.isfinite(y):
                    raise ValueError("nonfinite original/native P6F REAL4")
                if struct.pack("<f", x) == struct.pack("<f", y):
                    same += 1
                delta = abs(x - y)
                maximum = max(maximum, delta)
                if delta > tol(name, x, y):
                    bad += 1
                    if first is None:
                        first = {"i": k % NX + 1, "j": k // NX + 1,
                                 "original": x, "native": y,
                                 "abs_diff": delta, "frozen_limit": tol(name, x, y)}
                    if len(first_differences) < 25:
                        first_differences.append({"field": name.strip(),
                                                  "i": k % NX + 1,
                                                  "j": k // NX + 1,
                                                  "original": x, "native": y})
            fields[name.strip()] = {"count": NC, "bitwise_equal": same,
                                    "frozen_exceedances": bad,
                                    "max_abs": maximum,
                                    "first_exceedance": first}
            total += NC
            bitwise += same
            exceed += bad
    return {
        "status": ("PASS_SCOPED_HOUR3_ORIGINAL_NATIVE_P6F45_PRECOMMIT"
                   if exceed == 0 else "FAIL_HOUR3_ORIGINAL_NATIVE_P6F45"),
        "original_hour3_utc": THIRD_UTC,
        "compared_values": total,
        "bitwise_equal": bitwise,
        "frozen_tolerance_or_integer_exceedances": exceed,
        "fields": fields,
        "first_differences": first_differences,
        "g14_hour3_committed": False,
        "hour3_p6f_published": False,
        "hours4_6": "NOT_RUN",
        "p6_p7": "NOT_ACCEPTED",
        "independent_science_review": "NOT_RUN",
    }


def audit(original_path: Path, native_path: Path, native_sha: str) -> dict:
    if original_path.resolve() == native_path.resolve():
        raise ValueError("original/native cannot alias")
    if sha(original_path) != ORIGINAL_MET_SHA:
        raise ValueError("original MET SHA drift")
    if len(native_sha) != 64 or sha(native_path) != native_sha:
        raise ValueError("native P6F candidate SHA drift")
    result = compare(decode(original_path.read_bytes(), True),
                     decode(native_path.read_bytes(), False))
    result["original_met_sha256"] = ORIGINAL_MET_SHA
    result["native_candidate_sha256"] = native_sha
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("original_met", "native_candidate", "report"):
        parser.add_argument("--" + name.replace("_", "-"), type=Path, required=True)
    parser.add_argument("--expected-native-sha256", required=True)
    args = parser.parse_args()
    if args.report.exists():
        raise ValueError("refuse overwrite independent P6F report")
    result = audit(args.original_met, args.native_candidate,
                   args.expected_native_sha256)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(result, indent=2) + "\n")
    print(result["status"], result["bitwise_equal"], "/",
          result["compared_values"], "bitwise; exceedances",
          result["frozen_tolerance_or_integer_exceedances"])
    for name, stats in result["fields"].items():
        count = stats.get("frozen_exceedances", stats.get("unequal_int32", 0))
        if count:
            print("FAILED_FIELD", name, count, stats.get("first_exceedance"))
    if result["frozen_tolerance_or_integer_exceedances"]:
        raise SystemExit(3)


if __name__ == "__main__":
    main()
