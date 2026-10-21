#!/usr/bin/env python3
"""S4-R1b genuine 2SS+1US NOOW WATER HEATFX radiation reference.

Instrument only scratch copy of original CALMET 6.5.0, at the genuine
DIAGNO HEATFX -> AIRDEN -> ELUSTR source point. Compare all 378 REAL
water cell-hours to independent G19/G40 native SOLAR + frozen HEATFX.
Neither original trace nor CALMET.DAT is an input to native C++.
"""
from __future__ import annotations
import argparse
from collections import defaultdict
import hashlib
import json
import math
from pathlib import Path
import subprocess

PIN = "437f43bb7f0e51a1919e56664663e1a046986ed0"
TRACE = "s4r1b-original-water-heatfx.txt"
NX, NY, HOURS, WATER = 82, 85, 6, 63
FIELDS = 10

def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def source(path: Path) -> list[str]:
    got = subprocess.run(["git", "hash-object", str(path)], check=True,
                         capture_output=True, text=True).stdout.strip()
    if got != PIN:
        raise ValueError("Refuse nonpinned original CALMET")
    lines = path.read_text(encoding="utf-8").splitlines()
    anchors = {
        5669: "call surfvar(ug(1,1,1),vg(1,1,1),tprog,temp2d,irh2d,ipcode2d,0)",
        5686: "call heatfx(sinalpc,nears,temp2d,icc,ilandu,iwat1,",
        5693: "call elustr(z0,ug,vg,zmid(1),nears,",
        5697: "elseif(isfcmet.eq.1) then",
        33080: "500   continue",
    }
    for ln, expected in anchors.items():
        if lines[ln - 1].strip().lower() != expected:
            raise ValueError(f"Original Fortran line {ln} no longer original")
    return lines

def prepare(vendor: Path, dest: Path, receipt: Path) -> None:
    lines = source(vendor)
    # Insert immediately before original 5697 ELSEIF, still within the
    # ISFCMET=0 branch, AFTER second DIAGNO SURFVAR/HEATFX/ELUSTR.
    # Never sample final COMP (its third SURFVAR and WATER can overwrite).
    patch = [
        f"      open(unit=94,file='{TRACE}',",
        "     1  status='unknown',position='append',action='write')",
        "      do j=1,ny",
        "      do i=1,nx",
        "      if(ilandu(i,j).ge.iwat1.and.ilandu(i,j).le.iwat2)then",
        "      write(94,9812) i,j,nhrz,ilandu(i,j),nears(i,j),",
        "     1 icc(nears(i,j)),sinalpc(i,j),qsw(i,j),qh(i,j),temp2d(i,j)",
        "      endif",
        "      enddo",
        "      enddo",
        " 9812 format(6(i6,1x),4(es23.15,1x))",
        "      close(unit=94)",
    ]
    result: list[str] = []
    for ln, s in enumerate(lines, 1):
        if ln == 5697:
            result.extend(patch)
        result.append(s)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text("\n".join(result) + "\n", encoding="utf-8")
    receipt.parent.mkdir(parents=True, exist_ok=True)
    receipt.write_text(json.dumps({
        "status": "S4R1B_ORIGINAL_HEATFX_WATER_SCRATCH_ONLY",
        "original_calmet_blob": PIN,
        "original_sha256": sha(vendor),
        "instrumented_sha256": sha(dest),
        "insertion_line": 5697,
        "inserted_lines": len(patch),
        "native_numerical_parity": "NOT_RUN",
        "vendor_original_mutated": False,
    }, indent=2, sort_keys=True) + "\n")
    print("S4R1B_EXACT_ORIGINAL_DIAGNO_HEATFX_INSTRUMENT=PREPARED")

def _rows(path: Path) -> dict[tuple[int,int,int], tuple[int,int,int,float,float,float,float]]:
    rows: dict[tuple[int,int,int], tuple[int,int,int,float,float,float,float]] = {}
    for line in path.read_text().splitlines():
        parts = line.split()
        if len(parts) != FIELDS:
            raise ValueError(f"Original/native WATER shortwave trace arity={len(parts)}")
        i,j,hr,category,near,cloud = map(int,parts[:6])
        sine,qsw,qh,t = [float(x.replace("D","E")) for x in parts[6:]]
        key = i,j,hr
        if (key in rows or not (1<=i<=NX and 1<=j<=NY)
                or not 50<=category<=55 or not 1<=near<=2
                or not 0<=cloud<=10 or not all(map(math.isfinite,(sine,qsw,qh,t)))):
            raise ValueError(f"Invalid or duplicate WATER record {key}")
        rows[key] = category,near,cloud,sine,qsw,qh,t
    return rows

def verify(vendor: Path, deck: Path, geo: Path, original_met: Path,
           instrumented_met: Path, original_trace: Path,
           cpp_trace: Path, result: Path) -> None:
    source(vendor)
    from native_cpp.reference.compare_p3_makegeo_dynamic import parse_geo
    if sha(original_met)!=sha(instrumented_met):
        raise ValueError("Instrumentation changed original full 45-field MET.DAT bytes")
    grid=parse_geo(geo,nx=NX,ny=NY,zone=50,hem="N",x0=426.590,
                   y0=3464.125,dx=1.)
    cells={(k%NX+1,k//NX+1) for k,cat in enumerate(grid["category"])
           if 50<=int(cat)<=55}
    if len(cells)!=WATER:
        raise ValueError(f"Original genuine GEO WATER changed: {len(cells)}")
    original=_rows(original_trace)
    native=_rows(cpp_trace)
    if len(original)!=WATER*HOURS or set(native)!=set(original):
        raise ValueError(f"Actual 63x6 original/native source coverage differs {len(original)} {len(native)}")
    hours=defaultdict(set)
    max_sine,max_qsw=0.,0.
    max_sine_key,max_qsw_key=None,None
    positive_hours=set()
    for key in original:
        i,j,hr=key
        if (i,j) not in cells:raise ValueError("Source original GEO and original traced WATER not identical")
        hours[hr].add((i,j))
        oc,on,occ,os,oq,oh,ot=original[key]
        nc,nn,ncc,ns,nq,nh,nt=native[key]
        if (oc,on,occ)!=(nc,nn,ncc):
            raise ValueError(f"G40 genuine GEO/source-SETCOM NEARS/cloud mismatch at {key} {original[key][:3]} {native[key][:3]}")
        if oh!=0.0 or nh!=0.0:
            raise ValueError(f"Original HEATFX prior WATER QH not neutral zero at {key}: {oh}/{nh}")
        if not (180<=ot<=350 and 180<=nt<=350):
            raise ValueError(f"Observed-derived vs original SURFVAR temp invalid {key}")
        sine_error=abs(os-ns)
        qsw_error=abs(oq-nq)
        if sine_error>max_sine:
            max_sine,max_sine_key=sine_error,key
        if qsw_error>max_qsw:
            max_qsw,max_qsw_key=qsw_error,key
        if oq>0:positive_hours.add(hr)
        # Distinct original two code paths (vendor REAL4 arrays vs native
        # independently built SOLAR/HEATFX); no exact bit comparison claim.
        if sine_error>1e-3 or qsw_error>0.05:
            raise ValueError(f"Real WATER QSW/solar numerical parity failed at {key}: "
                             f"original (sin={os},qsw={oq}), C++ (sin={ns},qsw={nq}), "
                             f"error sin={sine_error}, qsw={qsw_error}")
    if len(hours)!=HOURS or set(hours)!={2,3,4,5,6,7} or any(ids!=cells for ids in hours.values()):
        raise ValueError(f"Original genuine 6-hour observation coverage changed {sorted(hours)}")
    if not positive_hours:
        raise ValueError("S4R1b never independently exercised positive day shortwave")
    report={
        "status":"S4R1B_REAL_NOAA_63_WATER_CELLS_X6H_QSW_SOURCE_NATIVE_PARITY_PASS_SCOPED",
        "source":"genuine NOAA 2022 2SS+1US 82x85 from case B0",
        "original_calmet_blob": PIN,
        "original_metinp_sha256": sha(deck),
        "original_geo_sha256": sha(geo),
        "original_met_sha256": sha(original_met),
        "instrumented_met_sha256": sha(instrumented_met),
        "original_45field_met_byte_identical":True,
        "actual_original_water_cells":WATER,
        "original_observed_hours":HOURS,
        "original_water_cell_hour_numeric_qsw_comparisons":WATER*HOURS,
        "source_nears_cloud_lu_identical":True,
        "neutral_original_and_native_water_qh_all_zero":True,
        "strict_qsw_absolute_tolerance_wm2":0.05,
        "strict_sinalpc_absolute_tolerance":0.001,
        "max_sinalpc_absolute_residual":max_sine,
        "max_sinalpc_cell_hour":max_sine_key,
        "max_qsw_wm2_absolute_residual":max_qsw,
        "max_qsw_cell_hour":max_qsw_key,
        "positive_hour_shortwave_observed":sorted(positive_hours),
        "native_QSW_provenance":"ACTUAL_SOURCE_GEO_AND_NOAA_CLOUD_NATIVE_SOLAR_FROZEN_P6E_HEATFX",
        "original_temperature": "TRACED_NOT_USED_AS_CPP_INPUT",
        "cpp_temperature_carrier":"REAL_RDSN_SURFVAR_OBS_NOT_POST_FRADJ",
        "real_post_fradj_two_pass_iavet_and_land_QH_Elustr":"NOT_ACCEPTED",
        "real_native_G24_water_UV":"NOT_RUN",
        "full_G14_G26_45_field_original_vs_native":"NOT_RUN",
        "P7":"BLOCKED",
    }
    result.parent.mkdir(parents=True,exist_ok=True)
    result.write_text(json.dumps(report,sort_keys=True,indent=2)+"\n")
    print("S4R1B_REAL_NOAA_63x6_WATER_QSW_QH_NATIVE_VS_ORIGINAL=PASS_SCOPED")
    print("S4R1B_ORIGINAL_VENDOR_ALL_45_FIELDS_BYTE_IDENTICAL=PASS")
    print("S4R1B_G24_NATIVE_WATER_WIND_AND_G26_45FIELDS=NOT_RUN")

def main():
    p=argparse.ArgumentParser()
    sub=p.add_subparsers(dest="mode",required=True)
    q=sub.add_parser("prepare")
    for k in ("vendor","out","receipt"):q.add_argument("--"+k,required=True,type=Path)
    q=sub.add_parser("verify")
    for k in ("vendor","deck","geo","original-met","instrumented-met",
              "original-trace","cpp-trace","result"):
        q.add_argument("--"+k,required=True,type=Path)
    a=p.parse_args()
    if a.mode=="prepare":prepare(a.vendor,a.out,a.receipt)
    else:verify(a.vendor,a.deck,a.geo,a.original_met,
                a.instrumented_met,a.original_trace,a.cpp_trace,a.result)
if __name__=="__main__":main()
