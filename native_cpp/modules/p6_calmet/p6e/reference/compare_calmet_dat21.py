#!/usr/bin/env python3
"""CALMET.DAT 2.1 truth-comparison harness for the P6E micrometeorology chain.

    python3 compare_calmet_dat21.py \
        --reference project/cases/hefei5km_2022_reference_case_20261011/run/met/met.dat \
        --reference-sha256 b1823cda92280888d70b00961ab39486036a3086e18637fff21efb4f4b237d30 \
        --candidate <P6E-produced CALMET.DAT 2.1> --out stats.json

The frozen reference SHA-256 is mandatory: without it, or without the
reference file, or without a candidate, the harness reports an explicit
BLOCKED_* status and exits 3. It never reports a silent pass.

Exit codes: 0 PASS, 1 FAIL_NUMERIC, 2 FAIL_REFERENCE_SHA256 /
FAIL_LAYOUT, 3 BLOCKED_*.

At least one --reference or --candidate path must be supplied; when only the
reference is given the harness still validates its layout and prints the
per-field inventory together with the list of fields P6E does not implement.
"""
import argparse
import hashlib
import json
import pathlib
import subprocess
import sys
import tempfile

BLOCKED_REFERENCE_MISSING="BLOCKED_REFERENCE_MISSING"
BLOCKED_REFERENCE_SHA256_MISSING="BLOCKED_REFERENCE_SHA256_MISSING"
BLOCKED_CANDIDATE_MISSING="BLOCKED_CANDIDATE_MISSING"
FAIL_REFERENCE_SHA256="FAIL_REFERENCE_SHA256"
FAIL_LAYOUT="FAIL_LAYOUT"
BLOCKED_EXIT=3
LAYOUT_EXIT=2


def run_tool(tool,args):
    proc=subprocess.run([str(tool)]+[str(a) for a in args],
                        capture_output=True,text=True)
    return proc


def sha256_of(path):
    digest=hashlib.sha256()
    with open(path,"rb") as handle:
        for block in iter(lambda: handle.read(1<<20), b""):
            digest.update(block)
    return digest.hexdigest()


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--reference")
    parser.add_argument("--reference-sha256",default="")
    parser.add_argument("--candidate")
    parser.add_argument("--out")
    parser.add_argument("--tool",required=True)
    args=parser.parse_args()
    report={"reference":args.reference,"candidate":args.candidate,
            "reference_sha256_expected":args.reference_sha256 or None,
            "reference_sha256_observed":None,
            "tool":str(args.tool)}
    if not args.reference and not args.candidate:
        report["status"]="BLOCKED_NO_INPUTS"
        report["status_detail"]="neither --reference nor --candidate was supplied"
        emit(report,args.out)
        return BLOCKED_EXIT
    if args.reference:
        reference=pathlib.Path(args.reference)
        if not reference.is_file():
            report["status"]=BLOCKED_REFERENCE_MISSING
            report["status_detail"]="reference CALMET.DAT 2.1 file is absent"
            emit(report,args.out)
            return BLOCKED_EXIT
        if not args.reference_sha256:
            report["status"]=BLOCKED_REFERENCE_SHA256_MISSING
            report["status_detail"]=("no frozen --reference-sha256 was supplied; "
                                     "refusing to compare against an unpinned reference")
            emit(report,args.out)
            return BLOCKED_EXIT
        observed=sha256_of(reference)
        report["reference_sha256_observed"]=observed
        if observed!=args.reference_sha256.lower():
            report["status"]=FAIL_REFERENCE_SHA256
            report["status_detail"]=("reference SHA-256 does not match the frozen value: "
                                     +observed)
            emit(report,args.out)
            return LAYOUT_EXIT
        inventory=run_tool(args.tool,["check","--file",reference])
        if inventory.returncode!=0:
            report["status"]=FAIL_LAYOUT
            report["status_detail"]="reference layout rejected: "+inventory.stderr.strip()
            emit(report,args.out)
            return LAYOUT_EXIT
        report["reference_layout"]=json.loads(inventory.stdout)
        if not args.candidate:
            report["status"]=BLOCKED_CANDIDATE_MISSING
            report["status_detail"]=("reference is pinned and layout-validated, but no "
                                     "P6E-produced --candidate exists yet")
            emit(report,args.out)
            return BLOCKED_EXIT
    candidate=pathlib.Path(args.candidate)
    if not candidate.is_file():
        report["status"]=BLOCKED_CANDIDATE_MISSING
        report["status_detail"]="candidate CALMET.DAT 2.1 file is absent"
        emit(report,args.out)
        return BLOCKED_EXIT
    if not args.reference:
        report["status"]=BLOCKED_REFERENCE_MISSING
        report["status_detail"]=("only a candidate was supplied; the frozen reference "
                                 "and its SHA-256 are required for a truthful comparison")
        emit(report,args.out)
        return BLOCKED_EXIT
    comparison=run_tool(args.tool,["compare","--reference",args.reference,
                                   "--candidate",candidate])
    if comparison.returncode==3:
        report["status"]=FAIL_LAYOUT
        report["status_detail"]="candidate layout rejected: "+comparison.stderr.strip()
        emit(report,args.out)
        return LAYOUT_EXIT
    try:
        report["comparison"]=json.loads(comparison.stdout)
    except json.JSONDecodeError:
        report["status"]=FAIL_LAYOUT
        report["status_detail"]="comparator did not return JSON: "+comparison.stdout[:400]
        emit(report,args.out)
        return LAYOUT_EXIT
    report["status"]=report["comparison"]["status"]
    report["status_detail"]=report["comparison"]["status_detail"]
    emit(report,args.out)
    return 0 if report["status"]=="PASS" else 1


def emit(report,out):
    text=json.dumps(report,indent=2)+"\n"
    sys.stdout.write(text)
    if out:
        pathlib.Path(out).write_text(text)


if __name__=="__main__":
    sys.exit(main())
