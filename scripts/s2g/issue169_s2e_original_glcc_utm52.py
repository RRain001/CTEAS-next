"""#169 S2-E: genuine original CTGPROC GLAZAS at a second UTM zone.

The original program is separately compiled and independently executed twice
from pinned Fortran/GLCC bytes. This module makes only original INPUT decks
and compares LFINAL=F integer HITS and LFINAL=T F6.3 outputs with actual
new-grid native B0 P2-A files. It is not a replacement Fortran calculation.
"""
from __future__ import annotations
import argparse
import csv
import json
import math
from pathlib import Path
import re
import sys

from native_cpp.reference.validate_p2_glazas_original import CATS, _edit_card
from scripts.s2g.issue160_hefei_glcc_science import (
    assert_canonical_source, make_inland_deck, sha
)
from scripts.s2g.issue123_d9_original_coastal_hits import control_value

NX=20
NY=20
NC=38
EPSG=32652
XREF="533.215"
YREF="3942.629"
DX="0.200"
HISTORIC_SOURCE="4f2a1977d141e2040da4d36ec6a4826c5c960c84686eaf10f226f388cb3ab90a"
ORIGINAL_SOURCE="719abbd2327269bb0377208b3a7a0c74000b878efc756686023bbb2ef932f281"

def need(ok,reason):
    if not ok:
        raise ValueError("S2E_P2A_ORIGINAL_UTM52_"+reason)

def check_controls(deck,final):
    expected={"LFINAL":final,"LCOAST":"F","LMARSWAP":"F","LMARFILL":"F",
              "LBLNREAD":"F","IUTMZN":"52","UTMHEM":"N","NX":"20",
              "NY":"20","XREFKM":XREF,"YREFKM":YREF,"DGRIDKM":DX,
              "MESHGLAZ":"20"}
    # Exact original mesh value is inherited from the approved 20x20
    # GLAZAS GLCC branch; do not modify original sampling formula.
    for key,value in expected.items():
        need(control_value(deck,key).upper()==value.upper(),
             "CONTROL_"+key)
    need(deck.count("1 !GLAZAS = glcc.img !")==1 and
         re.search(r"(?m)^\s*1\s+!GEN\s*=",deck) is None,
         "GLCC_SOURCE_NOT_ORIGINAL_SINGLE_GLAZAS")

def prepare(template,glcc,source,out):
    assert_canonical_source(glcc,source)
    need(not out.exists() and not out.is_symlink(),"CASE_OUT_ALREADY_EXISTS")
    deck=make_inland_deck(template.read_text(encoding="utf-8"))
    for key,value in (
        ("IUTMZN","52"),("NX","20"),("NY","20"),
        ("XREFKM",XREF),("YREFKM",YREF),("DGRIDKM",DX),
        ("MESHGLAZ","20")
    ):
        deck=_edit_card(deck,key,value)
    check_controls(deck,"F")
    frac=_edit_card(deck,"LFINAL","T")
    check_controls(frac,"T")
    need(_edit_card(frac,"LFINAL","F")==deck,"CONTROL_NOT_ONLY_LFINAL_DIFFERENT")
    for leaf,text in (("original_hits",deck),("original_fractions",frac)):
        path=out/leaf
        path.mkdir(parents=True)
        (path/"ctgproc.inp").write_text(text,encoding="utf-8")
        (path/"glcc.img").symlink_to(glcc.resolve())
    report={"status":"P2A_REAL_UTM52_TWO_ORIGINAL_GLAZAS_DECKS_PREPARED",
            "glcc_sha256":sha(glcc),"source_sha256":sha(source),
            "original_hits_control_sha256":sha(out/"original_hits/ctgproc.inp"),
            "original_fraction_control_sha256":sha(out/"original_fractions/ctgproc.inp"),
            "original_fortran_executions":"NOT_RUN",
            "grid":{"utm_epsg":EPSG,"nx":NX,"ny":NY,
                    "xrefkm":XREF,"yrefkm":YREF,"dgridkm":DX}}
    (out/"prepare.json").write_text(json.dumps(report,indent=2)+"\n")
    return report

def header(f,kind):
    lines=[f.readline().rstrip("\r\n") for _ in range(11)]
    need(lines[0].split()[:2]==["LU.DAT","2.1"],"ORIGINAL_LU_VERSION")
    need(lines[4].strip()==kind and lines[5].strip()=="UTM" and
         lines[6].strip()=="52N" and lines[7].startswith("WGS-84"),
         "ORIGINAL_LU_GRID_CRS")
    meta=lines[8].split()
    need(len(meta)>=7 and (int(meta[0]),int(meta[1]))==(NX,NY) and
         abs(float(meta[2])-float(XREF))<1e-8 and
         abs(float(meta[3])-float(YREF))<1e-8 and
         abs(float(meta[4])-float(DX))<1e-8 and
         abs(float(meta[5])-float(DX))<1e-8 and
         int(meta[6])==NC and
         tuple(map(int,lines[10].split()))==CATS,
         "ORIGINAL_LU_SIZE_OR_CLASS_ORDER")

def fixed_row(line,index,width,as_integer):
    need(len(line)>=10+NC*width,"SHORT_ORIGINAL_LU_ROW")
    i,j=int(line[:5]),int(line[5:10])
    need((i,j)==(index%NX+1,index//NX+1),"ORIGINAL_LU_ROW_ORDER")
    pieces=[line[10+k*width:10+(k+1)*width].strip() for k in range(NC)]
    if as_integer:
        vals=[int(v) for v in pieces]
        need(all(0<=x<=99999 for x in vals),"ORIGINAL_INTEGER_RANGE")
    else:
        need(all(re.fullmatch(r"(?:0|1)?\.\d{3}",v) for v in pieces),"ORIGINAL_F63_FORMAT")
        vals=pieces
    flag=line[10+NC*width:].strip()
    need(flag in (".","Missing"),"ORIGINAL_FLAG")
    return vals,flag

def compare(case,glcc,source,b0,out):
    assert_canonical_source(glcc,source)
    need(not out.exists() and not out.is_symlink(),"AUDIT_EXISTS")
    p=json.loads((case/"prepare.json").read_text())
    need(p["status"]=="P2A_REAL_UTM52_TWO_ORIGINAL_GLAZAS_DECKS_PREPARED" and
         p["glcc_sha256"]==sha(glcc) and p["source_sha256"]==sha(source),
         "PREPARE_SOURCE_CHANGED")
    for path,final,hashkey in (
        ("original_hits","F","original_hits_control_sha256"),
        ("original_fractions","T","original_fraction_control_sha256")
    ):
        control=case/path/"ctgproc.inp"
        check_controls(control.read_text(),final)
        need(sha(control)==p[hashkey],"ORIGINAL_CONTROL_DRIFT")
    native=json.loads((b0/"evidence/p2.json").read_text())
    need(native["status"]=="P2A_GENERIC_CASE_PRODUCED_UNVERIFIED" and
         native["original_science"]=="NOT_RUN" and
         native["utm_epsg"]==EPSG and
         (native["nx"],native["ny"])==(NX,NY) and
         abs(float(native["xrefkm"])-float(XREF))<1e-8 and
         abs(float(native["yrefkm"])-float(YREF))<1e-8 and
         abs(float(native["dgridkm"])-float(DX))<1e-8 and
         native["source_img_sha256"]==HISTORIC_SOURCE,
         "NATIVE_B0_SCOPE_OR_SOURCE")
    lu=b0/"geo/ctgproc/p2a_case/lu/lu.dat"
    hits=b0/"geo/ctgproc/p2a_case/raw/p2_glcc_usgs92_hits.csv"
    need(sha(lu)==native["lu_dat_sha256"] and
         sha(hits)==native["hits_sha256"],"NATIVE_IMMUTABLE_PRODUCT_SHA")
    oh=case/"original_hits/lu.dat"
    of=case/"original_fractions/lu.dat"
    for path in (oh,of,lu,hits):
        need(path.is_file() and path.stat().st_size>1000,"ACTUAL_OUTPUT_MISSING")
    err_hits=err_frac=err_flag=0
    total_original=total_native=0
    first=[]
    with oh.open() as a,of.open() as b,lu.open() as c,hits.open(newline="") as d:
        header(a,"HITS");header(b,"FRACTION");header(c,"FRACTION")
        reader=csv.reader(d)
        need(next(reader,None)==["i","j","samples"]+
             [f"cat{v}" for v in CATS],"NATIVE_INTEGER_COLUMNS")
        for row_index in range(NX*NY):
            ra,rb,rc=map(lambda x:x.readline().rstrip("\r\n"),(a,b,c))
            values=next(reader,None)
            need(values is not None and len(values)==41,"NATIVE_INTEGER_ROW")
            ih,fh=fixed_row(ra,row_index,5,True)
            ff,fb=fixed_row(rb,row_index,6,False)
            nf,fn=fixed_row(rc,row_index,6,False)
            vals=list(map(int,values))
            need(vals[:2]==[row_index%NX+1,row_index//NX+1] and
                 vals[2]==sum(vals[3:]),"NATIVE_INTEGER_COUNTS")
            total_original+=sum(ih);total_native+=vals[2]
            bad=sum(x!=y for x,y in zip(ih,vals[3:]))
            diff=sum(x!=y for x,y in zip(ff,nf))
            flags=(fh!=fb or fb!=fn or fn!=("Missing" if sum(ih)==0 else "."))
            err_hits+=bad;err_frac+=diff;err_flag+=flags
            if (bad or diff or flags) and len(first)<20:
                first.append({"i":row_index%NX+1,"j":row_index//NX+1,
                              "wrong_hits":bad,"wrong_F6_3":diff,"flag":bool(flags)})
        need(not a.readline() and not b.readline() and not c.readline() and
             next(reader,None) is None,"EXTRA_ROWS")
    passed=(err_hits==err_frac==err_flag==0 and total_original==total_native)
    report={"status":("P2A_TRUE_ORIGINAL_GLAZAS_UTM52_20X20_PASS_SCOPED" if passed else
                      "P2A_TRUE_ORIGINAL_GLAZAS_UTM52_NUMERIC_FAIL"),
            "source":{"historical_glcc_sha256":sha(glcc),
                      "original_ctgproc_source_sha256":sha(source)},
            "scope":"LCOAST_F_HISTORICAL_GLCC_ONLY_NOT_MODERN_30M",
            "grid":p["grid"],"cells":NX*NY,"categories":NC,
            "integer_fields_compared":NX*NY*NC,"integer_mismatches":err_hits,
            "F6_3_fields_compared":NX*NY*NC,"F6_3_mismatches":err_frac,
            "missing_flag_mismatches":err_flag,
            "original_hits_total":total_original,"native_hits_total":total_native,
            "original_hits_lu_sha256":sha(oh),
            "original_fraction_lu_sha256":sha(of),
            "native_lu_sha256":sha(lu),"native_hits_sha256":sha(hits),
            "b0_attestation_sha256":sha(b0/"evidence/p2.json"),
            "first_20_differences":first,"modern_30m_original_fortran":"NOT_APPLICABLE",
            "s3_g19":"NOT_RUN"}
    out.write_text(json.dumps(report,indent=2)+"\n")
    need(passed,"Genuine_original_UTM52_integer_fraction_mismatch")
    return report

def main():
    p=argparse.ArgumentParser()
    sub=p.add_subparsers(dest="command",required=True)
    a=sub.add_parser("prepare")
    for key in ("template","glcc","source","out"):
        a.add_argument("--"+key,type=Path,required=True)
    b=sub.add_parser("compare")
    for key in ("case","glcc","source","b0","out"):
        b.add_argument("--"+key,type=Path,required=True)
    args=p.parse_args()
    try:
        result=(prepare(args.template,args.glcc,args.source,args.out)
                if args.command=="prepare" else
                compare(args.case,args.glcc,args.source,args.b0,args.out))
        print(json.dumps({"status":result["status"],
                          "integer_mismatches":result.get("integer_mismatches","NOT_RUN"),
                          "F6_3_mismatches":result.get("F6_3_mismatches","NOT_RUN")}))
        return 0
    except (OSError,KeyError,ValueError,TypeError,IndexError) as error:
        print("S2E_P2A_FAIL_CLOSED:"+str(error)[:240],file=sys.stderr)
        return 2

if __name__=="__main__":
    raise SystemExit(main())
