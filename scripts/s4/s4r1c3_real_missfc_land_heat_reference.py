#!/usr/bin/env python3
"""S4-R1c3 independent first-hour original 6970-cell heat/air density science.
Fortran writes a scratch DIAGNO after-ELUSTR snapshot only. The native
G44 is fed exclusively genuine P1-P5 source files and no vendor outputs.
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

BLOB="437f43bb7f0e51a1919e56664663e1a046986ed0"
TRACE="s4r1c3-original-firsthour-after-elustr.txt"
NX,NY=82,85
COLUMNS=("temp2d_k","qsw_wm2","qh_after_elustr_wm2",
         "rho_kg_m3","ustar_mps","el_m")
ABS_LIMIT={"temp2d_k":0.001,"qsw_wm2":0.005,
           "qh_after_elustr_wm2":0.25,"rho_kg_m3":0.0001,
           "ustar_mps":0.005}
# Monin-Obukhov EL may be unbounded in weak-flux cases; use both
# absolute and source-relative significance rather than a magic cap.
EL_ABS=0.5
EL_REL=0.01

def sha(p:Path)->str:
    return hashlib.sha256(p.read_bytes()).hexdigest()

def source(vendor:Path)->list[str]:
    blob=subprocess.run(["git","hash-object",str(vendor)],check=True,
                        capture_output=True,text=True).stdout.strip()
    if blob!=BLOB:
        raise ValueError("Fortran CALMET original blob mismatch: "+blob)
    lines=vendor.read_text().splitlines()
    pinned={
      5692:"         if (itprog.lt.2) call airden(pres,temp2d,rho)",
      5693:"         call elustr(z0,ug,vg,zmid(1),nears,",
      5694:"     1               rho,temp2d,icc,ilandu,iwat1,iwat2,",
      5696:"     2               nx,ny,mcloud,ccgrid,ipsifcn,qh,ustar,el)",
      5697:"      elseif(isfcmet.EQ.1) then",
    }
    for n,v in pinned.items():
        if lines[n-1]!=v:raise ValueError(f"DIAGNO source anchor changed at {n}")
    return lines

def prepare(vendor:Path,dest:Path,receipt:Path)->None:
    lines=source(vendor)
    # No accidental duplicate label in original DIAGNO local subroutine.
    # The label 9883 is reserved for the write-only scratch reference.
    insert=[
      "      if(nhrz.eq.2) then",
      f"      open(unit=95,file='{TRACE}',",
      "     1     status='unknown',position='append',action='write')",
      "      do j=1,ny",
      "      do i=1,nx",
      "      write(95,9883) i,j,nhrz,ilandu(i,j),qh(i,j),rho(i,j),",
      "     1  ustar(i,j),el(i,j),temp2d(i,j),qsw(i,j)",
      "      enddo",
      "      enddo",
      " 9883 format(4(i6,1x),6(es23.15,1x))",
      "      close(unit=95)",
      "      endif",
    ]
    dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text("\n".join(lines[:5696]+insert+lines[5696:])+"\n")
    receipt.parent.mkdir(parents=True,exist_ok=True)
    receipt.write_text(json.dumps({
      "case":"S4R1C3_ORIGINAL_CALMET_AFTER_AIRDEN_ELUSTR_FIRSTHOUR_ONLY",
      "source_blob":BLOB,"source_sha256":sha(vendor),
      "scratch_sha256":sha(dest),"original_anchor_line":5697,
      "in_original_vendor_checkout":False,
      "scientific_parity":"NOT_RUN",
    },indent=2,sort_keys=True)+"\n")
    print("S4R1C3_SCRATCH_ONLY_ORIGINAL_FIRST_HOUR_HEAT_PROBE_PREPARED")

def verify(vendor:Path,original_met:Path,scratch_met:Path,
           original_trace:Path,native_csv:Path,report:Path)->None:
    source(vendor)
    if sha(original_met)!=sha(scratch_met):
        raise ValueError("R1c3 scratch Fortran changed original six-hour MET.DAT")
    original={}
    for line in original_trace.read_text().splitlines():
        a=line.strip().split()
        if len(a)!=10:raise ValueError("R1c3 original Fortran row malformed")
        i,j,h,cat=map(int,a[:4])
        if not 1<=i<=NX or not 1<=j<=NY or h!=2:
            raise ValueError("R1c3 original first-hour/source coordinate changed")
        key=(i,j)
        if key in original:raise ValueError("Duplicate original first-hour cell")
        qh,rho,ustar,el,temp,qsw=(
            float(v.replace("D","E")) for v in a[4:])
        original[key]=dict(qh_after_elustr_wm2=qh,rho_kg_m3=rho,
                           ustar_mps=ustar,el_m=el,temp2d_k=temp,
                           qsw_wm2=qsw,landuse=cat)
    if len(original)!=NX*NY:
        raise ValueError(f"Original 6970 first-hour cells incomplete {len(original)}")
    with native_csv.open(newline="") as f:
        native=list(csv.DictReader(f))
    if len(native)!=NX*NY:
        raise ValueError(f"Native 6970 first-hour cells incomplete {len(native)}")
    seen=set();maxima={k:{"max_abs":0.,"max_rel":0.,"at":None}
                       for k in COLUMNS}
    land=0;water=0;fails=[]
    for row in native:
        i,j=int(row["i"]),int(row["j"])
        key=(i,j)
        if key in seen or key not in original:
            raise ValueError("Native spatial coverage or ordering duplicated")
        seen.add(key)
        epoch=int(row["hour_end_utc_seconds"])
        instant=datetime.fromtimestamp(epoch,timezone.utc)
        if (instant.year,instant.month,instant.day,instant.hour)!=(2022,6,1,2):
            raise ValueError("R1c3 current source UTC 02 first-hour gate")
        ref=original[key]
        lu=int(row["landuse"])
        if lu!=ref["landuse"]:
            raise ValueError(f"Native and original land category differ at {key}")
        is_water=50<=lu<=55
        water+=int(is_water);land+=int(not is_water)
        if is_water:
            if float(row["qh_after_elustr_wm2"])!=0.:
                raise ValueError("Native WATER QH became physically synthetic")
            # Water USTAR/EL are computed by original later WATER, *not*
            # by this ELUSTR stage; the original scratch after ELUSTR may
            # carry initialization, so never claim WATER friction parity.
            active=("temp2d_k","qsw_wm2","rho_kg_m3")
        else:
            active=COLUMNS
        for label in active:
            value=float(row[label]);expected=ref[label]
            if not (math.isfinite(value) and math.isfinite(expected)):
                raise ValueError(f"Nonfinite original/native {label} {key}")
            error=abs(value-expected)
            relative=error/max(1.,abs(expected))
            if error>maxima[label]["max_abs"]:
                maxima[label].update(max_abs=error,at=[i,j])
            maxima[label]["max_rel"]=max(maxima[label]["max_rel"],relative)
            acceptable=(error<=max(EL_ABS,EL_REL*abs(expected))
                        if label=="el_m"
                        else error<=ABS_LIMIT[label])
            if not acceptable and len(fails)<40:
                fails.append(dict(cell=key,field=label,original=expected,
                                  native=value,error=error))
    if water!=63 or land!=6907 or len(seen)!=NX*NY:
        raise ValueError(f"Real original land/water grid not matched {land}/{water}")
    result={
      "status":"PASS_SCOPED_REAL_FIRSTHOUR_LAND_HEAT_AIRDEN_ELUSTR"
               if not fails else "FAIL_REAL_FIRSTHOUR_LAND_HEAT_AIRDEN_ELUSTR",
      "original_vendor_blob":BLOB,
      "original_met_sha256":sha(original_met),
      "scratch_met_sha256":sha(scratch_met),
      "native_original_hour_end_utc":"2022-06-01T02:00:00Z",
      "real_native_original_paired_cells":NX*NY,
      "water_cells":water,"land_cells":land,
      "numeric_residuals":maxima,
      "abs_thresholds":ABS_LIMIT,
      "el_abs_threshold_m":EL_ABS,"el_rel_threshold":EL_REL,
      "sample_failures":fails,
      "source_missfc":"G43_MODEL_INTERNAL_DETACHED",
      "p5_raw_source":"UNCHANGED",
      "native_water_ustar_el_zi":"NOT_COMPUTED",
      "full_g24_g26_6x45_field_p7":"NOT_ACCEPTED"
    }
    report.parent.mkdir(parents=True,exist_ok=True)
    report.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print("S4R1C3_NATIVE_ORIGINAL_LAND_6907_WATER_63_PAIR_ROWS="+str(NX*NY))
    print("S4R1C3_RESIDUALS="+json.dumps(maxima,sort_keys=True))
    print("S4R1C3_FAIL_EXAMPLES="+json.dumps(fails[:5]))
    if fails:raise ValueError("Original-vs-native first-hour thermal residual exceeds pre-registered tolerance")
    print("S4R1C3_REAL_NOAA_FIRSTHOUR_HEAT_AIRDEN_ELUSTR=PASS_SCOPED")
    print("S4R1C3_ORIGINAL_6H_45_FIELDS=BYTE_IDENTICAL")
    print("S4R1C3_WATER_USTAR_EL_G24_G26_P7=NOT_ACCEPTED")

def main():
    p=argparse.ArgumentParser()
    s=p.add_subparsers(dest="mode",required=True)
    q=s.add_parser("prepare")
    for k in ("vendor","dest","receipt"):
        q.add_argument("--"+k,required=True,type=Path)
    q=s.add_parser("verify")
    for k in ("vendor","original-met","scratch-met","original-trace",
              "native-csv","report"):
        q.add_argument("--"+k,required=True,type=Path)
    a=p.parse_args()
    if a.mode=="prepare":prepare(a.vendor,a.dest,a.receipt)
    else:verify(a.vendor,a.original_met,a.scratch_met,
                a.original_trace,a.native_csv,a.report)
if __name__=="__main__":main()
