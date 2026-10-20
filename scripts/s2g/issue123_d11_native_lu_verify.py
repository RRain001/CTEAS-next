#!/usr/bin/env python3
"""#123 D11: genuine original LFINAL=T vs independently generated C++ native
ORIGINAL_SAMPLING LU.DAT, same real-source Wolsong case. Fail closed.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys

from native_cpp.reference.validate_p2_glazas_original import CATS
from scripts.s2g.issue123_original_coastext_wolsong import SOURCE_SHA, GLCC_SHA, sha
from scripts.s2g.issue123_d9_original_coastal_hits import require, N, COLS
from scripts.s2g.issue123_d10_original_f63_lu import (
    D10_STATUS, parse_fraction_row,
)

EXPECTED_METHOD="ORIGINAL_SAMPLING_GLAZAS_REAL4_GSHHG_F_COASTRD_LUGRID_SVGRID_F63_V1"
EXPECTED_PRODUCER="cteas_p2_original_sampling_wolsong"
D11_STATUS="D11_REAL_ORIGINAL_VS_NATIVE_PRODUCTION_LU_F63_FLAGS_ZERO_DIFF_PASS_WOLSONG"


def read_header(reader):
    lines=[reader.readline().rstrip("\r\n") for _ in range(11)]
    require(lines[0].split()[:2]==["LU.DAT","2.1"],
            "D11_BAD_LU_VERSION")
    require(lines[4].strip()=="FRACTION" and
            lines[5].strip()=="UTM" and
            lines[6].strip()=="52N" and
            lines[7].startswith("WGS-84"),"D11_LU_WRONG_PROJECTION")
    dims=lines[8].split()
    require(len(dims)==7 and
            [int(v) for v in dims[:2]]==[N,N] and
            all(abs(float(dims[i])-target)<1e-6 for i,target in
                [(2,533.215),(3,3942.629),(4,.1),(5,.1)]) and
            int(dims[6])==COLS,"D11_WRONG_GRID_OR_CLASS")
    require(lines[9].strip()=="KM" and
            tuple(map(int,lines[10].split()))==CATS,
            "D11_USGS38_CATEGORY_ORDER")
    return lines


def compare(original:Path,native:Path,metadata:dict)->dict:
    differing_fractions=differing_flags=0
    first=[]
    with original.open(encoding="utf-8") as a, native.open(encoding="utf-8") as b:
        ah=read_header(a)
        bh=read_header(b)
        # Original WRTHEAD's comment and NIMADATE version strings are
        # informational and may differ from a standalone native producer.
        # Require the actual physical field definition, UTM zone, grid
        # geometry and original 38-class IDs to be identical.
        require(ah[4:7]==bh[4:7] and ah[8:11]==bh[8:11] and
                ah[7][:8]==bh[7][:8],
                "D11_ORIGINAL_NATIVE_PHYSICAL_HEADER_DRIFT")
        for index in range(N*N):
            orig=a.readline()
            cpp=b.readline()
            require(bool(orig) and bool(cpp),"D11_TRUNCATED_LU")
            ov,of=parse_fraction_row(orig.rstrip("\r\n"),index)
            nv,nf=parse_fraction_row(cpp.rstrip("\r\n"),index)
            if of!=nf:
                differing_flags+=1
                if len(first)<20:
                    first.append({"i":index%N+1,"j":index//N+1,
                                  "field":"flag","original":of,"cpp":nf})
            for k,(x,y) in enumerate(zip(ov,nv)):
                # Compare exactly the 3 printed decimal places, allowing
                # original Fortran F6.3 optional leading zero.
                if f"{float(x):.3f}"!=f"{float(y):.3f}":
                    differing_fractions+=1
                    if len(first)<20:
                        first.append({"i":index%N+1,"j":index//N+1,
                                      "category":CATS[k],
                                      "original":x,"cpp":y})
        require(not a.readline() and not b.readline(),
                "D11_EXTRA_LU_ROWS")
    return {**metadata,
        "status":D11_STATUS if not differing_fractions and not differing_flags
                else "D11_REAL_ORIGINAL_VS_NATIVE_LU_MISMATCH",
        "grid_cells_compared":N*N,
        "fraction_fields_compared":N*N*COLS,
        "fraction_3dp_differences":differing_fractions,
        "missing_flag_differences":differing_flags,
        "first_20_differences":first,
        "other_glcc_domains":"NOT_RUN",
        "other_original_coast_options":"NOT_RUN",
        "p3_p6_p7":"NOT_RUN",
    }


def main()->int:
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--original-final-dir",type=Path,required=True)
    ap.add_argument("--native-dir",type=Path,required=True)
    ap.add_argument("--d10-report",type=Path,required=True)
    ap.add_argument("--out",type=Path,required=True)
    args=ap.parse_args()
    try:
        require(not args.out.exists() and not args.out.is_symlink(),
                "D11_OUTPUT_ALREADY_EXISTS")
        require(args.d10_report.is_file() and not args.d10_report.is_symlink(),
                "D11_D10_AUTHENTIC_REPORT_MISSING")
        d10=json.loads(args.d10_report.read_text())
        orig=args.original_final_dir/"lu.dat"
        native=args.native_dir/"lu.dat"
        mp=args.native_dir/"p2_original_sampling_manifest.json"
        for file in (orig,native,mp):
            require(file.is_file() and not file.is_symlink(),
                    "D11_SOURCE_FILE_MISSING_"+file.name)
        m=json.loads(mp.read_text())
        require(d10.get("status")==D10_STATUS and
                d10.get("fraction_3dp_differences")==0 and
                d10.get("missing_flag_differences")==0 and
                d10.get("original_final_lu_sha256")==sha(orig) and
                d10.get("original_bln_sha256")==m.get("original_bln_sha256") and
                d10.get("original_source_sha256")==SOURCE_SHA and
                d10.get("original_glcc_sha256")==GLCC_SHA,
                "D11_REAL_ORIGINAL_D10_SCIENCE_GATE_NOT_MET")
        require(m.get("producer")==EXPECTED_PRODUCER and
                m.get("method")==EXPECTED_METHOD and
                m.get("source_sha256")==GLCC_SHA and
                m.get("original_vendor_source_sha256")==SOURCE_SHA and
                m.get("lu_dat_sha256")==sha(native) and
                m.get("total_samples")==40025 and
                m.get("nonempty_cells")==37035 and
                m.get("missing_cells")==2965 and
                m.get("fraction_fields")==1520000 and
                m.get("gshhg_resolution")=="Full" and
                m.get("lmarfill") is False,
                "D11_UNTRUSTED_NATIVE_OR_SOURCE_MANIFEST")
        detail=compare(orig,native,{
            "original_source_sha256":SOURCE_SHA,
            "original_glcc_sha256":GLCC_SHA,
            "original_bln_sha256":d10["original_bln_sha256"],
            "original_lfinal_lu_sha256":sha(orig),
            "native_lu_sha256":sha(native),
            "native_manifest_sha256":sha(mp),
            "d10_science_report_sha256":sha(args.d10_report),
            "method":EXPECTED_METHOD,
        })
        args.out.write_text(json.dumps(detail,indent=2)+"\n")
        print(json.dumps({k:detail[k] for k in
              ("status","fraction_fields_compared",
               "fraction_3dp_differences","missing_flag_differences")}))
        require(detail["status"]==D11_STATUS,
                "D11_NATIVE_FINAL_LU_DIFFERS_FROM_ORIGINAL")
        return 0
    except (ValueError,OSError,KeyError) as e:
        print("D11_FAIL_CLOSED:"+type(e).__name__+":"+str(e)[:200],
              file=sys.stderr)
        return 2


if __name__=="__main__":
    raise SystemExit(main())
