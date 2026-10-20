#!/usr/bin/env python3
"""Independent original CALMET TERSET/FRADJ on genuine Huoshan 1SS/1US input.

This compares only the selected FRADJ **kernel** on C++ supplied G19/G20/G21
source stage input, never independent original SURFVAR/PREPDI/CGAMMA/45 fields.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys
import tempfile

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import compare_g11_original_terrain_10km as g11
import compare_g21_file_backed_original_fradj as prior

NX=100
NY=100
NZ=9
CELL=NX*NY
TOLERANCE=2e-4  # pre-existing independent G11 vendor TERSET+FRADJ tolerance

def validate_stage(path: Path) -> dict:
    if path.is_symlink() or not path.is_file():
        raise ValueError("true G21 original stage source missing")
    with path.open() as f:
        header=f.readline().split()
        heights=f.readline().split()
        if len(header)!=9 or len(heights)!=10:
            raise ValueError("G21 original selected scalars/ZFACE absent")
        dims=list(map(int,header[:3]))
        dx,dy,terrad,critfn,t0=map(float,header[3:8])
        mode=int(header[8])
        if (dims != [NX,NY,NZ] or dx!=100.0 or dy!=100.0 or
            mode!=-1 or not all(math.isfinite(x) for x in (terrad,critfn,t0)) or
            terrad<0 or critfn<0 or not 180<=t0<=350):
            raise ValueError("G21 genuine UTM100m control mismatch")
        zface=list(map(float,heights))
        if any(not math.isfinite(v) for v in zface) or any(
                b<=a for a,b in zip(zface,zface[1:])):
            raise ValueError("G21 selected height grid unsupported")
        for i in range(CELL):
            row=f.readline().split()
            if len(row)!=3:
                raise ValueError("G21 source terrain/gamma/temp row absent")
            vals=list(map(float,row))
            if not all(math.isfinite(v) for v in vals) or not 180<=vals[2]<=350:
                raise ValueError("G21 original temperature/terrain/gamma nonfinite")
        wind=[]
        for i in range(CELL*NZ):
            row=f.readline().split()
            if len(row)!=2:
                raise ValueError("G21 original WIND1 source row absent")
            vals=tuple(map(float,row))
            if not all(math.isfinite(v) for v in vals):
                raise ValueError("G21 WIND1 source wind nonfinite")
            wind.append(vals)
        if f.readline():
            raise ValueError("G21 source stage contains trailing data")
    h=hashlib.sha256(path.read_bytes()).hexdigest()
    return {"terrad_km":terrad,"critfn":critfn,"wind":wind,"source_stage_sha256":h}

def parse_native(path:Path)->dict:
    if path.is_symlink() or not path.is_file():
        raise ValueError("real native source FRADJ not produced")
    out={}
    with path.open() as f:
        head=f.readline().strip()
        if head!="hour_end_utc_seconds,k_1based,j_1based,i_1based,u_mps_real4,v_mps_real4":
            raise ValueError("G21 actual FRADJ CSV header mismatch")
        hour=None
        for row in f:
            fields=row.strip().split(",")
            if len(fields)!=6:
                raise ValueError("G21 FRADJ data row malformed")
            t,k,j,i=map(int,fields[:4])
            if not(1<=i<=NX and 1<=j<=NY and 1<=k<=NZ):
                raise ValueError("G21 FRADJ grid index beyond real new site")
            if hour is None:hour=t
            if t!=hour: raise ValueError("G21 native contains mixed model hours")
            uv=tuple(map(float,fields[4:]))
            if not all(map(math.isfinite,uv)):
                raise ValueError("G21 native U/V nonfinite")
            key=(i,j,k)
            if key in out:raise ValueError("G21 duplicated U/V field")
            out[key]=uv
    if len(out)!=CELL*NZ:
        raise ValueError("G21 native FRADJ 3-D field incomplete")
    return out

def calculate(original_calmet: Path,source:Path,candidate:Path)->dict:
    check=validate_stage(source)
    native=parse_native(candidate)
    vendor=original_calmet
    if vendor.is_symlink() or not vendor.is_file():
        raise ValueError("S4 original CALMET source missing")
    # Reuse existing G11 independently source-extracted vendored code,
    # including original git-blob SHA guard and unmodified TERSET/FRADJ.
    g11.CALMET=vendor
    g11.VENDOR=vendor.parent
    template=prior.DRIVER
    if template.count("if(nr.ne.12.or.nc.ne.12.or.nlayer.ne.9)")!=1 or template.count(
        "dx.ne.10000..or.dy.ne.10000..or.mode.ne.-1")!=1:
        raise ValueError("original selected G21 Fortran harness changed")
    driver=template.replace(
        "if(nr.ne.12.or.nc.ne.12.or.nlayer.ne.9)",
        "if(nr.ne.100.or.nc.ne.100.or.nlayer.ne.9)",
    ).replace(
        "dx.ne.10000..or.dy.ne.10000..or.mode.ne.-1",
        "dx.ne.100..or.dy.ne.100..or.mode.ne.-1",
    )
    with tempfile.TemporaryDirectory(prefix="s4-p6b2-huoshan-fortran-") as d:
        root=Path(d)
        chunks,sha=g11.original_chunks(root)
        original_driver=root/"huoshan_original_terset_fradj.for"
        original_driver.write_text(driver)
        (root/"g21_original_stage.dat").write_bytes(source.read_bytes())
        exe=root/"vendor"
        subprocess.run(["gfortran","-O0","-std=legacy","-fno-automatic",
                        "-ffixed-line-length-none","-I"+str(vendor.parent),
                        str(chunks[0]),str(chunks[1]),str(original_driver),
                        "-o",str(exe)],check=True,capture_output=True,text=True)
        original=subprocess.run([str(exe)],cwd=root,check=True,capture_output=True,text=True)
    original_uv={}
    for line in original.stdout.splitlines():
        row=line.strip().split()
        if not row or row[0]!="GRID":continue
        if len(row)!=6:raise ValueError("original Fortran G21 grid row malformed")
        key=tuple(map(int,row[1:4]))
        uv=tuple(float(x.replace("D","E")) for x in row[4:])
        if key in original_uv or not all(map(math.isfinite,uv)):
            raise ValueError("original TERSET/FRADJ duplicated or nonfinite")
        original_uv[key]=uv
    if native.keys()!=original_uv.keys():
        raise ValueError("true 100x100 original/native FRADJ domain mismatch")
    first=check["wind"]
    bad=0
    worst=0.
    modified=0
    sample=[]
    for k in range(1,NZ+1):
        for j in range(1,NY+1):
            for i in range(1,NX+1):
                idx=(k-1)*CELL+(j-1)*NX+(i-1)
                for comp,base,cpp,ref in zip(("U","V"),first[idx],native[i,j,k],original_uv[i,j,k]):
                    diff=abs(cpp-ref)
                    worst=max(worst,diff)
                    if abs(cpp-base)>1e-5:modified+=1
                    if diff>TOLERANCE:
                        bad+=1
                        if len(sample)<10:
                            sample.append({"ijk":[i,j,k],"component":comp,
                                           "cpp":cpp,"vendor":ref,"delta":diff})
    return {
      "status":"S4_P6B2_REAL_HUOSHAN_ORIGINAL_FRADJ_KERNEL_PASS_SCOPED" if not bad
        else "S4_P6B2_REAL_HUOSHAN_ORIGINAL_FRADJ_KERNEL_MISMATCH",
      "grid":{"nx":NX,"ny":NY,"nz":NZ},
      "original_vendor_calmet_for_sha256":sha,
      "same_real_stage_sha256":check["source_stage_sha256"],
      "candidate_cpp_sha256":hashlib.sha256(candidate.read_bytes()).hexdigest(),
      "original_terrad_km":check["terrad_km"],"original_critfn":check["critfn"],
      "original_vendor_tolerance_mps":TOLERANCE,
      "source_wind1_grid_levels":CELL*NZ,
      "compared_uv_values":2*CELL*NZ,
      "max_abs_delta_mps":worst,
      "failures_over_tolerance":bad,
      "modified_uv_components_after_fradj":modified,
      "first_mismatches":sample,
      "actual_original_fortran_upstream_SIMILT_PREPDI_SURFVAR_CGAMMA":False,
      "original_full_CALMET_45_fields":False,
      "S4_P6_NEW_SITE_SCIENCE":"NOT_ACCEPTED",
    }

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--vendor-calmet-for",type=Path,required=True)
    ap.add_argument("--source-stage",type=Path,required=True)
    ap.add_argument("--candidate",type=Path,required=True)
    ap.add_argument("--out",type=Path,required=True)
    args=ap.parse_args()
    try:
        result=calculate(args.vendor_calmet_for,args.source_stage,args.candidate)
        if args.out.exists():raise ValueError("FRADJ original audit output must be new")
        args.out.parent.mkdir(parents=True,exist_ok=True)
        args.out.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
        print(json.dumps({"status":result["status"],"compared":result["compared_uv_values"],
                          "bad":result["failures_over_tolerance"],
                          "max_delta":result["max_abs_delta_mps"],
                          "nonidentity":result["modified_uv_components_after_fradj"]}))
        return 0 if not result["failures_over_tolerance"] else 2
    except (ValueError,OSError,subprocess.CalledProcessError) as exc:
        print(json.dumps({"status":"S4_P6B2_ORIGINAL_FRADJ_FAILED_CLOSED",
                          "reason":str(exc)[:1000]}),file=sys.stderr)
        return 2

if __name__=="__main__":
    raise SystemExit(main())
