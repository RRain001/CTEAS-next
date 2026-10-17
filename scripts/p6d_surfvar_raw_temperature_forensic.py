#!/usr/bin/env python3
"""Forensic original CALMET SURFVAR raw TEMP2D before AVETMP, Hefei 143h.

The production source, C++ kernels and scientific tolerances are never edited.
The trace is inserted only in a temporary Fortran copy, and its MET.DAT must
remain byte-identical to the frozen untouched CALMET result.
"""
from __future__ import annotations
import argparse, collections, json, re, struct, sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"native_cpp/modules/p6_calmet/reference"))
import original_internal_state_dump as dgm

PATTERN=re.compile(
    r"(?m)^      if \(iavet\.eq\.1\.and\.iall\.ne\.2\)[^\n]*\n"
    r"     &\s*call avetmp\(nx,ny,mnmdav,hafang,dgrid,u,v,temp2d\)\s*\n",
    re.IGNORECASE)
REPLACEMENT="""      if (iavet.eq.1.and.iall.ne.2) then
         call dgmrawt(temp2d,nx,ny)
         call avetmp(nx,ny,mnmdav,hafang,dgrid,u,v,temp2d)
      endif
"""
HELPER="""
c --- original SURFVAR pre-AVETMP grid, separate write-only file
      subroutine dgmrawt(temperature,nx,ny)
      include 'params.met'
      integer nx,ny
      real temperature(mxnx,mxny)
      logical started
      save started
      data started/.false./
      if(.not.started)then
         open(87,file='dgm_raw_surfvar_t.bin',form='unformatted',
     1        access='stream',status='replace')
         started=.true.
      endif
      write(87) nx,ny
      write(87) ((temperature(i,j),i=1,nx),j=1,ny)
      return
      end
"""

def main():
    ap=argparse.ArgumentParser()
    for p in ("original-dir","case","out"):
        ap.add_argument("--"+p,required=True,type=Path)
    ap.add_argument("--compiler",default="gfortran-11")
    a=ap.parse_args()
    audit=json.loads((a.original_dir/"dgm-audit.json").read_text())
    if (audit.get("status")!="ORIGINAL_MET_DAT_IDENTICAL" or
        audit.get("frozen_reference_sha256")!=dgm.TARGET_MET_DAT_SHA256):
        raise RuntimeError("unverified original CALMET baseline")
    source=a.original_dir/"calmet_instrumented.for"
    if (dgm.sha256_file(source)!=
        audit["instrumentation"]["instrumented_sha256"]["calmet_instrumented.for"]):
        raise RuntimeError("original-source input sha drift")
    original=source.read_text()
    new,matched=PATTERN.subn(REPLACEMENT,original)
    if matched!=1:raise RuntimeError(f"original SURFVAR AVETMP site drift: {matched}")
    root=a.out.parent/"raw_surfvar_source"
    root.mkdir(parents=True,exist_ok=True)
    copied=root/"calmet_surfvar_raw.for"
    copied.write_text(new+HELPER)
    exe=root/"bin"/"met-raw-surfvar.x"
    dgm._build(a.compiler,copied,a.original_dir/"include-alias",exe)
    case=root/"case"
    dgm._stage_case(a.case.resolve(),case)
    ran=dgm._run(exe,case/"run"/"met")
    if ran["met_dat_sha256"]!=dgm.TARGET_MET_DAT_SHA256:
        raise RuntimeError("write-only SURFVAR trace modified original MET.DAT")
    trace=case/"run"/"met"/"dgm_raw_surfvar_t.bin"
    data=trace.read_bytes()
    cells=2500;record=8+cells*4
    if len(data)!=3*143*record:
        raise RuntimeError(f"unexpected original AVETMP input trace size {len(data)}")
    statistics=[]
    per_site={}
    total_nonuniform=0
    total_changed=0
    for hour in range(143):
        sample={"hour_index":hour,
                "hour_end":str(__import__("datetime").datetime(2022,1,1)+
                         __import__("datetime").timedelta(hours=hour+1))}
        for phase,label in ((0,"DIAGNO_initial"),(1,"DIAGNO_post_FRADJ"),(2,"COMP")):
            off=(hour*3+phase)*record
            nx,ny=struct.unpack_from("<2i",data,off)
            if (nx,ny)!=(50,50):raise RuntimeError("source raw grid metadata drift")
            bits=struct.unpack_from("<2500I",data,off+8)
            counts=collections.Counter(bits)
            mode,count=counts.most_common(1)[0]
            vals=[struct.unpack("<f",struct.pack("<I",v))[0] for v in (min(bits),max(bits),mode,bits[(29-1)*50+23-1])]
            phase_stat={"unique_real4_values":len(counts),
                        "cells_differ_from_mode":2500-count,
                        "mode_kelvin":vals[2],
                        "sample_i23_j29_kelvin":vals[3],
                        "sample_i23_j29_minus_mode":vals[3]-vals[2]}
            sample[label]=phase_stat
            if phase==1:
                total_nonuniform+=len(counts)>1
                total_changed+=2500-count
                if hour in (18,131):per_site[label+str(hour)]=phase_stat
        statistics.append(sample)
    result={"status":"ORIGINAL_RAW_SURFVAR_FORENSIC_ONLY",
            "original_MET_DAT_byte_identical":True,
            "source_instrumented_sha256":dgm.sha256_file(copied),
            "calls":3*143,"grid":[50,50],"post_FRADJ_hours_nonuniform":total_nonuniform,
            "post_FRADJ_cells_differing_from_hourly_mode":total_changed,
            "case_2022_01_06_12":statistics[131],
            "case_2022_01_01_19":statistics[18],
            "per_hour":statistics}
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps({k:v for k,v in result.items() if k!="per_hour"},indent=2))
if __name__=="__main__":main()
