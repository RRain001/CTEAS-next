#!/usr/bin/env python3
"""S4-R1c4b independent unmodified original CALMET 6970-cell first-hour
WIND1/FRADJ plus two SURFVAR U/V/T science; no vendor as native input.

Source instrumentation exists ONLY in scratch, pinned to exact original
Fortran git blob, and verifies 6h x45-field original CALMET.DAT identity.
"""
from __future__ import annotations
import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import subprocess

BLOB = "437f43bb7f0e51a1919e56664663e1a046986ed0"
TRACE = "s4r1c4b-original-6970-firsthour-two-surfvar.txt"
NX, NY, NWATER = 82, 85, 63
FIELDS = ("wind1_u_mps", "wind1_v_mps", "fradj_u_mps",
          "fradj_v_mps", "pre_temp_k", "post_temp_k")
ABS_TOL = {k: 0.05 for k in FIELDS}  # Frozen R1c1 selected G21 gate.

def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def source(vendor: Path) -> list[str]:
    blob=subprocess.run(["git","hash-object",str(vendor)],check=True,
                        capture_output=True,text=True).stdout.strip()
    if blob != BLOB: raise ValueError("Original CALMET SHA-pinned git blob changed: "+blob)
    lines=vendor.read_text().splitlines()
    expected={
        5610:"     :  call surfvar(ug(1,1,1),vg(1,1,1),tprog,temp2d,irh2d,ipcode2d,0)",
        5613:"C ---- INITIALIZE THE VERTICAL VELOCITY",
        5669:"         call surfvar(ug(1,1,1),vg(1,1,1),tprog,temp2d,irh2d,ipcode2d,0)",
        5670:"      endif",
        5672:"c NEW: frr (12/96) --- SENSIBLE HEAT FLUX ----------------------------",
    }
    for i,s in expected.items():
        if lines[i-1]!=s:
            raise ValueError(f"Original DIAGNO source anchor at {i} changed")
    return lines

def prepare(vendor:Path,dest:Path,receipt:Path):
    lines=source(vendor)
    def instrument(phase:int)->list[str]:
        fmt=9876+phase
        return [
            "      if(nhrz.eq.2)then",
            f"      open(unit=95,file='{TRACE}',",
            "     1    status='unknown',position='append',action='write')",
            "      do j=1,ny",
            "      do i=1,nx",
            f"      write(95,{fmt}) i,j,nhrz,{phase},ilandu(i,j),",
            "     1    ug(i,j,1),vg(i,j,1),temp2d(i,j)",
            "      enddo",
            "      enddo",
            f" {fmt} format(5(i6,1x),3(es23.15,1x))",
            "      close(unit=95)",
            "      endif",
        ]
    insert={5613:instrument(1),5672:instrument(2)}
    out=[]
    for i,line in enumerate(lines,1):
        out.extend(insert.get(i,()))
        out.append(line)
    dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text("\n".join(out)+"\n")
    receipt.parent.mkdir(parents=True,exist_ok=True)
    receipt.write_text(json.dumps({
        "status":"S4R1C4B_PINNED_ORIGINAL_TWO_SURFVAR_TRACE_PREPARED",
        "source_blob":BLOB,"source_sha256":sha(vendor),
        "scratch_sha256":sha(dest),
        "before_original_lines":[5613,5672],
        "original_source_checkout_mutated":False,
        "science":"NOT_RUN",
    },sort_keys=True,indent=2)+"\n")
    print("S4R1C4B_ORIGINAL_FULL_GRID_FIRST_HOUR_TWO_STAGE_SCRATCH_ONLY=PREPARED")

def verify(vendor:Path,original_met:Path,scratch_met:Path,
           original_trace:Path,native_csv:Path,report:Path,
           geo:Path,deck:Path,surf:Path,up:Path):
    source(vendor)
    if sha(original_met)!=sha(scratch_met):
        raise ValueError("Scratch diagnostic changed original 6h 45-field MET.DAT bytes")
    from native_cpp.reference.compare_p3_makegeo_dynamic import parse_geo
    geographic=parse_geo(geo,nx=NX,ny=NY,zone=50,hem="N",
                         x0=426.590,y0=3464.125,dx=1.)
    lu=geographic["category"]
    if len(lu)!=NX*NY:raise ValueError("Actual original GEO cells incorrect")
    water={(i%NX+1,i//NX+1) for i,cat in enumerate(lu)
           if 50<=int(cat)<=55}
    if len(water)!=NWATER:raise ValueError("Original true GEO WATER=63 changed")
    original={}
    for line in original_trace.read_text().splitlines():
        values=line.split()
        if len(values)!=8:
            raise ValueError(f"Malformed original Fortran DIAGNO sample: {line[:120]}")
        i,j,h,phase,cat=map(int,values[:5])
        if not(1<=i<=NX and 1<=j<=NY and h==2 and phase in(1,2)):
            raise ValueError("Original first-hour trace position/clock/phase mismatch")
        if int(lu[(j-1)*NX+i-1])!=cat:
            raise ValueError(f"Original/source GEO landuse differs at {i,j}")
        key=(i,j,phase)
        if key in original:
            raise ValueError("Duplicate original first-hour SURFVAR observation")
        uvtemp=tuple(float(v.replace("D","E")) for v in values[5:])
        if not all(map(math.isfinite,uvtemp)):
            raise ValueError("Original reference nonfinite U/V/T")
        original[key]=uvtemp
    if len(original)!=2*NX*NY:
        raise ValueError(f"Original both 6970-grid stages unavailable: {len(original)}")
    with native_csv.open(newline="") as stream:
        native=list(csv.DictReader(stream))
    if len(native)!=NX*NY:
        raise ValueError(f"Actual native full grid missing: {len(native)}")
    maxima={group:{field:{"abs":0.,"at":None,"above_tolerance":0}
                   for field in FIELDS} for group in("land","water")}
    cells=set()
    missing=[]
    for r in native:
        i,j=int(r["i"]),int(r["j"])
        key=(i,j)
        if key in cells or not(1<=i<=NX and 1<=j<=NY):
            raise ValueError(f"Native cell duplicated/out of GEO: {key}")
        cells.add(key)
        when=datetime.fromtimestamp(int(r["hour_end_utc_seconds"]),timezone.utc)
        if (when.year,when.month,when.day,when.hour)!=(2022,6,1,2):
            raise ValueError("Native R1c4b actual first hour UTC changed")
        if int(r["landuse"])!=int(lu[(j-1)*NX+i-1]):
            raise ValueError(f"Native/original GEO cell-category differs: {key}")
        ref1=original.get((i,j,1))
        ref2=original.get((i,j,2))
        if ref1 is None or ref2 is None:
            raise ValueError("Native field has no independently run Fortran pair")
        data={
            "wind1_u_mps":(float(r["wind1_u_mps"]),ref1[0]),
            "wind1_v_mps":(float(r["wind1_v_mps"]),ref1[1]),
            "fradj_u_mps":(float(r["fradj_u_mps"]),ref2[0]),
            "fradj_v_mps":(float(r["fradj_v_mps"]),ref2[1]),
            "pre_temp_k":(float(r["pre_temp_k"]),ref1[2]),
            "post_temp_k":(float(r["post_temp_k"]),ref2[2]),
        }
        group="water" if key in water else "land"
        for field,(value,ref) in data.items():
            if not (math.isfinite(value) and math.isfinite(ref)):
                raise ValueError("Native/original nonfinite "+field)
            error=abs(value-ref)
            peak=maxima[group][field]
            if error>peak["abs"]:
                peak["abs"]=error
                peak["at"]=[i,j]
            if error>ABS_TOL[field]:
                peak["above_tolerance"]+=1
                if len(missing)<20:
                    missing.append({"cell":[i,j],"group":group,
                                    "field":field,"original":ref,"native":value,
                                    "error":error})
    if len(cells)!=NX*NY or len(cells & water)!=NWATER:
        raise ValueError("Land-water full source coverage mismatch")
    failures=sum(item["above_tolerance"] for d in maxima.values()
                 for item in d.values())
    result={
        "status":"PASS_SCOPED_6970_FIRST_HOUR_WIND1_FRADJ_2XSURFVAR"
                 if failures==0 else "FAIL_ORIGINAL_NATIVE_6970_FIRST_HOUR",
        "vendor_blob":BLOB,
        "input_source_sha256":{p:sha(v) for p,v in
             (("geo",geo),("met_inp",deck),("surf",surf),("upper",up))},
        "original_calmet_6h_45field_identical":True,
        "original_calmet_sha256":sha(original_met),
        "real_noaa_utc_hour_end":"2022-06-01T02:00:00Z",
        "source_stations":"583140/583210 2SS, 58424 1US",
        "native_cells":len(cells),"real_water_cells":len(water),
        "land_cells":NX*NY-len(water),
        "independently_original_two_stage_rows":len(original),
        "component_comparisons":len(cells)*len(FIELDS),
        "maxima":maxima,"frozen_absolute_tolerance":ABS_TOL,
        "exceeded":failures,"failure_examples":missing,
        "six_hour_native_G21_G39_previous_ZICONV":"NOT_RUN",
        "G24_G26_45FIELD_P7":"NOT_ACCEPTED",
        "native_reference_injection":False,
    }
    report.parent.mkdir(parents=True,exist_ok=True)
    report.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    for g,fields in maxima.items():
        for k,v in fields.items():
            print("S4R1C4B_ORIGINAL_NATIVE",g,k,v["abs"],v["at"],
                  v["above_tolerance"])
    if failures:
        raise ValueError(f"R1c4b real NOAA full-grid numerical gate FAIL: {failures}")
    print("S4R1C4B_REAL_NOAA_G42_G21_6970_FIRST_HOUR_NATIVE_ORIGINAL=PASS_SCOPED")
    print("S4R1C4B_UNMODIFIED_6H_45FIELD_ORIGINAL_REFERENCE=BYTE_IDENTICAL")
    print("S4R1C4B_6H_NATIVE_STATE_G24_G26_P7=NOT_ACCEPTED")

def main():
    p=argparse.ArgumentParser()
    q=p.add_subparsers(dest="cmd",required=True)
    a=q.add_parser("prepare")
    for k in ("vendor","dest","receipt"):
        a.add_argument("--"+k,type=Path,required=True)
    b=q.add_parser("verify")
    for k in ("vendor","original-met","scratch-met","original-trace",
              "native-csv","report","geo","deck","surf","up"):
        b.add_argument("--"+k,type=Path,required=True)
    z=p.parse_args()
    if z.cmd=="prepare":
        prepare(z.vendor,z.dest,z.receipt)
    else:
        verify(z.vendor,z.original_met,z.scratch_met,z.original_trace,
               z.native_csv,z.report,z.geo,z.deck,z.surf,z.up)
if __name__=="__main__":main()
