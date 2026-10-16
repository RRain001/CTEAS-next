#!/usr/bin/env python3
"""Independent FRADJ REAL*4 numerical oracle, unmodified CALMET original.

Passes the IDENTICAL, source-defined topographic maxima (HMAX), terrain,
lapse, temperature, wind fields to original FRADJ and independent C++.
This avoids implicitly comparing two different TERSET implementations.
Fortran original blob is pinned; no production/legacy P6 physics imported.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
import math
import subprocess
from pathlib import Path

ORIGINAL_BLOB="437f43bb7f0e51a1919e56664663e1a046986ed0"
NX=NY=50
NZ=9
N=NX*NY
TOL=2e-4

ORIGINAL_DRIVER="""      program testoriginalfradj
      include 'params.met'
      include 'grid.met'
      include 'd6.met'
      real topo(mxnx,mxny),highest(mxnx,mxny)
      real gam(mxnx,mxny),sfct(mxnx,mxny)
      real u(mxnx,mxny,mxnz),v(mxnx,mxny,mxnz)
      real critfn,tinf
      character*256 fin,fout,arg
      call get_command_argument(1,fin)
      call get_command_argument(2,fout)
      call get_command_argument(3,arg)
      read(arg,*) isurft
      nx=50
      ny=50
      nz=9
      dx=100.
      dy=100.
      critfn=1.
      tinf=285.
      zface(1)=0.
      zface(2)=20.
      zface(3)=40.
      zface(4)=80.
      zface(5)=160.
      zface(6)=320.
      zface(7)=640.
      zface(8)=1200.
      zface(9)=2000.
      zface(10)=3000.
      do k=1,nz
        dz(k)=zface(k+1)-zface(k)
      enddo
      open(10,file=trim(fin),status='old')
      do j=1,ny
        read(10,*) (topo(i,j),i=1,nx)
      enddo
      do j=1,ny
        read(10,*) (highest(i,j),i=1,nx)
      enddo
      do j=1,ny
        read(10,*) (gam(i,j),i=1,nx)
      enddo
      do j=1,ny
        read(10,*) (sfct(i,j),i=1,nx)
      enddo
      do k=1,nz
        do j=1,ny
          read(10,*) (u(i,j,k),i=1,nx)
        enddo
      enddo
      do k=1,nz
        do j=1,ny
          read(10,*) (v(i,j,k),i=1,nx)
        enddo
      enddo
      close(10)
      call fradj(u,v,topo,gam,isurft,tinf,sfct,critfn,
     1           zface,highest)
      open(11,file=trim(fout),status='replace')
      do k=1,nz
        do j=1,ny
          do i=1,nx
            write(11,'(3(I4,1X),2(ES22.13E3,1X))')
     1          i,j,k,u(i,j,k),v(i,j,k)
          enddo
        enddo
      enddo
      close(11)
      end
"""


def checked(argv: list[object]) -> None:
    p=subprocess.run(list(map(str,argv)),capture_output=True,text=True,timeout=120)
    if p.returncode:
        raise RuntimeError(f"command failed {argv}: {p.returncode}: "
                           f"{p.stdout[-500:]} {p.stderr[-2000:]}")


def scenes():
    hill=[100.+120.*math.exp(-((i-25)**2+(j-24)**2)/130.)
          for j in range(NY) for i in range(NX)]
    ridge=[102.+60.*math.sin(i*.14)+18.*math.cos(j*.15)
           for j in range(NY) for i in range(NX)]
    cases=[
      ("flat_calm",[100.]*N,0.,0.,-1),
      ("hill_stable_weak",hill,1.0,.006,-1),
      ("ridge_stable_weak",ridge,1.0,.006,-1),
      ("ridge_unstable",ridge,1.0,-.022,-1),
      ("ridge_fast_wind",ridge,20.0,.006,-1),
      ("ridge_representative_tinf",ridge,1.0,.006,1),
    ]
    for name,terrain,speed,lapse,isurft in cases:
        # For this isolated comparison, HMAX is explicitly supplied.
        # It is not recomputed independently or claimed to equal TERSET.
        high=[max(terrain[p]+75.,max(terrain)+5.) for p in range(N)]
        gamma=[lapse]*N
        temp=[275.+2.*math.sin((p%NX)*.06) for p in range(N)]
        u=[0.]* (N*NZ)
        v=[0.]* (N*NZ)
        for k in range(NZ):
            for j in range(NY):
                for i in range(NX):
                    n=k*N+j*NX+i
                    u[n]=speed*(1.0+.05*math.sin(.11*j+.08*k))
                    v[n]=speed*(.5+.05*math.cos(.13*i-.05*k))
        yield name,(terrain,high,gamma,temp,u,v),isurft


def main() -> None:
    parser=argparse.ArgumentParser()
    parser.add_argument("--vendor",required=True,type=Path)
    parser.add_argument("--cpp",required=True,type=Path)
    parser.add_argument("--out",required=True,type=Path)
    parser.add_argument("--fortran",default="gfortran")
    args=parser.parse_args()
    args.out.mkdir(parents=True,exist_ok=True)
    raw=(args.vendor/"calmet.for").read_bytes()
    git_blob=hashlib.sha1(f"blob {len(raw)}\0".encode()+raw).hexdigest()
    if git_blob!=ORIGINAL_BLOB:
        raise RuntimeError(f"CALMET original source drift: {git_blob}")
    lines=raw.decode().splitlines(keepends=True)
    first=next(i for i,l in enumerate(lines)
               if l.lower().startswith("      subroutine fradj("))
    after=next(i for i,l in enumerate(lines)
               if l.lower().startswith("      subroutine gride("))
    if (first+1,after+1)!=(7289,7457):
        raise RuntimeError(f"FRADJ original source anchors drift {first+1} {after+1}")
    fr_src=args.out/"fradj_original_unmodified.for"
    fr_src.write_text("".join(lines[first:after]))
    driver=args.out/"fradj_source_fixture.for"
    driver.write_text(ORIGINAL_DRIVER)
    fort=args.out/"original_fradj_source"
    checked([args.fortran,"-O0","-std=legacy","-fno-automatic",
             "-ffixed-line-length-none","-I"+str(args.vendor),
             fr_src,driver,"-o",fort])
    results=[]
    changes=0
    total_compared=0
    mismatch_examples=[]
    worst=0.
    for name,fields,isurft in scenes():
        inp=args.out/f"{name}.in"
        with inp.open("w") as f:
            for values in fields:
                for pos in range(0,len(values),50):
                    f.write(" ".join(f"{v:.9f}" for v in values[pos:pos+50])+"\n")
        expected=args.out/f"{name}.fortran.txt"
        actual=args.out/f"{name}.cpp.csv"
        checked([fort,inp,expected,isurft])
        checked([args.cpp,inp,actual,isurft])
        a=expected.read_text().splitlines()
        with actual.open(newline="") as f:
            b=list(csv.DictReader(f))
        if len(a)!=N*NZ or len(b)!=N*NZ:
            raise RuntimeError(f"{name}: FRADJ output shape invalid")
        changed=0
        err=0.
        for n,(line,row) in enumerate(zip(a,b)):
            nums=line.split()
            i=n%NX+1;j=(n//NX)%NY+1;k=n//N+1
            if len(nums)!=5 or tuple(map(int,nums[:3]))!=(i,j,k) or (
               int(row["i"]),int(row["j"]),int(row["k"]))!=(i,j,k):
                raise RuntimeError("FRADJ original/C++ cell index mismatch")
            for idx,key,rawfield in [(3,"u_mps",fields[4]),(4,"v_mps",fields[5])]:
                ref=float(nums[idx]);got=float(row[key])
                if not math.isfinite(ref) or not math.isfinite(got):
                    raise RuntimeError("FRADJ non-finite wind")
                delta=abs(ref-got)
                err=max(err,delta)
                worst=max(worst,delta)
                total_compared+=1
                if abs(ref-rawfield[n])>0.001:
                    changed+=1
                if delta>TOL and len(mismatch_examples)<25:
                    mismatch_examples.append({
                        "scene":name,"i":i,"j":j,"k":k,
                        "component":key,"original":ref,"independent":got,
                        "absolute_error":delta})
        changes+=changed
        results.append({"scene":name,"max_abs_error_mps":err,
                        "original_changed_components":changed,
                        "status":"FAIL" if err>TOL else "PASS"})
    valid=not mismatch_examples and changes>0
    report={"status":"PASS_SOURCE_FRADJ_REAL4" if valid else "FAIL",
            "original_fortran_blob":git_blob,
            "original_fradj_lines":[first+1,after],
            "precision":"Fortran REAL / C++ float, no FMA/reassociation",
            "scope":"FRADJ only; 50x50x9, supplied HMAX/GAMMA/TEMP2D; "
                    "does NOT validate upstream TERSET or all DIAGNO",
            "tolerance_mps":TOL,
            "total_components_compared":total_compared,
            "original_adjusted_components":changes,
            "max_abs_error_mps":worst,
            "cases":results,"first_mismatches":mismatch_examples}
    (args.out/"p6d-source-fradj-parity.json").write_text(
        json.dumps(report,indent=2)+"\n")
    print(json.dumps(report,indent=2))
    if not valid:raise SystemExit(1)

if __name__=="__main__":
    main()
