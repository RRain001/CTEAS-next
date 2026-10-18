#!/usr/bin/env python3
"""#53: independent original GLAZAS fractional LU and INTEGER HITS science.

CTGPROC's 'Number of data points used to update grid' is ncount, the count
of original GLCC source pixels whose sub-mesh touches the grid. Native D1
'included' and C++ cell_samples instead count individual MESHGLAZ subpoints.
Those counts MUST NEVER be directly equated (original 56 vs native 10011).
The trustworthy integer oracle is CTGPROC LU.DAT generated at LFINAL=F.
"""
from __future__ import annotations
import argparse
import csv
import json
from pathlib import Path
import re
import shutil
import os
import subprocess
import time

from native_cpp.reference.diagnose_glazas_mesh_coordinates import audit as diagnose_coordinates

from native_cpp.reference.validate_p2_glazas_original import (
    CATS, SRC_SHA, SRC_SIZE, CTEAS_ORIGINAL_COMMIT,
    CTGPROC_ORIGINAL_SOURCE_SHA256, FLOAT_TOL, GateError, require, file_sha,
    safe_original_file, make_glazas_control, _edit_card, parse_lu,
    parse_original_used, compare,
)

def read_hits(path: Path) -> list[list[int]]:
    lines = path.read_text(encoding="utf-8",errors="strict").splitlines()
    require(len(lines)==2511,"ORIGINAL_HITS_NOT_2511_LINES")
    require(lines[0].split()[:2]==["LU.DAT","2.1"],"ORIGINAL_HITS_BAD_VERSION")
    require(lines[4].strip()=="HITS" and lines[5].strip()=="UTM",
            "ORIGINAL_NOT_INTEGER_HITS_MODE")
    require(lines[6].strip()=="50N" and lines[7].startswith("WGS-84"),
            "ORIGINAL_HITS_BAD_CRS")
    hdr=lines[8].split()
    require(len(hdr)>=7 and [int(q) for q in hdr[:2]]==[50,50]
            and abs(float(hdr[2])-510.885)<1e-6
            and abs(float(hdr[3])-3531.269)<1e-6
            and abs(float(hdr[4])-.1)<1e-6
            and abs(float(hdr[5])-.1)<1e-6
            and int(hdr[6])==38, "ORIGINAL_HITS_GRID_MISMATCH")
    require(lines[9].split()==["KM"],"ORIGINAL_HITS_UNITS_NOT_KM")
    require(tuple(map(int,lines[10].split()))==CATS,"ORIGINAL_HITS_CATEGORY_ORDER")
    rows=[]
    for idx,line in enumerate(lines[11:]):
        f=line.split()
        require(len(f)==41 and f[-1]==".","ORIGINAL_HITS_BAD_ROW_OR_FLAGS")
        require(int(f[0])==idx%50+1 and int(f[1])==idx//50+1,
                "ORIGINAL_HITS_GRID_ORDER")
        v=[]
        for token in f[2:-1]:
            require(re.fullmatch(r"[0-9]+",token) is not None,"ORIGINAL_HITS_NON_INTEGER")
            v.append(int(token))
        require(len(v)==38,"ORIGINAL_HITS_BAD_CLASSES")
        rows.append(v)
    return rows

def read_native_hits(path: Path, manifest: dict) -> tuple[list[list[int]],list[int]]:
    require(manifest.get("producer")=="cteas_p2_glcc_raw"
            and manifest.get("source_sha256")==SRC_SHA
            and manifest.get("method")=="GLCC_HEADERLESS_ROW_DIRECT_GEN_7DP_REAL4_REPLAY",
            "NATIVE_HITS_UNTRUSTED_PRODUCER")
    require(manifest.get("nx")==50 and manifest.get("ny")==50
            and manifest.get("utm_epsg")==32650 and manifest.get("mesh")==20,
            "NATIVE_HITS_UNTRUSTED_GRID")
    require(manifest.get("hits_csv_sha256")==file_sha(path),
            "NATIVE_HITS_CSV_SHA_MISMATCH")
    rows=[];samples=[]
    with path.open(newline="",encoding="utf-8") as fp:
        rd=csv.reader(fp)
        require(next(rd,None)==["i","j","samples"]+[f"cat{x}" for x in CATS],
                "NATIVE_HITS_BAD_HEADER")
        for idx,line in enumerate(rd):
            require(idx<2500 and len(line)==41,"NATIVE_HITS_BAD_ROW")
            require(int(line[0])==idx%50+1 and int(line[1])==idx//50+1,
                    "NATIVE_HITS_GRID_ORDER")
            require(all(re.fullmatch(r"[0-9]+",token) is not None
                        for token in line[2:]),"NATIVE_HITS_BAD_INTEGER")
            n=int(line[2]);counts=list(map(int,line[3:]))
            require(n>0 and len(counts)==38 and sum(counts)==n,
                    "NATIVE_HITS_PER_CELL_COUNT_INVALID")
            samples.append(n);rows.append(counts)
    require(len(rows)==2500,"NATIVE_HITS_ROWS_NOT_2500")
    require(sum(samples)==manifest.get("included"),
            "NATIVE_HITS_SAMPLES_D1_TOTAL_MISMATCH")
    return rows,samples

def compare_integer_hits(original_rows, native_rows, native_samples,
                         original_fraction_rows, native_fraction_rows) -> dict:
    require(len(original_rows)==len(native_rows)==len(native_samples)==2500,
            "HITS_COMPARISON_SHAPE")
    exceedances=0;first=[];maxdelta=0;sumdelta=0;cell_count_deltas=0
    original_total=0;native_total=0;original_fraction_exceedances=0
    for idx,(oh,nh,n) in enumerate(zip(original_rows,native_rows,native_samples)):
        osum=sum(oh);nsum=sum(nh)
        original_total+=osum;native_total+=nsum
        require(nsum==n,"NATIVE_INTEGER_HITS_SAMPLES_MISMATCH")
        if osum!=nsum: cell_count_deltas+=1
        for k,(ov,nv) in enumerate(zip(oh,nh)):
            delta=abs(ov-nv)
            maxdelta=max(maxdelta,delta);sumdelta+=delta
            if delta:
                exceedances+=1
                if len(first)<20:
                    first.append(dict(i=idx%50+1,j=idx//50+1,
                                      usgs_category=CATS[k],original_hits=ov,
                                      native_hits=nv,delta=nv-ov))
        # Ensure original HITS belongs to the same *fraction* control inputs.
        # Both original GLAZAS passes must describe exactly the same integer count array.
        require(osum>0,"ORIGINAL_HITS_MISSING_COVERAGE")
        for k,hit in enumerate(oh):
            if abs(original_fraction_rows[idx][k]-hit/osum)>FLOAT_TOL+1e-8:
                original_fraction_exceedances+=1
    return {
        "integer_values_compared":95000,
        "max_integer_absolute_difference":maxdelta,
        "integer_difference_total_absolute":sumdelta,
        "integer_exceedances":exceedances,
        "different_cell_total_hit_counts":cell_count_deltas,
        "original_integer_submesh_hits_total":original_total,
        "native_integer_submesh_hits_total":native_total,
        "original_hits_vs_original_fraction_exceedances":original_fraction_exceedances,
        "first_20_integer_disagreements":first,
        "integer_gate":"PASS" if exceedances==0 and
                       cell_count_deltas==0 and
                       original_fraction_exceedances==0 else "FAIL",
    }

def stage_img(source: Path, work: Path):
    try:
        os.link(source,work/"glcc.img")
    except OSError:
        shutil.copyfile(source,work/"glcc.img")
    safe_original_file(work/"glcc.img",expected=SRC_SHA,exact_size=SRC_SIZE)

def main(argv=None) -> int:
    p=argparse.ArgumentParser(description=__doc__)
    for key in ("source-img","original-ctgproc","original-source-file",
                "control-template","native-lu","native-d3-manifest",
                "native-hits-csv","native-d1-manifest","out-dir"):
        p.add_argument("--"+key,type=Path,required=True)
    p.add_argument("--original-bin-sha256",required=True)
    p.add_argument("--native-qa-csv",type=Path)
    p.add_argument("--timeout-sec",type=int,default=300)
    a=p.parse_args(argv)
    require(10<=a.timeout_sec<=600,"TIMEOUT_OUT_OF_BOUNDS")
    safe_original_file(a.source_img,expected=SRC_SHA,exact_size=SRC_SIZE)
    require(a.original_ctgproc.is_file() and os.access(a.original_ctgproc,os.X_OK),
            "ORIGINAL_BINARY_MISSING_OR_NOT_EXECUTABLE")
    safe_original_file(a.original_ctgproc,expected=a.original_bin_sha256)
    safe_original_file(a.original_source_file,expected=CTGPROC_ORIGINAL_SOURCE_SHA256)
    for path in (a.control_template,a.native_lu,a.native_d3_manifest,
                 a.native_hits_csv,a.native_d1_manifest):
        require(path.is_file() and not path.is_symlink(),"MISSING_INPUT_OR_SYMLINK")
    require(not a.out_dir.exists() and not a.out_dir.is_symlink(),
            "OUTPUT_DIR_ALREADY_EXISTS")
    d1=json.loads(a.native_d1_manifest.read_text(encoding="utf-8"))
    d3=json.loads(a.native_d3_manifest.read_text(encoding="utf-8"))
    require(d3.get("producer")=="cteas_p2_glcc_lu_dat"
            and d3.get("source_sha256")==SRC_SHA
            and d3.get("lu_dat_sha256")==file_sha(a.native_lu)
            and d3.get("original_GLAZAS_parity")=="NOT_RUN"
            and d3.get("total_samples")==d1.get("included"),
            "D1_D3_ORIGINAL_BINDING_UNTRUSTED")
    if a.native_qa_csv is not None:
        require(a.native_qa_csv.is_file() and not a.native_qa_csv.is_symlink(),
                "NATIVE_QA_MISSING_OR_SYMLINK")
        require(d1.get("diagnostic_submesh_csv_sha256")==file_sha(a.native_qa_csv),
                "NATIVE_QA_SOURCE_SHA_MISMATCH")
    native_hits,native_samples=read_native_hits(a.native_hits_csv,d1)
    native_fractions=parse_lu(a.native_lu)
    for idx,row in enumerate(native_hits):
        for k,hit in enumerate(row):
            require(abs(native_fractions[idx][k]-hit/native_samples[idx])
                    <= FLOAT_TOL+1e-8, "NATIVE_HITS_FRACTIONS_DISAGREE")
    control=make_glazas_control(a.control_template.read_text(encoding="utf-8"))
    hits_control=_edit_card(control,"LFINAL","F")
    require("!GLAZAS = glcc.img !" in hits_control
            and "! LFINAL = F !" in hits_control,"HITS_NOT_GLAZAS_OR_NOT_LFINAL_F")
    a.out_dir.mkdir(parents=True)
    fraction_work=a.out_dir/"original_fraction"
    hits_work=a.out_dir/"original_hits"
    try:
        fraction_work.mkdir()
        hits_work.mkdir()
        stage_img(a.source_img,fraction_work)
        stage_img(a.source_img,hits_work)
        fraction_elapsed=execute_original_existing(a.original_ctgproc,fraction_work,control,a.timeout_sec)
        hits_elapsed=execute_original_existing(a.original_ctgproc,hits_work,hits_control,a.timeout_sec)
        require(file_sha(a.source_img)==SRC_SHA,"SOURCE_CHANGED_DURING_EXECUTION")
        original_fractions=parse_lu(fraction_work/"lu.dat")
        original_hits=read_hits(hits_work/"lu.dat")
        # Fraction field check uses existing pinned original GLAZAS comparator.
        fractions=compare(fraction_work/"lu.dat",a.native_lu,
                          fraction_work/"ctgproc.lst",a.native_d3_manifest)
        # 56 original source pixels used != 10011 mesh hits.
        original_parent_count=parse_original_used(fraction_work/"ctgproc.lst")
        hits_parent_count=parse_original_used(hits_work/"ctgproc.lst")
        require(original_parent_count==hits_parent_count and original_parent_count>0,
                "ORIGINAL_LFINAL_F_SOURCE_PIXEL_COUNT_CHANGED")
        ints=compare_integer_hits(original_hits,native_hits,native_samples,
                                  original_fractions,native_fractions)
        report={
          "gate":"P2_A_REAL_ORIGINAL_GLAZAS_FRACTION_AND_INTEGER_HITS",
          "source_sha256":SRC_SHA,
          "cteas_git_commit":CTEAS_ORIGINAL_COMMIT,
          "original_ctgproc_source_sha256":CTGPROC_ORIGINAL_SOURCE_SHA256,
          "original_binary_sha256":a.original_bin_sha256,
          "control_fraction_sha256":file_sha(fraction_work/"ctgproc.inp"),
          "control_hits_sha256":file_sha(hits_work/"ctgproc.inp"),
          "original_fraction_lu_sha256":file_sha(fraction_work/"lu.dat"),
          "original_integer_hits_lu_sha256":file_sha(hits_work/"lu.dat"),
          "native_d1_hits_csv_sha256":file_sha(a.native_hits_csv),
          "native_d3_fraction_lu_sha256":file_sha(a.native_lu),
          "original_fraction_execution_seconds":fraction_elapsed,
          "original_hits_execution_seconds":hits_elapsed,
          "source_GLCC_pixels_used_original_ncount":original_parent_count,
          "source_GLCC_pixels_used_original_hits_ncount":hits_parent_count,
          "point_count_semantics":"CTGPROC ncount = GLCC source pixels; D1 included = MESHGLAZ subpoints; intentionally NOT compared",
          "fractions_numeric_gate":fractions["numeric_gate"],
          "fraction_values_compared":fractions["compared_values"],
          "fraction_max_absolute_difference":fractions["max_absolute_fraction_difference"],
          "fraction_exceedances":fractions["exceedances"],
          **ints,
          "GLC_mapping":"P2_MAPPING_REVIEW_REQUIRED",
          "P3":"NOT_RUN",
          "overall":"PASS_ORIGINAL_GLAZAS_SAME_SOURCE_INTEGER_AND_FRACTION" if
             (fractions["numeric_gate"]=="PASS" and ints["integer_gate"]=="PASS")
             else "FAIL_ORIGINAL_GLAZAS_INTEGER_OR_FRACTION",
        }
        # Diagnostic pass is strictly separate from the two original science oracles.
        # Run on mismatch only; never modify the accepted original LFINAL=T/F controls
        # or grant PASS because a coordinate diagnostic succeeds.
        if report["overall"]!="PASS_ORIGINAL_GLAZAS_SAME_SOURCE_INTEGER_AND_FRACTION":
            if a.native_qa_csv is None:
                report["coordinate_diagnostic"]="NOT_CONFIGURED";
            else:
                try:
                    qa_work=a.out_dir/"original_debug_qa"
                    qa_work.mkdir()
                    stage_img(a.source_img,qa_work)
                    debug_control=_edit_card(hits_control,"LQACELL","T")
                    execute_original_existing(a.original_ctgproc,qa_work,debug_control,a.timeout_sec)
                    require(read_hits(qa_work/"lu.dat")==original_hits,
                            "DEBUG_QA_CHANGED_ORIGINAL_HITS")
                    require(parse_original_used(qa_work/"ctgproc.lst")==hits_parent_count,
                            "DEBUG_QA_CHANGED_SOURCE_PIXEL_COUNTS")
                    report["coordinate_diagnostic"]=diagnose_coordinates(
                        qa_work/"qamesh.dat",a.native_qa_csv)
                    report["coordinate_diagnostic"]["original_debug_qa_control_sha256"]=file_sha(qa_work/"ctgproc.inp")
                except Exception as ex:
                    report["coordinate_diagnostic"]={"status":"DIAGNOSTIC_FAILED_OR_MISSING",
                                                      "error":str(ex)}
        else:
            report["coordinate_diagnostic"]="NOT_NEEDED_ALL_INTEGER_FIELDS_EQUAL"
        (a.out_dir/"result.json").write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n")
        print(json.dumps(report,indent=2,ensure_ascii=False))
        require(report["overall"]=="PASS_ORIGINAL_GLAZAS_SAME_SOURCE_INTEGER_AND_FRACTION",
                "GLAZAS_TRUE_INTEGER_HITS_SCIENCE_FAIL_SEE_ARTIFACT")
        return 0
    except BaseException as e:
        (a.out_dir/"FAILED.txt").write_text(str(e)+"\n")
        raise

def execute_original_existing(exe: Path, work: Path, control: str, seconds: int):
    (work/"ctgproc.inp").write_text(control,encoding="utf-8")
    start=time.monotonic()
    p=subprocess.run([str(exe.resolve()),"ctgproc.inp"],
                     cwd=work,capture_output=True,text=True,errors="replace",
                     timeout=seconds,check=False)
    (work/"stdout.log").write_text(p.stdout,encoding="utf-8")
    (work/"stderr.log").write_text(p.stderr,encoding="utf-8")
    require(p.returncode==0,"ORIGINAL_CTGPROC_EXECUTION_FAILED")
    require((work/"lu.dat").is_file() and (work/"ctgproc.lst").is_file(),
            "ORIGINAL_CTGPROC_OUTPUT_MISSING")
    return round(time.monotonic()-start,3)

if __name__=="__main__":
    raise SystemExit(main())
