#!/usr/bin/env python3
"""Build a small reference directly from the vendored original CALMET WIND1.

This uses unchanged original Fortran statement lines 36204-36397, with
explicit deterministic 2-SS/2-US inputs supplied by a standalone driver.
Compares its U/V values to the C++ G9 kernel, not to a paraphrased reference.

Scope: the selected original 10km IEXTRP=-4/ICALM=0/NBAR=0 stage AFTER
surface SIMILT and upper PREPDI. No other parts of CALMET or P6E/F are tested.
"""
from __future__ import annotations

import argparse
import hashlib
import math
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
VENDOR = ROOT / "engine/vendor/src/CALMET_v6.5.0_L150223/calmet.for"
CPP = ROOT / "native_cpp/modules/p6_calmet/tests/p6g_g9_original_wind1_probe.cpp"
INCLUDE = ROOT / "native_cpp/modules/p6_calmet/include"

FORTRAN_HEAD = """      program original_wind1_probe
      implicit none
      integer nx,ny,nz,nssta,nowsta,nusta,nstat
      parameter(nx=3,ny=3,nz=3,nssta=2,nowsta=0,nusta=2,nstat=4)
      integer i,j,k,l,ll,iu,nbar,kbar,io6,icalm
      real dgrid,dgridi,xc,yc,xr2,wgt,sumwt
      real sumwsfold,sumwupold,beta,gamma,unext,vnext
      real x,y,ok,editl
      real xssta(nssta),yssta(nssta)
      real xusta(nusta),yusta(nusta)
      real xowsta(1),yowsta(1),xst(nstat),yst(nstat)
      real us(nz,nstat),vs(nz,nstat)
      real ustmp(nz,nstat),vstmp(nz,nstat)
      real ws10(nssta),rsqwt(nstat),vvw(nz,nstat)
      real bias(nz),ug(nx,ny,nz),vg(nx,ny,nz)
      dgrid=10000.
      editl=999998.
      io6=6
      nbar=0
      kbar=0
      icalm=0
      xssta(1)=10000.
      yssta(1)=10000.
      xssta(2)=30000.
      yssta(2)=40000.
      xusta(1)=20000.
      yusta(1)=20000.
      xusta(2)=50000.
      yusta(2)=50000.
      ws10(1)=0.
      ws10(2)=5.
      do k=1,nz
        bias(k)=0.
      enddo
      bias(1)=0.
      bias(2)=0.3
      bias(3)=-0.2
      do k=1,nz
        us(k,1)=0.
        vs(k,1)=0.
        us(k,2)=3.
        vs(k,2)=4.
        us(k,3)=5.
        vs(k,3)=-2.
        us(k,4)=9.
        vs(k,4)=10.
      enddo
      us(2,4)=999999.
      vs(2,4)=999999.
      do l=1,nstat
        do k=1,nz
          ustmp(k,l)=us(k,l)
          vstmp(k,l)=vs(k,l)
        enddo
      enddo
"""
FORTRAN_TAIL = """      do k=1,nz
        do j=1,ny
          do i=1,nx
            write(*,'(A,3(1X,I3),2(1X,ES17.9))')
     &        'GRID',i,j,k,ug(i,j,k),vg(i,j,k)
          enddo
        enddo
      enddo
      end

      subroutine barier(x,y,xst,yst,ok)
      real x,y,xst,yst,ok
      ok=1.
      return
      end
"""


def lift_vendor(expanded: bool) -> tuple[str, str]:
    raw = VENDOR.read_bytes()
    lines = raw.decode("latin-1").splitlines(keepends=True)
    if len(lines) < 36397:
        raise ValueError("vendor CALMET 6.5.0 WIND1 line numbers unavailable")
    excerpt = "".join(lines[36204 - 1 : 36397])
    if "compute bulk weights" not in excerpt.lower() or "subroutine" in excerpt.lower():
        raise ValueError("vendor WIND1 source location changed; do not fall back to reimplemented code")
    if "vvw(k,l)" not in excerpt or "ug(i,j,k)=unext" not in excerpt:
        raise ValueError("original WIND1 numerical source statements not found")
    header = FORTRAN_HEAD
    if expanded:
        header = (header
                  .replace("nx=3,ny=3,nz=3", "nx=12,ny=12,nz=9")
                  .replace("xssta(2)=30000.", "xssta(2)=100000.")
                  .replace("yssta(2)=40000.", "yssta(2)=100000.")
                  .replace("xusta(2)=50000.", "xusta(2)=90000.")
                  .replace("yusta(2)=50000.", "yusta(2)=90000."))
    return header + excerpt + FORTRAN_TAIL, hashlib.sha256(raw).hexdigest()


def rows(text: str, expected: int) -> dict[tuple[int, int, int], tuple[float, float]]:
    values = {}
    for record in text.splitlines():
        words = record.strip().split()
        if not words or words[0] != "GRID":
            continue
        if len(words) != 6:
            raise ValueError(f"malformed reference U/V row: {record}")
        key = tuple(map(int, words[1:4]))
        if key in values:
            raise ValueError(f"duplicate original field cell {key}")
        uv = tuple(float(x.replace("D", "E")) for x in words[4:])
        if not all(math.isfinite(q) for q in uv):
            raise ValueError(f"nonfinite original wind field {key}")
        values[key] = uv
    if len(values) != expected:
        raise ValueError(f"expected {expected} three-dimensional original WIND1 cells, got {len(values)}")
    return values


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=("Debug", "Release"), required=True)
    args = ap.parse_args()
    common = ["-ffixed-line-length-none", "-std=legacy"]
    opt = "-O0" if args.mode == "Debug" else "-O2"
    with tempfile.TemporaryDirectory(prefix="p6g-g9-source-") as temp:
        root = Path(temp)
        subprocess.run(["g++", "-std=c++20", opt, "-Wall", "-Wextra", "-Wpedantic",
                        "-Werror", "-I", str(INCLUDE), str(CPP),
                        "-o", str(root / "native")], check=True)
        for expanded in (False, True):
            fortran, sha = lift_vendor(expanded)
            scenario = "expanded120km" if expanded else "initial30km"
            expected = 12 * 12 * 9 if expanded else 3 * 3 * 3
            path = root / f"wind1_original_{scenario}.f"
            path.write_text(fortran, encoding="latin-1")
            executable = root / f"original_{scenario}"
            subprocess.run(["gfortran", opt, *common, str(path), "-o",
                            str(executable)], check=True)
            original = subprocess.run([str(executable)], capture_output=True,
                                      text=True, check=True)
            native_cmd = [str(root / "native")]
            if expanded:
                native_cmd.append("expanded")
            native = subprocess.run(native_cmd, capture_output=True,
                                    text=True, check=True)
            f = rows(original.stdout, expected)
            c = rows(native.stdout, expected)
            if f.keys() != c.keys():
                raise ValueError("original and C++ grid ordering/coordinates differ")
            failures = []
            maximum = 0.0
            for key in sorted(f):
                for a, b in zip(f[key], c[key]):
                    diff = abs(a - b)
                    maximum = max(maximum, diff)
                    if diff > 2e-6:
                        failures.append((key, a, b, diff))
            if failures:
                raise AssertionError(
                    f"original Fortran WIND1 vs C++ mismatch scenario={scenario}: "
                    f"max abs delta={maximum:.9g}, sample={failures[:5]}")
            print("PASS P6G_G9_DIRECT_ORIGINAL_FORTRAN_WIND1_SELECTED_MULTISTATION "
                  f"mode={args.mode} scenario={scenario} cells={len(f)} "
                  f"max_abs_uv_delta={maximum:.9g} original_sha256={sha}")


if __name__ == "__main__":
    main()
