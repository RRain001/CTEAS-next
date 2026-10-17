#!/usr/bin/env python3
"""Evidence-only 143h U/V/W field delta: original SIMILT station EL/ZII feed.

Do not confuse a forensic original-state-fed candidate with autonomous native
CALMET. This report quantifies how much the specified original state changes
reconstructed P6D U/V/W errors, keeping original acceptance tolerances.
"""
from __future__ import annotations
import argparse
import json
import math
from pathlib import Path


def fields(data: dict) -> dict:
    return {row["label"]:row for row in data["field_table"]["aux_reconstructed_calmet_dat"]}


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--baseline",type=Path,required=True)
    ap.add_argument("--intervention",type=Path,required=True)
    ap.add_argument("--out",type=Path,required=True)
    args=ap.parse_args()
    base=json.loads(args.baseline.read_text())
    obs=json.loads(args.intervention.read_text())
    if (base["reference"]["met_dat_sha256"]!=obs["reference"]["met_dat_sha256"]
            or base["reference"]["intervals"]!=143
            or obs["reference"]["intervals"]!=143
            or obs.get("forensic_original_similt_station",{}).get("mode")
               !="ORIGINAL_FORTRAN_SIMILT_ZII_EL_REFERENCE_ONLY"):
        raise SystemExit("forensic ZII/EL source or reference mismatch")
    b=fields(base);o=fields(obs)
    if b.keys()!=o.keys():
        raise SystemExit("per-field schema mismatch")
    comparison=[]
    better=worse=unchanged=0
    for label in sorted(b):
        if not (label.startswith("U-LEV") or label.startswith("V-LEV") or
                label.startswith("WFACE")):
            continue
        p,q=b[label],o[label]
        count_p,count_q=int(p["exceedances"]),int(q["exceedances"])
        if count_q<count_p:better+=1
        elif count_q>count_p:worse+=1
        else:unchanged+=1
        comparison.append({
            "field":label,
            "before":p["verdict"],"after":q["verdict"],
            "before_max_abs":p["max_abs_error"],
            "after_max_abs":q["max_abs_error"],
            "before_exceedances":count_p,
            "after_exceedances":count_q,
            "exceedance_delta":count_q-count_p,
        })
    if len(comparison)!=27:
        raise SystemExit(f"expected exactly 27 U/V/W field groups, got {len(comparison)}")
    result={
        "status":"PASS_DIAGNOSTIC_REPORT_NOT_P6D_ACCEPTANCE",
        "native_cpp_p6d_full_acceptance":False,
        "source_forcing":"original Fortran ELUSTR2 MIXHTST -> SIMILT station ZII,EL REAL4",
        "baseline_scientific_verdict":base["status"],
        "original_state_intervention_scientific_verdict":obs["status"],
        "improved_field_count":better,"worsened_field_count":worse,
        "unchanged_field_count":unchanged,
        "field_table":comparison,
    }
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps(result,indent=2))


if __name__=="__main__":
    main()
