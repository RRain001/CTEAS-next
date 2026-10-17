#!/usr/bin/env python3
"""Source-authentic selected-hour CALMET P6D U/V/W and SLOPE increment probe.

The six-hour binary is tracked verbatim from the write-only-instrumented
unmodified CALMET v6.5.0 source. This probe DOES NOT relax 143h acceptance.
No oracle value is fed to the C++ producer.
"""
from __future__ import annotations
import argparse
import datetime as dt
import hashlib
import json
import math
import struct
from pathlib import Path

SAMPLE_HOURS = (1, 2, 3, 81, 82, 83)
SOURCE_SHA = "972af841552f7a0eda6b02b221b6b2a808c61806054e634c617425d9ca9babdf"
NX = NY = 50
NZ = 9
GRID = NX * NY
VOLUME = NZ * GRID
FACES = (NZ + 1) * GRID
SCALARS = {7: (VOLUME, VOLUME), 8: (VOLUME, VOLUME),
           9: (VOLUME, VOLUME), 10: (VOLUME, FACES, VOLUME, VOLUME)}
# Diagnostic tolerances are specified before the comparisons, and may not
# silently override the frozen P6G 143h acceptance conditions.
TOLERANCES = {"slope_u": (2e-4, 0.0), "slope_v": (2e-4, 0.0),
              "u": (1e-4, 1e-5), "v": (1e-4, 1e-5),
              "w": (1e-5, 1e-5)}

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def read_source(path):
    if sha(path) != SOURCE_SHA:
        raise RuntimeError("pinned unmodified original CALMET six-hour dump has drifted")
    raw=path.read_bytes()
    off=0
    samples={}
    for h in SAMPLE_HOURS:
        group={}
        expected_clock=dt.datetime(2022,1,1)+dt.timedelta(hours=h-1)
        packed=expected_clock.year*100000+expected_clock.timetuple().tm_yday*100+expected_clock.hour
        for kpt in (7,8,9,10):
            if off+32>len(raw):raise RuntimeError("source record truncated")
            k,time,second,i0,j0,nx,ny,nz=struct.unpack_from("<8i",raw,off)
            if (k,time,second,i0,j0,nx,ny,nz)!=(kpt,packed,0,0,0,NX,NY,NZ):
                raise RuntimeError(f"source insertion/time/layout mismatch at {h}:{kpt}: {k,time,second,i0,j0,nx,ny,nz}")
            off+=32
            arrays=[]
            for size in SCALARS[kpt]:
                bytes_required=4*size
                if off+bytes_required>len(raw):raise RuntimeError("source payload truncated")
                v=struct.unpack_from(f"<{size}f",raw,off)
                if not all(math.isfinite(x) for x in v):raise RuntimeError("source values not finite")
                arrays.append(v)
                off+=bytes_required
            group[kpt]=arrays
        samples[h]=group
    if off!=len(raw):raise RuntimeError("source stream contains unexpected records")
    return samples

def read_candidate(path, count):
    if not path.is_file():raise RuntimeError(f"missing native candidate: {path}")
    raw=path.read_bytes()
    if len(raw)!=4*count:raise RuntimeError(f"candidate shape incorrect: {path}")
    v=struct.unpack(f"<{count}f",raw)
    if not all(math.isfinite(x) and abs(x)<999998 for x in v):
        raise RuntimeError(f"candidate has missing/nonfinite values: {path}")
    return v

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--source",type=Path,required=True)
    p.add_argument("--candidate",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    p.add_argument("--enforce-acceptance",action="store_true")
    a=p.parse_args()
    original=read_source(a.source)
    result={"status":"SOURCE_LOCKED_SIX_HOUR_DIAGNOSIS",
            "scientific_verdict":"NOT_ASSESSED","hours":list(SAMPLE_HOURS),
            "source_sha256":SOURCE_SHA,
            "no_original_oracle_injected":True,
            "reference":"unaltered CALMET DIAGNO DGM stage 7/8/9/10",
            "tolerances":TOLERANCES,"fields":{}}
    for name in TOLERANCES:
        result["fields"][name]={"count":0,"exceedances":0,"max_abs":0.,
                                "sum_sq":0.,"worst":None,"by_level":{}}
    for h in SAMPLE_HOURS:
        clock=dt.datetime(2022,1,1)+dt.timedelta(hours=h)
        label=clock.strftime("%Y-%m-%d_%H")
        source=original[h]
        u1=read_candidate(a.candidate/f"wind1_u_{label}.f32",VOLUME)
        v1=read_candidate(a.candidate/f"wind1_v_{label}.f32",VOLUME)
        uc=read_candidate(a.candidate/f"slope_corrected_u_{label}.f32",VOLUME)
        vc=read_candidate(a.candidate/f"slope_corrected_v_{label}.f32",VOLUME)
        final_u=read_candidate(a.candidate/f"blend_u_{label}.f32",VOLUME)
        final_v=read_candidate(a.candidate/f"blend_v_{label}.f32",VOLUME)
        final_w=read_candidate(a.candidate/f"w_face_{label}.f32",FACES)
        source_fields={
            "slope_u": tuple(x-y for x,y in zip(source[9][0],source[8][0])),
            "slope_v": tuple(x-y for x,y in zip(source[9][1],source[8][1])),
            "u":source[10][2],"v":source[10][3],"w":source[10][1]}
        native_fields={
            "slope_u":tuple(x-y for x,y in zip(uc,u1)),
            "slope_v":tuple(x-y for x,y in zip(vc,v1)),
            "u":final_u,"v":final_v,"w":final_w}
        for name,(abs_tol,rel_tol) in TOLERANCES.items():
            st=result["fields"][name]
            for idx,(ref,got) in enumerate(zip(source_fields[name],native_fields[name])):
                delta=abs(ref-got)
                level=idx//GRID+1
                st["count"]+=1
                st["sum_sq"]+=delta*delta
                if delta>abs_tol+rel_tol*abs(ref):
                    st["exceedances"]+=1
                    st["by_level"][str(level)]=st["by_level"].get(str(level),0)+1
                if delta>st["max_abs"]:
                    st["max_abs"]=delta
                    st["worst"]={"hour_end":label,"level":level,
                                 "i":idx%NX+1,"j":idx//NX%NY+1,
                                 "original":ref,"native":got,"error":delta}
    for name,st in result["fields"].items():
        expected=6*(FACES if name=="w" else VOLUME)
        if st["count"]!=expected:raise RuntimeError(f"incomplete {name} coverage")
        st["rms"]=math.sqrt(st.pop("sum_sq")/st["count"])
    result["scientific_verdict"]=("PASS_SIX_SELECTED_HOUR_UVW" if
        all(result["fields"][x]["exceedances"]==0 for x in ("u","v","w"))
        else "FAIL_SIX_SELECTED_HOUR_UVW")
    result["total_compared"]=sum(x["count"] for x in result["fields"].values())
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps({"scientific_verdict":result["scientific_verdict"],
                      "summary":{k:{"max_abs":v["max_abs"],"exceedances":v["exceedances"],
                                    "worst":v["worst"],"by_level":v["by_level"]}
                                for k,v in result["fields"].items()}},indent=2))
    if a.enforce_acceptance and result["scientific_verdict"]!="PASS_SIX_SELECTED_HOUR_UVW":
        raise SystemExit(1)

if __name__=="__main__":
    main()
