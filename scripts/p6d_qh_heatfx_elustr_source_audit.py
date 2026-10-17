#!/usr/bin/env python3
"""Pinned CALMET original DIAGNO QH bisection: after HEATFX vs after ELUSTR.

Uses write-only instrumentation, verifies original MET.DAT sha256 unchanged,
and compares original QH to the native write-only pre-ELUSTR trace and QH
actually consumed by SLOPE. No physics modification or tolerance widening.
"""
from __future__ import annotations
import argparse, datetime as dt, hashlib, json, math, struct, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"native_cpp/modules/p6_calmet/reference"))
import original_internal_state_dump as dgm
from p6d_trace_and_compare_slope_drivers_143h import sha,read_native

NX=NY=50
NH=143
CELLS=NX*NY
STRICT_QH=2e-4
HELPER="""
c --- Write-only original after-HEATFX and after-ELUSTR heat-flux grid
      subroutine dgmqhstage(point)
      include 'params.met'
      include 'gen.met'
      include 'grid.met'
      include 'metgrd.met'
      integer point,i,j
      logical opened
      save opened
      data opened/.false./
      if(.not.opened)then
         open(88,file='dgm_qh_stages.bin',form='unformatted',
     1        access='stream',status='replace')
         opened=.true.
      endif
      write(88) point,ndathrb,nsecb,nx,ny
      write(88) ((qh(i,j),i=1,nx),j=1,ny)
      return
      end
"""
def stage_instrument(before:Path,after:Path):
    lines=before.read_text().splitlines(keepends=True)
    # CALMET calls HEATFX in BOTH COMP (around L4583) and DIAGNO
    # (around L5686). Each has ISFCMET=0 and ISFCMET=1 branches:
    # four matches are expected. The SLOPE input audit must sample only
    # DIAGNO's first (ISFCMET=0) HEATFX and ELUSTR calls; COMP precedes
    # the per-hour DIAGNO wind construction and is a different stage.
    ending="     1              iwat2,nx,ny,mcloud,ccgrid,qh,qsw)"
    heat=[i for i,l in enumerate(lines)
          if l.rstrip()==ending
          and any("call heatfx(" in s.lower() for s in lines[max(0,i-6):i+1])]
    if len(heat)!=4 or not(heat[0]<heat[1]<5000<heat[2]<heat[3]):
        raise RuntimeError(f"HEATFX original COMP/DIAGNO source site drift: {heat}")
    first_heat=heat[2]
    end_elustr="     2               nx,ny,mcloud,ccgrid,ipsifcn,qh,ustar,el)"
    elustr=[i for i,l in enumerate(lines)
           if l.rstrip()==end_elustr
           and any("call elustr(" in s.lower() for s in lines[max(0,i-6):i+1])]
    if len(elustr)!=2 or not(first_heat<elustr[0]<heat[3]<elustr[1]):
        raise RuntimeError(f"DIAGNO ISFCMET ELUSTR source order drift: {elustr}")
    lines.insert(elustr[0]+1,"      call dgmqhstage(2)\n")
    lines.insert(first_heat+1,"      call dgmqhstage(1)\n")
    after.write_text("".join(lines)+HELPER)
def originals(path:Path):
    raw=path.read_bytes()
    size=20+CELLS*4
    if len(raw)!=NH*2*size:
        raise RuntimeError(f"QH stage trace size: {len(raw)}")
    for h in range(NH):
        values=[]
        for step in (1,2):
            off=(h*2+(step-1))*size
            tag,t,sec,nx,ny=struct.unpack_from("<5i",raw,off)
            start=dt.datetime(2022,1,1)+dt.timedelta(hours=h)
            expected=start.year*100000+start.timetuple().tm_yday*100+start.hour
            if (tag,t,sec,nx,ny)!=(step,expected,0,NX,NY):
                raise RuntimeError(f"QH stage header mismatch {h},{step}: {(tag,t,sec,nx,ny)}")
            data=struct.unpack_from("<2500f",raw,off+20)
            if not all(math.isfinite(x) and abs(x)<999998 for x in data):
                raise RuntimeError("original QH stage has missing/nonfinite")
            values.append(data)
        yield values
def main():
    ap=argparse.ArgumentParser()
    for k in ("original-dir","vendor","case","candidate","out"):
        ap.add_argument("--"+k,type=Path,required=True)
    ap.add_argument("--compiler",default="gfortran-11")
    args=ap.parse_args()
    audit=json.loads((args.original_dir/"dgm-audit.json").read_text())
    if audit.get("status")!="ORIGINAL_MET_DAT_IDENTICAL" or (
        audit.get("frozen_reference_sha256")!=dgm.TARGET_MET_DAT_SHA256 or
        sha(args.vendor/"calmet.for")!=dgm.ORIGINAL_CALMET_SHA256):
        raise RuntimeError("original reference audit or hash invalid")
    baseline=args.original_dir/"calmet_instrumented.for"
    if sha(baseline)!=audit["instrumentation"]["instrumented_sha256"]["calmet_instrumented.for"]:
        raise RuntimeError("baseline instrumented hash incorrect")
    build=args.out.parent/"qh_original_stages"
    build.mkdir(parents=True,exist_ok=True)
    program=build/"calmet_qh_stage_instrumented.for"
    stage_instrument(baseline,program)
    exe=build/"bin"/"calmet_original_qh_stages.x"
    dgm._build(args.compiler,program,args.original_dir/"include-alias",exe)
    original_case=build/"case"
    dgm._stage_case(args.case.resolve(),original_case)
    ran=dgm._run(exe,original_case/"run/met")
    if ran["met_dat_sha256"]!=dgm.TARGET_MET_DAT_SHA256:
        raise RuntimeError("QH original source instrumentation changed MET.DAT")
    sums={k:{"compared":0,"exceedances":0,"max_abs":0.,"worst":None,"hours":{}}
          for k in ("HEATFX_before_ELUSTR","ELUSTR_after")}
    for h,(src_pre,src_post) in enumerate(
        originals(original_case/"run/met"/"dgm_qh_stages.bin")):
        label=(dt.datetime(2022,1,1)+dt.timedelta(hours=h+1)).strftime("%Y-%m-%d_%H")
        source=args.candidate/f"hour_{h:03d}"/"diagno"
        if not source.is_dir():source=args.candidate
        for name,src,basename in (
            ("HEATFX_before_ELUSTR",src_pre,f"qh_before_elustr_{label}.f32"),
            ("ELUSTR_after",src_post,f"qh_{label}.f32")):
            cand=read_native(source/basename)
            agg=sums[name]
            for k,(expected,actual) in enumerate(zip(src,cand)):
                delta=abs(expected-actual)
                agg["compared"]+=1
                if delta>STRICT_QH:
                    agg["exceedances"]+=1
                    agg["hours"][label]=agg["hours"].get(label,0)+1
                if delta>agg["max_abs"]:
                    agg["max_abs"]=delta
                    agg["worst"]={"hour":label,"i":k%50+1,"j":k//50+1,
                                  "original":expected,"native":actual,
                                  "abs_error":delta}
    output={
        "status":"FORENSIC_ONLY_NO_PHYSICS_CHANGED",
        "original_met_byte_identical":True,
        "source_sha256":dgm.ORIGINAL_CALMET_SHA256,
        "instrumented_sha256":sha(program),
        "original_trace_sha256":sha(original_case/"run/met"/"dgm_qh_stages.bin"),
        "qH_absolute_tolerance_Wm2":STRICT_QH,
        "scientific_verdict":"PASS_BOTH_STAGES" if all(
            v["exceedances"]==0 for v in sums.values()) else
            "FAIL_ONE_OR_BOTH_STAGES",
        "fields":sums,
    }
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(output,indent=2)+"\n")
    print(json.dumps(output,indent=2))
if __name__=="__main__":
    main()
