#!/usr/bin/env python3
"""Compare unmodified full CALMET HEATFX against isolated source-backed C++.

24 modes x 5x4 grid x two fields, with water QH sentinel initialized before
each original call. This is not a 2022 integrated 143-hour scientific pass.
"""
import argparse
import hashlib
import json
import math
import subprocess
import tempfile
from pathlib import Path
BLOB="437f43bb7f0e51a1919e56664663e1a046986ed0"
NX,NY,NS,CASES=5,4,4,24
# pre-registered REAL*4 source/output tolerance in W/m^2; relative limit
# used only for non-sentinel floating values and finite physics.
TOL_ABS_WM2=0.02
TOL_REL=0.00003
PARAMS="""      integer mxnx,mxny,mxss
      parameter(mxnx=5,mxny=4,mxss=4)
"""
DRIVER="""      program full_heatfx_driver
      include 'params.met'
      real sun(mxnx,mxny),temp(mxnx,mxny),cloud(mxnx,mxny)
      real qh(mxnx,mxny),qsw(mxnx,mxny)
      integer near(mxnx,mxny),land(mxnx,mxny),icc(mxss)
      integer cases,nx,ny,ns,c,s,i,j,mode,wl,wh
      include 'hflux.met'
      read(*,*)cases,nx,ny,ns
      if(nx.ne.5.or.ny.ne.4.or.ns.ne.4)stop 12
      do c=1,cases
        read(*,*)mode,wl,wh,ha1,ha2,hb1,hb2,hc1,hc2,hc3p1
        do s=1,ns
          read(*,*)icc(s)
        enddo
        do i=1,nx
          do j=1,ny
            read(*,*)sun(i,j),temp(i,j),land(i,j),near(i,j),
     1               cloud(i,j),albedo(i,j),bowen(i,j),
     2               hcg(i,j),qf(i,j),qh(i,j)
          enddo
        enddo
        call heatfx(sun,near,temp,icc,land,wl,wh,
     1              nx,ny,mode,cloud,qh,qsw)
        do i=1,nx
          do j=1,ny
            write(*,'(3(I6,1X),2(ES22.12E3,1X))')
     1          c,i,j,qsw(i,j),qh(i,j)
          enddo
        enddo
      enddo
      end
"""
def run(args,inp=None):
    x=subprocess.run([str(y) for y in args],input=inp,text=True,
                     capture_output=True,check=True)
    return x.stdout
def exact_source(raw):
    l=raw.decode("utf-8").splitlines(keepends=True)
    a=[k for k,v in enumerate(l) if v.lower().startswith("      subroutine heatfx(")]
    b=[k for k,v in enumerate(l) if v.lower().startswith("      subroutine inter2(")]
    if len(a)!=1 or len(b)!=1 or not 100<=b[0]-a[0]<=160:
        raise RuntimeError("unmodified HEATFX source boundaries changed")
    return "".join(l[a[0]:b[0]]),[a[0]+1,b[0]]
def fixture():
    sun=(-0.85,-0.1,0.0,0.005,0.05,0.3,0.65,0.98)
    clouds=(0.0,0.1,0.2,0.5,0.8,1.0)
    temps=(269.9,278.5,288.0,295.2,304.0,312.0)
    lines=[f"{CASES} {NX} {NY} {NS}"]
    night=water=land=0
    for c in range(CASES):
        mode=1+c%4
        ha1=950.0+10*(c%5)
        ha2=48.0+2*(c%3)
        hb1=-0.75;hb2=3.0
        hc1=1.0e-13;hc2=30.0;hc3p1=1.5
        lines.append(f"{mode} 50 60 {ha1} {ha2} {hb1} {hb2} {hc1} {hc2} {hc3p1}")
        for ns in range(NS):lines.append(str((c+3*ns)%11))
        for i in range(NX):
            for j in range(NY):
                sine=sun[(i+2*j+c)%len(sun)]
                temp=temps[(i+3*j+c)%len(temps)]
                lu=55 if (i+3*j+c)%7==0 else 12
                sta=(i+j+c)%NS+1
                cloud=clouds[(2*i+j+c)%len(clouds)]
                albedo=0.1+0.05*((i+c)%6)
                bowen=0.35+0.35*((j+c)%5)
                hcg=0.05+0.03*((i+j+c)%5)
                anthrop=3.0+2.0*((i+c)%8)
                lines.append(f"{sine:.7f} {temp:.7f} {lu} {sta} "
                             f"{cloud:.7f} {albedo:.7f} {bowen:.7f} "
                             f"{hcg:.7f} {anthrop:.7f} -7777.0")
                water+=lu==55
                land+=lu!=55
                night+=lu!=55 and sine<=0
    return "\n".join(lines)+"\n",{"water":water,"land":land,"night":night}
def parse(raw):
    out=[]
    for line in raw.splitlines():
        v=line.split()
        if len(v)!=5:raise ValueError("HEATFX output schema")
        key=tuple(map(int,v[:3]))
        value=tuple(float(s.replace("D","E")) for s in v[3:])
        if not all(math.isfinite(x) for x in value):
            raise ValueError("nonfinite heat flux")
        out.append((key,value))
    if len(out)!=CASES*NX*NY:raise ValueError("HEATFX value count")
    return out
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--vendor",required=True,type=Path)
    p.add_argument("--cpp",required=True,type=Path)
    p.add_argument("--out",required=True,type=Path)
    a=p.parse_args()
    raw=a.vendor.read_bytes()
    sha=run(["git","hash-object",a.vendor]).strip()
    if sha!=BLOB:raise ValueError("unfrozen source blob")
    body,loc=exact_source(raw)
    fixture_data,stats=fixture()
    with tempfile.TemporaryDirectory(prefix="p6e-original-heatfx-") as path:
        d=Path(path)
        for name,text in (("params.met",PARAMS),
                          ("hflux.met",(a.vendor.parent/"hflux.met").read_text()),
                          ("full_heatfx.for",body),("driver.for",DRIVER)):
            (d/name).write_text(text)
        run(["gfortran","-O0","-std=legacy","-fno-automatic",
             "-ffixed-line-length-none","-I"+str(d),
             d/"full_heatfx.for",d/"driver.for","-o",d/"reference"])
        ref=parse(run([d/"reference"],fixture_data))
    cpp=parse(run([a.cpp],fixture_data))
    failures=[];maxqsw=0.0;maxqh=0.0;exceed=0
    for (k,ff),(kk,cc) in zip(ref,cpp):
        if k!=kk:raise ValueError("cell/time reordering")
        for which,(f,v) in enumerate(zip(ff,cc)):
            delta=abs(f-v)
            if which==0:maxqsw=max(maxqsw,delta)
            else:maxqh=max(maxqh,delta)
            # Sentinel and night -0.1 must agree exactly.
            sentinel=which==1 and f in (-7777.0,-0.1)
            bad=(f!=v) if sentinel else (delta>TOL_ABS_WM2+TOL_REL*abs(f))
            if bad:
                exceed+=1
                if len(failures)<20:failures.append({"cell":k,"field":which,"fortran":f,"cpp":v,"abs_err":delta})
    result={"status":"PASS" if not exceed else "FAIL",
            "cases":CASES,"cells":len(ref),"flux_components_compared":len(ref)*2,
            "water_cells":stats["water"],"land_cells":stats["land"],
            "land_night_cells":stats["night"],
            "max_abs_qsw_error_wm2":maxqsw,"max_abs_qh_error_wm2":maxqh,
            "frozen_abs_tolerance_wm2":TOL_ABS_WM2,
            "frozen_rel_tolerance":TOL_REL,
            "exceedances":exceed,"first_mismatches":failures,
            "original_git_blob":sha,"original_sha256":hashlib.sha256(raw).hexdigest(),
            "unmodified_source_lines":loc,
            "scientific_gate":"HEATFX selected source equivalence only; not real 2022 joint fields or completed P6E"}
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps(result,indent=2))
    if exceed:raise SystemExit(1)
if __name__=="__main__":main()
