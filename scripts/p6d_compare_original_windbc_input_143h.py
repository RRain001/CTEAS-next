#!/usr/bin/env python3
"""Compare ACTUAL original DIAGNO post-SLOPE UG/VG lateral edges to C++ inputs.

CALMET calmet.for L5732 completes the SLOPE addition; L5748 snapshots UG/VG
using WINDBC before INTER2. Original DGM kpt=9 stores the same unchanged UG/VG.
This checks the *physical values* entering WINDBC, not only its call order.

The baseline C++ producer intentionally runs without original GAMMA/ZII/EL
injections, so failures are expected while upstream physics is incomplete.
A successful forensic workflow never means P6D_FULL=PASS.
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
import original_internal_state_dump as original

NX=NY=50
NZ=9
HOURS=143
CELLS=NX*NY*NZ
ABS_TOL=1.0e-4
REL_TOL=1.0e-5


def sha256(path:Path)->str:
    hasher=hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda:stream.read(1024*1024),b""):
            hasher.update(block)
    return hasher.hexdigest()


def read_field(path:Path)->tuple[float,...]:
    blob=path.read_bytes()
    if len(blob)!=CELLS*4:
        raise RuntimeError(f"invalid C++ field bytes: {path}: {len(blob)}")
    field=struct.unpack(f"<{CELLS}f",blob)
    if any(not math.isfinite(x) or abs(x)>=999998 for x in field):
        raise RuntimeError(f"invalid C++ field contents: {path}")
    return field


def main():
    cli=argparse.ArgumentParser()
    cli.add_argument("--original-dir",type=Path,required=True)
    cli.add_argument("--candidate",type=Path,required=True)
    cli.add_argument("--out",type=Path,required=True)
    a=cli.parse_args()

    proof_file=a.original_dir/"dgm-audit.json"
    proof=json.loads(proof_file.read_text())
    dump=a.original_dir/"case/run/met/dgm_fields.bin"
    if (not proof.get("met_dat_identical") or
        not proof.get("met_dat_matches_frozen_reference") or
        proof.get("frozen_reference_sha256")!=original.TARGET_MET_DAT_SHA256 or
        not dump.is_file() or
        proof["dumps"]["dgm_fields.bin"]["sha256"]!=sha256(dump)):
        raise RuntimeError("original Fortran DGM provenance/byte-equality proof failed")

    records=original._walk_dump(dump)
    if len(records)!=HOURS*4 or [x["kpt"] for x in records]!=[7,8,9,10]*HOURS:
        raise RuntimeError("original original DIAGNO 143h kpt7-10 sequence incomplete")

    stats={}
    def collect(axis,level,index,ref,value,hour,i,j):
        entry=stats.setdefault(axis,{"n":0,"failures":0,"max_abs_error_mps":0.0,
                                      "worst":None,"per_level":{}})
        one=entry["per_level"].setdefault(str(level),{"n":0,"failures":0,
                                                      "max_abs_error_mps":0.0})
        error=abs(ref-value)
        entry["n"]+=1
        one["n"]+=1
        if error>entry["max_abs_error_mps"]:
            entry["max_abs_error_mps"]=error
            entry["worst"]={"hour":hour,"i":i,"j":j,"k":level,
                            "original":ref,"native":value,"error_mps":error}
        one["max_abs_error_mps"]=max(one["max_abs_error_mps"],error)
        if error>ABS_TOL+REL_TOL*abs(ref):
            entry["failures"]+=1
            one["failures"]+=1

    candidate_hours=(a.candidate/"produced_hours.txt").read_text().split()
    expected_hours=[(dt.datetime(2022,1,1)+dt.timedelta(hours=i+1)).strftime("%Y-%m-%d_%H")
                    for i in range(HOURS)]
    if candidate_hours!=expected_hours:
        raise RuntimeError("C++ 143-hour labels do not match original interval-end order")

    with dump.open("rb") as stream:
        for hour_index in range(HOURS):
            record=records[hour_index*4+2]
            if (record["nx"],record["ny"],record["nz"],record["seconds"])!=(NX,NY,NZ,0):
                raise RuntimeError("original post-SLOPE record geometry/seconds mismatch")
            packed=record["packed"]
            year=packed//100000
            julian=(packed//100)%1000
            hour=packed%100
            source_begin=dt.datetime(year,1,1)+dt.timedelta(days=julian-1,hours=hour)
            expected_begin=dt.datetime(2022,1,1)+dt.timedelta(hours=hour_index)
            if source_begin!=expected_begin:
                raise RuntimeError(f"original DGM UTC begin-time drift at {hour_index+1}")
            label=expected_hours[hour_index]
            stream.seek(record["offset"]+32)
            source_u=struct.unpack(f"<{CELLS}f",stream.read(CELLS*4))
            source_v=struct.unpack(f"<{CELLS}f",stream.read(CELLS*4))
            native_u=read_field(a.candidate/f"slope_corrected_u_{label}.f32")
            native_v=read_field(a.candidate/f"slope_corrected_v_{label}.f32")
            for k in range(NZ):
                base=k*NX*NY
                for j in range(NY):
                    for i in (0,NX-1):
                        n=base+j*NX+i
                        collect("UB_WEST_EAST",k+1,n,source_u[n],native_u[n],label,i+1,j+1)
                for i in range(NX):
                    for j in (0,NY-1):
                        n=base+j*NX+i
                        collect("VB_SOUTH_NORTH",k+1,n,source_v[n],native_v[n],label,i+1,j+1)

    count=sum(stat["n"] for stat in stats.values())
    failures=sum(stat["failures"] for stat in stats.values())
    if count!=HOURS*NZ*2*(NY+NX):
        raise RuntimeError(f"lateral state comparison incomplete: {count}")
    report={
        "status":"PASS_SOURCE_LOCKED_BOUNDARY_FORENSIC_COMPLETENESS",
        "physical_parity":"PASS" if failures==0 else "FAIL_NUMERIC",
        "scientific_scope":"C++ native pre-INTER2 post-SLOPE first-guess lateral inputs versus unchanged Fortran UG/VG, not final wind",
        "original_fortran_met_dat_byte_identical":True,
        "original_windbc_stage":"calmet.for L5732 post-SLOPE UG/VG; WINDBC(UG,VG) L5748",
        "comparison":"143 hours x 9 levels x (2x50 U edges + 2x50 V edges)",
        "threshold_abs_mps":ABS_TOL,"threshold_rel":REL_TOL,
        "values_compared":count,"numeric_exceedances":failures,
        "by_edge":stats,"p6d_full_acceptance":False,
        "original_dump_sha256":sha256(dump),
        "cpp_producer":"unassisted native, no original ZII/EL/GAMMA injection",
    }
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(report,indent=2)+"\n")
    print("P6D_ORIGINAL_POST_SLOPE_WINDBC_INPUT="+report["physical_parity"])
    print(json.dumps({key:{"count":val["n"],"failures":val["failures"],
                           "max_abs":val["max_abs_error_mps"],"worst":val["worst"]}
                      for key,val in stats.items()},indent=2))
    print("P6D_SOURCE_BOUNDARY_FORENSIC_COMPLETENESS=PASS; P6D_FULL_NOT_PASS")


if __name__=="__main__":
    main()
