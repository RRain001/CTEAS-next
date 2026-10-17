#!/usr/bin/env python3
"""Independent no-snow MAKEGEO 3.2 output field-by-field comparison.

This reader never invokes C++ and never changes reference data.
Checks exact class/terrain mask, fixed original F7.2/F7.4 rounding bounds.
"""
from __future__ import annotations
import argparse,csv,hashlib,json,math,re
from pathlib import Path

FIELD_SPECS=(
    ("category","LAND USE DATA",0.0),
    ("elevation_m","TERRAIN heights",0.0050001),
    ("z0_m","gridded z0 field",0.00005001),
    ("albedo","gridded albedo field",0.0050001),
    ("bowen","gridded Bowen ratio field",0.0050001),
    ("soil_heat","gridded soil heat flux parameters",0.0050001),
    ("anthropogenic_heat","gridded anthropogenic heat flux field",0.0050001),
    ("lai","gridded leaf area index field",0.0050001),
)

def sha(file):
    return hashlib.sha256(file.read_bytes()).hexdigest()

def parse_geo(file):
    lines=file.read_text().splitlines()
    if len(lines)<600 or lines[0].split()[:2]!=["GEO.DAT","2.1"]:
        raise ValueError("missing original MAKEGEO GEO.DAT v2.1")
    if lines[4].strip()!="UTM" or "50N" not in lines[5] or not lines[6].startswith("WGS-84"):
        raise ValueError("unexpected original GEO.DAT CRS")
    meta=lines[7].split()
    if len(meta)<6 or tuple(map(int,meta[:2]))!=(50,50):
        raise ValueError("GEO.DAT grid mismatch")
    marks=[]
    for name,label,_ in FIELD_SPECS:
        hit=[n for n,line in enumerate(lines) if label in line]
        if len(hit)!=1:raise ValueError(f"bad original GEO.DAT section {name}: {hit}")
        marks.append(hit[0])
    if marks!=sorted(marks):raise ValueError("GEO.DAT section order changed")
    out={}
    for index,(name,_,tolerance) in enumerate(FIELD_SPECS):
        a=marks[index]+(3 if name=="category" else 1)
        b=marks[index+1] if index+1<len(marks) else len(lines)
        block=lines[a:b]
        tokens=[token for line in block for token in line.replace(","," ").split()]
        if len(tokens)!=2500:raise ValueError(f"invalid original {name}: expected 2500, got {len(tokens)}")
        if name=="category":
            values=list(map(int,tokens))
        else:
            values=list(map(float,tokens))
            if not all(math.isfinite(v) for v in values):
                raise ValueError(f"non-finite original {name}")
        out[name]=[values[(49-j)*50+i] for j in range(50) for i in range(50)]
    return out

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--reference",required=True,type=Path)
    ap.add_argument("--cpp",required=True,type=Path)
    ap.add_argument("--cpp-geo",type=Path,help="independently produced no-snow GEO.DAT v2.1")
    ap.add_argument("--report",required=True,type=Path)
    a=ap.parse_args()
    original=parse_geo(a.reference)
    with a.cpp.open(newline="") as f:rows=list(csv.DictReader(f))
    cols=["i","j",*[name for name,_,_ in FIELD_SPECS]]
    if len(rows)!=2500 or list(rows[0])!=cols:
        raise ValueError(f"bad C++ shape or columns: {len(rows)} / {list(rows[0]) if rows else []}")
    metrics={}
    bad_total=0
    for name,_,tol in FIELD_SPECS:
        abs_errors=[];bad=[]
        for n,row in enumerate(rows):
            if (int(row["i"]),int(row["j"]))!=(n%50+1,n//50+1):
                raise ValueError("C++ row ordering mismatch")
            result=float(row[name])
            if not math.isfinite(result):raise ValueError(f"C++ nonfinite: {name}")
            err=abs(result-original[name][n])
            abs_errors.append(err)
            if err>tol:bad.append({"i":n%50+1,"j":n//50+1,
                                   "reference":original[name][n],"cpp":result,"abs_error":err})
        bad_total+=len(bad)
        metrics[name]={"cells":2500,"max_abs_error":max(abs_errors),
                       "mae":sum(abs_errors)/2500,
                       "rmse":math.sqrt(sum(e*e for e in abs_errors)/2500),
                       "predeclared_tolerance":tol,
                       "bad_cells":len(bad),"bad_first_20":bad[:20]}
    written_metrics={}
    if a.cpp_geo:
        generated=parse_geo(a.cpp_geo)
        for name,_,_ in FIELD_SPECS:
            errors=[abs(x-y) for x,y in zip(original[name],generated[name])]
            # Both files are already formatted at the same declared FORTRAN
            # precision, so this is intentionally an exact displayed-value gate.
            wrong=sum(e>0.0 for e in errors)
            bad_total+=wrong
            written_metrics[name]={"compared_cells":2500,"displayed_value_mismatch_count":wrong,
                                   "max_abs_error":max(errors)}
    result={"status":"PASS_SCOPED" if bad_total==0 else "FAIL",
            "model":"Original MAKEGEO v3.2 L110401 no-snow 100m Hefei",
            "original_geo_sha256":sha(a.reference),
            "cpp_csv_sha256":sha(a.cpp),
            "grid":"50x50 @ 100m UTM 50N WGS84",
            "float_field_count":7*2500,"category_field_count":2500,
            "failures":bad_total,"metrics":metrics,
            "cpp_geo_sha256":sha(a.cpp_geo) if a.cpp_geo else None,
            "writer_exact_formatted_value_gate":written_metrics,
            "limits":"Only original input LU.DAT + TERREL.DAT; integrated modern upstream not verified"}
    a.report.parent.mkdir(parents=True,exist_ok=True)
    a.report.write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps(result,indent=2))
    return 0 if bad_total==0 else 1
if __name__=="__main__":
    raise SystemExit(main())
