#!/usr/bin/env python3
"""Immutable CALPUFF COMP ordering and 1h/6h/143h DGM evidence audit.

This proves original source call *order* and independently captured original
states, but does NOT run a reconstructed C++ 143-hour CALPUFF model.
Missing reconstructed driver/concentration parity is an explicit gap.
"""
from __future__ import annotations
import argparse
import datetime as dt
import hashlib
import importlib.util
import json
import math
import re
import struct
import sys
from pathlib import Path

SHA_VENDOR = "da40372cab1c181158d0ee5faac16f678e876fc14415073c38c8e3bdabfbc568"
SHA_HOUR0 = "b51d20d3cd1085902342d5b6d6b2f34c4a84c96d4966b63a2b1231c126087c89"
ORIGINAL_CON_SHA = "0d51bdb68ff1a5798048bc41067107d3ffe10dc6222f25336df856bcbf48ba10"
EXPECTED = [
    ("sampling_cadence", 10347, "item6_sampling_cadence"),
    ("load_puff_state", 10473, "item1_start_of_step"),
    ("resolve_met_cell", 10487, "item2_cell_parameters"),
    ("puffdz", 10495, "item3_puffdz_return"),
    ("advect", 10499, "item4_advect_return"),
    ("rise_wind_and_calm", 10528, "item5_after_adjustments"),
    ("substep_length", 10548, None),
    ("advance_position", 10607, None),
    ("setpuf", 10942, "item7_setpuf_return"),
]


def require(ok: bool, problem: str) -> None:
    if not ok:
        raise AssertionError(problem)


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def f32(value: float) -> float:
    return struct.unpack("<f", struct.pack("<f", value))[0]


def one(deck: str, key: str) -> float:
    match = re.findall(r"!\s*" + re.escape(key) + r"\s*=\s*([^!\n\r]+)!",
                       deck, re.I)
    require(len(match) == 1, "original control missing/duplicated " + key)
    return float(match[0].strip().replace("D", "E").replace("d", "e"))


def load_original_dgm_module(path: Path):
    spec = importlib.util.spec_from_file_location("p7_dgm_oracle_tools", path)
    require(spec is not None and spec.loader is not None, "DGM reader not importable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def audit(vendor: Path, dgm_tool: Path, metadata: Path, first_hour: Path,
          control: Path, audit_record: Path, report: Path | None) -> dict:
    raw = vendor.read_bytes()
    require(sha(raw) == SHA_VENDOR, "unmodified vendor calpuff.for digest drift")
    lines = raw.decode("latin-1").splitlines()
    dgm = load_original_dgm_module(dgm_tool)
    require(dgm.ORIGINAL_CALPUFF_SHA256 == SHA_VENDOR, "DGM oracle source differs")
    pins = []
    for name, line_no, key in EXPECTED:
        require(line_no >= 1 and line_no <= len(lines), "vendor line out of bounds")
        if key is not None:
            anchor, expected_line, before, after = dgm.ANCHORS[key]
            require(anchor == line_no, f"vendor order anchor moved: {name}")
            require(lines[line_no - 1] == expected_line and
                    lines[line_no - 2] == before and
                    lines[line_no] == after,
                    f"vendor call order or Fortran statement changed: {name}")
        pins.append({"stage": name, "vendor_line": line_no,
                     "vendor_text": lines[line_no-1][:72]})
    require([p["vendor_line"] for p in pins] ==
            sorted(p["vendor_line"] for p in pins),
            "CALPUFF COMP step sequence out of order")

    data = json.loads(metadata.read_text())
    evidence = json.loads(audit_record.read_text())
    require(data["source"]["vendor_sha256"] == SHA_VENDOR, "DGM wrong source")
    require(data["binary"]["hours"] == 143 and
            data["binary"]["records"] == 254687 and
            data["binary"]["record_bytes"] == 352,
            "full DGM original 143h accounting changed")
    require(evidence["status"] == "ORIGINAL_PUFF_CON_IDENTICAL" and
            evidence["puff_con_identical"] and
            evidence["puff_con_matches_frozen_reference"] and
            evidence["frozen_reference_sha256"] == ORIGINAL_CON_SHA,
            "original Fortran instrumentation changed puff.con")
    table = data["time"]["hour_table"]
    require(len(table)==143 and sum(r["records"] for r in table) == 254687,
            "vendor reference has missing hourly records")
    hours = []
    for i, row in enumerate(table):
        packed = int(row["packed"])
        year, julian, hour = packed//100000, (packed//100)%1000, packed%100
        require(1 <= julian <= 366 and 0 <= hour < 24 and row["seconds"] == 0,
                "invalid original packed hour")
        timestamp = (dt.datetime(year,1,1) + dt.timedelta(days=julian-1,hours=hour))
        if hours:
            require(timestamp-hours[-1] == dt.timedelta(hours=1),
                    f"missing/nonsequential original DGM hour at index {i}")
        hours.append(timestamp)
    require(table[0]["packed"] == 202200100 and
            table[0]["records"] == 1275 and
            data["slice"]["sha256"] == SHA_HOUR0,
            "initial original hour identity mismatch")
    require(sha(first_hour.read_bytes()) == SHA_HOUR0, "modified original hour0 data")
    records=dgm._read_records(first_hour)
    require(len(records) == 1275, "wrong original first hour records")
    fields=control.read_text(encoding="latin-1")
    src=re.findall(r"!\s*X\s*=\s*([^!\n\r]+)!",fields,re.I)
    require(len(src)==1, "missing frozen source row")
    xy=[float(x.strip()) for x in src[0].split(",")]
    require(len(xy)==10, "wrong original source species count")
    dx=f32(one(fields,"DGRIDKM"))
    require(dx>0, "wrong original grid spacing")
    x=f32(f32(f32(xy[0])-f32(one(fields,"XORIGKM")))/dx)
    y=f32(f32(f32(xy[1])-f32(one(fields,"YORIGKM")))/dx)
    require((x,y)==(25.0,25.0),"input-derived original relative point source differs")
    initials=[r for r in records if r["iold"]==0 and r["ksam"]==r["nsstr"]]
    require(initials, "no original initial new-puff records")
    errors=[r for r in initials if
            (r["xold"]!=x or r["yold"]!=y or
             r["xpb_in"]!=x or r["ypb_in"]!=y or
             r["zold"]!=r["zpb_in"])]
    require(not errors,
            "original initial source coordinate/height state does not match control")
    origin_state={key:initials[0][key] for key in
                  ("packed","ii","iold","ksam","nsstr","xold","yold","zold",
                   "xpb_in","ypb_in","zpb_in","sigyb_in","sigzb_in")}
    # Main COMP branch location check is observational, not a claim of
    # runtime branch coverage (the untouched original DGM proves that).
    comp_calls=[]
    for lineno in range(9500, min(11200,len(lines))):
        code=lines[lineno-1][:72]
        if not code or code[0] in "cC*!":
            continue
        m=re.search(r"\bcall\s+(\w+)\s*\(",code,re.I)
        if m and m.group(1).lower() in (
            "points1","puffdz","advect","risewind","setpuf","getcell"):
            comp_calls.append({"line":lineno,"callee":m.group(1).upper()})

    out={
        "status":"ORIGINAL_SOURCE_ORDER_AND_INITIAL_ORACLE_PASS",
        "vendor_sha256":SHA_VENDOR,
        "COMP_phases":pins,
        "comp_selected_direct_calls":comp_calls,
        "original_initial_relative_x_cells":x,
        "original_initial_relative_y_cells":y,
        "original_first_hour_records":len(records),
        "original_initial_puff_samples":len(initials),
        "first_original_internal_state":origin_state,
        "original_six_hour_records":sum(r["records"] for r in table[:6]),
        "original_143_hour_records":sum(r["records"] for r in table),
        "original_143_hours":len(hours),
        "original_end_hour":hours[-1].isoformat(),
        "original_instrumentation_puff_con_identical":True,
        "cpp_integrated_driver": "NOT_YET_ESTABLISHED",
        "cpp_one_six_143_hour_PARITY": "NOT_YET_ESTABLISHED",
        "cpp_WROUT1_AVET_CONCENTRATION_PARITY": "NOT_YET_ESTABLISHED",
    }
    if report:
        report.parent.mkdir(parents=True,exist_ok=True)
        report.write_text(json.dumps(out,indent=2)+"\n")
    print("P7_ORIGINAL_COMP_PHASE_ORDER=PASS PHASES=9 SOURCE_SHA_PINNED=true")
    print("P7_ORIGINAL_FIRST_HOUR_INTERNAL_INPUT=PASS "
          f"RECORDS={len(records)} INITIAL_SAMPLES={len(initials)} XCELLS={x} YCELLS={y}")
    print("P7_ORIGINAL_DGM_1H_6H_143H=PASS "
          f"ROWS_1H={table[0]['records']} ROWS_6H={out['original_six_hour_records']} "
          f"ROWS_143H={out['original_143_hour_records']}")
    print("P7_CPP_1H_6H_143H_CONCENTRATION_PARITY=NOT_YET_ESTABLISHED")
    return out


def main() -> int:
    ap=argparse.ArgumentParser()
    for key in ("vendor","dgm-tool","metadata","first-hour","control","audit-record"):
        ap.add_argument("--"+key,required=True,type=Path)
    ap.add_argument("--report",type=Path)
    args=ap.parse_args()
    try:
        audit(args.vendor,args.dgm_tool,args.metadata,args.first_hour,
              args.control,args.audit_record,args.report)
    except (AssertionError,ValueError,OSError,KeyError,struct.error) as error:
        print("P7_ORIGINAL_ORDER_ORACLE=FAIL "+str(error),file=sys.stderr)
        return 1
    return 0

if __name__=="__main__":
    raise SystemExit(main())
