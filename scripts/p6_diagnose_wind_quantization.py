#!/usr/bin/env python3
"""Independent wind-input discontinuity audit for CALMET AVETMP/AVEMIX.

For the fixed 143h 50x50 Hefei case, compare native and original first-level
wind at *the integer/branch selection boundaries actually used* in
source-faithful AVETMP (INT of displacement, corner cone selection). Correlate
those branches with USTAR/EL/WSTAR errors, without modifying model physics,
injecting original wind, or relaxing any scientific tolerance.
"""
from __future__ import annotations
import argparse
from array import array
from collections import Counter
import json
import math
import pathlib
import subprocess
import sys

FIELDS = ("U-LEV  1", "V-LEV  1", "USTAR", "EL", "WSTAR")
TOL = {"USTAR": (3.e-5, 5.e-5), "EL": (0.04, 5.e-5),
       "WSTAR": (2.e-5, 3.e-5)}
NX = NY = 50
HOURS = 143

def single_float(x: float) -> float:
    # JSON reporter need not decide on source REAL*4; this cast only
    # mimics INT operand rounding in the diagnostic, not the solver.
    from struct import pack, unpack
    return unpack("<f", pack("<f", x))[0]

def dump(tool:pathlib.Path,source:pathlib.Path,field:str,work:pathlib.Path)->array:
    path=work/("native_" if source==dump.native else "original_")
    path=path/("_".join(field.split())+".f32")
    path.parent.mkdir(parents=True,exist_ok=True)
    p=subprocess.run([tool,"dump-field","--file",source,"--field",field,"--out",path],
                     capture_output=True,text=True)
    if p.returncode:
        raise RuntimeError(f"failed {source} {field}: {p.stderr[-600:]}")
    a=array("f")
    with path.open("rb") as handle:a.fromfile(handle,HOURS*NX*NY)
    if len(a)!=HOURS*NX*NY:raise RuntimeError("bad wind/field number of REAL*4 values")
    return a

def main()->int:
    cli=argparse.ArgumentParser()
    for name in ("tool","original","native","work"):
        cli.add_argument("--"+name,required=True,type=pathlib.Path)
    a=cli.parse_args()
    a.work.mkdir(parents=True,exist_ok=True)
    dump.native=a.native
    original={name:dump(a.tool,a.original,name,a.work) for name in FIELDS}
    native={name:dump(a.tool,a.native,name,a.work) for name in FIELDS}
    deg=single_float(0.01745329)
    tanang=single_float(math.tan(single_float(deg*single_float(30.))))
    dtdx=single_float(3600./100.)
    counts=Counter()
    exceed=Counter()
    hour_all=Counter()
    flips_hour=Counter()
    exceed_hours={field:Counter() for field in TOL}
    examples=[]
    max_u=max_v=0.
    wind_diff_quantiles=[]
    totals=NX*NY*HOURS
    for idx in range(totals):
        ru,rv=original["U-LEV  1"][idx],original["V-LEV  1"][idx]
        nu,nv=native["U-LEV  1"][idx],native["V-LEV  1"][idx]
        ud,vd=abs(ru-nu),abs(rv-nv)
        max_u,max_v=max(max_u,ud),max(max_v,vd)
        ra=single_float(ru*dtdx);rb=single_float(rv*dtdx)
        na=single_float(nu*dtdx);nb=single_float(nv*dtdx)
        old=(int(ra),int(rb),int(single_float(rb*tanang)),int(single_float(ra*tanang)))
        new=(int(na),int(nb),int(single_float(nb*tanang)),int(single_float(na*tanang)))
        crossed=old!=new
        if crossed:flips_hour[idx//2500+1]+=1
        counts["wind_displacement_integer_flip" if crossed else "same_integer_window"]+=1
        for k,key in enumerate(("ietax","ietay","icwx","icwy")):
            if old[k]!=new[k]:counts["flip_"+key]+=1
        errors=[]
        for name,(absolute,relative) in TOL.items():
            x,y=original[name][idx],native[name][idx]
            if abs(x-y)>absolute+relative*abs(x):
                exceed[name]+=1
                exceed_hours[name][idx//2500+1]+=1
                if crossed:exceed[name+"_with_integer_flip"]+=1
                errors.append(name)
        if crossed and errors and len(examples)<24:
            examples.append({"hour":idx//2500+1,"cell":idx%2500+1,
                "old_UV":[ru,rv],"new_UV":[nu,nv],
                "old_displacement_ints":old,"new_displacement_ints":new,
                "three_field_exceedances":errors})
        if errors and len(wind_diff_quantiles)<12:
            wind_diff_quantiles.append({"hour":idx//2500+1,
                "cell":idx%2500+1,"abs_U_delta":ud,"abs_V_delta":vd,
                "exceeded":errors,"branch_flip":crossed})
    comparison={
        "scientific_status":"FORENSIC_ONLY_NOT_ACCEPTANCE",
        "input":"Native C++ 143h CALMET.DAT and frozen CALMET 6.5 original",
        "grid":[143,50,50],"dx":100,"dtime":3600,
        "wind_max_delta_mps":{"U1":max_u,"V1":max_v},
        "avetmp_integer_shift_flips":dict(counts),
        "per_hour_flip_counts":dict(flips_hour.most_common(25)),
        "three_original_tolerance_exceedances":dict(exceed),
        "by_field_failure_hours":{k:dict(v.most_common(15))
                                  for k,v in exceed_hours.items()},
        "branch_flip_and_failure_examples":examples,
        "first_failure_wind_deltas":wind_diff_quantiles,
        "interpretation":"A flip in INT displacement/derived sector bounds is a discontinuous upwind-domain change. Even if no flips occur, other AVETMP bearing/distance selection and unstable ELUSTR may amplify sub-tolerance wind errors. This tool cannot prove which physics change is acceptable."
    }
    out=a.work/"p6e_source_quantization_diagnostic.json"
    out.write_text(json.dumps(comparison,indent=2)+"\n")
    print(json.dumps(comparison,indent=2))
    return 0

if __name__=="__main__":
    try:sys.exit(main())
    except Exception as e:
        print("P6E_INT_DISPLACEMENT_FORENSIC_FAIL: "+str(e),file=sys.stderr)
        sys.exit(3)
