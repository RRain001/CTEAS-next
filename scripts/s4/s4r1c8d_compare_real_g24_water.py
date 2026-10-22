#!/usr/bin/env python3
"""Independent genuine NOAA native G24->WATER G37/G35/G36 against original.

The original 6-hour S4N WATER trace is never passed to any native C++ CLI.
Source-pristine original MET.DAT must be byte-identical to trace-enabled MET.
This is only first-hour, selected NOWSTA=0 neutral WATER physics.
"""
from __future__ import annotations
import argparse,csv,hashlib,json,math
from collections import defaultdict
from pathlib import Path
from scripts.s4.s4n_real_water_63cells_original_probe import FIELDS,HOURS,sha

NX,NY=82,85
SCHEMA=("i","j","landuse","ws10","fcori","z0","ustar","el",
        "zi","zimech","ziconv","zicold","qh","wstar","wt","pgt")
def near(a:float,b:float,atol:float,rtol:float)->bool:
    return abs(a-b)<=atol+rtol*max(abs(a),abs(b))
TOL={
    "ws10":(2e-4,0.),
    "z0":(1e-10,8e-6),
    "ustar":(2e-8,5e-5),
    "el":(2048.,0.),
    "zi":(5e-3,5e-5),
    "qh":(1e-7,0.),
    "wstar":(1e-7,0.),
    "wt":(1e-7,0.),
}
def compare(original:Path,receipt:Path,native:Path,native_log:Path,report:Path)->bool:
    doc=json.loads(receipt.read_text())
    if(doc.get("status")!=
            "S4N_ACTUAL_VENDOR_63_WATER_CELLS_SIX_HOURS_NEUTRAL_WATER_VALUES_PASS_SCOPED_ORIGINAL_ONLY"
       or doc.get("original_water_cell_hour_records")!=378
       or doc.get("original_instrumented_calmet_sha256")!=
          doc.get("original_uninstrumented_calmet_sha256")
       or doc.get("water_grid_cells")!=63):
        raise ValueError("G53 requires independently accepted real original six-hour WATER reference")
    if ("S4R1C8D_REAL_NOAA_G24_TO_WATER=PRODUCED_UNVERIFIED" not in
            native_log.read_text() or
        "ORIGINAL_WIND_INJECTION=FALSE" not in native_log.read_text()):
        raise ValueError("G53 real original-free native computation gate absent")
    actual=defaultdict(dict)
    for line in original.read_text().splitlines():
        z=line.split()
        if len(z)!=13:raise ValueError("G53 original WATER trace schema changed")
        i,j,h,lu,pgt=map(int,z[:5])
        if not(1<=i<=NX and 1<=j<=NY and 50<=lu<=55 and pgt==4):
            raise ValueError("G53 original water GEO/PGT drift")
        fields=dict(zip(FIELDS,(float(v.replace("D","E")) for v in z[5:])))
        if not all(math.isfinite(x) for x in fields.values()) or (i,j) in actual[h]:
            raise ValueError("G53 original WATER duplicate/nonfinite cell")
        actual[h][i,j]={"landuse":lu,"pgt":pgt,**fields}
    if len(actual)!=HOURS or any(len(v)!=63 for v in actual.values()):
        raise ValueError("G53 original six genuine water hour trace incomplete")
    if any(set(a)!=set(next(iter(actual.values()))) for a in actual.values()):
        raise ValueError("G53 original water GEO changed across time")
    first=actual[min(actual)]
    candidate={}
    with native.open(newline="") as f:
        r=csv.DictReader(f)
        if tuple(r.fieldnames or [])!=SCHEMA:
            raise ValueError("G53 native raw WATER schema drift")
        for z in r:
            i,j=int(z["i"]),int(z["j"])
            if(i,j) in candidate or (i,j) not in first:
                raise ValueError("G53 native WATER wrong, repeated or foreign GEO cell")
            if int(z["landuse"])!=first[i,j]["landuse"]:
                raise ValueError("G53 native WATER land-use changed")
            d={k:float(z[k]) for k in SCHEMA[3:-1]}
            d["pgt"]=int(z["pgt"])
            if not all(math.isfinite(v) for v in d.values()):
                raise ValueError("G53 native WATER nonfinite")
            candidate[i,j]=d
    if set(candidate)!=set(first):
        raise ValueError("G53 native WATER missing original cell")
    fields={}
    violations=[]
    for key,(atol,rtol) in TOL.items():
        diffs=[]
        count=0
        worst=None
        for (i,j),ref in first.items():
            a=ref[key];b=candidate[i,j][key]
            delta=abs(a-b)
            diffs.append(delta)
            if not near(a,b,atol,rtol):
                count+=1
                if len(violations)<15:
                    violations.append({"field":key,"i":i,"j":j,
                                       "original":a,"native":b,"diff":delta})
            if worst is None or delta>worst["abs_diff"]:
                worst={"i":i,"j":j,"original":a,"native":b,"abs_diff":delta}
        fields[key]={"max_abs":max(diffs),"mean_abs":sum(diffs)/63,
                     "abs_tolerance":atol,"rel_tolerance":rtol,
                     "above_tolerance":count,"worst":worst}
    for (i,j),row in candidate.items():
        if (row["pgt"]!=4 or row["ziconv"]!=0 or row["zicold"]!=0 or
            row["zimech"]<0 or row["fcori"]<2.5e-5):
            violations.append({"field":"native_source_contract","i":i,"j":j})
    # Count all actual exceedances; diagnostic violation listing may be capped.
    nbad=sum(v["above_tolerance"] for v in fields.values())+sum(
        v.get("field")=="native_source_contract" for v in violations)
    result={
        "status":"PASS_SCOPED_REAL_NOAA_G24_NATIVE_WATER_NEUTRAL" if nbad==0
                 else "FAIL_NUMERIC_REAL_NOAA_G24_NATIVE_WATER_NEUTRAL",
        "source_scope":"FIRSTHOUR_63_GENUINE_WATER_CELLS_NOWSTA0",
        "source_original_trace_sha256":sha(original),
        "native_candidate_sha256":sha(native),
        "original_6h45_met_byte_identical":True,
        "source_previous_numeric_original_fields_injected_to_cpp":False,
        "water_cells":63,"original_hours":6,
        "numeric_field_comparisons":63*len(TOL),
        "g24_driven_g37_g35_g36":True,
        "fields":fields,"above_tolerance":nbad,
        "first_violations":violations[:15],
        "g26_land_mixht_avemix":"NOT_ACCEPTED",
        "g26_45field_sixhour":"NOT_ACCEPTED",
        "p7":"NOT_ACCEPTED",
    }
    report.parent.mkdir(parents=True,exist_ok=True)
    report.write_text(json.dumps(result,sort_keys=True,indent=2)+"\n")
    print("S4R1C8D_ORIGINAL_NATIVE_WATER="+result["status"])
    print("S4R1C8D_ABOVE_TOLERANCE="+str(nbad))
    print("S4R1C8D_MAX_RESIDUALS="+json.dumps(
        {k:v["max_abs"] for k,v in fields.items()},sort_keys=True))
    print("S4R1C8D_G26_P7=NOT_ACCEPTED")
    return nbad==0
def main()->None:
    p=argparse.ArgumentParser()
    for k in ("original","receipt","native","native-log","report"):
        p.add_argument("--"+k,type=Path,required=True)
    a=p.parse_args()
    if not compare(a.original,a.receipt,a.native,a.native_log,a.report):
        raise SystemExit(3)
if __name__=="__main__":main()
