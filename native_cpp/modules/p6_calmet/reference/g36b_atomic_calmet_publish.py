#!/usr/bin/env python3
"""G36B: crash-safe final publication of the full 143h native P6F image.

The P6G G14/P6F physical runner writes a private candidate in scratch.
Only a fully validated 143x45 source-authored CALMET.DAT can be published.
A READY.json manifest is the *last* atomic commit marker. Consumers must
verify its SHA256/length and the exact hourly inventory, not rely on the
presence of met.dat. No change to frozen writer/physics/thresholds.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile

sys.path.insert(0,str(Path(__file__).resolve().parent))
from g31_extract_original_science_hour import layout
from g34_verify_original_six_hour_oracle import utc_clock

HOURS=143
FIELDS=45
READY="READY.json"
MET="met.dat"


def digest(path:Path)->str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for data in iter(lambda:f.read(1048576),b""):
            h.update(data)
    return h.hexdigest()


def sync_dir(dirpath:Path)->None:
    fd=os.open(dirpath,os.O_RDONLY|os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def verify_image(file:Path)->dict:
    parsed=layout(file,"G36B_native_143h_output")
    if parsed["intervals"]!=HOURS or len(parsed["groups"])!=HOURS:
        raise ValueError("G36B rejects partial/short 143h weather")
    from datetime import datetime,timezone,timedelta
    start=datetime(2024,1,1,2,tzinfo=timezone.utc)
    end=datetime(2024,1,7,1,tzinfo=timezone.utc)
    last=None
    for k,group in enumerate(parsed["groups"]):
        a,asec,b,bsec=group[0][1:5]
        lo,hi=utc_clock(a,asec),utc_clock(b,bsec)
        if lo!=start+timedelta(hours=k) or hi-lo!=timedelta(hours=1):
            raise ValueError(f"G36B missing/repeated native original-formatted UTC hour {k}")
        last=hi
    if last!=end:
        raise ValueError("G36B incomplete source UTC window")
    return {"status":"FULL_143H_VALIDATED","hours":HOURS,"fields_per_hour":FIELDS,
            "records":HOURS*FIELDS,"sha256":digest(file),"bytes":file.stat().st_size,
            "first_utc":start.isoformat(),"last_utc":last.isoformat()}


def check_published(directory:Path)->dict:
    ready=directory/READY
    target=directory/MET
    if not ready.is_file():
        raise ValueError("G36B no committed READY manifest; weather output MUST NOT be consumed")
    data=json.loads(ready.read_text())
    if data.get("status")!="COMMITTED_G36B_NATIVE_143H" or data.get("filename")!=MET:
        raise ValueError("G36B forged/uncommitted manifest")
    if not target.is_file() or target.is_symlink():
        raise ValueError("G36B READY manifest but file missing/symlink")
    observed=verify_image(target)
    for key in ("sha256","bytes","hours","records","first_utc","last_utc"):
        if data.get(key)!=observed[key]:
            raise ValueError(f"G36B READY hash/source inventory mismatch: {key}")
    return data


def publish(source:Path,directory:Path,fault:str)->dict:
    if fault not in {"none","before_stage_fsync","after_stage_fsync",
                     "after_met_rename","before_ready_rename"}:
        raise ValueError("G36B unknown injected crash boundary")
    source=source.resolve(strict=True)
    directory=directory.resolve()
    directory.mkdir(parents=True,exist_ok=True)
    # Fail closed after a partially committed previous attempt. No silent
    # overwrite of preexisting native hour data or a different revision.
    if (directory/READY).exists():
        current=check_published(directory)
        candidate=verify_image(source)
        if current["sha256"]!=candidate["sha256"]:
            raise ValueError("G36B refuses overwrite of different committed native science")
        return {**current,"idempotent":True}
    if (directory/MET).exists():
        raise ValueError("G36B orphan met.dat from crash; inspect/discard explicitly")
    expected=verify_image(source)
    # Exclusive scratch name on the SAME filesystem as final output.
    handle,name=tempfile.mkstemp(prefix=".g36b-staging-",dir=directory)
    staging=Path(name)
    try:
        with os.fdopen(handle,"wb") as sink, source.open("rb") as stream:
            while block:=stream.read(1048576):
                sink.write(block)
            sink.flush()
            if fault=="before_stage_fsync":
                raise RuntimeError("INJECT_G36B_CRASH_BEFORE_STAGE_FSYNC")
            os.fsync(sink.fileno())
        if digest(staging)!=expected["sha256"] or staging.stat().st_size!=expected["bytes"]:
            raise ValueError("G36B staged file changed across copy")
        verify_image(staging)
        if fault=="after_stage_fsync":
            raise RuntimeError("INJECT_G36B_CRASH_AFTER_STAGE_FSYNC")
        os.replace(staging,directory/MET)
        sync_dir(directory)
        if fault=="after_met_rename":
            raise RuntimeError("INJECT_G36B_CRASH_AFTER_MET_RENAME")
        committed={"status":"COMMITTED_G36B_NATIVE_143H","filename":MET,
                   **{k:v for k,v in expected.items() if k!="status"}}
        with tempfile.NamedTemporaryFile(
            mode="w",encoding="utf-8",prefix=".g36b-ready-",
            dir=directory,delete=False
        ) as stream:
            manifest_stage=Path(stream.name)
            json.dump(committed,stream,indent=2,sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        try:
            if fault=="before_ready_rename":
                raise RuntimeError("INJECT_G36B_CRASH_BEFORE_READY_RENAME")
            os.replace(manifest_stage,directory/READY)
            sync_dir(directory)
        finally:
            manifest_stage.unlink(missing_ok=True)
        check_published(directory)
        return committed
    finally:
        staging.unlink(missing_ok=True)


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--candidate",type=Path)
    p.add_argument("--publish-dir",type=Path,required=True)
    p.add_argument("--verify-only",action="store_true")
    p.add_argument("--inject-failure",default="none")
    args=p.parse_args()
    if args.verify_only:
        result=check_published(args.publish_dir)
    elif args.candidate:
        result=publish(args.candidate,args.publish_dir,args.inject_failure)
    else:
        p.error("--candidate required unless --verify-only")
    print(json.dumps(result,indent=2,sort_keys=True))


if __name__=="__main__":
    main()
