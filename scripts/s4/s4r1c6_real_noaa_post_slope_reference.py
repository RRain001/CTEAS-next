#!/usr/bin/env python3
"""S4-R1c6: genuine 2SS/1US original-CALMET vs source-native post-SLOPE U/V.

Scratch-only original Fortran reports actual DIAGNO after SLOPE at all
9 vertical planes. Native G47 consumes original GEO/SURF/UP/met.inp ONLY.
Neither original MET.DAT nor this reference trace is a native input.
"""
from __future__ import annotations
import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import subprocess

BLOB="437f43bb7f0e51a1919e56664663e1a046986ed0"
TRACE="s4r1c6-original-firsthour-post-slope.txt"
NX,NY,NZ=82,85,9
WIND_ABS_MPS=0.05  # Existing pre-frozen true-NOAA G21 U/V envelope.

def sha(path:Path)->str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def source(vendor:Path)->list[str]:
    blob=subprocess.run(["git","hash-object",str(vendor)],
                        capture_output=True,text=True,check=True).stdout.strip()
    if blob!=BLOB:
        raise ValueError("R1c6 source CALMET original blob drift: "+blob)
    rows=vendor.read_text().splitlines()
    if ("if (ISLOPE.EQ.1)CALL SLOPE" not in rows[5721]
        or "300 CONTINUE" not in rows[5731]
        or "CALL FRADJ" not in rows[5642]):
        raise ValueError("Original DIAGNO SLOPE phase anchor drift")
    return rows

def prepare(vendor:Path,dest:Path,receipt:Path)->None:
    rows=source(vendor)
    insert=[
        "      if(nhrz.eq.2) then",
        f"      open(unit=95,file='{TRACE}',",
        "     1     status='unknown',position='append',action='write')",
        "      do k=1,nz",
        "      do j=1,ny",
        "      do i=1,nx",
        "      write(95,9886) nhrz,i,j,k,ilandu(i,j),",
        "     1     ug(i,j,k),vg(i,j,k)",
        "      enddo",
        "      enddo",
        "      enddo",
        " 9886 format(5(i6,1x),2(es23.15,1x))",
        "      close(unit=95)",
        "      endif",
    ]
    dest.parent.mkdir(parents=True,exist_ok=True)
    # The original line 5732 is the last line of SLOPE accumulation.
    # Insert strictly after original 300 CONTINUE without changing any formula.
    dest.write_text("\n".join(rows[:5732]+insert+rows[5732:])+"\n")
    receipt.parent.mkdir(parents=True,exist_ok=True)
    receipt.write_text(json.dumps({
        "source_original_blob":BLOB,
        "source_original_sha256":sha(vendor),
        "scratch_only_sha256":sha(dest),
        "write_only_after_original_line":5732,
        "original_physics_modified":False,
        "native_candidate_input_uses_original_fields":False,
        "scientific_result":"NOT_RUN"
    },indent=2,sort_keys=True)+"\n")
    print("S4R1C6_ORIGINAL_SLOPE_SCRATCH_INSTRUMENT=SHA_PINNED")

def verify(vendor:Path,baseline_met:Path,scratch_met:Path,
           original_trace:Path,native_csv:Path,report:Path)->None:
    source(vendor)
    if sha(baseline_met)!=sha(scratch_met):
        raise ValueError("Instrumented original mutated original 6h x 45 MET.DAT")
    n=NX*NY*NZ
    original={}
    for line in original_trace.read_text().splitlines():
        parts=line.strip().split()
        if len(parts)!=7:
            raise ValueError("R1c6 original post-SLOPE trace bad row")
        h,i,j,k,land=map(int,parts[:5])
        if h!=2 or not(1<=i<=NX and 1<=j<=NY and 1<=k<=NZ):
            raise ValueError("R1c6 original grid/level/hour drift")
        uv=tuple(float(x.replace("D","E")) for x in parts[5:])
        if not all(math.isfinite(x) for x in uv):
            raise ValueError("Nonfinite original U/V")
        key=(i,j,k)
        if key in original:
            raise ValueError("Duplicate original post-SLOPE cell")
        original[key]=(land,*uv)
    if len(original)!=n:
        raise ValueError(f"Incomplete original first-hour 9-plane coverage: {len(original)}")
    observed=set()
    maxima={label:{"max_abs_mps":0.0,"cell":None}
            for label in ("u","v")}
    per={"land":{"cells":0,"comparisons":0,"max_abs_mps":0.0},
         "water":{"cells":0,"comparisons":0,"max_abs_mps":0.0}}
    fails=[]
    with native_csv.open(newline="") as handle:
        rows=csv.DictReader(handle)
        expected=("i","j","k","hour_end_utc_seconds","landuse",
                  "pre_slope_u_mps","pre_slope_v_mps",
                  "post_slope_u_mps","post_slope_v_mps")
        if tuple(rows.fieldnames or ())!=expected:
            raise ValueError("Unexpected native SLOPE trace schema")
        for row in rows:
            key=tuple(int(row[k]) for k in ("i","j","k"))
            if key in observed or key not in original:
                raise ValueError("Duplicated or unknown native grid/level record")
            observed.add(key)
            utc=datetime.fromtimestamp(int(row["hour_end_utc_seconds"]),timezone.utc)
            if utc.isoformat()!="2022-06-01T02:00:00+00:00":
                raise ValueError("SLOPE original/source model clock disagreement")
            land,ref_u,ref_v=original[key]
            if int(row["landuse"])!=land:
                raise ValueError("Real original/native LU categories disagree")
            typ="water" if 50<=land<=55 else "land"
            per[typ]["cells"]+=1
            for label,ref in (("u",ref_u),("v",ref_v)):
                current=float(row[f"post_slope_{label}_mps"])
                if not math.isfinite(current):
                    raise ValueError("Native nonfinite post SLOPE")
                error=abs(current-ref)
                per[typ]["comparisons"]+=1
                per[typ]["max_abs_mps"]=max(per[typ]["max_abs_mps"],error)
                if error>maxima[label]["max_abs_mps"]:
                    maxima[label]={"max_abs_mps":error,"cell":list(key)}
                if error>WIND_ABS_MPS and len(fails)<40:
                    fails.append({"cell":list(key),"field":label,
                                  "original":ref,"native":current,"abs_error":error})
    if len(observed)!=n or per["water"]["cells"]!=63*NZ or per["land"]["cells"]!=6907*NZ:
        raise ValueError("Genuine mixed land/water 6970x9 original/native coverage drift")
    result={
        "status":"PASS_SOURCE_NATIVE_REAL_FIRSTHOUR_POST_SLOPE"
                  if not fails else "FAIL_SOURCE_NATIVE_REAL_FIRSTHOUR_POST_SLOPE",
        "original_vendor_git_blob":BLOB,
        "pristine_original_6h_45_sha256":sha(baseline_met),
        "instrumented_original_6h_45_sha256":sha(scratch_met),
        "byte_identical_original_six_hour_output":True,
        "native_original_comparisons":2*n,
        "per_type":per,
        "max_abs":maxima,
        "frozen_abs_limit_mps":WIND_ABS_MPS,
        "exceedance_samples":fails,
        "p5_wind_missing_calm":"UNCHANGED",
        "native_final_g24_wind":"NOT_RUN",
        "native_g14_6h_comp":"NOT_RUN",
        "native_g26_6h_45fields":"NOT_ACCEPTED",
        "p7":"NOT_ACCEPTED"
    }
    report.parent.mkdir(parents=True,exist_ok=True)
    report.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print("S4R1C6_POST_SLOPE_RESIDUALS",json.dumps(maxima,sort_keys=True))
    if fails:
        raise ValueError("G47 real-original post-SLOPE numeric threshold exceeded")
    print("S4R1C6_REAL_NOAA_FIRSTHOUR_9_LEVEL_SLOPE_ORIGINAL_NATIVE=PASS_SCOPED")
    print("S4R1C6_UNMODIFIED_ORIGINAL_6H45_MET=BYTE_IDENTICAL")
    print("S4R1C6_G23_G24_G26_P7=NOT_ACCEPTED")

def main()->None:
    parser=argparse.ArgumentParser()
    sub=parser.add_subparsers(dest="command",required=True)
    a=sub.add_parser("prepare")
    for key in ("vendor","dest","receipt"):
        a.add_argument("--"+key,required=True,type=Path)
    v=sub.add_parser("verify")
    for key in ("vendor","baseline-met","scratch-met","original-trace","native-csv","report"):
        v.add_argument("--"+key,required=True,type=Path)
    args=parser.parse_args()
    if args.command=="prepare":
        prepare(args.vendor,args.dest,args.receipt)
    else:
        verify(args.vendor,args.baseline_met,args.scratch_met,
               args.original_trace,args.native_csv,args.report)
if __name__=="__main__":main()
