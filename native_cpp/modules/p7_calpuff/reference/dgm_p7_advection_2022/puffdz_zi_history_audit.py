#!/usr/bin/env python3
"""Classify, never infer, CALPUFF ZIOLD/ZIMAX history from pinned original.

The analysis is intentionally read-only: it quantifies which original
vertical-state transitions remain to be implemented in native COMP. It must
not supply reference ZI values to the production solver.
"""
from __future__ import annotations
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import struct

REFERENCE_DGM="cbbdaa29c6222e6ca6aefe9f605ad13e7dd6d258f6ad243afcac07cb578108c6"
REFERENCE_ZI="3a7e519c91f26c17a649a7292435d37b09beef55f3d5d9765aace777781a14c4"
ROWS=254687

def digest(path: Path) -> str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for c in iter(lambda:f.read(1<<20),b""):h.update(c)
    return h.hexdigest()

def analyze(dgm: Path, zi: Path) -> dict:
    if dgm.stat().st_size!=ROWS*352 or digest(dgm)!=REFERENCE_DGM:
        raise ValueError("full original 143h DGM oracle drift")
    if zi.stat().st_size!=ROWS*8 or digest(zi)!=REFERENCE_ZI:
        raise ValueError("full original historical ZI oracle drift")
    prior={} # puff_id -> (raw ZIOLD bits, raw ZIMAX bits, hour)
    changes=Counter()
    first_values=Counter()
    first_examples=[]
    changed_examples=[]
    increases=Counter()
    counters=Counter()
    with dgm.open("rb") as a,zi.open("rb") as b:
        for index in range(1,ROWS+1):
            record=a.read(352)
            zraw=b.read(8)
            if len(record)!=352 or len(zraw)!=8:
                raise ValueError("short original DGM/ZI record")
            ints=struct.unpack_from("<24i",record)
            floats=struct.unpack_from("<64f",record,96)
            bits=struct.unpack("<2I",zraw)
            ziold,zimax=struct.unpack("<2f",zraw)
            puff=ints[3]
            hour=ints[1]
            if puff<=0 or ints[0]!=1 or hour//100000!=2022:
                raise ValueError(f"bad original record {index}")
            counters["rows"]+=1
            is_new=floats[19]==0.0 and floats[20]==0.0
            if is_new:
                if puff in prior:raise ValueError("duplicate initial puff id")
                counters["new_puffs"]+=1
                class_key=("10000" if ziold==10000 else
                           "dpbl" if bits[0]==struct.unpack("<I",struct.pack("<f",floats[3]))[0]
                           else "other")
                first_values[class_key]+=1
                if len(first_examples)<7:
                    first_examples.append({
                        "row":index,"puff":puff,"hour":hour,"stability":ints[8],
                        "ziold":ziold,"zimax":zimax,"dpbl":floats[3],
                        "height":floats[6],"class":class_key})
            elif puff not in prior:
                raise ValueError(f"nonnew puff without preceding record {puff}")
            if puff in prior:
                prev=prior[puff]
                if bits[0]!=prev[0] or bits[1]!=prev[1]:
                    kind=("both" if bits[0]!=prev[0] and bits[1]!=prev[1] else
                          "ziold" if bits[0]!=prev[0] else "zimax")
                    changes[kind]+=1
                    if hour!=prev[2]:counters["change_cross_hour"]+=1
                    if bits[0]!=prev[0] and ziold>struct.unpack("<f",struct.pack("<I",prev[0]))[0]:
                        increases["ziold"]+=1
                    if bits[1]!=prev[1] and zimax>struct.unpack("<f",struct.pack("<I",prev[1]))[0]:
                        increases["zimax"]+=1
                    if len(changed_examples)<12:
                        changed_examples.append({
                            "row":index,"puff":puff,"hour":hour,
                            "previous_hour":prev[2],"stability":ints[8],
                            "ziold_old":struct.unpack("<f",struct.pack("<I",prev[0]))[0],
                            "ziold_new":ziold,
                            "zimax_old":struct.unpack("<f",struct.pack("<I",prev[1]))[0],
                            "zimax_new":zimax,
                            "dpbl":floats[3],"height":floats[6],
                            "kind":kind})
                else:counters["unchanged_continuation"]+=1
            prior[puff]=(bits[0],bits[1],hour)
    counters["unique_puffs"]=len(prior)
    counters["changes"]=sum(changes.values())
    counters["continued_without_initialization"]=ROWS-counters["new_puffs"]
    return {"status":"ORIGINAL_PUFFDZ_HISTORICAL_ZI_CLASSIFIED",
            "scientific_boundary":"ORIGINAL_ORACLE_ONLY_NATIVE_UPDATE_UNPROVEN",
            "rows":ROWS,"original_dgm_sha256":REFERENCE_DGM,
            "original_zi_sha256":REFERENCE_ZI,
            "counts":dict(counters),"transition_kinds":dict(changes),
            "initial_ziold_types":dict(first_values),
            "increasing_transitions":dict(increases),
            "first_new_puff_examples":first_examples,
            "first_transition_examples":changed_examples}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--dgm",type=Path,required=True)
    p.add_argument("--zi",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    x=p.parse_args()
    result=analyze(x.dgm,x.zi)
    x.output.parent.mkdir(parents=True,exist_ok=True)
    x.output.write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps({k:result[k] for k in
          ("status","counts","transition_kinds","initial_ziold_types",
           "increasing_transitions","first_transition_examples")},indent=2))
    print("P7_ORIGINAL_ZI_HISTORY_AUDIT=PASS NATIVE_EVOLUTION=NOT_YET_VALIDATED")

if __name__=="__main__":main()
