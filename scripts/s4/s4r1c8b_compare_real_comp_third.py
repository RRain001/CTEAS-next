#!/usr/bin/env python3
"""Independent genuine NOAA CALMET COMP third SURFVAR vs native G17B4.

The source trace is read only AFTER independently executing G51;
the native executable accepts no original temperatures as forcing.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from pathlib import Path
import struct
from scripts.s4.s4r1c8b_original_real_comp_third_surfvar import (
    CELLS,NX,NY,HOURS,HEADER,DATA,RECORD,FIRST,sha
)
TOL_K=2e-4
def compare(original:Path,receipt:Path,native:Path,native_log:Path,
            report:Path)->bool:
    src=json.loads(receipt.read_text())
    if (src.get("status")!="PASS_ORIGINAL_REAL_NOAA_COMP_THIRD_REFERENCE_ONLY"
        or src.get("original_met_byte_identical") is not True
        or src.get("original_third_trace_sha256")!=sha(original)
        or src.get("six_original_hours")!=HOURS
        or src.get("grid")!=[NX,NY]):
        raise ValueError("original third COMP SURFVAR source reference not validated")
    log=native_log.read_text()
    if ("S4R1C8B_NATIVE_REAL_COMP_THIRD=PRODUCED_UNVERIFIED" not in log
        or "NO_FORTRAN_ORACLE_INPUT=TRUE" not in log
        or "P5_RAW_UNCHANGED=TRUE" not in log):
        raise ValueError("native COMP third source marker absent")
    raw=original.read_bytes()
    if len(raw)!=HOURS*RECORD:
        raise ValueError("original COMP third record size mutated")
    packed=FIRST.year*100000+FIRST.timetuple().tm_yday*100+FIRST.hour
    if HEADER.unpack_from(raw,0)!=(56,packed,0,NX,NY,0):
        raise ValueError("original third COMP source first UTC drift")
    reference=DATA.unpack_from(raw,HEADER.size)
    if native.stat().st_size!=DATA.size:
        raise ValueError("native real 6970-cell COMP third data missing")
    predicted=DATA.unpack(native.read_bytes())
    if not all(math.isfinite(x) for x in reference+predicted):
        raise ValueError("COMP third contains nonfinite temperature")
    errors=[abs(a-b) for a,b in zip(reference,predicted,strict=True)]
    above=sum(x>TOL_K for x in errors)
    bit_diff=sum(struct.pack("<f",a)!=struct.pack("<f",b)
                 for a,b in zip(reference,predicted,strict=True))
    max_index=max(range(CELLS),key=errors.__getitem__)
    result={
        "status":("PASS_GENUINE_NOAA_ORIGINAL_NATIVE_COMP_THIRD_SCOPED_FIRSTHOUR"
                  if above==0 else
                  "FAIL_NUMERIC_GENUINE_NOAA_COMP_THIRD_FIRSTHOUR"),
        "scope":"G24_FINAL_WIND_TO_COMP_SURFVAR_IALL1_ONLY",
        "provenance_original_trace_sha256":sha(original),
        "provenance_native_candidate_sha256":sha(native),
        "original_pristine_scratch_sixhour_45fields_byte_identical":True,
        "original_source_hour_utc":FIRST.isoformat(),
        "original_g26_native_fields_injected":False,
        "source_noaa_cardinality":{"SS":2,"US":1},
        "grid":[NX,NY],
        "compared_float_cells":CELLS,
        "frozen_abs_tolerance_kelvin":TOL_K,
        "above_frozen_tolerance":above,
        "bit_mismatches_diagnostic_only":bit_diff,
        "max_abs_residual_kelvin":errors[max_index],
        "mean_abs_residual_kelvin":sum(errors)/CELLS,
        "worst_cell":{
            "i_1based":max_index%NX+1,
            "j_1based":max_index//NX+1,
            "original_kelvin":reference[max_index],
            "native_kelvin":predicted[max_index]
        },
        "native_g26_45field":"NOT_ACCEPTED",
        "causal_sixhour_history":"NOT_ACCEPTED",
        "p7":"NOT_ACCEPTED",
    }
    report.parent.mkdir(parents=True,exist_ok=True)
    report.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print("S4R1C8B_COMP_THIRD_NUMERIC="+result["status"])
    print("S4R1C8B_TEMPERATURE_MAX_ABS_K="+str(errors[max_index]))
    print("S4R1C8B_ABOVE_TOLERANCE="+str(above))
    print("S4R1C8B_G26_P7=NOT_ACCEPTED")
    return above==0
def main()->None:
    p=argparse.ArgumentParser()
    for k in ("original","source-receipt","native","native-log","report"):
        p.add_argument("--"+k,type=Path,required=True)
    args=p.parse_args()
    if not compare(args.original,args.source_receipt,args.native,
                   args.native_log,args.report):
        raise SystemExit(3)
if __name__=="__main__":main()
