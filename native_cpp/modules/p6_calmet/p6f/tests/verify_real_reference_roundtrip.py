#!/usr/bin/env python3
"""P6F frozen-reference byte-identity CTest.

Ground truth for the P6F CALMET.DAT 2.1 writer: parsing the frozen real 2022
reference met.dat into explicit field arrays and serialising it back must
reproduce the file byte for byte (same SHA-256), the structural inventory the
writer reports must agree with an independent Python walk of the same bytes,
and the independent P7 CALMET.DAT decoder must accept the re-serialised file
and decode exactly the same content as the frozen original.

Negative cases are part of the gate: a corrupted, truncated or marker-damaged
copy must be rejected instead of silently accepted.

Only the standard library is used; the P7 decoder is invoked read-only.
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import pathlib
import struct
import subprocess
import sys
import tempfile

UTC = datetime.timezone.utc

FROZEN_SHA256 = "b1823cda92280888d70b00961ab39486036a3086e18637fff21efb4f4b237d30"
FROZEN_BYTES = 64762556
FROZEN_RECORDS = 7562
FROZEN_COMMENTS = 1114
FROZEN_INTERVALS = 143
RECORD_HEADER_BYTES = 24
MISSING_REAL = struct.pack("<f", 9999.0)
MISSING_INT = struct.pack("<i", 9999)
STATIC_LABELS = ("ZFACE", "XSSTA", "YSSTA", "XUSTA", "YUSTA", "XPSTA", "YPSTA",
                 "Z0", "ILANDU", "ELEV", "XLAI", "NEARS")


def fail(message: str) -> None:
    print("P6F_REAL_REFERENCE_FAIL " + message)
    sys.exit(1)


def run(command: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run([str(part) for part in command], capture_output=True,
                          text=True)


def expected_labels(nz: int, npsta: int, lcalgrd: bool = True,
                    irtype: int = 1) -> list[str]:
    """The OUTHR label order, derived here independently of the C++ writer."""
    labels: list[str] = []
    for level in range(1, nz + 1):
        labels.append(f"U-LEV{level:>3}")
        labels.append(f"V-LEV{level:>3}")
        if lcalgrd:
            labels.append(f"WFACE{level:>3}")
    if lcalgrd and irtype != 0:
        labels += [f"T-LEV{level:>3}" for level in range(1, nz + 1)]
    if irtype == 0:
        return labels
    labels += ["IPGT", "USTAR", "ZI", "EL", "WSTAR"]
    if npsta != 0:
        labels.append("RMM")
    labels += ["TEMPK", "RHO", "QSW", "IRH"]
    if npsta != 0:
        labels.append("IPCODE")
    return labels


def walk(data: bytes) -> list[tuple[int, int, int]]:
    """(record offset, payload length, payload offset) of every Fortran record."""
    records: list[tuple[int, int, int]] = []
    offset = 0
    while offset + 8 <= len(data):
        (length,) = struct.unpack_from("<i", data, offset)
        if length < 0 or offset + 8 + length > len(data):
            fail(f"damaged record length {length} at offset {offset}")
        (trailer,) = struct.unpack_from("<i", data, offset + 4 + length)
        if trailer != length:
            fail(f"record markers disagree at offset {offset}")
        records.append((offset, length, offset + 4))
        offset += 8 + length
    if offset != len(data):
        fail("the record walk does not reach the end of the file")
    return records


def stamp(clock: int, seconds: int) -> datetime.datetime:
    """Explicit start/end instant of one written field record."""
    year, rest = divmod(clock, 100000)
    julian, hour = divmod(rest, 100)
    if not (2000 <= year <= 2100 and 1 <= julian <= 366 and 0 <= hour <= 23
            and 0 <= seconds <= 86400):
        fail(f"invalid written time label ({clock},{seconds})")
    return (datetime.datetime(year, 1, 1, tzinfo=UTC) +
            datetime.timedelta(days=julian - 1, hours=hour, seconds=seconds))


def static_words(label: str, nx: int, ny: int, nz: int, nssta: int,
                 nusta: int, npsta: int) -> int:
    """Word count the original OUTHD writes for one static record."""
    cells = nx * ny
    if label == "ZFACE":
        return nz + 1
    if label in ("XSSTA", "YSSTA"):
        return nssta
    if label in ("XUSTA", "YUSTA"):
        return nusta
    if label in ("XPSTA", "YPSTA"):
        return npsta
    return cells  # Z0, ILANDU, ELEV, XLAI, NEARS


def aligned_missing(payload: bytes, pattern: bytes, count: int) -> int:
    """XMISS values of one payload, checked at 4-byte word alignment."""
    if pattern not in payload:
        return 0
    total = 0
    for offset in range(RECORD_HEADER_BYTES, RECORD_HEADER_BYTES + 4 * count, 4):
        if payload[offset:offset + 4] == pattern:
            total += 1
    return total


def independent_inventory(data: bytes, nx: int, ny: int, nz: int,
                          npsta: int) -> dict:
    """Structural inventory computed by this script, not by the C++ writer."""
    records = walk(data)
    cells = nx * ny
    labels = expected_labels(nz, npsta)
    declaration = records[0]
    if declaration[1] != 96:
        fail("declaration record must be 96 bytes")
    if not data[declaration[2]:declaration[2] + 96].startswith(b"CALMET.DAT"):
        fail("declaration does not start with CALMET.DAT")
    (ncom,) = struct.unpack_from("<i", data, records[1][2])
    if ncom != FROZEN_COMMENTS:
        fail(f"comment count {ncom} != {FROZEN_COMMENTS}")
    for index in range(2, 2 + ncom):
        if records[index][1] != 132:
            fail("comment record is not 132 bytes")
    controls = data[records[2 + ncom][2]:]
    if records[2 + ncom][1] != 176:
        fail("controls record must be 176 bytes")
    nx_b, ny_b, nz_b = struct.unpack_from("<3i", controls, 56)
    irlg, irtype = struct.unpack_from("<2i", controls, 48)
    iwfcod, nssta, nusta, npsta_b = struct.unpack_from("<4i", controls, 80)
    dgrid = struct.unpack_from("<f", controls, 68)[0]
    timezone = controls[40:48].decode("ascii")
    if (nx_b, ny_b, nz_b) != (nx, ny, nz):
        fail(f"controls grid {(nx_b, ny_b, nz_b)} != {(nx, ny, nz)}")
    if (irlg, irtype, iwfcod) != (FROZEN_INTERVALS, 1, 1):
        fail("controls run settings are not the frozen ones")
    if (nssta, nusta, npsta_b) != (1, 1, npsta):
        fail("controls station counts are not the frozen ones")
    if abs(dgrid - 100.0) > 1e-6 or timezone != "UTC+0000":
        fail("controls grid spacing/time zone are not the frozen ones")
    (nlu,) = struct.unpack_from("<i", controls, 100)
    ilandu_max = 0
    ilandu_over_nlu = 0
    ilandu_negative = 0
    index = 3 + ncom
    statics: dict[str, int] = {}
    for label in STATIC_LABELS:
        if label in ("XSSTA", "YSSTA") and nssta < 1:
            continue
        if label in ("XUSTA", "YUSTA") and nusta < 1:
            continue
        if label in ("XPSTA", "YPSTA") and npsta < 1:
            continue
        if label == "NEARS" and nssta < 1:
            continue
        offset, length, payload = records[index]
        found = data[payload:payload + 8].decode("ascii").rstrip()
        if found != label:
            fail(f"static record {index} is {found}, expected {label}")
        for word in range(4):
            (clock,) = struct.unpack_from("<i", data, payload + 8 + 4 * word)
            if clock != 0:
                fail(f"static record {label} carries a non-zero clock")
        words = static_words(label, nx, ny, nz, nssta, nusta, npsta)
        if length != RECORD_HEADER_BYTES + 4 * words:
            fail(f"static record {label} has {length} bytes, expected "
                 f"{RECORD_HEADER_BYTES + 4 * words}")
        statics[label] = words
        if label == "ILANDU":
            categories = struct.unpack_from(
                f"<{cells}i", data, payload + RECORD_HEADER_BYTES)
            ilandu_max = max(categories)
            ilandu_over_nlu = sum(1 for value in categories if value > nlu)
            ilandu_negative = sum(1 for value in categories if value < 0)
        index += 1
    counts = {label: 0 for label in labels}
    missing = {label: 0 for label in labels}
    first_begin = None
    previous_end = None
    intervals = 0
    while index < len(records):
        offset, length, payload = records[index]
        if length != RECORD_HEADER_BYTES + 4 * cells:
            fail(f"hourly record {index} has {length} bytes")
        label = data[payload:payload + 8].decode("ascii").rstrip()
        slot = (index - (3 + ncom) - len(statics)) % len(labels)
        if label != labels[slot]:
            fail(f"hourly order mismatch at record {index}: {label} != {labels[slot]}")
        begin, sec_begin, end, sec_end = struct.unpack_from("<4i", data, payload + 8)
        if end != begin or sec_end != sec_begin + 3600:
            fail(f"hourly time label of {label} is not the original one")
        if stamp(end, sec_end) - stamp(begin, sec_begin) != \
                datetime.timedelta(seconds=3600):
            fail(f"hourly interval of {label} is not one hour long")
        if slot == 0:
            instant = stamp(begin, sec_begin)
            if previous_end is not None and instant != previous_end:
                fail("hourly intervals are not contiguous")
            previous_end = stamp(end, sec_end)
            intervals += 1
            if first_begin is None:
                first_begin = instant
        counts[label] += 1
        if label in ("IPGT", "IRH"):
            missing[label] += aligned_missing(data[payload:payload + length],
                                              MISSING_INT, cells)
        else:
            missing[label] += aligned_missing(data[payload:payload + length],
                                              MISSING_REAL, cells)
        index += 1
    if intervals != FROZEN_INTERVALS:
        fail(f"interval count {intervals} != {FROZEN_INTERVALS}")
    for label in labels:
        if counts[label] != FROZEN_INTERVALS:
            fail(f"label {label} appears {counts[label]} times")
    if first_begin != datetime.datetime(2022, 1, 1, tzinfo=UTC):
        fail(f"the first interval does not begin at 2022-01-01T00:00Z: {first_begin}")
    if previous_end != datetime.datetime(2022, 1, 6, 23, tzinfo=UTC):
        fail(f"the last interval does not end at 2022-01-06T23:00Z: {previous_end}")
    return {
        "records": len(records),
        "comments": ncom,
        "intervals": intervals,
        "fields_per_interval": len(labels),
        "field_records": intervals * len(labels),
        "labels": labels,
        "missing": missing,
        "cells": cells,
        "first_begin": first_begin.isoformat(),
        "last_end": previous_end.isoformat(),
        "nlu": nlu,
        "ilandu_max": ilandu_max,
        "ilandu_over_nlu": ilandu_over_nlu,
        "ilandu_negative": ilandu_negative,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tool", required=True)
    parser.add_argument("--p7-decoder", required=True)
    parser.add_argument("--real-reference", required=True, type=pathlib.Path)
    parser.add_argument("--real-reference-sha256", default=FROZEN_SHA256)
    parser.add_argument("--report", default=None, type=pathlib.Path)
    args = parser.parse_args()

    frozen = args.real_reference
    if not frozen.is_file():
        fail(f"frozen reference {frozen} is missing")
    original_bytes = frozen.read_bytes()
    original_sha = hashlib.sha256(original_bytes).hexdigest()
    if original_sha != args.real_reference_sha256:
        fail(f"frozen reference sha256 {original_sha} != "
             f"{args.real_reference_sha256}")
    if len(original_bytes) != FROZEN_BYTES:
        fail(f"frozen reference is {len(original_bytes)} bytes, expected {FROZEN_BYTES}")

    evidence: dict = {
        "frozen_sha256": original_sha,
        "frozen_bytes": len(original_bytes),
        "status": "FAIL",
    }

    inventory = independent_inventory(original_bytes, 50, 50, 9, 0)
    if inventory["records"] != FROZEN_RECORDS:
        fail(f"record count {inventory['records']} != {FROZEN_RECORDS}")
    evidence["independent_inventory"] = {
        "records": inventory["records"],
        "nlu": inventory["nlu"],
        "ilandu_max": inventory["ilandu_max"],
        "ilandu_over_nlu": inventory["ilandu_over_nlu"],
        "comments": inventory["comments"],
        "intervals": inventory["intervals"],
        "fields_per_interval": inventory["fields_per_interval"],
        "field_records": inventory["field_records"],
        "missing_total": sum(inventory["missing"].values()),
    }

    with tempfile.TemporaryDirectory(prefix="p6f-real-") as work:
        work_dir = pathlib.Path(work)
        rewritten = work_dir / "rewritten.dat"
        report = work_dir / "roundtrip.json"

        result = run([args.tool, "roundtrip", "--file", frozen, "--out", rewritten,
                      "--expect-sha256", original_sha, "--report", report])
        if result.returncode != 0:
            print(result.stdout + result.stderr)
            fail("roundtrip did not report byte identity")
        if "P6F_ROUNDTRIP_BYTE_IDENTICAL" not in result.stdout:
            print(result.stdout)
            fail("missing P6F_ROUNDTRIP_BYTE_IDENTICAL")
        payload = json.loads(report.read_text())
        if not payload["byte_identical"] or not payload["expect_sha256_match"]:
            fail("roundtrip report does not claim byte identity")
        if payload["output_sha256"] != original_sha:
            fail("roundtrip output digest differs from the frozen digest")
        if payload["intervals"] != FROZEN_INTERVALS or \
                payload["fields_per_interval"] != 45:
            fail("roundtrip reports the wrong record-group shape")
        written_bytes = rewritten.read_bytes()
        if written_bytes != original_bytes:
            fail("the re-serialised file is not byte identical")
        if hashlib.sha256(written_bytes).hexdigest() != original_sha:
            fail("the re-serialised file hashes differently")
        evidence["roundtrip"] = {
            "sha256": payload["output_sha256"],
            "bytes": payload["output_bytes"],
            "intervals": payload["intervals"],
            "fields_per_interval": payload["fields_per_interval"],
            "byte_identical": True,
        }

        # Same bytes, but the independent Python walk must also survive the
        # re-serialised file: a fixpoint, not a one-way conversion.
        again = independent_inventory(written_bytes, 50, 50, 9, 0)
        if again != inventory:
            fail("the independent inventory of the re-serialised file differs")

        check_report = work_dir / "check.json"
        result = run([args.tool, "check", "--file", rewritten, "--report",
                      check_report])
        if result.returncode != 0:
            print(result.stdout + result.stderr)
            fail("check rejected the re-serialised file")
        checked = json.loads(check_report.read_text())
        if checked["status"] != "PASS_LAYOUT_VALID":
            fail("check did not report PASS_LAYOUT_VALID")
        if checked["file_sha256"] != original_sha:
            fail("check reports a different file digest")
        if checked["comments"] != FROZEN_COMMENTS or \
                checked["hourly"]["intervals"] != FROZEN_INTERVALS or \
                checked["hourly"]["field_records"] != FROZEN_INTERVALS * 45:
            fail("check reports the wrong inventory")
        if checked["controls"]["nx"] != 50 or checked["controls"]["ny"] != 50 or \
                checked["controls"]["nz"] != 9 or checked["controls"]["npsta"] != 0:
            fail("check reports the wrong grid")
        if checked["hourly"]["first_begin"] != "2022-01-01T00:00:00Z" or \
                checked["hourly"]["last_end"] != "2022-01-06T23:00:00Z":
            fail("check reports the wrong time span")
        # ILANDU is case input written verbatim; NLU is not an upper bound in the
        # no-observation case (the frozen case stores category 20 with NLU=14), so
        # the categories are reported instead of range-rejected.
        frozen_statics = checked["statics"]
        if frozen_statics["ilandu_max"] != inventory["ilandu_max"] or \
                frozen_statics["ilandu_over_nlu_cells"] != inventory["ilandu_over_nlu"] or \
                frozen_statics["ilandu_negative_cells"] != inventory["ilandu_negative"]:
            fail("the writer's ILANDU statistics disagree with the independent "
                 "scan")
        if inventory["ilandu_over_nlu"] == 0:
            fail("the frozen case was expected to carry land-use categories "
                 "above NLU; none were found")
        names = [entry["label"] for entry in checked["fields"]]
        if names != inventory["labels"]:
            fail("the writer's field inventory order differs from OUTHR")
        for entry in checked["fields"]:
            if entry["records"] != FROZEN_INTERVALS or \
                    entry["values"] != FROZEN_INTERVALS * 2500:
                fail(f"field {entry['label']} has the wrong denominator")
            if entry["missing"] != inventory["missing"][entry["label"]]:
                fail(f"field {entry['label']} missing count disagrees with the "
                     "independent walk")
            if entry["defined"] + entry["missing"] != entry["values"]:
                fail(f"field {entry['label']} does not partition its cells")
        evidence["writer_inventory"] = {"fields": len(names), "labels_match": True,
                                        "missing_total": sum(inventory["missing"].values())}

        # ---- independent P7 decoder cross-read ----
        decoder = pathlib.Path(args.p7_decoder)
        if not decoder.is_file():
            fail(f"P7 decoder {decoder} is missing")
        original_report = work_dir / "p7-original.json"
        rewritten_report = work_dir / "p7-rewritten.json"
        first = run([sys.executable, decoder, frozen, "--report", original_report])
        second = run([sys.executable, decoder, rewritten, "--report",
                      rewritten_report])
        if first.returncode != 0 or second.returncode != 0:
            print(first.stdout + first.stderr)
            print(second.stdout + second.stderr)
            fail("the P7 decoder rejected the original or the re-serialised file")
        decoded_original = json.loads(original_report.read_text())
        decoded_rewritten = json.loads(rewritten_report.read_text())
        if decoded_rewritten != decoded_original:
            fail("the P7 decoder reports different content for the two files")
        if decoded_original["status"] != \
                "PASS_ORIGINAL_CALMET_EXPLICIT_TIME_AND_FIELD_LAYOUT":
            fail("the P7 decoder did not pass on the re-serialised file")
        if decoded_original["original_calmet_sha256"] != original_sha:
            fail("the P7 decoder hashed a different file")
        if decoded_original["actual_n_hour_intervals"] != FROZEN_INTERVALS or \
                decoded_original["fields_per_interval"] != 45 or \
                decoded_original["total_hourly_fields"] != FROZEN_INTERVALS * 45:
            fail("the P7 decoder sees the wrong hourly shape")
        if decoded_original["grid"] != [50, 50, 9]:
            fail("the P7 decoder sees the wrong grid")
        if decoded_original["hourly_labels"] != inventory["labels"]:
            fail("the P7 decoder label order differs from OUTHR")
        evidence["p7_decoder"] = {
            "status": decoded_original["status"],
            "intervals": decoded_original["actual_n_hour_intervals"],
            "fields_per_interval": decoded_original["fields_per_interval"],
            "total_hourly_fields": decoded_original["total_hourly_fields"],
            "identical_decoding": True,
        }

        # ---- the gate must be able to fail ----
        negatives: dict[str, bool] = {}

        # A changed field byte is preserved verbatim: the writer is the
        # identity on legal value words, it never renormalises or drops them.
        corrupted = bytearray(original_bytes)
        corrupted[len(corrupted) // 2] ^= 0x01
        corrupted_path = work_dir / "corrupted.dat"
        corrupted_path.write_bytes(bytes(corrupted))
        result = run([args.tool, "roundtrip", "--file", corrupted_path])
        corrupted_digest = hashlib.sha256(bytes(corrupted)).hexdigest()
        negatives["value_bytes_preserved_verbatim"] = (
            result.returncode == 0 and
            "P6F_ROUNDTRIP_BYTE_IDENTICAL" in result.stdout and
            corrupted_digest != original_sha)

        truncated_path = work_dir / "truncated.dat"
        truncated_path.write_bytes(original_bytes[:-1])
        result = run([args.tool, "roundtrip", "--file", truncated_path])
        negatives["truncation_detected"] = (
            result.returncode != 0 and "P6F_ERROR" in result.stderr)

        marker_path = work_dir / "marker.dat"
        marker = bytearray(original_bytes)
        marker[4 + 96] = 7
        marker_path.write_bytes(bytes(marker))
        result = run([args.tool, "roundtrip", "--file", marker_path])
        negatives["marker_damage_detected"] = (
            result.returncode != 0 and "P6F_ERROR" in result.stderr)

        # Offset of the first hourly record: declaration + comment count +
        # comments + controls + the ten static records of the frozen case.
        first_hourly = 4 + 96 + 4
        first_hourly += 8 + 4
        first_hourly += FROZEN_COMMENTS * (8 + 132)
        first_hourly += 8 + 176
        for _ in range(10):
            (length,) = struct.unpack_from("<i", original_bytes, first_hourly)
            first_hourly += 8 + length
        (first_label,) = struct.unpack_from("<8s", original_bytes, first_hourly + 4)
        if first_label.rstrip(b" ") != b"U-LEV  1":
            fail(f"the first hourly record is {first_label!r}, expected U-LEV  1")

        label_path = work_dir / "label.dat"
        damaged = bytearray(original_bytes)
        struct.pack_into("<B", damaged, first_hourly + 4, 0)  # break the label
        label_path.write_bytes(bytes(damaged))
        result = run([args.tool, "roundtrip", "--file", label_path])
        negatives["label_damage_detected"] = (
            result.returncode != 0 and "P6F_ERROR" in result.stderr)

        seconds_path = work_dir / "seconds.dat"
        damaged = bytearray(original_bytes)
        struct.pack_into("<i", damaged, first_hourly + 4 + 20, 0)  # end seconds
        seconds_path.write_bytes(bytes(damaged))
        result = run([args.tool, "roundtrip", "--file", seconds_path])
        negatives["hourly_seconds_damage_detected"] = (
            result.returncode != 0 and "P6F_ERROR" in result.stderr and
            "3600" in result.stderr)

        clock_path = work_dir / "clock.dat"
        clock = bytearray(original_bytes)
        struct.pack_into("<i", clock, first_hourly - (8 + 10024) + 4 + 8, 1)
        clock_path.write_bytes(bytes(clock))
        result = run([args.tool, "roundtrip", "--file", clock_path])
        negatives["static_clock_damage_detected"] = (
            result.returncode != 0 and "P6F_ERROR" in result.stderr and
            "zero clock" in result.stderr)

        for name, passed in negatives.items():
            if not passed:
                fail(f"negative case did not fail closed: {name}")
        evidence["negatives"] = negatives

    evidence["status"] = "PASS"
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(evidence, indent=2) + "\n")
    print(f"P6F_REAL_REFERENCE_ROUNDTRIP_PASS sha256={original_sha} "
          f"bytes={FROZEN_BYTES} records={FROZEN_RECORDS} "
          f"intervals={FROZEN_INTERVALS} fields_per_interval=45")
    print(f"P7_CROSS_READ_PASS status={evidence['p7_decoder']['status']} "
          f"fields={evidence['p7_decoder']['total_hourly_fields']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
