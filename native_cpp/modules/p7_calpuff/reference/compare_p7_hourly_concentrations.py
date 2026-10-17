#!/usr/bin/env python3
"""Compare authentic CALPUFF Fortran-sequential H-3 REAL4 fields.

Header/comment bytes are audited separately: an independent P6F OUTHD may
change hundreds of echoed input comments without changing concentration.
This tool NEVER calls a green workflow proof of scientific equality merely
because both files are structurally valid. Different MET inputs get measured
differences; bit identity is required only with --require-bit-exact.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import struct
import sys

def fail(message: str) -> None:
    raise ValueError("P7_COUPLING_COMPARE_BLOCKED: " + message)

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()

def read_fields(path: Path, nx: int, ny: int, expected_hours: int) -> dict:
    if nx < 1 or ny < 1 or expected_hours < 1:
        fail("invalid grid dimensions/hours")
    if not path.is_file() or path.stat().st_size == 0:
        fail(f"missing/empty CALPUFF output {path}")
    data = path.read_bytes()
    pos = 0
    record_count = 0
    fields = []
    labels = []
    payload_size = 15 + 4 * nx * ny
    while pos < len(data):
        if pos + 8 > len(data):
            fail(f"{path}: truncated record at byte {pos}")
        (length,) = struct.unpack_from("<i", data, pos)
        if length < 0 or pos + length + 8 > len(data):
            fail(f"{path}: invalid Fortran record length at byte {pos}")
        payload = pos + 4
        (trailer,) = struct.unpack_from("<i", data, payload + length)
        if length != trailer:
            fail(f"{path}: leading/trailing record markers disagree at {pos}")
        if length == payload_size:
            name = data[payload:payload + 8].decode("ascii", errors="replace").strip()
            index = data[payload + 8:payload + 15].decode("ascii", errors="replace").strip()
            if name != "H-3" or index != "1":
                fail(f"{path}: unexpectedly sized species record {name!r}/{index!r}")
            values = struct.unpack_from(f"<{nx * ny}f", data, payload + 15)
            if any(not math.isfinite(v) or v < 0 for v in values):
                fail(f"{path}: H-3 contains negative/NaN/Inf values at hour {len(fields)+1}")
            fields.append(values)
            labels.append((name,index))
        record_count += 1
        pos += length + 8
    if len(fields) != expected_hours:
        fail(f"{path}: expected {expected_hours} H-3 hourly fields; got {len(fields)}")
    if not any(v > 0 for row in fields for v in row):
        fail(f"{path}: all H-3 hourly fields are zero; invalid scientific test")
    return {
        "path": str(path), "sha256": sha256(path), "size_bytes": len(data),
        "fortran_records": record_count, "hours": len(fields), "fields": fields,
        "nonzero_values": sum(v > 0 for row in fields for v in row),
    }

def compare(a: dict, b: dict, nx: int, ny: int) -> dict:
    exact = 0
    first = None
    abs_sum = 0.0
    sq_sum = 0.0
    max_abs = 0.0
    max_rel = 0.0
    max_where = None
    total_a = total_b = 0.0
    count = nx * ny * a["hours"]
    hour_summaries = []
    for h, (ar, br) in enumerate(zip(a["fields"], b["fields"]), 1):
        hour_matches = 0
        hour_max = 0.0
        nonzero_a = nonzero_b = 0
        for c, (x, y) in enumerate(zip(ar, br)):
            nonzero_a += x > 0
            nonzero_b += y > 0
            if struct.pack("<f", x) == struct.pack("<f", y):
                exact += 1
                hour_matches += 1
            elif first is None:
                first = {"hour_1based": h,"i_1based": c % nx + 1,
                         "j_1based": c // nx + 1, "a": x, "b": y}
            error = abs(x-y)
            abs_sum += error
            sq_sum += error*error
            total_a += x
            total_b += y
            hour_max = max(hour_max,error)
            rel = error/max(abs(x),abs(y),1e-30)
            max_rel = max(max_rel,rel)
            if error > max_abs:
                max_abs = error
                max_where = {"hour_1based": h, "i_1based":c%nx+1,
                             "j_1based":c//nx+1, "a":x, "b":y}
        hour_summaries.append({
            "hour_1based":h,"bit_exact":hour_matches==nx*ny,
            "matching_real4":hour_matches, "values":nx*ny,
            "max_absolute_difference_bq_m3":hour_max,
            "nonzero_a":nonzero_a,"nonzero_b":nonzero_b,
        })
    return {
        "hours":a["hours"],"nx":nx,"ny":ny,"values":count,
        "matching_real4":exact,"bitwise_identical":exact==count,
        "first_difference":first,"max_difference_location":max_where,
        "max_absolute_difference_bq_m3":max_abs,
        "max_symmetric_relative_difference":max_rel,
        "mean_absolute_difference_bq_m3":abs_sum/count,
        "rmse_bq_m3":math.sqrt(sq_sum/count),
        "sum_concentration_a":total_a,"sum_concentration_b":total_b,
        "hourly":hour_summaries,
    }

def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--a",required=True,type=Path)
    p.add_argument("--b",required=True,type=Path)
    p.add_argument("--nx",required=True,type=int)
    p.add_argument("--ny",required=True,type=int)
    p.add_argument("--hours",default=143,type=int)
    p.add_argument("--report",required=True,type=Path)
    p.add_argument("--require-bit-exact",action="store_true")
    a=p.parse_args()
    try:
        fields_a=read_fields(a.a,a.nx,a.ny,a.hours)
        fields_b=read_fields(a.b,a.nx,a.ny,a.hours)
        result=compare(fields_a,fields_b,a.nx,a.ny)
        result["a"]={k:v for k,v in fields_a.items() if k!="fields"}
        result["b"]={k:v for k,v in fields_b.items() if k!="fields"}
        result["acceptance_scope"]="measured_field_difference_only"
        result["scientific_bitwise_pass"]=result["bitwise_identical"]
        a.report.parent.mkdir(parents=True,exist_ok=True)
        a.report.write_text(json.dumps(result,indent=2)+"\n")
        print(f"P7_COUPLING_FIELDS=PASS HOURS={a.hours} NX={a.nx} NY={a.ny}"
              f" REAL4_MATCH={result['matching_real4']}/{result['values']}"
              f" BITWISE={result['bitwise_identical']} FIRST={result['first_difference']}"
              f" MAX_ABS={result['max_absolute_difference_bq_m3']}")
        if a.require_bit_exact and not result["bitwise_identical"]:
            fail("required same-MET REAL4 byte identity not achieved")
        return 0
    except (ValueError,OSError,struct.error) as exc:
        print(str(exc),file=sys.stderr)
        return 1

if __name__=="__main__":
    raise SystemExit(main())
