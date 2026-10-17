#!/usr/bin/env python3
"""Read-only 143h first-divergence check of P6D station COMP recurrence.

Native inputs: initial SURF/UP/GEO + native P6D wind -> P6E COMP history
  (ZI/ZICONV/DPTT, no original U/V/W reference fields injected).
Next P6D: uses previous hour's native COMP history, computes independent
  STHEOR/ELUSTR2 + MIXHTST + SIMILT, outputs station_mixhtst.csv.

CALMET original point-6 station sample and COMP point-3 history are used
ONLY in this comparator, never in the native producers. This is a state
closure diagnostic, NOT 143h full U/V/W parity certification.
"""
import argparse
import csv
import hashlib
import json
import math
import struct
from datetime import datetime,timedelta
from pathlib import Path

from p6d_station_mixhtst_source_precursor_143h import source

NC=2500
STATION=25+25*50
EXPECTED_SHA="c82a63f62a2a09fc3fe704c751edfcfc737df758995e77d638026a05c69ce7ed"
METRICS={
    "EL_M":("EL",0.2,0.001),
    "ZI_M":("ZII_TO_SIMILT",0.03,1.e-5),
    "ZICONV_M":("ZICONVI_AFTER_MIXHTST",0.03,1.e-5),
    "DPTT_K":("DPTT",0.002,1.e-5),
    "PREV_ZI_M":("ZI_GRID_ENTERING",0.03,1.e-5),
    "PREV_ZICONV_M":("ZICONV_GRID_ENTERING",0.03,1.e-5),
    "PREV_DPTT_K":("_PREV_DPTT",0.002,1.e-5),
}
def native_history(prefix:Path):
    with Path(str(prefix)+".state.json").open() as f:meta=json.load(f)
    if (meta.get("producer")!="p6e_calmet_dat21 emit-realcase" or
        meta.get("shape")!=[143,50,50] or
        "dptt" not in meta.get("fields",[]) or
        not meta.get("wind_source")):
        raise RuntimeError("native COMP state provenance, shape, DPTT or wind source invalid")
    history={}
    for key in ("zi","ziconv","dptt"):
        path=Path(str(prefix)+"."+key+".f32")
        raw=path.read_bytes()
        if len(raw)!=143*NC*4:raise RuntimeError(f"missing native COMP field {key}")
        history[key]=struct.unpack("<357500f",raw)
        if not all(math.isfinite(v) for v in history[key]):
            raise RuntimeError(f"invalid native COMP values {key}")
    return history,meta

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--cell-json",type=Path,required=True)
    ap.add_argument("--cell-bin",type=Path,required=True)
    ap.add_argument("--state-bin",type=Path,required=True)
    ap.add_argument("--comp-prefix",type=Path,required=True)
    ap.add_argument("--station-csv",type=Path,required=True)
    ap.add_argument("--out",type=Path,required=True)
    ap.add_argument("--require-parity",action="store_true")
    a=ap.parse_args()
    orig,prev_dptt=source(a.cell_json,a.cell_bin,a.state_bin)
    native,meta=native_history(a.comp_prefix)
    with a.station_csv.open(newline="") as f:rows=list(csv.DictReader(f))
    if len(rows)!=143:raise RuntimeError("native station record count not 143")
    stats={key:{"compared":0,"exceedances":0,"max_abs":0.0,"sum_sq":0.0,
                "first_exceedance":None,"worst":None} for key in METRICS}
    coupled_identity=0
    for h,(src,row) in enumerate(zip(orig,rows)):
        date=(datetime(2022,1,1)+timedelta(hours=h+1)).strftime("%Y-%m-%d_%H")
        if row["hour_end"]!=date or src["hour_index"]!=h+1 or row["source_kind"]!="native_p6e_comp_previous_hour":
            raise RuntimeError("station chain hour/provenance differs")
        for name,(target,abstol,reltol) in METRICS.items():
            ref=float(prev_dptt[h] if target=="_PREV_DPTT" else src[target])
            got=float(row[name])
            if not(math.isfinite(ref) and math.isfinite(got)):
                raise RuntimeError(f"nonfinite station metric {name}")
            st=stats[name];err=abs(got-ref);st["compared"]+=1
            st["sum_sq"]+=err*err
            if err>st["max_abs"]:
                st["max_abs"]=err
                st["worst"]={"hour":h+1,"end":date,"reference":ref,
                             "native":got,"abs_error":err}
            if err>abstol+reltol*abs(ref):
                st["exceedances"]+=1
                if st["first_exceedance"] is None:
                    st["first_exceedance"]={"hour":h+1,"end":date,"reference":ref,
                                           "native":got,"abs_error":err}
        if h>0:
            for key,col in (("zi","PREV_ZI_M"),("ziconv","PREV_ZICONV_M"),
                            ("dptt","PREV_DPTT_K")):
                prior=native[key][(h-1)*NC+STATION]
                if abs(float(row[col])-prior)>1.e-4+1.e-6*abs(prior):
                    raise RuntimeError(f"P6D failed to read actual P6E previous hour state: {date}/{key}")
                coupled_identity+=1
        else:
            if any(abs(float(row[k]))>1e-9 for k in
                   ("PREV_ZI_M","PREV_ZICONV_M","PREV_DPTT_K")):
                raise RuntimeError("first station hour not cold-started")
    for value in stats.values():
        value["rms"]=math.sqrt(value.pop("sum_sq")/value["compared"])
    status="PASS_NATIVE_COMP_STATION" if all(v["exceedances"]==0 for v in stats.values()) else "FAIL_NATIVE_COMP_STATION"
    report={
        "status":status,"hours":143,"source_original_sha256":EXPECTED_SHA,
        "native_comp_history_provenance":meta.get("wind_source"),
        "source_oracle_injected_into_native":False,
        "native_previous_hour_links_checked":coupled_identity,
        "comparison_kind":"Original CALMET point-6 station states vs native COMP driven P6D ELUSTR2/MIXHTST/SIMILT",
        "not_full_UVW_acceptance":True,
        "first_failure_by_field":{k:v["first_exceedance"] for k,v in stats.items()},
        "fields":stats,
        "tolerances":{k:{"absolute":v[1],"relative":v[2]} for k,v in METRICS.items()}}
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps(report,indent=2))
    if a.require_parity and status!="PASS_NATIVE_COMP_STATION":raise SystemExit(1)
if __name__=="__main__":main()
