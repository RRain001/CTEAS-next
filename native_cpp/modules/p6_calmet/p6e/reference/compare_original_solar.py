#!/usr/bin/env python3
"""P6E E1: literal unmodified CALMET 6.5.0 SOLAR vs independent C++20."""
import argparse
import hashlib
import json
import math
import subprocess
import tempfile
from pathlib import Path

BLOB="437f43bb7f0e51a1919e56664663e1a046986ed0"
TOL=3e-6
N=6*3*6*26
DRIVER="""      program original_solar_driver
      include 'params.met'
      include 'grid.met'
      real sinalp(mxnx,mxny,26),lats(6),lons(6)
      integer days(6),zones(3),iday,iz,n,i,j,k,h
      data lats/31.91,31.94,31.97,0.0,-31.94,66.6/
      data lons/117.11,117.14,117.17,0.0,-120.0,90.0/
      data days/1,80,172,266,355,366/
      data zones/-8,0,8/
      nx=3
      ny=2
      do j=1,ny
        do i=1,nx
          k=(j-1)*nx+i
          xlat(i,j)=lats(k)
          xlon(i,j)=lons(k)
        enddo
      enddo
      n=0
      do iday=1,6
        do iz=1,3
          n=n+1
          call solar(days(iday),zones(iz),sinalp)
          do h=1,26
            do j=1,ny
              do i=1,nx
                write(*,'(4(I4,1X),ES20.11E3)')
     1             n,i,j,h,sinalp(i,j,h)
              enddo
            enddo
          enddo
        enddo
      enddo
      end
"""
PARAMS="""      integer mxnx,mxny
      parameter(mxnx=3,mxny=2)
"""
GRID="""      integer nx,ny
      real xlat(mxnx,mxny),xlon(mxnx,mxny)
      common /p6e_grid/ nx,ny,xlat,xlon
"""
def run(*args):
    r=subprocess.run([str(a) for a in args],capture_output=True,text=True,check=True)
    return r.stdout
def source_slice(src):
    lines=src.splitlines(keepends=True)
    a=[i for i,v in enumerate(lines) if v.lower().startswith("      subroutine solar(")]
    b=[i for i,v in enumerate(lines) if v.lower().startswith("      subroutine stheor(")]
    if len(a)!=1 or len(b)!=1 or not 80<=b[0]-a[0]<=200 or a[0]>=b[0]:
        raise RuntimeError("CALMET source SOLAR bounds changed")
    return "".join(lines[a[0]:b[0]]),[a[0]+1,b[0]]
def parse(data):
    rows=[]
    for line in data.splitlines():
        parts=line.split()
        if len(parts)!=5:raise ValueError("SOLAR row shape")
        keys=tuple(int(x) for x in parts[:4])
        val=float(parts[4].replace("D","E"))
        if not math.isfinite(val) or abs(val)>1.000001:
            raise ValueError("invalid sine elevation")
        rows.append((keys,val))
    if len(rows)!=N:raise ValueError("SOLAR expected 2808 records, got "+str(len(rows)))
    return rows
def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--vendor",type=Path,required=True)
    ap.add_argument("--cpp",type=Path,required=True)
    ap.add_argument("--out",type=Path,required=True)
    opts=ap.parse_args()
    raw=opts.vendor.read_bytes()
    sha=run("git","hash-object",opts.vendor).strip()
    if sha!=BLOB: raise ValueError("CALMET vendor blob changed: "+sha)
    isolated,loc=source_slice(raw.decode("utf-8"))
    with tempfile.TemporaryDirectory(prefix="p6e-solar-original-") as folder:
        d=Path(folder)
        for name,s in (("params.met",PARAMS),("grid.met",GRID),
                       ("solar_original.for",isolated),("driver.for",DRIVER)):
            (d/name).write_text(s)
        run("gfortran","-O0","-std=legacy","-fno-automatic",
            "-ffixed-line-length-none","-I"+str(d),
            d/"solar_original.for",d/"driver.for","-o",d/"original_solar")
        ref=parse(run(d/"original_solar"))
    cpp=parse(run(opts.cpp))
    mismatches=[];max_delta=0.0
    for (key1,r),(key2,c) in zip(ref,cpp):
        if key1!=key2:raise RuntimeError("SOLAR index/time permutation")
        delta=abs(r-c);max_delta=max(max_delta,delta)
        if delta>TOL and len(mismatches)<20:
            mismatches.append({"location":key1,"fortran":r,"cpp":c,"difference":delta})
    status="PASS" if not mismatches else "FAIL"
    report={"status":status,"compared":N,"max_abs_sine_error":max_delta,
            "frozen_abs_tolerance":TOL,"vendor_git_blob":sha,
            "vendor_sha256":hashlib.sha256(raw).hexdigest(),
            "unmodified_solar_lines":loc,"first_mismatches":mismatches,
            "scope":"isolated original SOLAR only; complete P6E remains blocked"}
    opts.out.parent.mkdir(parents=True,exist_ok=True)
    opts.out.write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps(report,indent=2))
    if status!="PASS":raise SystemExit(1)
if __name__=="__main__":main()
