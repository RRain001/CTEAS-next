#!/usr/bin/env python3
"""Read-only source-level CALCPF trace at C2 H-3 receptor i=4,j=6.

Compile a TEMPORARY copy of frozen original CALPUFF Fortran with a callback
immediately AFTER the original concentration statement, use exactly the
same real MET/control inputs, and compare resulting entire puff.con bytes
to the pristine original CALPUFF output. Never alter original repository
vendor source, physics state, source/deposition parameters or native solver.
"""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ANCHOR = "                  conc=vdpvd(ipol)*xtemp*(qold(ipol)*t1+qnew(ipol)*t2)"
CALL = """                  call c2rec(isamp,jsamp,ipol,syrec,szrec,zpr,
     &                 zrpole,f1,xi1,xi2,t1,t2,qold(ipol),
     &                 qnew(ipol),xtemp,conc,frec,vdpvd(ipol),
     &                 hlid)
"""
HELPER = """
c --- C2 read-only CALCPF receiver-stage trace from identical input
      subroutine c2rec(isamp,jsamp,ipol,syrec,szrec,zpr,
     &                 zrpole,f1,xi1,xi2,t1,t2,qold,
     &                 qnew,xtemp,conc,frec,vdpvd,hlid)
      include 'datehr.puf'
      integer isamp,jsamp,ipol,seq
      real syrec,szrec,zpr,zrpole,f1,xi1,xi2,t1,t2
      real qold,qnew,xtemp,conc,frec,vdpvd,hlid
      logical first
      save seq,first
      data seq/0/,first/.true./
      if(isamp.ne.4.or.jsamp.ne.6.or.ipol.ne.1) return
c --- H1 starts at 2024 Jan 1 02:00 in accepted PR63 G35 inputs
      if(ndathrb.ne.202400102) return
      seq=seq+1
      if(seq.gt.250) return
      if(first)then
        open(unit=1937,file='c2_vendor_receiver_stage.txt',
     &       status='replace')
        first=.false.
      endif
      write(1937,*) seq,syrec,szrec,zpr,zrpole,f1,xi1,
     &             xi2,t1,t2,qold,qnew,xtemp,conc,frec,vdpvd,
     &             hlid
      return
      end
"""
FIELDS=("seq","sy","sz","zpr","zrpole","f1","xi1","xi2","t1",
        "t2","qold","qnew","xtemp","conc","frec","vdpvd","lid")

def sha256(p:Path)->str:
    return hashlib.sha256(p.read_bytes()).hexdigest()

def load_module(path:Path):
    spec=importlib.util.spec_from_file_location("c2_original_build_helper",path)
    if spec is None or spec.loader is None:
        raise ValueError("original pinned CALPUFF build helper missing")
    m=importlib.util.module_from_spec(spec)
    sys.modules[spec.name]=m
    spec.loader.exec_module(m)
    return m

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    for n in ("pr63_root","weather","control","baseline_con","out"):
        ap.add_argument("--"+n.replace("_","-"),required=True,type=Path)
    ap.add_argument("--compiler",default="gfortran")
    x=ap.parse_args()
    x.pr63_root=x.pr63_root.resolve()
    x.weather=x.weather.resolve()
    x.control=x.control.resolve()
    x.baseline_con=x.baseline_con.resolve()
    x.out.mkdir(parents=True,exist_ok=True)
    for path in (x.weather,x.control,x.baseline_con):
        if not path.is_file() or path.stat().st_size<1:
            raise ValueError("C2 vendor stage source input missing "+str(path))
    vendor=x.pr63_root/"engine/vendor/src/CALPUFF_v7.2.1_L150618"
    original=vendor/"calpuff.for"
    source=original.read_bytes().decode("latin-1")
    if source.count(ANCHOR)!=1 or source.count(ANCHOR+"\n")!=1:
        raise ValueError("source L4304 REAL4 contribution calculation anchor drift")
    for text in (CALL,HELPER):
        for line in text.splitlines():
            if len(line)>72 and line[:1]!="c":
                raise ValueError("fixed-form inserted Fortran statement exceeds col72: "+line)
    baseline_sha=sha256(x.baseline_con)
    with tempfile.TemporaryDirectory(prefix="p7-c2-readonly-source-") as d:
        root=Path(d)
        build=root/"build"
        build.mkdir()
        include=build/"include"
        include.mkdir()
        for item in sorted(vendor.iterdir()):
            if item.is_file():
                alias=include/item.name.lower()
                if not alias.exists():
                    alias.symlink_to(item.resolve())
        patched=root/"calpuff_readonly_trace.for"
        patched.write_bytes((source.replace(ANCHOR+"\n",ANCHOR+"\n"+CALL)+HELPER).encode("latin-1"))
        legacy=load_module(
            x.pr63_root/"native_cpp/modules/p6_calmet/p6f/tests/verify_original_calpuff_reads_written_calmet.py")
        binary=build/"calpuff-original-instrumented.x"
        cmd=[x.compiler,*legacy.FORTRAN_FLAGS,f"-I{include}",
             vendor/"modules.for",patched,"-o",binary]
        result=legacy.run(cmd,cwd=build,timeout=1200)
        if result.returncode!=0 or not binary.is_file():
            print(result.stdout[-5000:],result.stderr[-5000:],file=sys.stderr)
            raise ValueError("original CALPUFF trace compilation failed")
        working=legacy.stage(root/"staged",x.control,x.weather.read_bytes())
        execution=legacy.execute(working,binary,1200)
        if execution["returncode"]!=0 or not execution["concentration"].is_file():
            print(execution["stdout"][-5000:],file=sys.stderr)
            raise ValueError("original CALPUFF read-only trace runtime failed")
        if sha256(execution["concentration"])!=baseline_sha:
            raise ValueError("instrumented original CALPUFF puff.con changed; DO NOT trust trace")
        trace=working/"c2_vendor_receiver_stage.txt"
        if not trace.is_file() or trace.stat().st_size<5:
            raise ValueError("original vendor produced no receptor i4 j6 intermediate records")
        shutil.copy2(trace,x.out/"C2-vendor-H1-receptor-4-6-stage.txt")
        rows=[]
        for line in trace.read_text().splitlines():
            values=line.replace("D","E").split()
            if len(values)!=len(FIELDS):
                raise ValueError("unparsable original vendor C2 stage row: "+line[:150])
            entries={key:(int(value) if key=="seq" else float(value))
                     for key,value in zip(FIELDS,values)}
            if not all(__import__("math").isfinite(v) for v in entries.values()):
                raise ValueError("nonfinite original CALPUFF trace")
            rows.append(entries)
        report={
            "status":"ORIGINAL_VENDOR_SOURCE_TRACE_AUDITED",
            "scope":"C2 original MET i4 j6 real H-3 CALCPF contribution read-only",
            "original_calpuff_source_sha256":sha256(original),
            "original_met_sha256":sha256(x.weather),
            "controlled_source_deck_sha256":sha256(x.control),
            "original_baseline_con_sha256":baseline_sha,
            "instrumented_con_sha256":sha256(execution["concentration"]),
            "identical_complete_original_puff_con":True,
            "original_source_anchor":ANCHOR,
            "receiver_i":4,"receiver_j":6,"trace_rows":len(rows),
            "rows":rows,
        }
        (x.out/"C2-vendor-H1-receptor-4-6-stage.json").write_text(
            json.dumps(report,indent=2)+"\n")
        print(f"P7_C2_VENDOR_CALCPF_READONLY=PASS RECORDS={len(rows)}"
              f" WHOLE_PUFF_CON_IDENTICAL=YES SHA256={baseline_sha}"
              f" FIRST_CONC={rows[0]['conc']}")
        if len(rows)>=250:
            print("P7_C2_VENDOR_TRACE_NOTE=RECORD_CAP_REACHED 250 (first rows preserved)")
        return 0

if __name__=="__main__":
    try:
        raise SystemExit(main())
    except (ValueError,OSError,RuntimeError,subprocess.TimeoutExpired) as e:
        print("P7_C2_VENDOR_TRACE_BLOCKED: "+str(e),file=sys.stderr)
        raise SystemExit(1)
