#!/usr/bin/env python3
"""Independent original CALMET ELUSTR2 cell-point vs native station flux audit.

Original: frozen, hash-locked 143h DGM point 6 inside ELUSTR2 immediately
before SIMILT (not a decoded CALMET.DAT proxy); native: no original values
injected and no original wind, only frozen SURF/UP/GEO and source physics.
ZII is intentionally not accepted here; MIXHTST is a separate upstream gate.
"""
from __future__ import annotations
import argparse,csv,hashlib,json,math
from pathlib import Path

SOURCE_SHA = "c82a63f62a2a09fc3fe704c751edfcfc737df758995e77d638026a05c69ce7ed"
TOL = {"QQH":(0.01,1e-4), "USTAR":(0.0001,1e-4),
       "EL":(0.2,0.001), "RHO":(0.0002,2e-4), "Z0":(0.,0.)}
COL={"QQH":"QH_Wm2","USTAR":"USTAR_mps","EL":"EL_m",
     "RHO":"rho_kgm3","Z0":"Z0_m"}
def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--reference",type=Path,required=True)
    ap.add_argument("--source-bin",type=Path,required=True)
    ap.add_argument("--native",type=Path,required=True)
    ap.add_argument("--out",type=Path,required=True)
    ap.add_argument("--require-parity",action="store_true")
    a=ap.parse_args()
    h=hashlib.sha256(a.source_bin.read_bytes()).hexdigest()
    if h!=SOURCE_SHA:raise RuntimeError(f"original cell trace SHA changed: {h}")
    reference=json.loads(a.reference.read_text())
    if (reference["source"]["vendor_sha256"]!="430381b4fb87f15127e20b13cc3e99be8a0e0fccf1d5821110af7f980558d134"
            or reference["binary"]["sha256"]!=SOURCE_SHA
            or reference["binary"]["records"]!=143):
        raise RuntimeError("source/provenance gate failed")
    rows=reference["rows"]
    if len(rows)!=143:raise RuntimeError("source reference not 143 hours")
    with a.native.open(newline="") as f:native=list(csv.DictReader(f))
    if len(native)!=143:raise RuntimeError("C++ station trace not 143 hours")
    stats={k:{"count":0,"exceedances":0,"max_abs":0.,"worst":None,"sum_sq":0.}
           for k in TOL}
    for i,(ref,row) in enumerate(zip(rows,native)):
        from datetime import datetime,timedelta
        label=(datetime(2022,1,1)+timedelta(hours=i+1)).strftime("%Y-%m-%d_%H")
        if row["hour_end"]!=label or ref["hour_index"]!=i+1:
            raise RuntimeError(f"hour mismatch index {i}")
        if (int(row["station_cell_i"]),int(row["station_cell_j"])) != (ref["IS"],ref["JS"]):
            raise RuntimeError(f"cell geometry mismatch hour {i+1}")
        for name,(abs_tol,rel_tol) in TOL.items():
            b=float(row[COL[name]]); z=float(ref[name])
            if not(math.isfinite(z) and math.isfinite(b)):
                raise RuntimeError(f"invalid {name} hour {i+1}")
            st=stats[name];error=abs(z-b)
            st["count"]+=1;st["sum_sq"]+=error*error
            if error>abs_tol+rel_tol*abs(z):st["exceedances"]+=1
            if error>st["max_abs"]:
                st["max_abs"]=error
                st["worst"]={"hour":i+1,"end":label,"original":z,"native":b,"error":error}
    for s in stats.values():s["rms"]=math.sqrt(s.pop("sum_sq")/s["count"])
    verdict="PASS_ORIGINAL_STATION_ELUSTR2" if all(s["exceedances"]==0 for s in stats.values()) else "FAIL_ORIGINAL_STATION_ELUSTR2"
    report={"verdict":verdict,"reference_sha256":SOURCE_SHA,
            "original_call":"CALMET L6580-L6894 ELUSTR2 immediately before MIXHTST/SIMILT",
            "source_injected_to_native":False,"hours":143,"tolerances":TOL,
            "statistics":stats,"full_UVW_pass":False}
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps(report,indent=2))
    if a.require_parity and verdict!="PASS_ORIGINAL_STATION_ELUSTR2":raise SystemExit(1)
if __name__=="__main__":main()
