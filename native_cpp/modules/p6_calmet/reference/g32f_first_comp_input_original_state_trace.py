#!/usr/bin/env python3
"""G32F: locate original multi-SS COMP first divergence after G32E wind closure.

Reuse single-station pinned write-only original CALMET DGMSTATE kpt1..5 on
the real original full-CALMET G31 first hour. Compare against independently
native G29 MIXHT inputs, G29 output, G28 AVEMIX/WSTARR and G29 TEMP3D
surface TEMP2D. No original physics fields are supplied to C++; do not
change frozen 45-field acceptance or scientific thresholds.
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

from original_internal_state_dump import _read_records

NX=NY=12
N=NX*NY

def sha(path:Path)->str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def rows_xy(path, columns):
    data={}
    with path.open(newline="") as handle:
        source=csv.DictReader(handle)
        if not set(columns).issubset(source.fieldnames or []):
            raise ValueError("G32F invalid native CSV source columns "+str(path))
        for row in source:
            i,j=int(row["i"]),int(row["j"])
            if not (1<=i<=NX and 1<=j<=NY) or (i,j) in data:
                raise ValueError("G32F invalid/duplicate native grid point")
            vals={c:float(row[c]) for c in columns}
            if not all(math.isfinite(x) for x in vals.values()):
                raise ValueError("G32F nonfinite selected native cell")
            data[i,j]=vals
    if len(data)!=N:raise ValueError("G32F incomplete native grid")
    return data

def read_mixht_source(path):
    lines=path.read_text().splitlines()
    head=lines[0].split()
    if len(head)!=5 or list(map(int,head[:4]))!=[1,NX,NY,2]:
        raise ValueError("G32F original MIXHT source layout unexpected")
    level=int(head[4])
    if level<2 or level>10:
        raise ValueError("G32F source UP level count invalid")
    expected=2+2+4*level+N
    if len(lines)!=expected:
        raise ValueError(f"G32F MIXHT source count {len(lines)} != {expected}")
    data={}
    for index,line in enumerate(lines[4+4*level:]):
        values=line.split()
        if len(values)!=11:
            raise ValueError("G32F MIXHT source cell fields not all present")
        i,j=index//NY+1,index%NY+1
        vals=list(map(float,values))
        if not all(math.isfinite(x) for x in vals):
            raise ValueError("G32F MIXHT source nonfinite")
        data[i,j]={"QH":vals[0],"USTAR":vals[1],"EL":vals[2],
                   "RHO":vals[3]}
    return data

def read_temp3d_source(path):
    lines=path.read_text().splitlines()
    if list(map(int,lines[0].split()))!=[1,NX,NY,9,2]:
        raise ValueError("G32F native TEMP3D source header invalid")
    # first 2 header rows, 10 ZFACE, 2 site records, 20 AA/BB thermal,
    # then 144 actual surface-temperature / convective-ZI rows, i outer.
    skipped=2+10+2+20
    if len(lines)!=skipped+N:
        raise ValueError("G32F native TEMP3D source cell inventory changed")
    data={}
    for index,line in enumerate(lines[skipped:]):
        vals=list(map(float,line.split()))
        if len(vals)!=2 or not all(map(math.isfinite,vals)):
            raise ValueError("G32F invalid original temp input")
        i,j=index//NY+1,index%NY+1
        data[i,j]={"TEMP2D":vals[0]}
    return data

def source_state(path):
    rows=_read_records(path)
    if [r["kpt"] for r in rows]!=[1,2,3,4,5]:
        raise ValueError("G32F expected single original COMP hour kpt1→5")
    if any((r["nx"],r["ny"])!=(NX,NY) or r["nh"]!=1 for r in rows):
        raise ValueError("G32F original selected source geometry/hour drift")
    if len({(r["nyr"],r["ijul"],r["ihr"],r["isec"]) for r in rows})!=1:
        raise ValueError("G32F source COMP hour not single UTC hour")
    return {r["kpt"]:r for r in rows}

def compare(stage,label,original,native):
    deltas=[]
    mismatches=0
    first=None
    for j in range(1,NY+1):
        for i in range(1,NX+1):
            ref=original[(j-1)*NX+i-1]
            val=native[i,j][label]
            if not math.isfinite(ref):
                raise ValueError("G32F nonfinite original COMP")
            # Source native CSV uses float max_digits10, roundtrip REAL*4.
            val=struct.unpack("<f",struct.pack("<f",val))[0]
            gap=abs(ref-val)
            if struct.pack("<f",ref)!=struct.pack("<f",val):
                mismatches+=1
                if first is None:
                    first={"i":i,"j":j,"original":ref,"native":val,
                           "abs":gap}
            deltas.append(gap)
    return {"stage":stage,"field":label,"bit_mismatches":mismatches,
            "max_abs":max(deltas),
            "rms":math.sqrt(sum(x*x for x in deltas)/N),
            "first_bit_difference":first}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--original-dgm-state",type=Path,required=True)
    p.add_argument("--untouched-met",type=Path,required=True)
    p.add_argument("--instrumented-met",type=Path,required=True)
    p.add_argument("--frozen-verdict",type=Path,required=True)
    p.add_argument("--native-mixht-source",type=Path,required=True)
    p.add_argument("--native-temp3d-source",type=Path,required=True)
    p.add_argument("--native-mixht",type=Path,required=True)
    p.add_argument("--native-avemix-wstarr",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    args=p.parse_args()
    result={"status":"BLOCKED","scope":"G32F original first full multi-station COMP DGM kpt1..5 versus separately native source stages; diagnosis only",
            "scientific_status":"FAIL_NUMERIC"}
    try:
        verdict=json.loads(args.frozen_verdict.read_text())
        if (verdict.get("status")!="FAIL_NUMERIC" or
            verdict.get("fields_per_hour")!=45 or
            verdict.get("intervals")!=1):
            raise ValueError("G32F original frozen science verdict not genuine")
        if sha(args.untouched_met)!=sha(args.instrumented_met):
            raise ValueError("G32F pinned write-only original instrumented MET.DAT changed")
        states=source_state(args.original_dgm_state)
        mixed=read_mixht_source(args.native_mixht_source)
        mixed.update({}) # no silent original data injection
        surface=read_temp3d_source(args.native_temp3d_source)
        for i,j in mixed:
            mixed[i,j].update(surface[i,j])
        native_mix=rows_xy(args.native_mixht,("zi_m","ziconv_m","dptt_k"))
        native_ave=rows_xy(args.native_avemix_wstarr,(
            "zi_after_avemix_m","ziconv_after_avemix_m","wstar_mps"))
        stages=[
           (1,"QH",mixed,"QH"),(1,"USTAR",mixed,"USTAR"),
           (1,"EL",mixed,"EL"),(1,"RHO",mixed,"RHO"),
           (1,"TEMP2D",mixed,"TEMP2D"),
           (3,"ZI",native_mix,"zi_m"),
           (3,"ZICONV",native_mix,"ziconv_m"),
           (3,"DPTT",native_mix,"dptt_k"),
           (4,"ZI",native_ave,"zi_after_avemix_m"),
           (4,"ZICONV",native_ave,"ziconv_after_avemix_m"),
           (5,"WSTAR",native_ave,"wstar_mps"),
           (5,"ZICONV",native_ave,"ziconv_after_avemix_m"),
        ]
        compares=[]
        for kpt,key,native,native_key in stages:
            vals={ij:{key:row[native_key]} for ij,row in native.items()}
            compares.append(compare("kpt"+str(kpt),key,
                                    states[kpt]["fields"][key],vals))
        start=states[1]
        stamp=dt.datetime(start["nyr"],1,1,tzinfo=dt.timezone.utc)+dt.timedelta(
            days=start["ijul"]-1,hours=start["ihr"],seconds=start["isec"])
        if stamp!=dt.datetime(2024,1,1,2,tzinfo=dt.timezone.utc):
            raise ValueError("G32F source first hour drifted from G19 selected daylight")
        result.update({"status":"PASS_G32F_FIRST_COMP_SOURCE_INPUT_DIAGNOSIS",
            "original_met_sha256":sha(args.untouched_met),
            "original_dgm_state_sha256":sha(args.original_dgm_state),
            "frozen_total_exceedances":verdict["total_exceedances"],
            "hour_start_utc":stamp.isoformat(),
            "comparisons":compares,
            "source_earliest_bit_difference":next(
                (x for x in compares if x["bit_mismatches"]),None),
            "scientific_status":"FAIL_NUMERIC",
            "source_frozen_reference_never_used_as_native":True,
            "single_station_precedent":"original_internal_state_dump.py kpt1..5 verified write-only single-station reference"})
    except Exception as exc:
        result["blocker"]=str(exc)
        raise
    finally:
        args.out.parent.mkdir(parents=True,exist_ok=True)
        args.out.write_text(json.dumps(result,indent=2)+"\n")
        print(json.dumps({k:([{x:row[x] for x in
            ("stage","field","bit_mismatches","max_abs","rms")} for row in v]
            if k=="comparisons" else v)
            for k,v in result.items()},indent=2))

if __name__=="__main__":
    main()
