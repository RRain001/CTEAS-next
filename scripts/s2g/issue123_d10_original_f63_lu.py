#!/usr/bin/env python3
"""Issue #123 D10: independently run original LFINAL=T and compare every
original F6.3 fraction and missing flag to D9 C++ integer HITS.

D6, D8, D9 accepted authentic SHA-bound reports are hard prerequisites.
An independent original LFINAL=T invocation is mandatory: reformatting
an old LFINAL=F file as an oracle is forbidden. Original BLN must reproduce
byte-for-byte. No third-party data or full LU.DAT in archived artifacts.
"""
from __future__ import annotations
import argparse
import csv
import json
import math
from pathlib import Path
import re
import struct
import sys

from native_cpp.reference.validate_p2_glazas_original import CATS, _edit_card
from scripts.s2g.issue123_original_coastext_wolsong import (
    SOURCE_SHA, GLCC_SHA, sha,
)
from scripts.s2g.issue123_d9_original_coastal_hits import (
    D6_STATUS, D8_STATUS, N, COLS, audit_inputs, control_value,
    parse_fixed_hit_row, parse_lu_header, require,
)

D9_STATUS="D9_REAL_ORIGINAL_GLAZAS_HITS_38_ZERO_DIFF_PASS_SCOPED"
D10_STATUS="D10_REAL_ORIGINAL_GLAZAS_LFINAL_T_F63_FLAGS_ZERO_DIFF_PASS_SCOPED"


def f32(x:float)->float:
    return struct.unpack("<f",struct.pack("<f",x))[0]


def rounded_source_fraction(hit:int,total:int)->str:
    if total<=0 or hit<0 or hit>total:
        raise ValueError("D10_ILLEGAL_NATIVE_HIT_RATIO")
    # Original ctgproc.for SVGRID does NGRID(k,i,j)/FLOAT(ISUM)
    # with REAL*4 intermediate, then WRITE(F6.3).
    return f"{f32(f32(float(hit))/f32(float(total))):.3f}"


def validate_fraction_header(original_lines:list[str],frac_lines:list[str])->None:
    require(len(original_lines)==len(frac_lines)==11,"D10_HEADER_SHAPE")
    require(original_lines[4].strip()=="HITS" and
            frac_lines[4].strip()=="FRACTION","D10_LFINAL_T_NOT_FRACTION")
    # Titles and timestamps may vary between separate original executions.
    # All physical field definitions/grid/category/unit records must agree.
    # Original WRTHEAD intentionally prints land-use IDs with I5 under
    # LFINAL=F but I6 under LFINAL=T (vendor ctgproc.for:5530-5534).
    # Compare their categorical integers, never demand identical raw bytes.
    require(original_lines[5:10]==frac_lines[5:10],
            "D10_ORIGINAL_HITS_VS_FRACTION_GRID_HEADER_DRIFT")
    require(tuple(map(int,original_lines[10].split()))==
            tuple(map(int,frac_lines[10].split()))==
            CATS,"D10_ORIGINAL_HITS_VS_FRACTION_CATEGORY_IDS_DRIFT")
    require(frac_lines[0].split()[:2]==["LU.DAT","2.1"],
            "D10_ORIGINAL_FRACTION_VERSION")
    require(tuple(map(int,frac_lines[10].split()))==CATS,
            "D10_USGS38_ORDER")


def parse_fraction_row(line:str,index:int)->tuple[list[str],str]:
    # Original FORMAT(2I5,38F6.3,A20); field width 6, not whitespace tokens.
    require(len(line)>=10+COLS*6,"D10_ORIGINAL_FRACTION_TRUNCATED")
    try:
        i,j=int(line[:5]),int(line[5:10])
    except ValueError as exc:
        raise ValueError("D10_BAD_ORIGINAL_FRACTION_INDEX") from exc
    require(i==index%N+1 and j==index//N+1,
            "D10_ORIGINAL_FRACTION_CELL_ORDER")
    tokens=[line[10+k*6:16+k*6].strip() for k in range(COLS)]
    require(all(re.fullmatch(r"(?:0|1)?\.\d{3}",v) for v in tokens),
            "D10_NOT_F6_3_NUMERIC_FIELD")
    require(all(0.0<=float(v)<=1.0 and math.isfinite(float(v))
                for v in tokens),"D10_INVALID_ORIGINAL_FRACTION_RANGE")
    flag=line[10+COLS*6:].strip()
    require(flag in (".","Missing"),"D10_ORIGINAL_FRACTION_FLAG_NOT_SCOPED")
    return tokens,flag


def preflight(original_dir:Path,glcc:Path,native:Path,d9report:Path,
              executable:Path,out:Path)->dict:
    require(not out.exists() and not out.is_symlink(),
            "D10_OUTPUT_DIRECTORY_COLLISION")
    audited=audit_inputs(original_dir,native,glcc)
    require(d9report.is_file() and not d9report.is_symlink(),
            "D10_ACTUAL_D9_REPORT_REQUIRED")
    d9=json.loads(d9report.read_text())
    require(d9.get("status")==D9_STATUS and
            d9.get("integer_mismatches")==0 and
            d9.get("cells_with_differences")==0 and
            d9.get("integer_fields_compared")==N*N*COLS and
            d9.get("original_source_sha256")==SOURCE_SHA and
            d9.get("original_glcc_sha256")==GLCC_SHA and
            d9.get("original_bln_sha256")==audited["original_bln_sha256"] and
            d9.get("original_hits_lu_sha256")==audited["original_hits_lu_sha256"] and
            d9.get("native_hits_csv_sha256")==sha(native),
            "D10_D9_AUTHENTIC_HITS_NOT_ACCEPTED")
    d6=json.loads((original_dir/"original_coastext_report.json").read_text())
    require(executable.is_file() and not executable.is_symlink() and
            sha(executable)==d6.get("original_executable_sha256"),
            "D10_ORIGINAL_EXECUTABLE_SHA_DRIFT")
    source_deck=(original_dir/"ctgproc.inp").read_text()
    require(control_value(source_deck,"LFINAL").upper()=="F" and
            control_value(source_deck,"LBLNREAD").upper()=="F",
            "D10_PREDECESSOR_NOT_ORIGINAL_COASTEXT")
    final_deck=_edit_card(source_deck,"LFINAL","T")
    require(control_value(final_deck,"LFINAL").upper()=="T" and
            _edit_card(final_deck,"LFINAL","F")==source_deck,
            "D10_NOT_EXACT_ONE_CONTROL_CARD_CHANGE")
    out.mkdir(parents=True)
    for src_name in ("glcc.img","gshhs_f.b"):
        src=original_dir/src_name
        require(src.is_file(),"D10_REAL_INPUT_NOT_FOUND_"+src_name)
        (out/src_name).symlink_to(src.resolve())
    (out/"ctgproc.inp").write_text(final_deck)
    return {**audited,
        "final_control_sha256":sha(out/"ctgproc.inp"),
        "original_executable_sha256":sha(executable),
        "d9_report_sha256":sha(d9report),
        "final_control_exactly_lfinal_change":True,
        "original_glcc_source":"GLAZAS",
        "coastline_source":"ORIGINAL_GSHHG_FULL_F",
        "final_ocean_fill":"LMARFILL_F",
    }


def compare(original_dir:Path,final_dir:Path,native:Path,
            provenance:dict)->dict:
    bln=final_dir/"coast.bln"
    require(bln.is_file() and not bln.is_symlink() and
            sha(bln)==provenance["original_bln_sha256"],
            "D10_ORIGINAL_BLN_CHANGED_BETWEEN_F_AND_T")
    frac_file=final_dir/"lu.dat"
    hits_file=original_dir/"lu.dat"
    require(frac_file.is_file() and hits_file.is_file(),
            "D10_ORIGINAL_OUTPUT_MISSING")
    differences=0;flag_differences=0;first=[]
    original_frac_nonempty=native_nonempty=0
    with hits_file.open(encoding="utf-8") as hf, \
         frac_file.open(encoding="utf-8") as ff, \
         native.open(encoding="utf-8",newline="") as nf:
        hheader=[hf.readline().rstrip("\r\n") for _ in range(11)]
        fheader=[ff.readline().rstrip("\r\n") for _ in range(11)]
        validate_fraction_header(hheader,fheader)
        nreader=csv.reader(nf)
        require(next(nreader,None)==["i","j","samples"]+
                [f"cat{v}" for v in CATS],
                "D10_NATIVE_HITS_HEADER")
        for idx in range(N*N):
            hline=hf.readline()
            fline=ff.readline()
            nline=next(nreader,None)
            require(bool(hline) and bool(fline) and
                    nline is not None and len(nline)==41,
                    "D10_CELL_ROW_MISSING")
            counts,hflag=parse_fixed_hit_row(hline.rstrip("\r\n"),idx)
            fractions,fflag=parse_fraction_row(fline.rstrip("\r\n"),idx)
            require(all(re.fullmatch(r"\d+",v) for v in nline),
                    "D10_NATIVE_INTEGER_PARSE")
            numbers=list(map(int,nline))
            require(numbers[:2]==[idx%N+1,idx//N+1] and
                    sum(numbers[3:])==numbers[2],
                    "D10_NATIVE_COUNT_GRID_DRIFT")
            total=sum(counts)
            require(numbers[2]==total and numbers[3:]==counts,
                    "D10_ORIGINAL_VS_NATIVE_HITS_DRIFT")
            expected_flag="Missing" if total==0 else "."
            original_frac_nonempty+=total>0
            native_nonempty+=numbers[2]>0
            if hflag!=expected_flag or fflag!=expected_flag:
                flag_differences+=1
                if len(first)<20:
                    first.append({"i":idx%N+1,"j":idx//N+1,
                                  "field":"missing_flag","expected":expected_flag,
                                  "hits_flag":hflag,"final_flag":fflag})
            for k,(hit,actual) in enumerate(zip(counts,fractions)):
                expected=rounded_source_fraction(hit,total) if total else "0.000"
                # Fortran's F6.3 can legally omit a leading zero, but this
                # doesn't change its three printed decimal digits.
                canonical=f"{float(actual):.3f}"
                if canonical!=expected:
                    differences+=1
                    if len(first)<20:
                        first.append({"i":idx%N+1,"j":idx//N+1,
                                      "category":CATS[k],"hits":hit,
                                      "expected":expected,"original":actual})
        require(not hf.readline() and not ff.readline() and
                next(nreader,None) is None,"D10_EXTRA_ORIGINAL_OR_NATIVE_ROWS")
    report={**provenance,
        "status":D10_STATUS if differences==0 and flag_differences==0
                  else "D10_REAL_ORIGINAL_LU_F63_OR_FLAGS_MISMATCH",
        "scope":"SAME_ORIGINAL_EXECUTABLE_REAL_GLAZAS_UTM52N_LFINAL_F_VS_T",
        "printed_fractions_compared":N*N*COLS,
        "grid_cells_compared":N*N,
        "fraction_3dp_differences":differences,
        "missing_flag_differences":flag_differences,
        "nonempty_original_fraction_cells":original_frac_nonempty,
        "nonempty_native_hit_cells":native_nonempty,
        "original_final_lu_sha256":sha(frac_file),
        "original_final_bln_sha256":sha(bln),
        "first_20_differences":first,
        "lmarfill_on_coverage":"NOT_RUN",
        "full_native_production_lu_dat_writer":"NOT_RUN",
        "other_coast_physics_options":"NOT_RUN",
    }
    return report


def main()->int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode",choices=["prepare","compare"])
    parser.add_argument("--original-dir",type=Path,required=True)
    parser.add_argument("--final-dir",type=Path,required=True)
    parser.add_argument("--glcc",type=Path)
    parser.add_argument("--native",type=Path)
    parser.add_argument("--d9-report",type=Path)
    parser.add_argument("--original-exe",type=Path)
    parser.add_argument("--report-out",type=Path)
    args=parser.parse_args()
    try:
        if args.mode=="prepare":
            require(args.glcc is not None and args.native is not None and
                    args.d9_report is not None and args.original_exe is not None,
                    "D10_MISSING_REQUIRED_SOURCE")
            result=preflight(args.original_dir,args.glcc,args.native,
                             args.d9_report,args.original_exe,args.final_dir)
            (args.final_dir/"d10_provenance.json").write_text(
                json.dumps(result,indent=2)+"\n")
        else:
            require(args.native is not None and args.report_out is not None,
                    "D10_COMPARE_ARGS")
            provenance=json.loads((args.final_dir/"d10_provenance.json").read_text())
            require(provenance["final_control_sha256"]==
                    sha(args.final_dir/"ctgproc.inp"),
                    "D10_FINAL_CONTROL_CHANGED")
            result=compare(args.original_dir,args.final_dir,args.native,provenance)
            require(not args.report_out.exists(),"D10_REPORT_COLLISION")
            args.report_out.write_text(json.dumps(result,indent=2)+"\n")
            require(result["status"]==D10_STATUS,
                    "D10_REAL_ORIGINAL_FINAL_F63_NOT_EQUAL")
        print(json.dumps({k:result[k] for k in
            ("status","grid_cells_compared","printed_fractions_compared",
             "fraction_3dp_differences","missing_flag_differences")
            if k in result}))
        return 0
    except (OSError,ValueError,KeyError,OverflowError) as exc:
        print("D10_FAIL_CLOSED:"+type(exc).__name__+":"+str(exc)[:180],
              file=sys.stderr)
        return 2

if __name__=="__main__":
    raise SystemExit(main())
