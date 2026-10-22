#!/usr/bin/env python3
"""Independent full 45-record CALMET.DAT 2.1 first-hour comparison.

G59 reads only NOAA met.inp/GEO/SURF/UP. The independent pristine Fortran
MET.DAT is passed ONLY to this comparator, never to native P6 physics.
Strictly first-hour scoped; no G14 causal six-hour or P7 acceptance.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
import struct
from pathlib import Path
from scripts.s4.s4r1c8i_compare_noaa_43_real_p6f import (
    LABELS, REAL_LABELS, F32, INT, NC, NX, NY, NZ,
    fortran_records, original_hour, sha, tol
)

def native_hour(path: Path):
    records = fortran_records(path.read_bytes())
    if len(records) < 20 or len(records[0]) != 96:
        raise ValueError("G59 missing CALMET.DAT 2.1 file declaration")
    if records[0][:16].decode("ascii").strip() != "CALMET.DAT":
        raise ValueError("G59 CALMET.DAT declaration mismatch")
    if len(records[1]) != 4:
        raise ValueError("G59 NCOM record invalid")
    ncom, = struct.unpack("<i", records[1])
    if not 0 <= ncom <= 10000 or len(records) <= ncom + 3:
        raise ValueError("G59 comments count out of bounds")
    header = records[ncom + 2]
    if len(header) != 176:
        raise ValueError("G59 native OUTHD missing")
    irlg, irtype, nx, ny, nz = struct.unpack_from("<5i", header, 48)
    iwfcod, nss, nus, nps = struct.unpack_from("<4i", header, 80)
    if (irlg, irtype, nx, ny, nz, iwfcod, nss, nus, nps) != (
            1, 1, NX, NY, NZ, 1, 2, 1, 0):
        raise ValueError("G59 native firsthour P6F source header/masks changed")
    hourly = []
    for record in records[ncom + 3:]:
        if len(record) < 24:
            raise ValueError("G59 truncated P6F static/hourly record")
        label = record[:8].decode("ascii")
        start, startsec, end, endsec = struct.unpack_from("<4i", record, 8)
        if start == 0 and end == 0:
            continue
        if len(record) != 24 + 4*NC:
            raise ValueError("G59 full P6F field byte count drift")
        hourly.append((label, (start, startsec, end, endsec), record[24:]))
    if len(hourly) != 45 or [x[0] for x in hourly] != LABELS:
        raise ValueError("G59 original OUTHR 45-record ordering changed")
    if {x[1] for x in hourly} != {(202215201, 0, 202215201, 3600)}:
        raise ValueError("G59 NOAA original-clock hourly interval mismatch")
    return {label: raw for label, _, raw in hourly}, ncom, header

def compare(original: Path, native: Path, g57: Path, g58: Path,
            real_receipt: Path, integer_receipt: Path,
            native_log: Path, report: Path) -> bool:
    floats = json.loads(real_receipt.read_text())
    integers = json.loads(integer_receipt.read_text())
    if (floats.get("status") !=
            "PASS_SOURCE_SCOPED_REAL_NOAA_NATIVE_P6F_43_REAL_FIELDS" or
        floats.get("above_tolerance") != 0 or
        floats.get("float_compared") != 43*NC or
        floats.get("original_full_six_hour_met_sha256") != sha(original) or
        integers.get("status") !=
            "PASS_SOURCE_SCOPED_REAL_NOAA_TWO_P6F_INTEGERS" or
        integers.get("not_equal") != 0 or
        integers.get("integer_comparisons") != 2*NC or
        integers.get("source_unmodified_original_6h_met_sha256") != sha(original) or
        "S4R1C8K_NATIVE_NOAA_FIRSTHOUR_MET21=PRODUCED_UNVERIFIED"
            not in native_log.read_text() or
        "ORIGINAL_MET_INPUT=FALSE" not in native_log.read_text()):
        raise ValueError("G59 inherited original-source physical receipts absent")
    source, hours = original_hour(original)
    if hours != 6:
        raise ValueError("G59 untouched original must span six hours")
    produced, ncom, header = native_hour(native)
    raw43 = g57.read_bytes()
    raw2 = g58.read_bytes()
    stride = 8 + 4*NC
    if len(raw43) != 43*stride or len(raw2) != 2*INT.size:
        raise ValueError("G59 source-native G57/G58 raw extent mismatch")
    for i, label in enumerate(REAL_LABELS):
        part = raw43[i*stride:(i+1)*stride]
        if part[:8].decode("ascii") != label or produced[label] != part[8:]:
            raise ValueError("G59 serialized REAL4 differs from independently run G57")
    if (produced["IPGT    "] != raw2[:INT.size] or
        produced["IRH     "] != raw2[INT.size:]):
        raise ValueError("G59 serialized INTEGER4 differs from independent G58")
    fail = 0
    real_compared = 0
    int_compared = 0
    first_differences = []
    max_field = {}
    for label in LABELS:
        ref = source[label]
        calc = produced[label]
        if label in ("IPGT    ", "IRH     "):
            a, b = INT.unpack(ref), INT.unpack(calc)
            mismatches = [(i, x, y) for i, (x, y) in enumerate(zip(a, b))
                          if x != y]
            int_compared += NC
            fail += len(mismatches)
            max_field[label.strip()] = {"unequal": len(mismatches)}
            if mismatches and len(first_differences) < 10:
                i, x, y = mismatches[0]
                first_differences.append({"field": label, "i": i%NX+1,
                                          "j": i//NX+1, "original": x,
                                          "native": y})
        else:
            a, b = F32.unpack(ref), F32.unpack(calc)
            maximum = 0.0
            exceed = 0
            for i, (x, y) in enumerate(zip(a, b)):
                if not math.isfinite(x) or not math.isfinite(y):
                    raise ValueError("G59 nonfinite native/original physical record")
                delta = abs(x-y)
                maximum = max(maximum, delta)
                if delta > tol(label, x, y):
                    exceed += 1
                    if len(first_differences) < 10:
                        first_differences.append({"field": label, "i": i%NX+1,
                            "j": i//NX+1, "original": x, "native": y})
            fail += exceed
            real_compared += NC
            max_field[label.strip()] = {"max_abs": maximum,
                                         "above_frozen_tolerance": exceed}
    status = ("PASS_SOURCE_SCOPED_REAL_NOAA_NATIVE_FIRSTHOUR_FULL45_MET21"
              if fail == 0 else "FAIL_NATIVE_NOAA_FULL45_MET21")
    result = {
        "status": status,
        "source_original_6h_met_sha256": sha(original),
        "source_native_g57_sha256": sha(g57),
        "source_native_g58_sha256": sha(g58),
        "native_full_onehour_met_sha256": sha(native),
        "native_comment_records": ncom,
        "native_outhd_bytes": len(header),
        "original_hours": hours, "native_hours": 1,
        "source_grid": [NX, NY, NZ], "source_stations": [2, 1, 0],
        "original_hourly_record_labels": 45,
        "real_compared": real_compared, "integer_compared": int_compared,
        "above_tolerance_or_unequal": fail,
        "native_source_only_no_original_oracle_forcing": True,
        "six_hour_g14_causal": "NOT_ACCEPTED",
        "g26_production": "NOT_ACCEPTED", "p7": "NOT_ACCEPTED",
        "per_field": max_field, "first_differences": first_differences,
    }
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(result, indent=2, sort_keys=True)+"\n")
    print("S4R1C8K_NATIVE_NOAA_FIRSTHOUR_MET21="+status)
    print("S4R1C8K_45RECORDS_COMPARED="+str(len(LABELS)))
    print("S4R1C8K_ABOVE_TOLERANCE="+str(fail))
    print("S4R1C8K_6HOUR_G26_P7=NOT_ACCEPTED")
    return fail == 0

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    for name in ("original", "native", "g57", "g58", "real-receipt",
                 "integer-receipt", "native-log", "report"):
        parser.add_argument("--"+name, required=True, type=Path)
    opts = vars(parser.parse_args())
    if not compare(opts["original"], opts["native"], opts["g57"],
                   opts["g58"], opts["real_receipt"],
                   opts["integer_receipt"], opts["native_log"],
                   opts["report"]):
        raise SystemExit(3)
