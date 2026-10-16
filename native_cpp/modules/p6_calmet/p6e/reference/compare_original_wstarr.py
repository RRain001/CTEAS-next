#!/usr/bin/env python3
"""Fortran source-locked original WSTARR parity (not a coupled P6E gate)."""
import argparse
import hashlib
import json
import math
import subprocess
import tempfile
from pathlib import Path
BLOB="437f43bb7f0e51a1919e56664663e1a046986ed0"
NX,NY,CASES=5,4,30
ABS_TOL_MS=0.00002
REL_TOL=0.00003
PARAMS="""      integer mxnx,mxny,mxss,mxnz
      parameter(mxnx=5,mxny=4,mxss=4,mxnz=9)
"""
DRIVER="""      program wstarr_source_driver
      include 'params.met'
      real zic(mxnx,mxny),qh(mxnx,mxny),t(mxnx,mxny)
      real rho(mxnx,mxny),ws(mxnx,mxny)
      integer land(mxnx,mxny)
      integer c,ncases,nx,ny,i,j,wl,wh
      read(*,*)ncases,nx,ny
      if(nx.ne.5.or.ny.ne.4)stop 42
      do c=1,ncases
        read(*,*)wl,wh
        do i=1,nx
          do j=1,ny
            read(*,*)zic(i,j),qh(i,j),t(i,j),rho(i,j),
     1               land(i,j),ws(i,j)
          enddo
        enddo
        call wstarr(zic,qh,t,rho,land,wl,wh,nx,ny,ws)
        do i=1,nx
          do j=1,ny
            write(*,'(3(I6,1X),ES24.14E3)')c,i,j,ws(i,j)
          enddo
        enddo
      enddo
      end
"""
def run(a,inp=None):
    return subprocess.run([str(x) for x in a],input=inp,
                          text=True,capture_output=True,check=True).stdout
def immutable_body(src):
    lines=src.decode("utf-8").splitlines(keepends=True)
    a=[i for i,s in enumerate(lines) if s.lower().startswith("      subroutine wstarr(")]
    b=[i for i,s in enumerate(lines) if s.lower().startswith("      subroutine xmit(")]
    if len(a)!=1 or len(b)!=1 or not 55<b[0]-a[0]<85:
        raise RuntimeError("WSTARR source bounds unexpectedly changed")
    return "".join(lines[a[0]:b[0]]),[a[0]+1,b[0]]
def fixture():
    flux=[-0.1,0.,0.5,10.,60.,200.,500.,950.]
    zi=[0.,20.,100.,400.,1100.,2000.,2500.]
    temp=[269.,277.,288.,298.,309.]
    rho=[0.95,1.05,1.18,1.32]
    rows=[f"{CASES} {NX} {NY}"]
    countwater=0; countday=0; countnight=0
    for c in range(CASES):
        rows.append("50 60")
        for i in range(NX):
            for j in range(NY):
                k=i+2*j+c
                land=55 if (i+j+c)%8==0 else 12
                qh=flux[k%len(flux)]
                zic=zi[(i+3*j+c)%len(zi)]
                rows.append(f"{zic} {qh} {temp[(i+j+c)%len(temp)]} "
                            f"{rho[(i+2*j+c)%len(rho)]} {land} -7777.0")
                countwater+=land==55
                countday+=land!=55 and qh>0
                countnight+=land!=55 and qh<=0
    return "\n".join(rows)+"\n",dict(water=countwater,positive=countday,nonpositive=countnight)
def parse(raw):
    rows=[]
    for line in raw.splitlines():
        s=line.split()
        if len(s)!=4:raise ValueError("WSTARR schema mismatch")
        index=tuple(map(int,s[:3]));w=float(s[3])
        if not math.isfinite(w):raise ValueError("Nonfinite WSTARR output")
        rows.append((index,w))
    if len(rows)!=CASES*NX*NY:raise ValueError("Wrong WSTARR record count")
    return rows
def main():
    p=argparse.ArgumentParser()
    for name in ("vendor","cpp","out"):p.add_argument("--"+name,type=Path,required=True)
    a=p.parse_args()
    raw=a.vendor.read_bytes()
    sha=run(["git","hash-object",a.vendor]).strip()
    if sha!=BLOB:raise RuntimeError("WSTARR original vendor hash drift")
    body,loc=immutable_body(raw)
    inp,counts=fixture()
    with tempfile.TemporaryDirectory(prefix="cteas-p6e-wstarr-") as scratch:
        d=Path(scratch)
        for name,text in (("params.met",PARAMS),("wstarr.for",body),("driver.for",DRIVER)):
            (d/name).write_text(text)
        run(["gfortran","-O0","-std=legacy","-fno-automatic",
             "-ffixed-line-length-none","-I"+str(d),
             d/"wstarr.for",d/"driver.for","-o",d/"original"])
        expected=parse(run([d/"original"],inp))
    actual=parse(run([a.cpp],inp))
    first=[];errors=0;maxdiff=0.0
    for (ident,ref),(key,x) in zip(expected,actual):
        if ident!=key:raise ValueError("WSTARR cell reorder")
        delta=abs(ref-x)
        maxdiff=max(maxdiff,delta)
        sentinel=ref==-7777.
        bad=(ref!=x) if sentinel else delta>ABS_TOL_MS+REL_TOL*abs(ref)
        if bad:
            errors+=1
            if len(first)<20:first.append(dict(cell=ident,original=ref,cpp=x,delta=delta))
    result=dict(status="PASS" if errors==0 else "FAIL",
                grid_values_compared=len(actual),cases=CASES,
                water_cells=counts["water"],land_positive_heat_cells=counts["positive"],
                land_nonpositive_heat_cells=counts["nonpositive"],
                max_abs_wstar_error_ms=maxdiff,frozen_abs_tolerance_ms=ABS_TOL_MS,
                frozen_relative_tolerance=REL_TOL,
                mismatches=errors,first_mismatches=first,
                original_git_blob=sha,original_sha256=hashlib.sha256(raw).hexdigest(),
                unmodified_source_lines=loc,
                scope="isolated CALMET WSTARR original source; not 2022 143h MIXHT/heat-flux coupling")
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps(result,indent=2))
    if errors:raise SystemExit(1)
if __name__=="__main__":main()
