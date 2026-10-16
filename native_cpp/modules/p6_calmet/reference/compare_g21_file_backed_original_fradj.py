#!/usr/bin/env python3
"""Literal vendored CALMET TERSET+FRADJ on actual G21 source-file stage data.

Scientific scope: one selected 2SS+2US original-format (synthetic weather)
hour after source-file G20 WIND1, PREPDI/CGAMMA and first IAVET SURFVAR.
Uses original Fortran routines; not complete DIAGNO/COMP/P6F or verified
original Fortran processing from raw meteorological observations.
"""
from __future__ import annotations

import argparse
import json
import math
import subprocess
import tempfile
from pathlib import Path

from compare_g11_original_terrain_10km import (
    VENDOR, original_chunks, rows_from,
)

DRIVER = """      program g21_file_source_fradj
      include 'params.met'
      include 'grid.met'
      include 'metgrd.met'
      include 'geo.met'
      include 'd6.met'
      real topo(mxnx,mxny),highest(mxnx,mxny)
      real gam(mxnx,mxny),sfct(mxnx,mxny)
      real u(mxnx,mxny,mxnz),v(mxnx,mxny,mxnz)
      real terrad,critfn,tinf
      integer nr,nc,nlayer,mode
      open(unit=10,file='g21_original_stage.dat',status='old')
      read(10,*) nr,nc,nlayer,dx,dy,terrad,critfn,tinf,mode
      if(nr.ne.12.or.nc.ne.12.or.nlayer.ne.9) stop 71
      if(dx.ne.10000..or.dy.ne.10000..or.mode.ne.-1) stop 72
      nx=nr
      ny=nc
      nz=nlayer
      iwr=0
      iwat1=50
      iwat2=55
      isurft=mode
      read(10,*) (zface(k),k=1,nz+1)
      do k=1,nz
        dz(k)=zface(k+1)-zface(k)
      enddo
      do j=1,ny
        do i=1,nx
          read(10,*) topo(i,j),gam(i,j),sfct(i,j)
          ilandu(i,j)=20
        enddo
      enddo
      do k=1,nz
        do j=1,ny
          do i=1,nx
            read(10,*) u(i,j,k),v(i,j,k)
          enddo
        enddo
      enddo
      close(10)
      call terset(topo,highest,terrad)
      call fradj(u,v,topo,gam,isurft,tinf,sfct,critfn,
     1           zface,highest)
      do k=1,nz
        do j=1,ny
          do i=1,nx
            write(*,'(A,3(1X,I3),2(1X,ES17.9))')
     1           'GRID',i,j,k,u(i,j,k),v(i,j,k)
          enddo
        enddo
      enddo
      end
      subroutine xmit(n,val,a)
      real val,a(*)
      do i=1,iabs(n)
        a(i)=val
      enddo
      end
      subroutine wndlpt(a)
      real a(*)
      return
      end
"""


def read_stage(path: Path) -> dict:
    rows = path.read_text().splitlines()
    if len(rows) != 2 + 144 + 1296:
        raise ValueError("G21 stage input has wrong 12x12x9 source height")
    meta = rows[0].split()
    if len(meta) != 9:
        raise ValueError("G21 source FRADJ scalar control count invalid")
    nx, ny, nz = map(int, meta[:3])
    dx, dy, terrad, critfn, t0 = map(float, meta[3:8])
    isurft = int(meta[8])
    if (nx, ny, nz) != (12, 12, 9) or isurft != -1 or (
        dx != 10000.0 or dy != 10000.0
    ) or not all(map(math.isfinite, [terrad, critfn, t0])) or (
        terrad < 0 or critfn < 0 or t0 < 180 or t0 > 350
    ):
        raise ValueError("G21 source FRADJ outside selected true READCF branch")
    zface = [float(z) for z in rows[1].split()]
    if len(zface) != 10 or not all(map(math.isfinite, zface)) or any(
        b <= a for a, b in zip(zface, zface[1:])
    ):
        raise ValueError("G21 original ZFACE missing/invalid")
    for row in rows[2 : 2 + 144]:
        vals = [float(x) for x in row.split()]
        if len(vals) != 3 or not all(map(math.isfinite, vals)):
            raise ValueError("G21 GEO/GAMMA/TEMP2D invalid")
        if vals[2] < 180 or vals[2] > 350:
            raise ValueError("G21 actual SURFVAR TEMP2D outside source bounds")
    wind1 = []
    for row in rows[2 + 144 :]:
        vals = [float(x) for x in row.split()]
        if len(vals) != 2 or not all(map(math.isfinite, vals)):
            raise ValueError("G21 source WIND1 U/V invalid")
        wind1.append(tuple(vals))
    return {"cells": 1296, "source_terrad": terrad,
            "source_critfn": critfn, "wind1_uv": wind1}


def candidate_rows(path: Path) -> dict[tuple[int, int, int], tuple[float, float]]:
    lines = path.read_text().splitlines()
    expected_header = ("hour_end_utc_seconds,k_1based,j_1based,i_1based,"
                       "u_mps_real4,v_mps_real4")
    if len(lines) != 1297 or lines[0] != expected_header:
        raise ValueError("G21 native FRADJ output/header length invalid")
    results = {}
    clock = None
    for line in lines[1:]:
        row = line.split(",")
        if len(row) != 6:
            raise ValueError("G21 original native U/V columns invalid")
        t, k, j, i = [int(q) for q in row[:4]]
        if clock is None:
            clock = t
        elif t != clock:
            raise ValueError("G21 merged multiple hourly steps")
        values = tuple(float(q) for q in row[4:])
        key = (i, j, k)
        if key in results or not all(map(math.isfinite, values)):
            raise ValueError("G21 duplicate or nonfinite U/V")
        results[key] = values
    return results


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-stage", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--mode", choices=("Debug", "Release"), required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--require-nontrivial", action="store_true")
    args = parser.parse_args()
    stage = read_stage(args.source_stage)
    with tempfile.TemporaryDirectory(prefix="g21-literal-source-") as temp:
        root = Path(temp)
        chunks, sha256 = original_chunks(root)
        driver = root / "file_source_fradj.for"
        driver.write_text(DRIVER)
        (root / "g21_original_stage.dat").write_bytes(
            args.source_stage.read_bytes()
        )
        opt = "-O0" if args.mode == "Debug" else "-O2"
        vendor = root / "fradj_original"
        subprocess.run(
            ["gfortran", opt, "-std=legacy", "-fno-automatic",
             "-ffixed-line-length-none", "-I" + str(VENDOR),
             *[str(p) for p in chunks[:2]], str(driver), "-o", str(vendor)],
            check=True,
        )
        result = subprocess.run(
            [str(vendor)], cwd=root, check=True, text=True, capture_output=True
        )
        reference = rows_from(result.stdout)
    native = candidate_rows(args.candidate)
    if reference.keys() != native.keys():
        raise ValueError("G21 original FRADJ and native source grid indexing differ")
    failures = []
    maximum = 0.0
    modified_components = 0
    # Check a real corrected branch, not merely Fortran/C++ identity when
    # the selected source terrain has insufficient obstacle height.
    for (i,j,k), uv in native.items():
        p=(k-1)*144+(j-1)*12+(i-1)
        for corrected, first in zip(uv,stage["wind1_uv"][p]):
            if abs(corrected-first)>1e-5:
                modified_components+=1
    if args.require_nontrivial and modified_components==0:
        raise AssertionError(
            "G21 selected source produced identity FRADJ U/V; "
            "steep terrain stress case must exercise actual correction")
    # The ORIGINAL G11 vendor TERSET+FRADJ test uses exactly 2e-4 m/s.
    # Do not enlarge scientific tolerance for source-selected file inputs.
    for key in sorted(reference):
        for part, original, cpp in zip(("U", "V"), reference[key], native[key]):
            err = abs(original - cpp)
            maximum = max(maximum, err)
            if err > 2e-4:
                failures.append((key, part, original, cpp, err))
    evidence = {
        "scope": "selected G21 first-hour source-file WIND1 TEMP2D GAMMA TERSET FRADJ",
        "data": "synthetic observations in original format",
        "independent_fortran_original_source_sha256": sha256,
        "mode": args.mode,
        "cells": stage["cells"],
        "uv_compared": len(reference) * 2,
        "original_terrad_km": stage["source_terrad"],
        "original_critfn": stage["source_critfn"],
        "max_abs_uv_delta_mps": maximum,
        "nontrivially_modified_uv_components": modified_components,
        "nontrivial_correction_required": args.require_nontrivial,
        "unchanged_original_g11_tolerance_mps": 2e-4,
        "failures": failures[:10],
        "independent_original_fortran_preprocessing": False,
        "full_multi_station_45_field_accepted": False,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(evidence, indent=2) + "\n")
    if failures:
        raise AssertionError(
            f"G21 source-file original FRADJ failed on {len(failures)} "
            f"U/V, max abs={maximum:.8g}, first={failures[:3]}"
        )
    print(
        "PASS_P6G_G21_ORIGINAL_FORTRAN_SELECTED_SOURCE_FRADJ "
        f"mode={args.mode} compared={2*len(reference)} "
        f"max_abs_delta={maximum:.9g} corrected_components={modified_components} "
        f"vendor_sha256={sha256} "
        "full_calmet_45_field=NOT_ACCEPTED"
    )


if __name__ == "__main__":
    main()
