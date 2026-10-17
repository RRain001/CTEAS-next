#!/usr/bin/env python3
"""Report first *candidate* H1 receptor stage divergence from read-only traces.

Vendor/native event ordinal pairing is diagnostic, NOT a proof of matching
puff identity. A genuine physical fix requires puff-ID/KSAM provenance.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import struct

STAGES=[("frac","frec"),("sy","sy"),("sz","sz"),("zpr","zpr"),
        ("zrpole","zrpole"),("lid","lid"),("f1","f1"),("xi1","xi1"),("xi2","xi2"),
        ("t1","t1"),("t2","t2"),("qold","qold"),("qnew","qnew"),
        ("vdpvd","vdpvd"),("xtemp","xtemp"),("conc","conc")]

def load_native(path:Path):
    rows=[]
    for ln in path.read_text().splitlines():
        if not ln.startswith("P7_C2_NATIVE_RECEIVER "):
            continue
        vals={}
        for token in ln.split()[1:]:
            k,v=token.split("=",1)
            vals[k]=int(v) if k in ("puff","code") else float(v)
        if any(not math.isfinite(v) for v in vals.values()):
            raise ValueError("nonfinite native stage operand")
        rows.append(vals)
    if not rows:raise ValueError("no actual native CALCPF H1 receptor stages")
    return rows

def eq_real4(a,b):
    return struct.pack("<f",a)==struct.pack("<f",b)

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--vendor-json",required=True,type=Path)
    p.add_argument("--native-trace",required=True,type=Path)
    p.add_argument("--out",required=True,type=Path)
    args=p.parse_args()
    vendor=json.loads(args.vendor_json.read_text())
    if vendor.get("identical_complete_original_puff_con") is not True:
        raise ValueError("vendor source-stage trace did not prove original puff.con identity")
    vrows=vendor.get("rows") or []
    nrows=load_native(args.native_trace)
    report={
        "scope":"C2 H1 receptor (4,6), ORIGINAL MET, ORIGINAL CALPUFF vs native P7",
        "status":"READ_ONLY_FORENSICS_NOT_PHYSICAL_ACCEPTANCE",
        "vendor_binary_original_unchanged":True,
        "native_h1_trace_sha256":hashlib.sha256(args.native_trace.read_bytes()).hexdigest(),
        "vendor_events_h1":len(vrows),
        "native_events_h1":len(nrows),
        "event_ordinal_alignment":"UNPROVEN",
        "source_puff_ksam_alignment":"NOT_YET_INSTRUMENTED",
        "pairs":[],
    }
    total_equal=0
    for i,(v,n) in enumerate(zip(vrows,nrows),1):
        diffs=[]
        for native,vendor_name in STAGES:
            va=float(v[vendor_name])
            na=float(n[native])
            if not eq_real4(va,na):
                diffs.append({"stage":native,"vendor":va,"native":na,
                              "difference":na-va})
            else:total_equal+=1
        report["pairs"].append({
            "ordinal":i,"native_puff_id":n["puff"],
            "native_puff_code":n["code"],
            "first_difference":diffs[0] if diffs else None,
            "different_stage_count":len(diffs),
            "stage_differences":diffs,
        })
    report["count_of_bitwise_matching_stage_values"]=total_equal
    report["trace_pairs_compared"]=len(report["pairs"])
    report["candidate_first_difference"]=next(
        (x for x in report["pairs"] if x["first_difference"]),None)
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(report,indent=2)+"\n")
    v=report["candidate_first_difference"]
    print("P7_C2_H1_SOURCE_STAGE_TRACE=COMPLETE"
          f" VENDOR_EVENTS={len(vrows)} NATIVE_EVENTS={len(nrows)}"
          f" ORDINAL_ALIGNED=UNPROVEN FIRST_CANDIDATE={v and v['first_difference']}")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
