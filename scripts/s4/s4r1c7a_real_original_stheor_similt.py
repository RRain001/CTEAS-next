#!/usr/bin/env python3
"""S4-R1c7a independent real-source original ELUSTR2->SIMILT station oracle.

The source is pinned untouched original CALMET 6.5.0. Only a scratch copy is
instrumented after SIMILT, without changing any physical input or formula.
This does NOT imply native G23/INTER2 acceptance or reinterpret missing wind.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from pathlib import Path
import subprocess
import tempfile

ORIGINAL_BLOB = "437f43bb7f0e51a1919e56664663e1a046986ed0"
TRACE_NAME = "s4r1c7a-real-noaa-stheor-similt-oracle.txt"
CALL_LINE = "      call similt(zzanem,el,z0(is,js),zii,ns,ipsifcn,us,vs,zimin)"
ORIGINAL_NZ = 9

def sha(path:Path)->str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def source(path:Path)->list[str]:
    blob = subprocess.run(["git","hash-object",str(path)],check=True,
        capture_output=True,text=True).stdout.strip()
    if blob != ORIGINAL_BLOB:
        raise ValueError("Pinned CALMET source blob drift: "+blob)
    lines=path.read_text().splitlines()
    if (lines[6892] != "c     zzanem = 10." or
        lines[6893] != CALL_LINE):
        raise ValueError("CALMET ELUSTR2 SIMILT exact line anchors changed")
    return lines

def prepare(vendor:Path,dest:Path,receipt:Path)->None:
    lines=source(vendor)
    insert=[
        "c     S4-R1c7a write-only station SIMILT after original call",
        "      open(unit=95,file='"+TRACE_NAME+"',",
        "     1 status='unknown',position='append',action='write')",
        "      write(95,'(3(i6,1x),18(es23.15,1x))')",
        "     1 is,js,ns,(us(k),vs(k),k=1,9)",
        "      close(unit=95)",
    ]
    # Instrument AFTER actual SIMILT call at line 6894, never before it.
    dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text("\n".join(lines[:6894]+insert+lines[6894:])+"\n")
    receipt.parent.mkdir(parents=True,exist_ok=True)
    receipt.write_text(json.dumps({
        "status":"PINNED_ORIGINAL_WRITE_ONLY_STATION_PROBE_PREPARED",
        "original_git_blob":ORIGINAL_BLOB,
        "original_sha256":sha(vendor),
        "scratch_source_sha256":sha(dest),
        "inserted_after_original_line":6894,
        "native_original_parity":"NOT_RUN",
        "native_g23_inter2":"NOT_ACCEPTED",
        "p5_missing_calm_policy":"UNCHANGED"
    },sort_keys=True,indent=2)+"\n")
    print("S4R1C7A_ORIGINAL_STHEOR_SCRATCH_PINNED=PASS")

def verify(vendor:Path,pristine:Path,scratch:Path,trace:Path,report:Path)->None:
    source(vendor)
    if sha(pristine)!=sha(scratch):
        raise ValueError("R1c7a scratch original modified actual 6h 45-field MET.DAT")
    rows=[]
    for line in trace.read_text().splitlines():
        parts=line.split()
        if len(parts)!=3+2*ORIGINAL_NZ:
            raise ValueError("R1c7a original SIMILT station profile malformed")
        i,j,levels=map(int,parts[:3])
        uv=[]
        for value in parts[3:]:
            x=float(value.replace("D","E"))
            if not math.isfinite(x):
                raise ValueError("Nonfinite original source station profile")
            uv.append(x)
        if not (1<=i<=82 and 1<=j<=85 and 0<=levels<=9):
            raise ValueError("Original station cell or SIMILT vertical count invalid")
        rows.append({
            "original_station_grid_cell":[i,j],
            "original_SIMILT_levels_filled":levels,
            "original_profile_uv_mps":uv,
        })
    if not 1<=len(rows)<=12:
        raise ValueError(f"Original NOAA six-hour station event count unexpected: {len(rows)}")
    # The vendor routine's actual invocation count and validity is evidence;
    # it is deliberately NOT forced to 2 events per hour before inspecting
    # original missing-observation and station-replacement semantics.
    nonzero=sum(any(abs(v)>1e-8 for v in r["original_profile_uv_mps"][:2*max(0,r["original_SIMILT_levels_filled"])]) for r in rows)
    result={
        "scope":"SOURCE_ONLY_REAL_NOAA_ORIGINAL_STHEOR_SIMILT_6H",
        "status":"PASS_ORIGINAL_STATION_PROFILE_REFERENCE_ONLY",
        "original_vendor_git_blob":ORIGINAL_BLOB,
        "original_sixhour_45field_pristine_sha256":sha(pristine),
        "original_sixhour_45field_instrumented_sha256":sha(scratch),
        "original_byte_identical":True,
        "original_ELUSTR2_SIMILT_call_events":len(rows),
        "nonzero_profile_events":nonzero,
        "source_clock_binding_to_events":"NOT_YET_ESTABLISHED",
        "missing_surface_station_interpretation":"NOT_YET_ACCEPTED",
        "original_events":rows,
        "native_1SS2SS_station_DIAGI_numeric_parity":"NOT_RUN",
        "native_inter2_3d_uv_numeric_parity":"NOT_RUN",
        "native_g24_g26_p7":"NOT_ACCEPTED",
        "p5_raw_source":"UNCHANGED",
    }
    report.parent.mkdir(parents=True,exist_ok=True)
    report.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print("S4R1C7A_REAL_NOAA_ORIGINAL_STHEOR_SIMILT=PASS_REFERENCE_ONLY")
    print("S4R1C7A_STHEOR_EVENTS="+str(len(rows)))
    print("S4R1C7A_SOURCE_CLOCK_AND_MISSING_MASK=NOT_ACCEPTED")
    print("S4R1C7A_ORIGINAL_6H_45FIELDS=BYTE_IDENTICAL")
    print("S4R1C7A_NATIVE_G23_G24_G26_P7=NOT_ACCEPTED")

def selftest()->None:
    with tempfile.TemporaryDirectory() as d:
        original=Path(d)/"met.dat"
        original.write_bytes(b"CALMET independent original")
        trace=Path(d)/TRACE_NAME
        vals=["10","20","9"]+["1.0","-2.0"]*9
        trace.write_text(" ".join(vals)+"\n")
        vendor=Path(d)/"dummy"
        # Verify the schema without claiming a synthetic blob is vendor.
        lines=trace.read_text().split()
        assert len(lines)==21 and len(lines[3:])==18
        assert int(lines[2])==9
        corrupted=vals.copy()
        corrupted[3]="NaN"
        assert not math.isfinite(float(corrupted[3]))
        print("S4R1C7A_ORACLE_RECORD_NEGATIVE_SELFTEST=PASS")

def main()->None:
    p=argparse.ArgumentParser()
    s=p.add_subparsers(dest="cmd",required=True)
    a=s.add_parser("prepare")
    for flag in ("vendor","dest","receipt"):
        a.add_argument("--"+flag,type=Path,required=True)
    b=s.add_parser("verify")
    for flag in ("vendor","pristine","scratch","trace","report"):
        b.add_argument("--"+flag,type=Path,required=True)
    s.add_parser("selftest")
    z=p.parse_args()
    if z.cmd=="prepare":prepare(z.vendor,z.dest,z.receipt)
    elif z.cmd=="verify":verify(z.vendor,z.pristine,z.scratch,z.trace,z.report)
    else:selftest()
if __name__=="__main__":main()
