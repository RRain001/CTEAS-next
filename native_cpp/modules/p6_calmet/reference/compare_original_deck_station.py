#!/usr/bin/env python3
"""Read-only source-subsection oracle for original CALMET READCF station geometry.

Extract actual REAL*4 arithmetic lines from vendor calmet.for. Compile an
independent Fortran driver with those lines unchanged, and check the frozen
SS1/US1 records' bit patterns. This is selected-source input parity, not
a full original CALMET 143-hour wind-field acceptance claim.
"""
from __future__ import annotations

import argparse
import json
import re
import struct
import subprocess
from pathlib import Path


def extract(lines: list[str], expression: str, after: int = 0) -> str:
    found = [line for i, line in enumerate(lines)
             if i > after and line.strip().lower() == expression.lower()]
    if not found:
        raise AssertionError("original READCF statement absent: " + expression)
    return found[0]


def deck_value(deck: str, key: str) -> float:
    found = re.findall(rf"!\s*{re.escape(key)}\s*=\s*([^!]*)!", deck)
    if len(found) != 1:
        raise AssertionError(f"met.inp {key} non-unique/missing")
    return float(found[0].strip())


def deck_station(deck: str, key: str) -> tuple[int, float, float]:
    found = re.findall(rf"!\s*{re.escape(key)}\s*=\s*'[^']+'\s+([^!]*)!", deck)
    if len(found) != 1:
        raise AssertionError(f"met.inp {key} non-unique/missing")
    values = found[0].split()
    return int(values[0]), float(values[1]), float(values[2])


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--vendor", required=True, type=Path)
    p.add_argument("--deck", required=True, type=Path)
    p.add_argument("--out", required=True, type=Path)
    p.add_argument("--compiler", default="gfortran")
    a = p.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    lines = a.vendor.read_text(encoding="latin-1").splitlines()
    # Frozen source CALMET 6.5.0 L150223 READCF L27073..27188.
    statements = [
        extract(lines, "xorigr = 1000. * xorigkm"),
        extract(lines, "yorigr = 1000. * yorigkm"),
        extract(lines, "xssta(i)=1000.*xkm-xorigr"),
        extract(lines, "yssta(i)=1000.*ykm-yorigr"),
        extract(lines, "xusta(i)=1000.*xkm-xorigr"),
        extract(lines, "yusta(i)=1000.*ykm-yorigr"),
    ]
    h = [
        "      program calmet_station_real4_reference",
        "      integer i",
        "      real xorigkm,yorigkm,xorigr,yorigr,xkm,ykm",
        "      real xssta(1),yssta(1),xusta(1),yusta(1)",
        "      read(*,*) xorigkm,yorigkm,xssta(1),yssta(1),",
        "     1          xusta(1),yusta(1)",
        "      i=1",
        statements[0], statements[1],
        "      xkm=xssta(i)",
        "      ykm=yssta(i)",
        statements[2], statements[3],
        "      xkm=xusta(i)",
        "      ykm=yusta(i)",
        statements[4], statements[5],
        "      write(*,'(4(Z8.8,1X))') transfer(xssta(1),0),",
        "     1    transfer(yssta(1),0),transfer(xusta(1),0),",
        "     2    transfer(yusta(1),0)",
        "      end",
    ]
    source = a.out / "original_readcf_station.for"
    source.write_text("\n".join(h) + "\n")
    binary = a.out / "original_readcf_station"
    cp = subprocess.run(
        [a.compiler, "-O0", "-std=legacy", "-ffixed-line-length-none",
         str(source), "-o", str(binary)], text=True, capture_output=True)
    if cp.returncode:
        raise RuntimeError(cp.stderr)
    deck = a.deck.read_text()
    sxid, sx, sy = deck_station(deck, "SS1")
    uxid, ux, uy = deck_station(deck, "US1")
    inp = " ".join(str(n) for n in (
        deck_value(deck,"XORIGKM"), deck_value(deck,"YORIGKM"),
        sx, sy, ux, uy)) + "\n"
    run = subprocess.run([str(binary)], input=inp, text=True, capture_output=True)
    if run.returncode:
        raise RuntimeError(run.stderr)
    fortran_bits = [int(v, 16) for v in run.stdout.strip().split()]
    if len(fortran_bits) != 4:
        raise AssertionError(f"unexpected original output {run.stdout!r}")
    expected_values = (2500.0, 2500.0, 2498.96875, 2503.0)
    expected_bits = [struct.unpack("<I", struct.pack("<f", v))[0]
                     for v in expected_values]
    status = "PASS_ORIGINAL_READCF_REAL4_SOURCE" if fortran_bits == expected_bits else "FAIL"
    report = {"status": status, "station_ids": [sxid, uxid],
              "original_source_lines": statements,
              "real4_hex_fortran": [f"{n:08X}" for n in fortran_bits],
              "real4_hex_expected": [f"{n:08X}" for n in expected_bits],
              "scope": "READCF original literal station relative geometry only; not P6D wind-field parity"}
    (a.out / "result.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    if status != "PASS_ORIGINAL_READCF_REAL4_SOURCE":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
