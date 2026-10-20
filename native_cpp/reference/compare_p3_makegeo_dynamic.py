"""#46 D3: independent original MAKEGEO 3.2 vs native P3 field comparator.

Reads original Fortran GEO.DAT, C++ GEO.DAT and C++ high-precision CSV.
No C++ import, no per-site adjustment of precision tolerance, no imputation.
The original executable must be independently compiled and run by the caller.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path

FIELDS=(
    ("category","LAND USE DATA",0.0),
    ("elevation_m","TERRAIN heights",0.0050001),
    ("z0_m","gridded z0 field",0.00005001),
    ("albedo","gridded albedo field",0.0050001),
    ("bowen","gridded Bowen ratio field",0.0050001),
    ("soil_heat","gridded soil heat flux parameters",0.0050001),
    ("anthropogenic_heat","gridded anthropogenic heat flux field",0.0050001),
    ("lai","gridded leaf area index field",0.0050001),
)
COLS=["i","j",*(x[0] for x in FIELDS)]


def sha(path:Path)->str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for buf in iter(lambda:f.read(1<<20),b""):
            h.update(buf)
    return h.hexdigest()


def demand(ok,msg):
    if not ok: raise ValueError("P3_D3_ORIGINAL_COMPARISON: "+msg)


def parse_geo(path:Path,*,nx:int,ny:int,zone:int,hem:str,x0:float,y0:float,dx:float):
    lines=path.read_text(encoding="utf-8").splitlines()
    demand(len(lines)>20 and lines[0].split()[:2]==["GEO.DAT","2.1"],
           "original/non-original GEO v2.1 header missing")
    demand(lines[4].strip()=="UTM" and
           lines[5].strip()==str(zone)+hem and lines[6].strip().startswith("WGS-84"),
           "original GEO CRS mismatch")
    values=lines[7].split()
    demand(len(values)>=6,"GEO shape header absent")
    demand((int(values[0]),int(values[1]))==(nx,ny),"GEO shape not case")
    demand(all(abs(float(a)-v)<1e-6 for a,v in zip(values[2:6],(x0,y0,dx,dx))),
           "GEO origin/spacing not admitted case")
    marks=[]
    for name,needle,_ in FIELDS:
        indices=[i for i,s in enumerate(lines) if needle in s]
        demand(len(indices)==1,"GEO section not unique: "+name)
        marks.append(indices[0])
    demand(marks==sorted(marks),"GEO sections reordered")
    out={}
    for field,(name,label,tolerance) in enumerate(FIELDS):
        begin=marks[field]+(3 if name=="category" else 1)
        end=marks[field+1] if field+1<len(marks) else len(lines)
        tokens=[token for line in lines[begin:end]
                for token in line.replace(","," ").split()]
        demand(len(tokens)==nx*ny,
               "GEO field count invalid "+name+" expected "+str(nx*ny)+
               " actual "+str(len(tokens)))
        vals=[int(x) for x in tokens] if name=="category" else [float(x) for x in tokens]
        demand(all(math.isfinite(x) for x in vals),"GEO nonfinite "+name)
        # Native case rows are south-to-north j fastest by outer loop;
        # original GEO writes grid north-to-south with i fastest.
        out[name]=[vals[(ny-1-j)*nx+i] for j in range(ny) for i in range(nx)]
    return out


def compare(original:Path,cpp_csv:Path,cpp_geo:Path,report:Path,
            *,zone:int,hem:str,nx:int,ny:int,x0:float,y0:float,dx:float)->dict:
    expected=dict(nx=nx,ny=ny,zone=zone,hem=hem,x0=x0,y0=y0,dx=dx)
    a=parse_geo(original,**expected)
    b=parse_geo(cpp_geo,**expected)
    metrics={}
    problems=0
    for name,_,tolerance in FIELDS:
        wrong=0
        max_display_error=0.
        first=[]
        for idx,(reference,native) in enumerate(zip(a[name],b[name])):
            e=abs(float(reference)-float(native))
            max_display_error=max(max_display_error,e)
            if e>0:
                wrong+=1
                if len(first)<20:
                    first.append(dict(i=idx%nx+1,j=idx//nx+1,
                                      original=reference,native=native,delta=e))
        problems+=wrong
        metrics[name]=dict(displayed_value_mismatches=wrong,
                           max_displayed_abs_error=max_display_error,
                           original_vs_native_first20=first,
                           compared_cells=nx*ny,
                           predeclared_csv_tolerance=tolerance)
    with cpp_csv.open(newline="") as stream:
        reader=csv.DictReader(stream)
        demand(reader.fieldnames==COLS,"native P3 CSV schema changed")
        raw_errors={key:0 for key,_,_ in FIELDS}
        raw_first={key:[] for key,_,_ in FIELDS}
        rows=0
        for index,row in enumerate(reader):
            demand(index<nx*ny,"native P3 CSV extra rows")
            demand((int(row["i"]),int(row["j"]))==(index%nx+1,index//nx+1),
                   "native P3 CSV row order changed")
            for key,_,tol in FIELDS:
                value=float(row[key])
                demand(math.isfinite(value),"native P3 CSV nonfinite "+key)
                e=abs(value-a[key][index])
                if e>tol:
                    raw_errors[key]+=1
                    if len(raw_first[key])<20:
                        raw_first[key].append(dict(i=index%nx+1,j=index//nx+1,
                                      original=a[key][index],native=value,delta=e))
            rows+=1
    demand(rows==nx*ny,"native P3 CSV missing cells")
    problems+=sum(raw_errors.values())
    for key in raw_errors:
        metrics[key]["csv_outside_fixed_precision_tolerance"]=raw_errors[key]
        metrics[key]["csv_first20"]=raw_first[key]
    result=dict(
        status="P3_NONHEFEI_ORIGINAL_MAKEGEO_PASS" if problems==0 else
               "P3_NONHEFEI_ORIGINAL_MAKEGEO_NUMERIC_FAIL",
        source="Original MAKEGEO 3.2 L110401 independently compiled on the exact case-specific LU/TERREL input",
        native="CTEAS-next selected 38-to-14 no-snow MAKEGEO C++",
        nx=nx,ny=ny,utm_zone=zone,utm_hemisphere=hem,xrefkm=x0,yrefkm=y0,dgridkm=dx,
        values_compared=nx*ny*len(FIELDS),
        formatted_values_compared=nx*ny*len(FIELDS),
        original_geo_sha256=sha(original),native_geo_sha256=sha(cpp_geo),
        native_csv_sha256=sha(cpp_csv),
        failures=problems,metrics=metrics,
        limitations="Only selected no-snow physics branch and same true-source input")
    report.parent.mkdir(parents=True,exist_ok=True)
    report.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps({k:v for k,v in result.items() if k!="metrics"},sort_keys=True))
    return result


def main()->int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--original-geo",type=Path,required=True)
    p.add_argument("--cpp-geo",type=Path,required=True)
    p.add_argument("--cpp-csv",type=Path,required=True)
    p.add_argument("--report",type=Path,required=True)
    p.add_argument("--zone",type=int,required=True)
    p.add_argument("--hem",choices=["N","S"],required=True)
    p.add_argument("--nx",type=int,required=True)
    p.add_argument("--ny",type=int,required=True)
    p.add_argument("--xrefkm",type=float,required=True)
    p.add_argument("--yrefkm",type=float,required=True)
    p.add_argument("--dgridkm",type=float,required=True)
    o=p.parse_args()
    result=compare(o.original_geo,o.cpp_csv,o.cpp_geo,o.report,
                   zone=o.zone,hem=o.hem,nx=o.nx,ny=o.ny,
                   x0=o.xrefkm,y0=o.yrefkm,dx=o.dgridkm)
    return 0 if result["failures"]==0 else 1


if __name__=="__main__":
    raise SystemExit(main())
