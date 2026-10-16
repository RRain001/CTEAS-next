#!/usr/bin/env python3
"""Unmodified original CALMET SURFVAR full routine vs a strictly narrowed 1-station C++ candidate.

Only selected dry NOOBS=0, ITPROG=0, IRHPROG=0, NPSTA=0,
NSSTA=1, NOWSTA=0, IALL=1, IAVET=0, no-water-interpolation.
"""
import argparse
import hashlib
import json
import math
import subprocess
import tempfile
from pathlib import Path
BLOB="437f43bb7f0e51a1919e56664663e1a046986ed0"
TEMPS=[270.0,280.25,288.0,289.125,295.0,300.3,302.6,310.0,280.5,287.9,293.0,299.75]
RHS=[0,10,45,50,85,99,100,9999,32,78,9999,61]
NX,NY=5,4
PARAMS="""      integer mxnx,mxny,mxnz,mxss,mxows,mxtmp,mxwb
      parameter(mxnx=5,mxny=4,mxnz=9,mxss=4,mxows=2,
     1          mxtmp=6,mxwb=1)
      integer nx,ny,nz,nlu,nssta,nowsta,itprog,irhprog
      integer noobs,npsta,iavet,irad,numts,io6
      integer ilucat(38),ilandu(mxnx,mxny)
      integer jwat1(mxwb),jwat2(mxwb)
      integer nears(mxnx,mxny),irh(mxss),ipcode(mxss)
      real dgrid,trad,mnmdav,hafang
      real otempk(mxss),xssta(mxss),yssta(mxss)
      real tairow(mxows),rhow(mxows),xowsta(mxows),yowsta(mxows)
      common /p6e_state/ nx,ny,nz,nlu,nssta,nowsta,itprog,
     1       irhprog,noobs,npsta,iavet,irad,numts,io6,
     2       ilucat,ilandu,jwat1,jwat2,nears,irh,ipcode,
     3       dgrid,trad,mnmdav,hafang,otempk,xssta,yssta,
     4       tairow,rhow,xowsta,yowsta
"""
DRIVER="""      program selected_surfvar_driver
      include 'params.met'
      real u(mxnx,mxny),v(mxnx,mxny)
      real tprog(mxnx,mxny,mxnz),t2d(mxnx,mxny)
      integer rh2d(mxnx,mxny),pc2d(mxnx,mxny)
      integer irhpg(mxnx,mxny),ipcodepg(mxnx,mxny)
      common /surfprog/ irhpg,ipcodepg
      integer cases,c,i,j,nxi,nyi,rhs,iall
      real t
      read(*,*)cases,nxi,nyi
      if(nxi.ne.5.or.nyi.ne.4)stop 32
      nx=nxi
      ny=nyi
      nz=9
      nssta=1
      nowsta=0
      noobs=0
      npsta=0
      itprog=0
      irhprog=0
      iavet=0
      irad=1
      numts=1
      nlu=1
      ilucat(1)=12
      jwat1(1)=50
      jwat2(1)=60
      dgrid=100.
      trad=100.
      mnmdav=0.
      hafang=0.
      io6=6
      xssta(1)=150.
      yssta(1)=150.
      ipcode(1)=9999
      do i=1,nx
        do j=1,ny
          ilandu(i,j)=12
          nears(i,j)=1
          u(i,j)=2.
          v(i,j)=-1.
          irhpg(i,j)=60
          ipcodepg(i,j)=0
        enddo
      enddo
      do c=1,cases
        read(*,*)t,rhs
        otempk(1)=t
        irh(1)=rhs
        iall=1
        call surfvar(u,v,tprog,t2d,rh2d,pc2d,iall)
        do i=1,nx
          do j=1,ny
            write(*,'(3(I4,1X),ES20.11E3,1X,2(I5,1X))')
     1        c,i,j,t2d(i,j),rh2d(i,j),pc2d(i,j)
          enddo
        enddo
      enddo
      end

      subroutine avetmp(nx,ny,mnmdav,hafang,dgrid,u,v,t)
      stop 77
      end
"""
def run(args,data=None):
    r=subprocess.run([str(x) for x in args],capture_output=True,
                     input=data,text=True,check=True)
    return r.stdout
def original(src):
    lines=src.splitlines(keepends=True)
    a=[i for i,v in enumerate(lines) if v.lower().startswith("      subroutine surfvar(")]
    b=[i for i,v in enumerate(lines) if v.lower().startswith("      subroutine outhr(")]
    if len(a)!=1 or len(b)!=1 or not 490<b[0]-a[0]<570:raise RuntimeError("SURFVAR source bounds")
    return "".join(lines[a[0]:b[0]]),[a[0]+1,b[0]]
def decode(txt):
    rows=[]
    for line in txt.splitlines():
        a=line.split()
        if len(a)!=6:raise ValueError("unexpected SURFVAR output: "+line)
        row=(int(a[0]),int(a[1]),int(a[2]),float(a[3]),int(a[4]),int(a[5]))
        if not math.isfinite(row[3]):raise ValueError("invalid temperature")
        rows.append(row)
    if len(rows)!=len(TEMPS)*NX*NY:raise ValueError("wrong number of SURFVAR cells")
    return rows
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--vendor",type=Path,required=True)
    p.add_argument("--cpp",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    a=p.parse_args()
    raw=a.vendor.read_bytes()
    sha=run(["git","hash-object",a.vendor]).strip()
    if sha!=BLOB:raise RuntimeError("source hash changed")
    source,loc=original(raw.decode())
    inp=f"{len(TEMPS)} {NX} {NY}\n"+"".join(f"{t} {rh}\n" for t,rh in zip(TEMPS,RHS))
    with tempfile.TemporaryDirectory(prefix="p6e-surfvar-") as tmp:
        d=Path(tmp)
        files={"params.met":PARAMS,"surfvar.for":source,"driver.for":DRIVER}
        for empty in ("grid.met","met1.met","met2.met","tmp.met","geo.met",
                      "ovrwat.met","ziparm.met"):
            files[empty]="c all names supplied by synthetic params.met\n"
        for name,s in files.items():(d/name).write_text(s)
        run(["gfortran","-O0","-std=legacy","-fno-automatic",
             "-ffixed-line-length-none","-I"+str(d),
             d/"surfvar.for",d/"driver.for","-o",d/"original"])
        ref=decode(run([d/"original"],inp))
    cpp=decode(run([a.cpp],inp))
    diffs=[];max_temp=0.0
    for row,candidate in zip(ref,cpp):
        if row[:3]!=candidate[:3]:raise RuntimeError("case/grid cell permutation")
        delta=abs(row[3]-candidate[3]);max_temp=max(max_temp,delta)
        if (delta>0.0003 or row[4:]!=candidate[4:]) and len(diffs)<20:
            diffs.append({"original":row,"candidate":candidate})
    out={"status":"PASS" if not diffs else "FAIL","cases":len(TEMPS),
         "grid_cells":len(ref),"temperature_rh_precip_values":3*len(ref),
         "max_abs_kelvin_error":max_temp,"frozen_temperature_tolerance_K":0.0003,
         "exact_RH_and_IPCODE_masks":not diffs,
         "first_mismatches":diffs,
         "vendor_git_blob":sha,
         "vendor_sha256":hashlib.sha256(raw).hexdigest(),
         "unmodified_full_surfvar_source_lines":loc,
         "limits":"Single observed station, all-land, no smoothing, NPSTA=0. Dry original IPCODE output 0 is not validated wet forcing. Full SURFVAR and P6E NOT PASS."}
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(out,indent=2)+"\n")
    print(json.dumps(out,indent=2))
    if diffs:raise SystemExit(1)
if __name__=="__main__":main()
