#!/usr/bin/env python3
"""G30A: independent on-disk P6F candidate and upstream G24/G28/G29 handoff.

Reads raw Fortran-sequential records with struct, NOT the C++ P6F decoder.
Checks all 45 source-native arrays, canonical records, timestamps, geography,
and bitwise REAL*4 identity of 38 records independently emitted by earlier
G24 winds, G28 AVEMIX/WSTARR, and G29 temperature stage.

This verifies source-field handoff and P6F layout only. It DOES NOT compare
the candidate with a full original CALMET multi-station weather run.
"""
from __future__ import annotations
import argparse
import csv
import datetime as dt
import hashlib
import json
import math
import struct
from pathlib import Path

from verify_g18c6_independent_binary import fortran_records

NX,NY,NZ=12,12,9
N=NX*NY
SCALE=struct.Struct("<f")
LABELS=(sum(([f"U-LEV{k:3d}",f"V-LEV{k:3d}",f"WFACE{k:3d}"]
            for k in range(1,NZ+1)),[]) +
        [f"T-LEV{k:3d}" for k in range(1,NZ+1)] +
        ["IPGT    ","USTAR   ","ZI      ","EL      ","WSTAR   ",
         "TEMPK   ","RHO     ","QSW     ","IRH     "])
assert len(LABELS)==45

def bits(x:float)->bytes:
    if not math.isfinite(x):
        raise ValueError("nonfinite source stage scalar")
    return SCALE.pack(x)

def load_csv(path:Path,columns:tuple[str,...],dimensions:tuple[str,...]):
    with path.open(newline="") as stream:
        reader=csv.DictReader(stream)
        if set(reader.fieldnames or ()) != set(columns):
            raise ValueError(f"unexpected source-stage columns: {path}")
        result={}
        for row in reader:
            key=tuple(int(row[x]) for x in dimensions)
            if key in result:
                raise ValueError("duplicate stage grid cell")
            if not 1 <= key[0] <= NX or not 1 <= key[1] <= NY or (
                    len(key)==3 and not 1 <= key[2] <= NZ):
                raise ValueError("source-stage cell outside 12x12x9")
            result[key]=row
    n_expected=N*(NZ if len(dimensions)==3 else 1)
    if len(result)!=n_expected:
        raise ValueError(f"missing {n_expected-len(result)} source-stage grid cells in {path}")
    return result

def source_hour_clock(path:Path):
    with path.open(newline="") as stream:
        reader=csv.DictReader(stream)
        if set(reader.fieldnames or ()) != {
                "hour_end_utc_seconds","k_1based","j_1based","i_1based",
                "u_mps_real4","v_mps_real4"}:
            raise ValueError("G30A source WIND1 clock columns missing")
        stamps=set()
        count=0
        for row in reader:
            stamps.add(int(row["hour_end_utc_seconds"]))
            count+=1
    if len(stamps)!=1 or count!=N*NZ:
        raise ValueError("G30A source original G21 first-hour time not unique")
    end=dt.datetime.fromtimestamp(stamps.pop(),dt.timezone.utc)
    start=end-dt.timedelta(hours=1)
    if any(x.minute or x.second or x.microsecond for x in (start,end)):
        raise ValueError("G30A source time not exactly hourly")
    def header(x):
        return (x.year,x.month,x.day,x.hour,0)
    packed=(start.year*100000+start.timetuple().tm_yday*100+start.hour)
    return header(start),header(end),packed


def parse_bin(path:Path,expected_clock):
    records=fortran_records(path.read_bytes())
    if records[0][:16].decode("ascii").strip()!="CALMET.DAT" or (
            records[0][16:32].decode("ascii").strip()!="2.1"):
        raise ValueError("G30A wrong Fortran CALMET.DAT version")
    if len(records[0]) != 96:
        raise ValueError("G30A invalid Fortran header")
    (comment_count,)=struct.unpack("<i",records[1])
    if not 1 <= comment_count <= 30:
        raise ValueError("G30A invalid comment count")
    comments=records[2:2+comment_count]
    if len(comments)!=comment_count or any(len(x)!=132 for x in comments):
        raise ValueError("G30A corrupted comments")
    if not any(b"test-only" in x for x in comments):
        raise ValueError("G30A missing nonproduction file provenance")
    control=records[2+comment_count]
    if len(control)!=176:
        raise ValueError("G30A invalid control dimensions")
    start=struct.unpack_from("<5i",control,0)
    end=struct.unpack_from("<5i",control,20)
    timezone=control[40:48].decode("ascii")
    irlg,irtype,nx,ny,nz=struct.unpack_from("<5i",control,48)
    grid,xorig,yorig=struct.unpack_from("<3f",control,68)
    iwfcod,nss,nus,nps=struct.unpack_from("<4i",control,80)
    if ((irlg,irtype,nx,ny,nz,iwfcod,nss,nus,nps)!=(1,1,12,12,9,1,2,2,0)
        or timezone!="UTC+0000" or grid!=10000.0
        or not all(math.isfinite(x) for x in (xorig,yorig))):
        raise ValueError("G30A unexpected source P6F grid and station controls")
    expected_start,expected_end,source_packed_hour=expected_clock
    if start!=expected_start or end!=expected_end:
        raise ValueError(f"G30A wrong source first-hour UTC clock: {(start,end)} expected {(expected_start,expected_end)}")
    static={}
    hourly=[]
    for payload in records[3+comment_count:]:
        if len(payload)<24:
            raise ValueError("G30A truncated original Fortran field")
        label=payload[:8].decode("ascii")
        bpack,bsec,epack,esec=struct.unpack_from("<4i",payload,8)
        if bpack==epack==0:
            if label in static:
                raise ValueError("G30A repeated original static field")
            static[label]=payload[24:]
        else:
            hourly.append((label,bpack,bsec,epack,esec,payload[24:]))
    required_static=("ZFACE   ","XSSTA   ","YSSTA   ","XUSTA   ","YUSTA   ",
                     "Z0      ","ILANDU  ","ELEV    ","XLAI    ","NEARS   ")
    if any(x not in static for x in required_static):
        raise ValueError("G30A source physical GEO static fields missing")
    if len(static)!=len(required_static) or len(hourly)!=45:
        raise ValueError("G30A unexpected static/45-hourly field inventory")
    if len(static["ZFACE   "])!=4*(NZ+1):
        raise ValueError("G30A source ZFACE invalid")
    for name in ("XSSTA   ","YSSTA   ","XUSTA   ","YUSTA   "):
        if len(static[name])!=8:
            raise ValueError("G30A input SS/US source coordinate missing")
    for name in ("Z0      ","ILANDU  ","ELEV    ","XLAI    ","NEARS   "):
        if len(static[name])!=4*N:
            raise ValueError("G30A source static grid corrupt")
    nears=struct.unpack(f"<{N}i",static["NEARS   "])
    if not set(nears).issubset({1,2}):
        raise ValueError("G30A source static nearest SURF ordinal invalid")
    floats={}
    ints={}
    for k,(label,bpack,bsec,epack,esec,payload) in enumerate(hourly):
        if label!=LABELS[k] or (bpack,bsec,epack,esec)!=(source_packed_hour,0,source_packed_hour,3600):
            raise ValueError(f"G30A wrong source record label/clock at {k}: {label!r}")
        if len(payload)!=N*4:
            raise ValueError(f"G30A record {k} payload size wrong")
        if label in ("IPGT    ","IRH     "):
            vals=struct.unpack(f"<{N}i",payload)
            if label=="IPGT    " and not all(1<=v<=6 for v in vals):
                raise ValueError("G30A invalid original IPGT")
            if label=="IRH     " and not all(0<=v<=100 for v in vals):
                raise ValueError("G30A invalid original IRH")
            ints[label]=vals
        else:
            vals=struct.unpack(f"<{N}f",payload)
            if not all(math.isfinite(x) and x!=9999.0 for x in vals):
                raise ValueError("G30A uncomputed physical REAL4 field")
            floats[label]=vals
    return floats,ints,{"fortran_records":len(records),
                       "binary_bytes":path.stat().st_size,"nearest_ss_counts":
                       [nears.count(1),nears.count(2)],
                       "labels":LABELS,"source_first_hour":[start,end]}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--candidate",type=Path,required=True)
    p.add_argument("--wind-tail",type=Path,required=True)
    p.add_argument("--source-clock",type=Path,required=True)
    p.add_argument("--comp-prefix",type=Path,required=True)
    p.add_argument("--temp3d-prefix",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    a=p.parse_args()
    winds=load_csv(a.wind_tail,("i","j","k","u","v","div","w_below","w_above"),("i","j","k"))
    comp=load_csv(Path(str(a.comp_prefix)+".native.csv"),
                  ("i","j","zi_after_avemix_m","ziconv_after_avemix_m","wstar_mps"),("i","j"))
    temp=load_csv(Path(str(a.temp3d_prefix)+".native.csv"),("i","j","k","temp_k"),("i","j","k"))
    floats,ints,metadata=parse_bin(a.candidate,source_hour_clock(a.source_clock))
    expected={}
    for k in range(1,NZ+1):
        expected[f"U-LEV{k:3d}"]={(i,j):winds[i,j,k]["u"] for j in range(1,NY+1) for i in range(1,NX+1)}
        expected[f"V-LEV{k:3d}"]={(i,j):winds[i,j,k]["v"] for j in range(1,NY+1) for i in range(1,NX+1)}
        expected[f"WFACE{k:3d}"]={(i,j):winds[i,j,k]["w_above"] for j in range(1,NY+1) for i in range(1,NX+1)}
        expected[f"T-LEV{k:3d}"]={(i,j):temp[i,j,k]["temp_k"] for j in range(1,NY+1) for i in range(1,NX+1)}
    expected["ZI      "]={(i,j):comp[i,j]["zi_after_avemix_m"] for j in range(1,NY+1) for i in range(1,NX+1)}
    expected["WSTAR   "]={(i,j):comp[i,j]["wstar_mps"] for j in range(1,NY+1) for i in range(1,NX+1)}
    if len(expected)!=38:
        raise AssertionError("G30A expected 38 source-stage record cross-checks")
    mismatches=[]
    for label,staged in expected.items():
        field=floats[label]
        for j in range(1,NY+1):
            for i in range(1,NX+1):
                p=(j-1)*NX+i-1
                if bits(float(staged[i,j]))!=bits(field[p]):
                    if len(mismatches)<20:
                        mismatches.append(dict(label=label,i=i,j=j,
                                               binary=field[p],native=staged[i,j]))
    if mismatches:
        raise AssertionError(f"G30A P6F source/native field mapping mismatch: {mismatches}")
    outcome=dict(status="PASS",check="selected_first_hour_P6F_candidate_only",
                 fields=45,real_fields=len(floats),integer_fields=len(ints),
                 exact_real4_source_records=38,
                 exact_real4_scalar_checks=38*N,
                 original_calmet_45_field_science_parity="NOT_TESTED",
                 stage_record_fields=list(expected), 
                 candidate_sha256=hashlib.sha256(a.candidate.read_bytes()).hexdigest(),
                 metadata=metadata,source_cases_scope="selected 2SS 2US first hour only; no G14 commit")
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(outcome,indent=2)+"\n")
    print(json.dumps({key:outcome[key] for key in
          ("status","fields","exact_real4_source_records","exact_real4_scalar_checks",
           "original_calmet_45_field_science_parity")}))
if __name__=="__main__":main()
