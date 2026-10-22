#!/usr/bin/env python3
"""Compare genuine native G53 WATER ZI to independent original COMP stages.

The actual native CSV is created independently from original source G24.
Never pass original stage data as native forcing. This stage diagnostic
does NOT execute or certify LAND MIXHT nor AVEMIX in native.
"""
from __future__ import annotations
import argparse,csv,hashlib,json,math
from pathlib import Path
from scripts.s4.s4r1c8e_original_mixht_avemix_stages import (
    NX,NY,NC,sha,decode
)
ABS_ZI_M=5e-3
REL_ZI=5e-5
def compare(trace:Path,receipt:Path,native:Path,native_log:Path,
            report:Path)->bool:
    source=json.loads(receipt.read_text())
    if(source.get("status")!=
       "PASS_ORIGINAL_NOAA_WATER_TO_LAND_MIXHT_TO_AVEMIX_SOURCE_ONLY"
       or source.get("original_trace_sha256")!=sha(trace)
       or source.get("original_water_cells")!=63
       or source.get("original_water_changes_from_land_mixht")!=0
       or source.get("original_6h_45_met_byte_identical") is not True):
        raise ValueError("G54 original real source pre/post MIXHT provenance absent")
    log=native_log.read_text()
    if("S4R1C8D_REAL_NOAA_G24_TO_WATER=PRODUCED_UNVERIFIED" not in log
       or "ORIGINAL_WIND_INJECTION=FALSE" not in log):
        raise ValueError("G54 authentic native G24→G53 proof not available")
    data=decode(trace)
    first=data[2,1]
    post=data[2,2]
    last=data[2,3]
    points={}
    with native.open(newline="") as f:
        for r in csv.DictReader(f):
            i,j,cat=int(r["i"]),int(r["j"]),int(r["landuse"])
            if not(1<=i<=NX and 1<=j<=NY and 50<=cat<=55):
                raise ValueError("G54 invalid native WATER grid")
            idx=(j-1)*NX+i-1
            if idx in points:raise ValueError("G54 duplicate native WATER cell")
            zi=float(r["zi"]);zc=float(r["ziconv"])
            if not(math.isfinite(zi) and math.isfinite(zc)):
                raise ValueError("G54 nonfinite native water state")
            points[idx]=(zi,zc)
    if len(points)!=63:raise ValueError("G54 real NOAA WATER count !=63")
    maxerr=0.
    exceeded=0
    worst=None
    for idx,(zi,zc) in points.items():
        for step,values in (("pre_land_mixht",first),
                            ("after_land_mixht",post)):
            original_zi=values[0][idx]
            original_zc=values[1][idx]
            diff=abs(zi-original_zi)
            if diff>maxerr:
                maxerr=diff
                worst={"i":idx%NX+1,"j":idx//NX+1,
                       "stage":step,"original_zi_m":original_zi,
                       "native_zi_m":zi,"abs_diff_m":diff}
            if diff>ABS_ZI_M+REL_ZI*max(abs(zi),abs(original_zi)):
                exceeded+=1
            if zc!=0 or original_zc!=0:
                exceeded+=1
        if first[0][idx]!=post[0][idx] or first[1][idx]!=post[1][idx]:
            exceeded+=1
    result={
        "status":("PASS_REAL_NOAA_NATIVE_G53_WATER_BEFORE_AND_AFTER_LAND_MIXHT"
                  if exceeded==0 else
                  "FAIL_NUMERIC_REAL_NOAA_WATER_STAGE_HANDOFF"),
        "scope":"FIRSTHOUR_WATER_AFTER_REAL_WATER_BEFORE_AND_AFTER_ORIGINAL_LAND_MIXHT",
        "original_6h45_met_byte_identical":True,
        "original_trace_sha256":sha(trace),
        "native_g53_source_sha256":sha(native),
        "original_values_used_in_native_forcing":False,
        "source_grid":[NX,NY],"water_points":len(points),
        "water_zi_comparisons":2*len(points),
        "water_ziconv_exact_zeros_checked":2*len(points),
        "frozen_abs_zi_m":ABS_ZI_M,
        "frozen_rel_zi":REL_ZI,
        "above_tolerance_or_contract":exceeded,
        "max_abs_zi_residual_m":maxerr,
        "worst_zi":worst,
        "original_water_after_avemix_zi_changed_count":sum(
            last[0][idx]!=post[0][idx] for idx in points),
        "native_land_mixht":"NOT_RUN",
        "native_avemix":"NOT_RUN",
        "native_g26_45fields":"NOT_ACCEPTED",
        "causal_sixhours":"NOT_ACCEPTED",
        "p7":"NOT_ACCEPTED",
    }
    report.parent.mkdir(parents=True,exist_ok=True)
    report.write_text(json.dumps(result,sort_keys=True,indent=2)+"\n")
    print("S4R1C8E_ORIGINAL_NATIVE_G53_WATER_STAGE="+result["status"])
    print("S4R1C8E_NATIVE_WATER_ABOVE_TOLERANCE="+str(exceeded))
    print("S4R1C8E_G26_P7=NOT_ACCEPTED")
    return exceeded==0
def main()->None:
    p=argparse.ArgumentParser()
    for k in ("trace","receipt","native","native-log","report"):
        p.add_argument("--"+k,type=Path,required=True)
    a=p.parse_args()
    if not compare(a.trace,a.receipt,a.native,a.native_log,a.report):
        raise SystemExit(3)
if __name__=="__main__":main()
