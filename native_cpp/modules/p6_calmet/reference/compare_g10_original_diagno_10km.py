#!/usr/bin/env python3
"""G10 independent original CALMET DIAGNO tail U/V/DIV/W/boundary reference.

Runs literal original calmet.for L6119-6148 and the original unchanged
SMOOTH, DIVCEL, WINDBC subroutines on a 10 km, 12x12x9 test domain.
Uses the existing 50x50 source-verified script only for source extraction
and synthetic input *construction*; never uses its canned acceptance result.
Scope is selected IOBR=0/no-lake-breeze tail with controlled upstream inputs,
NOT real multi-station CALMET terrain/heat/FRADJ/SLOPE parity.
"""
from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import math
import subprocess
import tempfile
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
VENDOR=ROOT/"engine/vendor/src/CALMET_v6.5.0_L150223"
OLD=HERE/"compare_original_diagno_final_segment.py"
NX=NY=12
NZ=9
N=NX*NY
TOL_WIND=2e-4
TOL_DIV=1e-6


def source_reference():
    spec=importlib.util.spec_from_file_location("g10_original_diagno_reference",OLD)
    if spec is None or spec.loader is None:
        raise RuntimeError("frozen DIAGNO original script unavailable")
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def check_rows(original: Path,native: Path,before: Path,native_bound: Path):
    f=[line.split() for line in original.read_text().splitlines()]
    with native.open(newline="") as csv_file:
        c=list(csv.DictReader(csv_file))
    if len(f)!=N*NZ or len(c)!=N*NZ:
        raise ValueError("G10 mismatched 12x12x9 field size")
    errors={"u":0.,"v":0.,"div":0.,"w_below":0.,"w_above":0.}
    failures=[]
    nonzero=0
    for n,(ff,cc) in enumerate(zip(f,c)):
        key=(n%NX+1,(n//NX)%NY+1,n//N+1)
        if len(ff)!=8 or tuple(map(int,ff[:3]))!=key or (
            int(cc["i"]),int(cc["j"]),int(cc["k"]))!=key:
            raise ValueError("G10 U/V/W grid index/order mismatch")
        for field,index in (("u",3),("v",4),("div",5),("w_below",6),("w_above",7)):
            a,b=float(ff[index]),float(cc[field])
            if not math.isfinite(a) or not math.isfinite(b):
                raise ValueError("G10 nonfinite source or native field")
            difference=abs(a-b)
            errors[field]=max(errors[field],difference)
            if difference>(TOL_DIV if field=="div" else TOL_WIND):
                failures.append((key,field,difference))
        if abs(float(ff[7]))>1e-7:nonzero+=1
    fa=[line.split() for line in before.read_text().splitlines()]
    ca=[line.split() for line in native_bound.read_text().splitlines()]
    if len(fa)!=4*NX*NZ or len(ca)!=4*NX*NZ:
        raise ValueError("G10 12x12x9 boundary count mismatch")
    boundary=0.
    for row,(a,b) in enumerate(zip(fa,ca)):
        if len(a)!=5 or len(b)!=5 or a[:4]!=b[:4]:
            raise ValueError(f"G10 boundary identity mismatch {row}")
        diff=abs(float(a[4])-float(b[4]))
        boundary=max(boundary,diff)
        if diff>TOL_WIND:failures.append(("boundary",row,diff))
    if failures:
        raise AssertionError(f"G10 source-vendor DIAGNO tail mismatch: {failures[:7]}; max={errors}, boundary={boundary}")
    return dict(cells=N*NZ,uv_div_w_values=5*N*NZ,boundary_values=len(fa),
                nonzero_w=nonzero,max_abs=errors,max_boundary=boundary)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--mode",choices=("Debug","Release"),required=True)
    parser.add_argument("--cpp",type=Path,required=True)
    args=parser.parse_args()
    module=source_reference()
    module.NX=module.NY=NX
    module.N=N
    # Preserve verbatim original Fortran numerical tail and full subroutines.
    # Only spatial constants and horizontal dx/dy of the standalone driver differ.
    head=(module.DRIVER_HEAD
          .replace("nx=50","nx=12").replace("ny=50","ny=12")
          .replace("dx=100.","dx=10000.").replace("dy=100.","dy=10000."))
    with tempfile.TemporaryDirectory(prefix="p6g-g10-diagno-") as folder:
        work=Path(folder)
        originals,block,metadata=module.original_source(VENDOR,work)
        driver=work/"g10_original_diagno_12x12.for"
        driver.write_text(head+block+module.DRIVER_TAIL)
        exe=work/"original_diagno_10km"
        opt="-O0" if args.mode=="Debug" else "-O2"
        module.run(["gfortran",opt,"-std=legacy","-fno-automatic",
                    "-ffixed-line-length-none","-I"+str(VENDOR),
                    *[p for p,_ in originals],driver,"-o",exe])
        results={}
        for name,passes,fields in module.cases():
            infile=work/(name+".input")
            with infile.open("w") as f:
                f.write(" ".join(f"{z:.9f}" for z in module.DZ)+"\n")
                f.write(" ".join(map(str,passes))+"\n")
                for array,width in zip(fields,(NX,NX,NY,NX)):
                    for i in range(0,len(array),width):
                        f.write(" ".join(f"{v:.9f}" for v in array[i:i+width])+"\n")
            original_out=work/(name+".fortran")
            cpp_out=work/(name+".native.csv")
            original_boundary=work/(name+".original.bound")
            cpp_boundary=work/(name+".native.bound")
            module.run([exe,infile,original_out,original_boundary])
            module.run([args.cpp,infile,cpp_out,cpp_boundary])
            results[name]=check_rows(
                original_out,cpp_out,original_boundary,cpp_boundary)
        if results["calm_zero"]["nonzero_w"]!=0:
            raise AssertionError("G10 original calm baseline generated vertical wind")
        for case in ("flat_nonzero_divergence","layer_selective_smooth",
                     "rough_winds_and_boundaries"):
            if results[case]["nonzero_w"]==0:
                raise AssertionError("G10 original had no nonzero W in "+case)
        report={"status":"PASS_G10_SELECTED_12X12_10KM_ORIGINAL_DIAGNO_TAIL",
                "compiler_mode":args.mode,"nx":NX,"ny":NY,"nz":NZ,
                "spacing_m":10000,"original_source":metadata,
                "cases":results,"full_calmet_physics_accepted":False}
        print(json.dumps(report,ensure_ascii=False))
if __name__=="__main__":
    main()
