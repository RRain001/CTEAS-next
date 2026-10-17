#!/usr/bin/env python3
"""G36C: durable READY seal for a real native G14 replay checkpoint.

A checkpoint stores REAL committed ZI/ZICONV/DPTT bit patterns, both station
clock endpoints, and the complete 45xN native P6F prefix. On restart the
new native process deterministically replays the pinned original source
through hour N, proves saved physical state and prefix bit-identical, then
continues N..143. This is replay recovery; not in-memory direct restore.
"""
from __future__ import annotations
import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import tempfile

sys.path.insert(0,str(Path(__file__).resolve().parent))
from g31_extract_original_science_hour import layout
from g34_verify_original_six_hour_oracle import utc_clock

FILES=("met.inp","GEO.DAT","SURF.DAT","UP1.DAT","UP2.DAT")
MAGIC="CTEAS_G36C_REPLAY_CHECKPOINT_V1"
READY="READY.json"


def sha(path:Path)->str:
    h=hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda:stream.read(1048576),b""):
            h.update(block)
    return h.hexdigest()


def preflight(dir:Path,source:Path)->dict:
    state=dir/"state.txt"
    prefix=dir/"prefix.dat"
    if not state.is_file() or not prefix.is_file() or state.is_symlink() or prefix.is_symlink():
        raise ValueError("G36C incomplete checkpoint state/P6F prefix")
    lines=state.read_text().splitlines()
    if len(lines)!=5 or lines[0]!=MAGIC:
        raise ValueError("G36C unsupported/corrupted source-state schema")
    hdr=lines[1].split()
    if len(hdr)!=4:
        raise ValueError("G36C malformed state header")
    count,upper,gamma,n=(int(s) for s in hdr)
    if not 1<=count<=142 or n!=144:
        raise ValueError("G36C checkpoint source hours or grid wrong")
    expected=dt.datetime(2024,1,1,2,tzinfo=dt.timezone.utc)+dt.timedelta(hours=count)
    if upper!=int(expected.timestamp()) or gamma!=int(expected.timestamp()):
        raise ValueError("G36C missing/incorrect source station clocks")
    for group in lines[2:]:
        words=group.split()
        if len(words)!=n or not all(re.fullmatch(r"[0-9a-f]{8}",s) for s in words):
            raise ValueError("G36C corrupted REAL4 previous ZI/ZICONV/DPTT words")
    parsed=layout(prefix,"G36C_P6F_precommitted_checkpoint_prefix")
    if parsed["intervals"]!=count:
        raise ValueError("G36C checkpoint P6F prefix hours mismatch")
    first=parsed["groups"][0][0][1:5]
    final=parsed["groups"][-1][0][1:5]
    if utc_clock(first[0],first[1])!=dt.datetime(
            2024,1,1,2,tzinfo=dt.timezone.utc) or (
        utc_clock(final[2],final[3])!=expected):
        raise ValueError("G36C native P6F checkpoint UTC mismatched")
    inputs={}
    for filename in FILES:
        file=source/filename
        if not file.is_file() or file.is_symlink():
            raise ValueError("G36C checkpoint missing original source file "+filename)
        inputs[filename]=sha(file)
    return {"status":"SEALED_G36C_REPLAY_CHECKPOINT","hour_count":count,
            "next_hour_utc":expected.isoformat(),"source_files_sha256":inputs,
            "state_sha256":sha(state),"p6f_prefix_sha256":sha(prefix),
            "p6f_prefix_size":prefix.stat().st_size,
            "p6f_prefix_fields":count*45,
            "previous_state_real4_words":3*n,
            "station_clock_count":2}


def fsync_directory(dir:Path)->None:
    fd=os.open(dir,os.O_RDONLY|os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def verify(directory:Path,source:Path)->dict:
    if not (directory/READY).is_file():
        raise ValueError("G36C incomplete/unsealed checkpoint must NOT be replayed")
    committed=json.loads((directory/READY).read_text())
    observed=preflight(directory,source)
    if committed!=observed:
        raise ValueError("G36C persisted checkpoint manifest/source SHA256 mismatch")
    return committed


def seal(directory:Path,source:Path)->dict:
    directory=directory.resolve(strict=True)
    source=source.resolve(strict=True)
    if (directory/READY).exists():
        return verify(directory,source)
    observed=preflight(directory,source)
    # Both checkpoint files must reach storage before READY marker appears.
    for filename in ("state.txt","prefix.dat"):
        with (directory/filename).open("rb") as stream:
            os.fsync(stream.fileno())
    with tempfile.NamedTemporaryFile(mode="w",dir=directory,
        prefix=".g36c-ready-",encoding="utf-8",delete=False) as stream:
        temp=Path(stream.name)
        json.dump(observed,stream,sort_keys=True,indent=2)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    try:
        os.replace(temp,directory/READY)
        fsync_directory(directory)
    finally:
        temp.unlink(missing_ok=True)
    return verify(directory,source)


if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--checkpoint-dir",type=Path,required=True)
    ap.add_argument("--source-dir",type=Path,required=True)
    ap.add_argument("--verify-only",action="store_true")
    options=ap.parse_args()
    result=(verify if options.verify_only else seal)(
        options.checkpoint_dir,options.source_dir)
    print(json.dumps(result,indent=2,sort_keys=True))
