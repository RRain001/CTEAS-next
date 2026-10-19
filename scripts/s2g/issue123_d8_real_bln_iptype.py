#!/usr/bin/env python3
"""Issue #123 D8: SHA-audited authentic original BLN, exact original Fortran
COASTRD/IPTYPE/PNPOLY vs independently compiled native C++ IPTYPE.

Original Fortran source and extracted BLN remain ephemeral in Actions.
Only provenance, counts and bounded mismatches may be uploaded.
D8 does not establish original GLCC HITS or LU.DAT parity.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import random
import re
import struct
import sys

from scripts.s2g.issue123_original_coastext_wolsong import (
    SOURCE_SHA, GRID, sha, parse_bln, VERTEX, BLN_HEADER,
)

MAX_POINTS = 100_000
SEED = 12320261020
D6_STATUS = "D6B_GNU_SPLIT_IO_EOF_ADAPTED_ORIGINAL_COASTEXT_GENERATED_BLN_SCOPED"


def f32(value: float) -> float:
    return struct.unpack("<f", struct.pack("<f", value))[0]


def ulp_neighbor(value: float, increment: int) -> float:
    """Move a finite positive IEEE REAL*4 coordinate by one adjacent float."""
    bits = struct.unpack("<I", struct.pack("<f", f32(value)))[0]
    out = struct.unpack("<f", struct.pack("<I", bits + increment))[0]
    if not math.isfinite(out):
        raise ValueError("D8_NONFINITE_ULP")
    return out


def source_subroutine(source: str, start: str) -> str:
    lines = source.splitlines(keepends=True)
    matcher = re.compile(start, flags=re.IGNORECASE)
    starts = [i for i, line in enumerate(lines) if matcher.fullmatch(line.rstrip("\r\n"))]
    if len(starts) != 1:
        raise ValueError("D8_ORIGINAL_ROUTINE_UNIQUE_ANCHOR:" + start)
    stop = next((j for j in range(starts[0]+1, len(lines))
                 if re.fullmatch(r"\s*end\s*", lines[j], re.IGNORECASE)), None)
    if stop is None:
        raise ValueError("D8_ORIGINAL_ROUTINE_NO_END")
    return "".join(lines[starts[0]:stop+1]).rstrip("\r\n") + "\n"


def extract_original(source_path: Path, out: Path) -> None:
    if sha(source_path) != SOURCE_SHA:
        raise ValueError("D8_ORIGINAL_VENDOR_SHA_DRIFT")
    text = source_path.read_bytes().decode("latin-1")
    original = "".join([
        source_subroutine(text, r"\s*subroutine\s+coastrd\s*"),
        source_subroutine(text, r"\s*integer\s+function\s+iptype\s*\(\s*px\s*,\s*py\s*\)\s*"),
        source_subroutine(text, r"\s*subroutine\s+pnpoly\s*\(\s*px\s*,\s*py\s*,\s*x\s*,\s*y\s*,\s*n\s*,\s*inout\s*\)\s*"),
    ])
    (out / "original_d8_routines.for").write_text(original, encoding="latin-1")


# Driver contains only initialization, input/output and fail-closed I/O.
# The original three computational subroutines are extracted unmodified.
# OPEN_ERR is a negative-path external dependency of COASTRD; it must fail.
FORTRAN_DRIVER = """      program d8_driver
      include 'params.ctg'
      include 'control.ctg'
      include 'shores.ctg'
      include 'filnam.ctg'
      include 'grid.ctg'
      integer n,i,ios,iptype
      real px,py
      external iptype
      lcoast=.true.
      coastbln='coast.bln'
      xllk=533.215
      yllk=3942.629
      xurk=553.215
      yurk=3962.629
      do i=1,mxcoast
        pxmin(i)=1.0e30
        pymin(i)=1.0e30
        pxmax(i)=-1.0e30
        pymax(i)=-1.0e30
      enddo
      call coastrd
      if(nshore.lt.1.or.nshore.gt.mxcoast) stop 11
      read(*,*,iostat=ios) n
      if(ios.ne.0.or.n.lt.1.or.n.gt.100000) stop 12
      do i=1,n
        read(*,*,iostat=ios) px,py
        if(ios.ne.0) stop 13
        write(*,'(I0)') iptype(px,py)
      enddo
      read(*,*,iostat=ios) px,py
      if(ios.eq.0) stop 14
      end

      subroutine open_err(iunit,origin,descr,filename,fileno)
      character*(*) origin,descr,filename
      write(*,*) 'D8_COASTRD_OPEN_ERROR'
      stop 15
      end
"""


def make_points(bln: Path) -> list[tuple[float,float]]:
    """Wolsong complete 200x200 grid centers + authentic BLN vertices,
    immediate REAL4 neighbors, segment midpoints and seeded local probes.
    These are IDENTICAL supplied points to both programs; they are NOT
    asserted to be original GLAZAS source sample coordinates.
    """
    points: list[tuple[float,float]] = []
    x0, y0, dx = map(f32, (float(GRID["xrefkm"]),
                           float(GRID["yrefkm"]), float(GRID["dgridkm"])))
    for j in range(200):
        for i in range(200):
            points.append((f32(x0 + f32((i + 0.5) * dx)),
                           f32(y0 + f32((j + 0.5) * dx))))
    polygon: list[tuple[float,float]] = []
    with bln.open(encoding="utf-8") as stream:
        while header := stream.readline():
            match = BLN_HEADER.fullmatch(header.rstrip("\r\n"))
            if not match:
                raise ValueError("D8_BLN_BAD_HEADER")
            count = int(match.group(1))
            polygon = []
            for _ in range(count):
                line = stream.readline()
                match_v = VERTEX.fullmatch(line.rstrip("\r\n"))
                if match_v is None:
                    raise ValueError("D8_BLN_BAD_VERTEX")
                x,y = (f32(float(s)) for s in match_v.groups())
                polygon.append((x,y))
                points.extend([(x,y),(ulp_neighbor(x,-1),y),
                               (ulp_neighbor(x,1),y),(x,ulp_neighbor(y,-1)),
                               (x,ulp_neighbor(y,1))])
            for (ax,ay),(bx,by) in zip(polygon, polygon[1:]):
                points.append((f32((ax+bx)*f32(0.5)),
                               f32((ay+by)*f32(0.5))))
    rng = random.Random(SEED)
    for _ in range(2048):
        points.append((f32(533.215 + 20.0*rng.random()),
                       f32(3942.629 + 20.0*rng.random())))
    if not 40_000 <= len(points) <= MAX_POINTS:
        raise ValueError("D8_POINT_COUNT_BUDGET")
    return points


def prepare(out: Path, original_source: Path, bln: Path) -> dict:
    if out.exists() or out.is_symlink():
        raise ValueError("D8_OUTPUT_COLLISION")
    base = bln.parent
    report_path = base / "original_coastext_report.json"
    if not report_path.is_file() or report_path.is_symlink():
        raise ValueError("D8_NO_ACCEPTED_D6_ORIGINAL_REPORT")
    audit = json.loads(report_path.read_text())
    if (audit.get("status") != D6_STATUS or
        audit.get("original_source_sha256") != SOURCE_SHA or
        audit.get("original_coastext_bln") != "PASS_ORIGINAL_OUTPUT_PRESENT" or
        audit.get("original_bln_sha256") != sha(bln) or
        audit.get("original_bln_size_bytes") != bln.stat().st_size):
        raise ValueError("D8_D6_SHA_OR_REPORT_INVALID")
    fresh = parse_bln(bln)
    if (fresh["original_bln_sha256"] != audit["original_bln_sha256"] or
        fresh["polygons"] != audit["polygons"] or
        fresh["vertices"] != audit["vertices"]):
        raise ValueError("D8_INDEPENDENT_BLN_AUDIT_DRIFT")
    if sha(original_source) != SOURCE_SHA:
        raise ValueError("D8_VENDOR_SOURCE_SHA_DRIFT")
    out.mkdir(parents=True)
    extract_original(original_source, out)
    (out / "d8_driver.for").write_text(FORTRAN_DRIVER)
    points = make_points(bln)
    with (out / "points.txt").open("w") as handle:
        handle.write(str(len(points))+"\n")
        for x,y in points:
            handle.write(f"{x:.9g} {y:.9g}\n")
    provenance = {
        "status":"D8_REAL_BLN_SAME_INPUT_READY",
        "original_source_sha256":SOURCE_SHA,
        "original_bln_sha256":fresh["original_bln_sha256"],
        "original_bln_polygons":fresh["polygons"],
        "original_bln_vertices":fresh["vertices"],
        "original_bln_classes":fresh["classes"],
        "point_count":len(points),
        "points_sha256":sha(out / "points.txt"),
        "original_routines_sha256":sha(out / "original_d8_routines.for"),
        "driver_sha256":sha(out / "d8_driver.for"),
        "mesh_scope":"200x200_GRID_CENTERS_AND_REAL_BLN_EDGES_PLUS_SEEDED_PROBES",
        "actual_glazas_source_mesh_parity":"NOT_RUN",
        "original_hits_lu_parity":"NOT_RUN",
        "seed":SEED,
        "vendor_runtime":"GNU_SPLIT_IO_EOF_ADAPTED_SOURCE_FOR_D6_ONLY",
    }
    (out / "d8_provenance.json").write_text(json.dumps(provenance,indent=2)+"\n")
    return provenance


def compare(out: Path) -> dict:
    provenance = json.loads((out / "d8_provenance.json").read_text())
    if provenance.get("status") != "D8_REAL_BLN_SAME_INPUT_READY":
        raise ValueError("D8_NOT_PREPARED")
    if sha(out / "points.txt") != provenance["points_sha256"]:
        raise ValueError("D8_SAME_POINTS_SHA_DRIFT")
    original = (out / "fortran_classes.txt").read_text().splitlines()
    cpp = (out / "cpp_classes.txt").read_text().splitlines()
    if len(original) != provenance["point_count"] or len(cpp) != len(original):
        raise ValueError("D8_OUTPUT_ROW_COUNT_MISMATCH")
    try:
        a,b = [int(s) for s in original],[int(s) for s in cpp]
    except ValueError as exc:
        raise ValueError("D8_NON_INTEGER_CLASS") from exc
    if any(s not in (0,1,2,3,4) for s in a+b):
        raise ValueError("D8_INVALID_IPTYPE_CLASS")
    diff = [i for i,(x,y) in enumerate(zip(a,b)) if x!=y]
    report = {
        **provenance,
        "status": "D8_REAL_ORIGINAL_BLN_IPTYPE_ZERO_MISMATCH_PASS_SCOPED"
                  if not diff else "D8_REAL_ORIGINAL_BLN_IPTYPE_MISMATCH",
        "mismatch_count":len(diff),
        "original_counts":dict(Counter(a)),
        "cpp_counts":dict(Counter(b)),
        "first_20_mismatches":[{"point_index":i,"fortran":a[i],"cpp":b[i]}
                               for i in diff[:20]],
    }
    (out / "d8_iptype_report.json").write_text(json.dumps(report,indent=2)+"\n")
    if diff:
        raise ValueError(f"D8_ORIGINAL_IPTYPE_CLASS_MISMATCH:{len(diff)}")
    return report


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("mode", choices=("prepare","compare"))
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--original-source", type=Path)
    p.add_argument("--bln", type=Path)
    args = p.parse_args()
    try:
        if args.mode == "prepare":
            if args.original_source is None or args.bln is None:
                raise ValueError("D8_MISSING_REAL_ORIGINAL_SOURCE_OR_BLN")
            report = prepare(args.out,args.original_source,args.bln)
        else:
            report = compare(args.out)
        print(json.dumps({k:report[k] for k in
              ("status","point_count") if k in report},sort_keys=True))
    except (OSError,ValueError,KeyError,OverflowError) as exc:
        print(f"D8_FAIL_CLOSED:{type(exc).__name__}:{str(exc)[:200]}",
              file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
