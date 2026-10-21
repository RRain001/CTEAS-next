#!/usr/bin/env python3
"""S4-R1c4a independent original 6-hour WATER first-WIND1 U/V audit.

Source oracle: original CALMET Fortran DIAGNO 1st SURFVAR scratch trace
produced by the already accepted R1c1 pinned-vendor instrument. Compare
G45 real 63*6 source-native U/V; no original Fortran fields fed to G45.
"""
from __future__ import annotations
import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
from scripts.s4.s4r1c1_original_water_first_hour_diagno import pinned, _original

NX,NY=82,85
SOURCE_WATER_COUNT=63
HOURS=range(2,8)
# R1c1 frozen scientific first-hour U/V tolerance was 0.05 m/s.
# This stage may not loosen or change that accepted tolerance.
U_V_MAX_ABS_MPS=0.05

def sha(p:Path)->str:return hashlib.sha256(p.read_bytes()).hexdigest()

def verify(vendor:Path,pristine:Path,scratch:Path,original:Path,
           native:Path,deck:Path,geo:Path,surf:Path,report:Path)->None:
    pinned(vendor)
    if sha(pristine)!=sha(scratch):
        raise ValueError("G45 scientific original 6h*45 MET byte identity broken")
    table=_original(original)
    expected={}
    phases={}
    for (i,j,h,phase),(u,v,t) in table.items():
        if h not in HOURS:raise ValueError("Original source hour unexpected")
        phases.setdefault((h,phase),set()).add((i,j))
        if phase==1:expected[(h,i,j)]=(u,v)
    if len(phases)!=12 or any(len(s)!=SOURCE_WATER_COUNT for s in phases.values()):
        raise ValueError("Original 63x6 two SURFVAR phase trace not complete")
    for h in HOURS:
        if phases[h,1]!=phases[h,2]:
            raise ValueError("Original first/second same hour water identity differ")
    if len(expected)!=378:raise ValueError("Original reference count not 378")
    with native.open(newline="") as f:
        rows=list(csv.DictReader(f))
    if len(rows)!=378:raise ValueError(f"Native G45 rows not 378: {len(rows)}")
    seen=set()
    per_hour={str(h):{
        "source_hour_utc_end":f"2022-06-01T{h:02d}:00:00Z",
        "paired_water_cells":0,
        "max_abs_u_mps":0.,"max_abs_v_mps":0.,
        "max_relative_u":0.,"max_relative_v":0.,
        "max_abs_u_at":None,"max_abs_v_at":None,
        "missing_source_surface_sites":None,
        "calm_source_surface_sites":None,
        "failed_cells":0,"nonfinite_cells":0
    } for h in HOURS}
    sample_first={}
    sample_last={}
    max_abs=0.
    for row in rows:
        epoch=int(row["hour_end_utc_seconds"])
        d=datetime.fromtimestamp(epoch,timezone.utc)
        if (d.year,d.month,d.day)!=(2022,6,1) or d.hour not in HOURS:
            raise ValueError("Actual NOAA UTC source clock invalid")
        h=d.hour
        i,j=int(row["i"]),int(row["j"])
        key=h,i,j
        if not 1<=i<=NX or not 1<=j<=NY or key in seen or key not in expected:
            raise ValueError(f"G45 invalid/duplicate original WATER locator {key}")
        seen.add(key)
        if int(row["landuse"]) not in range(50,56):
            raise ValueError("G45 original water GEO category altered")
        u=float(row["wind1_u_mps"])
        v=float(row["wind1_v_mps"])
        ou,ov=expected[key]
        if not all(math.isfinite(x) for x in (u,v,ou,ov)):
            per_hour[str(h)]["nonfinite_cells"]+=1
            raise ValueError(f"G45 nonfinite source-native WIND1 {key}")
        missing=int(row["missing_surface_sites"])
        calm=int(row["calm_surface_sites"])
        if not 0<=missing<=2 or not 0<=calm<=2 or missing+calm>2:
            raise ValueError(f"Source site missing/calm flags wrong {key}")
        a=per_hour[str(h)]
        if a["missing_source_surface_sites"] is None:
            a["missing_source_surface_sites"]=missing
            a["calm_source_surface_sites"]=calm
        elif (missing,calm)!=(
            a["missing_source_surface_sites"],a["calm_source_surface_sites"]
        ):raise ValueError("G45 source station masks changed between cells")
        du,dv=abs(u-ou),abs(v-ov)
        if du>a["max_abs_u_mps"]:
            a["max_abs_u_mps"]=du;a["max_abs_u_at"]=[i,j]
        if dv>a["max_abs_v_mps"]:
            a["max_abs_v_mps"]=dv;a["max_abs_v_at"]=[i,j]
        a["max_relative_u"]=max(a["max_relative_u"],du/max(1.,abs(ou)))
        a["max_relative_v"]=max(a["max_relative_v"],dv/max(1.,abs(ov)))
        if du>U_V_MAX_ABS_MPS or dv>U_V_MAX_ABS_MPS:
            a["failed_cells"]+=1
        a["paired_water_cells"]+=1
        if h==2:sample_first[(i,j)]=(u,v)
        if h==7:sample_last[(i,j)]=(u,v)
        max_abs=max(max_abs,du,dv)
    if len(seen)!=378 or any(x["paired_water_cells"]!=SOURCE_WATER_COUNT
                            for x in per_hour.values()):
        raise ValueError("G45 six-hour native source had missing cell/hours")
    source_wind_evolves=any(
        abs(sample_first[k][0]-sample_last[k][0])>1.e-5 or
        abs(sample_first[k][1]-sample_last[k][1])>1.e-5
        for k in sample_first
    )
    if not source_wind_evolves:
        raise ValueError("G45 wind field stayed frozen at first-hour values")
    if per_hour["2"]["missing_source_surface_sites"]!=1:
        raise ValueError("G45 originally documented 583140 first-hour missing mask vanished")
    failure=sum(q["failed_cells"] for q in per_hour.values())
    record={
       "stage":"S4-R1c4a_real_noaa_2ss_1us_six_hour_source_WIND1_only",
       "scientific_label":"PASS_KERNEL_SCOPED_6H_WIND1" if failure==0 else "FAIL",
       "original_vendor_blob":"437f43bb7f0e51a1919e56664663e1a046986ed0",
       "pristine_scratch_45_field_sha_equal":True,
       "pristine_original_met_sha256":sha(pristine),
       "original_deck_sha256":sha(deck),
       "original_geo_sha256":sha(geo),
       "original_surf_sha256":sha(surf),
       "native_csv_sha256":sha(native),
       "genuine_source_water_cells":SOURCE_WATER_COUNT,
       "actual_source_hours":6,"paired_cell_hour_count":len(seen),
       "raw_p5_wind_source_mutated":False,
       "source_wind_evolves_between_hours":source_wind_evolves,
       "per_hour":per_hour,
       "max_abs_uv_mps":max_abs,
       "frozen_abs_tolerance_mps":U_V_MAX_ABS_MPS,
       "G21_G39_multi_hour_previous_ZICONV":"NOT_RUN",
       "G24_WATER_6h_final_UV":"NOT_RUN",
       "G26_native_6h_45_fields":"NOT_RUN","P7":"BLOCKED"
    }
    report.parent.mkdir(parents=True,exist_ok=True)
    report.write_text(json.dumps(record,indent=2,sort_keys=True)+"\n")
    print("S4R1C4A_WIND1_SOURCE_EVOLVES_6H=PASS")
    for h,a in per_hour.items():
        print("S4R1C4A_HOUR",h,
              "COUNT",a["paired_water_cells"],
              "MAX_U",a["max_abs_u_mps"],"MAX_V",a["max_abs_v_mps"],
              "MISSING_SS",a["missing_source_surface_sites"],
              "CALM_SS",a["calm_source_surface_sites"],
              "FAILED",a["failed_cells"])
    if failure:raise ValueError(f"G45 real original-vs-native 6h WIND1 {failure} failed cells")
    print("S4R1C4A_REAL_NOAA_63_WATER_X6H_WIND1=PASS_KERNEL_SCOPED_6H")
    print("S4R1C4A_ORIGINAL_6H_45_FIELD_MET=BYTE_IDENTICAL")
    print("S4R1C4A_NATIVE_G21_G39_G24_G26_P7=NOT_ACCEPTED")

def main()->None:
    ap=argparse.ArgumentParser()
    for key in ("vendor","pristine","scratch","original","native",
                "deck","geo","surf","report"):
        ap.add_argument("--"+key,required=True,type=Path)
    a=ap.parse_args()
    verify(a.vendor,a.pristine,a.scratch,a.original,a.native,
           a.deck,a.geo,a.surf,a.report)
if __name__=="__main__":main()
