#!/usr/bin/env python3
"""G18B8 literal vendor CALMET original CGAMMA->GAMMA grid oracle.

Extracts two DIAGNO IUPT branches and the actual CMPD2 Fortran routine
verbatim from calmet.for, compiles the original source and compares REAL*4
bit patterns against the C++ G18B8 source adapter (not rewritten Fortran).
"""
import argparse
import json
import pathlib
import struct
import subprocess
import tempfile


def vendor_oracle(source: str) -> str:
    lower = source.lower()
    cgamma = lower.find("call cgamma(nyrze,njulze,nhrze,nsece,iu,zupt")
    if cgamma < 0:
        raise RuntimeError("Original DIAGNO per-US CGAMMA call absent")
    branch = lower.rfind("if(iupt.gt.0) then", 0, cgamma)
    if branch < 0 or cgamma - branch > 2000:
        raise RuntimeError("Original IUPT branch not found near CGAMMA")
    fill_start = lower.find("              do i=1,nx", branch)
    fill_end = lower.find("              end do",
                          lower.find("              end do", fill_start) + 1)
    if fill_start < 0 or fill_end < 0 or fill_end - fill_start > 500:
        raise RuntimeError("Original positive IUPT GAMMA fill changed")
    positive = source[fill_start:fill_end + len("              end do")]
    start = lower.find("              do 210 i=1,nx", cgamma)
    end = lower.find("210           continue", start)
    if start < 0 or end < 0 or end - start > 1900:
        raise RuntimeError("Original 2D 1/R**2 GAMMA loop missing")
    grid = source[start:end + len("210           continue")]
    for expression in (
        "xgm=(float(i)-0.5)*dgrid",
        "ygm=(float(j)-0.5)*dgrid",
        "call cmpd2(xgm,ygm,xusta,yusta,nusta,dis2)",
        "dis2saf=amax1(dis2(k),0.01)",
        "top=top+gamup(k)/dis2saf",
        "bot=bot+1.0/dis2saf",
        "gamma(i,j)=top/bot",
    ):
        if "".join(expression.lower().split()) not in "".join(grid.lower().split()):
            raise RuntimeError("Original Fortran GAMMA equation changed: " + expression)
    cmppos = lower.index("      subroutine cmpd2(", 0)
    cmpend = lower.find("\n      end", cmppos)
    if cmpend < 0 or cmpend - cmppos > 2500:
        raise RuntimeError("Original CMPD2 source missing")
    cmpd2 = source[cmppos:cmpend + len("\n      end")]
    if "dist2(i)=(x(i)-xref)**2+(y(i)-yref)**2" not in cmpd2.lower():
        raise RuntimeError("Original CMPD2 REAL4 formula changed")
    return """      program original_g18b8
      implicit none
      integer nx,ny,nusta,iupt,io6
      integer i,j,k
      real dgrid,xgm,ygm,top,bot,dis2saf
      real xusta(6),yusta(6),gamup(6),dis2(6)
      real gamma(100,100)
      read(*,*) nx,ny,nusta,iupt,dgrid
      if(nx.lt.2.or.ny.lt.2.or.nx.gt.100.or.ny.gt.100)
     1   stop 90
      if(nusta.lt.1.or.nusta.gt.6)stop 91
      if(iupt.ne.-1.and.(iupt.lt.1.or.iupt.gt.nusta))stop 92
      do k=1,nusta
        read(*,*)xusta(k),yusta(k),gamup(k)
      enddo
      if(iupt.gt.0) then
""" + positive + """
      else
""" + grid + """
      endif
      do j=1,ny
        do i=1,nx
          write(*,'(ES20.10)') gamma(i,j)
        enddo
      enddo
      end
""" + cmpd2 + "\n"


def fixture(nx: int, ny: int, nusta: int, iupt: int,
            spacing: float, seed: int) -> str:
    rows = [f"{nx} {ny} {nusta} {iupt} {spacing}"]
    for k in range(nusta):
        if seed == 1 and k < 2:
            x = 5000.
            y = 5000.
        elif seed == 2 and k < 2:
            x = 0. if k == 0 else 10000.
            y = 5000.
        elif seed == 3 and k == 0:
            x = 5000.  # exact 0-m colocation with first 10km grid center
            y = 5000.
        else:
            x = float((k * 21000 + (seed + 1) * 1700)
                      % (nx * spacing + 12000))
            y = float((k * 13000 + (seed + 1) * 2500)
                      % (ny * spacing + 9000))
        value = (-1 if k % 2 else 1) * (0.00125 + 0.00003125 * k + seed / 128000.)
        rows.append(f"{x} {y} {value:.12g}")
    return "\n".join(rows) + "\n"


def real4_bits(text: str, count: int) -> list[bytes]:
    entries = [line.strip() for line in text.splitlines() if line.strip()]
    if len(entries) != count:
        raise AssertionError(f"expected {count} GAMMA entries, got {len(entries)}")
    return [struct.pack("<f", float(v.replace("D", "E"))) for v in entries]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--vendor", type=pathlib.Path, required=True)
    parser.add_argument("--cpp", type=pathlib.Path, required=True)
    parser.add_argument("--gfortran", default="gfortran")
    parser.add_argument("--out", type=pathlib.Path, required=True)
    args = parser.parse_args()
    source = args.vendor.read_text(encoding="latin-1")
    program = vendor_oracle(source)
    cases = [
        (3, 3, 1, -1, 10000., 0),
        (4, 4, 2, -1, 10000., 1),
        (2, 2, 2, -1, 10000., 2),
        (6, 8, 2, -1, 10000., 3),
        (12, 12, 3, -1, 10000., 0),
        (12, 12, 6, -1, 10000., 5),
        (24, 19, 6, -1, 10000., 3),
        (50, 50, 6, -1, 10000., 4),
        (7, 5, 4, -1, 5000., 0),
        (12, 12, 4, -1, 5000., 1),
        (12, 12, 3, 1, 10000., 0),
        (12, 12, 3, 2, 10000., 2),
        (12, 12, 3, 3, 10000., 5),
        (50, 50, 6, 6, 10000., 4),
    ]
    with tempfile.TemporaryDirectory(prefix="g18b8-source-") as folder:
        root = pathlib.Path(folder)
        src = root / "literal_vendor_gamma.f"
        binary = root / "literal_vendor_gamma"
        src.write_text(program, encoding="ascii")
        subprocess.run([args.gfortran, "-O0", "-ffixed-line-length-none",
                        str(src), "-o", str(binary)],
                       text=True, check=True, capture_output=True)
        total = 0
        for case in cases:
            stdin = fixture(*case)
            cells = case[0] * case[1]
            oracle = real4_bits(
                subprocess.run([str(binary)], input=stdin, text=True,
                               capture_output=True, check=True).stdout, cells)
            native = real4_bits(
                subprocess.run([str(args.cpp)], input=stdin, text=True,
                               capture_output=True, check=True).stdout, cells)
            for cell, (actual, expected) in enumerate(zip(native, oracle)):
                if actual != expected:
                    raise AssertionError(
                        f"G18B8 REAL4 parity mismatch: case={case} cell={cell} "
                        f"cpp={actual.hex()} vendor={expected.hex()}"
                    )
            total += cells
    report = {
        "status": "PASS",
        "cases": len(cases),
        "compared_cells": total,
        "tolerance": "literal REAL4 bit parity, zero exceptions",
        "source": "literal CALMET v6.5.0 DIAGNO IUPT GAMMA + CMPD2",
        "excludes": "upstream per-US CGAMMA state source and full 45-field hour"
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print("PASS_G18B8_LITERAL_VENDOR_DIAGNO_GAMMA_REAL4", report)


if __name__ == "__main__":
    main()
