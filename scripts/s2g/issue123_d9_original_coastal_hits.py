#!/usr/bin/env python3
"""#123 D9: source-pinned Wolsong CTGPROC original LFINAL=F HITS vs
C++ original-BLN coastal recount, all 200x200x38 integer fields.
No reclassified synthetic source or fake zero-filled scientific acceptance.
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
import re
import sys
from scripts.s2g.issue123_original_coastext_wolsong import (
    GRID, SOURCE_SHA, GLCC_SHA, sha, parse_bln,
)
from native_cpp.reference.validate_p2_glazas_original import CATS

D6_STATUS = "D6B_GNU_SPLIT_IO_EOF_ADAPTED_ORIGINAL_COASTEXT_GENERATED_BLN_SCOPED"
D8_STATUS = "D8_REAL_ORIGINAL_BLN_IPTYPE_ZERO_MISMATCH_PASS_SCOPED"
EXPECTED_SOURCE_GSHHG_SHA = "af9215d58ebc525b2d09654a89959829f09e6edc457f3666759cded37be4ecf6"
N = 200
COLS = 38


def require(v: bool, message: str) -> None:
    if not v:
        raise ValueError("D9_" + message)


def control_value(deck: str, key: str) -> str:
    matches = re.findall(r"!\s*" + re.escape(key) + r"\s*=\s*([^!\r\n]*?)\s*!",
                         deck, re.IGNORECASE)
    require(len(matches)==1, "CONTROL_CARD_NOT_UNIQUE_" + key)
    return matches[0].strip()


def validate_controls(control: Path) -> None:
    deck=control.read_text(encoding="utf-8")
    for key,val in (("LFINAL","F"),("LCOAST","T"),("LMARSWAP","T"),
                    ("LMARFILL","F"),("LBLNREAD","F"),("IOCEAN","55"),
                    ("MESHGLAZ","10"),("NX","200"),("NY","200"),
                    ("IUTMZN","52"),("XREFKM","533.215"),
                    ("YREFKM","3942.629"),("DGRIDKM","0.100")):
        require(control_value(deck,key).upper()==val, "CONTROL_DRIFT_"+key)
    require(re.search(r"(?m)^1\s+!GLAZAS\s*=\s*glcc.img\s*!", deck) is not None,
            "NOT_ORIGINAL_LEGAL_GLAZAS")


def parse_lu_header(fp):
    lines = [fp.readline().rstrip("\r\n") for _ in range(11)]
    require(len(lines)==11 and bool(lines[10]),"ORIGINAL_HITS_SHORT_HEADER")
    require(lines[0].split()[:2]==["LU.DAT","2.1"],"ORIGINAL_HITS_VERSION")
    require(lines[4].strip()=="HITS" and lines[5].strip()=="UTM" and
            lines[6].strip()=="52N" and lines[7].startswith("WGS-84"),
            "ORIGINAL_HITS_NOT_UTM52N_LFINAL_F")
    values=lines[8].split()
    require(len(values)>=7 and
            [int(v) for v in values[:2]]==[200,200] and
            abs(float(values[2])-533.215)<1e-6 and
            abs(float(values[3])-3942.629)<1e-6 and
            abs(float(values[4])-.1)<1e-6 and
            abs(float(values[5])-.1)<1e-6 and
            int(values[6])==38, "ORIGINAL_HITS_WRONG_WOLSONG_GRID")
    require(lines[9].split()==["KM"],"ORIGINAL_HITS_WRONG_UNIT")
    require(tuple(map(int,lines[10].split()))==CATS,
            "ORIGINAL_HITS_CATEGORY_ORDER")


def parse_fixed_hit_row(line: str, index: int):
    # Original ctgproc.for SVGRID fmtc='(2i5,38i5,a20)'.
    # Fixed fields must be used: adjacent I5=99999 values can have no spaces.
    require(len(line)>=200,"ORIGINAL_HITS_TRUNCATED_ROW")
    try:
        i,j=int(line[:5]),int(line[5:10])
        counts=[int(line[10+5*k:15+5*k]) for k in range(COLS)]
    except ValueError as exc:
        raise ValueError("D9_ORIGINAL_HITS_INVALID_INTEGER") from exc
    require(i==index%N+1 and j==index//N+1,"ORIGINAL_HITS_CELL_ORDER")
    require(all(v>=0 for v in counts),"ORIGINAL_HITS_NEGATIVE_COUNT")
    flag=line[200:].strip()
    require(flag in (".","Missing"),"ORIGINAL_HITS_UNEXPECTED_FLAG")
    require((sum(counts)==0)==(flag=="Missing"),"ORIGINAL_HITS_FLAG_SUM")
    return counts,flag


def audit_inputs(original_dir:Path,native:Path,glcc:Path) -> dict:
    d6file=original_dir/"original_coastext_report.json"
    d8file=original_dir.parent/"issue123-d8-oracle"/"d8_iptype_report.json"
    # When oracle lives in the runner temp parallel to D6 as by workflow:
    require(d6file.is_file() and not d6file.is_symlink(),"D6_AUDIT_MISSING")
    require(d8file.is_file() and not d8file.is_symlink(),"D8_SCIENCE_GATE_MISSING")
    d6=json.loads(d6file.read_text())
    d8=json.loads(d8file.read_text())
    bln=original_dir/"coast.bln"
    control=original_dir/"ctgproc.inp"
    lu=original_dir/"lu.dat"
    for path in (bln,control,lu,glcc,native):
        require(path.is_file() and not path.is_symlink() and path.stat().st_size>0,
                "MISSING_AUTHENTIC_FILE_"+path.name)
    require(glcc.stat().st_size==156_000_000 and sha(glcc)==GLCC_SHA,
            "GLCC_ORIGINAL_BYTES_INVALID")
    require(d6.get("status")==D6_STATUS and
            d6.get("original_source_sha256")==SOURCE_SHA and
            d6.get("original_glcc_sha256")==GLCC_SHA and
            d6.get("original_gshhs_full_sha256")==EXPECTED_SOURCE_GSHHG_SHA and
            d6.get("original_coastext_bln")=="PASS_ORIGINAL_OUTPUT_PRESENT" and
            d6.get("original_bln_sha256")==sha(bln) and
            d6.get("control_sha256")==sha(control),
            "D6_SOURCE_OR_BLN_SHA_ADMISSION")
    real_bln=parse_bln(bln)
    require(real_bln["original_bln_sha256"]==d6["original_bln_sha256"] and
            real_bln["vertices"]==d6["vertices"] and
            real_bln["polygons"]==d6["polygons"],
            "D6_BLN_GEOMETRY_CHANGED")
    require(d8.get("status")==D8_STATUS and d8.get("mismatch_count")==0 and
            d8.get("original_bln_sha256")==sha(bln) and
            d8.get("original_source_sha256")==SOURCE_SHA,
            "D8_REAL_ORIGINAL_ZERO_MISMATCH_GATE_REQUIRED")
    validate_controls(control)
    return {"original_source_sha256":SOURCE_SHA,
            "original_gshhg_full_sha256":EXPECTED_SOURCE_GSHHG_SHA,
            "original_glcc_sha256":GLCC_SHA,
            "original_bln_sha256":sha(bln),
            "original_control_sha256":sha(control),
            "original_hits_lu_sha256":sha(lu),
            "native_hits_csv_sha256":sha(native),
            "d8_report_sha256":sha(d8file),
            "grid":GRID}


def compare(original_lu:Path,native_csv:Path,provenance:dict) -> dict:
    diff=0
    max_abs=0
    total_abs=0
    distinct_cells=0
    orig_total=native_total=orig_nonempty=native_nonempty=0
    first=[]
    with original_lu.open(encoding="utf-8") as source, \
            native_csv.open(encoding="utf-8",newline="") as target:
        parse_lu_header(source)
        reader=csv.reader(target)
        require(next(reader,None)==["i","j","samples"]+
                [f"cat{k}" for k in CATS],"NATIVE_COLUMNS_INVALID")
        for index in range(N*N):
            original_line=source.readline()
            require(bool(original_line),"ORIGINAL_HITS_ROW_COUNT_SHORT")
            oh,flag=parse_fixed_hit_row(original_line.rstrip("\r\n"),index)
            row=next(reader,None)
            require(row is not None and len(row)==41 and
                    all(re.fullmatch(r"\d+",x) for x in row),
                    "NATIVE_HITS_MISSING_OR_NON_INTEGER")
            vals=list(map(int,row))
            require(vals[:2]==[index%N+1,index//N+1],
                    "NATIVE_CELL_ORDER")
            n=vals[2]
            nh=vals[3:]
            require(sum(nh)==n and len(nh)==COLS,
                    "NATIVE_HITS_CELL_CONSERVATION")
            osum=sum(oh)
            orig_total+=osum
            native_total+=n
            orig_nonempty+=bool(osum)
            native_nonempty+=bool(n)
            mismatch_here=False
            if osum!=n:mismatch_here=True
            for k,(orig,cpp) in enumerate(zip(oh,nh)):
                delta=abs(orig-cpp)
                total_abs+=delta
                max_abs=max(max_abs,delta)
                if delta:
                    diff+=1;mismatch_here=True
                    if len(first)<20:
                        first.append({"i":index%N+1,"j":index//N+1,
                                      "category":CATS[k],"original":orig,
                                      "cpp":cpp,"delta":cpp-orig})
            distinct_cells+=mismatch_here
        require(not source.readline(),"ORIGINAL_HITS_EXTRA_ROWS")
        require(next(reader,None) is None,"NATIVE_HITS_EXTRA_ROWS")
    result={**provenance,
        "status":"D9_REAL_ORIGINAL_GLAZAS_HITS_38_ZERO_DIFF_PASS_SCOPED"
            if diff==0 and distinct_cells==0
            else "D9_ORIGINAL_GLCC_HITS_MISMATCH",
        "original_fortran_control":"LFINAL_F_LCOAST_T_LMARSWAP_T_GLAZAS",
        "native_method":"GLCC_DIRECT_LAEA_UTM52N_MESH10_D7_REAL_BLN_RECOUNT",
        "cells_compared":N*N,"classes_compared":COLS,
        "integer_fields_compared":N*N*COLS,
        "integer_mismatches":diff,
        "cells_with_differences":distinct_cells,
        "max_absolute_hit_difference":max_abs,
        "total_absolute_hit_difference":total_abs,
        "original_total_hits":orig_total,
        "native_total_hits":native_total,
        "original_nonempty_cells":orig_nonempty,
        "native_nonempty_cells":native_nonempty,
        "first_20_disagreements":first,
        "d10_formatted_fraction_and_flags":"NOT_RUN",
        "production_integration":"NOT_RUN",
    }
    return result


def main()->int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--original-dir",type=Path,required=True)
    p.add_argument("--native-hits",type=Path,required=True)
    p.add_argument("--glcc",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    args=p.parse_args()
    try:
        require(not args.out.exists() and not args.out.is_symlink(),
                "OUTPUT_ALREADY_EXISTS")
        inputs=audit_inputs(args.original_dir,args.native_hits,args.glcc)
        report=compare(args.original_dir/"lu.dat",args.native_hits,inputs)
        args.out.write_text(json.dumps(report,indent=2)+"\n")
        print(json.dumps({k:report[k] for k in
             ("status","integer_fields_compared","integer_mismatches",
              "max_absolute_hit_difference")}))
        require(report["integer_mismatches"]==0 and
                report["cells_with_differences"]==0,
                "REAL_ORIGINAL_HITS_DIFFER")
        return 0
    except (ValueError,OSError,KeyError) as err:
        print(f"D9_FAIL_CLOSED:{type(err).__name__}:{str(err)[:200]}",
              file=sys.stderr)
        return 2


if __name__=="__main__":
    raise SystemExit(main())
