#!/usr/bin/env python3
"""Independent CALPUFF 7.2.1 original PFSCRN REAL*4 vs native C++ check.

Extracts the original Fortran subroutine directly from the bundled vendor
source and invokes gfortran. No reimplementation of the oracle formula.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import subprocess
import tempfile


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--vendor", type=Path, required=True)
    parser.add_argument("--probe", type=Path, required=True)
    parser.add_argument("--compiler", default="gfortran")
    args = parser.parse_args()
    content = args.vendor.read_text(encoding="latin-1")
    begin = content.lower().find("      subroutine pfscrn(")
    end = content.lower().find("      subroutine pfsamp(", begin)
    if begin < 0 or end < 0:
        raise RuntimeError("unmodified PFSCRN source bounds not found")
    original = content[begin:end]
    if "a=c1/puffr2" not in original.lower() or "dist2.gt.puffr2" not in original.lower():
        raise RuntimeError("CALPUFF PFSCRN original source authority drifted")
    driver = """
program probe
  implicit none
  real :: xo,yo,xn,yn,xr,yr,r2,dist
  logical :: impact
  integer :: status
  do
    read(*,*,iostat=status) xo,yo,xn,yn,xr,yr,r2
    if (status /= 0) exit
    call pfscrn(xo,yo,xn,yn,xr,yr,r2,dist,impact)
    write(*,'(Z8.8,1X,I1)') transfer(dist,0),merge(1,0,impact)
  end do
end program
"""
    # All coordinates and radius**2 are passed as exactly rounded REAL4.
    # Includes moving, outside, boundary, low-wind, oblique, and endpoint.
    cases = [
        (0,0,2,0,1,0,1),
        (0,0,2,0,1,0.5,1),
        (0,0,2,0,3,0,1),
        (0,0,2,0,3.5,0,1),
        (0,0,0,0,0.25,0.25,1),
        (0,0,0.001,0,0.25,0.25,1),
        (5,4,9,8,7,6,4),
        (5,4,9,8,5,4,4),
        (5,4,9,8,9,8,4),
        (5,4,9,8,10,10,4),
        (7,2,7,4,7,3,0.5),
        (7,2,7,4,8,3,0.5),
        (1,1,-1,-1,0,0,0.5),
        (100,200,101,201,100.5,200.75,2),
        (-10,-20,-9,-21,-9.5,-20.5,0.25),
        (1,2,1.001,2.001,1.25,2.25,16),
    ]
    input_text = "".join(" ".join(str(a) for a in case) + "\n" for case in cases)
    with tempfile.TemporaryDirectory(prefix="cteas-p7-pfscrn-") as tmp:
        folder = Path(tmp)
        fortran_source = folder / "vendor_pfscrn.for"
        fortran_source.write_text(original, encoding="latin-1")
        fortran_driver = folder / "driver.f90"
        fortran_driver.write_text(driver, encoding="ascii")
        exe = folder / "vendor_probe"
        subprocess.run(
            [args.compiler, "-O0", "-ffixed-line-length-none",
             str(fortran_source), str(fortran_driver), "-o", str(exe)],
            check=True, capture_output=True, text=True,
        )
        def execute(command: list[str]) -> list[str]:
            result = subprocess.run(command, input=input_text, text=True,
                                    capture_output=True, check=True)
            return [line.upper().strip() for line in result.stdout.splitlines()]
        vendor = execute([str(exe)])
        native = execute([str(args.probe)])
    if len(vendor) != len(cases) or len(native) != len(cases):
        raise AssertionError(f"wrong source/native counts: {len(vendor)}/{len(native)}")
    for number, (expected, actual) in enumerate(zip(vendor, native), 1):
        if expected != actual:
            raise AssertionError(
                f"ORIGINAL_PFSCRN_FIRST_DIFF_CASE={number} "
                f"inputs={cases[number-1]} ORIGINAL={expected} CXX={actual}"
            )
    print(f"P7_ORIGINAL_PFSCRN_REAL4_FORTRAN_PARITY=PASS CASES={len(cases)} "
          "DIST2_BITS=EXACT IMPACT=EXACT")


if __name__ == "__main__":
    main()
