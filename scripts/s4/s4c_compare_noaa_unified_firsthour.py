#!/usr/bin/env python3
"""Independent original vs single-hour unified G14 WATER trial audit.

Reference original CALMET six-hour file is read ONLY by this offline audit,
never by the native actor. This does not accept production P6 or P7.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from pathlib import Path
from scripts.s4.s4r1c8i_compare_noaa_43_real_p6f import LABELS, NC, NX, NY, NZ, F32, INT, tol
from scripts.s4.s4r1c9ah_compare_hour6_p6f45 import read_hour


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def audit(original: Path, native: Path, original_sha: str,
          native_sha: str, report: Path) -> dict:
    if original.resolve() == native.resolve() or report.exists():
        raise ValueError("Original and native must differ; no overwrite of audit evidence")
    if digest(original) != original_sha or digest(native) != native_sha:
        raise ValueError("Original/native bytes not identical to frozen SHA256")
    reference=read_hour(original,6,0)
    candidate=read_hour(native,1,0)
    stats={}
    differences=[]
    failed=0
    bitwise=0
    for label in LABELS:
        a=reference[label]
        b=candidate[label]
        is_int=label in ("IPGT    ","IRH     ")
        floats=INT if is_int else F32
        va=floats.unpack(a)
        vb=floats.unpack(b)
        exact=sum(a[i:i+4]==b[i:i+4] for i in range(0,len(a),4))
        bitwise+=exact
        excess=0
        maximum=0.
        for k,(x,y) in enumerate(zip(va,vb,strict=True)):
            if not is_int and (not math.isfinite(x) or not math.isfinite(y)):
                raise ValueError("nonfinite real original/candidate data")
            delta=abs(x-y)
            maximum=max(maximum,delta)
            if (x!=y if is_int else delta>tol(label,x,y)):
                excess+=1
                if len(differences)<25:
                    differences.append({"field":label.strip(),"cell":[k%NX+1,k//NX+1],"abs_diff":delta})
        failed+=excess
        stats[label.strip()]={"count":NC,"equal_real4_words":exact,
                              "frozen_exceedances":excess,"max_abs":maximum}
    result={"status":"PASS_SCOPED_S4C_UNIFIED_FIRSTHOUR_FORTRAN_45" if failed==0
                     else "FAIL_S4C_UNIFIED_FIRSTHOUR_FORTRAN_45",
            "original_met_sha256":original_sha,"native_met_sha256":native_sha,
            "hour":"2022-06-01 01:00–02:00 UTC", "original_hours":6,
            "native_hours":1,"grid":[NX,NY,NZ],"stations":[2,1],
            "fields":45,"compared_values":45*NC,"bitwise_equal":bitwise,
            "frozen_exceedances":failed,"first_differences":differences,
            "field_details":stats,"generic_p6":"NOT_ACCEPTED",
            "cross_hour":"NOT_RUN","independent_science_review":"NOT_RUN"}
    report.write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    return result


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--original",type=Path,required=True)
    parser.add_argument("--native",type=Path,required=True)
    parser.add_argument("--original-sha256",required=True)
    parser.add_argument("--native-sha256",required=True)
    parser.add_argument("--report",type=Path,required=True)
    args=parser.parse_args()
    result=audit(args.original,args.native,args.original_sha256,args.native_sha256,args.report)
    print(result["status"],"values",result["compared_values"],
          "bitwise",result["bitwise_equal"],"exceedances",result["frozen_exceedances"])
    if result["frozen_exceedances"]:
        raise SystemExit(3)

if __name__=="__main__":
    main()
