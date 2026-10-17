#!/usr/bin/env python3
"""Original CALMET DIAGNO tail SMOOTH/DIVCEL/W/WINDBC against G24 source.

Actual G19-G23 original-format 2SS/2US SYNTHETIC meteorology, original
G23 post-INTER2 12x12x9 U/V, untouched source-grid ZFACE/NMSMTH, and
original G24 post-INTER2 second WINDBC. Only original tail is independently
Fortran-computed, NOT full STHEOR/MIXHTST/DIAGNO or 45-field hour parity.
"""
from __future__ import annotations

import argparse
import json
import math
import subprocess
import tempfile
from pathlib import Path

import compare_original_diagno_final_segment as original
from compare_g10_original_diagno_10km import (
    VENDOR, check_rows, TOL_WIND, TOL_DIV,
)

NX=NY=12
NZ=9


def source_guard(path: Path) -> None:
    lines=path.read_text().splitlines()
    # 2 header rows + U/V 2*9*12 rows + UB/VB 2*9*2 rows.
    if len(lines) != 2 + (2*NZ*NY) + (2*NZ*2):
        raise ValueError("G24 original 12x12x9 DIAGNO tail stage shape malformed")
    dz=[float(x) for x in lines[0].split()]
    smooth=[int(x) for x in lines[1].split()]
    if len(dz)!=NZ or any(not math.isfinite(x) or x<=0 for x in dz):
        raise ValueError("G24 actual original ZFACE/DZ missing")
    if len(smooth)!=NZ or any(x<0 for x in smooth):
        raise ValueError("G24 source NSMTH incorrectly typed")
    for row in lines[2:]:
        vals=[float(x) for x in row.split()]
        if len(vals)!=NX or not all(map(math.isfinite,vals)):
            raise ValueError("G24 original source interpolated wind or WINDBC missing")


def main()->None:
    parser=argparse.ArgumentParser()
    parser.add_argument("--mode",choices=("Debug","Release"),required=True)
    parser.add_argument("--source-stage",type=Path,required=True)
    parser.add_argument("--native",type=Path,required=True)
    parser.add_argument("--native-boundaries",type=Path,required=True)
    parser.add_argument("--require-nontrivial",action="store_true")
    parser.add_argument("--out",type=Path,required=True)
    args=parser.parse_args()
    source_guard(args.source_stage)

    with tempfile.TemporaryDirectory(prefix="p6g-g24-original-diagno-") as tmp:
        work=Path(tmp)
        routines,block,source=original.original_source(VENDOR,work)
        driver=work/"g24_source_diagno.for"
        driver.write_text(
            original.DRIVER_HEAD.replace("nx=50","nx=12").replace(
                "ny=50","ny=12").replace("dx=100.","dx=10000.").replace(
                "dy=100.","dy=10000.")+
            block+original.DRIVER_TAIL
        )
        exe=work/"original_g24_diagno"
        opt="-O0" if args.mode=="Debug" else "-O2"
        subprocess.run([
            "gfortran",opt,"-std=legacy","-fno-automatic",
            "-ffixed-line-length-none","-I"+str(VENDOR),
            *[str(path) for path,_ in routines],str(driver),"-o",str(exe)
        ],check=True,capture_output=True,text=True)
        ref=work/"g24-original-winds.txt"
        bound=work/"g24-original-boundaries.txt"
        program=subprocess.run([
            str(exe),str(args.source_stage),str(ref),str(bound)
        ],cwd=work,capture_output=True,text=True)
        if program.returncode:
            raise RuntimeError(
                f"G24 original vendor DIAGNO tail failed {program.returncode}: "
                f"{program.stderr[-2400:]} {program.stdout[-900:]}")
        result=check_rows(ref,args.native,bound,args.native_boundaries)

    evidence={
        "scope":"Source-format G24 original post-INTER2 second WINDBC SMOOTH DIVCEL W",
        "source_cases":"2SS2US 12x12x9 source files with synthetic observations",
        "mode":args.mode,
        "original_vendor_sha":source["git_blob"],
        "source_routines":[r for _,r in routines],
        "original_diagno_lines":source["literal_diagno_lines"],
        "original_uv_div_w_values":result["uv_div_w_values"],
        "original_boundary_values":result["boundary_values"],
        "nonzero_original_w_cells":result["nonzero_w"],
        "max_abs":result["max_abs"],
        "max_boundary_abs_mps":result["max_boundary"],
        "unchanged_wind_tolerance_mps":TOL_WIND,
        "unchanged_divergence_tolerance_per_second":TOL_DIV,
        "required_nontrivial":args.require_nontrivial,
        "upstream_original_stheor_mixhtst_comp":False,
        "full_multistation_original_45_fields":False,
    }
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(evidence,indent=2)+"\n")
    if args.require_nontrivial and result["nonzero_w"]==0:
        raise AssertionError("G24 original DIAGNO W is zero everywhere in stress test")
    print(
        f"PASS_P6G_G24_LITERAL_ORIGINAL_DIAGNO mode={args.mode} "
        f"uv_div_w={result['uv_div_w_values']} boundaries={result['boundary_values']} "
        f"nonzero_w={result['nonzero_w']} max_errors={result['max_abs']} "
        f"max_boundary={result['max_boundary']:.9g} "
        "FULL_45_FIELD_MULTISTATION=NOT_ACCEPTED"
    )


if __name__=="__main__":
    main()
