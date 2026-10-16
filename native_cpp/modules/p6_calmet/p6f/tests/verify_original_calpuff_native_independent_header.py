#!/usr/bin/env python3
"""P6F end-to-end: original CALPUFF must consume a native-source OUTHD header.

Compare the *same native P6D/P6E 143-hour hourly meteorology* with its old
borrowed comments and with independently generated GEO.DAT/met.inp comments.
Original unmodified CALPUFF 7.2.1 must read both and output byte-identical
concentration data. Structural comparison proves the controls, statics, and
hourly payloads are identical, so only the header comment provenance changes.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import shutil
import struct
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import verify_original_calpuff_reads_written_calmet as oracle


def fail(msg: str) -> None:
    raise RuntimeError("FAIL_P6F_ORIGINAL_P7_NATIVE_HEADER: " + msg)


def compare_noncomment_records(native: bytes, source: bytes) -> tuple[int, int, int]:
    a = oracle.walk_records(native)
    b = oracle.walk_records(source)
    if len(a) < 100 or len(b) < 100:
        fail("CALMET.DAT record inventory incomplete")
    if a[0][1] != 96 or b[0][1] != 96:
        fail("CALMET file declaration not 96 bytes")
    def number_of_comments(data: bytes, records: list) -> int:
        if records[1][1] != 4:
            fail("NCOM record not four bytes")
        return struct.unpack_from("<i", data, records[1][2])[0]
    na, nb = number_of_comments(native, a), number_of_comments(source, b)
    if not 1 <= na <= 10000 or not 1 <= nb <= 10000:
        fail("invalid NCOM")
    if na == nb:
        fail("independent OUTHD comment source did not change NCOM")
    first_comment = source[b[2][2]:b[2][2] + b[2][1]]
    if not first_comment.startswith(b"CTEAS P6F native OUTHD from source"):
        fail("first independent comment not from source-only generator")
    if len(a) - (na + 2) != len(b) - (nb + 2):
        fail("non-comment record count changed")
    matched = 0
    for ia, ib in zip(a[na + 2:], b[nb + 2:]):
        # 176-byte OUTHD numeric block, statics, 143h weather must match.
        payload_a = native[ia[0]:ia[0] + 8 + ia[1]]
        payload_b = source[ib[0]:ib[0] + 8 + ib[1]]
        if payload_a != payload_b:
            fail(f"control/static/hourly record changed at index {matched}")
        matched += 1
    if matched < 6300:
        fail("the number of meteorological records is unexpectedly low")
    return na, nb, matched


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--native-weather", type=pathlib.Path, required=True)
    parser.add_argument("--independent-header-weather", type=pathlib.Path, required=True)
    parser.add_argument("--vendor", type=pathlib.Path, required=True)
    parser.add_argument("--puff-control", type=pathlib.Path, required=True)
    parser.add_argument("--work", type=pathlib.Path, required=True)
    parser.add_argument("--report", type=pathlib.Path, required=True)
    parser.add_argument("--fortran", default="gfortran-11")
    parser.add_argument("--max-seconds", type=int, default=600)
    args = parser.parse_args()
    for v in (args.native_weather, args.independent_header_weather,
              args.puff_control):
        if not v.is_file():
            fail("missing input " + str(v))
    args.work.mkdir(parents=True, exist_ok=True)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    raw_native = args.native_weather.read_bytes()
    raw_new = args.independent_header_weather.read_bytes()
    if raw_native == raw_new:
        fail("native and independent OUTHD are byte identical; no new header")
    original_comments, new_comments, matched = compare_noncomment_records(
        raw_native, raw_new)
    built = oracle.build_original(args.vendor.resolve(), args.fortran,
                                  (args.work / "original-build").resolve())
    original_binary = pathlib.Path(built["binary_path"])
    results = {}
    for label, content in (("native_borrowed_header", raw_native),
                           ("native_independent_header", raw_new)):
        run_root = args.work / label
        run_root.mkdir(exist_ok=True)
        run_dir = oracle.stage(run_root, args.puff_control.resolve(), content)
        result = oracle.execute(run_dir, original_binary, args.max_seconds)
        summary = oracle.require_clean_run(result, label, 143)
        summary["listing_echo"] = oracle.listing_evidence(result["listing"])
        summary["concentration"] = oracle.concentration_stats(result["concentration"])
        results[label] = summary
    old, new = (results[k] for k in ("native_borrowed_header",
                                    "native_independent_header"))
    full_binary_equal = old["concentration_sha256"] == new["concentration_sha256"]
    hourly_payload_equal = (
        old["concentration"]["payload_sha256"] ==
        new["concentration"]["payload_sha256"])
    if new["concentration"]["hourly_records"] != 143:
        fail("original CALPUFF did not write 143h of concentrations")
    old_file = (args.work/"native_borrowed_header"/"run"/"puff"/"puff.con").read_bytes()
    new_file = (args.work/"native_independent_header"/"run"/"puff"/"puff.con").read_bytes()
    old_records = oracle.walk_records(old_file)
    new_records = oracle.walk_records(new_file)
    first_record_difference = next(
        (i for i,(a,b) in enumerate(zip(old_records,new_records))
         if old_file[a[0]:a[0]+8+a[1]] != new_file[b[0]:b[0]+8+b[1]]),
        None)
    changed_records = sum(
        old_file[a[0]:a[0]+8+a[1]] != new_file[b[0]:b[0]+8+b[1]]
        for a,b in zip(old_records,new_records))
    result = {
        "status": "PASS_P6F_ORIGINAL_CALPUFF_NATIVE_INDEPENDENT_HEADER",
        "original_fortran": built,
        "old_comments": original_comments,
        "new_comments": new_comments,
        "identical_noncomment_records": matched,
        "old_met_sha256": oracle.sha256_bytes(raw_native),
        "new_met_sha256": oracle.sha256_bytes(raw_new),
        "calpuff_original_143h": results,
        "concentration_full_file_bit_equal": full_binary_equal,
        "concentration_hourly_payload_bit_equal": hourly_payload_equal,
        "concentration_first_changed_record": first_record_difference,
        "concentration_changed_records": changed_records,
        "concentration_old_records": len(old_records),
        "concentration_new_records": len(new_records),
        "source_independence_limit": (
            "header/states independently generated from GEO/deck; "
            "hourly C++ payload is from native P6D/P6E, but producer still "
            "consumes frozen original output as a case-control envelope"
        ),
    }
    args.report.write_text(json.dumps(result, indent=2) + "\n")
    print("P6F_ORIGINAL_CALPUFF_CONC_COMPARISON "
          f"file_equal={full_binary_equal} hourly_payload_equal={hourly_payload_equal} "
          f"first_changed_record={first_record_difference} changed_records={changed_records}")
    if not hourly_payload_equal:
        fail("actual 143h floating concentration grids changed with the OUTHD header")
    print("PASS_P6F_ORIGINAL_CALPUFF_NATIVE_INDEPENDENT_HEADER "
          f"old_comments={original_comments} new_comments={new_comments} "
          f"identical_noncomment_records={matched} "
          f"puff_con_sha256={new['concentration_sha256']}")


if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError, ValueError) as e:
        print(e, file=sys.stderr)
        sys.exit(1)
