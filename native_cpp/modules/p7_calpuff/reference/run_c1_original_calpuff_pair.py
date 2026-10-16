#!/usr/bin/env python3
"""C1 A/C: identical vendor CALPUFF on original and real PR53 native MET.DAT.

B was separately proven by P7's immutable strict 143h gate. D (native P7 on
PR53 weather) is NOT computed by this script and must never be marked PASS.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile
import time

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import compare_p7_hourly_concentrations as fields

def main()->int:
    p=argparse.ArgumentParser(description=__doc__)
    for arg in ("vendor","puff_control","original_met","native_met","original_puff_con","p6_helper","out"):
        p.add_argument("--"+arg.replace("_","-"),required=True,type=Path)
    p.add_argument("--compiler",default="gfortran-11")
    p.add_argument("--hours",type=int,default=143)
    a=p.parse_args()
    if a.hours!=143:
        raise ValueError("C1 source frozen scientific case MUST use all 143 hours")
    a.out.mkdir(parents=True,exist_ok=True)
    sys.path.insert(0,str(a.p6_helper.resolve().parent))
    import verify_original_calpuff_reads_written_calmet as legacy
    if a.p6_helper.resolve().name!="verify_original_calpuff_reads_written_calmet.py":
        raise ValueError("wrong PR53 original CALPUFF helper path")
    if not all(x.is_file() for x in (a.puff_control,a.original_met,a.native_met,a.original_puff_con)):
        raise FileNotFoundError("missing full original/native inputs or frozen oracle")
    frozen_sha=fields.sha256(a.original_met)
    if frozen_sha!="b1823cda92280888d70b00961ab39486036a3086e18637fff21efb4f4b237d30":
        raise ValueError("C1 original frozen CALMET.DAT SHA256 changed")
    provenance={
        "scope":"C1_V1_VENDOR_A_C_SCIENCE_AND_P7_B_HISTORICAL_REFERENCE_ONLY",
        "p6_branch_head":"8d6642272d0abb77153880591e150f93e14d4479",
        "p6_artifact_run_id":38417406969,
        "p6_artifact_name":"p6-causal-original-case-143h",
        "original_met_sha256":frozen_sha,
        "native_met_sha256":fields.sha256(a.native_met),
        "source_deck_sha256":fields.sha256(a.puff_control),
        "p7_native_B_historical_science_run":38699935854,
        "P7_native_D":"NOT_RUN; cannot claim coupled native P7 integration acceptance",
    }
    with tempfile.TemporaryDirectory(prefix="cteas-p7-c1-") as temp:
        root=Path(temp)
        build=legacy.build_original(a.vendor.resolve(),a.compiler,root/"build")
        provenance["original_calpuff_binary_sha256"]=build["binary_sha256"]
        for name,weather in (("A",a.original_met),("C",a.native_met)):
            stage=root/name
            stage.mkdir()
            working=legacy.stage(stage,a.puff_control,weather.read_bytes())
            execution=legacy.execute(working,Path(build["binary_path"]),1800)
            result=legacy.require_clean_run(execution,name,143)
            shutil.copy2(execution["concentration"],a.out/f"{name}-original-calpuff.con")
            (a.out/f"{name}-vendor-stdout.log").write_text(execution["stdout"])
            provenance[name]={"weather_sha256":fields.sha256(weather),
                               "calpuff_sha256":fields.sha256(a.out/f"{name}-original-calpuff.con"),
                               "vendor_hours":result["hours"],
                               "last_hour":result["last_hour"]}
    ref=fields.read_fields(a.original_puff_con,50,50,143)
    out_a=fields.read_fields(a.out/"A-original-calpuff.con",50,50,143)
    out_c=fields.read_fields(a.out/"C-original-calpuff.con",50,50,143)
    a_check=fields.compare(ref,out_a,50,50)
    if not a_check["bitwise_identical"]:
        raise ValueError("original ref CALPUFF A no longer reproduces pinned H-3 REAL4 output")
    provenance["A_original_baseline_vs_rerun"]={
        "matching_real4":a_check["matching_real4"],
        "expected_real4":a_check["values"],
        "bitwise_identical":True,
    }
    science=fields.compare(out_a,out_c,50,50)
    science["original_met_sha256"]=frozen_sha
    science["native_met_sha256"]=provenance["native_met_sha256"]
    science["p7_D_status"]="BLOCKED_NEEDS_NATIVE_P7_NONFROZEN_INPUT_ADAPTER"
    (a.out/"C1-vendor-A-vs-C-science.json").write_text(json.dumps(science,indent=2)+"\n")
    (a.out/"C1-provenance.json").write_text(json.dumps(provenance,indent=2)+"\n")
    print(f"P7_C1_VENDOR_A=PASS ORIGINAL_REFERENCE_REAL4={a_check['matching_real4']}/{a_check['values']}")
    print(f"P7_C1_VENDOR_C=PASS NATIVE_P6_MET_HOURS=143 REAL4_A_C={science['matching_real4']}/{science['values']}"
          f" MAX_ABS={science['max_absolute_difference_bq_m3']}")
    print("P7_C1_FOUR_ARM_ACCEPTANCE=OPEN REQUIRES_NATIVE_P7_ON_PR53_MET_AND_FOUR_WAY_COMPARISON")
    return 0

if __name__=="__main__":
    try:raise SystemExit(main())
    except (ValueError,RuntimeError,FileNotFoundError) as e:
        print("P7_C1_VENDOR_PAIR_BLOCKED "+str(e),file=sys.stderr)
        raise SystemExit(1)
