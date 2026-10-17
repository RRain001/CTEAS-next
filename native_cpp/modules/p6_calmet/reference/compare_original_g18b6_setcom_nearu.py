#!/usr/bin/env python3
"""G18B6: literally extract CALMET 6.5.0 vendor SETCOM NEARU source, compile
it with gfortran, and require exact one-based ordinal parity with production
C++ G18B3, including ordered upper-station ties and multisite grids.
No substitute hand-authored Fortran nearest-station formula is allowed.
"""
import argparse
import json
import pathlib
import subprocess
import tempfile


def literal_vendor_oracle(vendor: str) -> str:
    lower = vendor.lower()
    routine = lower.find("      subroutine setcom(ldb)")
    if routine < 0:
        raise RuntimeError("CALMET vendor SETCOM routine is absent")
    start = lower.find(
        "c --- find nearest upper air station to each grid point", routine
    )
    finish = lower.find("120   continue", start)
    if start < 0 or finish < 0 or finish - start > 2800:
        raise RuntimeError("Vendor SETCOM NEARU block missing or altered")
    block = vendor[start : finish + len("120   continue")]
    required = (
        "if(nusta.le.0)go to 121",
        "xgdpt=(float(i)-0.5)*dgrid",
        "ygdpt=(float(j)-0.5)*dgrid",
        "dist2=(xusta(k)-xgdpt)**2+(yusta(k)-ygdpt)**2",
        "if(dist2.lt.dmin2)then",
        "nearu(i,j)=ksv",
    )
    compact = "".join(block.lower().split())
    if any("".join(expr.lower().split()) not in compact for expr in required):
        raise RuntimeError("Vendor SETCOM NEARU source arithmetic has changed")
    return """      program original_setcom_nearu
      implicit none
      integer nx,ny,nusta,io6
      integer nearu(100,100)
      integer i,j,k,ksv
      real dgrid,rmax,dmin2,dist2,xgdpt,ygdpt
      real xusta(6),yusta(6)
      data rmax/1.e37/
      io6=6
      read(*,*) nx,ny,nusta,dgrid
      if(nx.lt.2.or.ny.lt.2.or.nx.gt.100.or.ny.gt.100)
     1  stop 90
      if(nusta.lt.1.or.nusta.gt.6)stop 91
      do k=1,nusta
         read(*,*)xusta(k),yusta(k)
      enddo
""" + block + """
121   continue
      do j=1,ny
        do i=1,nx
          write(*,'(I5)') nearu(i,j)
        enddo
      enddo
      stop
18    format(3i7,1x,a8)
      end
"""


def fixture(nx: int, ny: int, nsta: int, spacing: float, seed: int) -> str:
    stations: list[tuple[float, float]] = []
    for k in range(nsta):
        if seed == 1 and k < 2:
            # Identical station positions: first US ordinal always wins.
            x = y = 5000.0
        elif seed == 2 and k < 2:
            # Exactly equidistant around the first grid point.
            x, y = (0.0, 5000.0) if k == 0 else (10000.0, 5000.0)
        else:
            x = float((k * 21000 + (seed + 1) * 1700)
                      % (nx * spacing + 12000))
            y = float((k * 13000 + (seed + 1) * 2500)
                      % (ny * spacing + 9000))
        stations.append((x, y))
    return "\n".join(
        [f"{nx} {ny} {nsta} {spacing}"]
        + [f"{x} {y}" for x, y in stations]
    ) + "\n"


def output_ordinals(stdout: str, expected_count: int) -> list[int]:
    got = [int(line) for line in stdout.splitlines() if line.strip()]
    if len(got) != expected_count:
        raise AssertionError(f"Expected {expected_count} cells; got {len(got)}")
    return got


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--vendor", required=True, type=pathlib.Path)
    parser.add_argument("--cpp", required=True, type=pathlib.Path)
    parser.add_argument("--gfortran", default="gfortran")
    parser.add_argument("--out", required=True, type=pathlib.Path)
    args = parser.parse_args()

    vendor = args.vendor.read_text(encoding="latin-1")
    program = literal_vendor_oracle(vendor)
    cases = [
        (3, 3, 1, 10000.0, 0),
        (4, 4, 2, 10000.0, 1),
        (2, 2, 2, 10000.0, 2),
        (12, 12, 2, 10000.0, 0),
        (12, 12, 3, 10000.0, 2),
        (12, 12, 6, 10000.0, 3),
        (6, 8, 6, 5000.0, 1),
        (7, 5, 4, 5000.0, 0),
        (24, 19, 6, 10000.0, 4),
        (50, 50, 6, 10000.0, 5),
    ]
    with tempfile.TemporaryDirectory(prefix="g18b6-setcom-nearu-") as temp:
        root = pathlib.Path(temp)
        src = root / "original_nearu.f"
        exe = root / "original_nearu"
        src.write_text(program, encoding="ascii")
        subprocess.run(
            [args.gfortran, "-O0", "-ffixed-line-length-none",
             str(src), "-o", str(exe)],
            check=True, capture_output=True, text=True
        )
        checked = 0
        for case in cases:
            data = fixture(*case)
            num_cells = case[0] * case[1]
            vendor_result = output_ordinals(subprocess.run(
                [str(exe)], input=data, text=True,
                capture_output=True, check=True
            ).stdout, num_cells)
            cpp_result = output_ordinals(subprocess.run(
                [str(args.cpp)], input=data, text=True,
                capture_output=True, check=True
            ).stdout, num_cells)
            for idx, (candidate, original) in enumerate(
                zip(cpp_result, vendor_result)
            ):
                if candidate != original:
                    raise AssertionError(
                        f"NEARU strict source parity FAIL case={case}; "
                        f"cell={idx}; C++={candidate}, vendor={original}"
                    )
            checked += num_cells
    report = {
        "status": "PASS",
        "original_routine": "CALMET v6.5.0 SETCOM NEARU extracted literal",
        "cases": len(cases),
        "source_compared_cells": checked,
        "tolerance": "exact integer ordinal (zero exceptions)",
        "scope": "selected grid, 1-6 upper stations, REAL4 source ties",
        "not_accepted": "complete 17-stage multi-site CALMET physical parity",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print("PASS_G18B6_LITERAL_VENDOR_SETCOM_NEARU", report)


if __name__ == "__main__":
    main()
