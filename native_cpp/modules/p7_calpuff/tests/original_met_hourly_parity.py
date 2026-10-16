#!/usr/bin/env python3
"""Independent original Fortran MET.DAT byte decoder vs C++ hourly snapshots.

Each of the 143 * 45 source field payloads is checked at original binary
REAL*4/INTEGER*4 bit level. This is only MET input equivalence.
"""
import argparse
import datetime as dt
import re
import struct
import subprocess
import sys

O=14695981039346656037
P=1099511628211
N=143
LABELS=([x for i in range(1,10)
         for x in (f"U-LEV{i:>3}",f"V-LEV{i:>3}",f"WFACE{i:>3}")]
        +[f"T-LEV{i:>3}" for i in range(1,10)]
        +["IPGT","USTAR","ZI","EL","WSTAR","TEMPK","RHO","QSW","IRH"])

def records(path):
    with open(path,"rb") as f:
        while True:
            start=f.read(4)
            if not start:break
            if len(start)!=4:raise ValueError("incomplete record marker")
            (length,)=struct.unpack("<i",start)
            if length<0 or length>20000000:raise ValueError("invalid record size")
            data=f.read(length);end=f.read(4)
            if len(data)!=length or len(end)!=4 or struct.unpack("<i",end)[0]!=length:
                raise ValueError("Fortran record corruption")
            yield data

def clock(packed,seconds):
    y,j,h=packed//100000,(packed%100000)//100,packed%100
    if y<1900 or y>2100 or j<1 or j>366 or h>23 or seconds<0 or seconds>3600:
        raise ValueError("invalid timestamp")
    date=dt.datetime(y,1,1,tzinfo=dt.timezone.utc)+dt.timedelta(
        days=j-1,hours=h,seconds=seconds)
    if date.year!=y:raise ValueError("Julian day exceeded year")
    return int(date.timestamp())

def original(path):
    it=iter(records(path))
    header_id=next(it)
    if not header_id.startswith(b"CALMET.DAT") or b"2.1" not in header_id[:40]:
        raise ValueError("not CALMET 2.1")
    (comments,)=struct.unpack("<i",next(it))
    if not 0<=comments<=10000:raise ValueError("bad comment count")
    for _ in range(comments):
        if len(next(it))!=132:raise ValueError("bad comment")
    header=next(it)
    if struct.unpack_from("<3i",header,56)!=(50,50,9):
        raise ValueError("original MET geometry mismatch")
    result=[];index=0;fingerprint=O;stamps=None
    for field in it:
        if len(field)<24:
            if result or index:raise ValueError("unexpected record within MET data")
            continue
        y1,s1,y2,s2=struct.unpack_from("<4i",field,8)
        if y1==y2==0 and not result and not index:continue
        if len(field)!=10024 or field[:8].decode("ascii").rstrip()!=LABELS[index]:
            raise ValueError(f"original hourly field mismatch hour={len(result)} field={index}")
        new=(y1,s1,y2,s2)
        if index==0:stamps=new
        elif stamps!=new:raise ValueError("mixed original hourly timestamps")
        for b in field[24:]:fingerprint=((fingerprint^b)*P)&0xffffffffffffffff
        index+=1
        if index==len(LABELS):
            start,end=clock(y1,s1),clock(y2,s2)
            if end-start!=3600:raise ValueError("nonhourly MET interval")
            result.append((start,end,f"{fingerprint:016x}"))
            index=0;fingerprint=O
    if len(result)!=N or index:raise ValueError("not complete 143h MET")
    return result

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--binary",required=True)
    p.add_argument("--met",required=True)
    a=p.parse_args()
    run=subprocess.run([a.binary,a.met],capture_output=True,text=True,check=True)
    native=[]
    for row in run.stdout.splitlines():
        m=re.fullmatch(r"P7_MET_HOUR (\d+) (-?\d+) (-?\d+) ([0-9a-f]{16})",row)
        if m:
            t,b,e,d=m.groups()
            if int(t)!=len(native):raise ValueError("native index not contiguous")
            native.append((int(b),int(e),d))
    authoritative=original(a.met)
    if len(native)!=N:raise ValueError(f"native hours {len(native)} instead of 143")
    for i,(x,y) in enumerate(zip(authoritative,native,strict=True)):
        if x!=y:raise ValueError(f"MET FIRST_MISMATCH hour={i} ORIGINAL={x} CPP={y}")
        if i and y[0]!=native[i-1][1]:raise ValueError("hour gap/overlap")
    if "P7_NATIVE_MET_HOURLY=PASS HOURS=143" not in run.stdout:
        raise ValueError("no native reader success marker")
    print("P7_MET_143H_REAL4_BYTES=PASS HOURS=143 FIELDS=6435"
          " CELLS_PER_FIELD=2500 ALL_FIELD_BITS_EXACT=TRUE"
          " CALPUFF_GETCELL_ADVECT_PARITY=NOT_YET_ACCEPTED")

if __name__=="__main__":
    try:main()
    except (OSError,ValueError,subprocess.CalledProcessError,StopIteration) as e:
        print("P7_MET_143H_REAL4_BYTES=FAIL "+str(e),file=sys.stderr)
        sys.exit(1)
