#!/usr/bin/env python3
"""Independent selected 2022 original CALMET.DAT layout/C++ reader comparison.

Requires a real immutable original 2022 MET.DAT and a built C++ executable.
Uses P6's original Fortran OUTHD/OUTHR-grounded Python decoder snapshot
copied under reference/original_decode_calmet_hourly.py; no P6 branch checkout.
Comparing the same original input's decoded file structure is P7B I/O parity
only, NOT a native CALMET/CALPUFF atmospheric-solver parity claim.
"""
from __future__ import annotations
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile

def compare(met: Path, binary: Path, report_path: Path) -> dict:
    if not met.is_file() or not binary.is_file():
        raise FileNotFoundError("Explicit original MET.DAT and native inspector are required")
    original = Path(__file__).with_name("original_decode_calmet_hourly.py")
    with tempfile.TemporaryDirectory(prefix="p7-reference-") as t:
        expected_path = Path(t) / "original.json"
        subprocess.run([sys.executable,str(original),str(met),"--report",str(expected_path)],
                       check=True,capture_output=True,text=True)
        oracle=json.loads(expected_path.read_text())
    run=subprocess.run([str(binary),str(met),"--hefei-2022"],
                       check=True,capture_output=True,text=True)
    # The C++ inspector emits FIRST_UNIX_SEC=<n> END_UNIX_SEC=<n>
    # on one line. Each whitespace-delimited KEY=VALUE is independent.
    # Rejecting lines with multiple '=' dropped BOTH times and caused a
    # Python KeyError, although the original 2022 reader tests had passed.
    items=dict(token.split("=",1) for token in run.stdout.split()
               if token.count("=")==1)
    required=("P7B_CALMET21_FIELD_DECODE", "INTERVALS", "HOURLY_FIELDS",
              "FIRST_UNIX_SEC", "END_UNIX_SEC")
    missing=[key for key in required if key not in items]
    if missing:
        raise AssertionError("CALMET21 inspector missing keys: " +
                             ", ".join(missing) + "; stdout=" + repr(run.stdout[-500:]))
    if items.get("P7B_CALMET21_FIELD_DECODE")!="PASS":
        raise AssertionError("Native MET21 decode never returned PASS")
    if (int(items["INTERVALS"])!=oracle["actual_n_hour_intervals"] or
        int(items["HOURLY_FIELDS"])!=oracle["total_hourly_fields"]):
        raise AssertionError("Native and independent original record count disagree")
    original_start=datetime.datetime.fromisoformat(oracle["hour_interval_first"]).timestamp()
    original_end=datetime.datetime.fromisoformat(oracle["hour_interval_end"]).timestamp()
    if (int(items["FIRST_UNIX_SEC"])!=int(original_start) or
        int(items["END_UNIX_SEC"])!=int(original_end)):
        raise AssertionError("Original and C++ explicit timestamps mismatch")
    manifest={
        "gate":"P7B_SELECTED_HEFEI_2022_METDAT_IO_CONTRACT_PARITY",
        "status":"PASS",
        "not_a_solver_physics_test":True,
        "input_met_sha256":hashlib.sha256(met.read_bytes()).hexdigest(),
        "original_record_fields":oracle["total_hourly_fields"],
        "cpp_record_fields":int(items["HOURLY_FIELDS"]),
        "original_intervals":oracle["actual_n_hour_intervals"],
        "cpp_intervals":int(items["INTERVALS"]),
        "original_begin":oracle["hour_interval_first"],
        "original_end":oracle["hour_interval_end"],
        "cpp_stdout":run.stdout,
    }
    report_path.parent.mkdir(parents=True,exist_ok=True)
    report_path.write_text(json.dumps(manifest,indent=2)+"\n")
    return manifest

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--met",type=Path,required=True)
    ap.add_argument("--native-bin",type=Path,required=True)
    ap.add_argument("--report",type=Path,required=True)
    a=ap.parse_args()
    print(json.dumps(compare(a.met,a.native_bin,a.report),indent=2))
