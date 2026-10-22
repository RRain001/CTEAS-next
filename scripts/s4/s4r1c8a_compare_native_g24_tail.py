#!/usr/bin/env python3
"""Real 82x85x9 original Fortran G24 tail vs frozen native C++ G24.

No original wind, W, divergence, or boundaries are ever passed to the
native executable. A fail-closed diagnostic, not production G26 approval.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from pathlib import Path
import struct
from scripts.s4.s4r1c8a_real_noaa_original_g24_tail import (
    NX,NY,NZ,HOURS,COUNTS,COUNT,HEADER,RECORD_BYTES,FIRST,sha
)
FIELDS=("U_mps","V_mps","W_face_mps","div_per_s","UB_mps","VB_mps")
WIND_TOL=2e-4
DIV_TOL=1e-6

def compare(original:Path,receipt:Path,native:Path,native_log:Path,
            report:Path)->bool:
    o=json.loads(receipt.read_text())
    if (o.get("status")!="PASS_GENUINE_NOAA_ORIGINAL_POST_G24_SOURCE_REFERENCE_ONLY"
        or o.get("original_met_byte_identical") is not True
        or o.get("dimensions")!=[NX,NY,NZ]
        or o.get("components_per_record")!=list(COUNTS)
        or o.get("original_full_six_hour_tail_sha256")!=sha(original)):
        raise ValueError("G24 original SHA/provenance not independently accepted")
    if ("S4R1C8A_REAL_NOAA_NATIVE_G24=PRODUCED_UNVERIFIED" not in native_log.read_text()
        or "ORIGINAL_WIND_INJECTION=FALSE" not in native_log.read_text()):
        raise ValueError("G24 native source-only producer not recognized")
    raw=original.read_bytes()
    if len(raw)!=HOURS*RECORD_BYTES:
        raise ValueError("G24 true six-hour original raw reference incomplete")
    key=FIRST.year*100000+FIRST.timetuple().tm_yday*100+FIRST.hour
    if HEADER.unpack_from(raw,0)!=(54,key,0,NX,NY,NZ):
        raise ValueError("G24 original first-hour UTC/shape mismatch")
    values=struct.Struct("<"+str(COUNT)+"f")
    physical_original=values.unpack_from(raw,HEADER.size)
    if native.stat().st_size!=4*COUNT:
        raise ValueError("G24 native six-field first-hour payload missing")
    physical_native=values.unpack(native.read_bytes())
    if not all(map(math.isfinite,physical_original+physical_native)):
        raise ValueError("G24 original/native nonfinite data")
    diff={}
    start=0
    total_bad=0
    worst=None
    first_errors=[]
    for name,length in zip(FIELDS,COUNTS,strict=True):
        maximum=0.
        sum_err=0.
        failures=0
        tol=DIV_TOL if name=="div_per_s" else WIND_TOL
        for n in range(length):
            x=physical_original[start+n]
            y=physical_native[start+n]
            residual=abs(x-y)
            if residual>maximum:
                maximum=residual
            sum_err+=residual
            if residual>tol:
                failures+=1
                if len(first_errors)<16:
                    first_errors.append({"field":name,"offset":n,
                                         "original":x,"native":y,
                                         "absolute_error":residual})
            if worst is None or residual>worst["absolute_error"]:
                worst={"field":name,"offset":n,"original":x,"native":y,
                       "absolute_error":residual}
        diff[name]={"comparisons":length,"max_abs":maximum,
                    "mean_abs":sum_err/length,
                    "tolerance":tol,"above_tolerance":failures}
        total_bad+=failures
        start+=length
    result={
        "status":("PASS_SCOPED_REAL_NOAA_ORIGINAL_NATIVE_G24_FIRST_HOUR"
                  if total_bad==0 else
                  "FAIL_NUMERIC_REAL_NOAA_ORIGINAL_NATIVE_G24_FIRST_HOUR"),
        "scope":"ACTUAL_NOAA_FIRSTHOUR_POST_G24_TAIL_ONLY",
        "source_original_sha256":sha(original),
        "source_original_pristine_met_byte_identical":True,
        "native_candidate_sha256":sha(native),
        "native_original_wind_injection":False,
        "grid":[NX,NY,NZ],
        "field_comparison":diff,
        "total_float_comparisons":COUNT,
        "above_fixed_tolerances":total_bad,
        "worst_raw_absolute_residual":worst,
        "first_exceedances":first_errors,
        "model_start_utc":FIRST.isoformat(),
        "native_full_g26_45fields":"NOT_ACCEPTED",
        "native_six_hour_causal_state":"NOT_ACCEPTED",
        "p7":"NOT_ACCEPTED",
    }
    report.parent.mkdir(parents=True,exist_ok=True)
    report.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print("S4R1C8A_ORIGINAL_NATIVE_G24_REPORT="+result["status"])
    print("S4R1C8A_G24_ABOVE_TOLERANCE="+str(total_bad))
    print("S4R1C8A_G24_DIAGNOSTICS="+json.dumps(diff,sort_keys=True))
    print("S4R1C8A_G26_P7=NOT_ACCEPTED")
    return total_bad==0

def main()->None:
    p=argparse.ArgumentParser()
    for k in ("original","source-receipt","native","native-log","report"):
        p.add_argument("--"+k,required=True,type=Path)
    z=p.parse_args()
    if not compare(z.original,z.source_receipt,z.native,z.native_log,z.report):
        raise SystemExit(3)

if __name__=="__main__":main()
