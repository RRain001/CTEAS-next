#!/usr/bin/env python3
"""Genuine original CALMET WSTARR vs fully source-native G55.

All original values are independent external verification only; native
binary accepts original NOAA forcing but no original physical outputs.
"""
from __future__ import annotations
import argparse,hashlib,json,math
from pathlib import Path
from scripts.s4.s4r1c8g_original_comp_wstarr import (
    NX,NY,NC,GRID,records,sha
)
TOL=2e-4  # m/s, absolute
def compare(original:Path,receipt:Path,native:Path,native_log:Path,report:Path)->bool:
    obj=json.loads(receipt.read_text())
    if(obj.get("status")!="PASS_ORIGINAL_GENUINE_NOAA_SIXHOUR_WSTARR_REFERENCE_ONLY"
       or obj.get("original_wstarr_trace_sha256")!=sha(original)
       or obj.get("original_sixhour_45field_met_byte_identical") is not True
       or obj.get("grid")!=[NX,NY]
       or obj.get("firsthour_nonzero_cell_count",0)<=0):
        raise ValueError("G55 genuine original sixhour WSTARR not certified")
    log=native_log.read_text()
    if("S4R1C8G_NATIVE_NOAA_COMP_WSTARR=PRODUCED_UNVERIFIED" not in log
       or "NO_ORIGINAL_INTERMEDIATE_INPUT=TRUE" not in log):
        raise ValueError("G55 true source-native WSTARR production missing")
    if native.stat().st_size!=GRID.size:
        raise ValueError("G55 native WSTARR REAL4 field incomplete")
    original_field=records(original)[0]
    native_field=GRID.unpack(native.read_bytes())
    if not all(math.isfinite(x) and x>=0 for x in native_field):
        raise ValueError("G55 native WSTARR produced nonfinite/negative")
    above=0
    maximum=0.
    mean=0.
    mismatch=[]
    worst=None
    for idx,(a,b) in enumerate(zip(original_field,native_field,strict=True)):
        err=abs(a-b)
        mean+=err
        if err>maximum:
            maximum=err
            worst={"i":idx%NX+1,"j":idx//NX+1,
                   "original":a,"native":b,"abs_residual":err}
        if err>TOL:
            above+=1
            if len(mismatch)<20:
                mismatch.append({"i":idx%NX+1,"j":idx//NX+1,
                                 "original":a,"native":b,"abs_residual":err})
    result={
        "status":("PASS_SCOPED_REAL_NOAA_NATIVE_WSTARR_FIRST_HOUR"
                  if above==0 else "FAIL_REAL_NOAA_NATIVE_WSTARR_NUMERIC"),
        "scope":"G54_NATIVE_COMP_AVEMIX_TO_P6E_WSTARR_6970_CELLS_ONLY",
        "original_sixhour_45field_byte_identical":True,
        "original_wstarr_sha256":sha(original),
        "native_wstarr_sha256":sha(native),
        "fortran_wstarr_injected_to_cpp":False,
        "compared_real4":NC,
        "frozen_abs_tolerance_mps":TOL,
        "above_tolerance":above,
        "max_abs_residual_mps":maximum,
        "mean_abs_residual_mps":mean/NC,
        "worst":worst,
        "first_mismatches":mismatch,
        "native_temp3d":"NOT_RUN",
        "native_g26_45fields":"NOT_ACCEPTED",
        "native_sixhour_causal":"NOT_ACCEPTED",
        "p7":"NOT_ACCEPTED",
    }
    report.parent.mkdir(parents=True,exist_ok=True)
    report.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print("S4R1C8G_NATIVE_REAL_NOAA_WSTARR="+result["status"])
    print("S4R1C8G_WSTARR_ABOVE_TOLERANCE="+str(above))
    print("S4R1C8G_WSTARR_MAX_ABS_MPS="+str(maximum))
    print("S4R1C8G_TEMP3D_G26_P7=NOT_ACCEPTED")
    return above==0
def main():
    p=argparse.ArgumentParser()
    for k in ("original","receipt","native","native-log","report"):
        p.add_argument("--"+k,required=True,type=Path)
    a=p.parse_args()
    if not compare(a.original,a.receipt,a.native,a.native_log,a.report):
        raise SystemExit(3)
if __name__=="__main__":main()
