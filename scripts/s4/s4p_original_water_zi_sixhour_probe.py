#!/usr/bin/env python3
"""Independent selected WATER ZI source trace; never change vendor checkout.

Runs a separately compiled, instrumented COPY of unchanged pinned original,
then compares final CALMET.DAT byte-for-byte to fresh unmodified original.
Original process controls NOWSTA=0, ITWPROG=0, IMIXH=1 ONLY.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
import subprocess
from pathlib import Path
from collections import defaultdict
from scripts.s4.s4m_real_water_original_route_audit import audit as original_route

BLOB = "437f43bb7f0e51a1919e56664663e1a046986ed0"
SOURCE_ID = "S4P_ORIGINAL_NOWSTA0_WATER_ZI_63_CELLS_SIX_HOURS"
TRACE = "s4p-original-water-zi-state.txt"

def sha(path:Path)->str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def original(vendor:Path)->list[str]:
    actual=subprocess.run(["git","hash-object",str(vendor)],check=True,
                          capture_output=True,text=True).stdout.strip()
    if actual != BLOB:
        raise ValueError("unmodified original CALMET source identity violation")
    return vendor.read_text().splitlines()

def prepare(vendor:Path, out:Path, report:Path)->None:
    lines=original(vendor)
    assertions={32708:"do 500 i=1,nx", 32815:"wt=0.",
                32964:"zimech=constw*ustar(i,j)/fcori(i,j)",
                33015:"call MIXHMC(nhrz,i,j,wt,DTHDZ,ilapse,threshw,",
                33019:"Zicold(i,j)=ziconv",
                33027:"zi(i,j)=amax1(zimech,ziconv)",
                33028:"zi(i,j)=amax1(ziminw,zi(i,j))",
                33029:"zi(i,j)=amin1(zimaxw,zi(i,j))",
                33080:"500   continue"}
    for n,v in assertions.items():
        if lines[n-1].strip().lower()!=v.lower():
            raise ValueError(f"source WATER literal original line {n} is not pinned")
    blocks={
        32708:[f"      open(unit=97,file='{TRACE}',",
               "     1     status='unknown',position='append',action='write')"],
        33080:["      write(97,9860) i,j,nhrz,ilandu(i,j),",
               "     1 zi(i,j),fcori(i,j),constw,ziminw,zimaxw,",
               "     2 zicold(i,j),dptt(i,j),ziconv,zimech",
               " 9860 format(4(i5,1x),9(es23.15,1x))"],
        33081:["      close(unit=97)"],
    }
    modified=[]
    for i,line in enumerate(lines,1):
        modified.extend(blocks.get(i,()))
        modified.append(line)
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text("\n".join(modified)+"\n")
    receipt={"status":"S4P_VENDOR_REFERENCE_COPY_PATCH_PREPARED_ONLY",
             "original_fortran_git_blob":BLOB,
             "original_sha256":sha(vendor),"instrumented_copy_sha256":sha(out),
             "original_modified":False, "insert_before_source_lines":list(blocks),
             "added_lines":sum(map(len,blocks.values())),
             "physics_admission":"NOT_ACCEPTED"}
    report.parent.mkdir(parents=True,exist_ok=True)
    report.write_text(json.dumps(receipt,sort_keys=True,indent=2)+"\n")
    print("S4P_WATER_ZI_REFERENCE_COPY_ORIGINAL_PINNED=PASS")

def verify(vendor:Path,geo:Path,deck:Path,baseline:Path,instrumented:Path,
           trace:Path, prior:Path, out:Path)->None:
    lines=original(vendor)
    route=original_route(vendor,deck,geo)
    assert route["original_READCF_controls"]=={"NOWSTA":0,"ITWPROG":0,"ICOARE":10,"IMIXH":1}
    assert route["real_water_grid_cell_count"]==63
    if sha(baseline)!=sha(instrumented):
        raise ValueError("reference instrumentation changed 45-field final original MET output")
    from native_cpp.reference.compare_p3_makegeo_dynamic import parse_geo
    g=parse_geo(geo,nx=82,ny=85,zone=50,hem="N",x0=426.590,y0=3464.125,dx=1.)
    water={(idx%82+1,idx//82+1) for idx,c in enumerate(g["category"]) if 50<=int(c)<=55}
    if len(water)!=63:raise ValueError("observed water GEO changed")
    previous=defaultdict(dict)
    for line in prior.read_text().splitlines():
        z=line.split()
        if len(z)!=13:raise ValueError("S4N fixed original row schema drift")
        i,j,h,lu,pgt=map(int,z[:5])
        previous[h][i,j]=float(z[8]) # original S4N: QH USTAR EL ZI ...
    byhour=defaultdict(dict)
    for line in trace.read_text().splitlines():
        v=line.split()
        if len(v)!=13:raise ValueError(f"unexpected original WATER ZI trace width {len(v)}")
        i,j,h,lu=map(int,v[:4])
        if (i,j) not in water or h in byhour and (i,j) in byhour[h]:
            raise ValueError("invalid/repeated original water ZI coordinate")
        zi,f,constw,zmin,zmax,zold,dptt,zic,zmech=map(lambda x:float(x.replace("D","E")),v[4:])
        if not all(math.isfinite(x) for x in (zi,f,constw,zmin,zmax,zold,zic,zmech)):
            raise ValueError("nonfinite source original water mixing state")
        if not(0<f<1.e-2 and 0<constw<=10 and 0<zmin<=zi<=zmax):
            raise ValueError("unphysical original water source FCORI or mixed-height bounds")
        if zic!=0 or zold!=zmin:
            raise ValueError("original selected MIXHMC WT=0 branch ziconv/zicold differs")
        if not math.isclose(zi,max(zmin,min(zmax,zmech)),rel_tol=2e-6,abs_tol=2e-4):
            raise ValueError("original selected water ZI mechanical height clamp mismatch")
        if (i,j) not in previous[h] or not math.isclose(
                zi,previous[h][i,j],rel_tol=1e-7,abs_tol=1e-4):
            raise ValueError("independent original S4N WATER ZI differs")
        byhour[h][i,j]=(zi,f,constw,zmin,zmax,zold,zic,zmech)
    if len(byhour)!=6 or any(set(x)!=water for x in byhour.values()):
        raise ValueError("original water ZI field not exhaustive 63 cells x 6 hours")
    import statistics
    allrows=[z for x in byhour.values() for z in x.values()]
    result={"status":"S4P_ACTUAL_VENDOR_WATER_ZI_63_CELLS_X_6H_REFERENCE_PASS_ORIGINAL_ONLY",
            "original_git_blob":BLOB,
            "original_vendor_sha256":sha(vendor),
            "original_metinp_sha256":sha(deck),
            "original_geo_sha256":sha(geo),
            "instrumented_vendor_met_sha256":sha(instrumented),
            "untouched_original_met_sha256":sha(baseline),
            "whole_45_field_original_met_byte_identical":True,
            "original_water_cells":63,"original_hours":6,"original_water_rows":378,
            "original_water_ZI_m_range":[min(z[0] for z in allrows),max(z[0] for z in allrows)],
            "original_FCORI_range":[min(z[1] for z in allrows),max(z[1] for z in allrows)],
            "original_CONSTW":sorted({z[2] for z in allrows}),
            "original_ZIMINW":sorted({z[3] for z in allrows}),
            "original_ZIMAXW":sorted({z[4] for z in allrows}),
            "original_ZICOLD_range":[min(z[5] for z in allrows),max(z[5] for z in allrows)],
            "original_ZICONV_all_zero":True,
            "source_instrumentation":"SCRATCH_REFERENCE_ONLY",
            "cpp_native_water_ZI_vs_original":"NOT_RUN",
            "actual_native_FCORI_WIND":"NOT_RUN",
            "native_full_6x45":"NOT_RUN",
            "g14_g26_production":"NOT_ACCEPTED"}
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(result,sort_keys=True,indent=2)+"\n")
    print("S4P_ORIGINAL_REAL_WATER_ZI_63_CELLS_X_6H=378_INDEPENDENT_REFERENCE_PASS")
    print("S4P_FULL_ORIGINAL_CALMET_45_FIELDS_INSTRUMENTED_BYTE_IDENTICAL=PASS")

def main()->None:
    ap=argparse.ArgumentParser()
    subs=ap.add_subparsers(dest="mode",required=True)
    pre=subs.add_parser("prepare")
    for k in ("vendor","out","receipt"):pre.add_argument("--"+k,type=Path,required=True)
    v=subs.add_parser("verify")
    for k in ("vendor","geo","met","baseline","instrumented","trace","prior","out"):
        v.add_argument("--"+k,type=Path,required=True)
    args=ap.parse_args()
    if args.mode=="prepare":prepare(args.vendor,args.out,args.receipt)
    else:verify(args.vendor,args.geo,args.met,args.baseline,args.instrumented,args.trace,args.prior,args.out)
if __name__=="__main__":main()
