#!/usr/bin/env python3
"""S4-D independent *unchanged* original CALMET on already produced S3 Huoshan.

File staging only. This utility NEVER reads C++ native MET as input.
Original numeric/physical controls, real observation records and grid data
are neither replaced nor fabricated. Fails closed; preserves forensic listing.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import re
import shutil
import subprocess
from pathlib import Path

VENDOR_BLOB = "437f43bb7f0e51a1919e56664663e1a046986ed0"
NUMERICAL_CONTROLS = ("NX", "NY", "NSSTA", "NUSTA", "DGRIDKM",
                      "IEXTRP", "IMIXH", "IZICRLX", "IRAD", "ITPROG",
                      "IBYR", "IBMO", "IBDY", "IBHR", "IEYR", "IEMO",
                      "IEDY", "IEHR", "IUPT", "ZIMIN", "ZIMAX")
def sha(p: Path) -> str:
    h=hashlib.sha256()
    with p.open("rb") as stream:
        for part in iter(lambda: stream.read(1 << 20), b""):
            h.update(part)
    return h.hexdigest()
def git_blob(raw: bytes) -> str:
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()
def get(deck: str, key: str) -> str:
    found=re.findall(r"!\s*"+re.escape(key)+r"\s*=\s*([^!]*)!", deck, re.I)
    if len(found)!=1:
        raise ValueError("Original Huoshan deck missing/duplicate "+key)
    return found[0].strip()
def replace(deck: str, key: str, value: str) -> str:
    pat=re.compile(r"(!\s*"+re.escape(key)+r"\s*=\s*)([^!]*)(!)", re.I)
    found=list(pat.finditer(deck))
    if len(found)!=1:
        raise ValueError("S4-D duplicate/missing original filename "+key)
    match=found[0]
    return deck[:match.start()] + match.group(1)+value+" "+match.group(3)+deck[match.end():]

def run() -> None:
    ap=argparse.ArgumentParser()
    ap.add_argument("--case-root",type=Path,required=True)
    ap.add_argument("--vendor-dir",type=Path,required=True)
    ap.add_argument("--out",type=Path,required=True)
    ap.add_argument("--compiler",default="gfortran")
    args=ap.parse_args()
    case=args.case_root.resolve()
    vendor=args.vendor_dir.resolve()
    destination=args.out.resolve()
    destination.mkdir(parents=True,exist_ok=True)
    original=vendor/"calmet.for"
    receipt={"status":"BLOCKED","program":"unchanged CALMET 6.5.0",
             "vendor_original_fresh":False,"case_type":"Huoshan NOAA 2022 1SS1US 6h",
             "CXX_NATIVE_FIELDS_USED_AS_VENDOR_INPUT":False}
    try:
        original_data=original.read_bytes()
        receipt["vendor_calmet_for_git_blob"]=git_blob(original_data)
        receipt["vendor_calmet_for_sha256"]=sha(original)
        if receipt["vendor_calmet_for_git_blob"]!=VENDOR_BLOB:
            raise ValueError("Unpinned original CALMET source blob")
        source_paths={
            "original_metinp":case/"run/met/met.inp",
            "original_GEO":case/"geo/makegeo/geo.dat",
            "original_SURF":case/"met/surface/final/surf.dat",
            "original_UP":case/"met/upperair/final/up_58424.dat",
        }
        for role,path in source_paths.items():
            if not path.is_file() or not path.stat().st_size or path.is_symlink():
                raise ValueError("Missing non-symlink original producer source "+role)
            receipt[role+"_sha256"]=sha(path)
        deck=source_paths["original_metinp"].read_text()
        for k,v in {"NX":"100","NY":"100","NSSTA":"1","NUSTA":"1",
                    "IBYR":"2022","IBMO":"6","IBDY":"1","IBHR":"1",
                    "IEYR":"2022","IEMO":"6","IEDY":"1","IEHR":"7"}.items():
            if get(deck,k)!=v:
                raise ValueError(f"Original site model control {k}={get(deck,k)}, expected {v}")
        before={k:get(deck,k) for k in NUMERICAL_CONTROLS}
        stage=destination/"original-standalone-run"
        stage.mkdir(exist_ok=True)
        staged_files={
            "original_GEO":"geo.dat","original_SURF":"surf.dat",
            "original_UP":"up.dat"
        }
        for role,filename in staged_files.items():
            shutil.copyfile(source_paths[role],stage/filename)
            if sha(source_paths[role])!=sha(stage/filename):
                raise ValueError("Stage altered physical original source "+role)
        # Stage filename records only. Never alter original instrument values,
        # met deck's numerical choices, station identities or UTC duration.
        new_deck=deck
        for key,val in {"GEODAT":"geo.dat","SRFDAT":"surf.dat",
                        "UPDAT":"up.dat","METLST":"met.lst",
                        "METDAT":"met.dat"}.items():
            new_deck=replace(new_deck,key,val)
        after={k:get(new_deck,k) for k in NUMERICAL_CONTROLS}
        if before!=after:
            raise ValueError("Original numeric source controls changed by staging")
        receipt["untouched_numerical_controls"]=before
        (stage/"met.inp").write_text(new_deck)
        receipt["staged_original_deck_sha256"]=sha(stage/"met.inp")
        inc=destination/"include-alias"
        inc.mkdir(exist_ok=True)
        for f in vendor.iterdir():
            if f.is_file():
                link=inc/f.name.lower()
                if not link.exists():
                    link.symlink_to(f)
        executable=destination/"original-calmet.x"
        command=[args.compiler,"-std=legacy","-ffixed-line-length-none",
                 "-fno-automatic","-fno-align-commons",
                 "-fallow-argument-mismatch","-O0","-I"+str(inc),
                 str(original),"-o",str(executable)]
        receipt["original_compile_command"]=command
        build=subprocess.run(command,capture_output=True,text=True,timeout=360)
        (destination/"compiler-stdout.log").write_text(build.stdout)
        (destination/"compiler-stderr.log").write_text(build.stderr)
        if build.returncode or not executable.is_file():
            raise RuntimeError("Unchanged original CALMET compiler failed: "+
                               build.stderr[-1200:])
        receipt["original_binary_sha256"]=sha(executable)
        proc=subprocess.run([str(executable),"met.inp"],cwd=stage,
                            capture_output=True,text=True,timeout=600)
        (destination/"original-stdout.log").write_text(proc.stdout)
        (destination/"original-stderr.log").write_text(proc.stderr)
        receipt["original_exit_code"]=proc.returncode
        listing=stage/"met.lst"
        if listing.is_file():
            shutil.copy2(listing,destination/"original-met.lst")
            receipt["original_listing_sha256"]=sha(listing)
            receipt["original_listing_tail"]="\n".join(
                listing.read_text(errors="replace").splitlines()[-65:])
        met=stage/"met.dat"
        if proc.returncode!=0 or "Fortran runtime error" in proc.stderr:
            raise RuntimeError("Original CALMET error: "+proc.stderr[-1200:])
        if not met.is_file() or met.stat().st_size<200_000:
            raise RuntimeError("Original CALMET did not produce substantial MET.DAT")
        shutil.copyfile(met,destination/"original-met.dat")
        receipt["original_calmet_dat_sha256"]=sha(met)
        receipt["original_calmet_dat_bytes"]=met.stat().st_size
        receipt["status"]="ORIGINAL_VENDOR_FRESH_PRODUCED_UNVERIFIED"
        receipt["vendor_original_fresh"]=True
        print("S4D_HUOSHAN_6H_FRESH_UNMODIFIED_VENDOR_CALMET=PRODUCED_UNVERIFIED")
    except Exception as err:
        receipt["blocker"]=str(err)
        raise
    finally:
        (destination/"s4d-original-provenance.json").write_text(
            json.dumps(receipt,indent=2,sort_keys=True)+"\n")
if __name__=="__main__":
    run()
