#!/usr/bin/env python3
"""Actual Huoshan NOAA one-SS/one-US G22 SLOPE original Fortran kernel oracle.

Independently compile original, unmodified CALMET 6.5 TERSET/SLOPE routines.
The standalone driver reads actual G22 after-ELUSTR QH, second-SURFVAR
TEMP2D and true preceding G21 FRADJ U/V. Upstream HEATFX/ELUSTR Fortran
parity and full CALMET G14/P6F are explicitly NOT accepted.
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
import compare_g22_file_backed_original_slope as g22

NX,NY,NZ=100,100,9
NC=NX*NY
TOL=2e-4  # unchanged G11 and G22 original-vendor selected SLOPE tolerance

def check_source(stage:Path):
    if stage.is_symlink() or not stage.is_file():
        raise ValueError("real G22 source-original stage absent/nonregular")
    with stage.open() as f:
        meta=f.readline().split()
        heights=f.readline().split()
        if len(meta)!=10 or len(heights)!=10:
            raise ValueError("G22 source stage lacks real controls and zface")
        ix,iy,iz=map(int,meta[:3])
        dx,dy,terrad,t0=map(float,meta[3:7])
        iw1,iw2,mode=map(int,meta[7:])
        if ((ix,iy,iz)!=(NX,NY,NZ) or (dx,dy)!=(100.,100.) or
            terrad<0 or iw1>iw2 or mode!=-1 or
            not all(math.isfinite(x) for x in (terrad,t0)) or not 180<=t0<=350):
            raise ValueError("G22 original 100m source control invalid")
        zface=list(map(float,heights))
        if not all(math.isfinite(x) for x in zface) or any(
            b<=a for a,b in zip(zface,zface[1:])):
            raise ValueError("G22 actual original zface invalid")
        qh_min=math.inf;qh_max=-math.inf
        for _ in range(NC):
            row=f.readline().split()
            if len(row)!=4:
                raise ValueError("G22 exact cell-specific topography/temperature/QH missing")
            z,t,q=map(float,row[:3]);land=int(row[3])
            if not all(math.isfinite(x) for x in (z,t,q)) or not 180<=t<=350:
                raise ValueError("G22 real input nonfinite or impossible T")
            if iw1<=land<=iw2:
                raise ValueError("G22 genuine all-land selected branch contains water")
            qh_min=min(qh_min,q);qh_max=max(qh_max,q)
        first=[]
        for _ in range(NC*NZ):
            row=f.readline().split()
            if len(row)!=2:
                raise ValueError("G22 authentic previous FRADJ U/V missing")
            uv=tuple(map(float,row))
            if not all(map(math.isfinite,uv)):
                raise ValueError("G22 nonfinite initial wind")
            first.append(uv)
        if f.readline():
            raise ValueError("G22 stage contains unscoped extra data")
    return {"sha256":hashlib.sha256(stage.read_bytes()).hexdigest(),
            "source_terrad_km":terrad,"qh_min_max_wm2":[qh_min,qh_max],
            "first_uv":first}

def native_rows(candidate:Path):
    if candidate.is_symlink() or not candidate.is_file():
        raise ValueError("G22 native 100x100 SLOPE CSV missing/nonregular")
    out={}
    with candidate.open() as f:
        header=f.readline().strip()
        if header!="hour_end_utc_seconds,k_1based,j_1based,i_1based,u_mps_real4,v_mps_real4":
            raise ValueError("G22 native original grid CSV header changed")
        hour=None
        for line in f:
            cols=line.strip().split(",")
            if len(cols)!=6:raise ValueError("G22 native U/V malformed")
            t,k,j,i=map(int,cols[:4])
            if not (1<=i<=NX and 1<=j<=NY and 1<=k<=NZ):
                raise ValueError("G22 native U/V index outside original case")
            if hour is None: hour=t
            elif t!=hour:raise ValueError("G22 native mixed clock")
            uv=tuple(map(float,cols[4:]))
            if not all(map(math.isfinite,uv)):
                raise ValueError("G22 native wind nonfinite")
            key=(i,j,k)
            if key in out:raise ValueError("G22 duplicate original grid cell")
            out[key]=uv
    if len(out)!=NC*NZ:
        raise ValueError("G22 actual native 3D source output incomplete")
    return out

def compare(vendor:Path,stage:Path,candidate:Path):
    source=check_source(stage)
    native=native_rows(candidate)
    if vendor.is_symlink() or not vendor.is_file():
        raise ValueError("original CALMET vendor source absent/nonregular")
    g11.CALMET=vendor
    g11.VENDOR=vendor.parent
    driver=g22.DRIVER
    before1="if(nr.ne.12.or.nc.ne.12.or.nl.ne.9) stop 91"
    before2="if(dx.ne.10000..or.dy.ne.10000..or.mode.ne.-1) stop 92"
    if driver.count(before1)!=1 or driver.count(before2)!=1:
        raise ValueError("original G22 independent Fortran driver changed")
    driver=driver.replace(before1,"if(nr.ne.100.or.nc.ne.100.or.nl.ne.9) stop 91").replace(
        before2,"if(dx.ne.100..or.dy.ne.100..or.mode.ne.-1) stop 92")
    with tempfile.TemporaryDirectory(prefix="s4-p6b2-original-slope-huoshan-") as d:
        root=Path(d)
        sources,vendor_sha=g11.original_chunks(root)
        driver_path=root/"real_huoshan_original_slope.for"
        driver_path.write_text(driver)
        (root/"g22_stage.dat").write_bytes(stage.read_bytes())
        original=root/"fortran"
        subprocess.run(["gfortran","-O0","-std=legacy","-fno-automatic",
                        "-ffixed-line-length-none","-I"+str(vendor.parent),
                        str(sources[0]),str(sources[2]),str(driver_path),
                        "-o",str(original)],check=True,capture_output=True,text=True)
        run=subprocess.run([str(original)],cwd=root,check=True,
                           text=True,capture_output=True)
    reference={}
    for line in run.stdout.splitlines():
        cols=line.strip().split()
        if not cols or cols[0]!="GRID":continue
        if len(cols)!=6:raise ValueError("G22 original vendor grid row malformed")
        key=tuple(map(int,cols[1:4]))
        uv=tuple(float(v.replace("D","E")) for v in cols[4:])
        if key in reference or not all(map(math.isfinite,uv)):
            raise ValueError("G22 original Fortran output missing/duplicate")
        reference[key]=uv
    if reference.keys()!=native.keys():
        raise ValueError("G22 original selected Fortran and native grid domain differ")
    worst=0.;bad=0;modified=0;samples=[]
    for k in range(1,NZ+1):
        for j in range(1,NY+1):
            for i in range(1,NX+1):
                idx=(k-1)*NC+(j-1)*NX+(i-1)
                key=(i,j,k)
                for part,first,orig,cpp in zip(("U","V"),source["first_uv"][idx],
                                               reference[key],native[key]):
                    error=abs(cpp-orig)
                    worst=max(worst,error)
                    if abs(cpp-first)>1e-5:modified+=1
                    if error>TOL:
                        bad+=1
                        if len(samples)<10:
                            samples.append({"ijk":[i,j,k],"part":part,
                                            "cpp":cpp,"vendor":orig,"error":error})
    return {
        "status":("S4_P6B2B_HUOSHAN_ORIGINAL_SLOPE_KERNEL_PASS_SCOPED" if bad==0 else
                  "S4_P6B2B_HUOSHAN_ORIGINAL_SLOPE_KERNEL_MISMATCH"),
        "site":"REAL_HUOSHAN_2022_1SS_1US_100x100x9_FIRST_HOUR",
        "source_stage_sha256":source["sha256"],
        "native_output_sha256":hashlib.sha256(candidate.read_bytes()).hexdigest(),
        "vendor_original_calmet_for_sha256":vendor_sha,
        "source_terrad_km":source["source_terrad_km"],
        "source_qh_min_max_wm2":source["qh_min_max_wm2"],
        "original_tolerance_mps":TOL,
        "compared_uv_values":2*NC*NZ,
        "max_abs_uv_delta_mps":worst,
        "differences_exceeding_tolerance":bad,
        "genuine_modified_uv_components_after_slope":modified,
        "samples":samples,
        "independent_vendor_upstream_HEATFX_AIRDEN_ELUSTR":False,
        "independent_vendor_full_CALMET_45fields":False,
        "S4_P6_NEW_SITE_SCIENCE":"NOT_ACCEPTED",
        "Docker":"DEFERRED",
    }

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--vendor-calmet-for",type=Path,required=True)
    p.add_argument("--source-stage",type=Path,required=True)
    p.add_argument("--candidate",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    a=p.parse_args()
    try:
        result=compare(a.vendor_calmet_for,a.source_stage,a.candidate)
        if a.out.exists() or a.out.is_symlink():
            raise ValueError("S4 original SLOPE report must be fresh")
        a.out.parent.mkdir(parents=True,exist_ok=True)
        a.out.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
        print(json.dumps({"status":result["status"],"compared":result["compared_uv_values"],
                          "failures":result["differences_exceeding_tolerance"],
                          "max_abs":result["max_abs_uv_delta_mps"],
                          "modified":result["genuine_modified_uv_components_after_slope"]}))
        return 0 if not result["differences_exceeding_tolerance"] else 2
    except (OSError,ValueError,subprocess.CalledProcessError) as ex:
        print(json.dumps({"status":"S4_P6B2B_VENDOR_SLOPE_BLOCKED",
                          "reason":str(ex)[:1200]}),file=sys.stderr)
        return 2

if __name__=="__main__":
    raise SystemExit(main())
