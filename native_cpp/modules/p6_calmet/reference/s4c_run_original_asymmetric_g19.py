#!/usr/bin/env python3
"""Strict independent original CALMET 6.5.0 comparator for asymmetric G19 cases.

Only the original-format 2024 controlled 12x12 synthetic C2 source may be
used. No C++ MET field may be an input to the vendor. Original physical
met.inp controls and numerical GEO/SURF/UP payloads are frozen. File path,
Fortran column structure, and simulation time for a genuine prefix are
the only vendor-file staging changes.
"""
from __future__ import annotations
import argparse
import datetime as dt
import hashlib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import g31_run_literal_original_calmet_multisite as g31

def control(deck: str, key: str) -> str:
    found=re.findall(r"!\s*"+re.escape(key)+r"\s*=\s*([^!]*)!",deck,re.I)
    if len(found)!=1:raise ValueError(f"READCF ambiguous key {key}")
    return found[0].strip()

def surface_clock(path: Path, nss: int):
    lines=path.read_text().splitlines()
    if len(lines)<9+nss or not lines[0].startswith("SURF.DAT"):
        raise ValueError("Asymmetric original SURF source malformed")
    header=lines[5].split()
    if len(header)!=9 or int(header[-1])!=nss:
        raise ValueError("SURF original station/time header invalid")
    def instant(parts):
        y,j,h,m=(int(x) for x in parts)
        return dt.datetime(y,1,1,tzinfo=dt.timezone.utc)+dt.timedelta(days=j-1,hours=h,minutes=m)
    start=instant(header[:4])
    end=instant(header[4:8])
    ids=[int(x.strip()) for x in lines[6:6+nss]]
    if ids!=[583210+10*k for k in range(nss)]:
        raise ValueError("SURF controlled C2 authentic station subset mismatch")
    return start,end,ids

def move_station_declaration(deck: str, kind: str) -> str:
    if kind not in ("SS","US"):raise ValueError("bad station kind")
    extra=re.compile(r"(?m)^!\s*"+kind+r"2\s*=[^\n]*")
    second=list(extra.finditer(deck))
    if len(second)!=1:raise ValueError(f"Ambiguous {kind}2 original declaration")
    line=second[0].group()
    deck=deck[:second[0].start()]+deck[second[0].end():]
    first=list(re.finditer(r"(?m)^!\s*"+kind+r"1\s*=[^\n]*",deck))
    if len(first)!=1:raise ValueError(f"Missing {kind}1 original declaration")
    at=first[0].end()
    return deck[:at]+"\n"+line+deck[at:]

def stage_original_deck(deck: str,start:dt.datetime,end:dt.datetime,nss:int,nus:int)->str:
    values={"GEODAT":"geo.dat","SRFDAT":"surf.dat","METLST":"met.lst",
            "METDAT":"met.dat","LCFILES":"T",
            "IBYR":str(start.year),"IBMO":str(start.month),
            "IBDY":str(start.day),"IBHR":str(start.hour),"IBSEC":"0",
            "IEYR":str(end.year),"IEMO":str(end.month),
            "IEDY":str(end.day),"IEHR":str(end.hour),"IESEC":"0"}
    result=deck
    for k,v in values.items():result=g31.replace_control(result,k,v)
    anchor=re.compile(r"(?m)^UP1\.DAT[^\n]*!\s*UPDAT\s*=[^\n]*!END!")
    matches=list(anchor.finditer(result))
    if len(matches)!=1:raise ValueError("Original UP1 list ambiguous")
    old=matches[0]
    list_lines="UP1.DAT       input     1  ! UPDAT=up1.dat !    !END!"
    if nus==2:list_lines+="\nUP2.DAT       input     2  ! UPDAT=up2.dat !    !END!"
    result=result[:old.start()]+list_lines+result[old.end():]
    if nus==2:result=move_station_declaration(result,"US")
    if nss==2:result=move_station_declaration(result,"SS")
    if result.count("UPDAT=")!=nus:raise ValueError("Extra/missing original UP files")
    protected=("NSSTA","NUSTA","NX","NY","NZ","DGRIDKM","IUPT","IAVET",
               "IMIXH","IZICRLX","IEXTRP","IPROG","ITPROG","CRITFN",
               "TERRAD","IUTMZN","LCALGRD","IRAD","CONSTB","CONSTE")
    for k in protected:
        if control(deck,k)!=control(result,k):
            raise ValueError("S4-C modified protected physics "+k)
    return result

def run() -> None:
    ap=argparse.ArgumentParser()
    ap.add_argument("--source",type=Path,required=True)
    ap.add_argument("--out",type=Path,required=True)
    ap.add_argument("--vendor-dir",type=Path,required=True)
    ap.add_argument("--ss",type=int,choices=[1,2],required=True)
    ap.add_argument("--us",type=int,choices=[1,2],required=True)
    ap.add_argument("--hours",type=int,choices=[1,6],required=True)
    ap.add_argument("--compiler",default="gfortran")
    args=ap.parse_args()
    root=args.source.resolve();out=args.out.resolve();out.mkdir(parents=True,exist_ok=True)
    original_dir=args.vendor_dir.resolve()
    g31.VENDOR=original_dir
    receipt={"status":"BLOCKED","source_kind":"controlled_synthetic_C2_subset_NOT_NOAA",
             "station_pair":[args.ss,args.us],"hours":args.hours,
             "original_vendor_fresh":False,"CXX_MET_USED_AS_VENDOR_INPUT":False}
    try:
        src=original_dir/"calmet.for"
        blob=g31.git_blob(src.read_bytes())
        receipt["original_calmet_blob"]=blob
        receipt["original_calmet_sha256"]=g31.sha256(src)
        if blob!=g31.EXPECTED_VENDOR_BLOB:raise ValueError("Original CALMET source changed")
        input_deck=(root/"met.inp").read_text()
        if (control(input_deck,"NSSTA"),control(input_deck,"NUSTA"))!=(
            str(args.ss),str(args.us)):raise ValueError("Asymmetric cardinality declared incorrectly")
        if control(input_deck,"NX")!="12" or control(input_deck,"NY")!="12":
            raise ValueError("G31 fixed controlled 12x12 scope changed")
        start,source_end,ids=surface_clock(root/"SURF.DAT",args.ss)
        if source_end-start!=dt.timedelta(hours=6):
            raise ValueError("G19 original controlled six-hour source incomplete")
        end=start+dt.timedelta(hours=args.hours)
        receipt["model_time"]=[start.isoformat(),end.isoformat()]
        stage=out/"original-run";stage.mkdir(exist_ok=True)
        files={"GEO.DAT":"geo.dat","SURF.DAT":"surf.dat"}
        for i in range(args.us):files[f"UP{i+1}.DAT"]=f"up{i+1}.dat"
        for source_name,staged_name in files.items():
            source_path=root/source_name
            if not source_path.is_file():raise ValueError("Missing actual source "+source_name)
            shutil.copyfile(source_path,stage/staged_name)
            if g31.sha256(source_path)!=g31.sha256(stage/staged_name):
                raise ValueError("Original source changed during stage")
        receipt["actual_input_sha256"]={n:g31.sha256(root/n) for n in ["met.inp",*files]}
        # G31 staged original fixed-record header conversion: pixel data
        # remain exactly identical; synthetic C++ compact header cannot be
        # directly read by original Fortran READGE/UPDAT.
        geo=stage/"geo.dat"
        before=geo.read_text()
        geo.write_text(g31.stage_vendor_geodat_header(before))
        receipt["GEO_physical_rows_unchanged"]= (
            before.splitlines()[8:]==geo.read_text().splitlines()[8:])
        if not receipt["GEO_physical_rows_unchanged"]:
            raise ValueError("GEO numerical matrix changed")
        for i in range(args.us):
            station=58424+i
            p=stage/f"up{i+1}.dat"
            p.write_text(g31.stage_vendor_updat_header(p.read_text(),station))
        staged_deck=stage_original_deck(input_deck,start,end,args.ss,args.us)
        (stage/"met.inp").write_text(staged_deck)
        receipt["staged_original_deck_sha256"]=g31.sha256(stage/"met.inp")
        receipt["station_ids"]=ids
        exe=out/"original-calmet.x"
        receipt["original_compile_command"]=g31.original_compiler(src,exe,"Release",args.compiler)
        receipt["original_calmet_binary_sha256"]=g31.sha256(exe)
        process=subprocess.run([str(exe),"met.inp"],cwd=stage,
                               capture_output=True,text=True,timeout=480)
        (out/"original-stdout.log").write_text(process.stdout)
        (out/"original-stderr.log").write_text(process.stderr)
        receipt["original_exit_code"]=process.returncode
        listing=stage/"met.lst"
        if listing.exists():
            shutil.copyfile(listing,out/"original-met.lst")
            receipt["original_listing_tail"]="\n".join(listing.read_text(
                errors="replace").splitlines()[-80:])
        if process.returncode!=0 or "Fortran runtime error" in process.stderr:
            raise RuntimeError("Original Fortran failed; see original-met.lst: "+
                               process.stderr[-800:])
        data=stage/"met.dat"
        if not data.is_file() or data.stat().st_size<10000:
            raise RuntimeError("Original Fortran created no complete CALMET.DAT")
        from g31_extract_original_science_hour import layout
        groups=layout(data,"literal_original")["groups"]
        if len(groups)!=args.hours:raise RuntimeError("Original returned wrong 45-field hours")
        shutil.copyfile(data,out/"original-met.dat")
        receipt["original_met_sha256"]=g31.sha256(data)
        receipt["status"]="ORIGINAL_VENDOR_FRESH_PRODUCED_UNVERIFIED"
        receipt["original_vendor_fresh"]=True
        print("S4C_ASYMMETRIC_ORIGINAL_VENDOR_EXECUTED=PRODUCED_UNVERIFIED "+
              f"SS={args.ss} US={args.us} HOURS={args.hours}")
    except Exception as exc:
        receipt["blocker"]=str(exc)
        raise
    finally:
        (out/"original-verb-evidence.json").write_text(json.dumps(
            receipt,indent=2,sort_keys=True)+"\n")
if __name__=="__main__":
    run()
