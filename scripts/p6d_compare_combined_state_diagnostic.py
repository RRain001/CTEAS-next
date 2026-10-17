#!/usr/bin/env python3
"""Direct frozen CALMET 143h original-state combination residual analysis.

Compares exactly the same P6D/P6F/P6E C++ binaries after applying original
WINDBC boundary-source correction under three state configurations:
  A: unassisted original C++ state
  B: source-exact original ELUSTR2 ZII+EL station states
  C: original ZII+EL plus original pre-FRADJ gridded GAMMA.

All reference field tolerances stay unchanged. The purpose is identifying
remaining *native* state-production requirements, not qualifying use of
Fortran state files in a standalone native CALMET.
"""
import argparse
import json
from pathlib import Path


def get_fields(data):
    return {x["label"]:x for x in data["field_table"]["aux_reconstructed_calmet_dat"]
            if x["label"].startswith(("U-LEV","V-LEV","WFACE"))}


def main():
    p=argparse.ArgumentParser()
    for k in ("baseline","zii-el","zii-el-gamma","out"):
        p.add_argument("--"+k,type=Path,required=True)
    a=p.parse_args()
    reports={n:json.loads(f.read_text()) for n,f in (
        ("native",a.baseline),
        ("zii_el",a.zii_el),
        ("zii_el_gamma",a.zii_el_gamma)
    )}
    source=reports["native"]["reference"]["met_dat_sha256"]
    if any(x["reference"]["met_dat_sha256"]!=source or
           x["reference"]["intervals"]!=143 or
           x["reference"]["cells"]!=2500 for x in reports.values()):
        raise SystemExit("source reference differs across diagnostic arms")
    for arm in ("zii_el","zii_el_gamma"):
        x=reports[arm].get("forensic_original_similt_station",{})
        if x.get("mode")!="ORIGINAL_FORTRAN_SIMILT_ZII_EL_REFERENCE_ONLY":
            raise SystemExit(f"{arm}: missing original ZII+EL station SHA source proof")
    if reports["zii_el_gamma"].get("forensic_original_gamma",{}).get("mode")!=(
            "SOURCE_TRACED_ORIGINAL_REAL4_DIAGNOSTIC_ONLY"):
        raise SystemExit("full forensic arm missing original gridded GAMMA proof")
    a0={n:get_fields(x) for n,x in reports.items()}
    if any(set(d)!=set(a0["native"]) for d in a0.values()) or len(a0["native"])!=27:
        raise SystemExit("frozen 27-field U/V/W per-level schema changed")
    stats={}
    for arm,d in a0.items():
        stats[arm]={
            "passing":sum(x["verdict"]=="PASS" for x in d.values()),
            "failed":sum(x["verdict"]=="FAIL" for x in d.values()),
            "not_produced":sum(x["verdict"]!="PASS" and x["verdict"]!="FAIL"
                                for x in d.values())
        }
    rows=[]
    for field in sorted(a0["native"]):
        selected={arm:a0[arm][field] for arm in a0}
        rows.append({
            "field":field,
            "reference_intervals":143,
            "verdicts":{arm:val["verdict"] for arm,val in selected.items()},
            "max_abs_error":{arm:val["max_abs_error"] for arm,val in selected.items()},
            "exceedances":{arm:int(val["exceedances"]) for arm,val in selected.items()},
            "source_zii_el_delta":int(selected["zii_el"]["exceedances"])-
                                  int(selected["native"]["exceedances"]),
            "additional_original_gamma_delta":int(
                                  selected["zii_el_gamma"]["exceedances"])-
                                  int(selected["zii_el"]["exceedances"]),
        })
    result={
        "status":"PASS_THREE_ARM_FORENSIC_COMPLETENESS_ONLY",
        "original_CALMET_met_dat_sha256":source,
        "original_WINDBC_boundary_source_corrected_in_all_arms":True,
        "original_sourced_inputs_NOT_native_cpp":True,
        "unassisted_native_full_p6d_accepted":False,
        "numeric_gate_tolerance":"unchanged original P6E strict field-specific tolerance",
        "counts":stats,
        "fields":rows,
        "remaining_source_independent_physics":"ELUSTR2/MIXHTST hourly ZII,EL and PREPDI/GAMMA",
    }
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps({k:result[k] for k in (
        "status","counts","original_sourced_inputs_NOT_native_cpp",
        "unassisted_native_full_p6d_accepted")},indent=2))
    for v in rows:
        if any(x!="PASS" for x in v["verdicts"].values()):
            print(v["field"],v["verdicts"],v["max_abs_error"])
if __name__=="__main__":
    main()
