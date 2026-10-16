#!/usr/bin/env python3
"""Locate FIRST historical puff200 QOLD/DRY divergence in native vs vendor.

Original write-only Fortran full-case record is never used to initialize
native puff state. All direct scalar comparisons are float32 bitwise.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import struct

REC=struct.Struct("<3i15f")
def bits(v:float)->str:
    return f"0x{struct.unpack('<I',struct.pack('<f',v))[0]:08x}"

def main()->None:
    p=argparse.ArgumentParser()
    p.add_argument("--original",type=Path,required=True)
    p.add_argument("--native",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    p.add_argument("--require-bitwise",action="store_true",
                   help="fail if any original puff200 mass or resistance float32 bit differs")
    a=p.parse_args()
    binary=a.original.read_bytes()
    if not binary or len(binary)%REC.size:
        raise AssertionError("Fortran original puff200 mass trace missing or malformed")
    original={}
    for off in range(0,len(binary),REC.size):
        seq,ep,ks,qold,qnew,frac,vd,ratio,tsamp,vcbar,const,ra,rd,rc,rg,rf,rcut,lai=REC.unpack(binary[off:off+REC.size])
        if ep!=200 or seq in original or not 1<=seq<=11458:
            raise AssertionError("original historical puff200 record identity malformed")
        original[seq]=(ep,ks,dict(qold=qold,qnew=qnew,frac=frac,
                                   tsamp=tsamp,vd=vd,ratio=ratio,
                                   vcbar=vcbar,const=const,ra=ra,rd=rd,rc=rc,
                                   rg=rg,rf=rf,rcut=rcut,lai=lai))
    native={}
    for line in a.native.read_text().splitlines():
        words=line.split()
        if len(words)!=18:
            raise AssertionError("native 18-column float32 trace malformed: "+line)
        seq,ep,ks=map(int,words[:3])
        if seq in native or ep!=200:
            raise AssertionError("native historical puff200 step identity malformed")
        vals=list(map(float,words[3:]))
        native[seq]=(ep,ks,dict(zip(
            ("qold","qnew","frac","vd","ratio","tsamp","vcbar","const",
             "ra","rd","rc","rg","rf","rcut","lai"),vals)))
    if set(original)!=set(native):
        raise AssertionError("original/native puff200 coverage differs: "+
              f"oldOnly={sorted(set(original)-set(native))[:8]} "+
              f"nativeOnly={sorted(set(native)-set(original))[:8]}")
    if 5847 not in original:
        raise AssertionError("source first hour4 receptor disagreement step missing")
    counts={key:0 for key in
            ("qold","ra","rd","rg","rf","rcut","lai","rc","vd",
             "ratio","vcbar","const","frac","qnew","tsamp")}
    first=None
    for seq in sorted(original):
        ep,ks,ov=original[seq]
        nep,nks,nv=native[seq]
        if (ep,ks)!=(nep,nks):
            raise AssertionError(f"puff200 physical episode or KSAM mismatched at {seq}")
        for key in counts:
            match=bits(ov[key])==bits(nv[key])
            counts[key]+=int(match)
            if not match and first is None:
                first={"seq":seq,"ksam":ks,"stage":key,
                       "original":ov[key],"native":nv[key],
                       "original_bits":bits(ov[key]),"native_bits":bits(nv[key]),
                       "original_fields":ov,"native_fields":nv}
    first_5847={
        "original":original[5847][2],
        "native":native[5847][2],
        "first_diff":next((key for key in counts
              if bits(original[5847][2][key])!=bits(native[5847][2][key])),"NONE")
    }
    report={"scope":"full puff200 history across first six REAL CALPUFF MET hours",
            "all_substeps":len(original),"stage_equal":counts,
            "first_historical_difference":first,"source_step5847":first_5847,
            "full_sixhour_h3_parity":"CHECK_SEPARATE_COMPLETE_FIELD_GATE"}
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(report,indent=2)+"\n")
    print("P7_ORIGINAL_NATIVE_PUFF200_FIRST_MASS_DIVERGENCE=DIAGNOSTIC"
          f" STEPS={len(original)}"
          f" FIRST={json.dumps(first,sort_keys=True) if first else 'NONE'}")
    print("P7_PUFF200_HISTORICAL_QOLD_QNEW_FRAC_TSAMP_BITWISE "+
          " ".join(f"{key}={counts[key]}/{len(original)}" for key in counts))
    print("P7_PUFF200_DGM5847="+json.dumps(first_5847,sort_keys=True))
    if a.require_bitwise:
        if first is not None or any(n!=len(original) for n in counts.values()):
            raise AssertionError("original/native puff200 36-step REAL4 source parity regressed")
        print("P7_PUFF200_ORIGINAL_FULL_MASS_HISTORY=PASS"
              f" STEPS={len(original)} FIELDS={len(counts)}"
              " ALL_REAL4_BITWISE=YES FIRST_DIFFERENCE=NONE")
if __name__=="__main__":
    main()
