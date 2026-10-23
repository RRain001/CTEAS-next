#!/usr/bin/env python3
"""Fail-closed, read-only NOAA hour-two original CALMET vs G14 native P6F audit.

Original MET.DAT is an *oracle to this standalone comparator only*: never
supplied to C++ G14. The native file is an uncommitted forensic candidate,
not an accepted hourly production result. Strict frozen field tolerances are
imported from the already established first-hour comparator.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import struct
import tempfile
from pathlib import Path

from scripts.s4.s4r1c8i_compare_noaa_43_real_p6f import (
    F32, INT, LABELS, NC, NX, NY, NZ, fortran_records, tol
)

FIRST_UTC = 202215201
SECOND_UTC = 202215202
FIELD_BYTES = 24 + 4 * NC
INTERVAL = (SECOND_UTC, 0, SECOND_UTC, 3600)


def file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def decode(path: Path, *, original: bool):
    data = path.read_bytes()
    records = fortran_records(data)
    if len(records) < 3 or len(records[0]) != 96:
        raise ValueError("invalid CALMET 2.1 declaration")
    if records[0][:16].decode("ascii").strip() != "CALMET.DAT":
        raise ValueError("foreign file, not CALMET.DAT 2.1")
    if len(records[1]) != 4:
        raise ValueError("CALMET missing NCOM")
    ncom, = struct.unpack("<i", records[1])
    if not 0 <= ncom <= 10000 or len(records) < ncom + 3:
        raise ValueError("CALMET comment count invalid")
    head = records[ncom + 2]
    if len(head) != 176:
        raise ValueError("CALMET OUTHD extent invalid")
    meta = struct.unpack_from("<5i", head, 48) + struct.unpack_from("<4i", head, 80)
    expected = ((6 if original else 1), 1, NX, NY, NZ, 1, 2, 1, 0)
    if meta != expected:
        raise ValueError(f"source mode/grid/stations differ: {meta} != {expected}")
    hourly = []
    for rec in records[ncom + 3:]:
        if len(rec) < 24:
            raise ValueError("truncated CALMET static/hourly record")
        a, asec, b, bsec = struct.unpack_from("<4i", rec, 8)
        if a == 0 and b == 0:
            continue  # original read-only static records
        if len(rec) != FIELD_BYTES:
            raise ValueError("CALMET 45-field hourly record length invalid")
        hourly.append((rec[:8].decode("ascii"), (a, asec, b, bsec), rec[24:]))
    expected_hours = 6 if original else 1
    if len(hourly) != expected_hours * 45:
        raise ValueError("CALMET hourly record count inconsistent with source")
    groups = [hourly[i * 45:(i + 1) * 45] for i in range(expected_hours)]
    for i, group in enumerate(groups):
        expected_utc = FIRST_UTC + i if original else SECOND_UTC
        if [entry[0] for entry in group] != LABELS:
            raise ValueError("CALMET field order or labels differ from original")
        if {entry[1] for entry in group} != {
                (expected_utc, 0, expected_utc, 3600)}:
            raise ValueError("CALMET 45-field source hourly clock drift")
    group = groups[1] if original else groups[0]
    return {name: payload for name, _, payload in group}


def analyze(original: Path, native: Path, report: Path):
    if original.resolve() == native.resolve():
        raise ValueError("original and native candidate must be different files")
    reference = decode(original, original=True)
    candidate = decode(native, original=False)
    first_differences = []
    per_field = {}
    errors = 0
    words = 0
    for label in LABELS:
        if label in ("IPGT    ", "IRH     "):
            lhs, rhs = INT.unpack(reference[label]), INT.unpack(candidate[label])
            unequal = 0
            for i, (a, b) in enumerate(zip(lhs, rhs, strict=True)):
                if a != b:
                    unequal += 1
                    if len(first_differences) < 25:
                        first_differences.append({"field": label, "i": i % NX + 1,
                            "j": i // NX + 1, "original": a, "native": b})
            per_field[label.strip()] = {"unequal_int32": unequal}
            errors += unequal
        else:
            lhs, rhs = F32.unpack(reference[label]), F32.unpack(candidate[label])
            exceed, maximum, worst = 0, 0.0, None
            for i, (a, b) in enumerate(zip(lhs, rhs, strict=True)):
                if not (math.isfinite(a) and math.isfinite(b)):
                    raise ValueError(f"nonfinite original/native {label!r} field")
                delta = abs(a - b)
                if delta > maximum:
                    maximum = delta
                    worst = {"i": i % NX + 1, "j": i // NX + 1,
                        "original": a, "native": b, "abs": delta}
                if delta > tol(label, a, b):
                    exceed += 1
                    if len(first_differences) < 25:
                        first_differences.append({"field": label, "i": i % NX + 1,
                            "j": i // NX + 1, "original": a, "native": b,
                            "abs": delta})
            per_field[label.strip()] = {
                "exceed_frozen_tolerance": exceed,
                "max_abs": maximum, "worst": worst}
            errors += exceed
        words += NC
    if words != 313650:
        raise ValueError("45 original/native fields not exhaustively compared")
    result = {
        "status": ("PASS_SCOPED_ORIGINAL_NATIVE_HOUR2_FULL45"
                   if errors == 0 else "FAIL_ORIGINAL_NATIVE_HOUR2_FULL45"),
        "source": "PRISTINE_ORIGINAL_SIX_HOUR_MET_VS_UNCOMMITTED_G14_HOUR2",
        "original_sha256": file_sha(original),
        "native_forensic_sha256": file_sha(native),
        "original_hours": 6, "native_hours": 1,
        "hour": "2022-06-01T02:00:00Z/03:00:00Z",
        "source_grid": [NX, NY, NZ], "stations": [2, 1, 0],
        "fields_compared": 45, "words_compared": words,
        "frozen_tolerance_or_integer_exceedances": errors,
        "first_differences": first_differences, "per_field": per_field,
        "original_met_supplied_to_native": False,
        "g14_hour2_committed": False, "production_p6": "NOT_ACCEPTED",
        "general_p7": "NOT_ACCEPTED", "wet_deposition": "NOT_ACCEPTED"}
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print("S4R1C9G_NOAA_HOUR2_ORIGINAL_NATIVE_FULL45=" + result["status"])
    print("S4R1C9G_WORDS_COMPARED=313650")
    print("S4R1C9G_EXCEEDANCES=" + str(errors))
    print("S4R1C9G_HOUR2_G14_COMMIT_AND_PRODUCTION=NOT_ACCEPTED")
    return errors == 0


def selftest():
    """Synthetic transport/record-decoder regression ONLY, not science."""
    fbytes = struct.pack("<" + str(NC) + "f", *([280.0] * NC))
    ibytes = struct.pack("<" + str(NC) + "i", *([4] * NC))
    def record(body):
        return struct.pack("<i", len(body)) + body + struct.pack("<i", len(body))
    def build(hours, *, mutate_label=None, bad_clock=False):
        out = [record(b"CALMET.DAT".ljust(96, b" ")),
               record(struct.pack("<i", 0))]
        header = bytearray(176)
        struct.pack_into("<5i", header, 48, hours, 1, NX, NY, NZ)
        struct.pack_into("<4i", header, 80, 1, 2, 1, 0)
        out.append(record(header))
        for hi in range(hours):
            utc = FIRST_UTC + hi if hours == 6 else SECOND_UTC
            for label in LABELS:
                payload = ibytes if label in ("IPGT    ", "IRH     ") else fbytes
                if mutate_label == label and (hours == 1 or hi == 1):
                    altered = bytearray(payload)
                    altered[:4] = (struct.pack("<i", 3) if label == "IPGT    "
                                   else struct.pack("<f", 279.0))
                    payload = bytes(altered)
                this_utc = utc + (1 if bad_clock else 0)
                out.append(record(label.encode("ascii") +
                    struct.pack("<4i", this_utc, 0, this_utc, 3600) + payload))
        return b"".join(out)
    with tempfile.TemporaryDirectory(prefix="s4r1c9g-test-") as tmp:
        root = Path(tmp)
        original, native, report = (root / p for p in ("original.dat", "native.dat", "report.json"))
        original.write_bytes(build(6))
        native.write_bytes(build(1))
        assert analyze(original, native, report)
        assert json.loads(report.read_text())["words_compared"] == 313650
        for label in ("IPGT    ", "T-LEV  1"):
            native.write_bytes(build(1, mutate_label=label))
            assert not analyze(original, native, report)
            assert json.loads(report.read_text())["frozen_tolerance_or_integer_exceedances"] == 1
        native.write_bytes(build(1, bad_clock=True))
        try:
            analyze(original, native, report)
        except ValueError as exc:
            assert "hourly clock" in str(exc)
        else:
            raise AssertionError("hour2 wrong-clock negative test bypassed")
        native.write_bytes(build(1))
        assert analyze(original, native, report)
    print("S4R1C9G_PARSER_SELFTEST=PASS_SYNTHETIC_ONLY")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=("compare", "selftest"))
    ap.add_argument("--original", type=Path)
    ap.add_argument("--native", type=Path)
    ap.add_argument("--report", type=Path)
    args = ap.parse_args()
    if args.mode == "selftest":
        selftest()
    else:
        if any(x is None for x in (args.original, args.native, args.report)):
            ap.error("compare needs original, native, report")
        if not analyze(args.original, args.native, args.report):
            raise SystemExit(3)


if __name__ == "__main__":
    main()
