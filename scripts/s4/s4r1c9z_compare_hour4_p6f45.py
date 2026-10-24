#!/usr/bin/env python3
"""Fail-closed, original-versus-native NOAA hour-four CALMET 45-field audit.

Original Fortran six-hour file is read only here and NEVER by native P6.
Scope: local research-only fourth-hour precommit, not general P6 admission.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
import struct
from pathlib import Path
from scripts.s4.s4r1c8i_compare_noaa_43_real_p6f import (
    LABELS, F32, INT, NC, NX, NY, NZ, fortran_records, tol
)


def digest(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def read_hour(path: Path, expected_hours: int, hour_index: int = 3) -> dict[str, bytes]:
    records = fortran_records(path.read_bytes())
    if len(records) < 4 or len(records[0]) != 96 or (
        records[0][:16].decode("ascii").strip() != "CALMET.DAT"
    ):
        raise ValueError("CALMET.DAT 2.1 signature/header absent")
    if len(records[1]) != 4:
        raise ValueError("Invalid original/native NCOM record")
    (ncom,) = struct.unpack("<i", records[1])
    if not 0 <= ncom < 10000 or ncom + 3 > len(records):
        raise ValueError("Invalid CALMET comment count")
    header = records[ncom + 2]
    if len(header) != 176:
        raise ValueError("CALMET OUTHD incorrect length")
    dims = struct.unpack_from("<5i", header, 48)
    cardinality = struct.unpack_from("<4i", header, 80)
    if dims != (expected_hours, 1, NX, NY, NZ) or cardinality != (1, 2, 1, 0):
        raise ValueError(f"Selected NOAA source/header dimensions changed: {dims}/{cardinality}")
    hourly = []
    for record in records[ncom + 3:]:
        if len(record) < 24:
            raise ValueError("Truncated CALMET OUTHR/static record")
        clock = struct.unpack_from("<4i", record, 8)
        if clock[0] == 0 and clock[2] == 0:
            continue
        if len(record) != 24 + 4 * NC:
            raise ValueError("Wrong OUTHR 6970-cell REAL4/INTEGER4 payload")
        hourly.append((record[:8].decode("ascii"), clock, record[24:]))
    if len(hourly) != 45 * expected_hours:
        raise ValueError("Wrong number of source hourly fields")
    for idx in range(expected_hours):
        group = hourly[45 * idx:45 * (idx + 1)]
        if [label for label, _, _ in group] != LABELS:
            raise ValueError("CALMET 45-field order changed")
        expected_clock = 202215201 + (idx if expected_hours == 6 else hour_index)
        clocks = {clock for _, clock, _ in group}
        if clocks != {(expected_clock, 0, expected_clock, 3600)}:
            raise ValueError(f"CALMET hour {idx} clock changed: {clocks}")
    selected = (hour_index if expected_hours == 6 else 0)
    return {label: payload for label, _, payload in hourly[45 * selected:45 * (selected + 1)]}


def compare(original: Path, native: Path, original_sha: str, native_sha: str, report: Path) -> dict:
    if original.resolve() == native.resolve() or report.exists():
        raise ValueError("Original/native must be distinct and result must not exist")
    if digest(original) != original_sha or digest(native) != native_sha:
        raise ValueError("Independent source artifact SHA256 mismatch")
    ref = read_hour(original, 6)
    got = read_hour(native, 1)
    fields = {}
    total_bad = 0
    same_words = 0
    first_differences = []
    for label in LABELS:
        raw_a, raw_b = ref[label], got[label]
        equal = sum(raw_a[k:k + 4] == raw_b[k:k + 4] for k in range(0, 4 * NC, 4))
        same_words += equal
        aa, bb = (INT.unpack(raw_a), INT.unpack(raw_b)) if label in (
            "IPGT    ", "IRH     "
        ) else (F32.unpack(raw_a), F32.unpack(raw_b))
        exceed = 0
        biggest = 0.0
        for i, (a, b) in enumerate(zip(aa, bb, strict=True)):
            if label not in ("IPGT    ", "IRH     ") and not (
                math.isfinite(a) and math.isfinite(b)
            ):
                raise ValueError("Nonfinite source P6F field")
            diff = abs(a - b)
            biggest = max(biggest, diff)
            if (a != b) if label in ("IPGT    ", "IRH     ") else diff > tol(label, a, b):
                exceed += 1
                if len(first_differences) < 24:
                    first_differences.append({
                        "field": label.strip(), "i": i % NX + 1,
                        "j": i // NX + 1, "abs_diff": diff
                    })
        fields[label.strip()] = {
            "count": NC, "bitwise_equal": equal,
            "frozen_exceedances": exceed, "max_abs": biggest
        }
        total_bad += exceed
    status = ("PASS_SCOPED_HOUR4_ORIGINAL_NATIVE_P6F45_PRECOMMIT"
              if total_bad == 0 else "FAIL_HOUR4_ORIGINAL_NATIVE_P6F45")
    payload = {
        "status": status, "source_hour_utc": "2022-06-01 04:00–05:00",
        "original_met_sha256": original_sha, "native_candidate_sha256": native_sha,
        "original_hour_count": 6, "native_hour_count": 1,
        "grid": [NX, NY, NZ], "original_and_native_station_count": [2, 1],
        "field_count": 45, "compared_values": 45 * NC,
        "bitwise_equal": same_words, "frozen_tolerance_or_integer_exceedances": total_bad,
        "first_differences": first_differences, "fields": fields,
        "hour4_g14_atomic_commit": "NOT_RUN",
        "generic_p6": "NOT_ACCEPTED", "p7": "NOT_RUN",
        "independent_science_review": "NOT_RUN"
    }
    report.write_text(json.dumps(payload, indent=2) + "\n")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--original", type=Path, required=True)
    parser.add_argument("--native", type=Path, required=True)
    parser.add_argument("--original-sha256", required=True)
    parser.add_argument("--native-sha256", required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    result = compare(args.original, args.native, args.original_sha256,
                     args.native_sha256, args.report)
    print(result["status"], result["compared_values"],
          "values; exceedances", result["frozen_tolerance_or_integer_exceedances"],
          "bitwise", result["bitwise_equal"])
    if result["frozen_tolerance_or_integer_exceedances"]:
        raise SystemExit(3)


if __name__ == "__main__":
    main()
