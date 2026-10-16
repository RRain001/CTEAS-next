#!/usr/bin/env python3
"""G35A: validate REAL original CALMET 143h 2SS/2US oracle provenance.

This does NOT infer C++ scientific parity from the vendor run. It requires
actual 143 x 45 original Fortran records, UTC chronology across 6+ days, the
exact original static inventory, and byte-identical original first SIX hours
versus the already-accepted independent original G34A six-hour run.
"""
from __future__ import annotations
import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path

from g31_extract_original_science_hour import layout
from g34_verify_original_six_hour_oracle import utc_clock


def sha(path:Path)->str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify(six:Path,long:Path)->dict:
    if six.resolve()==long.resolve():
        raise ValueError("G35 original 6h and 143h references are the same file")
    small=layout(six,"G35_literal_original_six_hours")
    large=layout(long,"G35_literal_original_143_hours")
    if small["intervals"]!=6 or large["intervals"]!=143:
        raise ValueError("G35 independent literal original hourly counts are not 6 and 143")
    if small["static"]!=large["static"]:
        raise ValueError("G35 source static grid or stations drifted vs accepted G34A")
    for i in range(6):
        if tuple(row[5] for row in small["groups"][i])!=tuple(
                row[5] for row in large["groups"][i]):
            raise ValueError(f"G35 original vs original first six hours mismatch at hour {i+1}")
    clocks=[]
    for index,group in enumerate(large["groups"]):
        a,asec,b,bsec=group[0][1:5]
        first,last=utc_clock(a,asec),utc_clock(b,bsec)
        if last-first!=dt.timedelta(hours=1):
            raise ValueError(f"G35 original hour {index+1} is not 3600s")
        if clocks and first!=clocks[-1][1]:
            raise ValueError(f"G35 original hour {index+1} repeats/skips time")
        clocks.append((first,last))
    if clocks[0][0]!=dt.datetime(2024,1,1,2,tzinfo=dt.timezone.utc) or (
        clocks[-1][1]!=dt.datetime(2024,1,7,1,tzinfo=dt.timezone.utc)):
        raise ValueError("G35 original 143h source start/end is not pinned daylight G19")
    transitions=sum(a.date()!=b.date() for a,b in clocks)
    if transitions<5:
        raise ValueError("G35 no genuine multi-day transitions")
    return {
        "status":"PASS_G35A_ORIGINAL_143H_ORACLE_ONLY",
        "scope":"Unmodified original CALMET 6.5.0 143 actual hours × 45 original fields; native scientific comparison is separate",
        "source":"original G19 12x12x9 grid / 10km / 2SS+2US source-format synthetic meteorology",
        "original_hours":len(clocks),
        "original_fields_per_hour":45,
        "original_total_hourly_fields":143*45,
        "original_6h_sha256":sha(six),
        "original_143h_sha256":sha(long),
        "original_first_six_hour_payloads":"BIT_IDENTICAL",
        "first_utc":clocks[0][0].isoformat(),
        "last_utc":clocks[-1][1].isoformat(),
        "day_boundaries":transitions,
    }


def main()->None:
    ap=argparse.ArgumentParser()
    ap.add_argument("--six-hour-original",type=Path,required=True)
    ap.add_argument("--long-original",type=Path,required=True)
    ap.add_argument("--out",type=Path,required=True)
    args=ap.parse_args()
    args.out.parent.mkdir(parents=True,exist_ok=True)
    try:
        report=verify(args.six_hour_original,args.long_original)
    except Exception as error:
        args.out.write_text(json.dumps({"status":"BLOCKED_G35A","error":str(error)},
                                       indent=2)+"\n")
        raise
    args.out.write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps(report,indent=2))


if __name__=="__main__":
    main()
