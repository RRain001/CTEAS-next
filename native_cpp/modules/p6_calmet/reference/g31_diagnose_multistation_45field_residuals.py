#!/usr/bin/env python3
"""G31C forensic ONLY: localize independent original-CALMET 45-field failure.

Numerical PASS/FAIL is owned exclusively by the frozen P6E G3/G4 comparator.
This tool consumes the *FAILED* frozen verdict and both separate actual
Fortran-record files, verifies the full comparator counts from the bytes,
then reports physical stage ownership and spatial/vertical error patterns.
It cannot override the scientific FAIL or modify a field/tolerance.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
import statistics
import struct
from collections import defaultdict
from pathlib import Path

from verify_g18c6_independent_binary import fortran_records
from verify_g30_source_p6f_candidate import LABELS,NX,NY,NZ

N=NX*NY

def read_grid(path:Path):
    raw=path.read_bytes()
    record=fortran_records(raw)
    if record[0][:16].decode("ascii").strip()!="CALMET.DAT" or record[0][16:32].decode("ascii").strip()!="2.1":
        raise ValueError("G31C expected original CALMET.DAT 2.1 binary")
    ncom=struct.unpack("<i",record[1])[0]
    if ncom<0 or ncom>10000:
        raise ValueError("G31C corrupt comment count")
    control=record[2+ncom]
    nx,ny,nz=struct.unpack_from("<3i",control,56)
    if (nx,ny,nz)!=(NX,NY,NZ):
        raise ValueError("G31C wrong source array dimensions")
    out={}
    for entry in record[3+ncom:]:
        if len(entry)!=24+N*4:
            continue
        label=entry[:8].decode("ascii")
        if label not in LABELS:
            continue
        if label in out:
            raise ValueError("G31C duplicate original hour field")
        if label in ("IPGT    ","IRH     "):
            out[label]=struct.unpack(f"<{N}i",entry[24:])
        else:
            out[label]=struct.unpack(f"<{N}f",entry[24:])
    if set(out)!=set(LABELS) or len(out)!=45:
        raise ValueError("G31C missing original 45-field source data")
    return out,hashlib.sha256(raw).hexdigest()

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--original",type=Path,required=True)
    p.add_argument("--candidate",type=Path,required=True)
    p.add_argument("--frozen-verdict",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    a=p.parse_args()
    verdict=json.loads(a.frozen_verdict.read_text())
    if verdict.get("status")!="FAIL_NUMERIC" or (
            verdict.get("fields_per_hour")!=45 or verdict.get("intervals")!=1):
        raise ValueError("G31C diagnostic requires actual failed frozen P6E original 45 field verdict")
    original,osh=read_grid(a.original)
    candidate,csh=read_grid(a.candidate)
    summaries=[]
    total=0
    group_exceeded=defaultdict(int)
    group_field_names=defaultdict(list)
    cell_overruns=[0]*N
    for source in verdict["fields"]:
        label=source["label"].ljust(8)
        ref=original[label]
        got=candidate[label]
        abs_lim=source["abs_limit"]
        rel_lim=source["rel_limit"]
        err=[abs(float(x)-float(y)) for x,y in zip(ref,got)]
        exceed=[i for i,e in enumerate(err) if e>abs_lim+rel_lim*abs(ref[i])]
        if len(exceed)!=int(source["exceedances"]):
            raise ValueError("G31C frozen verdict scalar mismatch for "+label)
        group=(
            "G23_G24_near_surface_UV" if label in ("U-LEV  1","V-LEV  1") else
            "G23_G24_upper_UV" if label.startswith(("U-LEV","V-LEV")) else
            "G24_W_vertical_integration" if label.startswith("WFACE") else
            "G18C3_TEMP3D_low_layers" if label.startswith("T-LEV") else
            "G18C5_surface_stability" if label=="IPGT" else
            "G22_surface_flux" if label in ("USTAR   ","EL      ","TEMPK   ","RHO     ","QSW     ") else
            "G28_G29_mixing_state" if label in ("ZI      ","WSTAR   ") else
            "G18C5_humidity" if label=="IRH     " else "other"
        )
        n=len(exceed)
        total+=n;group_exceeded[group]+=n
        group_field_names[group].append(label.strip())
        for i in exceed:cell_overruns[i]+=1
        kmax=max(range(N),key=lambda i:err[i])
        summaries.append({"label":label,"group":group,
                          "exceedances":n,
                          "max_abs_error":max(err),
                          "mean_abs_error":statistics.mean(err),
                          "rms_error":math.sqrt(statistics.mean(x*x for x in err)),
                          "worst_ij":[kmax%NX+1,kmax//NX+1],
                          "reference_at_worst":ref[kmax],
                          "candidate_at_worst":got[kmax]})
    if total!=int(verdict["total_exceedances"]):
        raise ValueError("G31C computed individual violations != P6E frozen total")
    wlabels=[f"WFACE{k:3d}" for k in range(1,NZ+1)]
    offsets=[[candidate[label][cell]-original[label][cell]
              for label in wlabels] for cell in range(N)]
    wspread=[max(d)-min(d) for d in offsets]
    const_count=sum(v<1.e-6 for v in wspread)
    uerr=[candidate["U-LEV  1"][i]-original["U-LEV  1"][i] for i in range(N)]
    verr=[candidate["V-LEV  1"][i]-original["V-LEV  1"][i] for i in range(N)]
    maxcell=max(range(N),key=lambda i:cell_overruns[i])
    report={"status":"DIAGNOSTIC_ONLY_NUMERIC_SCIENCE_FAIL_UNCHANGED",
            "frozen_comparator_status":"FAIL_NUMERIC",
            "original_vendor_sha256":osh,
            "native_candidate_sha256":csh,
            "total_scalar_checks":45*N,
            "total_exceedances":total,
            "frozen_accepted_tol_modified":False,
            "selected_2SS_2US_first_hour_only":True,
            "groups":[{"name":g,"exceedances":v,
                       "fraction_of_total":v/total if total else 0,
                       "fields":group_field_names[g]}
                      for g,v in sorted(group_exceeded.items(),
                                      key=lambda kv:-kv[1])],
            "per_field":summaries,
            "wface_1_to_9":{
                "cells_with_uniform_difference_under_1e-6":const_count,
                "max_vertical_spread_of_candidate_minus_original_mps":
                    max(wspread),
                "max_absolute_baseline_at_first_wface_mps":
                    max(abs(v[0]) for v in offsets)},
            "surface_UV":{
                "max_abs_u1_difference_mps":max(map(abs,uerr)),
                "max_abs_v1_difference_mps":max(map(abs,verr)),
                "uv_upper_levels_with_zero_exceedances":
                    all(not row["exceedances"] for row in summaries
                        if row["group"]=="G23_G24_upper_UV")},
            "spatial":{
                "cells_with_any_failed_fields":sum(c>0 for c in cell_overruns),
                "max_failed_fields_at_one_cell":max(cell_overruns),
                "most_failed_ij":[maxcell%NX+1,maxcell//NX+1],
                "failed_fields_per_cell":cell_overruns},
            "diagnosis_priority":[
                "P0: isolate original-vendor G23 INTER2 pre/post DIAGI first-layer SURF site winds and G24 U/V at level 1; avoid modifying frozen kernels",
                "P1: original-vendor versus native G24 WFACE vertical offset and boundary condition",
                "P2: original-vendor G18C5 PGTSTB stability assignment for source observation and cloud inputs",
                "P3: original-vendor G22 ELUSTR/HEATFX station/grid scalar inputs; downstream ZI/WSTAR/T-LEV errors may be consequences",
            ]}
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps({k:v for k,v in report.items() if k not in
          ("per_field","spatial")},indent=2))
    print("PASS_G31C_FORENSIC_ONLY: frozen SCIENCE FAIL preserved")
if __name__=="__main__":
    main()
