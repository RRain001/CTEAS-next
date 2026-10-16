#!/usr/bin/env python3
"""Read a source-generated CTEAS P6F OUTHD using unchanged CALPUFF 7.2.1.

This is a reader/continuity/finite-concentration gate, NOT CALPUFF numeric
equivalence or evidence of generic P6F production independence. The input's
143 hourly fields were computed by native P6D/P6E; header/statics by GEO/deck.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path

from verify_original_calpuff_reads_written_calmet import (
    build_original, concentration_stats, execute, listing_evidence,
    require_clean_run, sha256_file, stage
)

def main() -> None:
    cli = argparse.ArgumentParser()
    cli.add_argument("--vendor",type=Path,required=True)
    cli.add_argument("--fortran",default="gfortran-11")
    cli.add_argument("--control",type=Path,required=True)
    cli.add_argument("--native-met",type=Path,required=True)
    cli.add_argument("--work",type=Path,required=True)
    cli.add_argument("--report",type=Path,required=True)
    args=cli.parse_args()
    if not args.native_met.is_file() or not args.control.is_file():
        raise SystemExit("FAIL_P6F_NATIVE_HEADER_MISSING_MET_OR_PUFF_CONTROL")
    args.work.mkdir(parents=True,exist_ok=True)
    original=build_original(args.vendor.resolve(),args.fortran,args.work/"compiler")
    met=args.native_met.read_bytes()
    runroot=args.work/"read_native"
    work=stage(runroot,args.control.resolve(),met)
    finished=execute(work,Path(original["binary_path"]),900)
    required=require_clean_run(finished,"P6F_INDEPENDENT_OUTHD",143)
    layout=listing_evidence(finished["listing"])
    values=concentration_stats(finished["concentration"])
    if values["values"]<=0 or values["nonzero"]<=0 or values["maximum"]<=0:
        raise RuntimeError("P6F_CALPUFF original did not produce finite positive nonzero data")
    result={
        "status":"PASS_P6F_UNMODIFIED_ORIGINAL_CALPUFF_READS_INDEPENDENT_OUTHD",
        "scope":"locked Hefei original CALPUFF 143-hour reader and nonzero finite concentration; not puff.con parity",
        "input_met_sha256":sha256_file(args.native_met),
        "original_calpuff":original,
        "run":required,
        "listing":layout,
        "concentration":values,
        "calpuff_physics_equivalence":"NOT_CLAIMED",
        "generic_P6F_acceptance":"NOT_CLAIMED"
    }
    args.report.parent.mkdir(parents=True,exist_ok=True)
    args.report.write_text(json.dumps(result,indent=2)+"\n")
    print(result["status"],"hours="+str(required["hours"]),
          "met="+result["input_met_sha256"][:16],
          "concentration_max="+str(values["maximum"]))

if __name__=="__main__":
    main()
