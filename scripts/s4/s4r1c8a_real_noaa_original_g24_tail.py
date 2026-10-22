#!/usr/bin/env python3
"""S4-R1c8a untouched original CALMET post-SMOOTH/DIVCEL/W field oracle.

Instrument only AFTER the literal original DIAGNO L6119–6148 segment; do
not replace any source formula or allow any oracle field into native C++.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import hashlib
import json
import math
from pathlib import Path
import struct
import subprocess
import tempfile

ORIGINAL_BLOB="437f43bb7f0e51a1919e56664663e1a046986ed0"
NAME="s4r1c8a-original-post-g24-tail.bin"
NX,NY,NZ,HOURS=82,85,9,6
N=NX*NY
COUNTS=(NZ*N,NZ*N,(NZ+1)*N,NZ*N,2*NY*NZ,2*NX*NZ)
COUNT=sum(COUNTS)
HEADER=struct.Struct("<6i")
RECORD_BYTES=HEADER.size+4*COUNT
FIRST=datetime(2022,6,1,1,tzinfo=timezone.utc)
HELPER=r"""
c --- S4-R1c8a write only: original DIAGNO tail after W and WINDBC
      subroutine s4c8a_g24_after
      include 'params.met'
      include 'gen.met'
      include 'grid.met'
      include 'd1.met'
      integer i,j,k,side
      logical opened
      save opened
      data opened/.false./
      if(.not.opened)then
         open(91,file='s4r1c8a-original-post-g24-tail.bin',
     1        form='unformatted',access='stream',status='replace')
         opened=.true.
      endif
      write(91) 54,ndathrb,nsecb,nx,ny,nz
      write(91) (((u(i,j,k),i=1,nx),j=1,ny),k=1,nz)
      write(91) (((v(i,j,k),i=1,nx),j=1,ny),k=1,nz)
      write(91) (((w(i,j,k),i=1,nx),j=1,ny),k=1,nz+1)
      write(91) (((div(i,j,k),i=1,nx),j=1,ny),k=1,nz)
      do k=1,nz
         do side=1,2
            write(91) (ub(j,side,k),j=1,ny)
         enddo
      enddo
      do k=1,nz
         do side=1,2
            write(91) (vb(i,side,k),i=1,nx)
         enddo
      enddo
      return
      end
"""

def sha(p:Path)->str:
    return hashlib.sha256(p.read_bytes()).hexdigest()

def source(p:Path)->list[str]:
    blob=subprocess.run(["git","hash-object",str(p)],capture_output=True,
                        check=True,text=True).stdout.strip()
    if blob!=ORIGINAL_BLOB:
        raise ValueError("pinned untouched CALMET source blob changed")
    lines=p.read_text().splitlines(keepends=True)
    tail="".join(lines[6118:6148]).upper()
    if (lines[6118].strip().upper()!="CALL SMOOTH(U,V,UB,VB,NSMTH)"
        or "CALL DIVCEL(U,V,W,DIV,UB,VB,DIVMAX,K)" not in tail
        or "CALL WINDBC(U,V,UB,VB,K)" not in tail
        or "CALL WINDBC(U,V,UB,VB,K)" not in "".join(lines[6096:6102]).upper()):
        raise ValueError("original selected second WINDBC/SMOOTH/DIVCEL/W physical anchor drift")
    return lines

def prepare(vendor:Path,destination:Path,receipt:Path)->None:
    lines=source(vendor)
    # After original physical line 6148; no original line replacement.
    destination.parent.mkdir(parents=True,exist_ok=True)
    destination.write_text("".join(lines[:6148])+
                           "      call s4c8a_g24_after\n"+
                           "".join(lines[6148:])+HELPER)
    receipt.parent.mkdir(parents=True,exist_ok=True)
    receipt.write_text(json.dumps({
        "status":"PINNED_SOURCE_ONLY_WRITE_ONLY_G24_PREPARED",
        "original_git_blob":ORIGINAL_BLOB,
        "original_sha256":sha(vendor),
        "instrumented_sha256":sha(destination),
        "hook_after_original_DIAGNO_line":6148,
        "raw_source_mutated":False,
        "native_g24_science":"NOT_RUN",
        "g26_p7":"NOT_ACCEPTED",
    },indent=2,sort_keys=True)+"\n")
    print("S4R1C8A_ORIGINAL_G24_SCRATCH_PINNED=PASS")

def records(trace:Path)->list[tuple[int,tuple[float,...]]]:
    raw=trace.read_bytes()
    if len(raw)!=HOURS*RECORD_BYTES:
        raise ValueError("original G24 tail six-hour source record size wrong")
    decoded=[]
    unpack=struct.Struct("<"+str(COUNT)+"f")
    for h in range(HOURS):
        off=h*RECORD_BYTES
        tag,packed,sec,nx,ny,nz=HEADER.unpack_from(raw,off)
        clk=FIRST+timedelta(hours=h)
        expected=clk.year*100000+clk.timetuple().tm_yday*100+clk.hour
        if (tag,packed,sec,nx,ny,nz)!=(54,expected,0,NX,NY,NZ):
            raise ValueError(f"original post-tail clock/shape mismatch at hour {h}")
        vals=unpack.unpack_from(raw,off+HEADER.size)
        if not all(math.isfinite(x) for x in vals):
            raise ValueError(f"nonfinite original post-G24 source values hour {h}")
        decoded.append((packed,vals))
    return decoded

def verify(vendor:Path,pristine:Path,scratch:Path,trace:Path,report:Path)->None:
    source(vendor)
    if sha(pristine)!=sha(scratch):
        raise ValueError("G24 write-only scratch changed original six-hour 45-field MET")
    decoded=records(trace)
    first=decoded[0][1]
    uv=first[:COUNTS[0]+COUNTS[1]]
    w=first[COUNTS[0]+COUNTS[1]:sum(COUNTS[:3])]
    if len(uv)!=2*N*NZ or len(w)!=N*(NZ+1):
        raise ValueError("original G24 tail U/V/W shape not source-correct")
    if not any(abs(x)>1e-8 for x in uv):
        raise ValueError("original G24 tail wind unexpectedly all zero")
    result={
        "status":"PASS_GENUINE_NOAA_ORIGINAL_POST_G24_SOURCE_REFERENCE_ONLY",
        "original_vendor_git_blob":ORIGINAL_BLOB,
        "original_pristine_met_sha256":sha(pristine),
        "original_instrumented_met_sha256":sha(scratch),
        "original_met_byte_identical":True,
        "original_full_six_hour_tail_sha256":sha(trace),
        "hourly_original_packed_keys":[x[0] for x in decoded],
        "dimensions":[NX,NY,NZ],
        "components_per_record":list(COUNTS),
        "float_components_per_record":COUNT,
        "original_first_hour_nonzero_horizontal_wind":sum(abs(x)>1e-8 for x in uv),
        "original_first_hour_nonzero_vertical_wind":sum(abs(x)>1e-8 for x in w),
        "native_first_hour_g24":"NOT_RUN",
        "complete_g26_p7":"NOT_ACCEPTED",
        "p5_original_wind_mask":"UNCHANGED",
    }
    report.parent.mkdir(parents=True,exist_ok=True)
    report.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print("S4R1C8A_GENUINE_ORIGINAL_6H_G24_TAIL=PASS_REFERENCE_ONLY")
    print("S4R1C8A_ORIGINAL_6H45_MET=BYTE_IDENTICAL")
    print("S4R1C8A_NATIVE_G24_G26_P7=NOT_ACCEPTED")

def selftest()->None:
    with tempfile.TemporaryDirectory() as d:
        trace=Path(d)/NAME
        with trace.open("wb") as f:
            for h in range(HOURS):
                clk=FIRST+timedelta(hours=h)
                packed=clk.year*100000+clk.timetuple().tm_yday*100+clk.hour
                f.write(HEADER.pack(54,packed,0,NX,NY,NZ))
                f.write(bytes(4*COUNT))
        assert len(records(trace))==HOURS
        payload=bytearray(trace.read_bytes())
        payload[0]=55
        trace.write_bytes(payload)
        try:records(trace)
        except ValueError:pass
        else:raise AssertionError("G24 accepted corrupted original record")
    print("S4R1C8A_ORIGINAL_6H_TAIL_SCHEMA_NEGATIVE_SELFTEST=PASS")

def main()->None:
    p=argparse.ArgumentParser()
    sub=p.add_subparsers(dest="cmd",required=True)
    a=sub.add_parser("prepare")
    for key in ("vendor","destination","receipt"):
        a.add_argument("--"+key,required=True,type=Path)
    b=sub.add_parser("verify")
    for key in ("vendor","pristine","scratch","trace","report"):
        b.add_argument("--"+key,required=True,type=Path)
    sub.add_parser("selftest")
    z=p.parse_args()
    if z.cmd=="prepare":prepare(z.vendor,z.destination,z.receipt)
    elif z.cmd=="verify":verify(z.vendor,z.pristine,z.scratch,z.trace,z.report)
    else:selftest()
if __name__=="__main__":main()
