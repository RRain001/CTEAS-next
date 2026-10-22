#!/usr/bin/env python3
"""Native P6E MIXHT vs untouched-source original after LAND MIXHT.

Native consumes only authentic met/GEO/SS/US and computes its own G24,
COMP third SURFVAR/HEATFX/ELUSTR, WATER, and sparse DPTT. Fortran source
trace is read here, *after* independently executing the native binary.
"""
from __future__ import annotations
import argparse,hashlib,json,math,struct
from pathlib import Path
from scripts.s4.s4r1c8e_original_mixht_avemix_stages import (
    NX,NY,NC,decode,sha
)
DATA=struct.Struct("<"+str(5*NC)+"f")
ZI_ABS_M=5e-3
ZI_REL=5e-5

def compare(original:Path,receipt:Path,native:Path,native_log:Path,
            report:Path)->bool:
    proof=json.loads(receipt.read_text())
    if(proof.get("status")!="PASS_ORIGINAL_NOAA_WATER_TO_LAND_MIXHT_TO_AVEMIX_SOURCE_ONLY"
       or proof.get("original_trace_sha256")!=sha(original)
       or proof.get("original_6h_45_met_byte_identical") is not True
       or proof.get("original_water_cells")!=63 or proof.get("original_land_cells")!=6907
       or proof.get("original_water_changes_from_land_mixht")!=0):
        raise ValueError("G54 missing independently certified genuine original sixhour COMP")
    native_text=native_log.read_text()
    if("S4R1C8F_NATIVE_REAL_LAND_MIXHT=PRODUCED_UNVERIFIED" not in native_text
       or "ORIGINAL_INTERMEDIATE_INJECTION=FALSE" not in native_text):
        raise ValueError("G54 native genuine source computation proof missing")
    if native.stat().st_size!=DATA.size:
        raise ValueError("G54 native original-free MIXHT candidate REAL4 shape changed")
    values=DATA.unpack(native.read_bytes())
    if not all(math.isfinite(v) for v in values):
        raise ValueError("G54 native MIXHT produced nonfinite field")
    stages=decode(original)
    original_before=stages[2,1]
    original_after=stages[2,2]
    if len(original_after[0])!=NC or len(original_after[1])!=NC:
        raise ValueError("G54 original pinned first-hour full grid missing")
    # Source water-mask is identified by the actual pre/post MIXHT
    # 63 water indices only after matching independently accepted G53 GEO
    # from the immutable authentic WATER result. A water mask must not
    # be fabricated from zero residuals, so require separate original
    # NOAA WATER geo source receipt before claiming LAND acceptance.
    # The original G54 comparator works on ALL NC cells; any mismatch
    # fails, including water values (which native G53 should preserve).
    result={}
    errors=[]
    above=0
    for k,name in enumerate(("MIXHT_ZI","MIXHT_ZICONV",
                             "AVEMIX_ZI","AVEMIX_ZICONV")):
        orig=(original_after if k<2 else stages[2,3])[k%2]
        pred=values[k*NC:(k+1)*NC]
        mx=-1.
        worst=None
        total=0.
        fails=0
        for index,(o,v) in enumerate(zip(orig,pred,strict=True)):
            d=abs(o-v)
            total+=d
            if d>mx:
                mx=d
                worst={"i":index%NX+1,"j":index//NX+1,
                       "original_m":o,"native_m":v,"abs_residual_m":d}
            if d>ZI_ABS_M+ZI_REL*max(abs(o),abs(v)):
                fails+=1
                if len(errors)<20:
                    errors.append({"field":name,"i":index%NX+1,
                                   "j":index//NX+1,"original":o,"native":v,
                                   "abs_error":d})
        above+=fails
        result[name]={"float_comparisons":NC,"max_abs_error_m":mx,
                      "mean_abs_error_m":total/NC,
                      "abs_tolerance_m":ZI_ABS_M,"rel_tolerance":ZI_REL,
                      "above_tolerance":fails,"worst":worst}
    # No inference about DPTT acceptance: the source tracing currently
    # includes only ZI and ZICONV, not native/Fortran DPTT parity.
    result_all={
        "status":("PASS_SCOPED_REAL_NOAA_NATIVE_MIXHT_AND_AVEMIX"
                  if above==0 else
                  "FAIL_REAL_NOAA_NATIVE_LAND_MIXHT_NUMERIC"),
        "case":"2022-06-01_01-02_UTC_true_2SS_1US_82x85x9",
        "science_scope":"FIRSTHOUR_SOURCE_COMP_LAND_MIXHT_AND_WHOLE_GRID_AVEMIX_ZI_ZICONV",
        "original_trace_sha256":sha(original),
        "native_source_only_candidate_sha256":sha(native),
        "original_sixhour_45_met_byte_identical":True,
        "native_original_intermediate_injection":False,
        "source_land_count":6907,"source_water_count":63,
        "float_compared":4*NC,
        "fields":result,
        "above_frozen_tolerance":above,
        "first_exceedances":errors,
        "native_avemix":"TEST_ONLY_NUMERIC_CANDIDATE",
        "native_wstarr_temp3d":"NOT_RUN",
        "native_6h_causal":"NOT_ACCEPTED",
        "g26_45field_p7":"NOT_ACCEPTED",
    }
    report.parent.mkdir(parents=True,exist_ok=True)
    report.write_text(json.dumps(result_all,indent=2,sort_keys=True)+"\n")
    print("S4R1C8F_NATIVE_SOURCE_MIXHT="+result_all["status"])
    print("S4R1C8F_MIXHT_ABOVE_TOLERANCE="+str(above))
    print("S4R1C8F_MIXHT_AVEMIX_MAX="+json.dumps(
        {k:v["max_abs_error_m"] for k,v in result.items()},sort_keys=True))
    print("S4R1C8F_AVEMIX_G26_P7=NOT_ACCEPTED")
    return above==0

def main():
    ap=argparse.ArgumentParser()
    for k in ("original","receipt","native","native-log","report"):
        ap.add_argument("--"+k,required=True,type=Path)
    args=ap.parse_args()
    if not compare(args.original,args.receipt,args.native,args.native_log,args.report):
        raise SystemExit(3)
if __name__=="__main__":main()
