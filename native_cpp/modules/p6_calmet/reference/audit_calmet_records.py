#!/usr/bin/env python3
"""Strict read-only original CALMET.DAT Fortran sequential record audit.

Decode physical record *framing*, never infer numeric layout or atmospheric
fields before matching original OUT/HDR/OUTHR/IFORMO specifications. Validated
framing is NOT equivalence of meteorological variables or model correctness.
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import os
import struct
from pathlib import Path

def inspect(path: Path):
    size=path.stat().st_size
    if size<1024:raise ValueError("empty or undersized MET.DAT")
    h=hashlib.sha256()
    with path.open("rb") as f:
        while block:=f.read(1<<20):h.update(block)
    probes=[]
    for fmt,endian,marker in (("little_4","<",4),("big_4",">",4),("little_8","<",8),("big_8",">",8)):
        try:
            n=0;counts=collections.Counter();prefix=[];max_len=0
            length_fmt=endian+("i" if marker==4 else "q")
            pos=0
            with path.open("rb") as f:
                while pos<size:
                    if size-pos<2*marker:raise ValueError("truncated marker")
                    head=f.read(marker)
                    if len(head)!=marker:raise ValueError("short record header")
                    (record_bytes,)=struct.unpack(length_fmt,head)
                    if record_bytes<0 or record_bytes>size-pos-2*marker:
                        raise ValueError("record-size bounds or unsupported split records")
                    if n<10:
                        # Record preview is intentionally limited and not persisted verbatim:
                        # original CALMET headers can include identifying station metadata.
                        prefix.append({"record_index":n,"payload_bytes":record_bytes})
                    # Skip payload without loading massive 3-D record into memory.
                    f.seek(record_bytes,os.SEEK_CUR)
                    tail=f.read(marker)
                    if len(tail)!=marker or struct.unpack(length_fmt,tail)[0]!=record_bytes:
                        raise ValueError("mismatched Fortran trailing marker")
                    pos+=record_bytes+2*marker
                    counts[record_bytes]+=1
                    max_len=max(max_len,record_bytes)
                    n+=1
                    if n>1000000:raise ValueError("excessive record count")
            if pos==size and n>10:
                probes.append({
                    "kind":fmt,"record_count":n,
                    "initial_record_lengths":prefix,
                    "payload_length_histogram":dict(sorted(counts.items())),
                    "largest_payload_bytes":max_len,
                    "exact_eof":True,
                })
        except (ValueError,struct.error,OSError):
            continue
    if len(probes)!=1:
        raise ValueError(f"ambiguous or unrecognized CALMET.DAT Fortran record framing: {len(probes)} candidates")
    return {
        "status":"PASS_ORIGINAL_FORTRAN_FRAMING_ONLY",
        "file_bytes":size,"sha256":h.hexdigest(),**probes[0],
        "limits":"No decoding of wind/temperature/precip/mixing fields; no numerical or scientific equivalence inferred",
    }

def main():
    p=argparse.ArgumentParser()
    p.add_argument("met_dat",type=Path)
    p.add_argument("--manifest",required=True,type=Path)
    a=p.parse_args()
    report=inspect(a.met_dat)
    a.manifest.parent.mkdir(parents=True,exist_ok=True)
    a.manifest.write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps(report,indent=2))
if __name__=="__main__":
    main()
