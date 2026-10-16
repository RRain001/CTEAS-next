#!/usr/bin/env python3
"""G31B: select EXACT source-aligned 45 original vendor records, no new physics.

Do not copy a C++ candidate record into the original oracle. This script only
selects unmodified original hourly *record payloads*, verifies original hours,
and creates a forensic one-hour view with original static field records and
the original header with an updated 1h-only file declaration.

The frozen accepted #53 P6E "p6e_calmet_dat21 compare" remains the *sole*
numeric scientific authority and tolerance provider. Any difference must be
reported by that comparator, not silently accepted by this extractor.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import struct
import subprocess
from pathlib import Path

from verify_g18c6_independent_binary import fortran_records
from verify_g30_source_p6f_candidate import LABELS,NX,NY,NZ


def digest(x:bytes)->str:
    return hashlib.sha256(x).hexdigest()

def recode(payloads:list[bytes])->bytes:
    result=bytearray()
    for row in payloads:
        n=len(row)
        result+=struct.pack("<i",n)+row+struct.pack("<i",n)
    return bytes(result)

def layout(path:Path,origin:str):
    raw=path.read_bytes()
    records=fortran_records(raw)
    if len(records)<10 or len(records[0])!=96 or (
            records[0][:16].decode("ascii").strip()!="CALMET.DAT" or
            records[0][16:32].decode("ascii").strip()!="2.1"):
        raise ValueError(f"{origin}: invalid real Fortran CALMET.DAT header")
    if len(records[1])!=4:
        raise ValueError(f"{origin}: corrupt original comments count")
    (ncomments,)=struct.unpack("<i",records[1])
    if not 0<=ncomments<=10000 or len(records)<3+ncomments+10:
        raise ValueError(f"{origin}: corrupt original comment inventory")
    control=records[2+ncomments]
    if len(control)!=176:
        raise ValueError(f"{origin}: original 176-byte control record absent")
    irlg,irtype,nx,ny,nz=struct.unpack_from("<5i",control,48)
    iwfcod,nss,nus,nps=struct.unpack_from("<4i",control,80)
    if (irtype,nx,ny,nz,iwfcod,nss,nus,nps)!=(1,NX,NY,NZ,1,2,2,0):
        raise ValueError(f"{origin}: original source domain/site configuration differs: "+
                         str((irtype,nx,ny,nz,iwfcod,nss,nus,nps)))
    statics=[]
    hourlies=[]
    started=False
    for payload in records[3+ncomments:]:
        if len(payload)<24:
            raise ValueError(f"{origin}: short static or hourly Fortran record")
        label=payload[:8].decode("ascii")
        a,asec,b,bsec=struct.unpack_from("<4i",payload,8)
        if a==b==0:
            if started:
                raise ValueError(f"{origin}: static after hourly record")
            statics.append(payload)
        else:
            started=True
            if len(payload)!=24+4*NX*NY:
                raise ValueError(f"{origin}: wrong original 12x12 REAL4/INT4 payload")
            hourlies.append((label,a,asec,b,bsec,payload))
    if len(hourlies)<45 or len(hourlies)%45!=0:
        raise ValueError(f"{origin}: original 45-record hourly layout incomplete: "+
                         str(len(hourlies)))
    groups=[hourlies[k:k+45] for k in range(0,len(hourlies),45)]
    expected=tuple(LABELS)
    for group in groups:
        if tuple(row[0] for row in group)!=expected:
            raise ValueError(f"{origin}: source first-hour 45 labels not canonical")
        if len({row[1:5] for row in group})!=1:
            raise ValueError(f"{origin}: 45 fields from multiple model hours")
    if irlg!=len(groups):
        raise ValueError(f"{origin}: file IRLG {irlg} != original hourly groups {len(groups)}")
    return {"file":path,"bytes":raw,"records":records,
            "control":control,"static":statics,"groups":groups,
            "comments":ncomments,"intervals":irlg,
            "source_sha256":digest(raw)}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--original",type=Path,required=True)
    p.add_argument("--candidate",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    p.add_argument("--forensic-reference",type=Path,required=True)
    p.add_argument("--frozen-comparator",type=Path,required=True)
    args=p.parse_args()
    args.out.parent.mkdir(parents=True,exist_ok=True)
    verdict={"status":"BLOCKED","scope":"G31B true original-vendor 2SS/2US 45-field first-hour numerical gate, frozen P6E tolerance unchanged"}
    try:
        reference=layout(args.original,"literal_original")
        candidate=layout(args.candidate,"native_candidate")
        if len(candidate["groups"])!=1:
            raise ValueError("G31B candidate must contain exactly one G26B physical hour")
        selected_clock=candidate["groups"][0][0][1:5]
        matching=[g for g in reference["groups"] if g[0][1:5]==selected_clock]
        if len(matching)!=1:
            raise ValueError("G31B missing/ambiguous G19 same-source original-hour clock "+
                             str(selected_clock))
        # Header comments and physical static binary records are copied
        # unchanged from the independent ORIGINAL, and only the original
        # source hour's 45 raw hourly payloads are included. The output
        # header declares just 1h so the frozen P6E comparison can consume
        # the same original source hour as the C++ first-hour candidate.
        control=bytearray(reference["control"])
        struct.pack_into("<i",control,48,1)
        # The source timestamp must be the first original time. No
        # backdating or invented time is permitted.
        chosen=matching[0]
        first_original=reference["groups"][0]
        if matching[0] is not first_original:
            raise ValueError("G31B only original first chronological hour admitted")
        begin=struct.unpack_from("<5i",control,0)
        end=struct.unpack_from("<5i",control,20)
        cand_begin=struct.unpack_from("<5i",candidate["control"],0)
        cand_end=struct.unpack_from("<5i",candidate["control"],20)
        if begin!=cand_begin or end!=cand_end:
            # Source model control may declare additional hours. They
            # must not be relabeled without scientific evidence. We
            # retain the independent original original clock if the
            # original first hour is not exactly aligned with candidate.
            raise ValueError("G31B original header start/end differs from candidate "+
                             str((begin,end,cand_begin,cand_end)))
        original_prefix=reference["records"][:2+reference["comments"]]
        extracted=original_prefix+[bytes(control)]+reference["static"]+[
            row[5] for row in chosen]
        payload=recode(extracted)
        args.forensic_reference.parent.mkdir(parents=True,exist_ok=True)
        args.forensic_reference.write_bytes(payload)
        if digest(payload)==candidate["source_sha256"]:
            raise ValueError("G31B original vendor must remain independent of native candidate")
        verdict.update(status="ORIGINAL_HOUR_EXTRACTED",
                       original_sha256=reference["source_sha256"],
                       candidate_sha256=candidate["source_sha256"],
                       original_intervals=reference["intervals"],
                       selected_original_hour=selected_clock,
                       original_static_records=len(reference["static"]),
                       original_45_raw_field_sha256=[
                           digest(row[5]) for row in chosen],
                       forensic_reference_sha256=digest(payload),
                       output_original_met_bytes=args.original.stat().st_size)
        # No custom numeric thresholds here: use the unmodified frozen
        # comparator's per-field abs+rel limits and strict exit status.
        run=subprocess.run([str(args.frozen_comparator),"compare",
                            "--reference",str(args.forensic_reference),
                            "--candidate",str(args.candidate),
                            "--out",str(args.out.parent/"g31-frozen-45field-verdict.json")],
                           capture_output=True,text=True,timeout=60)
        verdict["frozen_comparator_returncode"]=run.returncode
        verdict["frozen_comparator_stdout_tail"]=run.stdout[-1200:]
        verdict["frozen_comparator_stderr_tail"]=run.stderr[-1200:]
        verdict["status"]="PASS_ORIGINAL_45_FIELD" if run.returncode==0 else "FAIL_ORIGINAL_45_FIELD"
        if run.returncode:
            raise RuntimeError("G31B frozen original science 45-field comparator rejected: "+
                               run.stderr[-700:])
    except Exception as exc:
        if verdict["status"]!="FAIL_ORIGINAL_45_FIELD":
            verdict["status"]="BLOCKED"
        verdict["blocker"]=str(exc)
        raise
    finally:
        args.out.write_text(json.dumps(verdict,indent=2)+"\n")
        print(json.dumps({k:v for k,v in verdict.items()
                          if k!="original_45_raw_field_sha256"},indent=2))

if __name__=="__main__":
    main()
