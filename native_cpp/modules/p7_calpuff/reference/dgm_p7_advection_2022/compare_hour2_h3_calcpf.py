#!/usr/bin/env python3
"""Original-vs-native *physical same-step* CALCPF REAL4 diagnostic, hour 2.

This tool consumes independent original CALPUFF write-only Fortran trace and
native single-authority COMP trace. Original trace/puff.con are NEVER inputs
to the C++ solver. A diagnostic comparison exit zero does NOT imply parity.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import struct

SOURCE = struct.Struct("<3i13f")
FREC = struct.Struct("<3if")
NAMES = ("syrec","szrec","zpr","zrpole","f1","xi1","xi2",
         "t1","t2","qold","qnew","xtemp","conc")
PRIORITY = ("qold","qnew","syrec","szrec","zpr","zrpole",
            "f1","xi1","xi2","t1","t2","xtemp","conc")


def u32(number: float) -> int:
    return struct.unpack("<I",struct.pack("<f",number))[0]


def read_original(path: Path, lower: int, upper: int, puff_max: int) -> dict[int, tuple]:
    result = {}
    with path.open("rb") as handle:
        while block := handle.read(SOURCE.size):
            if len(block)!=SOURCE.size:
                raise ValueError("original CALCPF record truncated")
            block2=handle.read(FREC.size)
            if len(block2)!=FREC.size:
                raise ValueError("original paired receptor FREC truncated")
            seq,episode,ksam,*numbers=SOURCE.unpack(block)
            seq2,episode2,ksam2,frac=FREC.unpack(block2)
            if (seq,episode,ksam)!=(seq2,episode2,ksam2):
                raise ValueError("source paired CALCPF/FREC physical keys differ")
            if not lower<=seq<=upper or not 1<=episode<=puff_max or not 1<=ksam<=99:
                raise ValueError(f"bad original real hour2 physical key {seq}/{episode}/{ksam}")
            if seq in result:
                raise ValueError("original physical substep duplicated")
            result[seq]=(episode,ksam,dict(zip(NAMES,numbers)),frac)
    if not result or list(result)!=sorted(result):
        raise ValueError("original CALCPF hour2 trace empty or unordered")
    return result


def read_native(path: Path, lower: int, upper: int) -> dict[int, tuple]:
    result={}
    for row in path.read_text().splitlines():
        words=row.split()
        if len(words)!=16:
            raise ValueError(f"native hour2 must have 3 keys +13 REAL4 stages: {row}")
        seq,episode,ksam=map(int,words[:3])
        if seq in result or not lower<=seq<=upper:
            raise ValueError(f"duplicate/invalid native step {seq}")
        result[seq]=(episode,ksam,dict(zip(NAMES,(float(v) for v in words[3:]))))
    if not result or list(result)!=sorted(result):
        raise ValueError("native CALCPF hour2 trace empty or unordered")
    return result


def main() -> None:
    p=argparse.ArgumentParser()
    p.add_argument("--original",type=Path,required=True)
    p.add_argument("--native",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    p.add_argument("--hour",type=int,choices=(2,4,9),default=2)
    p.add_argument("--receptor-i",type=int,default=None,
                   help="1-based receiver i; H9 first-residual trace override")
    p.add_argument("--receptor-j",type=int,default=None,
                   help="1-based receiver j; H9 first-residual trace override")
    a=p.parse_args()
    lower,upper,puff_max,ix,jy={
        2:(1276,3517,137,25,28),
        4:(5424,7555,272,47,13),
        # First residual after source-exact 8 contiguous hours.
        9:(16420,16679,618,25,1)
    }[a.hour]
    if (a.receptor_i is None)!=(a.receptor_j is None):
        raise ValueError("both receptor coordinates must be specified")
    if a.receptor_i is not None:
        if a.hour!=9 or not (1<=a.receptor_i<=50 and 1<=a.receptor_j<=50):
            raise ValueError("receptor override is only supported for H9 frozen 50x50")
        ix,jy=a.receptor_i,a.receptor_j
    source=read_original(a.original,lower,upper,puff_max)
    native=read_native(a.native,lower,upper)
    common=sorted(source.keys() & native.keys())
    if not common:
        raise AssertionError("original/native hour2 receptor has no common physical substeps")
    counts={k:0 for k in NAMES}
    first=None
    identity_mismatch=0
    largest={k:0.0 for k in NAMES}
    stage_differences={k:[] for k in NAMES}
    for seq in sorted(source.keys()|native.keys()):
        orig=source.get(seq);nat=native.get(seq)
        if orig is None or nat is None:
            if first is None:
                first={"seq":seq,"stage":"RECEPTOR_COVERAGE",
                       "original_present":orig is not None,
                       "native_present":nat is not None}
            continue
        oi,ok,ov,_frac=orig
        ni,nk,nv=nat
        if (oi,ok)!=(ni,nk):
            identity_mismatch+=1
            if first is None:
                first={"seq":seq,"stage":"EPISODE_KSAM",
                       "original":[oi,ok],"native":[ni,nk]}
            continue
        for name in NAMES:
            ob,nb=u32(ov[name]),u32(nv[name])
            if ob==nb:
                counts[name]+=1
            else:
                stage_differences[name].append({
                    "seq":seq,"puff":oi,"ksam":ok,
                    "original":ov[name],"native":nv[name],
                    "original_bits":f"0x{ob:08x}",
                    "native_bits":f"0x{nb:08x}",
                    "absolute_error":abs(ov[name]-nv[name]),
                })
            largest[name]=max(largest[name],abs(ov[name]-nv[name]))
        if first is None:
            for name in PRIORITY:
                if u32(ov[name])!=u32(nv[name]):
                    first={"seq":seq,"puff":oi,"ksam":ok,"stage":name,
                           "original":ov[name],"native":nv[name],
                           "original_bits":hex(u32(ov[name])),
                           "native_bits":hex(u32(nv[name])),
                           "original_stages":ov,"native_stages":nv,
                           "original_frac":_frac}
                    break
    outcome={
        "status":"DIAGNOSTIC; REAL4_ACCEPTANCE_NOT_YET_CLAIMED",
        "hour":a.hour,"receptor_i":ix,"receptor_j":jy,
        "original_sampled":len(source),"native_sampled":len(native),
        "aligned_physical_substeps":len(common),
        "first_source_order_difference":first,
        "original_only":sorted(source.keys()-native.keys())[:20],
        "native_only":sorted(native.keys()-source.keys())[:20],
        "episode_ksam_mismatch":identity_mismatch,
        "stage_bitwise_equal":counts,
        "stage_max_absolute_error":largest,
        "stage_differences":stage_differences,
        "first_difference_per_stage":{
            name:(rows[0] if rows else None)
            for name,rows in stage_differences.items()},
        "all_stages_bitwise":first is None,
    }
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(outcome,indent=2)+"\n")
    print(f"P7_HEFEI_HOUR{a.hour}_H3_{ix}_{jy}_FIRST_SOURCE_DIFFERENCE=DIAGNOSTIC"
          f" ORIGINAL_SAMPLES={len(source)} NATIVE_SAMPLES={len(native)}"
          f" ALIGNED={len(common)}"
          f" FIRST={json.dumps(first,sort_keys=True) if first else 'NONE'}"
          " FULL_6H_CONCENTRATION_PARITY=OPEN")
    print(f"P7_HEFEI_HOUR{a.hour}_{ix}_{jy}_STAGE_BITWISE "+
          " ".join(f"{key}={counts[key]}/{len(common)}" for key in PRIORITY))
    for name in ("zrpole","f1","xtemp","conc"):
        rows=stage_differences[name]
        print(f"P7_HEFEI_HOUR{a.hour}_{ix}_{jy}_STAGE_DIVERGENCES"
              f" STAGE={name.upper()} COUNT={len(rows)}"
              f" PHYSICAL_KEYS={json.dumps(rows,sort_keys=True,separators=(',',':'))}")


if __name__=="__main__":
    main()
