#!/usr/bin/env python3
"""Original unmodified CALMET 6.5.0 MIXDT source numerical parity.
Soundings contain missing temperature levels but always bracket both
heights. Uses exact vendor source; not a 2022 AA/BB-time integration gate.
"""
import argparse
import hashlib
import json
import math
import subprocess
import tempfile
from pathlib import Path

BLOB="437f43bb7f0e51a1919e56664663e1a046986ed0"
CASES,NS,NLEV=96,2,10
ABS=(0.0004,0.0004,0.000002)
REL=0.00001
PARAMS="""      integer mxnx,mxny,mxus,mxlev,io6
      parameter(mxnx=5,mxny=4,mxus=2,mxlev=10,io6=6)
"""
DRIVER="""      program original_source_mixdt
      include 'params.met'
      real zl(mxus,mxlev),tz(mxus,mxlev)
      real htold,dzzi,dptmin,tht,thtp,dtheta
      integer cases,nsta,nlev,ista,c,st,k,i,j
      read(*,*)cases,nsta,nlev
      if(nsta.ne.mxus.or.nlev.ne.mxlev)stop 62
      do c=1,cases
        read(*,*)ista,htold,dptmin,dzzi
        do st=1,nsta
          do k=1,nlev
            read(*,*)zl(st,k),tz(st,k)
          enddo
        enddo
        call mixdt(12,1,1,ista,htold,nlev,zl,tz,dptmin,
     1             dzzi,tht,thtp,dtheta)
        write(*,'(I6,1X,3(ES24.14E3,1X))')
     1       c,tht,thtp,dtheta
      enddo
      end
"""
def run(command,inp=None):
    return subprocess.run([str(x) for x in command],input=inp,
                          text=True,capture_output=True,check=True).stdout
def original_source(raw):
    lines=raw.decode("utf-8").splitlines(keepends=True)
    aa=[i for i,v in enumerate(lines) if v.lower().startswith("      subroutine mixdt(")]
    bb=[i for i,v in enumerate(lines) if v.lower().startswith("      subroutine mixdt2(")]
    if len(aa)!=1 or len(bb)!=1 or not 185<bb[0]-aa[0]<220:
        raise RuntimeError("Original MIXDT source anchors drifted")
    return "".join(lines[aa[0]:bb[0]]),[aa[0]+1,bb[0]]
def fixture():
    heights=(0.,50.,100.,180.,300.,450.,650.,900.,1250.,1800.)
    old=(0.,65.,100.,190.,375.,700.,1100.)
    depth=(20.,75.,120.,200.,300.)
    rows=[f"{CASES} {NS} {NLEV}"]
    missing_cases=clipped=0
    for c in range(CASES):
        station=1+c%NS
        htold=old[(c//2)%len(old)]
        dzzi=depth[(c//5)%len(depth)]
        dptmin=(0.0005,0.001,0.006,0.02)[(c//3)%4]
        rows.append(f"{station} {htold} {dptmin} {dzzi}")
        for st in range(NS):
            for k,h in enumerate(heights):
                z=h+20.*st
                # Keep level at 0 for both sites to bracket HTOLD=0;
                # move other heights slightly between AA station profiles.
                if k==0:z=0.
                temp=304.-0.0072*z+st*1.3+c*0.02+0.12*(k%3)
                if k in (1,4,7) and (c+st+k)%3!=0:
                    temp=9999.
                    missing_cases+=1
                rows.append(f"{z:.4f} {temp:.7f}")
        clipped+=dptmin>=0.006
    return "\n".join(rows)+"\n",dict(missing_temperature_cells=missing_cases,
                                    high_minimum_gradient_cases=clipped,
                                    stations=NS)
def parse(text):
    rows=[]
    for line in text.splitlines():
        f=line.split()
        if len(f)!=4:raise ValueError("MIXDT original output record malformed")
        key=int(f[0]); v=tuple(float(z.replace("D","E")) for z in f[1:])
        if not all(math.isfinite(y) for y in v):
            raise ValueError("MIXDT nonfinite original output")
        rows.append((key,v))
    if len(rows)!=CASES:raise ValueError("MIXDT lost comparison rows")
    return rows
def main():
    p=argparse.ArgumentParser()
    for n in ("vendor","cpp","out"):p.add_argument("--"+n,type=Path,required=True)
    x=p.parse_args()
    raw=x.vendor.read_bytes()
    sha=run(["git","hash-object",x.vendor]).strip()
    if sha!=BLOB:raise RuntimeError("CALMET version hash drift")
    source,locations=original_source(raw)
    inp,counts=fixture()
    with tempfile.TemporaryDirectory(prefix="cteas-p6e-mixdt-") as work:
        d=Path(work)
        for name,val in (("params.met",PARAMS),
                         ("gen.met",(x.vendor.parent/"gen.met").read_text()),
                         ("mixdt.for",source),("driver.for",DRIVER)):
            (d/name).write_text(val)
        run(["gfortran","-O0","-std=legacy","-fno-automatic",
             "-ffixed-line-length-none","-I"+str(d),
             d/"mixdt.for",d/"driver.for","-o",d/"original"])
        expected=parse(run([d/"original"],inp))
    actual=parse(run([x.cpp],inp))
    maxerr=[0.,0.,0.];first=[];bad=0
    for (key,a),(kk,b) in zip(expected,actual):
        if key!=kk:raise RuntimeError("MIXDT comparison record reordering")
        for i in range(3):
            err=abs(a[i]-b[i]);maxerr[i]=max(maxerr[i],err)
            if err>ABS[i]+REL*abs(a[i]):
                bad+=1
                if len(first)<20:first.append(
                    dict(case=key,field=i,fortran=a[i],cpp=b[i],absdiff=err))
    data=dict(status="PASS" if bad==0 else "FAIL",
              cases=CASES,values_compared=CASES*3,
              max_abs_error_tht_thtp_gamma=maxerr,
              frozen_absolute_tolerances=ABS,
              frozen_relative_tolerance=REL,
              mismatches=bad,first_mismatches=first,
              distribution=counts,original_git_blob=sha,
              original_sha256=hashlib.sha256(raw).hexdigest(),
              original_source_lines=locations,
              scope="MIXDT temperature lapse from selected sounding profile only;"
                    " no AA/BB selection, full MIXHT, TEMP3D or real 143h coupling")
    x.out.parent.mkdir(parents=True,exist_ok=True)
    x.out.write_text(json.dumps(data,indent=2)+"\n")
    print(json.dumps(data,indent=2))
    if bad:raise SystemExit(1)
if __name__=="__main__":main()
