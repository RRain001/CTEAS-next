#!/usr/bin/env python3
"""Independently parse P1/P2 original output fields; never synthesize expected data."""
from __future__ import annotations
import argparse, hashlib, json, math, statistics
from collections import Counter
from pathlib import Path

def sha(path):
    h=hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda:stream.read(1<<20),b""):h.update(chunk)
    return h.hexdigest()

def header_shape(line, count):
    chunks=line.split()
    if len(chunks)!=count:
        raise ValueError(f"unexpected coordinate/header column count: {len(chunks)} != {count}")
    nx,ny=map(int,chunks[:2])
    x0,y0,dx,dy=map(float,chunks[2:6])
    if nx<=0 or ny<=0 or dx<=0 or dy<=0 or not all(math.isfinite(v) for v in (x0,y0,dx,dy)):
        raise ValueError("invalid model grid in original data")
    return {"nx":nx,"ny":ny,"x0_km_rounded":x0,"y0_km_rounded":y0,"dx_km":dx,"dy_km":dy},chunks[6:]

def terrain(path):
    lines=path.read_text().splitlines()
    if len(lines)<11 or not lines[0].startswith("TERREL.DAT") or lines[0].split()[1]!="2.0":
        raise ValueError("not TERREL.DAT 2.0")
    if lines[4].strip()!="UTM" or lines[5].strip()!="50N" or not lines[6].startswith("WGS-84"):
        raise ValueError("terrain projection/datum mismatch")
    grid,extra=header_shape(lines[7],6)
    if extra or lines[8].split()!=["KM","M"] or lines[9].split()!=["W_E","N_S"]:
        raise ValueError("unexpected terrain units/axis ordering")
    values=[]
    for row in lines[10:]:
        values.extend(float(v) for v in row.split())
    if len(values)!=grid["nx"]*grid["ny"]:
        raise ValueError(f"wrong terrain denominator: {len(values)}")
    if not all(math.isfinite(v) for v in values):
        raise ValueError("terrain has NaN/Inf")
    missing=sum(v==-999 for v in values)
    valid=[v for v in values if v!=-999]
    return {"file":"TERREL.DAT","version":"2.0","sha256":sha(path),
            "grid":grid,"number_of_cell_values":len(values),
            "valid_cell_values":len(valid),"missing_sentinel_minus999":missing,
            "valid_denominator":len(valid),"min_m":min(valid) if valid else None,
            "max_m":max(valid) if valid else None,
            "mean_m":statistics.fmean(valid) if valid else None,
            "values_digest_identity":"SHA256 refers to raw file, not float list"}

def landuse(path,expected_grid):
    lines=path.read_text().splitlines()
    if len(lines)<12 or not lines[0].startswith("LU.DAT") or lines[0].split()[1]!="2.1":
        raise ValueError("not LU.DAT 2.1")
    if lines[4].strip()!="FRACTION" or lines[5].strip()!="UTM" or lines[6].strip()!="50N" or not lines[7].startswith("WGS-84"):
        raise ValueError("landuse format/projection mismatch")
    grid,extra=header_shape(lines[8],7)
    if len(extra)!=1:raise ValueError("missing landuse number of categories")
    ncat=int(extra[0])
    if ncat<=0 or lines[9].strip()!="KM":
        raise ValueError("invalid class count or landuse units")
    categories=[int(c) for c in lines[10].split()]
    if len(categories)!=ncat or len(set(categories))!=ncat:
        raise ValueError("category list not distinct/full")
    if grid!=expected_grid:raise ValueError("P1/P2 grids do not agree")
    if len(lines[11:])!=grid["nx"]*grid["ny"]:
        raise ValueError("wrong landuse record denominator")
    sums=[];fraction_hist=Counter();dominant=Counter();valid_cells=0;missing_cells=0
    minfrac,maxfrac=math.inf,-math.inf
    for n,line in enumerate(lines[11:]):
        fields=line.split()
        if len(fields)!=ncat+3 or fields[-1]!=".":
            raise ValueError(f"invalid landuse row {n+1}, expected {ncat+3} columns")
        i,j=int(fields[0]),int(fields[1])
        if (i,j)!=(n%grid["nx"]+1,n//grid["nx"]+1):
            raise ValueError(f"bad Fortran i/j index in record {n+1}: {(i,j)}")
        fractions=[float(v) for v in fields[2:-1]]
        if not all(math.isfinite(v) for v in fractions):
            raise ValueError(f"nonfinite fraction at {i},{j}")
        if any(v<0 or v>1 for v in fractions):
            raise ValueError(f"out-of-range fraction at {i},{j}")
        minfrac=min(minfrac,*fractions)
        maxfrac=max(maxfrac,*fractions)
        total=sum(fractions)
        sums.append(total)
        positives=[(categories[k],value) for k,value in enumerate(fractions) if value>0]
        if positives:
            valid_cells+=1
            for cat,value in positives:fraction_hist[cat]+=1
            dominant[categories[max(range(ncat),key=fractions.__getitem__)]]+=1
        else:missing_cells+=1
    return {"file":"LU.DAT","version":"2.1","sha256":sha(path),
            "grid":grid,"category_count":ncat,"category_codes":categories,
            "row_count":len(sums),"valid_cells_nonzero_fraction":valid_cells,
            "zero_fraction_cells_not_interpreted_as_water":missing_cells,
            "sum_min":min(sums),"sum_max":max(sums),
            "sum_exact_1_count":sum(v==1.0 for v in sums),
            "fraction_min":minfrac,"fraction_max":maxfrac,
            "positive_category_cell_count":dict(sorted(fraction_hist.items())),
            "dominant_category_cell_count":dict(sorted(dominant.items()))}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--reference-dir",required=True,type=Path)
    ap.add_argument("--summary",required=True,type=Path)
    a=ap.parse_args()
    p1=terrain(a.reference_dir/"p1/terrel.dat")
    p2=landuse(a.reference_dir/"p2/lu.dat",p1["grid"])
    if p1["grid"]["nx"]!=50 or p1["grid"]["ny"]!=50 or p1["grid"]["dx_km"]!=0.1:
        raise ValueError("reference output is not the required 100m 50x50 square")
    summary={"analysis_status":"PARSED_ORIGINAL_NOT_COMPARED_TO_CPP",
             "P1_terrain":p1,"P2_landuse":p2,
             "limits":["no C++ numerical algorithm compared",
                       "no acceptance tolerance inferred from reference output",
                       "source mask and Fortran internal precision not independently validated",
                       "original data header origin rounded to 3 decimal km"]}
    a.summary.parent.mkdir(parents=True,exist_ok=True)
    a.summary.write_text(json.dumps(summary,indent=2,ensure_ascii=False)+"\n")
    print(json.dumps(summary,indent=2,ensure_ascii=False))
    return 0

if __name__=="__main__":raise SystemExit(main())
