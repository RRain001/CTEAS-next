#!/usr/bin/env python3
"""Source-locked original CALMET CLOUD3 exact RH 850mb cloud formula."""
import argparse
import hashlib
import json
import math
import subprocess
import tempfile
from pathlib import Path
BLOB="437f43bb7f0e51a1919e56664663e1a046986ed0"
NX,NY,CASES=5,4,32
ABS_TOL=0.000002
REL_TOL=0.000002
PARAMS="""      integer mxnx,mxny
      parameter(mxnx=5,mxny=4)
"""
DRIVER="""      program full_original_cloud3
      include 'params.met'
      real rh(mxnx,mxny),cc(mxnx,mxny)
      integer cases,nx,ny,c,i,j
      read(*,*)cases,nx,ny
      if(nx.ne.5.or.ny.ne.4)stop 44
      do c=1,cases
        do i=1,nx
          do j=1,ny
            read(*,*)rh(i,j)
            cc(i,j)=-7777.
          enddo
        enddo
        call cloud3(nx,ny,rh,cc)
        do i=1,nx
          do j=1,ny
            write(*,'(3(I6,1X),ES24.14E3)')c,i,j,cc(i,j)
          enddo
        enddo
      enddo
      end
"""
def cmd(args,source=None):
    return subprocess.run([str(x) for x in args],input=source,
                          text=True,capture_output=True,check=True).stdout
def exact_body(raw):
    lines=raw.decode("utf-8").splitlines(keepends=True)
    st=[i for i,v in enumerate(lines) if v.lower().startswith("      subroutine cloud3(")]
    en=[i for i,v in enumerate(lines) if v.lower().startswith("      subroutine cloud4 (")]
    if len(st)!=1 or len(en)!=1 or not 40<en[0]-st[0]<70:
        raise RuntimeError("Original CLOUD3 Fortran boundaries changed")
    return "".join(lines[st[0]:en[0]]),[st[0]+1,en[0]]
def fixture():
    rh=(0.,0.01,1.,5.,10.,25.,35.,50.,65.,75.,85.,93.,97.,98.,98.5,98.99,99.,99.01,99.5,100.)
    lines=[f"{CASES} {NX} {NY}"]
    countclip=0
    for c in range(CASES):
        for i in range(NX):
            for j in range(NY):
                x=rh[(i+5*j+3*c)%len(rh)]
                countclip+=x>=99.
                lines.append(str(x))
    return "\n".join(lines)+"\n",countclip
def parse(text):
    result=[]
    for line in text.splitlines():
        s=line.split()
        if len(s)!=4:raise ValueError("CLOUD3 result schema")
        key=tuple(int(x) for x in s[:3]); cc=float(s[3])
        if not math.isfinite(cc):raise ValueError("CLOUD3 nonfinite source output")
        result.append((key,cc))
    if len(result)!=CASES*NX*NY:raise ValueError("CLOUD3 lost a cell")
    return result
def main():
    p=argparse.ArgumentParser()
    for key in ("vendor","cpp","out"):p.add_argument("--"+key,required=True,type=Path)
    a=p.parse_args()
    raw=a.vendor.read_bytes()
    sha=cmd(["git","hash-object",a.vendor]).strip()
    if sha!=BLOB:raise RuntimeError("Original vendor CALMET SHA mismatch")
    original,loc=exact_body(raw)
    input_data,saturated=fixture()
    with tempfile.TemporaryDirectory(prefix="cteas-p6e-cloud3-") as tmp:
        d=Path(tmp)
        for name,source in (("params.met",PARAMS),("cloud3_original.for",original),
                            ("driver.for",DRIVER)):
            (d/name).write_text(source)
        cmd(["gfortran","-O0","-std=legacy","-fno-automatic",
             "-ffixed-line-length-none","-I"+str(d),
             d/"cloud3_original.for",d/"driver.for","-o",d/"original"])
        fortran=parse(cmd([d/"original"],input_data))
    cpp=parse(cmd([a.cpp],input_data))
    maxabs=0.;bad=[]
    for (fkey,f),(ckey,c) in zip(fortran,cpp):
        if fkey!=ckey:raise RuntimeError("CLOUD3 cell ordering mismatch")
        err=abs(f-c);maxabs=max(maxabs,err)
        if err>ABS_TOL+REL_TOL*abs(f):
            if len(bad)<15:bad.append({"cell":fkey,"fortran":f,"cpp":c,"err":err})
    out={"status":"PASS" if not bad else "FAIL","cases":CASES,
         "grid_cells_compared":len(fortran),
         "rh_ge_99_saturated_cells":saturated,
         "max_abs_cloud_fraction_error":maxabs,
         "frozen_abs_tol":ABS_TOL,"frozen_rel_tol":REL_TOL,
         "mismatches":len(bad),"first_mismatches":bad,
         "vendor_original_blob":sha,
         "vendor_sha256":hashlib.sha256(raw).hexdigest(),
         "unmodified_source_lines":loc,
         "scope":"CLOUD3 prognostic RH-based cloud only; no 2022 MCLOUD=3/4 coupled validation"}
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(out,indent=2)+"\n")
    print(json.dumps(out,indent=2))
    if bad:raise SystemExit(1)
if __name__=="__main__":main()
