#!/usr/bin/env python3
"""Original CALMET FACET+INTP verbatim Fortran vs C++ 13 real P4 soundings.

Original routines are copied without modifications from calmet.for; input
is raw-Kelvin and first-level-relative heights from the already-validated
P6C original RDUPN level reader. This checks vertical T interpolation at
ten grid *faces*, not CALMET temperature-lapse or final 3-D temperature.
"""
from __future__ import annotations
import argparse,csv,hashlib,json,math,subprocess
from pathlib import Path

FORTRAN=r"""      program original_face_driver
      include 'params.met'
      real tt(mxus,mxlev),zz(mxus,mxlev),zface(mxnzp1)
      real tface(mxnzp1)
      integer nlev(mxus),n,number,k,i
      character*256 inp,out
      call get_command_argument(1,inp)
      call get_command_argument(2,out)
      open(10,file=trim(inp),status='old')
      open(11,file=trim(out),status='replace')
      read(10,*)number
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
      do n=1,number
        read(10,*)nlev(1)
        if(nlev(1).lt.2.or.nlev(1).gt.mxlev)stop 11
        do i=1,nlev(1)
          read(10,*)zz(1,i),tt(1,i)
        enddo
        call facet(1,tt,zz,nlev,10,zface,tface)
        do k=1,10
          write(11,'(2(I4,1X),ES22.13E3)')
     1      n,k,tface(k)
        enddo
      enddo
      close(10)
      close(11)
      end
"""
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def run(argv):
    x=subprocess.run(list(map(str,argv)),capture_output=True,text=True)
    if x.returncode:raise RuntimeError(f"original FACET/INTP failure rc={x.returncode}: {argv}, {x.stderr[-1500:]} {x.stdout[-1500:]}")
def orig(src,first,nextname,dest):
    a=src.read_text().splitlines(keepends=True)
    beg=[i for i,l in enumerate(a) if l.lower().startswith("      subroutine "+first+"(")]
    end=[i for i,l in enumerate(a) if l.lower().startswith("      subroutine "+nextname+"(")]
    if len(beg)!=1 or len(end)!=1 or not beg[0]<end[0] or end[0]-beg[0]>100:
        raise RuntimeError("original FACET/INTP source boundary changed")
    dest.write_text("".join(a[beg[0]:end[0]]))
    return {"first_source_line":beg[0]+1,"last_source_line":end[0],
            "source_sha256":sha(dest)}
def fixture(path,dest):
    with path.open(newline="") as f:records=list(csv.DictReader(f))
    groups={}
    for r in records:
        key=(int(r["station_id"]),int(r["epoch_end"]))
        groups.setdefault(key,[]).append(r)
    if len(groups)!=13:raise RuntimeError("expected 13 real source-parity sounding records")
    with dest.open("w") as f:
        f.write(f"{len(groups)}\n")
        for rows in groups.values():
            f.write(f"{len(rows)}\n")
            for r in rows:f.write(r["height_lgl_m"]+" "+r["temperature_k"]+"\n")
    return len(records)
def compare(ref,candidate):
    a=[line.split() for line in ref.read_text().splitlines()]
    with candidate.open(newline="") as f:b=list(csv.DictReader(f))
    if len(a)!=130 or len(b)!=130:raise RuntimeError("13 soundings ×10 temperature faces expected")
    bad=[];maxdiff=0.
    for idx,(row,modern) in enumerate(zip(a,b)):
        if len(row)!=3 or int(row[0])!=idx//10+1 or int(row[1])!=idx%10+1 or\
           int(modern["sounding_index"])!=idx//10+1 or int(modern["face_index"])!=idx%10+1:
            raise ValueError("FACET original/modern face index mismatch")
        delta=abs(float(row[2])-float(modern["temperature_k"]))
        if not math.isfinite(delta):raise ValueError("FACET invalid result")
        maxdiff=max(delta,maxdiff)
        if delta>0.0003 and len(bad)<20:
            bad.append({"sound":idx//10+1,"face":idx%10+1,"difference":delta})
    return {"status":"PASS" if not bad else "FAIL","compared_face_temperatures":130,
            "max_abs_kelvin_error":maxdiff,"frozen_tolerance_kelvin":0.0003,
            "first_mismatches":bad}
def main():
    p=argparse.ArgumentParser()
    for name in ("vendor","up","cpp-level","cpp-facet","out"):
        p.add_argument("--"+name,required=True,type=Path)
    p.add_argument("--station",required=True,type=int)
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
    origin=a.vendor/"calmet.for"
    facets=a.out/"original_facet.for";inter=a.out/"original_intp.for"
    src=[orig(origin,"facet","fillgeo",facets),
         orig(origin,"intp","ireplac",inter)]
    drv=a.out/"facets_driver.for";drv.write_text(FORTRAN)
    binary=a.out/"facets_original"
    run(["gfortran","-O0","-std=legacy","-fno-automatic",
         "-ffixed-line-length-none","-I"+str(a.vendor),
         facets,inter,drv,"-o",binary])
    levels=a.out/"read_up_fields.csv"
    raw=a.out/"face_input.txt"
    result=a.out/"original_face_temperature.txt"
    modern=a.out/"modern_face_temperature.csv"
    run([a.cpp_level,a.up,levels,a.station])
    count=fixture(levels,raw)
    run([binary,raw,result])
    run([a.cpp_facet,a.up,modern,a.station])
    report=compare(result,modern)
    report.update({"original_routine_sources":src,"upper_levels":count,
                   "vendor_source_sha256":sha(origin),"p4_up_sha256":sha(a.up),
                   "scope":"Original FACET+INTP on 13 real 2022 upper soundings; no AA/BB time interpolation or complete 3D temperature field"})
    (a.out/"p6c-facet-intp-parity.json").write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps(report,indent=2))
    if report["status"]!="PASS":raise SystemExit(1)
if __name__=="__main__":main()
