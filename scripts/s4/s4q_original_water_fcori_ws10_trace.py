#!/usr/bin/env python3
"""Vendor-immutable source audit for WATER's actual U10/V10/WS10 and FCORI.

Reference-only instrumentation is kept in a GitHub Actions scratch directory.
It is not a port of a wind solver or a declaration of G26 parity.
"""
from __future__ import annotations
import argparse
from collections import defaultdict
import hashlib
import json
import math
from pathlib import Path
import re
import subprocess

PIN = "437f43bb7f0e51a1919e56664663e1a046986ed0"
TRACE = "s4q-original-water-u10-fcori.txt"

def sha(p:Path)->str:
    return hashlib.sha256(p.read_bytes()).hexdigest()

def vendor_lines(p:Path)->list[str]:
    blob=subprocess.run(["git","hash-object",str(p)],
        capture_output=True,text=True,check=True).stdout.strip()
    if blob != PIN:
        raise ValueError("original CALMET 6.5.0 source changed")
    return p.read_text().splitlines()

def source_real_control(deck:Path, field:str)->float:
    text=deck.read_text()
    found=re.findall(r"!\s*"+re.escape(field)+r"\s*=\s*"
                    r"([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eEdD][+-]?\d+)?)\s*!",
                    text,re.I)
    if len(found)!=1:raise ValueError(f"original {field} not unique: {found}")
    return float(found[0].replace("D","E").replace("d","e"))

def prepare(vendor:Path,dest:Path,report:Path)->None:
    source=vendor_lines(vendor)
    literal={9607:"if (fcoriol.gt.998.) then",
             9608:"f= 2*(twopi/86400.)*sin(xlat(i,j)*twopi/360.)",
             9610:"f=fcoriol",
             9614:"fcori(i,j)=max(abs(f),0.25e-4)",
             32716:"ws10=sqrt(u10(i,j)**2+v10(i,j)**2)",
             33080:"500   continue"}
    for ln,expected in literal.items():
        if source[ln-1].strip().lower()!=expected.lower():
            raise ValueError(f"pinned original FCORI/WS10 line {ln} changed")
    patches={
        32708:[
          f"      open(unit=96,file='{TRACE}',",
          "     1     status='unknown',position='append',action='write')"],
        33080:[
          "      write(96,9871) i,j,nhrz,ilandu(i,j),",
          "     1 u10(i,j),v10(i,j),ws10,fcori(i,j)",
          " 9871 format(4(i5,1x),4(es23.15,1x))"],
        33081:["      close(unit=96)"],
    }
    out=[]
    for number,line in enumerate(source,1):
        out.extend(patches.get(number,()))
        out.append(line)
    dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text("\n".join(out)+"\n")
    r={"status":"S4Q_ORIGINAL_SOURCE_ONLY_REFERENCE_COPY_PREPARED",
       "source_original_git_blob":PIN,"source_original_sha256":sha(vendor),
       "source_instrumented_copy_sha256":sha(dest),
       "source_patch_line_before":list(patches),
       "original_vendor_tree_changed":False,
       "original_vs_native_final_wind":"NOT_RUN",
       "native_45_field":"NOT_RUN"}
    report.parent.mkdir(parents=True,exist_ok=True)
    report.write_text(json.dumps(r,sort_keys=True,indent=2)+"\n")
    print("S4Q_PINNED_VENDOR_FCORI_WATER_FIRST_WIND_SOURCE=PASS")

def verify(vendor:Path,deck:Path,pristine:Path,modified:Path,trace:Path,
           s4n:Path,s4p:Path,out:Path)->None:
    vendor_lines(vendor)
    from scripts.s4.s4m_real_water_original_route_audit import audit
    # This is the ACTUAL original same NOAA source, not an extrapolation.
    # Route audit requires the original GEO, provided separately by --geo.
    if sha(pristine)!=sha(modified):
        raise ValueError("original MET.DAT changed due to WATER-only instrumentation")
    fcoriol=source_real_control(deck,"FCORIOL")
    if not math.isfinite(fcoriol) or fcoriol>998:
        raise ValueError("real site original latitude-varying FCORIOL outside this selected bridge")
    true_fcori=max(abs(fcoriol),2.5e-5)
    previous={}
    for line in s4n.read_text().splitlines():
        vals=line.split()
        if len(vals)!=13:raise ValueError("S4N WATER trace source changed")
        i,j,h=map(int,vals[:3])
        previous[i,j,h]=float(vals[-1].replace("D","E"))
    prior_fcori={}
    for line in s4p.read_text().splitlines():
        vals=line.split()
        if len(vals)!=13:raise ValueError("S4P WATER-ZI original trace changed")
        i,j,h=map(int,vals[:3])
        prior_fcori[i,j,h]=float(vals[5].replace("D","E"))
    actual={}
    hours=defaultdict(set)
    for line in trace.read_text().splitlines():
        vals=line.split()
        if len(vals)!=8:raise ValueError(f"original source trace arity {len(vals)}")
        i,j,h,land=map(int,vals[:4])
        u,v,ws,fc=map(lambda x:float(x.replace("D","E")),vals[4:])
        key=(i,j,h)
        if key in actual or key not in previous or key not in prior_fcori:
            raise ValueError("original cell/hour identity not paired with previous vendor")
        if not (1<=i<=82 and 1<=j<=85 and 50<=land<=55 and
                all(math.isfinite(x) for x in (u,v,ws,fc))):
            raise ValueError("original WATER source coordinate or scalar bad")
        if not math.isclose(ws,previous[key],rel_tol=5.e-7,abs_tol=5.e-8):
            raise ValueError("original independent WS10 reference drift")
        if not math.isclose(fc,prior_fcori[key],rel_tol=1.e-7,abs_tol=1.e-9):
            raise ValueError("original independent FCORI reference drift")
        if not math.isclose(fc,true_fcori,rel_tol=1.e-6,abs_tol=2.e-9):
            raise ValueError("original selected SETCOM source FCORI mismatch")
        if not math.isclose(math.hypot(u,v),ws,rel_tol=2.e-5,abs_tol=5.e-7):
            raise ValueError("original U10/V10 alias not the first G14 wind")
        actual[key]=(u,v,ws,fc,land)
        hours[h].add((i,j))
    if len(actual)!=378 or len(hours)!=6 or any(len(c)!=63 for c in hours.values()):
        raise ValueError("genuine 63x6 original wind source incomplete")
    if any(c!=next(iter(hours.values())) for c in hours.values()):
        raise ValueError("water geometry differs across actual original model hours")
    result={
        "status":"S4Q_REAL_63x6_VENDOR_FCORI_FIRST_WIND_SOURCE_PASS_ONLY",
        "actual_true_original_water_cell_hours":378,"water_cells":63,"hours":6,
        "vendor_original_blob":PIN,"original_sha256":sha(vendor),
        "original_metinp_sha256":sha(deck),"original_fcoriol":fcoriol,
        "original_fcori_branch":"SOURCE_CONSTANT_NOT_GLOBE",
        "original_fcori_value_s_inv":true_fcori,
        "original_pristine_calmet_sha256":sha(pristine),
        "original_instrumented_calmet_sha256":sha(modified),
        "original_45_field_output_byte_equal":True,
        "original_water_u10v10_source":"ORIGINAL_FINAL_DIAGNO_LEVEL_1_RANK_ALIAS",
        "original_ws10_definition":"SQRT_U10_SQUARED_PLUS_V10_SQUARED",
        "native_actual_G24_final_wind_63x6":"NOT_RUN",
        "cpp_water_mixing_G14_G26":"NOT_RUN",
        "full_native_vendor_270_groups":"NOT_RUN",
        "production":"NOT_ACCEPTED"}
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(result,sort_keys=True,indent=2)+"\n")
    print("S4Q_ORIGINAL_63X6_FCORI_U10_V10_WS10_SOURCE=PASS_SCOPED")
    print("S4Q_ORIGINAL_VS_INSTRUMENTED_CALMET_ALL_FIELDS=BYTE_IDENTICAL")
    print("S4Q_REAL_ACTUAL_G24_NATIVE_WIND=NOT_RUN")

def main()->None:
    ap=argparse.ArgumentParser()
    sub=ap.add_subparsers(dest="mode",required=True)
    p=sub.add_parser("prepare")
    for k in ("vendor","out","receipt"):p.add_argument("--"+k,type=Path,required=True)
    v=sub.add_parser("verify")
    for k in ("vendor","met","original","instrumented","trace","s4n","s4p","out"):
        v.add_argument("--"+k,type=Path,required=True)
    args=ap.parse_args()
    if args.mode=="prepare":prepare(args.vendor,args.out,args.receipt)
    else:verify(args.vendor,args.met,args.original,args.instrumented,
                args.trace,args.s4n,args.s4p,args.out)
if __name__=="__main__":main()
