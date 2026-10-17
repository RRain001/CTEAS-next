#!/usr/bin/env python3
"""G18C1: extract the actual original CALMET 6.5.0 AVEMIX routine,
compile unchanged Fortran under explicit params.met workspace dimensions,
and compare each original REAL*4 output against the new native C++ kernel.
No hand-written surrogate physics/oracle; REAL*4 exact comparison.
"""
import argparse
import json
import pathlib
import struct
import subprocess
import tempfile


def vendor_source(blob: str) -> str:
    low = blob.lower()
    start = low.find("      subroutine avemix(")
    end = low.find("\n      end\n", start)
    if start < 0 or end < 0 or end - start > 15000:
        raise RuntimeError("Original vendor CALMET AVEMIX source missing")
    block = blob[start:end + len("\n      end")]
    for sentinel in [
        "dtdx = dtime / dgrid",
        "tanang= tan(degrad * hafang)",
        "ietax = int(etax)",
        "icwx = int(etay * tanang)",
        "if ((abs(irel).le.mnmdav).and.(abs(jrel).le.mnmdav)) goto 47",
        "wt = one / (dela**2 + (one + abs(delc))**2)",
        "ziave(i,j)  = zibar  / sumwt",
        "zicave(i,j) = zicbar / sumwt",
    ]:
        if "".join(sentinel.lower().split()) not in "".join(block.lower().split()):
            raise RuntimeError("Original AVEMIX source expression altered: " + sentinel)
    return block


def oracle_program(block: str) -> str:
    program = """      program literal_original_avemix
      implicit none
      integer nx,ny,mnmdav,i,j
      real hafang,dgrid
      real u(64,64),v(64,64),zi(64,64),zc(64,64)
      read(*,*) nx,ny,mnmdav,hafang,dgrid
      if(nx.lt.2.or.ny.lt.2.or.nx.gt.64.or.ny.gt.64)
     &   stop 90
      do j=1,ny
         do i=1,nx
            read(*,*) u(i,j),v(i,j),zi(i,j),zc(i,j)
         enddo
      enddo
      call avemix(nx,ny,mnmdav,hafang,dgrid,u,v,zi,zc)
      do j=1,ny
         do i=1,nx
            write(*,'(2(ES20.10,1X))') zi(i,j),zc(i,j)
         enddo
      enddo
      end
"""
    return program + block + "\n"


def fixture(nx: int, ny: int, radius: int, half: float,
            spacing: float, seed: int) -> str:
    out = [f"{nx} {ny} {radius} {half} {spacing}"]
    for j in range(ny):
        for i in range(nx):
            if seed == 0:
                u = v = 0.
            elif seed == 1:
                u = (i % 3 - 1) * 3.
                v = (j % 3 - 1) * 2.
            elif seed == 2:
                u = 4.
                v = 0.
            elif seed == 3:
                u = -4.
                v = 3.
            elif seed == 4:
                u = 12. if j % 2 else -12.
                v = 7. if i % 2 else -7.
            else:
                u = (i * 7 + j * 11 + seed * 3) % 23 - 11.
                v = (i * 19 - j * 13 + seed * 7) % 17 - 8.
            zi = 100. + float((i * 13 + j * 7 + seed * 11) % 251)
            zc = float((i * 29 + j * 17 + seed * 5) % 191)
            out.append(f"{u} {v} {zi} {zc}")
    return "\n".join(out) + "\n"


def values(text: str, expected: int) -> list[tuple[bytes, bytes]]:
    rows = [line.split() for line in text.splitlines() if line.strip()]
    if len(rows) != expected or any(len(row) != 2 for row in rows):
        raise AssertionError(f"AVEMIX return shape incorrect: {len(rows)} vs {expected}")
    return [tuple(struct.pack("<f", float(v.replace("D", "E"))) for v in row)
            for row in rows]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--vendor", required=True, type=pathlib.Path)
    parser.add_argument("--cpp", required=True, type=pathlib.Path)
    parser.add_argument("--gfortran", default="gfortran")
    parser.add_argument("--out", required=True, type=pathlib.Path)
    args = parser.parse_args()
    block = vendor_source(args.vendor.read_text(encoding="latin-1"))
    cases = [
        (3, 3, 0, 30., 10000., 0),
        (3, 3, 1, 30., 10000., 0),
        (5, 5, 1, 30., 10000., 1),
        (5, 5, 1, 30., 10000., 2),
        (7, 6, 1, 30., 10000., 3),
        (10, 9, 1, 30., 10000., 4),
        (12, 12, 1, 30., 10000., 5),
        (12, 12, 3, 30., 10000., 6),
        (12, 12, 3, 25., 5000., 3),
        (17, 13, 2, 45., 5000., 5),
        (20, 17, 4, 35., 1000., 5),
        (30, 21, 1, 30., 10000., 7),
        (50, 50, 1, 30., 10000., 5),
    ]
    with tempfile.TemporaryDirectory(prefix="g18c1-vendor-avemix-") as tmp:
        root = pathlib.Path(tmp)
        src = root / "literal_avemix.f"
        binary = root / "literal_avemix"
        # Only dimensions/IO unit supplied by params.met; original AVEMIX
        # executable lines are not edited or reimplemented.
        (root / "params.met").write_text(
            "      integer mxnx,mxny,io6\n"
            "      parameter(mxnx=64,mxny=64,io6=6)\n", encoding="ascii")
        src.write_text(oracle_program(block), encoding="ascii")
        subprocess.run([args.gfortran, "-O0", "-ffixed-line-length-none",
                        "-I", str(root), str(src), "-o", str(binary)],
                       check=True, capture_output=True, text=True)
        compared = 0
        for spec in cases:
            input_data = fixture(*spec)
            count = spec[0] * spec[1]
            original = values(subprocess.run(
                [str(binary)], input=input_data, capture_output=True,
                text=True, check=True).stdout, count)
            candidate = values(subprocess.run(
                [str(args.cpp)], input=input_data, capture_output=True,
                text=True, check=True).stdout, count)
            for cell, (actual, expected) in enumerate(zip(candidate, original)):
                if actual != expected:
                    raise AssertionError(
                        f"AVEMIX source mismatch case={spec}, cell={cell}, "
                        f"C++={[v.hex() for v in actual]}, "
                        f"Fortran={[v.hex() for v in expected]}")
            compared += count
    report = {
        "status": "PASS",
        "source": "literal CALMET 6.5.0 AVEMIX, original executable Fortran body",
        "cases": len(cases),
        "compared_cells": compared,
        "fields": ["ZI", "ZICONV"],
        "tolerance": "exact REAL*4 bit parity",
        "not_accepted": "complete multi-station COMP/P6F or 45-field full run"
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print("PASS_G18C1_LITERAL_VENDOR_AVEMIX_SOURCE_REAL4", report)


if __name__ == "__main__":
    main()
