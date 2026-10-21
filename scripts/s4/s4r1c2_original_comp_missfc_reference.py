#!/usr/bin/env python3
"""S4-R1c2 original CALMET COMP MISSFC 2SS x 6h exact source parity.

Vendor source is SHA-pinned. Scratch instrumentation samples ORIGINAL
SURF arrays immediately BEFORE and AFTER COMP->MISSFC; C++ receives only
original source GEO/SURF/met.inp/UP, never original arrays or original MET.
"""
from __future__ import annotations
import argparse, hashlib, json, math, subprocess
from pathlib import Path

VENDOR="437f43bb7f0e51a1919e56664663e1a046986ed0"
TRACE="s4r1c2-original-comp-missfc-raw-vs-resolved.txt"
STATIONS={583140,583210}
TIMES={202215202,202215203,202215204,202215205,202215206,202215207}
FIELDS=["ceiling","cloud","humidity","precip_code",
        "temperature_k","pressure_mb","wind_speed_mps","wind_direction_deg"]

def sha(p:Path)->str:return hashlib.sha256(p.read_bytes()).hexdigest()
def original(vendor:Path)->list[str]:
    blob=subprocess.run(["git","hash-object",str(vendor)],capture_output=True,
                        text=True,check=True).stdout.strip()
    if blob!=VENDOR:raise ValueError("Reject non-pinned vendor source")
    lines=vendor.read_text().splitlines()
    if lines[3985].strip().lower()!="call missfc(iyr,ijul,ihr)" or \
       "111   continue" not in lines[3987]:
        raise ValueError("CALMET source COMP MISSFC call moved")
    return lines

def prepare(vendor:Path,dest:Path,receipt:Path)->None:
    lines=original(vendor)
    def trace(phase:int):
        return [
          f"      open(unit=96,file='{TRACE}',",
          "     1 status='unknown',position='append',action='write')",
          "      do kk=1,nssta",
          "      write(96,'(7(i12,1x),4(es23.15,1x))')",
          f"     1 idathre,idssta(kk),{phase},iceil(kk),icc(kk),",
          "     2 irh(kk),ipcode(kk),tempk(kk),pres(kk),ws(kk),wd(kk)",
          "      enddo",
          "      close(unit=96)",
        ]
    out=[]
    for k,line in enumerate(lines,1):
        if k==3986:out.extend(trace(0))
        out.append(line)
        if k==3986:out.extend(trace(1))
    dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text("\n".join(out)+"\n")
    receipt.parent.mkdir(parents=True,exist_ok=True)
    receipt.write_text(json.dumps({
        "status":"S4R1C2_VENDOR_COMP_MISSFC_SCRATCH_ONLY",
        "original_blob":VENDOR,"original_sha256":sha(vendor),
        "instrumented_sha256":sha(dest),
        "insertion":"before+after exact original COMP call L3986",
        "vendor_checkout_mutated":False,"native_parity":"NOT_RUN"
    },sort_keys=True,indent=2)+"\n")
    print("S4R1C2_ORIGINAL_COMP_MISSFC_SOURCE_SCRATCH_PREPARED")

def _parse(path:Path,has_header:bool):
    data={}
    rows=path.read_text().splitlines()
    if has_header:
        if rows.pop(0).split()!=["original_yyyyjjjhh","station_id","phase",
                                *FIELDS]:
            raise ValueError("Native station fields changed")
    for line in rows:
        fields=line.split()
        if len(fields)!=11:raise ValueError(f"MISSFC trace columns: {len(fields)}")
        stamp,sid,phase,ceil,cloud,rh,pc=map(int,fields[:7])
        temp,pres,ws,wd=(float(x.replace("D","E")) for x in fields[7:])
        key=(stamp,sid,phase)
        if stamp not in TIMES or sid not in STATIONS or phase not in (0,1):
            raise ValueError(f"Unrecognized original source station/hour {key}")
        if key in data:raise ValueError(f"Duplicate station hour {key}")
        if not all(math.isfinite(x) for x in (temp,pres,ws,wd)):
            raise ValueError("Nonfinite original model source")
        data[key]=[ceil,cloud,rh,pc,temp,pres,ws,wd]
    if len(data)!=24:
        raise ValueError(f"Expected 2 surface sites x 6h x 2 MISSFC phases: {len(data)}")
    return data

def verify(vendor:Path,baseline:Path,scratch:Path,
           deck:Path,surf:Path,fortran:Path,native:Path,report:Path)->None:
    original(vendor)
    if sha(baseline)!=sha(scratch):
        raise ValueError("MISSFC scratch changed original 6h 45-field MET.DAT")
    ref=_parse(fortran,False)
    cpp=_parse(native,True)
    if set(ref)!=set(cpp):
        raise ValueError("Unpaired original-vs-native MISSFC station hours")
    max_res={"temperature_k":0.,"pressure_mb":0.,
             "wind_speed_mps":0.,"wind_direction_deg":0.}
    at={}
    per_field_repairs={k:0 for k in ("ceiling","cloud","humidity","temperature_k","pressure_mb")}
    for key,r in ref.items():
        n=cpp[key]
        for idx,name in enumerate(FIELDS):
            if idx<4 and r[idx]!=n[idx]:
                raise ValueError(f"Original MISSFC {name} integer mismatch {key}: {r[idx]} vs {n[idx]}")
            if idx>=4:
                err=abs(r[idx]-n[idx])
                if err>max_res[name]:
                    max_res[name]=err;at[name]=key
                if err>0.001:
                    raise ValueError(f"Original MISSFC {name} numeric mismatch {key}: {err}")
        if key[2]==1:
            old=ref[(key[0],key[1],0)]
            for name,index in (("ceiling",0),("cloud",1),("humidity",2),
                               ("temperature_k",4),("pressure_mb",5)):
                if old[index]!=r[index]:per_field_repairs[name]+=1
            # Absolute invariant: original MISSFC never fills wind or precip.
            for k in (3,6,7):
                if old[k]!=r[k] or cpp[(key[0],key[1],0)][k]!=n[k]:
                    raise ValueError("P5 sparse wind/precip was mutated in MISSFC")
    initial=(202215202,583140)
    if not (ref[(*initial,0)][4]>=9998.99 and
            ref[(*initial,0)][5]>=9998.99 and
            ref[(*initial,1)][4]<9998.99 and
            ref[(*initial,1)][5]<9998.99 and
            ref[(*initial,0)][6]>=9998.99 and
            ref[(*initial,1)][6]>=9998.99):
        raise ValueError("Original P5 AUX missing source/COMP MISSFC source changed")
    proof={
      "status":"S4R1C2_REAL_NOAA_ORIGINAL_VS_NATIVE_COMP_MISSFC_2SS6H_PASS_SCOPED",
      "pinned_original_calmet_blob":VENDOR,
      "original_metinp_sha256":sha(deck),
      "original_surf_sha256":sha(surf),
      "original_calmet_sha256":sha(baseline),
      "instrumented_calmet_sha256":sha(scratch),
      "original_45field_met_byte_identical":True,
      "paired_station_hours_phases":24,
      "source_surface_stations":sorted(STATIONS),
      "source_hours":sorted(TIMES),
      "original_vs_native_max_residual":max_res,
      "max_residual_location":at,
      "original_nonwind_repaired_station_hours":per_field_repairs,
      "original_aux_583140_first_hour_P5_wind_missing_unchanged":True,
      "P5_wind_policy":"NOT_MODIFIED",
      "G39_REAL_SELECTED_THERMAL":"NOT_RUN_YET",
      "G24_G26_P7":"NOT_RUN"
    }
    report.parent.mkdir(parents=True,exist_ok=True)
    report.write_text(json.dumps(proof,sort_keys=True,indent=2)+"\n")
    print("S4R1C2_ORIGINAL_NATIVE_2SSX6H_COMP_MISSFC=PASS_SCOPED")
    print("S4R1C2_ORIGINAL_45_FIELDS_BYTE_IDENTICAL=PASS")
    print("S4R1C2_P5_SPARSE_WIND_UNCHANGED=PASS")
    print("S4R1C2_G39_G24_G26_P7=NOT_RUN")

def main():
    p=argparse.ArgumentParser()
    sub=p.add_subparsers(dest="mode",required=True)
    x=sub.add_parser("prepare")
    for f in ("vendor","dest","receipt"):x.add_argument("--"+f,type=Path,required=True)
    x=sub.add_parser("verify")
    for f in ("vendor","baseline","scratch","deck","surf","fortran","native","report"):
        x.add_argument("--"+f,type=Path,required=True)
    args=p.parse_args()
    if args.mode=="prepare":prepare(args.vendor,args.dest,args.receipt)
    else:verify(args.vendor,args.baseline,args.scratch,args.deck,args.surf,
                args.fortran,args.native,args.report)
if __name__=="__main__":main()
