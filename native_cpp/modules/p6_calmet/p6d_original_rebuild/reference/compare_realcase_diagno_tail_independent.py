#!/usr/bin/env python3
"""Actual-hour black-box differential of independent DIAGNO tail vs old P6D.

Both receive IDENTICAL pre-tail INTER2 U/V from the frozen Hefei 2022 P6D
fixture. This determines whether the previously developed CTEAS tail differs
from an independent direct port of the immutable CALMET source. It does not
claim either input blend or final field matches original CALMET.DAT.
"""
from __future__ import annotations
import argparse
import csv
import json
import math
import re
import struct
import subprocess
import sys
from pathlib import Path

PLANE = 2500
LAYERS = 9
TOL = 2e-4


def controls(deck: str, key: str) -> list[float]:
    m=re.findall(rf"!\s*{re.escape(key)}\s*=\s*([^!]*)!",deck,re.I)
    if len(m)!=1:
        raise RuntimeError(f"original met.inp has ambiguous/missing {key}")
    values=[v for v in re.split(r"[,\s]+",m[0].strip()) if v]
    out=[float(v.replace("D","E").replace("d","e")) for v in values]
    if not all(math.isfinite(v) for v in out):raise RuntimeError("nonfinite control")
    return out


def floats(path: Path, count: int) -> list[float]:
    data=path.read_bytes()
    if len(data)!=4*count:
        raise RuntimeError(f"wrong float32 length {path}: {len(data)} != {4*count}")
    out=[n[0] for n in struct.iter_unpack("<f",data)]
    if not all(map(math.isfinite,out)):
        raise RuntimeError(f"nonfinite original stage field: {path}")
    return out


def main() -> None:
    parser=argparse.ArgumentParser()
    parser.add_argument("--vendor",required=True,type=Path)
    parser.add_argument("--fortran",default="gfortran")
    parser.add_argument("--case",required=True,type=Path)
    parser.add_argument("--p6d-fields",required=True,type=Path)
    parser.add_argument("--cpp",required=True,type=Path)
    parser.add_argument("--out",required=True,type=Path)
    args=parser.parse_args()
    args.out.mkdir(parents=True,exist_ok=True)
    labels=(args.p6d_fields/"produced_hours.txt").read_text().splitlines()
    if len(labels)!=1:raise RuntimeError("only one real-case hour is supported")
    hour=labels[0].strip()
    deck=(args.case/"run/met/met.inp").read_text()
    z=controls(deck,"ZFACE")
    passes=controls(deck,"NSMTH")
    if len(z)!=10 or len(passes)!=9 or any(int(x)!=x for x in passes):
        raise RuntimeError("wrong original CALMET nine-layer control")
    dz=[z[k+1]-z[k] for k in range(LAYERS)]
    def load(prefix: str,count: int=PLANE*LAYERS) -> list[float]:
        return floats(args.p6d_fields/f"{prefix}_{hour}.f32",count)
    u=load("inter2_u")
    v=load("inter2_v")
    old_u=load("blend_u")
    old_v=load("blend_v")
    old_w=load("w_face",PLANE*(LAYERS+1))
    ub=[];vb=[]
    for k in range(LAYERS):
        for side in (0,1):
            ix=0 if side==0 else 49
            for j in range(50):
                ub.append(u[k*PLANE+j*50+ix])
    for k in range(LAYERS):
        for side in (0,1):
            row=0 if side==0 else 49
            for i in range(50):
                vb.append(v[k*PLANE+row*50+i])
    fixture=args.out/"original_real_hour_diagno_tail.input"
    with fixture.open("w") as f:
        f.write(" ".join(f"{x:.9g}" for x in dz)+"\n")
        f.write(" ".join(str(int(x)) for x in passes)+"\n")
        for values,width in ((u,50),(v,50),(ub,50),(vb,50)):
            for start in range(0,len(values),width):
                f.write(" ".join(f"{x:.9g}" for x in values[start:start+width])+"\n")
    csv_path=args.out/"independent_diagno_tail.csv"
    bounds=args.out/"independent_diagno_tail.bound"
    proc=subprocess.run([str(args.cpp),str(fixture),str(csv_path),str(bounds)],
        capture_output=True,text=True,timeout=120)
    if proc.returncode:
        raise RuntimeError(f"independent DIAGNO C++ exited {proc.returncode}: {proc.stderr}")
    worst={"u":0.0,"v":0.0,"w_below":0.0,"w_above":0.0}
    mismatch=[]
    with csv_path.open(newline="") as f:
        rows=csv.DictReader(f)
        count=0
        for count,row in enumerate(rows,1):
            n=count-1
            k=n//PLANE
            ij=n%PLANE
            i=ij%50;j=ij//50
            if (int(row["i"]),int(row["j"]),int(row["k"]))!=(i+1,j+1,k+1):
                raise RuntimeError(f"wrong independent DIAGNO row ordering {n}")
            ref={"u":old_u[n],"v":old_v[n],
                 "w_below":old_w[n],"w_above":old_w[n+PLANE]}
            for key,value in ref.items():
                modern=float(row[key])
                if not math.isfinite(modern):raise RuntimeError("nonfinite rebuilt field")
                error=abs(modern-value)
                worst[key]=max(worst[key],error)
                if error>TOL and len(mismatch)<30:
                    mismatch.append({"field":key,"i":i+1,"j":j+1,"k":k+1,
                                     "old":value,"independent":modern,
                                     "absolute_error":error})
        if count!=PLANE*LAYERS:
            raise RuntimeError("missing DIAGNO source rows")
    # Independent actual-hour reference: compile the untouched original
    # SMOOTH/DIVCEL/WINDBC routines plus the verbatim DIAGNO L6119-6148
    # call segment. Both versions receive EXACTLY this same real-case
    # INTER2 pre-tail field and prespecified synthetic boundary snapshot.
    # Comparison with old P6D is diagnostic evidence, never a substitute
    # for the direct original-vs-new Fortran oracle.
    sys.path.insert(0,str(Path(__file__).resolve().parents[2]/"reference"))
    import compare_original_diagno_final_segment as original
    chunks,block,original_provenance=original.original_source(args.vendor,args.out)
    fortran_driver=args.out/"real_hour_original_diagno_source.for"
    fortran_driver.write_text(original.DRIVER_HEAD+block+original.DRIVER_TAIL)
    fortran_bin=args.out/"real_hour_original_diagno_source"
    original.run([args.fortran,"-O0","-std=legacy","-fno-automatic",
                  "-ffixed-line-length-none","-I"+str(args.vendor),
                  *[name for name,_ in chunks],fortran_driver,"-o",fortran_bin])
    fortran_wind=args.out/"real_hour_original_diagno_wind.txt"
    fortran_boundary=args.out/"real_hour_original_diagno_boundary.txt"
    original.run([fortran_bin,fixture,fortran_wind,fortran_boundary])
    strict=original.compare(fortran_wind,csv_path,fortran_boundary,bounds)
    old_worst={"u":0.,"v":0.,"w_below":0.,"w_above":0.}
    old_first=[]
    with fortran_wind.open() as reference:
        for n,line in enumerate(reference):
            tokens=line.split()
            if len(tokens)!=8 or n>=PLANE*LAYERS:
                raise RuntimeError("original source output shape/index error")
            kk=n//PLANE+1
            ii=n%50+1
            jj=(n//50)%50+1
            if tuple(map(int,tokens[:3]))!=(ii,jj,kk):
                raise RuntimeError("original source cell index drift")
            expected={"u":float(tokens[3]),"v":float(tokens[4]),
                      "w_below":float(tokens[6]),"w_above":float(tokens[7])}
            old={"u":old_u[n],"v":old_v[n],
                 "w_below":old_w[n],"w_above":old_w[n+PLANE]}
            for key in expected:
                diff=abs(expected[key]-old[key])
                old_worst[key]=max(old_worst[key],diff)
                if diff>TOL and len(old_first)<20:
                    old_first.append({"field":key,"i":ii,"j":jj,"k":kk,
                                      "original":expected[key],"old":old[key],
                                      "absolute_error":diff})
    oracle_pass=strict["status"]=="PASS"
    result={"status":"PASS_REAL_HOUR_ORIGINAL_SOURCE_DIAGNO_TAIL" if oracle_pass else "FAIL",
            "hour":hour,"grid":[50,50,9],"wind_abs_tol_mps":TOL,
            "stage_input":"same old CTEAS real-case pre-tail INTER2 U/V",
            "source_covered":"SMOOTH+DIVCEL+W+WINDBC from unmodified CALMET",
            "original_fortran_blob_sha":original_provenance["git_blob"],
            "original_source_vs_independent":strict,
            "original_source_vs_old_diagnostic":{
                "status":"PASS" if not old_first else "FAIL",
                "max_abs_error_mps":old_worst,"first_mismatches":old_first},
            "new_vs_old_diagnostic_status":"PASS" if not mismatch else "FAIL",
            "max_abs_error_mps":worst,"first_mismatches":mismatch,
            "scientific_limit":"Not an original CALMET.DAT final-field parity claim. "
                               "MIXHTST/EL/ZI/PREPDI stages are upstream and untested here."}
    (args.out/"first_hour_diagno_independent_vs_old.json").write_text(
        json.dumps(result,indent=2)+"\n")
    print(json.dumps(result,indent=2))
    if not oracle_pass:raise SystemExit(1)


if __name__=="__main__":
    main()
