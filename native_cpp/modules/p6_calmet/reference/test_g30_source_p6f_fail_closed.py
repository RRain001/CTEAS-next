#!/usr/bin/env python3
"""G30B guard: audit-only P6F 45-record validator MUST reject tampering.

This is not original CALMET science parity. It verifies independent G30A
Fortran framing, original hourly header, record labels, original NEARS, and
G24/G29 stage provenance checks reject individually corrupted inputs.
"""
from __future__ import annotations

import argparse
import csv
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parent
VERIFIER=ROOT/"verify_g30_source_p6f_candidate.py"


def records(raw:bytes):
    idx=0
    out=[]
    while idx<len(raw):
        if idx+8>len(raw):
            raise ValueError("short Fortran frame")
        (n,)=struct.unpack_from("<i",raw,idx)
        if n<0 or idx+n+8>len(raw) or struct.unpack_from("<i",raw,idx+n+4)[0]!=n:
            raise ValueError("bad original Fortran frame")
        out.append((idx+4,n))
        idx+=n+8
    if idx!=len(raw):
        raise ValueError("trailing Fortran frame bytes")
    return out


def locate(raw:bytes, label:str):
    for pos,n in records(raw):
        if n>=24 and raw[pos:pos+8].decode("ascii",errors="replace")==label:
            return pos
    raise ValueError("no original P6F record "+label)


def launch(a,candidate,work,temperature_prefix=None):
    cmd=[sys.executable,str(VERIFIER),
         "--candidate",str(candidate),
         "--wind-tail",str(a.wind_tail),
         "--source-clock",str(a.source_clock),
         "--comp-prefix",str(a.comp_prefix),
         "--temp3d-prefix",str(temperature_prefix or a.temp3d_prefix),
         "--out",str(work/"result.json")]
    return subprocess.run(cmd,capture_output=True,text=True)


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--candidate",type=Path,required=True)
    ap.add_argument("--wind-tail",type=Path,required=True)
    ap.add_argument("--source-clock",type=Path,required=True)
    ap.add_argument("--comp-prefix",type=Path,required=True)
    ap.add_argument("--temp3d-prefix",type=Path,required=True)
    a=ap.parse_args()
    raw=a.candidate.read_bytes()
    index=records(raw)
    if len(index)<50:
        raise RuntimeError("G30B candidate is not a complete CALMET 2.1 file")
    with tempfile.TemporaryDirectory(prefix="cteas-g30-p6f-reject-") as directory:
        work=Path(directory)
        baseline=launch(a,a.candidate,work)
        if baseline.returncode:
            raise RuntimeError("G30B baseline G30A verification did not PASS:\n"+
                               baseline.stderr[-1800:])
        corrupted=[]
        # Mutate a single U-LEV float, keeping valid sequential framing.
        wind=bytearray(raw)
        off=locate(raw,"U-LEV  1")+24
        struct.pack_into("<f",wind,off,struct.unpack_from("<f",wind,off)[0]+4.0)
        corrupted.append(("physical_u_lev",wind))
        # A single wrong output record name must not pass via self-roundtrip.
        name=bytearray(raw)
        off=locate(raw,"V-LEV  1")
        name[off:off+8]=b"X-LEV  1"
        corrupted.append(("wrong_field_label",name))
        # Header time must remain bound to G21 source hourly input.
        timing=bytearray(raw)
        (ncomments,)=struct.unpack_from("<i",raw,index[1][0])
        off=index[2+ncomments][0]+20+12
        struct.pack_into("<i",timing,off,18)
        corrupted.append(("wrong_model_hour",timing))
        # A plausible-looking binary with invalid nearest station must fail.
        nears=bytearray(raw)
        off=locate(raw,"NEARS   ")+24
        struct.pack_into("<i",nears,off,99)
        corrupted.append(("invalid_nears",nears))
        # Record-length mismatch must be caught before any field consumption.
        framing=bytearray(raw)
        framing[-1]^=1
        corrupted.append(("corrupted_record_framing",framing))
        statuses={}
        for key,payload in corrupted:
            file=work/(key+".calmet.dat")
            file.write_bytes(payload)
            r=launch(a,file,work)
            if r.returncode==0:
                raise RuntimeError(f"G30B unexpected ACCEPT of {key} tampered binary")
            if not any(word in r.stderr for word in ("ValueError","AssertionError")):
                raise RuntimeError(f"G30B {key} failed for non-validation reason: {r.stderr[-700:]}")
            statuses[key]="REJECTED"
        # Even a valid P6F image fails if independent G29 temperatures
        # are replaced with an unrelated numerical field.
        prefix=work/"mutated_temp3d"
        src=Path(str(a.temp3d_prefix)+".native.csv")
        rows=list(csv.DictReader(src.open(newline="")))
        if not rows:
            raise RuntimeError("G30B source TEMP3D CSV missing")
        rows[0]["temp_k"]=str(float(rows[0]["temp_k"])+4.0)
        with Path(str(prefix)+".native.csv").open("w",newline="") as out:
            writer=csv.DictWriter(out,fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
        r=launch(a,a.candidate,work,prefix)
        if r.returncode==0:
            raise RuntimeError("G30B accepted mutated original TEMP3D handoff")
        if "AssertionError" not in r.stderr:
            raise RuntimeError("G30B TEMP3D mismatch validation not reached: "+r.stderr[-700:])
        statuses["mutated_temp3d_source"]="REJECTED"
    print("PASS_G30B_FAIL_CLOSED "+str(statuses))
    if len(statuses)!=6:
        raise RuntimeError("G30B negative cases incomplete")

if __name__=="__main__":
    main()
