#!/usr/bin/env python3
"""#160 C1: independently audit true original CTGPROC Hefei 20km inland
GLAZAS LFINAL=F integer HITS, independently rerun original LFINAL=T, and
compare both to native C++ original sampling. Distinct from modern 30m P2-C.

Only JSON summaries may be published. Source data, original binaries and
raw LU.DAT files are ephemeral. Never treat a synthetic test as science.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import re
import sys

from native_cpp.reference.validate_p2_glazas_original import CATS, _edit_card
from scripts.s2g.issue123_original_coastext_wolsong import (
    build_deck as original_legal_glazas_deck, GLCC_SHA, GLCC_BYTES, SOURCE_SHA,
    sha,
)
from scripts.s2g.issue123_d9_original_coastal_hits import control_value

N=200
NC=38
XREF="503.385"
YREF="3523.769"
GRID={"utm_epsg":32650, "xrefkm":XREF, "yrefkm":YREF,
      "dgridkm":"0.100", "nx":N, "ny":N, "meshglaz":10}
METHOD="ORIGINAL_GLAZAS_LUGRID_SVGRID_HISTORICAL_GLCC_INLAND_V1"

def require(ok:bool,reason:str)->None:
    if not ok:
        raise ValueError("ISSUE160_HEFEI_"+reason)

def regular(path:Path)->bool:
    return path.is_file() and not path.is_symlink()

def assert_canonical_source(glcc:Path,original:Path)->None:
    require(regular(glcc) and glcc.stat().st_size==GLCC_BYTES and
            sha(glcc)==GLCC_SHA,"CANONICAL_GLCC_BYTES_SHA")
    require(regular(original) and sha(original)==SOURCE_SHA,
            "CANONICAL_ORIGINAL_FORTRAN_SHA")

def make_inland_deck(template:str)->str:
    # Start from the already tested, single legal original GLAZAS data card;
    # touch only declared original control cards. The Wolsong builder here
    # is a CARD TEMPLATE helper, not any GSHHG/coast sampling invocation.
    deck=original_legal_glazas_deck(template)
    edits=(("LCOAST","F"),("LMARSWAP","F"),("LMARFILL","F"),
           ("LBLNREAD","F"),("LFINAL","F"),("IUTMZN","50"),
           ("XREFKM",XREF),("YREFKM",YREF),("DGRIDKM","0.100"),
           ("NX","200"),("NY","200"),("MESHGLAZ","10"))
    for key,val in edits:
        deck=_edit_card(deck,key,val)
    validate_deck(deck,"F")
    return deck

def validate_deck(deck:str,lfinal:str)->None:
    expected=(("GLAZAS","glcc.img"),("LFINAL",lfinal),("LCOAST","F"),
              ("LMARSWAP","F"),("LMARFILL","F"),("LBLNREAD","F"),
              ("MESHGLAZ","10"),("IUTMZN","50"),("UTMHEM","N"),
              ("NX","200"),("NY","200"),("XREFKM",XREF),
              ("YREFKM",YREF),("DGRIDKM","0.100"),("IOCEAN","55"))
    for key,val in expected:
        if key=="GLAZAS":
            require(deck.count("1 !GLAZAS = glcc.img !")==1,
                    "NOT_SINGLE_LEGAL_GLAZAS")
        else:
            require(control_value(deck,key).upper()==val.upper(),
                    "CONTROL_DRIFT_"+key)
    require("!GEN =" not in deck,"GEN_NOT_ALLOWED")

def prepare(template:Path,glcc:Path,original:Path,out:Path)->dict:
    assert_canonical_source(glcc,original)
    require(not out.exists() and not out.is_symlink(),"OUTPUT_COLLISION")
    hits=make_inland_deck(template.read_text(encoding="utf-8"))
    fractions=_edit_card(hits,"LFINAL","T")
    validate_deck(fractions,"T")
    require(_edit_card(fractions,"LFINAL","F")==hits,"CONTROL_ONLY_LFINAL_CHANGE")
    out.mkdir(parents=True)
    for name,deck in (("original_hits",hits),("original_fractions",fractions)):
        d=out/name
        d.mkdir()
        (d/"ctgproc.inp").write_text(deck,encoding="utf-8")
        (d/"glcc.img").symlink_to(glcc.resolve())
    result={"status":"HEFEI_ORIGINAL_TWO_RUN_DECK_PREPARED",
            "grid":GRID,"original_fortran_source_sha256":SOURCE_SHA,
            "historical_glcc_sha256":GLCC_SHA,
            "hits_control_sha256":sha(out/"original_hits"/"ctgproc.inp"),
            "fractions_control_sha256":sha(out/"original_fractions"/"ctgproc.inp"),
            "distinct_original_executions":True,
            "control_difference":"LFINAL_ONLY",
            "real_historical_science":"NOT_RUN",
            "modern_glc30m_science":"NOT_RUN"}
    (out/"prepare.json").write_text(json.dumps(result,indent=2)+"\n")
    return result

def parsed_header(stream,kind:str)->None:
    lines=[stream.readline().rstrip("\r\n") for _ in range(11)]
    require(len(lines)==11 and lines[0].split()[:2]==["LU.DAT","2.1"],
            "LU_HEADER_VERSION")
    require(lines[4].strip()==kind and lines[5].strip()=="UTM" and
            lines[6].strip()=="50N" and lines[7].startswith("WGS-84"),
            "LU_HEADER_CRS_FORMAT_"+kind)
    vals=lines[8].split()
    require(len(vals)==7 and int(vals[0])==N and int(vals[1])==N and
            math.isclose(float(vals[2]),float(XREF),abs_tol=1e-8) and
            math.isclose(float(vals[3]),float(YREF),abs_tol=1e-8) and
            math.isclose(float(vals[4]),.1,abs_tol=1e-8) and
            math.isclose(float(vals[5]),.1,abs_tol=1e-8) and
            int(vals[6])==NC,"LU_HEADER_GRID")
    require(lines[9].strip().startswith("KM"),"LU_HEADER_UNITS")
    require(tuple(int(v) for v in lines[10].split())==CATS,
            "LU_HEADER_CLASSES")

def parse_hit_row(line:str,index:int)->tuple[list[int],str]:
    require(len(line)>=10+NC*5,"SHORT_I5_HITS")
    try:
        i,j=int(line[:5]),int(line[5:10])
        hits=[int(line[10+k*5:15+k*5]) for k in range(NC)]
    except ValueError as exc:
        raise ValueError("ISSUE160_HEFEI_BAD_INTEGER_HITS") from exc
    require((i,j)==(index%N+1,index//N+1),"HITS_ROW_COLUMN_ORDER")
    require(all(0<=v<=99999 for v in hits),"NEGATIVE_OR_OVERFLOW_HITS")
    flag=line[10+NC*5:].strip()
    require(flag in (".","Missing") and (sum(hits)==0)==(flag=="Missing"),
            "HITS_MISSING_CONSERVATION")
    return hits,flag

def parse_fraction_row(line:str,index:int)->tuple[list[str],str]:
    require(len(line)>=10+NC*6,"SHORT_F6_3_ROW")
    try:
        i,j=int(line[:5]),int(line[5:10])
    except ValueError as exc:
        raise ValueError("ISSUE160_HEFEI_BAD_FRACTION_INDEX") from exc
    require((i,j)==(index%N+1,index//N+1),"FRACTION_ROW_COLUMN_ORDER")
    fields=[line[10+6*k:16+6*k].strip() for k in range(NC)]
    require(all(re.fullmatch(r"(?:0|1)?\.\d{3}",v) for v in fields),
            "F6_3_TOKEN_INVALID")
    require(all(0<=float(v)<=1 for v in fields),"F6_3_OUTSIDE_UNIT_INTERVAL")
    flag=line[10+NC*6:].strip()
    require(flag in (".","Missing"),"F6_3_BAD_FLAG")
    return fields,flag

def compare(case:Path,glcc:Path,original:Path,native:Path,out:Path)->dict:
    assert_canonical_source(glcc,original)
    require(not out.exists() and not out.is_symlink(),"REPORT_EXISTS")
    p=json.loads((case/"prepare.json").read_text())
    require(p.get("status")=="HEFEI_ORIGINAL_TWO_RUN_DECK_PREPARED" and
            p.get("original_fortran_source_sha256")==SOURCE_SHA and
            p.get("historical_glcc_sha256")==GLCC_SHA,"PREPARE_PROVENANCE")
    hdir=case/"original_hits"
    fdir=case/"original_fractions"
    hdeck=(hdir/"ctgproc.inp").read_text()
    fdeck=(fdir/"ctgproc.inp").read_text()
    validate_deck(hdeck,"F")
    validate_deck(fdeck,"T")
    require(_edit_card(fdeck,"LFINAL","F")==hdeck,"T_NOT_LFINAL_ONLY")
    require(sha(hdir/"ctgproc.inp")==p["hits_control_sha256"] and
            sha(fdir/"ctgproc.inp")==p["fractions_control_sha256"],
            "ORIGINAL_CONTROLS_SHA_CHANGED")
    target=json.loads((native/"p2_original_sampling_manifest.json").read_text())
    require(target.get("producer")=="cteas_p2_original_sampling_hefei" and
            target.get("method")==METHOD and
            target.get("scope")=="HEFEI_200X200_UTM50N_GLCC_HISTORICAL_ONLY" and
            target.get("source_sha256")==GLCC_SHA and
            target.get("original_vendor_source_sha256")==SOURCE_SHA and
            target.get("original_fortran_integer_parity")=="NOT_RUN" and
            target.get("original_fortran_fraction_parity")=="NOT_RUN" and
            target.get("utm_epsg")==32650 and
            target.get("nx")==N and target.get("ny")==N and
            target.get("mesh")==10 and target.get("classes")==NC and
            target.get("xrefkm")==XREF and target.get("yrefkm")==YREF,
            "NATIVE_CANDIDATE_MANIFEST_DRIFT")
    hf=hdir/"lu.dat"
    ff=fdir/"lu.dat"
    nf=native/"lu.dat"
    cf=native/"hits.csv"
    for path in (hf,ff,nf,cf):
        require(regular(path) and path.stat().st_size>1000,
                "REAL_OUTPUT_MISSING_"+path.name)
    require(target.get("hits_csv_sha256")==sha(cf) and
            target.get("lu_dat_sha256")==sha(nf),"NATIVE_OUTPUT_SHA")
    original_hit_total=native_hit_total=0
    errors_int=errors_f63=errors_flag=0
    distinct_cells=0
    missing=0
    first=[]
    with hf.open(encoding="utf-8") as oh, ff.open(encoding="utf-8") as of, \
         nf.open(encoding="utf-8") as nl, cf.open(encoding="utf-8",newline="") as nh:
        parsed_header(oh,"HITS")
        parsed_header(of,"FRACTION")
        parsed_header(nl,"FRACTION")
        reader=csv.reader(nh)
        require(next(reader,None)==["i","j","samples"]+
                [f"cat{c}" for c in CATS],"NATIVE_HITS_CSV_COLUMNS")
        for idx in range(N*N):
            line_h=oh.readline()
            line_f=of.readline()
            line_n=nl.readline()
            row=next(reader,None)
            require(line_h and line_f and line_n and row is not None and
                    len(row)==41 and all(re.fullmatch(r"\d+",v) for v in row),
                    "MISSING_GRID_ROW")
            ih,flag_h=parse_hit_row(line_h.rstrip("\r\n"),idx)
            fo,flag_o=parse_fraction_row(line_f.rstrip("\r\n"),idx)
            fn,flag_n=parse_fraction_row(line_n.rstrip("\r\n"),idx)
            vals=[int(v) for v in row]
            require(vals[:2]==[idx%N+1,idx//N+1],"NATIVE_ROW_ORDER")
            require(sum(vals[3:])==vals[2],"NATIVE_CELL_INTEGER_CONSERVATION")
            n_orig=sum(ih)
            original_hit_total+=n_orig
            native_hit_total+=vals[2]
            missing+=n_orig==0
            bad=False
            for k,(a,b) in enumerate(zip(ih,vals[3:])):
                if a!=b:
                    errors_int+=1
                    bad=True
                    if len(first)<20:
                        first.append({"i":idx%N+1,"j":idx//N+1,
                                      "category":CATS[k],"kind":"hit","original":a,"native":b})
            if vals[2]!=n_orig:
                bad=True
            expected_flag="Missing" if n_orig==0 else "."
            if flag_h!=flag_o or flag_o!=flag_n or flag_n!=expected_flag:
                errors_flag+=1
                bad=True
                if len(first)<20:
                    first.append({"i":idx%N+1,"j":idx//N+1,"kind":"missing_flag",
                                  "original_hits":flag_h,"original_fractions":flag_o,
                                  "native":flag_n})
            for k,(a,b) in enumerate(zip(fo,fn)):
                if float(a)!=float(b):
                    errors_f63+=1
                    bad=True
                    if len(first)<20:
                        first.append({"i":idx%N+1,"j":idx//N+1,
                                      "category":CATS[k],"kind":"F6.3","original":a,"native":b})
            distinct_cells+=bad
        require(not oh.readline() and not of.readline() and
                not nl.readline() and next(reader,None) is None,
                "EXTRA_ROWS")
    good=(errors_int==errors_f63==errors_flag==0 and
          original_hit_total==native_hit_total==
          target.get("total_samples") and
          target.get("missing_cells")==missing and distinct_cells==0)
    result={**p,
            "status":("P2C_HEFEI_20KM_ORIGINAL_GLCC_INTEGER_F63_ZERO_DIFF_PASS"
                      if good else "P2C_HEFEI_ORIGINAL_GLCC_SCIENTIFIC_MISMATCH"),
            "source_code_sha256":SOURCE_SHA,"historical_glcc_sha256":GLCC_SHA,
            "original_fortran_hits_sha256":sha(hf),
            "original_fortran_fraction_sha256":sha(ff),
            "native_hits_sha256":sha(cf),"native_lu_sha256":sha(nf),
            "grid_cells":N*N,"classes":NC,
            "integer_fields_compared":N*N*NC,
            "integer_mismatches":errors_int,
            "F6_3_fields_compared":N*N*NC,"F6_3_mismatches":errors_f63,
            "missing_cells":missing,"missing_flag_mismatches":errors_flag,
            "cells_with_mismatches":distinct_cells,
            "original_total_hits":original_hit_total,"native_total_hits":native_hit_total,
            "first_20_differences":first,
            "modern_glc30m_sampling":"NOT_RUN",
            "p3_makegeo":"OUT_OF_SCOPE_ISSUE46",
            "source_and_original_lu_not_redistributed":True}
    out.write_text(json.dumps(result,indent=2)+"\n")
    require(good,"REAL_40K_X_38_SCIENCE_NOT_ACCEPTED")
    return result

def main()->int:
    p=argparse.ArgumentParser(description=__doc__)
    sub=p.add_subparsers(dest="command",required=True)
    prep=sub.add_parser("prepare")
    prep.add_argument("--template",type=Path,required=True)
    prep.add_argument("--glcc",type=Path,required=True)
    prep.add_argument("--original-source",type=Path,required=True)
    prep.add_argument("--out",type=Path,required=True)
    check=sub.add_parser("compare")
    check.add_argument("--case",type=Path,required=True)
    check.add_argument("--glcc",type=Path,required=True)
    check.add_argument("--original-source",type=Path,required=True)
    check.add_argument("--native",type=Path,required=True)
    check.add_argument("--out",type=Path,required=True)
    a=p.parse_args()
    try:
        if a.command=="prepare":
            d=prepare(a.template,a.glcc,a.original_source,a.out)
        else:
            d=compare(a.case,a.glcc,a.original_source,a.native,a.out)
        print(json.dumps({"status":d["status"],"grid":GRID,
                          "integer_mismatches":d.get("integer_mismatches","NOT_RUN"),
                          "F6_3_mismatches":d.get("F6_3_mismatches","NOT_RUN")}))
        return 0
    except (ValueError, OSError, KeyError, json.JSONDecodeError) as ex:
        print(f"ISSUE160_C1_FAIL_CLOSED:{ex}",file=sys.stderr)
        return 2

if __name__=="__main__":
    raise SystemExit(main())
