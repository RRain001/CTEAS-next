#!/usr/bin/env python3
"""G32A write-only original DIAGNO diagnosis; scientific FAIL remains active.

Reuse the previously validated frozen-case CALMET write-only instrumentation
from original_internal_state_dump.py on the *G31A original staged run*, then
require the instrumented program to emit byte-identical original MET.DAT.
Compare original DIAGNO kpt10 U/V/W/DIV with separately produced G24 C++
native full-grid wind CSV. Never substitute reference arrays into C++ or
change original-vendor physical equations, numeric tolerances, or PR #53.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
import math
import shutil
import struct
from pathlib import Path

import original_internal_state_dump as dgm

NX,NY,NZ=12,12,9
N=NX*NY

def sha(path:Path)->str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def native_wind(path:Path):
    with path.open(newline="") as f:
        rd=csv.DictReader(f)
        columns={"i","j","k","u","v","div","w_below","w_above"}
        if set(rd.fieldnames or ())!=columns:
            raise ValueError("G32A actual G24 source wind CSV columns invalid")
        out={}
        for row in rd:
            key=tuple(int(row[k]) for k in ("i","j","k"))
            if (key in out or not (1<=key[0]<=NX and 1<=key[1]<=NY
                    and 1<=key[2]<=NZ)):
                raise ValueError("G32A G24 wind grid indices out of source scope")
            vals={name:float(row[name]) for name in ("u","v","div","w_below","w_above")}
            if not all(map(math.isfinite,vals.values())):
                raise ValueError("G32A G24 had nonfinite wind fields")
            out[key]=vals
    if len(out)!=N*NZ:
        raise ValueError("G32A G24 3D wind source incomplete")
    return out

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--source-run-dir",type=Path,required=True)
    p.add_argument("--original-met",type=Path,required=True)
    p.add_argument("--native-wind",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    p.add_argument("--compiler",default="gfortran")
    args=p.parse_args()
    args.out.mkdir(parents=True,exist_ok=True)
    report={"status":"BLOCKED","scope":"G32A source 2SS 2US independent original DIAGNO internal fields; DIAGNOSTIC ONLY"}
    evidence=args.out/"g32a-diagnostic.json"
    try:
        original_met=args.original_met
        if not original_met.is_file() or original_met.stat().st_size<1024:
            raise RuntimeError("G32A no independent untouched original MET.DAT")
        if sha(original_met)!=sha(args.source_run_dir/"met.dat"):
            raise RuntimeError("G32A original independent source run not identical to published copy")
        vendor=(Path(__file__).resolve().parents[4]/
                "engine/vendor/src/CALMET_v6.5.0_L150223")
        # This is the existing, source-SHA-pinned, explicitly write-only
        # DGM instrumenter already tested against original single-station
        # 143h MET.DAT byte equality. Do not implement any new Fortran
        # reference physics.
        inst_root=args.out/"source_instrumentation"
        detail=dgm.instrument(vendor,inst_root)
        alias=dgm._alias_tree(vendor,args.out/"include-alias")
        binary=args.out/"calmet_original_write_only.x"
        compile_cmd=dgm._build(
            args.compiler,inst_root/"calmet_instrumented.for",alias,binary)
        run=args.out/"instrumented-original-case"
        if run.exists():
            shutil.rmtree(run)
        shutil.copytree(args.source_run_dir,run)
        actual=dgm._run(binary,run)
        if actual["met_dat_sha256"]!=sha(original_met):
            raise RuntimeError("G32A original instrumentation changed MET.DAT values, fail closed")
        path=run/"dgm_fields.bin"
        if not path.exists() or path.stat().st_size<32:
            raise RuntimeError("G32A original DIAGNO did not produce write-only internal dump")
        order=dgm._walk_dump(path)
        audit=[x for x in order if x["kpt"]==10]
        if len(audit)!=1:
            raise RuntimeError("G32A expected one true original source-hour DIAGNO tail")
        meta=audit[0]
        if (meta["nx"],meta["ny"],meta["nz"])!=(NX,NY,NZ):
            raise RuntimeError("G32A original model internal geometry changed")
        with path.open("rb") as f:
            f.seek(meta["offset"]+32)
            div=struct.unpack("<"+str(N*NZ)+"f",f.read(4*N*NZ))
            face=struct.unpack("<"+str(N*(NZ+1))+"f",f.read(4*N*(NZ+1)))
            u=struct.unpack("<"+str(N*NZ)+"f",f.read(4*N*NZ))
            v=struct.unpack("<"+str(N*NZ)+"f",f.read(4*N*NZ))
        native=native_wind(args.native_wind)
        measured={}
        for name,arr in (("U",u),("V",v),("DIV",div),("WBELOW",face),
                         ("WABOVE",face)):
            per_level=[]
            for k in range(1,NZ+1):
                errors=[]
                first=[]
                for j in range(1,NY+1):
                    for i in range(1,NX+1):
                        cell=(j-1)*NX+i-1
                        key=(i,j,k)
                        if name=="U": orig=arr[(k-1)*N+cell]; val=native[key]["u"]
                        elif name=="V":orig=arr[(k-1)*N+cell];val=native[key]["v"]
                        elif name=="DIV":orig=arr[(k-1)*N+cell];val=native[key]["div"]
                        elif name=="WBELOW":orig=arr[(k-1)*N+cell];val=native[key]["w_below"]
                        else:orig=arr[k*N+cell];val=native[key]["w_above"]
                        errors.append(abs(orig-val))
                        if len(first)<3 and abs(orig-val)>1e-4:
                            first.append({"ij":[i,j],"original":orig,"cpp":val})
                per_level.append({"level":k,
                                  "max_abs":max(errors),
                                  "mean_abs":sum(errors)/len(errors),
                                  "samples":first})
            measured[name]=per_level
        report.update({
            "status":"PASS_WRITE_ONLY_TRACE_DIAGNOSTIC_NOT_SCIENCE",
            "original_MET_DAT_unchanged_sha256":sha(original_met),
            "instrumentation_source_sha256":detail["vendor_source_sha256"],
            "dump_sha256":sha(path),
            "dump_bytes":path.stat().st_size,
            "source_hour_original_DGM_labels":{"packed":meta["packed"],"seconds":meta["seconds"]},
            "original_vs_Cpp_G24_kpt10_level_errors":measured,
            "compiler_command":compile_cmd,
            "scientific_45_field_status":"UNCHANGED_FAIL_NUMERIC",
            "next_gate":"isolate first differing source DIAGNO stage from original kpt7/8/9 and G23 post SLOPE/G24 input",
        })
    except Exception as error:
        report["blocker"]=str(error)
        raise
    finally:
        evidence.write_text(json.dumps(report,indent=2)+"\n")
        print(json.dumps({key:val for key,val in report.items()
                          if key not in ("original_vs_Cpp_G24_kpt10_level_errors",)},
                         indent=2))
        if "original_vs_Cpp_G24_kpt10_level_errors" in report:
            for name,values in report["original_vs_Cpp_G24_kpt10_level_errors"].items():
                print(name,"max_abs_by_level",",".join(f"{x['max_abs']:.6g}" for x in values))
if __name__=="__main__":
    main()
