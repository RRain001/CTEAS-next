#!/usr/bin/env python3
"""Locate earliest source-vs-native WIND1 3D REAL*4 discrepancy at hour 1.

A write-only subroutine is inserted into a copy of SHA-locked CALMET after
WIND1's original interpolation loop, before returning to DIAGNO. The original
CALMET.DAT must remain bitwise equal to the frozen 143h reference. No original
wind is injected into the C++ calculation. All 50*50*9 U and V REAL4 values
are compared, not just the already accepted first layer.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import shutil
import struct
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"native_cpp/modules/p6_calmet/reference"))
import original_internal_state_dump as oracle

NXY=50*50
NZ=9
VOLUME=NXY*NZ
SOURCE_HELPER=r"""
c --- Write-only first-hour selected WIND1 full 3D U/V original state.
      subroutine p6e_wind1_first3d
      include 'params.met'
      include 'gen.met'
      include 'grid.met'
      include 'd1.met'
      integer i,j,k
      logical done
      save done
      data done/.false./
      if(done)return
      if(nx.ne.50.or.ny.ne.50.or.nz.ne.9)
     1  stop 'P6E_WIND1_FORENSIC_SHAPE'
      open(98,file='p6e_wind1_full3d_first.bin',
     1    form='unformatted',access='stream',status='replace')
      write(98) (((ug(i,j,k),i=1,nx),j=1,ny),k=1,nz)
      write(98) (((vg(i,j,k),i=1,nx),j=1,ny),k=1,nz)
      close(98)
      done=.true.
      return
      end
"""

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def patch(original,output):
    if sha(original)!=oracle.ORIGINAL_CALMET_SHA256:
        raise ValueError("CALMET source does not match frozen original")
    lines=original.read_text().splitlines(keepends=True)
    if (lines[36400].strip().lower()!="return" or
        "End loop over i,j cells" not in lines[36398]):
        raise ValueError("original WIND1 return/loop source anchor changed")
    lines.insert(36400,"      call p6e_wind1_first3d\n")
    output.write_text("".join(lines)+SOURCE_HELPER)

def read_native(path):
    raw=path.read_bytes()
    if len(raw)!=VOLUME*4:
        raise ValueError(f"native {path} has wrong REAL4 50x50x9 shape")
    return struct.unpack("<22500f",raw)

def compare(original_data,native,field):
    summary=[]
    nonzero=0
    exact=0
    for k in range(NZ):
        ref=original_data[k*NXY:(k+1)*NXY]
        val=native[k*NXY:(k+1)*NXY]
        worst={"abs":0.0,"layer":k+1,"i":None,"j":None}
        first=None
        sq=0.0
        layer_nonzero=0
        for idx,(a,b) in enumerate(zip(ref,val)):
            if not(math.isfinite(a) and math.isfinite(b)):
                raise ValueError(f"nonfinite original/native {field} layer {k+1}")
            diff=abs(a-b)
            sq+=diff*diff
            if diff:
                layer_nonzero+=1
                if first is None:
                    first={"i":idx%50+1,"j":idx//50+1,
                           "original":a,"native":b,"abs":diff}
            if diff>worst["abs"]:
                worst={"abs":diff,"layer":k+1,"i":idx%50+1,
                       "j":idx//50+1,"original":a,"native":b}
        nonzero+=layer_nonzero
        exact+=NXY-layer_nonzero
        summary.append({"k":k+1,"total":NXY,"nonzero":layer_nonzero,
                        "rms":math.sqrt(sq/NXY),"first":first,"worst":worst})
    return {"field":field,"total":VOLUME,"nonzero":nonzero,
            "exact":exact,"layers":summary}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--vendor",required=True,type=Path)
    p.add_argument("--case",required=True,type=Path)
    p.add_argument("--native",required=True,type=Path)
    p.add_argument("--out",required=True,type=Path)
    p.add_argument("--compiler",default="gfortran-11")
    a=p.parse_args()
    vendor=a.vendor.resolve()
    if sha(vendor/"calutils.for")!=oracle.ORIGINAL_CALUTILS_SHA256:
        raise ValueError("CALUTILS source changed")
    root=a.out.resolve().parent/"original-wind1-3d"
    root.mkdir(parents=True,exist_ok=True)
    instrumented=root/"calmet_wind1_3d_writeonly.for"
    patch(vendor/"calmet.for",instrumented)
    aliases=oracle._alias_tree(vendor,root/"includes")
    exe=root/"bin/original-wind1-3d.x"
    oracle._build(a.compiler,instrumented,aliases,exe)
    case=root/"case"
    if case.exists():shutil.rmtree(case)
    oracle._stage_case(a.case.resolve(),case)
    rundir=case/"run/met"
    outcome=oracle._run(exe,rundir)
    if outcome["met_dat_sha256"]!=oracle.TARGET_MET_DAT_SHA256:
        raise ValueError("original wind3d instrumentation changed frozen MET.DAT")
    rawfile=rundir/"p6e_wind1_full3d_first.bin"
    raw=rawfile.read_bytes()
    if len(raw)!=VOLUME*2*4:
        raise ValueError(f"wrong original wind3d binary shape {len(raw)}")
    original=struct.unpack("<45000f",raw)
    n=a.native.resolve()
    stamp="2022-01-01_01"
    byfield={}
    for field,offset in (("u",0),("v",VOLUME)):
        source=original[offset:offset+VOLUME]
        candidate=read_native(n/f"wind1_{field}_{stamp}.f32")
        byfield[field]=compare(source,candidate,field)
    report={"status":"ORIGINAL_WIND1_FULL3D_SOURCE_DIFFERENCE_MEASURED",
            "scope":"first hour full 50x50x9 U/V original WIND1 output",
            "frozen_original_met_sha256":outcome["met_dat_sha256"],
            "instrumented_source_sha256":sha(instrumented),
            "original_wind1_snapshot_sha256":sha(rawfile),
            "no_original_wind_input_into_native":True,
            "fields":byfield,
            "science_P6E_G4":"NOT_CLAIMED"}
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(report,indent=2)+"\n")
    for name,val in byfield.items():
        print("WIND1_3D",name,"TOTAL_NONZERO",val["nonzero"])
        for item in val["layers"]:
            print("WIND1_3D_LAYER",name,item["k"],"NONZERO",
                  item["nonzero"],"RMS",item["rms"],
                  "MAX_ABS",item["worst"]["abs"],"FIRST",item["first"])

if __name__=="__main__":
    main()
