#!/usr/bin/env python3
"""Forensic-only control for residual USTAR/EL/WSTAR after native 27/27 P6D PASS.

Both paths use the same real native P6D station ELUSTR2 CSV and the same
native P6E COMP code. Change ONLY 3D wind provenance:
 A = strictly native one-pass C++ P6D->P6E 143h candidate;
 B = original frozen CALMET.DAT wind used as a *control*, not as an output.
Neither B nor the frozen input may replace native A's accepted wind.
"""
from __future__ import annotations
import argparse
import json
import pathlib
import subprocess
import sys

THREE=("USTAR","EL","WSTAR")

def execute(command:list[object],log:pathlib.Path,allow_numeric_fail=False)->int:
    p=subprocess.run([str(x) for x in command],capture_output=True,text=True)
    log.write_text("exit="+str(p.returncode)+"\n"+p.stdout+"\n"+p.stderr)
    if p.returncode not in ((0,1) if allow_numeric_fail else (0,)):
        raise RuntimeError(f"scientific control did not run: {command[0]} {p.returncode}, {p.stderr[-1200:]}")
    return p.returncode

def main():
    arg=argparse.ArgumentParser()
    for flag in ("case","p6e","native","observations","station-flux","work"):
        arg.add_argument("--"+flag,required=True,type=pathlib.Path)
    a=arg.parse_args()
    work=a.work;work.mkdir(parents=True,exist_ok=True)
    original=a.case/"run/met/met.dat"
    geo=a.case/"geo/makegeo/geo.dat"
    controlled=work/"p6e_original_wind_control.dat"
    # This is a deliberate ONE-VARIABLE control. It must not feed native A.
    execute([a.p6e,"emit-realcase",
             "--reference",original,"--observations",a.observations,
             "--wind-file",original,"--geo-file",geo,
             "--station-flux-csv",a.station_flux,
             "--dptt-refresh",0,"--native-hour-comp",1,
             "--out",controlled],work/"original_wind_control.log")
    analyses=[]
    for role,file in (("native_wind",a.native),
                      ("original_wind_control",controlled)):
        verdict=work/f"{role}_comparison.json"
        rc=execute([a.p6e,"compare","--reference",original,
                    "--candidate",file,"--out",verdict],
                   work/f"{role}_compare.log",True)
        comparison=json.loads(verdict.read_text())
        rows={field["label"].strip():field for field in comparison["fields"]}
        analyses.append({
            "role":role,
            "comparator_status":comparison.get("status"),
            "return_code":rc,
            "three_fields":[{
                "label":name,
                "exceedances":rows[name]["exceedances"],
                "max_abs_error":rows[name]["max_abs_error"],
                "first_exceedances":rows[name]["first_exceedances"],
            }for name in THREE]
        })
    out={
        "scope":"diagnostic-only original-wind control (never native model output)",
        "case":"frozen 2022 Hefei 143h",
        "same_native_p6d_station_flux":True,
        "same_native_cpp_p6e_kernels":True,
        "changed_dimension":"U/V/W incoming provenance only",
        "physical_accreditation":"P6E_FULL_NUMERIC_NOT_ACCEPTED_UNTIL_3_FIELDS_PASS_WITH_NATIVE_WIND",
        "comparisons":analyses,
    }
    (work/"p6e_three_field_wind_control.json").write_text(
        json.dumps(out,indent=2)+"\n")
    print(json.dumps(out,indent=2))
    return 0

if __name__=="__main__":
    try:sys.exit(main())
    except Exception as err:
        print(f"P6E_3FIELD_FORENSIC_BLOCKED: {err}",file=sys.stderr)
        sys.exit(3)
