#!/usr/bin/env python3
"""G33B: original third SURFVAR IALL=1 at COMP L4567 vs G24-final-wind C++.

Original source DIAGNO calls SURFVAR twice at L5610/L5669, followed by
COMP's THIRD SURFVAR (U,V final native diagnostic field) at L4567.
We reuse G33A's pinned source and write-only Fortran helper, append one
COMP-only call AFTER original L4567, and independently compare to the
native source G24-final-wind temperature. Frozen P6E remains authoritative.
"""
from __future__ import annotations
import argparse
import csv
import datetime as dt
import hashlib
import json
import math
import shutil
import struct
from pathlib import Path

import original_internal_state_dump as vendor
import g33a_trace_original_multisite_two_pass_surfvar as g33a
from g32f_first_comp_input_original_state_trace import read_temp3d_source

N = g33a.CELLS
NX = g33a.NX
NY = g33a.NY
RECORD = g33a.RECORD_BYTES

def sha(path:Path)->str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def create_trace_source(source_path:Path,out:Path):
    anchors=g33a.patch_vendor(source_path,out)
    lines=out.read_text().splitlines(keepends=True)
    # Validate original COMP source L4567; these two original unchanged
    # source cards appear BEFORE G33A's 2 DIAGNO insertions. An
    # instrumentation drift must fail rather than trace the wrong call.
    original_line=(
        "         call surfvar(u(1,1,1),v(1,1,1),"
        "tprog,temp2d,irh2d,ipcode2d,1)"
    )
    if len(lines)<4569 or lines[4566].strip().lower()!=original_line.strip().lower():
        raise RuntimeError("G33B original COMP SURFVAR IALL=1 L4567 anchor changed")
    if lines[4565].strip().lower()!="if(isfcmet.eq.0) then":
        raise RuntimeError("G33B original COMP surface flag guard missing")
    lines.insert(4567,"      call dgm_g33a_surfvar(3,temp2d)\n")
    out.write_text("".join(lines))
    return anchors+[{"ordinal":3,"original_start_line":4567,
                     "original_last_line":4567,
                     "source_call":lines[4566].strip()}]

def native_third(path:Path):
    rows={};timestamps=set()
    with path.open(newline="") as handle:
        r=csv.DictReader(handle)
        if set(r.fieldnames or [])!={"hour_end_utc_seconds","i","j","temp_k"}:
            raise ValueError("G33B third native CSV column schema changed")
        for row in r:
            i,j=int(row["i"]),int(row["j"])
            val=float(row["temp_k"])
            if not(1<=i<=NX and 1<=j<=NY) or (i,j) in rows or not math.isfinite(val):
                raise ValueError("G33B third native cell duplicated/nonfinite")
            rows[i,j]=struct.unpack("<f",struct.pack("<f",val))[0]
            timestamps.add(int(row["hour_end_utc_seconds"]))
    if len(rows)!=N or len(timestamps)!=1:
        raise ValueError("G33B native final source COMP grid or UTC hour invalid")
    return rows,timestamps.pop()

def read_three_original(path:Path,stamp:int):
    blob=path.read_bytes()
    if len(blob)!=3*RECORD:
        raise ValueError("G33B original CALMET requires THREE source SURFVAR updates")
    output=[]
    for k in range(3):
        off=k*RECORD
        h=struct.unpack_from("<6i",blob,off)
        if h!=(k+1,stamp,0,NX,NY,0):
            raise ValueError("G33B original SURFVAR call order/time/geometry mismatch")
        output.append(struct.unpack_from("<"+str(N)+"f",blob,off+24))
    return output

def compare(source_grid, candidate_grid, stage):
    errors=[];bits=0;first=None
    for j in range(1,NY+1):
        for i in range(1,NX+1):
            idx=(j-1)*NX+i-1
            ref=source_grid[idx];val=candidate_grid[i,j]
            if not math.isfinite(ref) or not math.isfinite(val):
                raise ValueError("G33B grid has non-finite temperature")
            delta=abs(ref-val);errors.append(delta)
            if struct.pack("<f",ref)!=struct.pack("<f",val):
                bits+=1
                if first is None:
                    first={"i":i,"j":j,"original_k":ref,"candidate_k":val,
                           "abs_k":delta}
    return {"stage":stage,"compared_cells":N,"bit_mismatches":bits,
            "max_abs_k":max(errors),
            "rms_k":math.sqrt(sum(e*e for e in errors)/N),
            "first_bit_difference":first}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--source-run-dir",required=True,type=Path)
    p.add_argument("--untouched-met",required=True,type=Path)
    p.add_argument("--frozen-verdict",required=True,type=Path)
    p.add_argument("--native-two-pass",required=True,type=Path)
    p.add_argument("--native-third-pass",required=True,type=Path)
    p.add_argument("--existing-comp-temp3d-source",required=True,type=Path)
    p.add_argument("--out",required=True,type=Path)
    p.add_argument("--compiler",default="gfortran")
    a=p.parse_args()
    a.out.mkdir(parents=True,exist_ok=True)
    result={"status":"BLOCKED","scientific_status":"FAIL_NUMERIC",
            "scope":"G33B original full CALMET DIAGNO twice and COMP THIRD SURFVAR, scientific hold"}
    try:
        verdict=json.loads(a.frozen_verdict.read_text())
        if (verdict.get("status")!="FAIL_NUMERIC"
                or verdict.get("fields_per_hour")!=45
                or verdict.get("intervals")!=1):
            raise ValueError("G33B requires genuine G31 frozen 45-field failure")
        if sha(a.untouched_met)!=sha(a.source_run_dir/"met.dat"):
            raise ValueError("G33B original unchanged science MET.DAT differs")
        two,old_stamp=g33a.native_grid(a.native_two_pass)
        third,end=native_third(a.native_third_pass)
        if old_stamp!=end:
            raise ValueError("G33B C++ two/third SURFVAR hours differ")
        date=dt.datetime.fromtimestamp(end-3600,dt.timezone.utc)
        if date!=dt.datetime(2024,1,1,2,tzinfo=dt.timezone.utc):
            raise ValueError("G33B original CALMET selected source hour drift")
        packed=date.year*100000+date.timetuple().tm_yday*100+date.hour
        vendor_path=Path(__file__).resolve().parents[4]/"engine/vendor/src/CALMET_v6.5.0_L150223"
        if sha(vendor_path/"calutils.for")!=vendor.ORIGINAL_CALUTILS_SHA256:
            raise ValueError("G33B original vendor calutils SHA drift")
        src=a.out/"original-calmet-third-surfvar-writeonly.for"
        anchors=create_trace_source(vendor_path/"calmet.for",src)
        alias=vendor._alias_tree(vendor_path,a.out/"include-alias")
        exe=a.out/"original-calmet-third-surfvar-writeonly.x"
        vendor._build(a.compiler,src,alias,exe)
        staged=a.out/"instrumented-original"
        if staged.exists():shutil.rmtree(staged)
        shutil.copytree(a.source_run_dir,staged)
        instrument=vendor._run(exe,staged)
        if instrument["met_dat_sha256"]!=sha(a.untouched_met):
            raise ValueError("G33B original third-pass write-only altered MET.DAT bytes")
        dump=staged/"g33a_surfvar_two_pass.bin"
        originals=read_three_original(dump,packed)
        native1={(i,j):vals[0] for (i,j),vals in two.items()}
        native2={(i,j):vals[1] for (i,j),vals in two.items()}
        actual_native=[native1,native2,third]
        diag=[compare(ref,cand,["DIAGNO_SURFVAR_first",
                               "DIAGNO_SURFVAR_second",
                               "COMP_SURFVAR_THIRD"][k])
              for k,(ref,cand) in enumerate(zip(originals,actual_native))]
        existing=read_temp3d_source(a.existing_comp_temp3d_source)
        old_comp={(i,j):values["TEMP2D"] for (i,j),values in existing.items()}
        old_vs_original=compare(originals[2],old_comp,
                                "ORIGINAL_COMP_THIRD_vs_existing_native_COMP_TEMP3D_input")
        native_third_vs_original=diag[2]
        # Full source original kpt1 TEMP2D may be identical to original third,
        # but this report claims only the instrumented original third stage,
        # not an uninstrumented final numerical acceptance.
        result.update({"status":"PASS_G33B_ORIGINAL_COMP_THIRD_SURFVAR_DIAGNOSIS_ONLY",
            "scientific_status":"FAIL_NUMERIC",
            "original_vendor_sha256":sha(vendor_path/"calmet.for"),
            "original_unchanged_met_sha256":sha(a.untouched_met),
            "instrumented_met_sha256":instrument["met_dat_sha256"],
            "original_three_surfvar_dump_sha256":sha(dump),
            "full_frozen_exceedances":verdict["total_exceedances"],
            "original_three_calls":anchors,
            "original_versus_native_by_call":diag,
            "original_COMP_THIRD_vs_existing_native_comp_input":old_vs_original,
            "source_comp_third_is_exact_from_final_wind":
                native_third_vs_original["bit_mismatches"]==0,
            "comp_input_is_stale_second_survar":
                old_vs_original["bit_mismatches"]>0,
            "original_source_never_injected_into_native":True,
            "note":"Source COMP runs SURFVAR(U,V,...,IALL=1) at calmet.for L4567; G26B must not reuse DIAGNO heat/TEMP2D unless separately demonstrated full original parity.",
        })
    except Exception as exc:
        result["blocker"]=str(exc)
        raise
    finally:
        (a.out/"g33b-third-surfvar-diagnosis.json").write_text(
            json.dumps(result,indent=2)+"\n")
        print(json.dumps(result,indent=2))

if __name__=="__main__":
    main()
