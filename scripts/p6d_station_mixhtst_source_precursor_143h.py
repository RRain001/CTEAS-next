#!/usr/bin/env python3
"""Forensic MIXHTST transition comparator with ORIGINAL precursor state.

This isolates the original STHEOR/MIXHTST numerical formula by replaying the
already source-dumped *entering* COMP grid ZI/ZICONV/DPTT and original station
QH/USTAR/EL/RHO. It is NOT an autonomous P6D end-to-end test: using prior
original fields as inputs is strictly for physical kernel bisection.
"""
import argparse,csv,hashlib,json,math,struct
from pathlib import Path
CELLS=2500
CELL=25+25*50  # original surface station at (26,26) 1-based
CELL_SHA="c82a63f62a2a09fc3fe704c751edfcfc737df758995e77d638026a05c69ce7ed"
STATE_SHA="e6b8ab309f81ddc3015dc750272eeb2ee8289a2d34563b364884d9e443be6ece"
TOL={"ZI_M":(0.03,1e-5),"ZICONV_M":(0.03,1e-5),"DPTT_K":(0.002,1e-5)}
KEYS={"ZI_M":"ZII_TO_SIMILT","ZICONV_M":"ZICONVI_AFTER_MIXHTST","DPTT_K":"DPTT"}
NUM_FIELDS={1:5,2:2,3:3,4:2,5:2}

def source(rows_file,cell_file,state_file):
    if hashlib.sha256(cell_file.read_bytes()).hexdigest()!=CELL_SHA:
        raise RuntimeError("source CALMET station-cell binary SHA changed")
    if hashlib.sha256(state_file.read_bytes()).hexdigest()!=STATE_SHA:
        raise RuntimeError("source CALMET grid DPTT binary SHA changed")
    x=json.loads(rows_file.read_text())
    if x["source"]["vendor_sha256"]!="430381b4fb87f15127e20b13cc3e99be8a0e0fccf1d5821110af7f980558d134":
        raise RuntimeError("original vendor source drift")
    rows=x["rows"]
    if len(rows)!=143:raise RuntimeError("original source hourly cell count wrong")
    raw=state_file.read_bytes()
    off=0; previous_dptt=0.
    previous=[]
    for hour in range(1,144):
        previous.append(previous_dptt)
        for kpt in range(1,6):
            if off+32>len(raw):raise RuntimeError("original COMP state truncated")
            tags=struct.unpack_from("<8i",raw,off)
            if tags[0]!=kpt or tags[1]!=hour or tags[-2:]!=(50,50):
                raise RuntimeError(f"COMP state record mismatch hour={hour} point={kpt}")
            if kpt==3:
                previous_dptt=struct.unpack_from("<f",raw,
                    off+32+(2*CELLS+CELL)*4)[0]
            off+=32+4*CELLS*NUM_FIELDS[kpt]
        if not math.isfinite(previous_dptt):
            raise RuntimeError("original grid DPTT not finite")
    if off!=len(raw):raise RuntimeError("original COMP state has trailing bytes")
    return rows,previous

def prepare(args,rows,previous):
    # We explicitly use original prior COMP grid state to isolate
    # the independently reconstructed MIXHTST kernel, never call this native.
    with args.out.open("w") as f:
        f.write("143\n")
        for hour,(r,prev_dptt) in enumerate(zip(rows,previous),1):
            if r["hour_index"]!=hour or (r["IS"],r["JS"])!=(26,26):
                raise RuntimeError("original station identity/hour unexpected")
            vals=[hour,r["ZI_GRID_ENTERING"],r["ZICONV_GRID_ENTERING"],
                  prev_dptt,r["QQH"],r["USTAR"],r["EL"],r["RHO"]]
            if not all(math.isfinite(float(v)) for v in vals):
                raise RuntimeError("source input not finite")
            f.write(" ".join(f"{v:.10g}" if isinstance(v,float) else str(v) for v in vals)+"\n")
    print(json.dumps({"status":"ORIGINAL_MIXHTST_PRECURSOR_FIXTURE_READY",
                      "hours":143,"uses_source_precursor":True,
                      "forensic_only":True,"path":str(args.out)}))

def compare(args,rows):
    with args.native.open(newline="") as f:native=list(csv.DictReader(f))
    if len(native)!=143:raise RuntimeError("MIXHTST output missing hours")
    stats={k:{"count":0,"exceedances":0,"max_abs":0.,"worst":None,"sum_sq":0.}
           for k in KEYS}
    for hour,(r,n) in enumerate(zip(rows,native),1):
        if int(n["hour"])!=hour:raise RuntimeError("MIXHTST output reordered")
        for name,key in KEYS.items():
            ref=float(r[key]);act=float(n[name])
            if not(math.isfinite(ref) and math.isfinite(act)):
                raise RuntimeError("invalid station source value")
            err=abs(ref-act);st=stats[name]
            st["count"]+=1;st["sum_sq"]+=err*err
            a,b=TOL[name]
            if err>a+b*abs(ref):st["exceedances"]+=1
            if err>st["max_abs"]:
                st["max_abs"]=err;st["worst"]={"hour":hour,"original":ref,"cpp":act,"abs_error":err}
    for st in stats.values():st["rms"]=math.sqrt(st.pop("sum_sq")/st["count"])
    verdict="PASS_ORIGINAL_MIXHTST_SOURCE_PRECURSOR" if all(st["exceedances"]==0 for st in stats.values()) else "FAIL_ORIGINAL_MIXHTST_SOURCE_PRECURSOR"
    report={"verdict":verdict,"hours":143,"uses_original_precursor":True,
            "cannot_certify_autonomous_uvw":True,
            "frozen_original_cell_sha256":CELL_SHA,"frozen_original_grid_dptt_sha256":STATE_SHA,
            "tolerance":TOL,"fields":stats}
    args.out.write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps(report,indent=2))
    if args.require_parity and verdict.startswith("FAIL"):raise SystemExit(1)

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--mode",choices=["prepare","compare"],required=True)
    p.add_argument("--cell-json",type=Path,required=True)
    p.add_argument("--cell-bin",type=Path,required=True)
    p.add_argument("--state-bin",type=Path,required=True)
    p.add_argument("--native",type=Path)
    p.add_argument("--out",type=Path,required=True)
    p.add_argument("--require-parity",action="store_true")
    a=p.parse_args()
    rows,previous=source(a.cell_json,a.cell_bin,a.state_bin)
    a.out.parent.mkdir(parents=True,exist_ok=True)
    if a.mode=="prepare":prepare(a,rows,previous)
    else:
        if a.native is None:raise RuntimeError("missing native MIXHTST output")
        compare(a,rows)
if __name__=="__main__":main()
