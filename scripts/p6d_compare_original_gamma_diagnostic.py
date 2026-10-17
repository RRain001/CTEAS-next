#!/usr/bin/env python3
"""Report P6D original-FRADJ-GAMMA intervention vs identical no-GAMMA run.

Neither branch is allowed a scientific PASS unless the unchanged original
CALMET.DAT tolerance gates pass. The instrumented-GAMMA branch is explicitly
ORACLE-FED rather than a self-contained C++ CALMET reproduction.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path


def by_label(report: dict, group: str) -> dict:
    return {row["label"]: row for row in report["field_table"][group]}


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--baseline", type=Path, required=True)
    p.add_argument("--gamma", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    a=p.parse_args()
    b=json.loads(a.baseline.read_text())
    g=json.loads(a.gamma.read_text())
    for name,doc in (("baseline",b),("original_gamma",g)):
        if doc["reference"]["intervals"]!=143 or doc["reference"]["cells"]!=2500:
            raise SystemExit(f"{name}: invalid frozen baseline grid/hours")
    if b["reference"]["met_dat_sha256"]!=g["reference"]["met_dat_sha256"]:
        raise SystemExit("baseline/original-GAMMA interventions used different frozen met.dat")
    forensic=g.get("forensic_original_gamma",{})
    if forensic.get("mode")!="SOURCE_TRACED_ORIGINAL_REAL4_DIAGNOSTIC_ONLY":
        raise SystemExit("GAMMA intervention missing source-verified-forensic provenance")
    br=by_label(b,"aux_reconstructed_calmet_dat")
    gr=by_label(g,"aux_reconstructed_calmet_dat")
    if br.keys()!=gr.keys():
        raise SystemExit("field groups differ between baseline and GAMMA")
    changes=[]
    nbetter=nworse=0
    for name in sorted(br):
        old,new=br[name],gr[name]
        if not (name.startswith("U-LEV") or name.startswith("V-LEV")
                or name.startswith("WFACE")):
            continue
        old_count=int(old["exceedances"])
        new_count=int(new["exceedances"])
        if new_count<old_count:nbetter+=1
        elif new_count>old_count:nworse+=1
        changes.append({
            "field":name,
            "baseline_verdict":old["verdict"],
            "original_gamma_verdict":new["verdict"],
            "baseline_max_abs":old["max_abs_error"],
            "original_gamma_max_abs":new["max_abs_error"],
            "baseline_exceedances":old_count,
            "original_gamma_exceedances":new_count,
            "delta_exceedances":new_count-old_count,
        })
    if len(changes)!=27:raise SystemExit(f"need 27 U/V/W fields, got {len(changes)}")
    result={
        "status":"PASS_DIAGNOSTIC_COMPLETENESS_NOT_PHYSICS_CERTIFICATION",
        "scope":"143-hour original Fortran GAMMA source-forcing experiment only",
        "baseline_full_science_verdict":b["status"],
        "original_gamma_full_science_verdict":g["status"],
        "source_fed_not_native_cpp":True,
        "fields_improved_by_exceedance_count":nbetter,
        "fields_worsened_by_exceedance_count":nworse,
        "field_deltas":changes,
        "scientific_claim":"P6D_FULL_NOT_PASS unless complete unassisted 143h field gate passes",
    }
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps(result,indent=2))


if __name__=="__main__":
    main()
