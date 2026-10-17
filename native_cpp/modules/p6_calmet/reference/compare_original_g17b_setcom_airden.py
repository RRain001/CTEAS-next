#!/usr/bin/env python3
"""Compile literal source SETCOM NEARS and AIRDEN fragments from original CALMET.

Do not replace the vendor fragment with a handwritten reference: source
provenance is checked and both reference fragments are used verbatim.
Strict station ordinal and REAL*4 density bit parity on 10km multisite grids.
"""
import argparse
import json
import pathlib
import struct
import subprocess
import tempfile

def extract(source: str, beginning: str, ending: str, after: str = "") -> str:
    pos = source.lower().find(after.lower()) if after else 0
    if pos < 0:
        raise ValueError("Original CALMET subroutine not present: " + after)
    start = source.lower().find(beginning.lower(), pos)
    if start < 0:
        raise ValueError("Original CALMET block start not present: " + beginning)
    finish = source.lower().find(ending.lower(), start)
    if finish < 0:
        raise ValueError("Original CALMET block end not present: " + ending)
    finish += len(ending)
    return source[start:finish]

def oracle_source(vendor: str) -> str:
    selected = extract(vendor, "      do 20 i=1,nx",
                       "20    continue", "      subroutine setcom(ldb)")
    airden = extract(vendor, "      do 200 j=1,ny",
                     "200   continue", "      subroutine airden(")
    for term in ("dmin2=rmax", "dist2.lt.dmin2", "nears(i,j)=ksv"):
        if term.lower() not in selected.lower():
            raise ValueError("SETCOM original semantics changed: " + term)
    if "rho(i,j)=0.3484321*pres(nsta)/temp2d(i,j)" not in airden.lower():
        raise ValueError("AIRDEN source expression missing/changed")
    return """      program original_g17b
      implicit none
      integer nx,ny,nssta,io6
      integer nears(100,100)
      integer i,j,k,ksv,nsta
      real dgrid,rmax,dmin2,dist2,xgdpt,ygdpt
      real xssta(6),yssta(6),pres(6)
      real temp2d(100,100),rho(100,100)
      data rmax/1.e37/
      io6=6
      read(*,*) nx,ny,nssta,dgrid
      if(nx.lt.2.or.ny.lt.2.or.nx.gt.100.or.ny.gt.100)
     1   stop 90
      if(nssta.lt.1.or.nssta.gt.6)stop 91
      do k=1,nssta
         read(*,*)xssta(k),yssta(k),pres(k)
      enddo
      do j=1,ny
         read(*,*)(temp2d(i,j),i=1,nx)
      enddo
""" + selected + "\n" + airden + """
      do j=1,ny
         do i=1,nx
            write(*,'(I5,1X,ES20.10)') nears(i,j),rho(i,j)
         enddo
      enddo
      end
"""

def as_rows(stdout: str, cells: int) -> list[tuple[int, bytes]]:
    rows = [line.split() for line in stdout.splitlines() if line.strip()]
    if len(rows) != cells:
        raise AssertionError(f"Expected {cells} cells, got {len(rows)}")
    if any(len(row) != 2 for row in rows):
        raise AssertionError("Malformed NEARS/AIRDEN output")
    return [(int(r[0]), struct.pack("<f", float(r[1]))) for r in rows]

def fixture(nx, ny, nsta, spacing, seed):
    # Multiple source-order situations incl. exactly equidistant station
    # pairs (original uses strict '<' to preserve first station).
    stations = []
    for k in range(nsta):
        if seed == 1 and k < 2:
            x = y = 5000.0
        else:
            x = (k * 21000 + (seed + 1) * 1700) % (nx * spacing + 12000)
            y = (k * 13000 + (seed + 1) * 2500) % (ny * spacing + 9000)
        stations.append((float(x), float(y), 985.0 + k * 7.0))
    temps = [276.0 + 0.125 * (i + j * nx) + 0.03125 * seed
             for j in range(ny) for i in range(nx)]
    lines = [f"{nx} {ny} {nsta} {spacing}"]
    lines += [f"{x} {y} {p}" for x, y, p in stations]
    lines += [" ".join(str(temps[j * nx + i]) for i in range(nx))
              for j in range(ny)]
    return "\n".join(lines) + "\n"

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--vendor", required=True, type=pathlib.Path)
    parser.add_argument("--cpp", required=True, type=pathlib.Path)
    parser.add_argument("--gfortran", default="gfortran")
    parser.add_argument("--out", required=True, type=pathlib.Path)
    args = parser.parse_args()
    vendor = args.vendor.read_text(encoding="latin-1")
    oracle = oracle_source(vendor)
    cases = [
        (3, 3, 1, 10000., 0),
        (4, 4, 2, 10000., 1),
        (12, 12, 2, 10000., 0),
        (12, 12, 3, 10000., 2),
        (6, 8, 6, 10000., 3),
        (12, 12, 6, 10000., 1),
        (7, 5, 4, 5000., 3),
        (12, 12, 2, 10000., 4),
    ]
    with tempfile.TemporaryDirectory(prefix="g17b-original-") as root:
        source = pathlib.Path(root) / "g17b_original.f"
        binary = pathlib.Path(root) / "source_original"
        source.write_text(oracle, encoding="ascii")
        subprocess.run([args.gfortran, "-O0", "-ffixed-line-length-none",
                        str(source), "-o", str(binary)],
                       check=True, capture_output=True, text=True)
        checked = 0
        for case in cases:
            input_data = fixture(*case)
            expected = as_rows(
                subprocess.run([str(binary)], input=input_data, text=True,
                               capture_output=True, check=True).stdout,
                case[0] * case[1])
            actual = as_rows(
                subprocess.run([str(args.cpp)], input=input_data, text=True,
                               capture_output=True, check=True).stdout,
                case[0] * case[1])
            for index, (a, b) in enumerate(zip(actual, expected)):
                if a != b:
                    raise AssertionError(
                        f"Original SETCOM/AIRDEN mismatch case={case}, "
                        f"cell={index} C++=({a[0]},{a[1].hex()}) "
                        f"Fortran=({b[0]},{b[1].hex()})")
            checked += len(expected)
    report = {"status": "PASS", "cases": len(cases),
              "cells_and_density_values": checked,
              "comparison": "exact NEARS ordinal and REAL*4 AIRDEN bit equality",
              "reference": "literal vendor calmet.for SETCOM + AIRDEN source"}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print("PASS_G17B_ORIGINAL_SETCOM_AIRDEN_SOURCE_PARITY", report)
if __name__ == "__main__":
    main()
