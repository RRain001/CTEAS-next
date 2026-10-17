#!/usr/bin/env python3
"""P6F synthetic CLI round-trip CTest.

Exercises the writer CLI end to end on explicitly generated field arrays:
emit-fixture -> check -> roundtrip, with an independent Python walk of the
produced bytes (record framing, declaration, controls, static extents, hourly
order, time labels and XMISS counts) and the fail-closed cases.

The fixtures are explicitly synthetic: every value is a constant of the grid
index, so this test says nothing about reconstructed meteorology. Only the
standard library is used.
"""
from __future__ import annotations

import argparse
import datetime
import json
import pathlib
import struct
import subprocess
import sys
import tempfile

EPOCH = datetime.date(1970, 1, 1)

RECORD_HEADER_BYTES = 24
MISSING_REAL = struct.pack("<f", 9999.0)
MISSING_INT = struct.pack("<i", 9999)

# (hours, nx, ny, nz, nssta, nusta, npsta, with_missing)
VARIANTS = [
    (3, 8, 5, 3, 1, 1, 0, False),
    (2, 4, 4, 2, 0, 0, 2, True),
    (2, 5, 5, 1, 1, 0, 1, True),
    (1, 3, 3, 4, 2, 2, 3, True),
]


def fail(message: str) -> None:
    print("P6F_SYNTHETIC_CLI_FAIL " + message)
    sys.exit(1)


def run(command: list) -> subprocess.CompletedProcess:
    return subprocess.run([str(part) for part in command], capture_output=True,
                          text=True)


def expected_labels(nz: int, npsta: int) -> list[str]:
    labels: list[str] = []
    for level in range(1, nz + 1):
        labels += [f"U-LEV{level:>3}", f"V-LEV{level:>3}", f"WFACE{level:>3}"]
    labels += [f"T-LEV{level:>3}" for level in range(1, nz + 1)]
    labels += ["IPGT", "USTAR", "ZI", "EL", "WSTAR"]
    if npsta != 0:
        labels.append("RMM")
    labels += ["TEMPK", "RHO", "QSW", "IRH"]
    if npsta != 0:
        labels.append("IPCODE")
    return labels


def walk(data: bytes) -> list[tuple[int, int, int]]:
    records = []
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


def instant_of(clock: int, seconds: int) -> int:
    """Absolute UTC instant of one explicit written time label."""
    year, rest = divmod(clock, 100000)
    julian, hour = divmod(rest, 100)
    if not (2000 <= year <= 2100 and 1 <= julian <= 366 and 0 <= hour <= 23
            and 0 <= seconds <= 86400):
        fail(f"invalid written time label ({clock},{seconds})")
    days = (datetime.date(year, 1, 1) - EPOCH).days + julian - 1
    return days * 86400 + hour * 3600 + seconds


def aligned_missing(payload: bytes, pattern: bytes, cells: int) -> int:
    if pattern not in payload:
        return 0
    return sum(1 for offset in range(RECORD_HEADER_BYTES,
                                    RECORD_HEADER_BYTES + 4 * cells, 4)
               if payload[offset:offset + 4] == pattern)


def verify_variant(variant, tool: str, work: pathlib.Path) -> dict:
    hours, nx, ny, nz, nssta, nusta, npsta, with_missing = variant
    tag = f"h{hours}_x{nx}y{ny}z{nz}_s{nssta}{nusta}{npsta}_m{int(with_missing)}"
    emitted = work / f"fixture-{tag}.dat"
    labels = expected_labels(nz, npsta)
    cells = nx * ny
    statics = 5 + (2 if nssta >= 1 else 0) + (2 if nusta >= 1 else 0) + \
        (2 if npsta >= 1 else 0) + (1 if nssta >= 1 else 0)

    emit = [tool, "emit-fixture", "--out", emitted, "--hours", hours,
            "--nx", nx, "--ny", ny, "--nz", nz, "--nssta", nssta,
            "--nusta", nusta, "--npsta", npsta]
    if with_missing:
        emit.append("--with-missing")
    result = run(emit)
    if result.returncode != 0 or "P6F_FIXTURE_WRITTEN" not in result.stdout:
        print(result.stdout + result.stderr)
        fail(f"emit-fixture failed for {tag}")

    check_json = work / f"check-{tag}.json"
    result = run([tool, "check", "--file", emitted, "--report", check_json])
    if result.returncode != 0:
        print(result.stdout + result.stderr)
        fail(f"check rejected the fixture {tag}")
    report = json.loads(check_json.read_text())
    if report["status"] != "PASS_LAYOUT_VALID":
        fail(f"check did not pass for {tag}")
    if report["hourly"]["intervals"] != hours or \
            report["hourly"]["fields_per_interval"] != len(labels) or \
            report["hourly"]["field_records"] != hours * len(labels):
        fail(f"check reports a wrong hourly shape for {tag}")
    if report["controls"]["npsta"] != npsta or \
            report["controls"]["nssta"] != nssta or \
            report["controls"]["nusta"] != nusta:
        fail(f"check reports wrong station counts for {tag}")
    if report["statics"]["zface_faces"] != nz + 1 or \
            report["statics"]["grid_cells"] != cells:
        fail(f"check reports wrong static extents for {tag}")
    # hourly_layout reports the 8-byte label the file carries; the 2-D names
    # are space padded to that width exactly as the original writes them.
    if [entry["label"] for entry in report["hourly_layout"]] != \
            [label.ljust(8) for label in labels]:
        fail(f"the writer label order differs from OUTHR for {tag}")

    result = run([tool, "roundtrip", "--file", emitted])
    if result.returncode != 0 or "P6F_ROUNDTRIP_BYTE_IDENTICAL" not in result.stdout:
        print(result.stdout + result.stderr)
        fail(f"roundtrip failed for {tag}")

    data = emitted.read_bytes()
    records = walk(data)
    if len(records) != 3 + 4 + statics + hours * len(labels):
        fail(f"unexpected record count {len(records)} for {tag}")
    if records[0][1] != 96 or not data[records[0][2]:].startswith(b"CALMET.DAT"):
        fail(f"declaration record is not the original 96-byte one for {tag}")
    (ncom,) = struct.unpack_from("<i", data, records[1][2])
    if ncom != 4:
        fail(f"fixture comment count is {ncom}, expected 4 for {tag}")
    controls = data[records[2 + ncom][2]:]
    if records[2 + ncom][1] != 176:
        fail(f"controls record is not 176 bytes for {tag}")
    got_nx, got_ny, got_nz = struct.unpack_from("<3i", controls, 56)
    got_irlg, got_irtype = struct.unpack_from("<2i", controls, 48)
    got_wfcod, got_nssta, got_nusta, got_npsta = struct.unpack_from("<4i", controls, 80)
    if (got_nx, got_ny, got_nz) != (nx, ny, nz) or got_irlg != hours or \
            got_irtype != 1 or got_wfcod != 1:
        fail(f"controls record does not describe the requested run for {tag}")
    if (got_nssta, got_nusta, got_npsta) != (nssta, nusta, npsta):
        fail(f"controls station counts are wrong for {tag}")
    if controls[40:48] != b"UTC+0000":
        fail(f"controls time zone is wrong for {tag}")

    index = 3 + ncom
    wanted = ["ZFACE"] + \
        (["XSSTA", "YSSTA"] if nssta >= 1 else []) + \
        (["XUSTA", "YUSTA"] if nusta >= 1 else []) + \
        (["XPSTA", "YPSTA"] if npsta >= 1 else []) + \
        ["Z0", "ILANDU", "ELEV", "XLAI"] + (["NEARS"] if nssta >= 1 else [])
    for position, label in enumerate(wanted):
        offset, length, payload = records[index + position]
        found = data[payload:payload + 8].decode("ascii").rstrip()
        if found != label:
            fail(f"static record {position} is {found}, expected {label} for {tag}")
        for word in range(4):
            (clock,) = struct.unpack_from("<i", data, payload + 8 + 4 * word)
            if clock != 0:
                fail(f"static record {label} has a non-zero clock for {tag}")
    index += len(wanted)

    counts = {label: 0 for label in labels}
    missing = {label: 0 for label in labels}
    previous = None
    for position in range(hours * len(labels)):
        offset, length, payload = records[index + position]
        if length != RECORD_HEADER_BYTES + 4 * cells:
            fail(f"hourly record {position} has {length} bytes for {tag}")
        label = data[payload:payload + 8].decode("ascii").rstrip()
        if label != labels[position % len(labels)]:
            fail(f"hourly order mismatch at {position}: {label} for {tag}")
        begin, seconds, end, end_seconds = struct.unpack_from("<4i", data, payload + 8)
        if begin != end or end_seconds != seconds + 3600:
            fail(f"hourly time label of {label} is not the original one for {tag}")
        if instant_of(end, end_seconds) - instant_of(begin, seconds) != 3600:
            fail(f"hourly interval of {label} is not one hour long for {tag}")
        if position % len(labels) == 0:
            if previous is not None and instant_of(begin, seconds) != previous:
                fail(f"hourly intervals are not contiguous for {tag}")
            if previous is None and instant_of(begin, seconds) != \
                    (datetime.date(2022, 1, 1) - EPOCH).days * 86400:
                fail(f"the fixture does not start at 2022-01-01T00:00Z for {tag}")
            previous = instant_of(end, end_seconds)
        counts[label] += 1
        pattern = MISSING_INT if label in ("IPGT", "IRH") else MISSING_REAL
        missing[label] += aligned_missing(data[payload:payload + length], pattern,
                                          cells)
    for label in labels:
        if counts[label] != hours:
            fail(f"label {label} appears {counts[label]} times for {tag}")
    reported = {entry["label"]: entry for entry in report["fields"]}
    for label in labels:
        entry = reported[label]
        if entry["records"] != hours or entry["values"] != hours * cells:
            fail(f"writer denominator for {label} is wrong for {tag}")
        if entry["missing"] != missing[label]:
            fail(f"writer XMISS count for {label} is {entry['missing']}, "
                 f"independent count is {missing[label]} for {tag}")
    if with_missing and sum(missing.values()) == 0:
        fail(f"--with-missing produced no XMISS value for {tag}")
    if not with_missing and sum(missing.values()) != 0:
        fail(f"unexpected XMISS values for {tag}")

    truncated = work / f"truncated-{tag}.dat"
    truncated.write_bytes(data[:-1])
    result = run([tool, "roundtrip", "--file", truncated])
    if result.returncode == 0 or "P6F_ERROR" not in result.stderr:
        fail(f"a truncated fixture was not rejected for {tag}")
    damaged = bytearray(data)
    damaged[len(damaged) // 2] ^= 0x01
    damaged_path = work / f"damaged-{tag}.dat"
    damaged_path.write_bytes(bytes(damaged))
    result = run([tool, "roundtrip", "--file", damaged_path])
    if result.returncode != 0 or "P6F_ROUNDTRIP_BYTE_IDENTICAL" not in result.stdout:
        fail(f"a changed value word was not preserved verbatim for {tag}")
    clock = bytearray(data)
    static_offset = records[3 + ncom][2]  # ZFACE payload
    struct.pack_into("<i", clock, static_offset + 8, 1)
    clock_path = work / f"clock-{tag}.dat"
    clock_path.write_bytes(bytes(clock))
    result = run([tool, "roundtrip", "--file", clock_path])
    if result.returncode == 0 or "zero clock" not in result.stderr:
        fail(f"a static clock word was not validated for {tag}")
    return {"tag": tag, "records": len(records), "fields_per_interval": len(labels),
            "missing_total": sum(missing.values())}


def verify_wind_only_mode(tool: str, work: pathlib.Path) -> dict:
    """IRTYPE=0 writes only the wind block of each hour (OUTHR returns early)."""
    emitted = work / "fixture-wind-only.dat"
    result = run([tool, "emit-fixture", "--out", emitted, "--hours", "2",
                  "--nx", "4", "--ny", "3", "--nz", "2", "--nssta", "1",
                  "--nusta", "1", "--npsta", "0", "--irtype", "0"])
    if result.returncode != 0 or "P6F_FIXTURE_WRITTEN" not in result.stdout:
        print(result.stdout + result.stderr)
        fail("emit-fixture failed for the IRTYPE=0 fixture")
    check_json = work / "check-wind-only.json"
    result = run([tool, "check", "--file", emitted, "--report", check_json])
    if result.returncode != 0:
        print(result.stdout + result.stderr)
        fail("check rejected the IRTYPE=0 fixture")
    report = json.loads(check_json.read_text())
    if report["controls"]["irtype"] != 0 or report["hourly"]["fields_per_interval"] != 6:
        fail("the IRTYPE=0 fixture does not have the wind-only layout")
    labels = ["U-LEV  1", "V-LEV  1", "WFACE  1", "U-LEV  2", "V-LEV  2", "WFACE  2"]
    if [entry["label"] for entry in report["hourly_layout"]] != labels:
        fail("the IRTYPE=0 label order is not the OUTHR wind block")
    result = run([tool, "roundtrip", "--file", emitted])
    if result.returncode != 0 or "P6F_ROUNDTRIP_BYTE_IDENTICAL" not in result.stdout:
        fail("the IRTYPE=0 fixture does not round trip")
    data = emitted.read_bytes()
    records = walk(data)
    (ncom,) = struct.unpack_from("<i", data, records[1][2])
    first = records[3 + ncom + 10][2]
    if data[first:first + 8] != b"U-LEV  1":
        fail("the first IRTYPE=0 record is not U-LEV 1")
    if len(records) != 3 + 4 + 10 + 2 * len(labels):
        fail(f"the IRTYPE=0 fixture has {len(records)} records")
    return {"records": len(records), "fields_per_interval": len(labels)}


def verify_subhourly_start(tool: str, work: pathlib.Path) -> dict:
    """The OUTHD run clock is (year, month, day, hour) + seconds in that hour.

    A 00:30 start must be written as hour 0 with a 1800 s word, and the field
    records must still carry the original 3600 s interval labels.
    """
    emitted = work / "fixture-subhourly.dat"
    result = run([tool, "emit-fixture", "--out", emitted, "--hours", "2",
                  "--nx", "3", "--ny", "3", "--nz", "2",
                  "--nssta", "0", "--nusta", "0", "--npsta", "0",
                  "--start", "2022-01-01T00:30:00"])
    if result.returncode != 0 or "P6F_FIXTURE_WRITTEN" not in result.stdout:
        print(result.stdout + result.stderr)
        fail("emit-fixture rejected a sub-hourly start")
    result = run([tool, "roundtrip", "--file", emitted])
    if result.returncode != 0 or "P6F_ROUNDTRIP_BYTE_IDENTICAL" not in result.stdout:
        fail("a sub-hourly fixture did not round trip")
    data = emitted.read_bytes()
    records = walk(data)
    (ncom,) = struct.unpack_from("<i", data, records[1][2])
    controls = records[2 + ncom][2]
    begin = struct.unpack_from("<5i", data, controls)
    end = struct.unpack_from("<5i", data, controls + 20)
    if begin != (2022, 1, 1, 0, 1800) or end != (2022, 1, 1, 2, 1800):
        fail(f"sub-hourly run clock is {begin} .. {end}, expected the "
             "hour + seconds-in-hour form")
    labels = expected_labels(2, 0)
    first = records[3 + ncom + 5][2]          # five static records, no stations
    second = records[3 + ncom + 5 + len(labels)][2]
    first_words = struct.unpack_from("<4i", data, first + 8)
    second_words = struct.unpack_from("<4i", data, second + 8)
    if first_words != (202200100, 1800, 202200100, 5400):
        fail(f"the first sub-hourly field label is {first_words}")
    if second_words != (202200101, 1800, 202200101, 5400):
        fail(f"the second sub-hourly field label is {second_words}")
    return {"start": "2022-01-01T00:30:00", "records": len(records),
            "first_record_time_words": list(first_words),
            "second_record_time_words": list(second_words)}


def fail_closed_options(tool: str, work: pathlib.Path) -> dict:
    """The CLI must reject an impossible request instead of writing a file."""
    cases = {
        "nz_above_999": ["--nz", "1000"],
        "zero_grid": ["--nx", "0"],
        "negative_hours": ["--hours", "-1"],
        "bad_timezone_start": ["--start", "2022-13-01T00:00"],
    }
    results: dict[str, bool] = {}
    for name, extra in cases.items():
        out = work / f"invalid-{name}.dat"
        result = run([tool, "emit-fixture", "--out", out, "--hours", "1",
                      "--nx", "3", "--ny", "3", "--nz", "2"] + extra)
        results[name] = result.returncode != 0 and "P6F_ERROR" in result.stderr
        if not results[name]:
            fail(f"the writer accepted an impossible request: {name}")
    return results


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tool", required=True)
    parser.add_argument("--report", default=None, type=pathlib.Path)
    args = parser.parse_args()
    evidence = {"variants": [], "status": "FAIL"}
    with tempfile.TemporaryDirectory(prefix="p6f-synthetic-") as work:
        root = pathlib.Path(work)
        for variant in VARIANTS:
            evidence["variants"].append(verify_variant(variant, args.tool, root))
        evidence["fail_closed_options"] = fail_closed_options(args.tool, root)
        evidence["subhourly_start"] = verify_subhourly_start(args.tool, root)
        evidence["wind_only_mode"] = verify_wind_only_mode(args.tool, root)
    evidence["status"] = "PASS"
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(evidence, indent=2) + "\n")
    total_missing = sum(v["missing_total"] for v in evidence["variants"])
    print(f"P6F_SYNTHETIC_CLI_ROUNDTRIP_PASS variants={len(VARIANTS) + 1} "
          f"records={sum(v['records'] for v in evidence['variants'])} "
          f"xmix_values={total_missing} subhourly_start=ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
