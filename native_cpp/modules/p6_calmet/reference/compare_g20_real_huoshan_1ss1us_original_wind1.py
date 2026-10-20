#!/usr/bin/env python3
"""P6-B1 independent literal original CALMET WIND1 kernel on real Huoshan columns.

The 1SS+1US 100x100x9 station-column file MUST have been made by actual
NOAA-backed S3 G19+G20 C++ on the exact case. The unmodified original
calmet.for WIND1 statements run separately with those same columns.
This is WIND1 STAGE KERNEL parity, not independent SIMILT/PREPDI, full
CALMET 45-field/hour, FRADJ/SLOPE/INTER2/COMP/P6F or P7 acceptance.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys
import tempfile

REFERENCE = Path(__file__).resolve().parent
sys.path.insert(0, str(REFERENCE))
from compare_g20_file_backed_original_wind1 import DRIVER_READS
from compare_g9_original_wind1_multisite import FORTRAN_HEAD, FORTRAN_TAIL, rows

NX, NY, NZ, NS, NU = 100, 100, 9, 1, 1
ORIGINAL_LINES = (36204, 36397)
ORIGINAL_TOLERANCE_MPS = 2e-6  # Existing G9/G20 independent Fortran tolerance


def source_extract(original_fortran: Path) -> tuple[str, str]:
    if original_fortran.is_symlink() or not original_fortran.is_file():
        raise ValueError("P6-B1 original CALMET source absent or symlinked")
    raw = original_fortran.read_bytes()
    lines = raw.decode("latin-1").splitlines(keepends=True)
    if len(lines) < ORIGINAL_LINES[1]:
        raise ValueError("P6-B1 original CALMET source shorter than pinned WIND1 block")
    vendor = "".join(lines[ORIGINAL_LINES[0] - 1:ORIGINAL_LINES[1]])
    if ("compute bulk weights" not in vendor.lower()
            or "ug(i,j,k)=unext" not in vendor
            or "vvw(k,l)" not in vendor):
        raise ValueError("P6-B1 original WIND1 source statement location changed")
    declaration = FORTRAN_HEAD.split("      dgrid=10000.\n", 1)[0]
    if ("nx=3,ny=3,nz=3,nssta=2,nowsta=0,nusta=2,nstat=4" not in declaration
            or "real bias(nz),ug(nx,ny,nz)" not in declaration):
        raise ValueError("P6-B1 independent vendor driver declaration drift")
    declaration = declaration.replace(
        "nx=3,ny=3,nz=3,nssta=2,nowsta=0,nusta=2,nstat=4",
        f"nx={NX},ny={NY},nz={NZ},nssta={NS},nowsta=0,nusta={NU},nstat={NS+NU}",
    )
    declaration += "      integer nxr,nyr,nzr,nsr,nur,ipresent\n"
    return declaration + DRIVER_READS + vendor + FORTRAN_TAIL, hashlib.sha256(raw).hexdigest()


def validate_columns(path: Path) -> dict:
    if path.is_symlink() or not path.is_file():
        raise ValueError("real Huoshan WIND1 station columns unavailable")
    lines = [line.split() for line in path.read_text().splitlines()]
    if not lines or len(lines[0]) != 7:
        raise ValueError("malformed original station-column header")
    dims = tuple(int(x) for x in lines[0][:6])
    if dims[:5] != (NX, NY, NZ, NS, NU):
        raise ValueError("original weather source cardinality/grid mismatch")
    icalm=dims[5]
    if icalm not in (0, 1):
        raise ValueError("original CALMET ICALM wind switch out of selected scope")
    dx=float(lines[0][6])
    if not math.isfinite(dx) or abs(dx-100.0)>1e-5:
        raise ValueError("original selected WIND1 data spacing not the real 100 m model grid")
    size=1+NS+NU+NZ+NZ*(NS+NU)
    if len(lines) != size:
        raise ValueError(f"real WIND1 station rows {len(lines)} != expected {size}")
    for line in lines[1:1+NS]:
        if len(line)!=3 or not all(math.isfinite(float(v)) for v in line):
            raise ValueError("real NOAA SURF station/profile row invalid")
    for line in lines[1+NS:1+NS+NU]:
        if len(line)!=2 or not all(math.isfinite(float(v)) for v in line):
            raise ValueError("real NOAA UP station location invalid")
    for line in lines[1+NS+NU:1+NS+NU+NZ]:
        if len(line)!=1 or not math.isfinite(float(line[0])):
            raise ValueError("original BIAS not finite")
    for line in lines[1+NS+NU+NZ:]:
        if (len(line)!=3 or line[2]!="1"
                or any(not math.isfinite(float(v)) or abs(float(v))>=998.99 for v in line[:2])):
            raise ValueError("WIND1 original source 1SS/1US level wind missing/nonfinite")
    return {"grid_rows": NX*NY*NZ, "source_stations": NS+NU,
            "vertical_levels":NZ,"original_icalm":icalm,
            "station_profile_sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def compare(args: argparse.Namespace) -> dict:
    input_desc=validate_columns(args.source_columns)
    original_code,vendor_sha=source_extract(args.vendor_calmet_for)
    if args.candidate.is_symlink() or not args.candidate.is_file():
        raise ValueError("G20 original real-source candidate output missing")
    candidate_sha=hashlib.sha256(args.candidate.read_bytes()).hexdigest()
    with tempfile.TemporaryDirectory(prefix="p6b1-original-vendor-huoshan-") as scratch:
        root=Path(scratch)
        (root/"original_wind1.f").write_text(original_code,encoding="latin-1")
        (root/"source_columns.dat").write_bytes(args.source_columns.read_bytes())
        command=["gfortran", "-O0", "-ffixed-line-length-none", "-std=legacy",
                 str(root/"original_wind1.f"), "-o", str(root/"original")]
        subprocess.run(command,check=True,capture_output=True,text=True)
        result=subprocess.run([str(root/"original")],cwd=root,
                              check=True,capture_output=True,text=True)
    reference=rows(result.stdout,input_desc["grid_rows"])
    actual={}
    records=args.candidate.read_text().splitlines()
    if (len(records)!=input_desc["grid_rows"]+1
            or records[0]!="hour_end_utc_seconds,k_1based,j_1based,i_1based,u_mps_real4,v_mps_real4"):
        raise ValueError("P6-B1 actual 90k U/V CSV malformed")
    hour=None
    for record in records[1:]:
        row=record.split(",")
        if len(row)!=6:
            raise ValueError("P6-B1 native source grid U/V malformed")
        t,k,j,i=[int(x) for x in row[:4]]
        if hour is None:
            hour=t
        elif hour!=t:
            raise ValueError("P6-B1 mixed original UTC hours")
        key=(i,j,k)
        if key in actual:
            raise ValueError("P6-B1 duplicate native WIND1 grid cell")
        uv=tuple(float(x) for x in row[4:])
        if not all(math.isfinite(v) for v in uv):
            raise ValueError("P6-B1 candidate includes nonfinite values")
        actual[key]=uv
    if actual.keys()!=reference.keys():
        raise ValueError("original Fortran and C++ WIND1 grid index domain differs")
    worst=0.0
    failures=[]
    badcount=0
    for key in reference:
        for part,native,original in zip(("U","V"),actual[key],reference[key]):
            error=abs(native-original)
            worst=max(worst,error)
            if error>ORIGINAL_TOLERANCE_MPS:
                badcount+=1
                if len(failures)<12:
                    failures.append({"index":key,"component":part,
                                     "original":original,"cpp":native,
                                     "error":error})
    output={
      "status":"P6B1_REAL_HUOSHAN_ORIGINAL_WIND1_KERNEL_PASS_SCOPED" if badcount==0
         else "P6B1_REAL_HUOSHAN_ORIGINAL_WIND1_KERNEL_NOT_EQUIVALENT",
      "source":"pinned unmodified CALMET_v6.5.0_L150223 original WIND1 statements",
      "original_calmet_for_sha256":vendor_sha,
      "original_statement_lines":[*ORIGINAL_LINES],
      "actual_station_profile_sha256":input_desc["station_profile_sha256"],
      "native_wind1_grid_sha256":candidate_sha,
      "mode":"gfortran -O0",
      "grid":{"nx":NX,"ny":NY,"nz":NZ,"cells":NX*NY*NZ,"SS":NS,"US":NU},
      "actual_original_icalm":input_desc["original_icalm"],
      "compared_uv_fields":NX*NY*NZ*2,
      "original_wind1_tolerance_mps":ORIGINAL_TOLERANCE_MPS,
      "max_abs_uv_difference_mps":worst,
      "differences_exceeding_tolerance":badcount,
      "first_mismatches":failures,
      "independent_original_PREPDI_SIMILT":False,
      "original_full_CALMET_45_fields":False,
      "P6_NEW_SITE_SCIENCE":"NOT_ACCEPTED",
      "docker":"DEFERRED",
    }
    return output


def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vendor-calmet-for",type=Path,required=True)
    parser.add_argument("--source-columns",type=Path,required=True)
    parser.add_argument("--candidate",type=Path,required=True)
    parser.add_argument("--out",type=Path,required=True)
    a=parser.parse_args()
    try:
        result=compare(a)
        if a.out.exists() or a.out.is_symlink():
            raise ValueError("P6-B1 original numerical result must be a fresh artifact")
        a.out.parent.mkdir(parents=True,exist_ok=True)
        a.out.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
        print(json.dumps({"status":result["status"],"compared":result["compared_uv_fields"],
                          "failed":result["differences_exceeding_tolerance"],
                          "max_abs":result["max_abs_uv_difference_mps"],
                          "original_fortran_SHA":result["original_calmet_for_sha256"]}))
        return 0 if result["differences_exceeding_tolerance"]==0 else 2
    except (OSError,ValueError,subprocess.CalledProcessError) as exc:
        print(json.dumps({"status":"P6B1_VENDOR_INDEPENDENT_COMPARE_BLOCKED",
                          "error":str(exc)[:1000]}),file=sys.stderr)
        return 2


if __name__=="__main__":
    raise SystemExit(main())
