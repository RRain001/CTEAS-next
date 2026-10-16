#!/usr/bin/env python3
"""Test full unmodified original CALMET MIXHT in stable QH<0 grid path.

Daytime dependencies MIXDT/MIXHMC/MIXHBG/OUT are stop-stubs; if a
fixture mistakenly exercises daytime or debug printing, original exits.
The full source itself remains unaltered.
"""
import argparse
import hashlib
import json
import math
import subprocess
import tempfile
from pathlib import Path
BLOB="437f43bb7f0e51a1919e56664663e1a046986ed0"
CASES,NX,NY=30,5,4
ABS_TOL_M=0.06
REL_TOL=0.00004
PARAMS="""      integer mxnx,mxny,mxss,mxus,mxlev,mxnz
      parameter(mxnx=5,mxny=4,mxss=4,mxus=2,mxlev=12,
     1          mxnz=9)
"""
DRIVER="""      program original_stable_mixht_driver
      include 'params.met'
      include 'ziparm.met'
      include 'upmet.met'
      real el(mxnx,mxny),ustar(mxnx,mxny),qh(mxnx,mxny)
      real rho(mxnx,mxny),zi(mxnx,mxny),ziconv(mxnx,mxny)
      integer nearu(mxnx,mxny),land(mxnx,mxny)
      integer c,ncases,nx,ny,i,j,wl,wh,iupt,imixh,ihrgmt
      logical ldbhr
      read(*,*)ncases,nx,ny
      if(nx.ne.5.or.ny.ne.4)stop 31
      ldbhr=.false.
      iupt=-1
      imixh=1
      ihrgmt=12
      do c=1,ncases
        read(*,*)wl,wh,constn,zimin,zimax
        do i=1,nx
          do j=1,ny
            read(*,*)qh(i,j),ustar(i,j),el(i,j),fcori(i,j),
     1               land(i,j),zi(i,j),ziconv(i,j)
            nearu(i,j)=1
            rho(i,j)=1.2
            justa(1)=1
          enddo
        enddo
        call mixht(el,ustar,qh,nx,ny,rho,ihrgmt,nearu,
     1            iupt,land,wl,wh,ldbhr,imixh,zi,ziconv)
        do i=1,nx
          do j=1,ny
            write(*,'(3(I6,1X),2(ES23.13E3,1X))')
     1           c,i,j,zi(i,j),ziconv(i,j)
          enddo
        enddo
      enddo
      end
      subroutine mixdt
      stop 90
      end
      subroutine mixhmc
      stop 91
      end
      subroutine mixhbg
      stop 92
      end
      subroutine out
      stop 93
      end
"""
def run(args,inp=None):
    return subprocess.run([str(x) for x in args],input=inp,
            text=True,capture_output=True,check=True).stdout
def immutable_body(raw):
    rows=raw.decode("utf-8").splitlines(keepends=True)
    a=[i for i,s in enumerate(rows) if s.lower().startswith("      subroutine mixht(")]
    b=[i for i,s in enumerate(rows) if s.lower().startswith("      subroutine mixhtst(")]
    if len(a)!=1 or len(b)!=1 or not 230<b[0]-a[0]<320:
        raise RuntimeError("MIXHT original source location drift")
    return "".join(rows[a[0]:b[0]]),[a[0]+1,b[0]]
def fixture():
    us=[0.05,0.1,0.15,0.25,0.4,0.6,0.9,1.2]
    length=[4.,12.,24.,60.,140.,400.,1100.]
    f=[2.5e-5,5.7e-5,7.2e-5,1.1e-4]
    rows=[f"{CASES} {NX} {NY}"]
    land=water=0
    for c in range(CASES):
        constn=2400.+50.*(c%5)
        zimin=20.+5.*(c%4)
        zimax=1300.+100.*(c%6)
        rows.append(f"50 60 {constn} {zimin} {zimax}")
        for i in range(NX):
            for j in range(NY):
                k=i+2*j+c
                use=55 if (i+j+3*c)%7==0 else 12
                water+=use==55
                land+=use!=55
                rows.append(f"-0.1 {us[k%len(us)]} "
                    f"{length[(2*i+j+c)%len(length)]} "
                    f"{f[(i+2*j+c)%len(f)]} {use} -7777.0 -7777.0")
    return "\n".join(rows)+"\n",dict(land=land,water=water)
def parse(rows):
    output=[]
    for line in rows.splitlines():
        v=line.split()
        if len(v)!=5:raise ValueError("MIXHT reference schema mismatch")
        ident=tuple(map(int,v[:3]))
        values=tuple(float(x) for x in v[3:])
        if not all(math.isfinite(x) for x in values):raise ValueError("Nonfinite MIXHT")
        output.append((ident,values))
    if len(output)!=CASES*NX*NY:raise ValueError("MIXHT missing source records")
    return output
def main():
    p=argparse.ArgumentParser()
    for name in ("vendor","cpp","out"):p.add_argument("--"+name,type=Path,required=True)
    args=p.parse_args()
    original=args.vendor.read_bytes()
    sha=run(["git","hash-object",args.vendor]).strip()
    if sha!=BLOB:raise RuntimeError("Original CALMET source drift")
    body,loc=immutable_body(original)
    inp,counts=fixture()
    with tempfile.TemporaryDirectory(prefix="cteas-p6e-mixht-stable-") as tmp:
        d=Path(tmp)
        for name,text in (("params.met",PARAMS),
                          ("ziparm.met",(args.vendor.parent/"ziparm.met").read_text()),
                          ("upmet.met",(args.vendor.parent/"upmet.met").read_text()),
                          ("mixht.for",body),("driver.for",DRIVER)):
            (d/name).write_text(text)
        run(["gfortran","-O0","-std=legacy","-fno-automatic",
             "-ffixed-line-length-none","-I"+str(d),
             d/"mixht.for",d/"driver.for","-o",d/"original"])
        ref=parse(run([d/"original"],inp))
    got=parse(run([args.cpp],inp))
    errors=0;maxdelta=[0.,0.];first=[];water_count=0
    for (ident,f),(kk,v) in zip(ref,got):
        if ident!=kk:raise ValueError("MIXHT original order mismatch")
        if f[0]==-7777.:
            water_count+=1
            bad=f!=v
        else:
            if f[1]!=0.:raise ValueError("Original night mixed layer not zero")
            bad=False
            for k in range(2):
                delta=abs(f[k]-v[k]);maxdelta[k]=max(delta,maxdelta[k])
                bad |= delta>ABS_TOL_M+REL_TOL*abs(f[k])
        if bad:
            errors+=1
            if len(first)<20:first.append({"grid":ident,"original":f,"cpp":v})
    if water_count!=counts["water"]:raise ValueError("water mask count drift")
    report=dict(status="PASS" if errors==0 else "FAIL",
                cases=CASES,grid_cells=CASES*NX*NY,
                fields_compared=2*CASES*NX*NY,
                land_cells=counts["land"],water_cells=counts["water"],
                max_abs_error_zi_ziconv_m=maxdelta,
                frozen_absolute_tolerance_m=ABS_TOL_M,
                frozen_relative_tolerance=REL_TOL,
                mismatches=errors,first_mismatches=first,
                original_git_blob=sha,original_sha256=hashlib.sha256(original).hexdigest(),
                unmodified_full_mixht_source_lines=loc,
                scope="MIXHT only QH<0 stable branch, no upper-air sounding or daytime mixing, no P6D 143h coupling")
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps(report,indent=2))
    if errors:raise SystemExit(1)
if __name__=="__main__":main()
