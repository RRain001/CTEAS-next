#!/usr/bin/env python3
"""P6F locked-case CALMET v2.1 OUTHD control provenance without a reference header template.

Expected controls are derived only from met.inp + GEO.DAT. The CALMET.DAT
binary is read strictly as the candidate under audit. Header comments and
free-form model declaration are NOT claimed independently generated.

The supported source scope is the frozen 2022 Hefei 50x50x9, 1-hour UTM 50N
scenario; unsupported configs fail closed.
"""
from __future__ import annotations
import argparse
import datetime as dt
import json
from pathlib import Path
import re
import struct
from typing import Any

CONTROLS_BYTES=176
DECK_PATTERN=r"!\s*{key}\s*=\s*([^!]*)!"
MASK="CALMET 2.1 frozen Hefei source-only OUTHD"
HEADER_SOURCE_FIELDS={
    "IBYR":"begin_year", "IBMO":"begin_month", "IBDY":"begin_day",
    "IBHR":"begin_hour", "IBSEC":"begin_second",
    "IEYR":"end_year", "IEMO":"end_month", "IEDY":"end_day",
    "IEHR":"end_hour", "IESEC":"end_second",
    "IRTYPE":"irtype", "NX":"nx", "NY":"ny", "NZ":"nz",
    "NSSTA":"nssta", "NUSTA":"nusta", "NPSTA":"npsta", "NOWSTA":"nowsta",
    "IUTMZN":"iutmzn",
}
def expect(ok: bool, why: str)->None:
    if not ok: raise ValueError("P6F_HEADER_SOURCE_NOT_PASS: "+why)
def deck_field(data:str, key:str)->str:
    m=re.search(DECK_PATTERN.format(key=re.escape(key)),data,re.I)
    expect(m is not None, "met.inp key missing: "+key)
    value=m.group(1).strip()
    expect(bool(value), "met.inp key empty: "+key)
    return value
def integer(data:str,key:str)->int:
    value=deck_field(data,key)
    expect(bool(re.fullmatch(r"[+-]?\d+",value)), "met.inp integer malformed: "+key)
    return int(value)
def real(data:str,key:str)->float:
    value=deck_field(data,key)
    try: answer=float(value.replace("D","E").replace("d","e"))
    except ValueError: raise ValueError("P6F_HEADER_SOURCE_NOT_PASS: met.inp real malformed: "+key)
    expect(answer==answer and abs(answer)<1e9,"met.inp nonfinite/extreme real: "+key)
    return answer
def cardinal(data:str,key:str)->float:
    value=deck_field(data,key).strip().upper()
    m=re.fullmatch(r"([+-]?(?:\d+(?:\.\d*)?|\.\d+))\s*([NSEW])",value)
    expect(m is not None,"met.inp cardinal value malformed: "+key)
    x=float(m.group(1))
    if m.group(2) in ("S","W"): x=-x
    return x
def f32(x:float)->float:
    return struct.unpack("<f",struct.pack("<f",x))[0]
def record(file,expected_size:int,name:str)->bytes:
    size_word=file.read(4)
    expect(len(size_word)==4,"truncated "+name+" record marker")
    size=struct.unpack("<i",size_word)[0]
    expect(size==expected_size,f"{name} record has size {size}; expected {expected_size}")
    payload=file.read(size)
    expect(len(payload)==size,"truncated "+name+" contents")
    tail=file.read(4)
    expect(tail==size_word,f"{name} closing record marker differs")
    return payload
def get_controls(binary:Path)->dict[str,Any]:
    with binary.open("rb") as f:
        declaration=record(f,96,"declaration")
        expect(declaration[:16].rstrip()==b"CALMET.DAT","dataset declaration mismatch")
        expect(declaration[16:32].rstrip()==b"2.1","version mismatch")
        ncom=struct.unpack("<i",record(f,4,"comment count"))[0]
        expect(0<=ncom<=10000,"unbounded comments")
        for i in range(ncom): record(f,132,f"comment {i+1}")
        b=record(f,CONTROLS_BYTES,"OUTH D controls")
    i=lambda offset:struct.unpack_from("<i",b,offset)[0]
    fl=lambda offset:struct.unpack_from("<f",b,offset)[0]
    st=lambda offset,n:b[offset:offset+n].decode("ascii").rstrip()
    fields=dict(zip(
        ("begin_year","begin_month","begin_day","begin_hour","begin_second",
         "end_year","end_month","end_day","end_hour","end_second"),
        (i(n*4) for n in range(10))))
    fields.update({
        "timezone":st(40,8),"irlg":i(48),"irtype":i(52),
        "nx":i(56),"ny":i(60),"nz":i(64),
        "dgrid_m":fl(68),"xorigin_m":fl(72),"yorigin_m":fl(76),
        "iwfcod":i(80),"nssta":i(84),"nusta":i(88),"npsta":i(92),
        "nowsta":i(96),"nlu":i(100),"iwat1":i(104),"iwat2":i(108),
        "lcalgrd":i(112),"pmap":st(116,8),"datum":st(124,8),
        "daten":st(132,12),"feast":fl(144),"fnorth":fl(148),
        "utmhem":st(152,4),"iutmzn":i(156),
        "rnlat0":fl(160),"relon0":fl(164),"xlat1":fl(168),"xlat2":fl(172),
    })
    return fields
def geo_header(path:Path)->dict[str,Any]:
    lines=path.read_text(encoding="ascii").splitlines()
    expect(len(lines)>=10,"short GEO source")
    expect(lines[0].startswith("GEO.DAT") and lines[0][16:32].strip()=="2.1",
           "GEO v2.1 identity")
    expect(lines[1].strip()=="2","GEO source comment count")
    expect(lines[4].strip()=="UTM","GEO projection")
    expect(lines[5].strip()=="50N","GEO zone/hemisphere")
    datum=lines[6][:8].strip()
    daten=lines[6][8:].strip()
    dimensions=lines[7].split()
    expect(len(dimensions)==6,"GEO grid dimensions")
    expect(lines[9].split()[0]=="1","GEO direct category path only")
    # Land-use NLU comes after IOPT1.
    nlu_line=lines[10].split(" - ")[0].split()
    expect(len(nlu_line)==3,"GEO NLU/IWAT control row malformed")
    return {
        "pmap":"UTM","iutmzn":50,"utmhem":"N","datum":datum,
        "daten":daten,"nx":int(dimensions[0]),"ny":int(dimensions[1]),
        "xorigin_km":float(dimensions[2]),"yorigin_km":float(dimensions[3]),
        "dx_km":float(dimensions[4]),"dy_km":float(dimensions[5]),
        "nlu":int(nlu_line[0]),"iwat1":int(nlu_line[1]),"iwat2":int(nlu_line[2])
    }
def compare(deck:str,geo:dict[str,Any],control:dict[str,Any])->int:
    matched=0
    def eq(key:str,expected)->None:
        nonlocal matched
        actual=control[key]
        expect(actual==expected,f"{key} candidate {actual!r} != source {expected!r}")
        matched+=1
    def close(key:str,expected:float,tolerance:float=0.001)->None:
        nonlocal matched
        actual=control[key]
        expect(abs(actual-expected)<=tolerance,
               f"{key} candidate {actual!r} != source {expected!r}")
        matched+=1
    for source,destination in HEADER_SOURCE_FIELDS.items():
        eq(destination,integer(deck,source))
    eq("timezone",deck_field(deck,"ABTZ"))
    eq("lcalgrd",int(deck_field(deck,"LCALGRD").upper()=="T"))
    eq("pmap",deck_field(deck,"PMAP"))
    eq("datum",deck_field(deck,"DATUM"))
    eq("utmhem",deck_field(deck,"UTMHEM"))
    eq("iwfcod",1) # source OUTHD wind component flag in locked LCALGRD=T case
    eq("nlu",geo["nlu"])
    eq("iwat1",geo["iwat1"])
    eq("iwat2",geo["iwat2"])
    eq("daten",geo["daten"])
    close("dgrid_m",1000*real(deck,"DGRIDKM"))
    # Model READCF uses REAL*4 km coordinates and outputs metres.
    close("xorigin_m",f32(f32(real(deck,"XORIGKM"))*f32(1000.)),0.25)
    close("yorigin_m",f32(f32(real(deck,"YORIGKM"))*f32(1000.)),0.25)
    close("feast",real(deck,"FEAST"))
    close("fnorth",real(deck,"FNORTH"))
    for key,field in (("RLAT0","rnlat0"),("RLON0","relon0"),("XLAT1","xlat1"),("XLAT2","xlat2")):
        close(field,cardinal(deck,key))
    eq("iutmzn",integer(deck,"IUTMZN"))
    for key in ("nx","ny","pmap","datum","iutmzn","utmhem"):
        expect(control[key]==geo[key],f"{key} disagrees with GEO.DAT")
        matched+=1
    for key,left,right in (("dgrid_m",geo["dx_km"]*1000,geo["dy_km"]*1000),
                            ("xorigin_m",geo["xorigin_km"]*1000,real(deck,"XORIGKM")*1000),
                            ("yorigin_m",geo["yorigin_km"]*1000,real(deck,"YORIGKM")*1000)):
        expect(abs(left-right)<=0.02,"GEO grid vs deck mismatch: "+key)
        expect(abs(control[key]-left)<=0.25,"GEO grid vs CALMET binary mismatch: "+key)
        matched+=1
    step=integer(deck,"NSECDT")
    expect(step==3600,"only one-hour science mode accepted")
    begin=dt.datetime(*(integer(deck,x) for x in ("IBYR","IBMO","IBDY","IBHR")))
    end=dt.datetime(*(integer(deck,x) for x in ("IEYR","IEMO","IEDY","IEHR")))
    duration=int((end-begin).total_seconds()+integer(deck,"IESEC")-integer(deck,"IBSEC"))
    expect(duration>0 and duration%step==0,"invalid original run interval")
    eq("irlg",duration//step)
    return matched
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--deck",type=Path,required=True)
    p.add_argument("--geo",type=Path,required=True)
    p.add_argument("--candidate",type=Path,required=True)
    p.add_argument("--out",type=Path)
    args=p.parse_args()
    deck=args.deck.read_text(encoding="utf-8")
    geo=geo_header(args.geo)
    controls=get_controls(args.candidate)
    count=compare(deck,geo,controls)
    report={
        "status":"PASS_P6F_SOURCE_INDEPENDENT_OUTH D_CONTROLS".replace(" ",""),
        "source":"met.inp + GEO.DAT independent of CALMET.DAT run-control values",
        "fields_validated":count,
        "source_hours":controls["irlg"],
        "source_grid":[controls["nx"],controls["ny"],controls["nz"]],
        "frozen_file_used_only_as_candidate":True,
        "header_comments_independent":False,
        "hourly_records_independent":False,
        "complete_P6F_accepted":False,
    }
    if args.out:
        args.out.parent.mkdir(parents=True,exist_ok=True)
        args.out.write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps(report,sort_keys=True))
if __name__=="__main__":
    main()
