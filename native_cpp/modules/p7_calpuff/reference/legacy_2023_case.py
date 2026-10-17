#!/usr/bin/env python3
"""P7 historical original CALMET/CALPUFF 2023 pre-P6 reference.

Immutable 2023 case is a separate, noncanonical regression fixture.
This is not 2022/100m validation, not an assertion of native puff parity.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import struct
import subprocess

CASE = "project/cases/smoke5d_coldstart_20260701"
PINS = {
    "run/met/met.dat": "cd0af6fed77639a5e7205bc1fc4f9e4421b41926",
    "run/puff/puff.inp": "67dcdb856c0af92d30de346d4877af3b7d80db6f",
    "run/puff/puff.con": "2a0c1a0dabf50e1e61badaa526780cc623150dc3",
}

def digest(path: Path) -> dict:
    sha = hashlib.sha256()
    git_sha = hashlib.sha1()
    size = path.stat().st_size
    git_sha.update(f"blob {size}\0".encode())
    with path.open("rb") as file:
        for piece in iter(lambda: file.read(1048576), b""):
            sha.update(piece)
            git_sha.update(piece)
    return {"bytes": size, "sha256": sha.hexdigest(), "git_blob_sha1": git_sha.hexdigest()}

def assert_pins(root: Path) -> dict:
    checks={}
    for rel, expected in PINS.items():
        path=root / CASE / rel
        if not path.is_file():
            raise FileNotFoundError("P7 HISTORICAL ORIGINAL file missing: " + str(path))
        value=digest(path)
        if value["git_blob_sha1"] != expected:
            raise ValueError(f"Original 2023 Git blob changed: {rel} {value}")
        checks[rel]=value
    return checks

def active(text: str, name: str) -> str:
    m=re.findall(r"!\s*"+re.escape(name)+r"\s*=\s*([^!\r\n]+)!",text,re.IGNORECASE)
    if len(m)!=1:
        raise ValueError(f"P7 original 2023 expected exactly one active {name}: {len(m)}")
    return m[0].strip()

def check_2023(text: str) -> dict:
    for name, expected in {
       "IBYR":2023,"IBMO":1,"IBDY":1,"IBHR":0,
       "IEYR":2023,"IEMO":1,"IEDY":5,"IEHR":23,
       "NX":50,"NY":50,"NZ":9,"METFM":1,
       "NSPEC":2,"NSE":1,"MWET":0,"MCHEM":0,"NDECAY":0,
       "MGAUSS":1,"MDISP":3,"IOUTU":3,"NPT1":1,
    }.items():
        actual=int(active(text,name))
        if actual!=expected:
            raise ValueError(f"Noncanonical historical control {name}={actual}, expected {expected}")
    spacing=float(active(text,"DGRIDKM"))
    if spacing!=1.0 or active(text,"ABTZ").upper()!="UTC+0000":
        raise ValueError("2023 historical grid/timezone mismatch")
    if active(text,"METDAT").replace("\\","/")!="../../deliverables/met/met.dat":
        raise ValueError("2023 original weather relative path differs")
    if active(text,"LCFILES").upper()!="T":
        raise ValueError("2023 expects original lowercase output names")
    return {"years":[2023,2023],"start":"2023-01-01T00:00:00Z",
            "end":"2023-01-05T23:00:00Z","nx":50,"ny":50,"nz":9,
            "dgrid_km":1.0,"wet_scavenging":"disabled",
            "reference_class":"HISTORICAL_2023_NOT_CANONICAL_2022"}

def record_manifest(path: Path) -> dict:
    """Record-envelope-level comparison only; no concentration field semantics."""
    size=path.stat().st_size
    count=0
    with path.open("rb") as stream:
        while stream.tell()<size:
            header=stream.read(4)
            if len(header)!=4:raise ValueError("Truncated CALPUFF concentration header")
            length=struct.unpack("<i",header)[0]
            if length<0 or length>128*1024*1024:
                raise ValueError("Negative/chained/oversized concentration record")
            content=stream.read(length)
            if len(content)!=length:raise ValueError("Truncated concentration payload")
            tail=stream.read(4)
            if len(tail)!=4 or struct.unpack("<i",tail)[0]!=length:
                raise ValueError("Invalid concentration record trailer")
            count+=1
    if count==0:raise ValueError("No concentration records in reference")
    return {"records":count,**digest(path)}

def run(root: Path, output: Path, original_binary: Path,
        native_inspector: Path, timeout_s: int) -> dict:
    if timeout_s<1 or timeout_s>3600:raise ValueError("Selected historical timeout outside 1–3600s")
    root=root.resolve()
    output=output.resolve()
    original_binary=original_binary.resolve(strict=True)
    native_inspector=native_inspector.resolve(strict=True)
    if output==root or root in output.parents or output in root.parents:
        raise ValueError("Historical output root must be isolated from source checkout")
    files=assert_pins(root)
    source=root/CASE
    content=(source/"run/puff/puff.inp").read_text(encoding="latin-1")
    contract=check_2023(content)
    work=output/"case/run/puff"
    met=output/"case/deliverables/met"
    if output.exists() and any(output.iterdir()):
        raise FileExistsError("P7 historical output not empty: refusing stale results")
    work.mkdir(parents=True)
    met.mkdir(parents=True)
    shutil.copy2(source/"run/met/met.dat",met/"met.dat")
    shutil.copy2(source/"run/puff/puff.inp",work/"puff.inp")
    shutil.copy2(source/"run/puff/puff.inp",work/"calpuff.inp")
    path=work/active(content,"METDAT")
    if path.resolve()!= (met/"met.dat").resolve():
        raise ValueError("Historical CALPUFF METDAT does not resolve to staged original")
    output_name=active(content,"CONDAT")
    if Path(output_name).is_absolute() or ".." in Path(output_name).parts:
        raise ValueError("Unsafe original concentration output")
    result={"status":"ORIGINAL_2023_NOT_EXECUTED","baseline":contract,
            "pinned_git_blobs":files,"original_binary":digest(original_binary),
            "result_semantics":"REAL_2023_REFERENCE_NOT_2022_NOT_CPP_PUFF_PARITY"}
    manifest=output/"historical-2023-reference.json"
    manifest.write_text(json.dumps(result,indent=2)+"\n")
    with (output/"original-2023-runtime.log").open("w") as f:
        try:
            p=subprocess.run([str(original_binary)],cwd=work,stdout=f,
                             stderr=subprocess.STDOUT,timeout=timeout_s,check=False)
        except subprocess.TimeoutExpired as exc:
            result["status"]="ORIGINAL_2023_TIMEOUT"
            manifest.write_text(json.dumps(result,indent=2)+"\n")
            raise RuntimeError("Original 2023 CALPUFF reference timed out") from exc
    listing=work/active(content,"PUFLST")
    new_con=work/output_name
    result["original_returncode"]=p.returncode
    result["original_listing_present"]=listing.exists() and listing.stat().st_size>0
    result["original_concentration_present"]=new_con.exists() and new_con.stat().st_size>0
    if p.returncode!=0 or not result["original_listing_present"] or not result["original_concentration_present"]:
        result["status"]="ORIGINAL_2023_EXECUTION_FAIL"
        manifest.write_text(json.dumps(result,indent=2)+"\n")
        raise RuntimeError("Original 2023 CALPUFF failed, inspect logs/listing")
    result["original_concentration_record_envelope"]=record_manifest(new_con)
    history=source/"run/puff/puff.con"
    result["historical_concentration_record_envelope"]=record_manifest(history)
    result["historical_concentration_byte_identical"]=(
        result["original_concentration_record_envelope"]["sha256"]==
        result["historical_concentration_record_envelope"]["sha256"])
    result["historical_record_count_identical"]=(
        result["original_concentration_record_envelope"]["records"]==
        result["historical_concentration_record_envelope"]["records"])
    # Do not confuse original re-run comparison with C++ concentration parity.
    result["historical_binary_parity"]="EXACT_BYTE_MATCH" if result["historical_concentration_byte_identical"] else "DIFFERENT_UNEVALUATED"
    inspector=subprocess.run([str(native_inspector),str(source/"run/met/met.dat")],
                             text=True,capture_output=True,check=False,timeout=180)
    result["cpp_met21_inspector_returncode"]=inspector.returncode
    result["cpp_met21_inspector_stdout"]=inspector.stdout[:12000]
    result["cpp_met21_inspector_stderr"]=inspector.stderr[:12000]
    result["status"]="HISTORICAL_2023_REFERENCE_EXECUTION_PASS" if inspector.returncode==0 else "HISTORICAL_2023_CPP_MET21_DECODE_FAIL"
    manifest.write_text(json.dumps(result,indent=2)+"\n")
    # Original Fortran *did* complete and its real historical CONC.DAT
    # was validated before any C++ MET.DAT reader comparison.
    print("P7A_HISTORICAL_2023_ORIGINAL_CALPUFF_EXECUTION=PASS",flush=True)
    print("P7A_HISTORY_CONC_BYTE_PARITY="+result["historical_binary_parity"],flush=True)
    print("P7A_HISTORICAL_2023_CONC_RECORDS="+str(result["original_concentration_record_envelope"]["records"]),flush=True)
    if inspector.returncode:
        raise RuntimeError("Historical real CALMET.DAT failed P7B decode: "+inspector.stderr[:1500])
    print("P7B_HISTORICAL_2023_REAL_CALMET21_DECODE=PASS",flush=True)
    print("P7A_2022_CANONICAL_ACCEPTANCE=NOT_EVALUATED")
    return result

def main() -> None:
    ap=argparse.ArgumentParser()
    ap.add_argument("--repo",type=Path,required=True)
    ap.add_argument("--original-binary",type=Path,required=True)
    ap.add_argument("--native-inspector",type=Path,required=True)
    ap.add_argument("--output",type=Path,required=True)
    ap.add_argument("--timeout",type=int,default=600)
    x=ap.parse_args()
    run(x.repo,x.output,x.original_binary,x.native_inspector,x.timeout)
if __name__=="__main__":
    main()
