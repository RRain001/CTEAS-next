#!/usr/bin/env python3
"""P6F real-scale XMISS round trip CTest.

The frozen 2022 reference `met.dat` happens to contain no missing value, so the
XMISS path of the writer is otherwise only exercised at toy grid sizes. This
test builds a *real-scale* fixture (NX=NY=50, NZ=9, 143 one-hour intervals, the
same record layout as the frozen case) whose real and integer fields carry the
original sentinel ``9999.`` / ``9999``, and then requires:

  * the writer's own inventory to report exactly the sentinel counts an
    independent Python scan of the produced bytes finds, per label;
  * the sentinel to be preserved verbatim and not to be confused with an absent
    field (the round trip is byte-identical and the file still carries all 45
    labels per hour);
  * the independent P7 CALMET.DAT decoder to accept the file
    (PASS_ORIGINAL_CALMET_EXPLICIT_TIME_AND_FIELD_LAYOUT);
  * the fail-closed boundary to stay closed: the same fixture with one sentinel
    replaced by NaN is rejected, while the sentinel itself is not.

The fixture is explicitly synthetic: values are constants of the grid index, so
this test says nothing about reconstructed meteorology.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import struct
import subprocess
import sys
import tempfile

NX = 50
NY = 50
NZ = 9
HOURS = 143
CELLS = NX * NY
RECORD_HEADER_BYTES = 24
SENTINEL_REAL = 9999.0
SENTINEL_INT = 9999
SENTINEL_STRIDE = 97
EXPECTED_PER_RECORD = len(range(0, CELLS, SENTINEL_STRIDE))


def fail(message: str) -> None:
    print("P6F_REAL_SCALE_XMISS_FAIL " + message)
    sys.exit(1)


def run(command: list) -> subprocess.CompletedProcess:
    return subprocess.run([str(part) for part in command], capture_output=True,
                          text=True)


def walk(data: bytes) -> list[tuple[int, int, int]]:
    records = []
    offset = 0
    while offset + 8 <= len(data):
        (length,) = struct.unpack_from("<i", data, offset)
        if length < 0 or offset + 8 + length > len(data):
            fail(f"damaged record length {length} at offset {offset}")
        (trailer,) = struct.unpack_from("<i", data, offset + 4 + length)
        if trailer != length:
            fail("record length markers disagree")
        records.append((offset, length, offset + 4))
        offset += 8 + length
    if offset != len(data):
        fail("the record walk does not reach the end of the file")
    return records


def expected_labels(nz: int) -> list[str]:
    labels: list[str] = []
    for level in range(1, nz + 1):
        labels += [f"U-LEV{level:>3}", f"V-LEV{level:>3}", f"WFACE{level:>3}"]
    labels += [f"T-LEV{level:>3}" for level in range(1, nz + 1)]
    labels += ["IPGT", "USTAR", "ZI", "EL", "WSTAR", "TEMPK", "RHO", "QSW", "IRH"]
    return labels


def independent_missing_counts(data: bytes) -> dict[str, int]:
    """Aligned XMISS counts per label, computed here from the raw words."""
    counts: dict[str, int] = {}
    for _, length, payload in walk(data):
        if length != RECORD_HEADER_BYTES + 4 * CELLS:
            continue
        name = data[payload:payload + 8].decode("ascii", "replace").rstrip()
        if not name:
            continue
        if name not in expected_labels(NZ):
            continue
        words = data[payload + RECORD_HEADER_BYTES:payload + length]
        if name in ("IPGT", "IRH"):
            values = struct.unpack(f"<{CELLS}i", words)
            counts[name] = counts.get(name, 0) + values.count(SENTINEL_INT)
        else:
            values = struct.unpack(f"<{CELLS}f", words)
            counts[name] = counts.get(name, 0) + values.count(SENTINEL_REAL)
    return counts


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tool", required=True)
    parser.add_argument("--p7-decoder", required=True)
    parser.add_argument("--report", default=None, type=pathlib.Path)
    args = parser.parse_args()
    evidence: dict = {"status": "FAIL", "grid": [NX, NY, NZ], "intervals": HOURS}

    with tempfile.TemporaryDirectory(prefix="p6f-xmiss-") as work:
        root = pathlib.Path(work)
        fixture = root / "real-scale-xmiss.dat"
        report = root / "check.json"
        result = run([args.tool, "emit-fixture", "--out", fixture, "--hours", HOURS,
                      "--nx", NX, "--ny", NY, "--nz", NZ, "--nssta", "1",
                      "--nusta", "1", "--npsta", "0", "--with-missing"])
        if result.returncode != 0 or "P6F_FIXTURE_WRITTEN" not in result.stdout:
            print(result.stdout + result.stderr)
            fail("emit-fixture failed for the real-scale sentinel fixture")
        data = fixture.read_bytes()
        # Independent size expectation for this layout: 104-byte declaration
        # record, the 4 comment records, the 176-byte controls record, the ten
        # static records of NSSTA=1/NUSTA=1/NPSTA=0 and 143*45 records of
        # 24 + 4*NX*NY bytes.
        expected_bytes = (8 + 96                       # declaration record
                          + 8 + 4                      # comment count
                          + 4 * (8 + 132)              # four comment records
                          + 8 + 176                    # controls record
                          + 8 + RECORD_HEADER_BYTES + 4 * (NZ + 1)   # ZFACE
                          + 4 * (8 + RECORD_HEADER_BYTES + 4)        # XSSTA/YSSTA/XUSTA/YUSTA
                          + 5 * (8 + RECORD_HEADER_BYTES + 4 * CELLS)  # Z0/ILANDU/ELEV/XLAI/NEARS
                          + HOURS * 45 * (8 + RECORD_HEADER_BYTES + 4 * CELLS))
        if len(data) != expected_bytes:
            fail(f"the real-scale fixture is {len(data)} bytes, the layout says "
                 f"{expected_bytes}")

        result = run([args.tool, "check", "--file", fixture, "--report", report])
        if result.returncode != 0:
            print(result.stdout + result.stderr)
            fail("check rejected the real-scale sentinel fixture")
        checked = json.loads(report.read_text())
        if checked["status"] != "PASS_LAYOUT_VALID":
            fail("check did not report PASS_LAYOUT_VALID")
        if checked["hourly"]["intervals"] != HOURS or \
                checked["hourly"]["fields_per_interval"] != 45:
            fail("the fixture has the wrong hourly shape")
        independent = independent_missing_counts(data)
        labels = expected_labels(NZ)
        if sorted(independent) != sorted(labels):
            fail("the independent scan did not see all 45 labels")
        reported = {entry["label"]: entry for entry in checked["fields"]}
        for label in labels:
            entry = reported[label]
            if entry["missing"] != independent[label]:
                fail(f"label {label}: the writer reports {entry['missing']} "
                     f"XMISS values, the independent scan finds "
                     f"{independent[label]}")
            if entry["missing"] != HOURS * EXPECTED_PER_RECORD:
                fail(f"label {label}: {entry['missing']} sentinels, expected "
                     f"{HOURS * EXPECTED_PER_RECORD}")
            if entry["defined"] + entry["missing"] != entry["values"]:
                fail(f"label {label} does not partition its cells")
        # the sentinel must be preserved, and must not look like an absent field
        records = walk(data)
        first = records[3 + struct.unpack_from("<i", data, records[1][2])[0] + 10]
        controls = data[first[2]:first[2] + 8].decode("ascii", "replace")
        if controls.rstrip() != "U-LEV  1":
            fail(f"the first hourly record is {controls!r}, expected U-LEV  1")
        first_values = struct.unpack_from(f"<{CELLS}f", data, first[2] + 24)
        if first_values[0] != SENTINEL_REAL:
            fail("the sentinel of the first cell was not written verbatim")
        if first_values[1] == SENTINEL_REAL:
            fail("a non-sentinel cell became the sentinel")

        result = run([args.tool, "roundtrip", "--file", fixture])
        if result.returncode != 0 or "P6F_ROUNDTRIP_BYTE_IDENTICAL" not in result.stdout:
            fail("the real-scale sentinel fixture does not round trip exactly")
        evidence["xmix"] = {
            "bytes": len(data),
            "sha256": hashlib.sha256(data).hexdigest(),
            "sentinel_per_record": EXPECTED_PER_RECORD,
            "sentinel_per_label": HOURS * EXPECTED_PER_RECORD,
            "labels": len(labels),
            "total_sentinel_values": HOURS * EXPECTED_PER_RECORD * len(labels),
        }

        decoder = pathlib.Path(args.p7_decoder)
        if not decoder.is_file():
            fail(f"the P7 decoder {decoder} is missing")
        decoded = root / "p7.json"
        result = run([sys.executable, decoder, fixture, "--report", decoded])
        if result.returncode != 0:
            print(result.stdout + result.stderr)
            fail("the independent P7 decoder rejected the sentinel fixture")
        p7 = json.loads(decoded.read_text())
        if p7["status"] != "PASS_ORIGINAL_CALMET_EXPLICIT_TIME_AND_FIELD_LAYOUT":
            fail("the P7 decoder did not pass on the sentinel fixture")
        if p7["actual_n_hour_intervals"] != HOURS or \
                p7["fields_per_interval"] != 45:
            fail("the P7 decoder sees the wrong shape")
        evidence["p7_decoder"] = {
            "status": p7["status"],
            "intervals": p7["actual_n_hour_intervals"],
            "fields_per_interval": p7["fields_per_interval"],
        }

        # fail-closed: the sentinel is accepted, NaN is not
        nan_copy = bytearray(data)
        index = first[2] + RECORD_HEADER_BYTES
        struct.pack_into("<f", nan_copy, index, float("nan"))
        nan_path = root / "nan.dat"
        nan_path.write_bytes(bytes(nan_copy))
        result = run([args.tool, "check", "--file", nan_path])
        if result.returncode == 0 or "non-finite" not in result.stderr:
            print(result.stdout + result.stderr)
            fail("a NaN met value was not rejected while the XMISS sentinel is "
                 "accepted")
        evidence["nan_rejected"] = True

        # fail-closed: a value equal to the sentinel is not an absent field
        result = run([args.tool, "check", "--file", fixture])
        if "field_records=6435" not in result.stdout:
            fail("the sentinel fixture lost field records")

    evidence["status"] = "PASS"
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(evidence, indent=2) + "\n")
    print(f"P6F_REAL_SCALE_XMISS_PASS bytes={evidence['xmix']['bytes']} "
          f"sentinel_values={evidence['xmix']['total_sentinel_values']} "
          f"per_label={evidence['xmix']['sentinel_per_label']} "
          f"p7={evidence['p7_decoder']['status']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
