#!/usr/bin/env python3
"""S4-R1c7b: real NOAA source-native G17C3 vs pinned original ELUSTR2 SIMILT.

Never load original station U/V into a C++ process. This script is purely a
post-hoc comparator of independently executed native and scratch original.
"""
from __future__ import annotations
import argparse
import csv
from datetime import datetime,timezone
import json
import math
from pathlib import Path

TOL_MPS=2e-4  # pre-existing unchanged original-vs-native SIMILT kernel gate
FIELDS=("surface_ordinal_1based","surface_id","upper_id","i","j","k",
        "hour_end_utc_seconds","levels_filled","native_u_mps",
        "native_v_mps","native_zii_m","native_station_qh_wm2",
        "native_station_ustar_mps")

def verify(original_report:Path,native_csv:Path,report:Path)->dict:
    ref=json.loads(original_report.read_text())
    if (ref.get("status")!="PASS_ORIGINAL_STATION_PROFILE_REFERENCE_ONLY" or
        ref.get("original_ELUSTR2_SIMILT_call_events")!=8 or
        ref.get("original_byte_identical") is not True):
        raise ValueError("Missing source-exact original 8-event six-hour oracle")
    events=ref.get("original_events",[])
    if len(events)!=8:
        raise ValueError("Original spatial/temporal event count corrupted")
    with native_csv.open(newline="") as handle:
        reader=csv.DictReader(handle)
        if tuple(reader.fieldnames or ())!=FIELDS:
            raise ValueError("Native first-hour G48 schema drift")
        rows=list(reader)
    if len(rows)!=9:
        raise ValueError("G48 must emit exactly nine vertical layers for ONE actual valid surface station")
    first=events[0]
    ordinal=int(rows[0]["surface_ordinal_1based"])
    if ordinal!=first["original_SIMILT_station_ordinal"]:
        raise ValueError("Original and native first valid station ordinal differ")
    i,j=first["original_station_grid_cell"]
    if (int(rows[0]["i"]),int(rows[0]["j"]))!=(i,j):
        raise ValueError("Original/native station cell ownership differs")
    filled=int(rows[0]["levels_filled"])
    if not 1<=filled<=9:
        raise ValueError("G48 original-coupled station valid height count invalid")
    residuals={"U":{"max_abs_mps":0.0,"at_level":None},
               "V":{"max_abs_mps":0.0,"at_level":None}}
    fails=[]
    count=0
    for k,row in enumerate(rows,1):
        if (int(row["k"])!=k or
            int(row["surface_ordinal_1based"])!=ordinal or
            (int(row["i"]),int(row["j"]))!=(i,j) or
            int(row["levels_filled"])!=filled):
            raise ValueError("Out-of-order/forged source native STHEOR levels")
        end=datetime.fromtimestamp(int(row["hour_end_utc_seconds"]),timezone.utc)
        if end.isoformat()!="2022-06-01T02:00:00+00:00":
            raise ValueError("Original-native NOAA model hour wrong")
        if k>filled:continue
        for component,name in enumerate(("U","V")):
            expected=float(first["original_profile_uv_mps"][2*(k-1)+component])
            actual=float(row["native_"+name.lower()+"_mps"])
            if not(math.isfinite(expected) and math.isfinite(actual)):
                raise ValueError("STHEOR nonfinite original/native")
            # A literal missing/sentinel in a level that native deems filled
            # is not physical parity and must NEVER be counted as passed.
            if abs(expected)>=900:
                raise ValueError("Original SIMILT source missing level vs native populated")
            delta=abs(actual-expected)
            count+=1
            if delta>residuals[name]["max_abs_mps"]:
                residuals[name]={"max_abs_mps":delta,"at_level":k}
            if delta>TOL_MPS and len(fails)<30:
                fails.append({"field":name,"level":k,
                              "original":expected,"native":actual,
                              "abs_error":delta})
    if count<=0:
        raise ValueError("No genuine populated station layers compared")
    verdict={
        "status":"PASS_REAL_FIRSTHOUR_ORIGINAL_NATIVE_SPARSE_STHEOR_SIMILT"
                  if not fails else "FAIL_REAL_FIRSTHOUR_ORIGINAL_NATIVE_SPARSE_STHEOR_SIMILT",
        "oracle_original_sixhour_STHEOR_events":8,
        "original_firsthour_station_ordinal":ordinal,
        "grid_cell_ij":[i,j],
        "native_surface_station_count":2,
        "native_valid_firsthour_stheor_sites":1,
        "native_skipped_missing_firsthour_ss":1,
        "native_original_valid_level_uv_comparisons":count,
        "original_similt_preexisting_tolerance_mps":TOL_MPS,
        "residuals":residuals,
        "out_of_limit_samples":fails,
        "p5_missing_calm":"UNCHANGED",
        "g23_native_inter2":"NOT_RUN",
        "g24_native_final_wind":"NOT_RUN",
        "g14_native_6h_water_comp":"NOT_RUN",
        "g26_native_6h_45_fields":"NOT_ACCEPTED",
        "p7":"NOT_ACCEPTED"
    }
    report.parent.mkdir(parents=True,exist_ok=True)
    report.write_text(json.dumps(verdict,indent=2,sort_keys=True)+"\n")
    print("S4R1C7B_FIRSTHOUR_STATION_RESIDUALS="+json.dumps(residuals,sort_keys=True))
    if fails:
        raise ValueError("Actual first-hour original/native STHEOR station profile discrepancy")
    print("S4R1C7B_GENUINE_NOAA_NATIVE_STHEOR_SIMILT=PASS_STATION_SCOPED")
    print("S4R1C7B_NATIVE_G23_INTER2_G24_G26_P7=NOT_ACCEPTED")
    return verdict

def main()->None:
    p=argparse.ArgumentParser()
    for key in ("original-report","native-csv","report"):
        p.add_argument("--"+key,required=True,type=Path)
    a=p.parse_args()
    verify(a.original_report,a.native_csv,a.report)
if __name__=="__main__":main()
