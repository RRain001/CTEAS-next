#!/usr/bin/env python3
"""Three-way source-authentic bisection of P6D FRADJ/SLOPE, 143 real hours.

Unchanged CALMET DIAGNO dumps:
  kpt=7: original USLOPE,VSLOPE immediately after SLOPE;
  kpt=8: original UG,VG immediately BEFORE SLOPE addition (after FRADJ);
  kpt=9: original UG,VG immediately AFTER the addition (before WINDBC).
The stand-alone native producer writes WIND1 and post-SLOPE. With no injected
GAMMA, native pre-SLOPE is WIND1; the difference at kpt8 is an acknowledged
missing FRADJ drive, not a numerical verdict on the FRADJ kernel itself.
The candidate slope increment is post-SLOPE minus its chosen pre-SLOPE state.
When feeding the original source GAMMA to the native FRADJ, the comparison
is oracle-input-scoped and can test physical FRADJ execution without claiming
native GAMMA production. We compare that
increment separately against ORIGINAL kpt7 to isolate SLOPE/QH/temperature
from upstream FRADJ without silently substituting any original state.

This diagnostic is not a P6D full-physics acceptance or a replacement for the
strict 27-field CALMET.DAT gate. No tolerances are relaxed.
"""
from __future__ import annotations
import argparse
import datetime as dt
import hashlib
import json
import math
import struct
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"native_cpp/modules/p6_calmet/reference"))
import original_internal_state_dump as dgm

NX=NY=50
NZ=9
N3=NX*NY*NZ
NH=143
ABS_TOL=1.e-4
REL_TOL=1.e-5
PAIRS=(("u","UG","USLOPE"),("v","VG","VSLOPE"))
STAGES=("pre_slope_after_original_FRADJ","slope_increment","post_slope")

def digest(path:Path)->str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for blob in iter(lambda:f.read(1024*1024),b""):
            h.update(blob)
    return h.hexdigest()

def native(path:Path)->tuple[float,...]:
    buf=path.read_bytes()
    if len(buf)!=N3*4:raise RuntimeError(f"wrong native field byte count: {path}")
    v=struct.unpack(f"<{N3}f",buf)
    if not all(math.isfinite(x) and abs(x)<999998 for x in v):
        raise RuntimeError(f"missing/nonfinite native wind: {path}")
    return v

def source(stream,rec):
    if (rec["nx"],rec["ny"],rec["nz"],rec["seconds"])!=(NX,NY,NZ,0):
        raise RuntimeError("source DIAGNO geometry/clock mismatch")
    stream.seek(rec["offset"]+32)
    raw=stream.read(N3*8)
    if len(raw)!=N3*8:raise RuntimeError("short original DIAGNO record")
    return (struct.unpack_from(f"<{N3}f",raw,0),
            struct.unpack_from(f"<{N3}f",raw,N3*4))

def new_stats():
    return {"compared":0,"exceedances":0,"max_abs_mps":0.,"sum_sq":0.,
            "worst":None,"per_level":{}}

def update(stats,ref,candidate,stage,axis,label,index):
    error=abs(ref-candidate)
    k=index//(NX*NY)+1
    entry=stats["per_level"].setdefault(str(k),
        {"compared":0,"exceedances":0,"max_abs_mps":0.})
    stats["compared"]+=1
    entry["compared"]+=1
    stats["sum_sq"]+=error*error
    if error>ABS_TOL+REL_TOL*abs(ref):
        stats["exceedances"]+=1
        entry["exceedances"]+=1
    entry["max_abs_mps"]=max(entry["max_abs_mps"],error)
    if error>stats["max_abs_mps"]:
        stats["max_abs_mps"]=error
        stats["worst"]={"hour_end":label,"axis":axis,"stage":stage,
            "i":index%NX+1,"j":index%(NX*NY)//NX+1,"k":k,
            "original":ref,"native":candidate,"abs_error_mps":error}

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--original-dir",required=True,type=Path)
    parser.add_argument("--candidate",required=True,type=Path)
    parser.add_argument("--pre-slope-prefix",choices=("wind1","fradj_corrected"),
                        default="wind1",
                        help="select native unassisted WIND1 or native FRADJ fed by pinned original GAMMA")
    parser.add_argument("--out",required=True,type=Path)
    args=parser.parse_args()
    proof=json.loads((args.original_dir/"dgm-audit.json").read_text())
    dump=args.original_dir/"case/run/met/dgm_fields.bin"
    if (proof.get("status")!="ORIGINAL_MET_DAT_IDENTICAL"
        or not proof.get("met_dat_identical")
        or not proof.get("met_dat_matches_frozen_reference")
        or proof.get("frozen_reference_sha256")!=dgm.TARGET_MET_DAT_SHA256
        or not dump.is_file()
        or proof["dumps"]["dgm_fields.bin"]["sha256"]!=digest(dump)):
        raise RuntimeError("non-original or non-byte-identical source evidence")
    records=dgm._walk_dump(dump)
    if len(records)!=NH*4 or [x["kpt"] for x in records]!=[7,8,9,10]*NH:
        raise RuntimeError("original 143h source stage order incomplete")
    hours=[(dt.datetime(2022,1,1)+dt.timedelta(hours=h+1))
            .strftime("%Y-%m-%d_%H") for h in range(NH)]
    if (args.candidate/"produced_hours.txt").read_text().split()!=hours:
        raise RuntimeError("candidate 143h UTC end labels mismatched")
    summaries={stage:{axis:new_stats() for axis,*_ in PAIRS}
               for stage in STAGES}
    source_addition_worst=0.
    source_addition_violations=0
    with dump.open("rb") as file:
        for h,label in enumerate(hours):
            hour_start=dt.datetime(2022,1,1)+dt.timedelta(hours=h)
            base=h*4
            snapshots=[source(file,records[base+k]) for k in range(3)]
            for k in range(3):
                rec=records[base+k]
                t=rec["packed"]
                stamp=dt.datetime(t//100000,1,1)+dt.timedelta(
                    days=(t//100)%1000-1,hours=t%100,seconds=rec["seconds"])
                if stamp!=hour_start:
                    raise RuntimeError(f"original source stage time drift kpt={k+7}, h={h+1}")
            for comp,(axis,_,__) in enumerate(PAIRS):
                candidate_initial=native(args.candidate/f"{args.pre_slope_prefix}_{axis}_{label}.f32")
                candidate_final=native(args.candidate/f"slope_corrected_{axis}_{label}.f32")
                source_slope=snapshots[0][comp]
                source_pre=snapshots[1][comp]
                source_post=snapshots[2][comp]
                for index in range(N3):
                    # Original source must satisfy its own kpt8+kpt7=kpt9
                    # to the same REAL*4 precision used by the numerical gate.
                    source_arithmetic=abs(
                        (source_pre[index]+source_slope[index])-source_post[index])
                    if source_arithmetic>source_addition_worst:
                        source_addition_worst=source_arithmetic
                    if source_arithmetic>ABS_TOL+REL_TOL*abs(source_post[index]):
                        source_addition_violations+=1
                    update(summaries[STAGES[0]][axis],source_pre[index],
                        candidate_initial[index],STAGES[0],axis,label,index)
                    update(summaries[STAGES[1]][axis],source_slope[index],
                        candidate_final[index]-candidate_initial[index],
                        STAGES[1],axis,label,index)
                    update(summaries[STAGES[2]][axis],source_post[index],
                        candidate_final[index],STAGES[2],axis,label,index)
    expected=NH*N3
    counts={}
    for stage,fields in summaries.items():
        counts[stage]={}
        for axis,stats in fields.items():
            if stats["compared"]!=expected:
                raise RuntimeError(f"incomplete {stage}/{axis} numerical comparison")
            stats["rms_mps"]=math.sqrt(stats.pop("sum_sq")/stats["compared"])
            counts[stage][axis]={"exceedances":stats["exceedances"],
                "max_abs_mps":stats["max_abs_mps"]}
    if source_addition_violations:
        raise RuntimeError(f"source arithmetic provenance failed in {source_addition_violations} cells")
    report={
        "status":"PASS_SOURCE_AUTHENTIC_FRADJ_SLOPE_BISECTION_COMPLETENESS",
        "scientific_verdict":"NOT_FULL_P6D_PARITY",
        "source_sha256":dgm.ORIGINAL_CALMET_SHA256,
        "original_reference_sha256":dgm.TARGET_MET_DAT_SHA256,
        "original_dgm_sha256":digest(dump),
        "hours":NH,"grid":[NX,NY,NZ],
        "values_compared":expected*2*len(STAGES),
        "native_FRADJ_status":(
            "original-GAMMA-driven native FRADJ (forensic/oracle-scoped)"
            if args.pre_slope_prefix=="fradj_corrected"
            else "NOT_NATIVE: missing CALMET PREPDI gridded GAMMA"),
        "candidate_pre_slope_prefix":args.pre_slope_prefix,
        "original_internal_slope_addition_max_error_mps":source_addition_worst,
        "original_internal_slope_addition_exceedances":source_addition_violations,
        "numerical_threshold":{"abs_mps":ABS_TOL,"relative":REL_TOL},
        "counts":counts,
        "fields":summaries,
        "interpretation":"kpt8 compares original post-FRADJ with native pre-FRADJ WIND1; kpt7 compares independently produced slope increments; kpt9 compares the actual corrected pre-WINDBC fields",
        "scope":"source authentic, identical frozen MET.DAT; forensic only; no injected oracle input; no automatic full CALMET acceptance"}
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps({"status":report["status"],"values":report["values_compared"],
        "source_addition_worst":source_addition_worst,"counts":counts},indent=2))
    print("P6D_143H_FRADJ_SLOPE_PHYSICS_BISECTION_ONLY; P6D_FULL_NOT_PASS")

if __name__=="__main__":
    main()
