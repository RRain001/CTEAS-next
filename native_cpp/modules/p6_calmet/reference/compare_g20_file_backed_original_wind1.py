#!/usr/bin/env python3
"""G20: independent literal-vendor CALMET WIND1 from FILE-BACKED C++ columns.

This is a *selected 3-D WIND1 kernel*, not independent provenance of upstream
SIMILT, VERTAV, PREPDI, FRADJ or complete 45-field native CALMET outputs.
The original-format GEO/SURF/UP case in CI contains synthetic observations.
All source WIND1 operations come from unchanged vendor calmet.for statements,
not a reimplemented numerical equation or an original .DAT output oracle.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
import tempfile
from pathlib import Path

from compare_g9_original_wind1_multisite import (
    VENDOR, FORTRAN_HEAD, FORTRAN_TAIL, rows,
)

DRIVER_READS = """      io6=6
      nbar=0
      kbar=0
      editl=999998.
      open(unit=10,file='source_columns.dat',status='old')
      read(10,*) nxr,nyr,nzr,nsr,nur,icalm,dgrid
      if(nxr.ne.nx.or.nyr.ne.ny.or.nzr.ne.nz.or.
     &   nsr.ne.nssta.or.nur.ne.nusta) stop 91
      do l=1,nssta
        read(10,*) xssta(l),yssta(l),ws10(l)
      enddo
      do l=1,nusta
        read(10,*) xusta(l),yusta(l)
      enddo
      do k=1,nz
        read(10,*) bias(k)
      enddo
      do k=1,nz
        do l=1,nstat
          read(10,*) us(k,l),vs(k,l),ipresent
          if(ipresent.ne.1) stop 92
          ustmp(k,l)=us(k,l)
          vstmp(k,l)=vs(k,l)
        enddo
      enddo
      close(10)
"""
# Header duplicates vendor's WIND1 local variable declarations only.
# Preserve every numerical kernel statement from calmet.for verbatim.
DECLARATIONS = FORTRAN_HEAD.split("      dgrid=10000.\n", 1)[0]
if "real bias(nz),ug(nx,ny,nz)" not in DECLARATIONS:
    raise RuntimeError("original WIND1 reference driver declarations drifted")
DECLARATIONS = (
    DECLARATIONS.replace("nx=3,ny=3,nz=3", "nx=12,ny=12,nz=9")
    + "      integer nxr,nyr,nzr,nsr,nur,ipresent\n"
)


def validate_profile_file(path: Path) -> dict:
    if not path.is_file():
        raise ValueError("G20 selected WIND1 column file absent")
    lines = [line.split() for line in path.read_text().splitlines()]
    if not lines or len(lines[0]) != 7:
        raise ValueError("G20 malformed WIND1 source header")
    nx, ny, nz, ns, nu, icalm = map(int, lines[0][:6])
    dgrid = float(lines[0][6])
    if (nx, ny, nz, ns, nu, icalm) != (12, 12, 9, 2, 2, 0):
        raise ValueError("G20 vendor extractor pinned source scope mismatch")
    if not math.isfinite(dgrid) or dgrid != 10000.0:
        raise ValueError("G20 source DGRID not 10km")
    expected = 1 + ns + nu + nz + nz * (ns + nu)
    if len(lines) != expected:
        raise ValueError(f"G20 2SS+2US original stage profile count {len(lines)} != {expected}")
    for row in lines[1 : 1 + ns]:
        if len(row) != 3 or not all(math.isfinite(float(x)) for x in row):
            raise ValueError("G20 SURF wind/site array invalid")
    for row in lines[1 + ns : 1 + ns + nu]:
        if len(row) != 2 or not all(math.isfinite(float(x)) for x in row):
            raise ValueError("G20 UP site coordinate array invalid")
    for row in lines[1 + ns + nu : 1 + ns + nu + nz]:
        if len(row) != 1 or not math.isfinite(float(row[0])):
            raise ValueError("G20 original source effective BIAS invalid")
    for row in lines[1 + ns + nu + nz :]:
        if len(row) != 3 or row[2] != "1" or any(
            not math.isfinite(float(x)) or abs(float(x)) >= 998.99
            for x in row[:2]
        ):
            raise ValueError("G20 missing/nonfinite selected WIND1 observation")
    return {"cells": nx * ny * nz, "stations": ns + nu, "levels": nz}


def source_extract() -> tuple[str, str]:
    raw = VENDOR.read_bytes()
    lines = raw.decode("latin-1").splitlines(keepends=True)
    source = "".join(lines[36204 - 1 : 36397])
    if ("compute bulk weights" not in source.lower() or
            "ug(i,j,k)=unext" not in source or "vvw(k,l)" not in source):
        raise ValueError("vendored literal original CALMET WIND1 moved; fail closed")
    return DECLARATIONS + DRIVER_READS + source + FORTRAN_TAIL, hashlib.sha256(raw).hexdigest()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source-columns", type=Path, required=True)
    ap.add_argument("--candidate", type=Path, required=True)
    ap.add_argument("--mode", choices=["Debug", "Release"], required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    desc = validate_profile_file(args.source_columns)
    original_source, sha = source_extract()
    with tempfile.TemporaryDirectory(prefix="p6g-g20-vendor-") as tmp:
        root = Path(tmp)
        (root / "original_wind1.f").write_text(original_source, encoding="latin-1")
        (root / "source_columns.dat").write_bytes(args.source_columns.read_bytes())
        exe = root / "original"
        opt = "-O0" if args.mode == "Debug" else "-O2"
        subprocess.run(
            ["gfortran", opt, "-ffixed-line-length-none", "-std=legacy",
             str(root / "original_wind1.f"), "-o", str(exe)], check=True
        )
        original = subprocess.run(
            [str(exe)], cwd=root, capture_output=True, text=True, check=True
        )
    expected = desc["cells"]
    vendor = rows(original.stdout, expected)
    candidate: dict[tuple[int, int, int], tuple[float, float]] = {}
    all_lines = args.candidate.read_text().splitlines()
    if len(all_lines) != expected + 1 or all_lines[0].strip() != (
        "hour_end_utc_seconds,k_1based,j_1based,i_1based,"
        "u_mps_real4,v_mps_real4"
    ):
        raise ValueError("G20 candidate first-hour 3D original-grid U/V CSV malformed")
    hour = None
    for record in all_lines[1:]:
        items = record.split(",")
        if len(items) != 6:
            raise ValueError("G20 candidate line has wrong physical field count")
        t, k, j, i = [int(item) for item in items[:4]]
        if hour is None:
            hour = t
        elif t != hour:
            raise ValueError("G20 candidate mixed multiple model hours")
        key = (i, j, k)
        if key in candidate:
            raise ValueError("G20 duplicate native WIND1 grid index")
        uv = tuple(float(v) for v in items[4:])
        if not all(math.isfinite(x) for x in uv):
            raise ValueError("G20 non-finite native WIND1 candidate")
        candidate[key] = uv
    if vendor.keys() != candidate.keys():
        raise ValueError("G20 candidate and literal original Fortran grid indices differ")
    failures = []
    maximum = 0.0
    for cell in sorted(vendor):
        for part, original_component, native_component in zip(
            ("U", "V"), vendor[cell], candidate[cell]
        ):
            error = abs(original_component - native_component)
            maximum = max(maximum, error)
            if error > 2e-6:  # PREEXISTING strict G9 vendor kernel tolerance
                failures.append((cell, part, original_component, native_component, error))
    evidence = {
        "scope": "first-hour 2SS+2US 12x12x9 source-file WIND1 kernel only",
        "source_data": "synthetic original-format GEO SURF UP met.inp",
        "original_source_sha256": sha,
        "mode": args.mode,
        "cells": expected,
        "compared_uv_values": 2 * expected,
        "max_abs_uv_difference_mps": maximum,
        "tolerance_mps": 2e-6,
        "failures": failures[:10],
        "independent_original_similt_prepdi_parity": False,
        "whole_hour_calmet_45_field_accepted": False,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n")
    if failures:
        raise AssertionError(
            f"G20 literal vendor WIND1 source from real-file station columns:"
            f" {len(failures)} FAIL; max={maximum:.9g}; first={failures[:3]}"
        )
    print("PASS_P6G_G20_REAL_FILE_COLUMNS_LITERAL_VENDOR_WIND1 "
          f"mode={args.mode} compared={2*expected} max_abs_uv={maximum:.9g}"
          f" vendor_sha256={sha} full_calmet_parity=NOT_ACCEPTED")


if __name__ == "__main__":
    main()
