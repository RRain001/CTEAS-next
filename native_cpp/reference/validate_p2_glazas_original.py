#!/usr/bin/env python3
"""#53 scientific gate: ORIGINAL CTGPROC GLAZAS vs authentic native GLCC D1/D3.

Legacy FRACTION-ONLY diagnostic retained for parser reuse and traceability.
For full authentic original science use validate_p2_glazas_hits.py, which
requires original Fortran LFINAL=T and LFINAL=F independent integer HITS.
Authentic original binary is pinned by source commit and binary SHA256. Never substitutes GEN, captured historical LU, or a
synthetic fixture as the original GLAZAS oracle. Invoked ONLY manually.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import time

SRC_SHA = "4f2a1977d141e2040da4d36ec6a4826c5c960c84686eaf10f226f388cb3ab90a"
SRC_SIZE = 156_000_000
CTEAS_ORIGINAL_COMMIT = "dfad99a78ed84d655e21411c9d25eb0d2583bf13"
CTGPROC_ORIGINAL_SOURCE_SHA256 = "719abbd2327269bb0377208b3a7a0c74000b878efc756686023bbb2ef932f281"
CATS = (11,12,13,14,15,16,17,21,22,23,24,31,32,33,41,42,43,
        51,52,53,54,55,61,62,71,72,73,74,75,76,77,81,82,83,84,85,91,92)
FROZEN = dict(nx=50, ny=50, xrefkm="510.885", yrefkm="3531.269",
              dgridkm="0.100", iutmzn=50, hemisphere="N", mesh=20)
FLOAT_TOL = 0.0005

class GateError(RuntimeError):
    pass

def require(condition: bool, message: str):
    if not condition:
        raise GateError(message)

def file_sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()

def safe_original_file(path: Path, *, expected: str, exact_size: int | None = None):
    require(not path.is_symlink() and path.is_file(), "SOURCE_MISSING_OR_SYMLINK")
    require(re.fullmatch(r"[0-9a-f]{64}", expected) is not None, "MALFORMED_EXPECTED_SHA")
    if exact_size is not None:
        require(path.stat().st_size == exact_size, "WRONG_SOURCE_SIZE_OR_GIT_LFS_POINTER")
    require(file_sha(path) == expected, "SOURCE_SHA256_MISMATCH")

def _edit_card(text: str, key: str, value: str) -> str:
    # Only active ! KEY = value ! cards. Preserve the source's template comments.
    pattern = re.compile(r"(?m)(!\s*" + re.escape(key) + r"\s*=\s*)([^!\r\n]*)(!)")
    matches = list(pattern.finditer(text))
    require(len(matches) == 1, "CONTROL_MISSING_OR_DUPLICATE_" + key)
    match = matches[0]
    return text[:match.start(2)] + value + " " + text[match.end(2):]

def make_glazas_control(source: str) -> str:
    """Create genuine GLAZAS, never GEN, from the selected frozen CTGPROC deck."""
    require(source.count("\x00") == 0, "CONTROL_BINARY")
    # Reject secondary GEN/GLAZAS dataset declarations; exactly one active line.
    dataset = re.compile(r"(?m)^[ \t]*1[ \t]+!(?:GEN|GLAZAS)\s*=[^\r\n]*!END![ \t]*$")
    found = list(dataset.finditer(source))
    require(len(found) == 1 and "!GEN" in found[0].group(0), "CONTROL_DATASET_NOT_EXACT_ONE_GEN")
    original = found[0]
    deck = (source[:original.start()] +
            "1 !GLAZAS = glcc.img !    !END!" +
            source[original.end():])
    for key, value in (
        ("NDBF", "1"), ("MESHGLAZ", "20"), ("LFINAL", "T"),
        ("LPREV", "F"), ("LCOAST", "F"), ("LQACELL", "F"),
        ("LSNOW", "F"), ("DUSGSLA", "ESR-S"), ("LCFILES", "T"),
        ("IUTMZN", "50"), ("UTMHEM", "N"), ("XREFKM", "510.885"),
        ("YREFKM", "3531.269"), ("DGRIDKM", "0.100"),
        ("NX", "50"), ("NY", "50"), ("LUDAT", "lu.dat"),
        ("RUNLST", "ctgproc.lst"),
    ):
        deck = _edit_card(deck, key, value)
    require(deck.count("!GLAZAS = glcc.img !") == 1,"GLAZAS_NOT_SELECTED")
    require(not re.search(r"(?m)^[ \t]*1[ \t]+!GEN\s*=", deck),
            "GEN_NOT_REMOVED")
    return deck

def parse_lu(path: Path):
    text = path.read_text(encoding="utf-8", errors="strict").splitlines()
    require(len(text) == 2511, "LU_DAT_NOT_2511_LINES")
    require(text[0].split()[:2] == ["LU.DAT","2.1"], "NOT_LU_DAT_VERSION_2_1")
    require(text[4].strip() == "FRACTION" and text[5].strip() == "UTM",
            "NOT_UTM_FRACTION")
    require(text[6].strip() == "50N" and text[7].startswith("WGS-84"),
            "LU_GRID_PROJECTION_MISMATCH")
    hdr = text[8].split()
    require(len(hdr) >= 7 and tuple(map(int,hdr[:2])) == (50,50),
            "LU_GRID_SIZE_MISMATCH")
    require(abs(float(hdr[2])-510.885) < 1e-6 and
            abs(float(hdr[3])-3531.269) < 1e-6 and
            abs(float(hdr[4])-0.1)<1e-6 and
            abs(float(hdr[5])-0.1)<1e-6 and int(hdr[6]) == 38,
            "LU_ORIGIN_OR_SPACING_MISMATCH")
    require(text[9].split() in (["KM"], ["KM","M"]), "LU_UNITS_MISMATCH")
    require(tuple(map(int,text[10].split())) == CATS,"LU_CATEGORY_ORDER_MISMATCH")
    rows=[]
    for n,line in enumerate(text[11:]):
        f=line.split()
        require(len(f)==41 and f[-1]==".","LU_INVALID_CELL_WIDTH_OR_TERMINATOR")
        require(int(f[0])==n%50+1 and int(f[1])==n//50+1,
                "LU_CELL_INDEX_ORDER")
        values=[float(v) for v in f[2:-1]]
        require(all(math.isfinite(v) and 0<=v<=1 for v in values),
                "LU_FRACTION_NONFINITE_OR_OUT_OF_RANGE")
        # Round-to-3 display may sum 0.99..1.01 for 38 classes.
        require(0.98 <= sum(values) <= 1.02,"LU_CELL_FRACTION_SUM_INVALID")
        rows.append(values)
    return rows

def parse_original_used(lst: Path) -> int:
    txt = lst.read_text(encoding="latin-1", errors="replace")
    matches = re.findall(r"Number of data points used to update grid:\s*(\d+)", txt, re.I)
    require(len(matches)==1,"ORIGINAL_CTGLST_POINT_COUNT_MISSING_OR_MULTIPLE")
    return int(matches[0])

def compare(original: Path,native: Path,lst: Path,native_manifest: Path) -> dict:
    o=parse_lu(original)
    n=parse_lu(native)
    manifest=json.loads(native_manifest.read_text(encoding="utf-8"))
    require(manifest.get("producer")=="cteas_p2_glcc_lu_dat",
            "NOT_D3_GLCC_PRODUCER")
    require(manifest.get("source_sha256")==SRC_SHA,"D3_SOURCE_NOT_OFFICIAL")
    require(manifest.get("lu_dat_sha256")==file_sha(native),
            "D3_LU_SHA_MISMATCH")
    require(manifest.get("rows")==2500 and manifest.get("classes")==38,
            "D3_BAD_SHAPE")
    used=parse_original_used(lst)
    native_used=manifest.get("total_samples")
    require(type(native_used)==int and native_used>0,"D3_MISSING_SAMPLE_COUNT")
    maximum=0.0;total=0.0;first=[];different=0
    for index,(x,y) in enumerate(zip(o,n)):
        for k,(a,b) in enumerate(zip(x,y)):
            delta=abs(a-b)
            total+=delta
            maximum=max(maximum,delta)
            if delta>FLOAT_TOL:
                different+=1
                if len(first)<20:
                    first.append({"i":index%50+1,"j":index//50+1,
                                  "usgs_category":CATS[k],
                                  "glazas":a,"native":b,"absolute_difference":delta})
    report={
        "gate":"P2_A_ORIGINAL_GLAZAS_156MB_SAME_SOURCE",
        "source_sha256":SRC_SHA,
        "original_input_kind":"GLAZAS_not_GEN",
        "meshglaz":20,
        "grid":"50x50_100m_UTM50N_510.885_3531.269",
        "compared_cells":2500,
        "compared_classes":38,
        "compared_values":2500*38,
        "tolerance_abs_display_fraction":FLOAT_TOL,
        "max_absolute_fraction_difference":maximum,
        "mean_absolute_fraction_difference":total/(2500*38),
        "exceedances":different,
        "first_20_exceedances":first,
        "original_glcc_source_pixels_used":used,
        "native_d1_d3_submesh_hits":native_used,
        "point_count_comparison":"NOT_COMPARABLE_DIFFERENT_UNITS",
        "numeric_gate":"PASS" if different==0 else "FAIL",
    }
    report["overall"]="PASS_FRACTION_ONLY_PENDING_INTEGER_HITS" if different==0 else "FAIL_ORIGINAL_GLAZAS_FRACTIONS"
    return report

def run(argv=None) -> int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source-img", type=Path, required=True)
    p.add_argument("--original-ctgproc", type=Path, required=True)
    p.add_argument("--original-bin-sha256", required=True)
    p.add_argument("--original-source-file", type=Path, required=True)
    p.add_argument("--control-template", type=Path, required=True)
    p.add_argument("--grid-cmn", type=Path, required=True)
    p.add_argument("--native-lu", type=Path, required=True)
    p.add_argument("--native-manifest", type=Path, required=True)
    p.add_argument("--out-dir", type=Path, required=True)
    p.add_argument("--timeout-sec", type=int, default=300)
    a=p.parse_args(argv)
    require(10<=a.timeout_sec<=600,"TIMEOUT_OUT_OF_BOUNDS")
    for path in (a.control_template,a.grid_cmn,a.native_lu,a.native_manifest):
        require(path.is_file() and not path.is_symlink(),"INPUT_MISSING_OR_SYMLINK")
    safe_original_file(a.source_img,expected=SRC_SHA,exact_size=SRC_SIZE)
    require(a.original_ctgproc.is_file() and os.access(a.original_ctgproc,os.X_OK),
            "ORIGINAL_BINARY_NOT_FOUND_OR_NOT_EXECUTABLE")
    safe_original_file(a.original_ctgproc,expected=a.original_bin_sha256)
    safe_original_file(a.original_source_file,expected=CTGPROC_ORIGINAL_SOURCE_SHA256)
    require(not a.out_dir.exists() and not a.out_dir.is_symlink(),
            "OUTPUT_DIRECTORY_COLLISION")
    control = make_glazas_control(a.control_template.read_text(encoding="utf-8"))
    # Re-check native field/manifests BEFORE executing original program.
    parse_lu(a.native_lu)
    d3=json.loads(a.native_manifest.read_text(encoding="utf-8"))
    require(d3.get("source_sha256")==SRC_SHA and
            d3.get("lu_dat_sha256")==file_sha(a.native_lu) and
            d3.get("original_GLAZAS_parity")=="NOT_RUN",
            "NATIVE_MANIFEST_UNTRUSTED")
    a.out_dir.mkdir(parents=True,exist_ok=False)
    result = a.out_dir/"result.json"
    work=a.out_dir/"original"
    work.mkdir()
    try:
        (a.out_dir/"grid.cmn").write_bytes(a.grid_cmn.read_bytes())
        (work/"ctgproc.inp").write_text(control,encoding="utf-8")
        # Short path for vintage Fortran: point into verified original LFS bytes.
        # Link within output workdir is controlled and source is SHA-pinned.
        try:
            os.link(a.source_img,work/"glcc.img")
        except OSError:
            shutil.copyfile(a.source_img,work/"glcc.img")
        safe_original_file(work/"glcc.img",expected=SRC_SHA,exact_size=SRC_SIZE)
        start=time.monotonic()
        invocation=subprocess.run([str(a.original_ctgproc.resolve()),"ctgproc.inp"],
            cwd=work,capture_output=True,text=True,errors="replace",
            timeout=a.timeout_sec,check=False)
        elapsed=time.monotonic()-start
        (work/"original_stdout.log").write_text(invocation.stdout)
        (work/"original_stderr.log").write_text(invocation.stderr)
        require(invocation.returncode==0, "ORIGINAL_CT GPROC_EXIT_NONZERO".replace(" ",""))
        require((work/"lu.dat").is_file() and (work/"ctgproc.lst").is_file(),
                "ORIGINAL_OUTPUT_MISSING")
        safe_original_file(a.source_img,expected=SRC_SHA,exact_size=SRC_SIZE)
        report=compare(work/"lu.dat",a.native_lu,work/"ctgproc.lst",a.native_manifest)
        report.update({
            "original_bin_sha256":a.original_bin_sha256,
            "original_source_git_commit":CTEAS_ORIGINAL_COMMIT,
            "original_ctgproc_for_sha256":CTGPROC_ORIGINAL_SOURCE_SHA256,
            "control_sha256":file_sha(work/"ctgproc.inp"),
            "grid_sha256":file_sha(a.out_dir/"grid.cmn"),
            "original_lu_sha256":file_sha(work/"lu.dat"),
            "original_log_sha256":file_sha(work/"ctgproc.lst"),
            "native_lu_sha256":file_sha(a.native_lu),
            "original_binary_returncode":invocation.returncode,
            "original_execution_seconds":round(elapsed,3),
            "vendor_source_not_redistributed":True,
            "p3_geo_dat":"NOT_RUN",
            "glc_fcs30d_crosswalk":"P2_MAPPING_REVIEW_REQUIRED",
        })
        result.write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n")
        print(json.dumps(report,indent=2,ensure_ascii=False))
        require(False,"FRACTION_ONLY_IS_NOT_SCIENCE_PASS_USE_validate_p2_glazas_hits")
        return 0
    except (Exception,BaseException) as e:
        (a.out_dir/"FAILED.txt").write_text(str(e)+"\n")
        raise

if __name__=="__main__":
    raise SystemExit(run())
