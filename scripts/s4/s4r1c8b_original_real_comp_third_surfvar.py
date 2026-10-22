#!/usr/bin/env python3
"""Authentic 2SS+1US NOAA CALMET COMP SURFVAR(IALL=1) source oracle.

This merely adds a write-only call AFTER the original L4567 SURFVAR;
the original physical code, station inputs and 45-field MET are immutable.
Never supply this trace or its contents to native G17B4.
"""
from __future__ import annotations
import argparse
from datetime import datetime,timedelta,timezone
import hashlib,json,math,struct,subprocess,tempfile
from pathlib import Path
SOURCE_BLOB="437f43bb7f0e51a1919e56664663e1a046986ed0"
TRACE="s4r1c8b-original-comp-third-surfvar.bin"
NX,NY,HOURS=82,85,6
CELLS=NX*NY
FIRST=datetime(2022,6,1,1,tzinfo=timezone.utc)
HEADER=struct.Struct("<6i")
DATA=struct.Struct("<"+str(CELLS)+"f")
RECORD=HEADER.size+DATA.size
HELPER=r"""
c --- S4-R1c8b genuine original COMP IALL=1 SURFVAR: WRITE ONLY
      subroutine s4c8b_comp_third(temp2d)
      include 'params.met'
      include 'gen.met'
      include 'grid.met'
      real temp2d(mxnx,mxny)
      integer i,j
      logical opened
      save opened
      data opened/.false./
      if(.not.opened)then
         open(90,file='s4r1c8b-original-comp-third-surfvar.bin',
     1        form='unformatted',access='stream',status='replace')
         opened=.true.
      endif
      write(90) 56,ndathrb,nsecb,nx,ny,0
      write(90) ((temp2d(i,j),i=1,nx),j=1,ny)
      return
      end
"""
def sha(p:Path)->str:
    return hashlib.sha256(p.read_bytes()).hexdigest()
def checked_source(vendor:Path)->list[str]:
    blob=subprocess.run(["git","hash-object",str(vendor)],check=True,
                        capture_output=True,text=True).stdout.strip()
    if blob!=SOURCE_BLOB:raise ValueError("original CALMET pinned blob mismatch")
    lines=vendor.read_text().splitlines(keepends=True)
    expected=("call surfvar(u(1,1,1),v(1,1,1),"
              "tprog,temp2d,irh2d,ipcode2d,1)")
    if not(lines[4565].strip().lower()=="if(isfcmet.eq.0) then" and
           lines[4566].strip().lower()==expected):
        raise ValueError("original COMP IALL=1 SURFVAR L4567 source anchor drift")
    return lines
def prepare(vendor:Path,destination:Path,receipt:Path)->None:
    lines=checked_source(vendor)
    destination.parent.mkdir(parents=True,exist_ok=True)
    # Insert at original line L4567 + 1. Do not alter one byte of source cards.
    destination.write_text(
        "".join(lines[:4567])+
        "      call s4c8b_comp_third(temp2d)\n"+
        "".join(lines[4567:])+HELPER
    )
    receipt.parent.mkdir(parents=True,exist_ok=True)
    receipt.write_text(json.dumps({
        "state":"PINNED_ORIGINAL_ONLY_COMP_THIRD_WRITE_ONLY",
        "original_git_blob":SOURCE_BLOB,
        "original_vendor_sha256":sha(vendor),
        "instrumented_source_sha256":sha(destination),
        "original_hook_after_line":4567,
        "raw_p5_observations":"UNCHANGED",
        "native_comp_state":"NOT_ACCEPTED"
    },indent=2,sort_keys=True)+"\n")
    print("S4R1C8B_ORIGINAL_COMP_THIRD_SOURCE_PIN=PASS")
def read_records(path:Path)->list[tuple[int,tuple[float,...]]]:
    raw=path.read_bytes()
    if len(raw)!=HOURS*RECORD:
        raise ValueError("original six-hour COMP third SURFVAR records missing")
    rows=[]
    for hour in range(HOURS):
        offset=hour*RECORD
        tag,packed,sec,nx,ny,unused=HEADER.unpack_from(raw,offset)
        when=FIRST+timedelta(hours=hour)
        expected=when.year*100000+when.timetuple().tm_yday*100+when.hour
        if(tag,packed,sec,nx,ny,unused)!=(56,expected,0,NX,NY,0):
            raise ValueError(f"original COMP third SURFVAR source clock/order drift hour={hour}")
        temp=DATA.unpack_from(raw,offset+HEADER.size)
        if not all(math.isfinite(x) and 180<=x<=350 for x in temp):
            raise ValueError("invalid original COMP third 2D temperature values")
        rows.append((packed,temp))
    return rows
def verify(vendor:Path,pristine:Path,scratch:Path,trace:Path,
           report:Path)->None:
    checked_source(vendor)
    if sha(pristine)!=sha(scratch):
        raise ValueError("third COMP SURFVAR trace changed pristine CALMET six-hour 45-field MET")
    rows=read_records(trace)
    first=rows[0][1]
    res={
        "status":"PASS_ORIGINAL_REAL_NOAA_COMP_THIRD_REFERENCE_ONLY",
        "source_git_blob":SOURCE_BLOB,
        "original_met_byte_identical":True,
        "original_pristine_met_sha256":sha(pristine),
        "original_instrumented_met_sha256":sha(scratch),
        "original_third_trace_sha256":sha(trace),
        "six_original_hours":HOURS,
        "original_packed_hours":[x[0] for x in rows],
        "grid":[NX,NY],
        "original_firsthour_temp_min_k":min(first),
        "original_firsthour_temp_max_k":max(first),
        "original_firsthour_cells":CELLS,
        "native_comp_third":"NOT_RUN",
        "native_g26_45fields":"NOT_ACCEPTED",
        "causal_six_hour_g14":"NOT_ACCEPTED",
        "p7":"NOT_ACCEPTED",
    }
    report.parent.mkdir(parents=True,exist_ok=True)
    report.write_text(json.dumps(res,indent=2,sort_keys=True)+"\n")
    print("S4R1C8B_ORIGINAL_NOAA_COMP_THIRD=PASS_REFERENCE_ONLY")
    print("S4R1C8B_ORIGINAL_6H45_MET=BYTE_IDENTICAL")
    print("S4R1C8B_NATIVE_COMP_THIRD_G26_P7=NOT_ACCEPTED")
def selftest()->None:
    with tempfile.TemporaryDirectory() as d:
        p=Path(d)/TRACE
        with p.open("wb") as f:
            for k in range(HOURS):
                t=FIRST+timedelta(hours=k)
                pk=t.year*100000+t.timetuple().tm_yday*100+t.hour
                f.write(HEADER.pack(56,pk,0,NX,NY,0))
                f.write(DATA.pack(*([290.]*CELLS)))
        assert len(read_records(p))==HOURS
        raw=bytearray(p.read_bytes())
        raw[0]=57
        p.write_bytes(raw)
        try:read_records(p)
        except ValueError:pass
        else:raise AssertionError("corrupt COMP source header accepted")
    print("S4R1C8B_ORIGINAL_COMP_THIRD_NEGATIVE_SCHEMA=PASS")
def main()->None:
    parser=argparse.ArgumentParser()
    sub=parser.add_subparsers(dest="cmd",required=True)
    a=sub.add_parser("prepare")
    for key in ("vendor","destination","receipt"):a.add_argument("--"+key,type=Path,required=True)
    b=sub.add_parser("verify")
    for key in ("vendor","pristine","scratch","trace","report"):
        b.add_argument("--"+key,type=Path,required=True)
    sub.add_parser("selftest")
    args=parser.parse_args()
    if args.cmd=="prepare":prepare(args.vendor,args.destination,args.receipt)
    elif args.cmd=="verify":verify(args.vendor,args.pristine,args.scratch,args.trace,args.report)
    else:selftest()
if __name__=="__main__":main()
