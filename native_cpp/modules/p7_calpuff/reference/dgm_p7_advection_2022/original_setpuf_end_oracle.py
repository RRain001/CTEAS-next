#!/usr/bin/env python3
"""Write-only source-pinned SETPUF endpoint CTADJ2/SIGTZ oracle at DGM #3874.

The original file and case are immutable. We compile a temporary instrumented
copy, require exact original puff.con and all 254687 original DGM records, and
capture only one real original endpoint. This oracle NEVER feeds C++ physics.
"""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import struct
import sys

sys.path.insert(0,str(Path(__file__).resolve().parent))
import original_puff_step_dump as base

DGM_SHA="cbbdaa29c6222e6ca6aefe9f605ad13e7dd6d258f6ad243afcac07cb578108c6"
RECORD=struct.Struct("<4i7f")
BEFORE="            szadj=sze1*strain"
AFTER="            call sigtz(szadj,zero,zero,zpb(ii),sze1,vtze1,vdze1)"
TEMP_HELPERS="""
c --- Diagnostic COMMON is entirely separate from any CALPUFF physics COMMON.
      subroutine p7endreset
      integer hit,epid,istep,ii,ksam
      real rat,sig0,strain,adj,sige,vt,vd
      common /p7dgend/ hit,epid,rat,sig0,strain,adj,sige,vt,vd
      hit=0
      epid=0
      rat=0.
      sig0=0.
      strain=0.
      adj=0.
      sige=0.
      vt=0.
      vd=0.
      return
      end
      subroutine p7endmid(ii,r,s0,s,a)
      integer ii,hit,epid
      real r,s0,s,a,rat,sig0,strain,adj,sige,vt,vd
      common /p7dgend/ hit,epid,rat,sig0,strain,adj,sige,vt,vd
      hit=1
      epid=ii
      rat=r
      sig0=s0
      strain=s
      adj=a
      return
      end
      subroutine p7endpost(ii,se,t,dx)
      integer ii,hit,epid
      real se,t,dx,rat,sig0,strain,adj,sige,vt,vd
      common /p7dgend/ hit,epid,rat,sig0,strain,adj,sige,vt,vd
      if(hit.ne.1.or.epid.ne.ii) stop 98
      hit=2
      sige=se
      vt=t
      vd=dx
      return
      end
      subroutine p7enddump(ii,ksam)
      integer ii,ksam,hit,epid,step_count,traceunit
      real rat,sig0,strain,adj,sige,vt,vd
      common /p7dgend/ hit,epid,rat,sig0,strain,adj,sige,vt,vd
      save step_count
      data step_count/0/
      step_count=step_count+1
      if(step_count.ne.3874) return
      if(ii.ne.138.or.ksam.ne.23.or.hit.ne.2.or.epid.ne.ii) stop 97
      open(newunit=traceunit,file='dgm_setpuf_end_3874.bin',
     &     form='unformatted',access='stream',status='replace')
      write(traceunit) step_count,ii,ksam,hit,
     &          rat,sig0,strain,adj,sige,vt,vd
      close(traceunit)
      return
      end
"""

def sha(path:Path)->str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main()->None:
    ap=argparse.ArgumentParser()
    ap.add_argument("--vendor",type=Path,required=True)
    ap.add_argument("--case",type=Path,required=True)
    ap.add_argument("--out",type=Path,required=True)
    ap.add_argument("--compiler",default="gfortran-11")
    args=ap.parse_args()
    vendor,case,out=(p.resolve() for p in (args.vendor,args.case,args.out))
    base.CALLS["item8a_setpuf_entry"] += "            call p7endreset\n"
    base.CALLS["item7_setpuf_return"] += (
        "            call p7enddump(ii,ksam)\n")
    base.instrument(vendor,out)
    target=out/"calpuff_instrumented.for"
    source=target.read_text(encoding="latin-1")
    if source.count(BEFORE)!=1 or source.count(AFTER)!=1:
        raise AssertionError("original SETPUF endpoint source anchor drifted")
    source=source.replace(BEFORE+"\n",
        BEFORE+"\n"
        "            call p7endmid(ii,r,sze1,strain,szadj)\n")
    source=source.replace(AFTER+"\n",
        AFTER+"\n"
        "            call p7endpost(ii,sze1,vtze1,vdze1)\n")
    target.write_text(source+TEMP_HELPERS,encoding="latin-1")
    alias=base._alias_tree(vendor,out/"include-alias")
    executable=out/"bin"/"puff-original-setpuf-end.x"
    base._build(args.compiler,vendor/"modules.for",target,alias,executable)
    staged=out/"case"
    base._stage_case(case,staged)
    runtime=staged/"run"/"puff"
    try:
        result=base._run(executable,runtime)
    except SystemExit:
        path=runtime/"puff_runtime.log"
        if path.exists():
            print(path.read_text(errors="replace")[-6000:],file=sys.stderr)
        raise
    if result["puff_con_sha256"]!=base.TARGET_PUFF_CON_SHA256:
        raise AssertionError("original puff.con changed under SETPUF stage trace")
    dgm=runtime/"dgm_puffstep.bin"
    if sha(dgm)!=DGM_SHA or dgm.stat().st_size!=254687*352:
        raise AssertionError("original 143h COMP DGM changed under stage trace")
    with dgm.open("rb") as fd:
        fd.seek((3874-1)*352)
        dgmrow=fd.read(352)
    idx=struct.unpack("<24i",dgmrow[:96])
    assert idx[3]==138 and idx[16]==23 and idx[1]==202200102,idx
    trace=runtime/"dgm_setpuf_end_3874.bin"
    if trace.stat().st_size!=RECORD.size:
        raise AssertionError("original exactly-one endpoint record not emitted")
    count,epid,ksam,hit,*floats=RECORD.unpack(trace.read_bytes())
    if (count,epid,ksam,hit)!=(3874,138,23,2):
        raise AssertionError("original original-stage/COMP identity drifted")
    names=("R","SZE1_BEFORE_STRAIN","CTADJ2_STRAIN","SZADJ",
           "SZE1_AFTER_SIGTZ","VTZE1","VDZE1")
    print("P7_ORIGINAL_SETPUF_END_DGM3874=PASS"
          " HOUR=3 PUFF=138 KSAM=23"
          " FROZEN_PUFF_CON_AND_143H_DGM_UNCHANGED=YES")
    for name,value in zip(names,floats):
        bits=struct.unpack("<I",struct.pack("<f",value))[0]
        print(f"P7_ORIGINAL_SETPUF_END_VALUE {name}={value:.10g}"
              f" BITS=0x{bits:08x}")
    print(f"P7_ORIGINAL_SETPUF_END_TRACE_SHA256={sha(trace)}")

if __name__=="__main__":
    main()
