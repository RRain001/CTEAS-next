#!/usr/bin/env python3
"""Unmodified CALMET v6.5.0 AVETMP original-source parity.

Compiles the verbatim AVETMP subroutine extracted from the pinned vendor
calmet.for and compares it with the independent P6E C++20 kernel on
synthetic u/v/temperature fields that exercise the zero-wind fallback, the
+/-MNMDAV square shortcut, the upwind cone, the causal-frontier test and
several grid spacings.
"""
import argparse
import hashlib
import json
import math
import subprocess
import tempfile
from pathlib import Path

BLOB = "437f43bb7f0e51a1919e56664663e1a046986ed0"
CASES = 40
ABS_LIMIT = 1e-4
REL_LIMIT = 1e-5
PARAMS = """      integer mxnx,mxny,io6
      parameter(mxnx=8,mxny=6,io6=6)
"""
DRIVER = """      program avetmp_original_driver
      include 'params.met'
      integer cases,c,nx,ny,mnmdav,i,j
      real hafang,dgrid
      real u(mxnx,mxny),v(mxnx,mxny),zt(mxnx,mxny)
      read(*,*)cases
      do c=1,cases
        read(*,*)nx,ny,mnmdav,hafang,dgrid
        do j=1,ny
          do i=1,nx
            read(*,*)u(i,j),v(i,j),zt(i,j)
          enddo
        enddo
        call avetmp(nx,ny,mnmdav,hafang,dgrid,u,v,zt)
        do j=1,ny
          do i=1,nx
            write(*,'(3(I6,1X),ES23.13E3)')c,i,j,zt(i,j)
          enddo
        enddo
      enddo
      end
"""


def run(command, inp=None):
    return subprocess.run([str(x) for x in command], input=inp, text=True,
                          capture_output=True, check=True).stdout


def extract(raw):
    lines = raw.decode("utf-8").splitlines(keepends=True)
    first = [i for i, v in enumerate(lines)
             if v.lower().startswith("      subroutine avetmp(")]
    last = [i for i, v in enumerate(lines)
            if v.lower().startswith("      subroutine barier(")]
    if len(first) != 1 or len(last) != 1 or not 180 < last[0] - first[0] < 320:
        raise RuntimeError("Unmodified AVETMP bounds changed")
    return "".join(lines[first[0]:last[0]]), [first[0] + 1, last[0]]


def fixture():
    shapes = ((5, 4), (8, 6), (1, 1), (2, 2), (7, 3), (8, 1))
    spacings = (100.0, 1000.0, 10000.0)
    half_angles = (30.0, 45.0, 60.0, 90.0)
    rows = [str(CASES)]
    counts = dict(zero_wind=0, uniform_wind=0, rotating=0, single_hot=0)
    for c in range(CASES):
        nx, ny = shapes[c % len(shapes)]
        mnmdav = 1 + c % 3
        hafang = half_angles[c % len(half_angles)]
        dgrid = spacings[c % len(spacings)]
        rows.append(f"{nx} {ny} {mnmdav} {hafang} {dgrid}")
        mode = c % 4
        counts[("zero_wind", "uniform_wind", "rotating", "single_hot")[mode]] += 1
        for j in range(ny):
            for i in range(nx):
                if mode == 0:
                    u = v = 0.0
                elif mode == 1:
                    u, v = 3.0, -1.5
                elif mode == 2:
                    u = 4.0 * math.cos(0.5 * (i + 1)) + 0.25 * c
                    v = 4.0 * math.sin(0.5 * (j + 1)) - 0.25 * c
                else:
                    u, v = 1.0 + 0.1 * i, 1.0 - 0.1 * j
                temp = 285.0 + 0.5 * ((i + 2 * j + c) % 7)
                if mode == 3 and i == nx // 2 and j == ny // 2:
                    temp = 305.0
                rows.append(f"{u!r} {v!r} {temp!r}")
    return "\n".join(rows) + "\n", counts


def parse(raw):
    values = {}
    for line in raw.splitlines():
        parts = line.split()
        if len(parts) != 4:
            raise RuntimeError("AVETMP comparator schema: " + line)
        case = int(parts[0])
        i = int(parts[1])
        j = int(parts[2])
        value = float(parts[3])
        if not math.isfinite(value):
            raise RuntimeError("nonfinite AVETMP value")
        values[(case, i, j)] = value
    return values


def main():
    parser = argparse.ArgumentParser()
    for flag in ("vendor", "cpp", "out"):
        parser.add_argument("--" + flag, required=True, type=Path)
    parser.add_argument("--gfortran", default="gfortran")
    args = parser.parse_args()
    raw = args.vendor.read_bytes()
    sha = run(["git", "hash-object", args.vendor]).strip()
    if sha != BLOB:
        raise RuntimeError("CALMET original source drift")
    original, loc = extract(raw)
    test, counts = fixture()
    with tempfile.TemporaryDirectory(prefix="cteas-p6e-avetmp-") as work:
        d = Path(work)
        (d / "params.met").write_text(PARAMS)
        (d / "avetmp_original.for").write_text(original)
        (d / "driver.for").write_text(DRIVER)
        run([args.gfortran, "-O0", "-std=legacy", "-fno-automatic",
             "-ffixed-line-length-none", "-I" + str(d),
             d / "avetmp_original.for", d / "driver.for", "-o", d / "original"])
        expected = parse(run([d / "original"], test))
    actual = parse(run([args.cpp], test))
    if len(expected) != len(actual):
        raise RuntimeError("AVETMP output size mismatch")
    largest = 0.0
    bad = 0
    samples = []
    for key in expected:
        a = expected[key]
        b = actual[key]
        error = abs(a - b)
        largest = max(largest, error)
        if error > ABS_LIMIT + REL_LIMIT * abs(a):
            bad += 1
            if len(samples) < 20:
                samples.append({"case": key[0], "i": key[1], "j": key[2],
                                "original": a, "cpp": b, "error": error})
    report = {"status": "PASS" if bad == 0 else "FAIL", "cases": CASES,
              "values": len(expected), "mode_distribution": counts,
              "max_abs_error_k": largest, "abs_limit": ABS_LIMIT,
              "rel_limit": REL_LIMIT, "mismatches": bad,
              "first_mismatches": samples, "original_blob": sha,
              "vendor_sha256": hashlib.sha256(raw).hexdigest(),
              "unmodified_source_lines": loc,
              "scope": "isolated original AVETMP with synthetic u/v; the "
                       "real-case IAVET=1 term still needs the P6D wind field"}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    if bad:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
