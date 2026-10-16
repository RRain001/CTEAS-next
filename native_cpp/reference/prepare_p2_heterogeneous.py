#!/usr/bin/env python3
"""Build a deterministic heterogeneous GEN-only reference without altering study data."""
from __future__ import annotations
import argparse,hashlib,json,math,re,shutil,subprocess
from pathlib import Path

def sha(p:Path)->str:
    return hashlib.sha256(p.read_bytes()).hexdigest()

def main()->int:
    p=argparse.ArgumentParser()
    p.add_argument("--capture-dir",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    args=p.parse_args()
    root=args.capture_dir.resolve()
    dest=args.output.resolve()
    dest.mkdir(parents=True,exist_ok=False)
    data,p2=dest/"data",dest/"p2"
    data.mkdir();p2.mkdir()
    original=root/"data/generic_landuse.txt"
    lines=original.read_text().splitlines()
    if lines[0].strip()!="GENERIC.LANDUSE 1.0" or lines[1].strip()!="1":
        raise RuntimeError("GEN source header not expected format")
    ncomment=int(lines[1].strip())
    classes_index=2+ncomment+3
    number=int(lines[classes_index])
    categories=[int(n) for n in lines[classes_index+1].split()]
    if number!=38 or len(categories)!=number or len(set(categories))!=number:
        raise RuntimeError("unexpected original GEN category list")
    start=classes_index+2
    if len(lines)-start!=57600:
        raise RuntimeError("unexpected original GEN point denominator")
    synthetic=data/"generic_landuse.txt"
    replacements=0
    with synthetic.open("w") as out:
        for line in lines[:start]:
            out.write(line+"\n")
        for n,line in enumerate(lines[start:]):
            fields=line.split()
            if len(fields)!=3:raise RuntimeError(f"malformed original point line {n+1}")
            int(fields[0]);float(fields[1]);float(fields[2])
            # Controlled deterministic non-physical distribution for method QA.
            # Selection is independent of Fortran/C++ grid class results.
            new_cat=categories[(17*n+n//3)%len(categories)]
            replacements+=int(int(fields[0])!=new_cat)
            out.write(f"{new_cat} {fields[1]} {fields[2]}\n")
    if replacements<50000:
        raise RuntimeError("synthetic sample changes too few")
    shutil.copy2(root/"p2/ctgproc.inp",p2/"ctgproc.inp")
    control=(p2/"ctgproc.inp").read_text()
    if "GEN =" not in control or not re.search(r"!\s*DNZGEN\s*=\s*ESR-S\s*!",control):
        raise RuntimeError("original CTGPROC control not in GEN/ESR-S mode")
    cmd=[str((root/"bin/ctgproc.x").resolve()),"ctgproc.inp"]
    run=subprocess.run(cmd,cwd=p2,text=True,capture_output=True,timeout=150)
    (dest/"ctgproc.stdout.txt").write_text(run.stdout)
    (dest/"ctgproc.stderr.txt").write_text(run.stderr)
    if run.returncode or not (p2/"lu.dat").exists():
        raise RuntimeError("heterogeneous original CTGPROC run failed; logs retained")
    original_result=(p2/"lu.dat").read_text().splitlines()
    if original_result[0].split()[:2]!=["LU.DAT","2.1"] or len(original_result[11:])!=2500:
        raise RuntimeError("heterogeneous reference output incomplete")
    mixed=0
    present=set()
    for row in original_result[11:]:
        fields=row.split()
        if len(fields)!=number+3:raise RuntimeError("malformed output fractions")
        positives=[idx for idx,frac in enumerate(map(float,fields[2:-1])) if frac>0]
        mixed+=(len(positives)>=2)
        present.update(positives)
    if mixed<100 or len(present)<8:
        raise RuntimeError("heterogeneous benchmark lacks independently verified class diversity")
    meta={"classification":"SYNTHETIC_NONPHYSICAL_GEN_REFERENCE",
          "source_original_sha256":sha(original),
          "synthetic_gen_sha256":sha(synthetic),
          "changed_input_class_records":replacements,
          "source_record_count":len(lines)-start,
          "reference_lu_sha256":sha(p2/"lu.dat"),
          "reference_mixed_class_cells":mixed,
          "distinct_present_categories":len(present),
          "original_exit_status":run.returncode,
          "scope":"GEN ESR-S same exact input coordinate strings; only class codes changed"}
    (dest/"hetero_manifest.json").write_text(json.dumps(meta,indent=2)+"\n")
    print(json.dumps(meta,indent=2))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
