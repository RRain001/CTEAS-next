#!/usr/bin/env python3
"""Extract six true, consecutive original CALPUFF DGM hours with pinned SHA.

Requires a fresh full original 143h DGM re-run. No invented or reconstructed
Fortran trajectory is accepted. Output is validation data, not model input.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def digest(path: Path) -> str:
    h=hashlib.sha256()
    with path.open("rb") as handle:
        for data in iter(lambda:handle.read(2*1024*1024), b""):
            h.update(data)
    return h.hexdigest()


def extract(full: Path, meta: Path, target: Path) -> dict:
    data=json.loads(meta.read_text())
    expected=data["binary"]
    if full.stat().st_size!=expected["bytes"] or digest(full)!=expected["sha256"]:
        raise ValueError("full 143h original DGM binary differs from frozen oracle SHA")
    table=data["time"]["hour_table"]
    if len(table)!=143 or expected["records"]!=254687 or expected["record_bytes"]!=352:
        raise ValueError("frozen 143h DGM metadata invalid")
    for i in range(6):
        item=table[i]
        if item["packed"]!=202200100+i or item["seconds"]!=0:
            raise ValueError("original first six hours are not chronological")
        if i>0 and table[i-1]["last_byte_offset"]+352!=item["first_byte_offset"]:
            raise ValueError("gap or duplicate in DGM hour boundaries")
    count=sum(item["records"] for item in table[:6])
    if count!=11458 or table[0]["first_byte_offset"]!=0:
        raise ValueError("incorrect original first-six-hour row count")
    length=table[5]["last_byte_offset"]+352
    if length!=count*352:
        raise ValueError("misaligned original DGM byte boundaries")
    with full.open("rb") as stream:
        blob=stream.read(length)
    if len(blob)!=length:
        raise ValueError("original six-hour slice is truncated")
    first=table[0]["records"]*352
    if hashlib.sha256(blob[:first]).hexdigest()!=data["slice"]["sha256"]:
        raise ValueError("original pinned first-hour DGM was not preserved")
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_bytes(blob)
    result={"status":"ORIGINAL_DGM_SIX_HOURS_PINNED","rows":count,
            "bytes":length,"sha256":hashlib.sha256(blob).hexdigest(),
            "hours":[item["packed"] for item in table[:6]],
            "oracle_full_sha256":expected["sha256"],
            "native_cpp_state_parity":"NOT_TESTED_BY_THIS_EXTRACTOR"}
    (target.parent/"dgm_first_six_hours_provenance.json").write_text(
        json.dumps(result,indent=2)+"\n")
    print("P7_ORIGINAL_SIX_HOUR_CAPTURE=PASS ROWS=11458 HOURS=6 SHA256="+result["sha256"])
    return result


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--full",required=True,type=Path)
    p.add_argument("--metadata",required=True,type=Path)
    p.add_argument("--out",required=True,type=Path)
    args=p.parse_args()
    extract(args.full,args.metadata,args.out)
