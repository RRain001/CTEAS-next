#!/usr/bin/env python3
"""Export exactly the original REAL*4 ZII and EL passed into SIMILT.

Runs the pre-existing source-pinned original_internal_state_dump audit, which
compiles untouched and write-only-instrumented CALMET FORTRAN, requires their
MET.DAT hashes to match and checks the unchanged frozen Hefei reference.
Its point-six trace sits at calmet.for L6893 immediately before SIMILT, after
MIXHTST's local mixing-height calculation; grid ZI is NOT interchangeable.

The exported files are 143 consecutive hours of unmodified station-cell
float32 little-endian values. They must never be described as a native P6D
physics model: they are original Fortran diagnostic oracle inputs.
"""
from __future__ import annotations
import argparse
import datetime as dt
import hashlib
import json
import math
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/"native_cpp/modules/p6_calmet/reference"))
import original_internal_state_dump as source

BLOB="437f43bb7f0e51a1919e56664663e1a046986ed0"


def digest(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> None:
    cli=argparse.ArgumentParser()
    cli.add_argument("--vendor",required=True,type=Path)
    cli.add_argument("--case",required=True,type=Path)
    cli.add_argument("--out",required=True,type=Path)
    cli.add_argument("--compiler",default="gfortran-11")
    cli.add_argument("--hours",type=int,default=143)
    args=cli.parse_args()
    out=args.out.resolve()
    out.mkdir(parents=True,exist_ok=True)
    vendor=args.vendor.resolve()
    raw=(vendor/"calmet.for").read_bytes()
    blob=hashlib.sha1(f"blob {len(raw)}\0".encode()+raw).hexdigest()
    if blob!=BLOB:raise RuntimeError("original source was modified")
    # Reuse original source-locked instrumentation and its frozen output gate.
    audit_args=argparse.Namespace(vendor=vendor,case=args.case.resolve(),
                                  out=out,compiler=args.compiler)
    proof=source.audit(audit_args)
    if (proof["status"]!="ORIGINAL_MET_DAT_IDENTICAL" or
        not proof["met_dat_identical"] or
        not proof["met_dat_matches_frozen_reference"] or
        proof["runs"]["original"]["met_dat_sha256"]!=source.TARGET_MET_DAT_SHA256):
        raise RuntimeError("write-only trace is not bitwise identical to frozen original")
    dump=out/"case/run/met/dgm_cell.bin"
    state=out/"case/run/met/dgm_state.bin"
    if not dump.is_file() or not state.is_file():
        raise RuntimeError("original SIMILT source trace incomplete")
    table=source.celltable(argparse.Namespace(
        dump=dump,out=out,hours=args.hours,state_dump=state,
        station_i=26,station_j=26))
    rows=table["rows"]
    if len(rows)!=args.hours:raise RuntimeError("station source trace must have 143 hours")
    if any(row["IS"]!=26 or row["JS"]!=26 or row["NS"]!=1 for row in rows):
        raise RuntimeError("original surface-station cell/index contract changed")
    if any(row["ITPROG"]!=0 or row["IPSIFCN"]!=0 for row in rows):
        raise RuntimeError("original stability/extrapolation scope changed")
    blobbytes=dump.read_bytes()
    # Source DGM point 6 packs int32[8], int32[12], float32[13]
    # in the order listed in POINT2_FIELDS[6]. Copy two REAL*4 payloads
    # literally: preserve original 32-bit representation, not Python re-rounding.
    recsize=32+12*4+13*4
    if len(blobbytes)!=args.hours*recsize:
        raise RuntimeError(f"original cell-dump layout changed: {len(blobbytes)}")
    ziibytes=bytearray();elbytes=bytearray()
    labels=[];previous=None
    for k,row in enumerate(rows):
        start=k*recsize
        ids=struct.unpack_from("<8i",blobbytes,start)
        if ids[0]!=6 or (ids[3],ids[4],ids[5])!=(26,26,50) or ids[6:8]!=(50,9):
            raise RuntimeError("original point-six binary header drift")
        zii=struct.unpack_from("<f",blobbytes,start+80)[0]
        el=struct.unpack_from("<f",blobbytes,start+80+5*4)[0]
        if not (math.isfinite(zii) and zii>0.0 and math.isfinite(el)):
            raise RuntimeError("invalid original ZII/EL at hour "+str(k+1))
        if abs(zii-row["ZII_TO_SIMILT"])>1e-6 or abs(el-row["EL"])>1e-6:
            raise RuntimeError("original binary vs celltable disagreement")
        ziibytes.extend(blobbytes[start+80:start+84])
        elbytes.extend(blobbytes[start+100:start+104])
        instant=dt.datetime.strptime(f"{ids[1]:09d}","%Y%j%H")
        if previous is not None and instant-previous!=dt.timedelta(hours=1):
            raise RuntimeError("original station ELUSTR2 hour discontinuity")
        previous=instant
        labels.append((instant+dt.timedelta(hours=1)).strftime("%Y-%m-%d_%H"))
    expected=[(dt.datetime(2022,1,1,0)+dt.timedelta(hours=k+1)).strftime("%Y-%m-%d_%H")
              for k in range(args.hours)]
    if labels!=expected:raise RuntimeError("source-traced station times differ from frozen Hefei run")
    zii_out=out/"source_original_station_zii_143h.f32"
    el_out=out/"source_original_station_el_143h.f32"
    zii_out.write_bytes(ziibytes);el_out.write_bytes(elbytes)
    manifest={
      "status":"PASS_ORIGINAL_SIMILT_ZII_EL_SOURCE_REAL4",
      "original_git_blob":blob,
      "reference_met_dat_sha256":source.TARGET_MET_DAT_SHA256,
      "original_and_instrumented_met_dat_byte_identical":True,
      "fortran_call":"ELUSTR2: MIXHTST -> SIMILT at calmet.for L6876-L6894",
      "time":"143 consecutive original hour-end labels; begins 2022-01-01_01",
      "station_1_based":{"is":26,"js":26,"ns":1},
      "dtype":"IEEE-754 binary32 little endian (untouched original source bytes)",
      "zii_file":zii_out.name,"el_file":el_out.name,
      "hours":args.hours,"source_rows":len(rows),
      "zii_sha256":digest(zii_out),"el_sha256":digest(el_out),
      "cell_dump_sha256":digest(dump),
      "audit_sha256":digest(out/"dgm-audit.json"),
      "labels":labels,
      "scope":"original FORTRAN forcing/reference only; NOT native C++ MIXHTST/ELUSTR2",
    }
    path=out/"source_original_similt_station_manifest.json"
    path.write_text(json.dumps(manifest,indent=2)+"\n")
    print(json.dumps({k:manifest[k] for k in (
        "status","hours","station_1_based","zii_sha256","el_sha256",
        "reference_met_dat_sha256","scope")},indent=2))


if __name__=="__main__":
    main()
