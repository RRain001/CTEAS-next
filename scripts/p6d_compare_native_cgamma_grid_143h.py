#!/usr/bin/env python3
"""Verify native P6E-ZICONV-driven CGAMMA against unchanged Fortran 143h GAMMA.

Source uses the pinned write-only original pre-FRADJ GAMMA trace and byte-
identical reference MET.DAT. Candidate is generated from native MIXHT/AVEMIX
ZICONV, CGammaState, and original UP.DAT observation data, never from source
GAMMA. Strict 3e-6 K/m threshold; forensic completion != physics success.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
import struct
from pathlib import Path

NH=143
NC=2500
TOL=3.e-6
REFERENCE_SHA="b1823cda92280888d70b00961ab39486036a3086e18637fff21efb4f4b237d30"

def sha(path:Path):
    h=hashlib.sha256()
    with path.open("rb") as f:
        for blob in iter(lambda:f.read(1024*1024),b""):
            h.update(blob)
    return h.hexdigest()

def read_f32(path:Path):
    raw=path.read_bytes()
    if len(raw)!=NC*4:
        raise RuntimeError(f"not 2500 REAL4 values: {path}")
    return struct.unpack("<2500f",raw)

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--original",required=True,type=Path,
                        help="source-pinned p6d_trace_original_gamma.py output directory")
    parser.add_argument("--native",required=True,type=Path)
    parser.add_argument("--out",required=True,type=Path)
    parser.add_argument("--require-numeric-parity",action="store_true")
    a=parser.parse_args()
    proof=json.loads((a.original/"gamma_source_manifest.json").read_text())
    if (proof.get("status")!="PASS_ORIGINAL_GAMMA_SOURCE_REAL4" or
        not proof.get("met_dat_byte_identical") or
        not proof.get("met_dat_matches_frozen_reference") or
        proof.get("reference_sha256")!=REFERENCE_SHA or
        proof.get("gamma",{}).get("hours")!=NH):
        raise RuntimeError("original GAMMA source chain-of-custody failed")
    provenance=json.loads((a.native/"native_cgamma_manifest.json").read_text())
    if (provenance.get("status")!="NATIVE_CGAMMA_P6E_ZICONV_143H_BRIDGE" or
        provenance.get("original_reference_injected") is not False or
        provenance.get("hours")!=NH or
        provenance.get("current_hour_leakage") is not False):
        raise RuntimeError("candidate gamma is not native P6E-driven")
    totals={"values":0,"exceedances":0,"max_abs_kpm":0.0,"rms_sum":0.0,
            "worst":None,"hours_failing":[]}
    hour_source=proof["gamma"]["records"]
    if len(hour_source)!=NH:
        raise RuntimeError("source GAMMA record count mismatch")
    expected=[r["hour"] for r in hour_source]
    if len(set(expected))!=NH:
        raise RuntimeError("source GAMMA clock duplicates")
    for n,label in enumerate(expected,1):
        src=a.original/"gamma"/f"gamma_{label}.f32"
        candidate=a.native/f"gamma_{label}.f32"
        if sha(src)!=hour_source[n-1]["sha256"]:
            raise RuntimeError("source real4 payload not byte-identical to source trace")
        values_ref=read_f32(src)
        values_new=read_f32(candidate)
        hourly=0
        for cell,(ref,v) in enumerate(zip(values_ref,values_new)):
            if not math.isfinite(ref) or not math.isfinite(v):
                raise RuntimeError("non-finite source/candidate gamma")
            delta=abs(ref-v)
            totals["values"]+=1
            totals["rms_sum"]+=delta*delta
            if delta>totals["max_abs_kpm"]:
                totals["max_abs_kpm"]=delta
                totals["worst"]={"hour_end":label,"i":cell%50+1,
                                 "j":cell//50+1,"original":ref,
                                 "native":v,"abs_error_kpm":delta}
            if delta>TOL:
                totals["exceedances"]+=1
                hourly+=1
        if hourly:totals["hours_failing"].append({"hour_end":label,"exceedances":hourly})
    if totals["values"]!=NH*NC:
        raise RuntimeError("gamma data incomplete")
    totals["rms_kpm"]=math.sqrt(totals.pop("rms_sum")/totals["values"])
    report={"status":"PASS_NATIVE_VS_ORIGINAL_GAMMA_FORENSIC_COMPLETENESS",
            "scientific_verdict":"PASS_NATIVE_GAMMA_143H" if totals["exceedances"]==0
                else "FAIL_NATIVE_GAMMA_143H",
            "comparison_tolerance_K_per_m":TOL,
            "reference_met_dat_sha256":REFERENCE_SHA,
            "original_source_instrumented_write_only":True,
            "native_original_gamma_injection":False,
            "native_p6e_internal_ziconv":True,
            "hourly_upstream_state":"previous-hour native P6E MIXHT/AVEMIX, current PREPDI CGAMMA",
            "qualified_scope":"one-upper-station 2022 gamma grid; not DIAGNO/P6D full parity",
            "counts":totals}
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps({k:report[k] for k in ("status","scientific_verdict","counts")},indent=2))
    if a.require_numeric_parity and totals["exceedances"]:
        raise SystemExit(1)

if __name__=="__main__":
    main()
