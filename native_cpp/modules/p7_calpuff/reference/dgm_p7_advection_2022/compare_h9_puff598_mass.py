#!/usr/bin/env python3
"""Read-only original/native real H9 puff598 mass-history first-divergence audit."""
from __future__ import annotations
import argparse
import json
import math
from pathlib import Path
import struct

REC=struct.Struct("<3i5f")
FIELDS=("qold","qnew","fracdry","vd","tsamp")

def bits(v:float)->int:
    return struct.unpack("<I",struct.pack("<f",v))[0]

def original(path:Path)->dict:
    raw=path.read_bytes()
    if not raw or len(raw)%REC.size:
        raise AssertionError("original H9 puff598 mass binary missing/invalid")
    out={}
    for i in range(0,len(raw),REC.size):
        seq,puff,ksam,*vals=REC.unpack(raw[i:i+REC.size])
        if not (16420<=seq<=16679 and puff==598 and 1<=ksam<=99):
            raise AssertionError("bad source H9 puff598 key")
        if seq in out or not all(math.isfinite(x) for x in vals):
            raise AssertionError("source mass step duplicate or nonfinite")
        out[seq]=(puff,ksam,dict(zip(FIELDS,vals)))
    return out

def native(path:Path)->dict:
    out={}
    for line in path.read_text().splitlines():
        words=line.split()
        if len(words)!=8:
            raise AssertionError("native H9 puff598 mass must have 3+5 columns")
        seq,puff,ksam=map(int,words[:3])
        vals=list(map(float,words[3:]))
        if seq in out or puff!=598 or not all(math.isfinite(x) for x in vals):
            raise AssertionError("native mass step duplicate/invalid")
        out[seq]=(puff,ksam,dict(zip(FIELDS,vals)))
    return out

def main()->None:
    p=argparse.ArgumentParser()
    p.add_argument("--original",type=Path,required=True)
    p.add_argument("--native",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    p.add_argument("--require-bitwise",action="store_true",
                   help="fail closed unless every original H9 puff598 mass field is exact")
    a=p.parse_args()
    o=original(a.original)
    n=native(a.native)
    if len(o)<8 or len(n)<8:
        raise AssertionError("H9 puff598 missing physical substeps")
    first=None
    equal={f:0 for f in FIELDS}
    for seq in sorted(o.keys()|n.keys()):
        if seq not in o or seq not in n:
            if first is None:
                first={"step":seq,"stage":"COVERAGE",
                       "source":seq in o,"native":seq in n}
            continue
        op,ok,ov=o[seq]
        np,nk,nv=n[seq]
        if (op,ok)!=(np,nk):
            if first is None:
                first={"step":seq,"stage":"PUFF_KSAM",
                       "source":[op,ok],"native":[np,nk]}
            continue
        for f in FIELDS:
            if bits(ov[f])==bits(nv[f]):
                equal[f]+=1
            elif first is None:
                first={"step":seq,"puff":op,"ksam":ok,"stage":f,
                       "source":ov[f],"native":nv[f],
                       "source_bits":hex(bits(ov[f])),
                       "native_bits":hex(bits(nv[f]))}
    aligned=len(o.keys()&n.keys())
    result={
        "status":"DIAGNOSTIC_NOT_H9_ACCEPTANCE",
        "original_steps":len(o),"native_steps":len(n),
        "aligned_steps":aligned,"first":first,
        "bitwise_equal_per_field":equal,
    }
    a.out.write_text(json.dumps(result,indent=2)+"\n")
    print("P7_H9_PUFF598_FIRST_MASS_DIFFERENCE=DIAGNOSTIC"
          f" ORIGINAL_STEPS={len(o)} NATIVE_STEPS={len(n)}"
          f" ALIGNED={aligned}"
          f" FIRST={json.dumps(first,sort_keys=True) if first else 'NONE'}")
    print("P7_H9_PUFF598_MASS_REAL4 "+
          " ".join(f"{f}={equal[f]}/{aligned}" for f in FIELDS))
    if a.require_bitwise:
        if first is not None or len(o)!=8 or len(n)!=8 or aligned!=8 or \
           any(equal[f]!=8 for f in FIELDS):
            raise AssertionError("H9 puff598 original/native eight-step mass not bitwise exact")
        print("P7_H9_PUFF598_MASS_BITWISE=PASS STEPS=8 FIELDS=QOLD,QNEW,FRACDRY,VD,TSAMP 9H_H3=OPEN")

if __name__=="__main__":
    main()
