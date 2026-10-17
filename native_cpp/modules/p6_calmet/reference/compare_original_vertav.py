#!/usr/bin/env python3
"""Exact original CALMET 6.5.0 VERTAV vs C++ isolated vertical integration.

Uses the unmodified original VERTAV source from calmet.for L32253-32402
compiled against vendor params.met. Both implementations receive the
*same source-parity-vetted 2022 P4 UP.DAT levels*: C++ RDUPN CSV converts
them to LGL/U/V, original Fortran VERTAV operates on those values directly.
This is VERTAV physics isolation and does NOT cover COMP AA/BB scheduling.
"""
from __future__ import annotations
import argparse,csv,hashlib,json,math,subprocess
from pathlib import Path

FORTRAN=r"""      program original_vertav_driver
      include 'params.met'
      real uu(mxus,mxlev),vv(mxus,mxlev),zz(mxus,mxlev)
      real zface(mxnzp1),uave(mxnz),vave(mxnz)
      integer k,n,nprofiles,nlev,i
      character*256 inp,out
      call get_command_argument(1,inp)
      call get_command_argument(2,out)
      open(10,file=trim(inp),status='old')
      open(11,file=trim(out),status='replace')
      read(10,*)nprofiles
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
      do n=1,nprofiles
        read(10,*)nlev
        if(nlev.lt.2.or.nlev.gt.mxlev)stop 11
        do i=1,nlev
          read(10,*)zz(1,i),uu(1,i),vv(1,i)
        enddo
        call vertav(1,uu,vv,zz,nlev,9,zface,uave,vave)
        do k=1,9
           write(11,'(3(I4,1X),2(ES22.13E3,1X))')
     1       n,nlev,k,uave(k),vave(k)
        enddo
      enddo
      close(10)
      close(11)
      end
"""
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def run(args):
    proc=subprocess.run(list(map(str,args)),capture_output=True,text=True)
    if proc.returncode:raise RuntimeError(
       f"original VERTAV compare subprocess failed {args} rc={proc.returncode} stderr={proc.stderr[-1500:]} stdout={proc.stdout[-1500:]}")
def source_extract(path,destination):
    ls=path.read_text().splitlines(keepends=True)
    a=[i for i,l in enumerate(ls) if l.lower().startswith("      subroutine vertav(")]
    b=[i for i,l in enumerate(ls) if l.lower().startswith("      subroutine water(")]
    if len(a)!=1 or len(b)!=1 or not 130<=b[0]-a[0]<=170:
        raise RuntimeError("unfrozen original VERTAV source anchors")
    destination.write_text("".join(ls[a[0]:b[0]]))
    return {"original_calmet_sha256":sha(path),"verbatim_vertav_sha256":sha(destination),
            "original_line_first":a[0]+1,"original_line_after_last":b[0]}
def fixture_from_cpp(csvfile,outfile):
    with csvfile.open(newline="") as f:rows=list(csv.DictReader(f))
    if not rows:raise RuntimeError("empty UP.dat level reader output")
    groups={}
    for row in rows:
        key=(int(row["station_id"]),int(row["epoch_end"]))
        groups.setdefault(key,[]).append(row)
    if len(groups)!=13:raise RuntimeError(f"unexpected 2022 sounding count: {len(groups)}")
    with outfile.open("w") as out:
        out.write(f"{len(groups)}\n")
        for key,group in groups.items():
            if len(group)>99 or any(int(row["level"])!=i+1 for i,row in enumerate(group)):
                raise ValueError(f"UP.DAT level mismatch {key}")
            out.write(f"{len(group)}\n")
            for row in group:
                out.write(f'{row["height_lgl_m"]} {row["u_mps"]} {row["v_mps"]}\n')
    return len(groups),len(rows)
def compare(fortran,modern):
    f=[l.split() for l in fortran.read_text().splitlines()]
    with modern.open(newline="") as h:c=list(csv.DictReader(h))
    if len(f)!=117 or len(c)!=117:raise RuntimeError("expected 13 soundings * 9 layers")
    maxerr={"u_mps":0.,"v_mps":0.}
    bad=[]
    for n,(ref,row) in enumerate(zip(f,c)):
        if len(ref)!=5 or int(ref[0])!=n//9+1 or int(ref[2])!=n%9+1 or\
           int(row["sounding_index"])!=n//9+1 or int(row["layer"])!=n%9+1:
            raise ValueError(f"original VERTAV/C++ layer ordering mismatch {n}")
        for i,key in [(3,"u_mps"),(4,"v_mps")]:
            a=float(ref[i]);b=float(row[key])
            if not (math.isfinite(a) and math.isfinite(b)):
                raise ValueError("VERTAV original/candidate nonfinite")
            error=abs(a-b)
            maxerr[key]=max(maxerr[key],error)
            if error>0.0002 and len(bad)<30:
                bad.append({"sounding":n//9+1,"layer":n%9+1,
                            "field":key,"fortran":a,"cpp":b,"error":error})
    return {"status":"PASS" if not bad else "FAIL","compared_layer_wind_components":234,
            "max_abs_errors_mps":maxerr,"frozen_abs_tolerance_mps":0.0002,
            "first_mismatches":bad}
def main():
    p=argparse.ArgumentParser()
    for key in ("vendor","up","cpp-level","cpp-vertav","out"):
        p.add_argument("--"+key,required=True,type=Path)
    p.add_argument("--station",required=True,type=int)
    a=p.parse_args()
    a.out.mkdir(parents=True,exist_ok=True)
    original=a.out/"original_vertav.for"
    source=source_extract(a.vendor/"calmet.for",original)
    driver=a.out/"original_vertav_driver.for"
    driver.write_text(FORTRAN)
    exe=a.out/"original_vertav_bin"
    run(["gfortran","-O0","-std=legacy","-fno-automatic",
         "-ffixed-line-length-none","-I"+str(a.vendor),
         original,driver,"-o",exe])
    levels=a.out/"upper_levels.csv"
    fixture=a.out/"vertav_source_levels.txt"
    reference=a.out/"original_vertav_result.txt"
    modern=a.out/"cpp_vertav_result.csv"
    run([a.cpp_level,a.up,levels,a.station])
    total_profiles,total_levels=fixture_from_cpp(levels,fixture)
    run([exe,fixture,reference])
    run([a.cpp_vertav,a.up,modern,a.station])
    report=compare(reference,modern)
    report.update({"original_source":source,"fortran_driver_sha256":sha(driver),
          "p4_up_dat_sha256":sha(a.up),"sounding_count":total_profiles,
          "raw_observation_levels":total_levels,
          "scope":"Exact original Fortran VERTAV source + current C++ RDUPN-converted profile levels; AA/BB PREPDI/time interpolation still separate"})
    (a.out/"p6c-vertav-parity.json").write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps(report,indent=2))
    if report["status"]!="PASS":raise SystemExit(1)
if __name__=="__main__":main()
