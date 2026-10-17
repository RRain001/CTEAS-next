#!/usr/bin/env python3
"""Source-extracted CALMET 6.5.0 SLOPE parity; isolated physics, NOT P6D acceptance."""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
import math
import subprocess
from pathlib import Path

SOURCE_BLOB = "437f43bb7f0e51a1919e56664663e1a046986ed0"
NX, NY, NZ = 50, 50, 9
ZFACE = (0, 20, 40, 80, 160, 320, 640, 1200, 2000, 3000)
ABS_TOL = 2.0e-4  # predeclared before reference-comparator execution

DRIVER = """      program slopedrv
      include 'params.met'
      include 'grid.met'
      include 'metgrd.met'
      include 'geo.met'
      include 'd6.met'
      real topo(mxnx,mxny), peaks(mxnx,mxny)
      real tmp(mxnx,mxny),u(mxnx,mxny,mxnz)
      real v(mxnx,mxny,mxnz),tinf
      character*512 infile,outfile
      call get_command_argument(1,infile)
      call get_command_argument(2,outfile)
      open(10,file=trim(infile),status='old')
      read(10,*) nx,ny,nz,dx,dy,iwat1,iwat2,isurft,tinf
      read(10,*) (zface(k),k=1,nz+1)
      do j=1,ny
        read(10,*) (topo(i,j),i=1,nx)
      enddo
      do j=1,ny
        read(10,*) (peaks(i,j),i=1,nx)
      enddo
      do j=1,ny
        read(10,*) (hmin(i,j),i=1,nx)
      enddo
      do j=1,ny
        read(10,*) (disthmax(i,j),i=1,nx)
      enddo
      do j=1,ny
        read(10,*) (disthmin(i,j),i=1,nx)
      enddo
      do j=1,ny
        read(10,*) (qh(i,j),i=1,nx)
      enddo
      do j=1,ny
        read(10,*) (tmp(i,j),i=1,nx)
      enddo
      do j=1,ny
        read(10,*) (ilandu(i,j),i=1,nx)
      enddo
      close(10)
      iwr=0
      call slope(u,v,topo,isurft,tinf,tmp,peaks)
      open(11,file=trim(outfile),status='replace')
      do k=1,nz
        do j=1,ny
          do i=1,nx
            write(11,'(3(I4,1X),2(ES22.13E3,1X))')
     1                 i,j,k,u(i,j,k),v(i,j,k)
          enddo
        enddo
      enddo
      close(11)
      end
c -- Original SLOPE calls output plotting / zero-initialization helpers:
c -- local test harness stubs only, not original physical source changes.
      subroutine xmit(n,val,a)
      real val,a(*)
      do i=1,iabs(n)
        a(i)=val
      enddo
      end
      subroutine wndlpt(a)
      real a(*)
      return
      end
"""

def run(cmd: list[object]) -> None:
    r = subprocess.run([str(x) for x in cmd], capture_output=True, text=True, timeout=120)
    if r.returncode:
        raise RuntimeError(f"command failed {cmd}; rc={r.returncode}; stdout={r.stdout[-1000:]} stderr={r.stderr[-2000:]}")

def original_slope(source: Path, target: Path) -> str:
    raw = source.read_bytes()
    sha = hashlib.sha1(f"blob {len(raw)}\0".encode() + raw).hexdigest()
    if sha != SOURCE_BLOB:
        raise RuntimeError(f"Original CALMET source changed: {sha}")
    lines = raw.decode("utf-8", errors="replace").splitlines(keepends=True)
    start = [i for i, line in enumerate(lines) if line.lower().startswith("      subroutine slope(")]
    if len(start) != 1 or start[0] + 1 != 30372:
        raise RuntimeError("Unexpected SLOPE subroutine location")
    end = next((i for i in range(start[0]+1, len(lines))
                if lines[i].lower().startswith("      subroutine ")), None)
    if end is None:
        raise RuntimeError("Unable to locate SLOPE terminator")
    target.write_text("".join(lines[start[0]:end]))
    return hashlib.sha256(target.read_bytes()).hexdigest()

def synthetic_cases():
    for name in ("flat", "downslope", "upslope", "ridge_water", "spatial_temperature", "weak_slope"):
        topo, hmax, hmin, dmax, dmin, qh, temp, lu = ([] for _ in range(8))
        for j in range(NY):
            for i in range(NX):
                if name == "flat":
                    z = 120.0
                elif name == "weak_slope":
                    z = 120.0 + i*0.1
                else:
                    z = 110.0 + 14.0*i + 3.0*j + 20.0*math.sin(i/8.0)*math.cos(j/11.0)
                topo.append(z)
                hmax.append(z + 950.0 + (i % 4))
                hmin.append(z - 650.0 - (j % 5))
                dmax.append(900.0 + i*12.0)
                dmin.append(1100.0 + j*10.0)
                heat = 160.0 if name == "upslope" else -90.0
                if name == "ridge_water" and i % 7 < 2:
                    heat = 0.0
                qh.append(heat)
                temp.append(273.0 + 0.2*i + 0.15*j)
                lu.append(52 if name == "ridge_water" and j % 6 == 0 else 10)
        isurft = 1 if name == "spatial_temperature" else -1
        yield name, (topo,hmax,hmin,dmax,dmin,qh,temp,lu), isurft

def write_input(path: Path, arrays, isurft: int) -> None:
    with path.open("w") as f:
        f.write(f"{NX} {NY} {NZ} 100 100 50 55 {isurft} 285.0\n")
        f.write(" ".join(str(z) for z in ZFACE) + "\n")
        for field in arrays:
            for off in range(0, NX*NY, NX):
                f.write(" ".join(f"{v:.7f}" if isinstance(v,float) else str(v)
                                 for v in field[off:off+NX])+"\n")

def compare(a: Path, b: Path) -> dict:
    original = [line.split() for line in a.read_text().splitlines()]
    with b.open(newline="") as f:
        modern = list(csv.DictReader(f))
    if len(original) != NX*NY*NZ or len(modern) != NX*NY*NZ:
        raise RuntimeError("SLOPE output record count mismatch")
    mismatch = []
    nonzero = 0
    maxerr = {"u_mps":0.0,"v_mps":0.0}
    for n,(r,c) in enumerate(zip(original,modern)):
        idx = (n%NX+1, n//NX%NY+1, n//(NX*NY)+1)
        if len(r)!=5 or tuple(int(v) for v in r[:3])!=idx or \
           (int(c["i"]),int(c["j"]),int(c["k"]))!=idx:
            raise RuntimeError(f"SLOPE source ordering mismatch row {n}")
        for field, col in (("u_mps",3),("v_mps",4)):
            a0,b0 = float(r[col]), float(c[field])
            if not (math.isfinite(a0) and math.isfinite(b0)):
                raise RuntimeError("nonfinite Fortran/C++ SLOPE output")
            if abs(a0)>1.0e-5: nonzero+=1
            delta=abs(a0-b0)
            maxerr[field]=max(maxerr[field],delta)
            if delta>ABS_TOL and len(mismatch)<10:
                mismatch.append({"idx":idx,"field":field,"fortran":a0,"cpp":b0,"error":delta})
    return {"status":"PASS" if not mismatch else "FAIL",
            "components":2*NX*NY*NZ,"nonzero_original_u":nonzero,
            "max_abs_errors":maxerr,"first_mismatches":mismatch}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--vendor",required=True,type=Path)
    p.add_argument("--cpp",required=True,type=Path)
    p.add_argument("--out",required=True,type=Path)
    arg=p.parse_args()
    arg.out.mkdir(parents=True,exist_ok=True)
    extraction=arg.out/"slope_original.for"
    extraction_sha=original_slope(arg.vendor/"calmet.for",extraction)
    driver=arg.out/"slope_driver.for"
    driver.write_text(DRIVER)
    binary=arg.out/"slope_fortran"
    run(["gfortran","-O0","-std=legacy","-fno-automatic",
         "-ffixed-line-length-none","-I"+str(arg.vendor),
         extraction,driver,"-o",binary])
    cases={}
    total=0
    for name,fields,isurft in synthetic_cases():
        case=arg.out/(name+".input")
        foutput=arg.out/(name+".fortran")
        coutput=arg.out/(name+".cpp.csv")
        write_input(case,fields,isurft)
        run([binary,case,foutput])
        run([arg.cpp,case,coutput])
        entry=compare(foutput,coutput)
        cases[name]=entry
        total+=entry["components"]
    status="PASS_ISOLATED_ORIGINAL_SLOPE_PARITY" if all(x["status"]=="PASS" for x in cases.values()) else "FAIL"
    if not any(x["nonzero_original_u"]>0 for x in cases.values()):
        status="FAIL_NO_PHYSICAL_SLOPE_FLOW"
    report={"status":status,"scope":"Isolated original SLOPE only: synthetic heat flux/terrain, not actual hourly CALMET diagnostic 3D wind",
            "original_calmet_git_blob":SOURCE_BLOB,"extracted_subroutine_sha256":extraction_sha,
            "abs_tolerance_mps":ABS_TOL,"comparison_components":total,"cases":cases,
            "p6c_complete":False,"p6d_integrated":False,"wet_forcing_validated":False}
    (arg.out/"p6d-slope-parity.json").write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps(report,indent=2))
    if not status.startswith("PASS"): raise SystemExit(1)

if __name__=="__main__":
    main()
