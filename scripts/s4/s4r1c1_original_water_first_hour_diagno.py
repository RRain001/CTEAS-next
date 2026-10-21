#!/usr/bin/env python3
"""Original CALMET DIAGNO WATER first-hour WIND1/SURFVAR/FRADJ reference.

All original Fortran instrumentation is in a disposable, SHA-pinned source
copy. The native G41 reads real GEO/SURF/UP/met.inp, never original MET/trace.
"""
from __future__ import annotations
import argparse
from collections import defaultdict
import csv
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import subprocess

BLOB="437f43bb7f0e51a1919e56664663e1a046986ed0"
TRACE="s4r1c1-original-water-diagno-firsthour.txt"
NX,NY,WATER=82,85,63

def sha(p:Path)->str:return hashlib.sha256(p.read_bytes()).hexdigest()
def pinned(p:Path)->list[str]:
    blob=subprocess.run(["git","hash-object",str(p)],check=True,
        capture_output=True,text=True).stdout.strip()
    if blob!=BLOB:raise ValueError(f"Unapproved CALMET original blob {blob}")
    lines=p.read_text().splitlines()
    pins={
      5610:"     :  call surfvar(ug(1,1,1),vg(1,1,1),tprog,temp2d,irh2d,ipcode2d,0)",
      5613:"C ---- INITIALIZE THE VERTICAL VELOCITY",
      5669:"         call surfvar(ug(1,1,1),vg(1,1,1),tprog,temp2d,irh2d,ipcode2d,0)",
      5670:"      endif",
      5672:"c NEW: frr (12/96) --- SENSIBLE HEAT FLUX ----------------------------",
    }
    for ln,raw in pins.items():
        if lines[ln-1]!=raw:raise ValueError(f"Unapproved DIAGNO anchor line {ln}")
    return lines

def prepare(vendor:Path,out:Path,receipt:Path)->None:
    source=pinned(vendor)
    # The first original SURFVAR is finished immediately before 5613,
    # and FRADJ + SECOND SURFVAR is finished immediately before 5672.
    # Water-only records prevent a 82x85 source trace becoming enormous.
    def probe(phase:int)->list[str]:
        return [
          f"      open(unit=95,file='{TRACE}',",
          "     1     status='unknown',position='append',action='write')",
          "      do j=1,ny",
          "      do i=1,nx",
          "      if(ilandu(i,j).ge.iwat1.and.ilandu(i,j).le.iwat2)then",
          f"      write(95,9877) i,j,nhrz,{phase},ug(i,j,1),vg(i,j,1),",
          "     1              temp2d(i,j)",
          "      endif",
          "      enddo",
          "      enddo",
          " 9877 format(4(i6,1x),3(es23.15,1x))",
          "      close(unit=95)",
        ]
    mods={5613:probe(1),5672:probe(2)}
    result=[]
    for i,s in enumerate(source,1):
        result.extend(mods.get(i,()))
        result.append(s)
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text("\n".join(result)+"\n")
    receipt.parent.mkdir(parents=True,exist_ok=True)
    receipt.write_text(json.dumps({
      "status":"S4R1C1_SOURCE_WATER_DIAGNO_FIRST_SECOND_SCRATCH",
      "original_blob":BLOB,"original_source_sha256":sha(vendor),
      "scratch_sha256":sha(out),"before_original_lines":[5613,5672],
      "vendor_checkout_mutated":False,
      "original_vs_native_numeric":"NOT_RUN",
    },indent=2,sort_keys=True)+"\n")
    print("S4R1C1_PINNED_VENDOR_FIRST_SECOND_WATER_WIND_INSTRUMENT=PASS_SOURCE_ONLY")

def _original(path:Path)->dict[tuple[int,int,int,int],tuple[float,float,float]]:
    out={}
    for row in path.read_text().splitlines():
        fields=row.strip().split()
        if len(fields)!=7:raise ValueError("Original G21 water row malformed")
        i,j,h,phase=map(int,fields[:4])
        if not 1<=i<=NX or not 1<=j<=NY or phase not in (1,2):
            raise ValueError("Original G21 water source coordinate")
        key=i,j,h,phase
        if key in out:raise ValueError(f"Duplicated original water {key}")
        u,v,t=(float(v.replace("D","E")) for v in fields[4:])
        if not all(math.isfinite(x) for x in (u,v,t)):
            raise ValueError("Nonfinite original water wind/T")
        out[key]=(u,v,t)
    return out

def verify(original_vendor:Path,original_met:Path,scratch_met:Path,
           geo:Path,deck:Path,fortran_trace:Path,native_csv:Path,
           output:Path)->None:
    pinned(original_vendor)
    if sha(original_met)!=sha(scratch_met):
        raise ValueError("Source instrument changed original 45-field CALMET bytes")
    from native_cpp.reference.compare_p3_makegeo_dynamic import parse_geo
    d=parse_geo(geo,nx=NX,ny=NY,zone=50,hem="N",
                x0=426.590,y0=3464.125,dx=1.)
    cells={(k%NX+1,k//NX+1) for k,cat in enumerate(d["category"])
           if 50<=int(cat)<=55}
    if len(cells)!=WATER:raise ValueError("Original GEO 63 water cells changed")
    orig=_original(fortran_trace)
    by_phase=defaultdict(set)
    for (i,j,h,p) in orig:by_phase[h,p].add((i,j))
    if len(by_phase)!=12 or any(v!=cells for v in by_phase.values()):
        raise ValueError(f"Original six-hour two-pass water coverage {[(a,len(v)) for a,v in by_phase.items()]}")
    with native_csv.open(newline="") as f:
        native=list(csv.DictReader(f))
    if len(native)!=WATER:raise ValueError(f"Native first-hour count {len(native)}")
    duplicate=set()
    maxima={name:[0.0,None] for name in
            ("wind1_u_mps","wind1_v_mps","fradj_u_mps","fradj_v_mps",
             "pre_temp_k","post_temp_k")}
    for row in native:
        i,j=int(row["i"]),int(row["j"])
        epoch=int(row["hour_end_utc_seconds"])
        hh=datetime.fromtimestamp(epoch,timezone.utc)
        if (hh.year,hh.month,hh.day,hh.hour)!=(2022,6,1,2):
            raise ValueError(f"Native original UTC source hour {hh}")
        if (i,j) not in cells or (i,j) in duplicate:
            raise ValueError("Native source water identity repeated/unknown")
        duplicate.add((i,j))
        if int(row["landuse"])!=int(d["category"][(j-1)*NX+i-1]):
            raise ValueError("Native GEO water category mismatch")
        first=orig.get((i,j,hh.hour,1))
        second=orig.get((i,j,hh.hour,2))
        if first is None or second is None:
            raise ValueError("Original native hour cell not paired")
        samples={
          "wind1_u_mps":(float(row["wind1_u_mps"]),first[0]),
          "wind1_v_mps":(float(row["wind1_v_mps"]),first[1]),
          "fradj_u_mps":(float(row["fradj_u_mps"]),second[0]),
          "fradj_v_mps":(float(row["fradj_v_mps"]),second[1]),
          "pre_temp_k":(float(row["pre_temp_k"]),first[2]),
          "post_temp_k":(float(row["post_temp_k"]),second[2]),
        }
        if float(row["qh_water_wm2"])!=0:
            raise ValueError("Native no-OW WATER heat source isn't neutral")
        for label,(value,reference) in samples.items():
            if not (math.isfinite(value) and math.isfinite(reference)):
                raise ValueError(f"{label} nonfinite")
            err=abs(value-reference)
            if err>maxima[label][0]:maxima[label]=[err,[i,j,hh.hour]]
    if duplicate!=cells:raise ValueError("Native water coverage incomplete")
    # Pin explicit numerical gates before seeing new native results. These
    # are stage-reconstruction tolerances, NOT broad 45-field acceptance.
    thresholds={name:(0.05 if "temp" not in name else 0.05)
                for name in maxima}
    report={
      "status":"S4R1C1_ACTUAL_NOAA_NATIVE_WIND1_FRADJ_63_WATER_FIRST_HOUR",
      "scope":"FIRST_HOUR_ONLY_NO_G24_NO_G26",
      "source_original_fortran_blob":BLOB,
      "source_metinp_sha256":sha(deck),"source_geo_sha256":sha(geo),
      "full_original_calmet_byte_identical":True,
      "original_calmet_sha256":sha(original_met),
      "water_cells":WATER,"native_hours":1,
      "original_6hour_phase1_phase2_water_rows":len(orig),
      "native_first_hour_water_rows":len(native),
      "max_residual":maxima,"strict_abs_tolerance":thresholds,
      "native_source_provenance":"G19_SOURCE_CLOCK_G41_G20_WIND1_G21_FRADJ_G39_HEAT",
      "native_G24_water_firstplane_final_uv":"NOT_RUN",
      "full_G14_G26_6H_45FIELD":"NOT_RUN","P7":"BLOCKED",
    }
    pass_all=all(maxima[k][0]<=thresholds[k] for k in maxima)
    report["first_hour_original_vs_native_selected_six_fields"]="PASS" if pass_all else "FAIL"
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")
    for k,(v,loc) in maxima.items():print("S4R1C1_ORIGINAL_VS_NATIVE",k,v,loc)
    if not pass_all:
        raise ValueError(f"G41 actual original-vs-native first-hour wind/FRADJ numerical residual exceeds tolerance: {maxima}")
    print("S4R1C1_TRUE_NOAA_63_WATER_FIRST_HOUR_NATIVE_WIND1_FRADJ_TEMP=PASS_SCOPED")
    print("S4R1C1_ORIGINAL_6H_45_FIELDS_UNTOUCHED=BYTE_IDENTICAL")
    print("S4R1C1_FULL_NATIVE_G24_G26_P7=NOT_ACCEPTED")

def main():
    p=argparse.ArgumentParser()
    sp=p.add_subparsers(dest="mode",required=True)
    pr=sp.add_parser("prepare")
    for k in ("vendor","out","receipt"):
        pr.add_argument("--"+k,type=Path,required=True)
    v=sp.add_parser("verify")
    for k in ("vendor","original-met","scratch-met","geo","deck",
              "fortran-trace","native-csv","output"):
        v.add_argument("--"+k,type=Path,required=True)
    x=p.parse_args()
    if x.mode=="prepare":prepare(x.vendor,x.out,x.receipt)
    else:verify(x.vendor,x.original_met,x.scratch_met,x.geo,x.deck,
                x.fortran_trace,x.native_csv,x.output)
if __name__=="__main__":main()
