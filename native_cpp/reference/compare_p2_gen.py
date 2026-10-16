#!/usr/bin/env python3
"""P2 Fortran-vs-C++ GEN field comparator; exact categories, fixed format tolerance."""
import argparse,csv,json,math,re
from pathlib import Path

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--reference",type=Path,required=True)
    p.add_argument("--cpp",type=Path,required=True)
    p.add_argument("--report",type=Path,required=True)
    args=p.parse_args()
    source=args.reference/"p2/lu.dat"
    lines=source.read_text().splitlines()
    if lines[0].split()[:2]!=["LU.DAT","2.1"] or lines[4].strip()!="FRACTION":
        raise ValueError("reference is not original LU.DAT fractional version 2.1")
    nxy=[int(v) for v in lines[8].split()[:2]]
    if nxy!=[50,50]:raise ValueError("not 50x50 original field")
    cats=[int(v) for v in lines[10].split()]
    if len(cats)!=38 or len(lines[11:])!=2500:raise ValueError("bad reference category/row count")
    rows=list(csv.DictReader(args.cpp.open()))
    colnames=["cat"+str(k) for k in cats]
    if len(rows)!=2500 or list(rows[0].keys())!=["i","j","samples",*colnames]:
        raise ValueError("CPP shape/category mismatch")
    used=0; errors=[]; missing=0; mismatch_count=0
    all_reference_valid=0
    for n,(ref,line) in enumerate(zip(lines[11:],rows)):
        raw=ref.split()
        if len(raw)!=41 or raw[-1]!=".":
            raise ValueError("bad reference row")
        i,j=map(int,raw[:2])
        if (i,j)!=(n%50+1,n//50+1) or (int(line["i"]),int(line["j"]))!=(i,j):
            raise ValueError("bad output row ordering")
        ref_values=[float(v) for v in raw[2:-1]]
        npts=int(line["samples"])
        if npts==0:
            missing+=1
            if sum(ref_values)>0:mismatch_count+=1
            continue
        used+=npts
        all_reference_valid+=1
        for key,x in zip(colnames,ref_values):
            value=float(line[key])
            if not math.isfinite(value):raise ValueError("CPP nonfinite fraction")
            errors.append(abs(value-x))
    # Predeclared fixed-format rounding resolution: original LU.DAT writes three decimals,
    # so comparison is per-field 0.0005 absolute, never tuned post-results.
    tol=0.0005
    max_error=max(errors,default=math.nan)
    ref_lst=(args.reference/"p2/ctgproc.lst").read_text()
    m=re.search(r"Number of data points used to update grid:\s*(\d+)",ref_lst)
    if not m:raise ValueError("missing independent original point-count line")
    original_used=int(m.group(1))
    report={"comparison":"CTGPROC GEN EPSG32650 first Hefei 100m",
            "valid_fraction_cells_original":2500,
            "valid_fraction_cells_cpp":all_reference_valid,
            "missing_cpp_cells":missing,
            "cell_mask_mismatch_count":mismatch_count,
            "compared_float_fields":len(errors),
            "max_absolute_fraction_error":max_error,
            "mean_absolute_fraction_error":sum(errors)/len(errors) if errors else None,
            "rmse_fraction_error":math.sqrt(sum(x*x for x in errors)/len(errors)) if errors else None,
            "predeclared_absolute_fraction_tolerance":tol,
            "original_accepted_point_count":original_used,
            "cpp_accepted_point_count":used,
            "point_count_difference":used-original_used,
            "numeric_fraction_gate":"PASS" if missing==0 and mismatch_count==0 and len(errors)==2500*38 and max_error<=tol else "FAIL",
            "internal_count_gate":"PASS" if used==original_used else "FAIL",
            "other_algorithms":"NOT_TESTED"}
    args.report.parent.mkdir(parents=True,exist_ok=True)
    args.report.write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps(report,indent=2))
    if report["numeric_fraction_gate"]!="PASS" or report["internal_count_gate"]!="PASS":
        raise SystemExit(1)
    return 0
if __name__=="__main__":raise SystemExit(main())
