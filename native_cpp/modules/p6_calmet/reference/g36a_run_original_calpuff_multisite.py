#!/usr/bin/env python3
"""G36A: ACTUALLY run untouched CALPUFF 7.2.1 on 143h NATIVE P6G output.

Never substitute the original CALMET 6.5.0 MET.DAT. Reuses the pinned
2022 CALPUFF control as a test fixture; changes only meteorological grid,
run clock and subset/receptor extents to match the accepted G35 synthetic
2SS/2US 12x12x9 10km meteorology. Keeps the source, chemistry, transport
and numerical controls intact. Not a production real-weather plume study.
"""
from __future__ import annotations
import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path
import re
import shutil
import struct
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[4]
P7_CONTROL=ROOT/"project/cases/hefei5km_2022_reference_case_20261011/run/puff/puff.inp"
VENDOR=ROOT/"engine/vendor/src/CALPUFF_v7.2.1_L150618"
sys.path.insert(0,str(Path(__file__).resolve().parent))
from g31_extract_original_science_hour import layout

SOURCE_CONTROL_GIT_BLOB="1de904ff1cbd1816ddded47849464439b8aad860"
EXPECTED_HOURS=143
EXPECTED_START=dt.datetime(2024,1,1,2,tzinfo=dt.timezone.utc)
EXPECTED_END=dt.datetime(2024,1,7,1,tzinfo=dt.timezone.utc)


def sha(path:Path)->str:
    s=hashlib.sha256()
    with path.open("rb") as f:
        for data in iter(lambda:f.read(1024*1024),b""):
            s.update(data)
    return s.hexdigest()


def git_blob(data:bytes)->str:
    return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()


def put_control(text:str,key:str,value:str)->str:
    p=re.compile(r"(!\s*"+re.escape(key)+r"\s*=\s*)([^!]*)(!)",re.I)
    matches=list(p.finditer(text))
    if len(matches)!=1:
        raise ValueError(f"G36A expected exactly one active original CALPUFF {key}: {len(matches)}")
    m=matches[0]
    return text[:m.start()]+m.group(1)+value+" "+m.group(3)+text[m.end():]


def control_value(text:str,key:str)->str:
    matches=re.findall(r"!\s*"+re.escape(key)+r"\s*=\s*([^!\r\n]+)!",text,re.I)
    if len(matches)!=1:
        raise ValueError(f"G36A missing/ambiguous original control {key}")
    return matches[0].strip()


def stamp(year:int,month:int,day:int,hour:int,second:int)->dt.datetime:
    if second!=0:
        raise ValueError("G36A original CALMET source nonzero seconds")
    return dt.datetime(year,month,day,hour,tzinfo=dt.timezone.utc)


def time_bounds(control:bytes)->tuple[dt.datetime,dt.datetime]:
    start=struct.unpack_from("<5i",control,0)
    end=struct.unpack_from("<5i",control,20)
    return stamp(*start),stamp(*end)


def make_control(original:str)->str:
    # CALPUFF original's IEHR denotes the LAST PROCESSED PERIOD END,
    # not the beginning of the last hour: its listing prints this clock.
    # G35 143h is 2024-01-01T02Z .. 2024-01-07T01Z (end exclusive).
    # A previous Jan 07 00 control silently ran only 142h despite exit 0.
    last=EXPECTED_END
    changes={
        "NX":"12","NY":"12","NZ":"9","DGRIDKM":"10.0",
        "IBCOMP":"1","JBCOMP":"1","IECOMP":"12","JECOMP":"12",
        "IBSAMP":"1","JBSAMP":"1","IESAMP":"12","JESAMP":"12",
        "IBYR":str(EXPECTED_START.year),"IBMO":str(EXPECTED_START.month),
        "IBDY":str(EXPECTED_START.day),"IBHR":str(EXPECTED_START.hour),
        "IEYR":str(last.year),"IEMO":str(last.month),
        "IEDY":str(last.day),"IEHR":str(last.hour),
    }
    for key,value in changes.items():
        original=put_control(original,key,value)
    mandatory={
        "METFM":"1","METRUN":"0","ABTZ":"UTC+0000","LCFILES":"T",
        "MWET":"0","MCHEM":"0","IUTMZN":"50","UTMHEM":"N",
        "IBMIN":"0","IEMIN":"0","IBSEC":"0","IESEC":"0",
        "METDAT":"../../deliverables/met/met.dat","NPT1":"1",
        "NMETDAT":"1",
    }
    for key,expected in mandatory.items():
        if control_value(original,key).upper()!=expected.upper():
            raise ValueError(f"G36A independent original puff control {key} drifted")
    # The stage must not alter the physically accepted original source,
    # release, or model numerical settings from the frozen 2022 baseline.
    return original


def fortran_record_count(path:Path)->int:
    size=path.stat().st_size
    n=0
    with path.open("rb") as stream:
        while stream.tell()<size:
            marker=stream.read(4)
            if len(marker)!=4:
                raise ValueError("G36A truncated original CALPUFF concentration envelope")
            (length,)=struct.unpack("<i",marker)
            if length<0 or length>128*1024*1024:
                raise ValueError("G36A invalid original CALPUFF concentration record length")
            chunk=stream.read(length)
            tail=stream.read(4)
            if len(chunk)!=length or len(tail)!=4 or struct.unpack("<i",tail)[0]!=length:
                raise ValueError("G36A malformed CALPUFF concentration record/trailer")
            n+=1
    if n<3:
        raise ValueError("G36A no meaningful original CALPUFF concentration records")
    return n


def execute(native_met:Path,out:Path,max_seconds:int)->dict:
    out=out.resolve()
    if out.exists() and any(out.iterdir()):
        raise ValueError("G36A must use an empty clean isolated output directory")
    out.mkdir(parents=True,exist_ok=True)
    report=out/"g36a-manifest.json"
    evidence={"status":"BLOCKED_G36A","scope":"actual unchanged CALPUFF 7.2.1 reading native continuous 143h G35 2SS/2US CALMET.DAT","hours_required":EXPECTED_HOURS}
    try:
        if max_seconds<1 or max_seconds>3600:
            raise ValueError("G36A bounded vendor CALPUFF execution requires 1-3600 seconds")
        if git_blob(P7_CONTROL.read_bytes())!=SOURCE_CONTROL_GIT_BLOB:
            raise ValueError("G36A pinned original P7 2022 CALPUFF control changed")
        native_met=native_met.resolve(strict=True)
        parsed=layout(native_met,"G36A_genuine_native_P6G_output")
        if parsed["intervals"]!=EXPECTED_HOURS:
            raise ValueError("G36A candidate is not 143 original-format hourly groups")
        begin,end=time_bounds(parsed["control"])
        if (begin,end)!=(EXPECTED_START,EXPECTED_END):
            raise ValueError("G36A native 143h source not in accepted G35 UTC window")
        evidence.update(native_met_sha256=sha(native_met),
                        native_met_bytes=native_met.stat().st_size,
                        native_met_hours=parsed["intervals"],
                        original_control_blob=SOURCE_CONTROL_GIT_BLOB)
        work=out/"case/run/puff"
        weather=out/"case/deliverables/met"
        weather.mkdir(parents=True)
        work.mkdir(parents=True)
        # A separate copy is the sole weather input, not vendor/oracle MET.DAT.
        staged_met=weather/"met.dat"
        shutil.copyfile(native_met,staged_met)
        if sha(staged_met)!=evidence["native_met_sha256"]:
            raise ValueError("G36A staged native 143h MET.DAT mutated")
        control=make_control(P7_CONTROL.read_text(encoding="latin-1"))
        (work/"calpuff.inp").write_text(control,encoding="latin-1")
        (work/"puff.inp").write_text(control,encoding="latin-1")
        evidence["staged_original_calpuff_control_sha256"]=sha(work/"calpuff.inp")
        source_files=[VENDOR/"modules.for",VENDOR/"calpuff.for"]
        for source in source_files:
            if not source.is_file() or source.stat().st_size<1000:
                raise FileNotFoundError("G36A original CALPUFF 7.2.1 Fortran source missing: "+str(source))
        evidence["original_vendor_source_sha256"]={x.name:sha(x) for x in source_files}
        flags=["-std=legacy","-ffixed-line-length-72","-fno-automatic",
               "-fno-align-commons","-fallow-argument-mismatch",
               "-fdec-format-defaults","-O0"]
        binary=out/"original-calpuff-7.2.1.x"
        compile_cmd=["gfortran",*flags,*map(str,source_files),"-o",str(binary)]
        compiled=subprocess.run(compile_cmd,cwd=out,capture_output=True,text=True,timeout=240)
        (out/"original-compile.log").write_text(compiled.stdout+"\n"+compiled.stderr)
        if compiled.returncode or not binary.is_file():
            raise RuntimeError("G36A untouched original CALPUFF failed to compile: "+compiled.stderr[-1200:])
        evidence["original_binary_sha256"]=sha(binary)
        with (out/"original-calpuff-runtime.log").open("w") as log:
            try:
                result=subprocess.run([str(binary)],cwd=work,stdout=log,
                                      stderr=subprocess.STDOUT,timeout=max_seconds)
            except subprocess.TimeoutExpired as error:
                raise RuntimeError("G36A CALPUFF 143h full run timed out") from error
        evidence["original_returncode"]=result.returncode
        listing=work/"puff.lst"
        concentration=work/"puff.con"
        evidence["listing_present"]=listing.is_file() and listing.stat().st_size>0
        evidence["concentration_present"]=concentration.is_file() and concentration.stat().st_size>0
        evidence["original_runtime_tail"]=(out/"original-calpuff-runtime.log").read_text(errors="replace")[-3000:]
        if listing.is_file():
            evidence["original_listing_tail"]=listing.read_text(errors="replace")[-4000:]
        if result.returncode or not evidence["listing_present"] or not evidence["concentration_present"]:
            raise RuntimeError("G36A original CALPUFF did not finish with valid listing/concentration")
        # A zero exit code and CONC.DAT are insufficient: CALPUFF can end
        # early with 142/143 hours while still producing valid files.
        # Its unchanged listing explicitly states the LAST PERIOD END.
        listing_text=listing.read_text(errors="replace")
        ending=re.search(
            r"LAST PERIOD PROCESSED ENDS AT:\s*"
            r"Year:\s*(\d+)\s*Month:\s*(\d+)\s*Day:\s*(\d+)\s*"
            r"Julian day:\s*\d+\s*Hour:\s*(\d+)\s*Second:\s*(\d+)",
            listing_text,re.I)
        if not ending:
            raise RuntimeError("G36A original CALPUFF listing missing last processed UTC period")
        actual_end=stamp(*(int(v) for v in ending.groups()))
        evidence["original_last_period_end_utc"]=actual_end.isoformat()
        evidence["original_processed_hour_count"]=int(
            (actual_end-EXPECTED_START).total_seconds()//3600)
        if actual_end!=EXPECTED_END or evidence["original_processed_hour_count"]!=143:
            raise RuntimeError("G36A original CALPUFF did not process ALL 143 native hours")
        combined=evidence["original_runtime_tail"]+evidence.get("original_listing_tail","")
        if re.search(r"(?im)^\s*ERROR IN SUBR\.|\bFATAL\b|\bABORT\b|forrtl:\s*severe|segmentation fault",combined):
            raise RuntimeError("G36A original CALPUFF runtime printed fatal condition")
        if sha(staged_met)!=evidence["native_met_sha256"] or (
            sha(native_met)!=evidence["native_met_sha256"]):
            raise RuntimeError("G36A source/native weather altered during actual CALPUFF run")
        evidence["original_concentration_records"]=fortran_record_count(concentration)
        evidence["original_concentration_sha256"]=sha(concentration)
        evidence["original_listing_sha256"]=sha(listing)
        evidence["status"]="PASS_G36A_ORIGINAL_CALPUFF_7_2_1_FULL_143H_NATIVE_INPUT"
    except Exception as error:
        evidence["blocker"]=str(error)
        raise
    finally:
        report.write_text(json.dumps(evidence,indent=2)+"\n")
        print(json.dumps(evidence,indent=2))


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--native-met",required=True,type=Path)
    parser.add_argument("--out",required=True,type=Path)
    parser.add_argument("--max-seconds",type=int,default=900)
    options=parser.parse_args()
    execute(options.native_met,options.out,options.max_seconds)
