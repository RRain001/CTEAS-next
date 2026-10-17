#!/usr/bin/env python3
"""Audit TERREL original grid data and intermediate hit counts against C++.
No tolerance is adjusted on failure. Original source artifacts are read only.
"""
from __future__ import annotations
import argparse,csv,hashlib,json,math,struct
from pathlib import Path

def read_fortran_records(path:Path)->list[bytes]:
    raw=path.read_bytes()
    offset=0
    records=[]
    while offset<len(raw):
        if offset+8>len(raw):raise ValueError("truncated Fortran record header")
        (n,)=struct.unpack_from("<i",raw,offset)
        if n<0 or offset+8+n>len(raw):raise ValueError("invalid Fortran record size")
        (end,)=struct.unpack_from("<i",raw,offset+4+n)
        if n!=end:raise ValueError("Fortran record marker mismatch")
        records.append(raw[offset+4:offset+4+n])
        offset+=8+n
    return records

def original(path:Path):
    lines=path.read_text().splitlines()
    if len(lines)<11 or lines[0].split()[:2]!=["TERREL.DAT","2.0"]:
        raise ValueError("wrong TERREL source format")
    if lines[4].strip()!="UTM" or lines[5].strip()!="50N" or not lines[6].startswith("WGS-84"):
        raise ValueError("unexpected original projection")
    meta=lines[7].split()
    if len(meta)!=6 or list(map(int,meta[:2]))!=[50,50] or abs(float(meta[4])-0.1)>1e-9:
        raise ValueError("unexpected original 50x50 100m grid")
    if lines[8].split()!=["KM","M"] or lines[9].split()!=["W_E","N_S"]:
        raise ValueError("unexpected units/output order")
    heights=[float(f) for line in lines[10:] for f in line.split()]
    if len(heights)!=2500 or not all(math.isfinite(x) for x in heights):
        raise ValueError("TERREL.DAT incomplete or nonfinite")
    # File W_E N_S is north -> south. Return south -> north to match internal i-fastest array.
    return [heights[(49-j)*50+i] for j in range(50) for i in range(50)]

def original_save(path:Path):
    rec=read_fortran_records(path)
    if len(rec)<4 or [len(v) for v in rec[:4]]!=[28,10000,10000,10000]:
        raise ValueError("TERREL.SAV unexpected record envelope")
    ids=struct.unpack("<7i",rec[0])
    if ids[4:6]!=(50,50):raise ValueError("TERREL.SAV grid shape mismatch")
    sums=struct.unpack("<2500f",rec[1])
    hits=struct.unpack("<2500i",rec[2])
    if not all(h>=0 for h in hits) or sum(hits)!=3456:
        raise ValueError("TERREL.SAV unexpected hit histogram")
    if not all(math.isfinite(v) for v in sums):
        raise ValueError("TERREL.SAV nonfinite sums")
    return sums,hits

def cpp(path:Path):
    with path.open(newline="") as f:
        rows=list(csv.DictReader(f))
    if len(rows)!=2500 or list(rows[0].keys())!=["i","j","hits","elevation_m"]:
        raise ValueError("C++ grid shape or header mismatch")
    hits=[];z=[]
    for k,row in enumerate(rows):
        if (int(row["i"]),int(row["j"]))!=(k%50+1,k//50+1):
            raise ValueError("C++ grid index/order mismatch")
        hits.append(int(row["hits"]))
        z.append(float(row["elevation_m"]))
    if not all(math.isfinite(v) for v in z):raise ValueError("C++ nonfinite terrain")
    return hits,z

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--reference-dir",required=True,type=Path)
    p.add_argument("--cpp",required=True,type=Path)
    p.add_argument("--report",required=True,type=Path)
    a=p.parse_args()
    expected=original(a.reference_dir/"p1/terrel.dat")
    sums,orig_hits=original_save(a.reference_dir/"p1/terrel.sav")
    hits,elev=cpp(a.cpp)
    count_diffs=[(i%50+1,i//50+1,old,new) for i,(old,new) in enumerate(zip(orig_hits,hits)) if old!=new]
    missing=[(i%50+1,i//50+1) for i,(o,n) in enumerate(zip(orig_hits,hits)) if (o==0)!=(n==0)]
    errors=[abs(x-y) for x,y in zip(expected,elev)]
    # TERREL.SAV holds the pre-format REAL*4 accumulated elevation sums.
    # Independently compare unrounded means, not only formatted TERREL.DAT.
    original_means=[sum_m/float(hits_m) if hits_m else -999.0
                    for sum_m,hits_m in zip(sums,orig_hits)]
    raw_errors=[abs(x-y) for x,y in zip(original_means,elev)]
    raw_tolerance=0.00001
    raw_failures=[(i%50+1,i//50+1,original_means[i],elev[i])
                  for i,e in enumerate(raw_errors) if e>raw_tolerance]
    # Original TERREL.DAT has f8.1, so 0.05 m represents fixed readout resolution.
    # Declared before running C++ comparison. Internal integer hits MUST match exactly.
    tolerance=0.0500001
    failures=[(i%50+1,i//50+1,expected[i],elev[i],hits[i],orig_hits[i])
              for i,e in enumerate(errors) if e>tolerance]
    report={
      "status":"PASS_SCOPED" if not count_diffs and not missing and not failures and not raw_failures else "FAIL",
      "reference_terrel_dat_sha256":hashlib.sha256((a.reference_dir/"p1/terrel.dat").read_bytes()).hexdigest(),
      "reference_terrel_sav_sha256":hashlib.sha256((a.reference_dir/"p1/terrel.sav").read_bytes()).hexdigest(),
      "grid":{"nx":50,"ny":50,"dx_m":100,"row_order":"C++ south-to-north, original data reversed"},
      "reference_input_hits":sum(orig_hits),"cpp_input_hits":sum(hits),
      "matched_hit_count_cells":2500-len(count_diffs),
      "hit_count_mismatch_count":len(count_diffs),
      "hit_count_mismatches_first_40":count_diffs[:40],
      "missing_mask_mismatch_count":len(missing),"missing_mask_mismatches":missing[:40],
      "height_fields_compared":len(errors),
      "height_max_error_m":max(errors),
      "height_mae_m":sum(errors)/len(errors),
      "height_rmse_m":math.sqrt(sum(e*e for e in errors)/len(errors)),
      "height_tolerance_m_from_fortran_f8_1":tolerance,
      "height_bad_cells":len(failures),
      "height_bad_first_40":failures[:40],
      "original_unrounded_real4_mean_tolerance_m":raw_tolerance,
      "unrounded_mean_max_error_m":max(raw_errors),
      "unrounded_mean_mae_m":sum(raw_errors)/len(raw_errors),
      "unrounded_mean_bad_cells":len(raw_failures),
      "unrounded_mean_bad_first_40":raw_failures[:40],
      "limitations":["No multi-CRS, void fill, peak or ocean processing compared",
                     "Raw float32 sums in original save need separate strict bitwise audit"]
    }
    a.report.parent.mkdir(parents=True,exist_ok=True)
    a.report.write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps(report,indent=2))
    return 0 if report["status"]=="PASS_SCOPED" else 1

if __name__=="__main__":
    raise SystemExit(main())
