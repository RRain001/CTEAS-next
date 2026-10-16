#!/usr/bin/env python3
"""Literal unchanged CALMET 6.5.0 PGTSTB vs standalone C++20 output.

28 atmospheric/cloud configurations x 5x4 grid, fixed 4 stations;
water sentinel explicitly preserved and counted separately.
"""
import argparse
import hashlib
import json
import subprocess
import tempfile
from pathlib import Path
EXPECTED_BLOB="437f43bb7f0e51a1919e56664663e1a046986ed0"
NC=28
NX,NY,NS=5,4,4
SENTINEL=-999
DRIVER="""      program original_pgtstb_driver
      include 'params.met'
      real u(mxnx,mxny),v(mxnx,mxny)
      real sun(mxnx,mxny),cloud(mxnx,mxny)
      integer near(mxnx,mxny),land(mxnx,mxny)
      integer ceilg(mxnx,mxny),pgt(mxnx,mxny)
      integer icc(mxss),iceil(mxss)
      integer cases,nx,ny,ns,c,s,i,j,mode,wl,wh
      read(*,*)cases,nx,ny,ns
      if(nx.ne.5.or.ny.ne.4.or.ns.ne.4)stop 11
      do c=1,cases
        read(*,*)mode,wl,wh
        do s=1,ns
          read(*,*)icc(s),iceil(s)
        enddo
        do i=1,nx
          do j=1,ny
            read(*,*)u(i,j),v(i,j),sun(i,j),land(i,j),
     1               near(i,j),cloud(i,j),ceilg(i,j)
            pgt(i,j)=-999
          enddo
        enddo
        call pgtstb(u,v,near,icc,iceil,sun,land,wl,wh,
     1       nx,ny,mode,cloud,ceilg,pgt)
        do i=1,nx
          do j=1,ny
            write(*,'(4(I6,1X))')c,i,j,pgt(i,j)
          enddo
        enddo
      enddo
      end
"""
PARAMS="""      integer mxnx,mxny,mxss
      parameter(mxnx=5,mxny=4,mxss=4)
"""
def run(args,inp=None):
    r=subprocess.run([str(x) for x in args],input=inp,capture_output=True,
                     text=True,check=True)
    return r.stdout
def slice_fortran(src):
    lines=src.splitlines(keepends=True)
    start=[k for k,line in enumerate(lines)
           if line.lower().startswith("      subroutine pgtstb(")]
    stop=[k for k,line in enumerate(lines)
          if line.lower().startswith("      subroutine prepdi(")]
    if len(start)!=1 or len(stop)!=1 or not 150<stop[0]-start[0]<260:
        raise RuntimeError("source PGTSTB boundaries changed")
    return "".join(lines[start[0]:stop[0]]),[start[0]+1,stop[0]]
def fixture():
    solar=(-0.8,-0.01,0.0,0.001,0.258819,0.25882,
           0.5735764,0.573577,0.8660254,0.866026,1.0)
    cloud=(0.0,0.4,0.5,0.6,0.9,1.0)
    ceil=(0,69,70,159,160,999)
    wind=(0,0.2,0.6,1.2,2.2,4.0,9.0,19.0)
    lines=[f"{NC} {NX} {NY} {NS}"]
    water=0
    for c in range(NC):
        lines.append(f"{1+c%4} 50 60")
        for s in range(NS):
            lines.append(f"{(s+c)%11} {ceil[(c+s)%len(ceil)]}")
        for i in range(NX):
            for j in range(NY):
                u=wind[(i+3*j+c)%len(wind)]
                v=wind[(2*i+j+2*c)%len(wind)]/2
                sun=solar[(i+2*j+3*c)%len(solar)]
                land=55 if (i+2*j+c)%9==0 else 12
                water+=land==55
                nears=(i+j+c)%NS+1
                cc=cloud[(i+2*j+c)%len(cloud)]
                ceiling=ceil[(3*i+j+c)%len(ceil)]
                lines.append(f"{u:.7f} {v:.7f} {sun:.7f} {land} "
                             f"{nears} {cc:.7f} {ceiling}")
    return "\n".join(lines)+"\n",water
def parse(raw):
    rows=[]
    for line in raw.splitlines():
        parts=line.split()
        if len(parts)!=4:raise ValueError("unexpected PGTSTB output")
        x=tuple(int(t) for t in parts)
        if x[3]!=SENTINEL and not 1<=x[3]<=6:
            raise ValueError("invalid PGTSTB class")
        rows.append(x)
    if len(rows)!=NC*NX*NY:raise ValueError("wrong comparison size")
    return rows
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--vendor",type=Path,required=True)
    p.add_argument("--cpp",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    a=p.parse_args()
    raw=a.vendor.read_bytes()
    sha=run(["git","hash-object",a.vendor]).strip()
    if sha!=EXPECTED_BLOB:raise ValueError("vendor blob changed")
    body,loc=slice_fortran(raw.decode("utf-8"))
    inp,expected_water=fixture()
    with tempfile.TemporaryDirectory(prefix="p6e-original-pgtstb-") as tmp:
        d=Path(tmp)
        for name,content in (("params.met",PARAMS),
                             ("pgtstb.for",body),("driver.for",DRIVER)):
            (d/name).write_text(content)
        run(["gfortran","-O0","-std=legacy","-fno-automatic",
             "-ffixed-line-length-none","-I"+str(d),
             d/"pgtstb.for",d/"driver.for","-o",d/"original"])
        original=parse(run([d/"original"],inp))
    candidate=parse(run([a.cpp],inp))
    errors=[{"original":f,"cpp":c} for f,c in zip(original,candidate) if f!=c][:20]
    orig_water=sum(r[3]==SENTINEL for r in original)
    cpp_water=sum(r[3]==SENTINEL for r in candidate)
    if orig_water!=expected_water or cpp_water!=expected_water:
        raise RuntimeError("water output masks differ")
    report={"status":"PASS" if not errors else "FAIL",
            "compared_cells":len(original),
            "land_cells":len(original)-orig_water,
            "water_cells_preserved":orig_water,
            "mismatches":len(errors),"first_mismatches":errors,
            "vendor_git_blob":sha,"vendor_sha256":hashlib.sha256(raw).hexdigest(),
            "original_lines":loc,"cases":NC,
            "scope":"isolated PGTSTB source-equivalent on synthetic gridded/observed clouds, not integrated 2022 COMP or complete P6E"}
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps(report,indent=2))
    if errors:raise SystemExit(1)
if __name__=="__main__":main()
