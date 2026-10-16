#!/usr/bin/env python3
"""G31A: execute LITERAL unmodified CALMET 6.5.0 on G19 2SS/2US source.

G19 provides original-format *synthetic* GEO/SURF/UP; only the copied met.inp
is adjusted for file locations, two UP file records and the single-hour
clock, which is independently taken from the G21 source first-hour trace.
The vendor Fortran bytes/COMMON physics and upstream G19 files are unchanged.

G31A is the independent original execution prerequisite, not yet a 45-field
scientific parity result. Never substitute a C++ candidate CALMET.DAT for the
original vendor output; failure to execute original CALMET is a HARD STOP.
"""
from __future__ import annotations
import argparse
import csv
import datetime as dt
import hashlib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[4]
VENDOR=ROOT/"engine/vendor/src/CALMET_v6.5.0_L150223"
sys.path.insert(0,str(Path(__file__).resolve().parent))
EXPECTED_VENDOR_BLOB="437f43bb7f0e51a1919e56664663e1a046986ed0"

def sha256(file:Path)->str:
    return hashlib.sha256(file.read_bytes()).hexdigest()

def git_blob(raw:bytes)->str:
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()

def source_clock(path:Path):
    with path.open(newline="") as stream:
        reader=csv.DictReader(stream)
        expected={"hour_end_utc_seconds","k_1based","j_1based","i_1based",
                  "u_mps_real4","v_mps_real4"}
        if set(reader.fieldnames or ())!=expected:
            raise ValueError("G31A first-hour source clock not genuine G21")
        stamps=set()
        count=0
        for row in reader:
            count+=1
            stamps.add(int(row["hour_end_utc_seconds"]))
    if count!=12*12*9 or len(stamps)!=1:
        raise ValueError("G31A source G21 did not contain one 1296-row hour")
    end=dt.datetime.fromtimestamp(stamps.pop(),dt.timezone.utc)
    start=end-dt.timedelta(hours=1)
    if any(t.minute or t.second for t in (start,end)):
        raise ValueError("G31A source hour not UTC on the hour")
    return start,end

def replace_control(deck:str,key:str,value:str)->str:
    # Source READCF control tokens are bracketed by ! !, no guessed defaults.
    pattern=re.compile(r"(!\s*"+re.escape(key)+r"\s*=\s*)([^!]*)(!)",re.I)
    matches=list(pattern.finditer(deck))
    if len(matches)!=1:
        raise ValueError(f"G31A ambiguous or missing source READCF {key}: {len(matches)}")
    m=matches[0]
    return deck[:m.start()]+m.group(1)+value+" "+m.group(3)+deck[m.end():]

def stage_deck(src:str,start:dt.datetime,end:dt.datetime)->str:
    # All numerical READCF choices, station coordinates/identities,
    # model domain and physical scalar coefficients remain from G19.
    updates={
        "GEODAT":"geo.dat","SRFDAT":"surf.dat",
        "METLST":"met.lst","METDAT":"met.dat","LCFILES":"T",
        "IBYR":str(start.year),"IBMO":str(start.month),
        "IBDY":str(start.day),"IBHR":str(start.hour),"IBSEC":"0",
        # Original CALMET insists IE* strictly follows IB*; the one-hour
        # G21 frame gives BOTH temporal boundaries with no invented clock.
        "IEYR":str(end.year),"IEMO":str(end.month),
        "IEDY":str(end.day),"IEHR":str(end.hour),"IESEC":"0"
    }
    result=src
    for key,val in updates.items():
        result=replace_control(result,key,val)
    matches=list(re.finditer(r"^UP1\.DAT[^\n]*!\s*UPDAT\s*=[^\n]*!END!",result,re.M|re.I))
    if len(matches)!=1:
        raise ValueError("G31A original 1UP file-list anchor has drifted")
    m=matches[0]
    line="UP1.DAT       input     1  ! UPDAT=up1.dat !    !END!"
    extra="UP2.DAT       input     2  ! UPDAT=up2.dat !    !END!"
    result=result[:m.start()]+line+"\n"+extra+result[m.end():]
    if result.count("UPDAT=")!=2:
        raise ValueError("G31A 2-UP vendor READCF group not exactly two")
    # Unlike the G19 C++ input parser, untouched CALMET READCF scans for
    # SS1 / US1 and then consumes exactly NSSTA / NUSTA *consecutive*
    # station rows (vendor calmet.for 25884-25952). G19 appends SS2 / US2
    # at EOF only for its C++ parser. Move the very same source station
    # declarations after SS1 / US1 on the *staged copy*; never fabricate
    # station IDs/coords or edit the original G19 case.
    for prefix in ("SS","US"):
        extra_re=re.compile(r"(?m)^! "+prefix+r"2\b[^\n]*")
        found=list(extra_re.finditer(result))
        if len(found)!=1:
            raise ValueError("G31A G19 original station "+prefix+"2 not unique")
        extra=found[0].group(0)
        result=result[:found[0].start()]+result[found[0].end():]
        existing=re.compile(r"(?m)^! "+prefix+r"1\b[^\n]*")
        first=list(existing.finditer(result))
        if len(first)!=1:
            raise ValueError("G31A original "+prefix+"1 station group missing")
        where=first[0].end()
        result=result[:where]+"\n"+extra+result[where:]
        if result.count(prefix+"2")!=1:
            raise ValueError("G31A original second station duplicated")

    if src==result:
        raise ValueError("G31A source run deck not staged")
    # No interpolation or source-data fabrication is allowed here.
    for key in ("NSSTA","NUSTA","NX","NY","IUPT","IMIXH","IZICRLX",
                "CRITFN","TERRAD","ZIMIN","ZIMAX","CONSTN","CONSTE"):
        m=re.compile(r"!\s*"+key+r"\s*=\s*([^!]+)!")
        a=m.findall(src)
        b=m.findall(result)
        if len(a)!=1 or a!=b:
            raise ValueError("G31A changed protected physical source control "+key)
    return result

def stage_vendor_geodat_header(data:str)->str:
    """Format only G19 GEO.DAT header as untouched READGE fixed-column input.

    Input G19 grid/terrain/landuse and all six physical gridded matrices
    remain exactly the same numerical payload. Original READGE uses
    (I4,A4) for UTM and (2I8,4F12.3) for geometry, whereas the G19
    synthetic C++ reader accepts compact, space-separated header forms.
    """
    lines=data.splitlines(keepends=True)
    if len(lines)<36 or not lines[0].startswith("GEO.DAT") or (
            lines[3].strip()!="UTM" or lines[4].strip()!="50N" or
            not lines[5].startswith("WGS-84") or
            not lines[7].startswith("KM")):
        raise ValueError("G31A original G19 GEO expected header layout changed")
    tokens=lines[6].split()
    if len(tokens)!=6:
        raise ValueError("G31A G19 GEO geometry columns changed")
    nx,ny=int(tokens[0]),int(tokens[1])
    x,y,dx,dy=(float(t) for t in tokens[2:])
    if (nx,ny,x,y,dx,dy)!=(12,12,510.885,3531.269,10.0,10.0):
        raise ValueError("G31A original GEO numeric geometry out of source scope")
    # Only lines 5 and 7 (1-based) are rewritten; the 12x12 LANDUSE,
    # terrain and six source surface matrices stay byte-identical.
    lines[4]=f"{50:4d}{'N':<4}\n"
    lines[6]=f"{nx:8d}{ny:8d}{x:12.3f}{y:12.3f}{dx:12.3f}{dy:12.3f}\n"
    result="".join(lines)
    if result.splitlines()[8:]!=data.splitlines()[8:]:
        raise ValueError("G31A physical GEO data rows altered in staging")
    return result


def stage_vendor_updat_header(data:str,expected_station:int)->str:
    """Reformat only source header/UTC sounding metadata to RDHDU/RDUPN.

    The original CALMET vendor uses (1X,8I5,F5.0,2I5) for the UP
    interval and (9X,I8,2(4X,I4,I4,I3,I3,I5),8X,I5) for observations.
    G19's physically identical 2UP synthetic observation records are
    whitespace delimited for the C++ parser and require this *copy-only*
    conversion. Slash-delimited meteorological level rows are untouched.
    """
    lines=data.splitlines(keepends=True)
    if (len(lines)<10 or not lines[0].startswith("UP.DAT") or
            lines[3].strip()!="NONE" or lines[4].strip()!="UTC+0000"):
        raise ValueError("G31A source G19 UP header not expected")
    head=lines[5].split()
    if len(head)!=11:
        raise ValueError("G31A 2UP original record timing corrupted")
    ints=[int(v) for v in head[:8]]
    ptop=float(head[8]); jdat=int(head[9]); fmt=int(head[10])
    if ptop!=500.0 or jdat!=2 or fmt!=1:
        raise ValueError("G31A source UP physical Ptop/type not accepted")
    lines[5]=" "+ "".join(f"{k:5d}" for k in ints)+f"{ptop:5.0f}{jdat:5d}{fmt:5d}\n"
    flags=lines[6].split()
    if flags!=["F","F","F","F"]:
        raise ValueError("G31A original UP missing thermometer/wind flags")
    lines[6]=" "+ "".join("    "+k for k in flags)+"\n"
    observations=0
    sounding_times=[]
    for index in range(7,len(lines)):
        pieces=lines[index].split()
        if not pieces or pieces[0]!="6201":
            continue
        if len(pieces)!=14:
            raise ValueError("G31A unexpected source sounding time schema")
        station=int(pieces[1])
        if station!=expected_station:
            raise ValueError("G31A changed source UP station identity")
        ints=[int(v) for v in pieces[2:12]]
        if ints[0]<2023 or ints[0]>2024 or ints[5]<2023 or ints[5]>2024:
            raise ValueError("G31A changed source sounding UTC year")
        nlev=int(pieces[-1])
        if nlev!=2 or int(pieces[-2])!=2:
            raise ValueError("G31A source two-level sounding unsupported")
        first="".join(f"    {ints[j]:4d}{ints[j+1]:4d}{ints[j+2]:3d}{ints[j+3]:3d}{ints[j+4]:5d}"
                      for j in (0,5))
        lines[index]=f"   6201  {station:8d}"+first+f"        {nlev:5d}\n"
        t=dt.datetime(ints[0],ints[1],ints[2],ints[3],ints[4],
                      tzinfo=dt.timezone.utc)
        if (ints[:5]!=ints[5:] or
            (sounding_times and t-sounding_times[-1]!=dt.timedelta(hours=12))):
            raise ValueError("G35 original source upper brackets shifted or not 12h")
        sounding_times.append(t)
        observations+=1
    if observations not in (3,15):
        raise ValueError("G35 unexpected original upper sounding count")
    return "".join(lines)


def original_compiler(source:Path,exe:Path,mode:str,compiler:str):
    include=exe.parent/"include-alias"
    include.mkdir(parents=True,exist_ok=True)
    for f in VENDOR.iterdir():
        if f.is_file():
            alias=include/f.name.lower()
            if not alias.exists():
                alias.symlink_to(f)
    flags=["-std=legacy","-ffixed-line-length-none","-fno-automatic",
           "-fno-align-commons","-fallow-argument-mismatch",
           "-O0"]
    cmd=[compiler,*flags,"-I"+str(include),str(source),"-o",str(exe)]
    p=subprocess.run(cmd,capture_output=True,text=True,timeout=240)
    if p.returncode or not exe.is_file():
        raise RuntimeError("G31A literal original vendor compile failed\n"+p.stderr[-5000:])
    return cmd

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--mode",choices=["Debug","Release"],required=True)
    ap.add_argument("--source",type=Path,required=True,
                    help="G19 exported source folder with GEO.DAT, SURF.DAT, UP1/UP2.DAT, met.inp")
    ap.add_argument("--source-clock",type=Path,required=True)
    ap.add_argument("--hours",type=int,choices=(1,6,143),default=1,
                    help="original CALMET 1h, 6h or G35A 143h whole-run oracle")
    ap.add_argument("--out",type=Path,required=True)
    ap.add_argument("--compiler",default="gfortran")
    args=ap.parse_args()
    args.out.mkdir(parents=True,exist_ok=True)
    evidence={"status":"NOT_EXECUTED","mode":args.mode,
              "scope":f"Independent literal vendor {args.hours}h original output; "
                       "native multi-hour 45-field parity NOT tested"}
    report=args.out/"g31a-evidence.json"
    try:
        raw=(VENDOR/"calmet.for").read_bytes()
        evidence["original_vendor_blob"]=git_blob(raw)
        if evidence["original_vendor_blob"]!=EXPECTED_VENDOR_BLOB:
            raise RuntimeError("G31A original CALMET 6.5.0 source blob drift")
        clock_start,clock_end=source_clock(args.source_clock)
        evidence["source_hour_utc"]=[clock_start.isoformat(),clock_end.isoformat()]
        run_end=clock_start+dt.timedelta(hours=args.hours)
        evidence["requested_original_hours"]=args.hours
        evidence["original_run_end_utc"]=run_end.isoformat()
        staged=args.out/"run"
        staged.mkdir(parents=True,exist_ok=True)
        copies={"GEO.DAT":"geo.dat","SURF.DAT":"surf.dat",
                "UP1.DAT":"up1.dat","UP2.DAT":"up2.dat"}
        evidence["unchanged_source_files"]={}
        for original,target in copies.items():
            p=args.source/original
            if not p.is_file() or not p.stat().st_size:
                raise RuntimeError("G31A missing actual G19 source file "+original)
            shutil.copy2(p,staged/target)
            if sha256(p)!=sha256(staged/target):
                raise RuntimeError("G31A original input bytes changed "+original)
            evidence["unchanged_source_files"][original]=sha256(p)
        # Original G19 grid matrices remain fixed; normalize only
        # vendor GEO header column formatting on a separate staged copy.
        geo=staged/"geo.dat"
        transformed=stage_vendor_geodat_header(geo.read_text())
        geo.write_text(transformed)
        evidence["staged_vendor_geodat_sha256"]=sha256(geo)
        evidence["staged_vendor_updat_sha256"]={}
        for filename,station_id in (("up1.dat",58424),("up2.dat",58425)):
            source_upper=staged/filename
            source_upper.write_text(stage_vendor_updat_header(
                source_upper.read_text(),station_id))
            evidence["staged_vendor_updat_sha256"][filename]=sha256(source_upper)
        # G35 original all six days are strictly covered by unmodified
        # actual upper source, never reused 6h station buffers.
        original_upper_text=(args.source/filename.replace(".dat",".DAT").upper()).read_text()
        upper_dates=[]
        for line in original_upper_text.splitlines()[7:]:
            row=line.split()
            if row and row[0]=="6201":
                upper_dates.append(dt.datetime(*(int(n) for n in row[2:7]),
                                               tzinfo=dt.timezone.utc))
        if not upper_dates or not upper_dates[0]<=clock_start or upper_dates[-1]<run_end:
            raise RuntimeError("G35 actual original UP soundings do not bracket full run")
        evidence.setdefault("source_sounding_count",{})[filename]=len(upper_dates)
        met=(args.source/"met.inp")
        if not met.is_file():
            raise RuntimeError("G31A missing G19 original source controls")
        original_deck=met.read_text()
        result=stage_deck(original_deck,clock_start,run_end)
        (staged/"met.inp").write_text(result)
        evidence["original_G19_metinp_sha256"]=sha256(met)
        evidence["staged_vendor_metinp_sha256"]=sha256(staged/"met.inp")
        binary=args.out/"original-calmet.x"
        evidence["frozen_original_compiler_optimization"]="-O0"
        evidence["compiler_command"]=original_compiler(
            VENDOR/"calmet.for",binary,args.mode,args.compiler)
        proc=subprocess.run([str(binary),"met.inp"],cwd=staged,
                            capture_output=True,text=True,
                            timeout=900 if args.hours==143 else 180)
        (args.out/"original-stdout.log").write_text(proc.stdout)
        (args.out/"original-stderr.log").write_text(proc.stderr)
        evidence["return_code"]=proc.returncode
        evidence["stdout_tail"]=proc.stdout[-2500:]
        evidence["stderr_tail"]=proc.stderr[-2500:]
        listing=staged/"met.lst"
        output=staged/"met.dat"
        evidence["original_listing_present"]=listing.exists()
        if listing.exists():
            evidence["original_listing_sha256"]=sha256(listing)
            evidence["original_listing_bytes"]=listing.stat().st_size
            shutil.copy2(listing,args.out/"original-met.lst")
            lines=listing.read_text(errors="replace").splitlines()
            evidence["original_listing_tail"]="\n".join(lines[-100:])
            evidence["original_listing_errors"]=[
                line[:300] for line in lines if
                re.search(r"error|fatal|stop|invalid|missing|warning",line,re.I)
            ][-30:]
        if "STOP " in proc.stderr or "Fortran runtime error" in proc.stderr:
            raise RuntimeError("G31A original CALMET STOP: "+proc.stderr[-400:])
        if proc.returncode:
            raise RuntimeError("G31A untouched original CALMET exited "+
                               str(proc.returncode)+"; inspect original-met.lst and original logs")
        if not output.is_file() or output.stat().st_size<=1024:
            raise RuntimeError("G31A original CALMET made no substantial MET.DAT")
        # Fail closed on partial vendor output, wrong 45-record group count,
        # timestamps, station inventory, or malformed Fortran record framing.
        # Reuse the existing G31B original-layout reader, not any native data.
        from g31_extract_original_science_hour import layout
        vendor_output=layout(output,"literal_original")
        if len(vendor_output["groups"])!=args.hours:
            raise RuntimeError(
                f"G34 original produced {len(vendor_output['groups'])} 45-field "
                f"hours instead of required {args.hours}")
        evidence["original_hour_clocks"]=[
            list(group[0][1:5]) for group in vendor_output["groups"]]
        evidence["original_45_fields_per_hour"]=45
        evidence["original_static_field_records"]=len(vendor_output["static"])
        evidence["original_met_dat_sha256"]=sha256(output)
        evidence["original_met_dat_bytes"]=output.stat().st_size
        shutil.copy2(output,args.out/"original-met.dat")
        # The original vendor output is NEVER derived from the C++ binary.
        evidence["status"]="ORIGINAL_VENDOR_EXECUTED"
    except Exception as exc:
        evidence["status"]="BLOCKED"
        evidence["blocker"]=str(exc)
        raise
    finally:
        report.write_text(json.dumps(evidence,indent=2)+"\n")
        print(json.dumps(evidence,indent=2))

if __name__=="__main__":
    main()
