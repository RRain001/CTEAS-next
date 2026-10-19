#!/usr/bin/env python3
"""Issue #123 D4 user-manual oracle: compare UNMODIFIED original PNPOLY vs C++.

The original CTGPROC source is fetched at runtime from a pinned PUBLIC
repository commit. It is SHA-gated, never bundled in this repo/artifact.
This checks PNPOLY on identical synthetic REAL*4 vertices/points ONLY.
It does not claim full IPTYPE/COASTEXT or production GLCC parity.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import random
from urllib.request import urlopen

SOURCE_SHA = "719abbd2327269bb0377208b3a7a0c74000b878efc756686023bbb2ef932f281"
SOURCE_URL = ("https://raw.githubusercontent.com/RRain001/CTEAS/"
    "dfad99a78ed84d655e21411c9d25eb0d2583bf13/"
    "engine/vendor/src/CTGPROC_v7.0.0_L150211/ctgproc.for")
# Synthetic generator intentionally has no inputs that could be used to
# accidentally select non-Full/source-less production data.
SEED = 12320261019


def extract_original(source: bytes) -> str:
    lines = source.decode("latin-1").splitlines(keepends=True)
    start = next((i for i, line in enumerate(lines)
                  if line.strip().upper() ==
                  "SUBROUTINE PNPOLY (PX,PY,X,Y,N,INOUT)"), None)
    if start is None:
        raise ValueError("ORIGINAL_PNPOLY_SUBROUTINE_MISSING")
    finish = next((i for i in range(start+1, len(lines))
                   if lines[i].strip().upper() == "END"), None)
    if finish is None:
        raise ValueError("ORIGINAL_PNPOLY_END_MISSING")
    return "".join(lines[start:finish+1]) + "\n"


def f32_string(value: float) -> str:
    # Nine decimal significant digits roundtrip any finite IEEE float32.
    return format(value, ".9g")


def synthetic_cases():
    rng = random.Random(SEED)
    boxes = [(0., 0., 10., 10.),
             (533.215, 3942.629, 543.215, 3952.629),
             (0., 0., .03125, .015625)]
    cases = []
    for x0, y0, x1, y1 in boxes:
        v = [(x0,y0),(x1,y0),(x1,y1),(x0,y1),(x0,y0)]
        cx, cy = (x0+x1)/2., (y0+y1)/2.
        points = [
            (cx,cy),(x0-1.,cy),(x1+1.,cy),
            (x0,cy),(x1,cy),(cx,y0),(cx,y1),
            (x0,y0),(x1,y1),(x0,y1),(x1,y0),
            (x0+.0001,cy),(x0-.0001,cy),
            (x1+.0001,cy),(x1-.0001,cy),
        ]
        for _ in range(160):
            points.append((rng.uniform(x0-(x1-x0)/5.,x1+(x1-x0)/5.),
                           rng.uniform(y0-(y1-y0)/5.,y1+(y1-y0)/5.)))
        for x, y in points:
            cases.append((v,x,y))
            # Reverse winding; same polygon, same classification by Fortran.
            if len(cases)%13==0:
                cases.append((list(reversed(v)),x,y))
    return cases


DRIVER = """program pnpoly_driver
  implicit none
  integer,parameter :: max_vertices=1000
  real :: x(max_vertices),y(max_vertices),px,py
  integer :: n,inc,k,j,i,result
  read(*,*,iostat=inc) n
  if (inc /= 0 .or. n < 1 .or. n > 25000) stop 2
  do k=1,n
     read(*,*,iostat=inc) j,px,py
     if (inc /= 0 .or. j < 3 .or. j > max_vertices) stop 3
     do i=1,j
        read(*,*,iostat=inc) x(i),y(i)
        if (inc /= 0) stop 4
     enddo
     call pnpoly(px,py,x,y,j,result)
     write(*,'(I0)') result
  enddo
end program pnpoly_driver
"""


def prepare(out: Path) -> None:
    if out.exists():
        raise ValueError("ORIGINAL_ORACLE_OUTPUT_DIR_ALREADY_EXISTS")
    out.mkdir(parents=True)
    with urlopen(SOURCE_URL,timeout=45) as response:
        source = response.read(1_000_001)
    if len(source)>1_000_000 or hashlib.sha256(source).hexdigest()!=SOURCE_SHA:
        raise ValueError("ORIGINAL_CTGPROC_SOURCE_SHA256_MISMATCH")
    (out / "original_pnpoly.for").write_text(extract_original(source))
    (out / "driver.f90").write_text(DRIVER)
    cases=synthetic_cases()
    with (out / "cases.txt").open("w") as f:
        f.write(str(len(cases))+"\n")
        for points,px,py in cases:
            f.write(f"{len(points)} {f32_string(px)} {f32_string(py)}\n")
            for x,y in points:
                f.write(f"{f32_string(x)} {f32_string(y)}\n")
    (out / "provenance.json").write_text(json.dumps({
       "original_source_sha256":SOURCE_SHA,
       "original_commit":"dfad99a78ed84d655e21411c9d25eb0d2583bf13",
       "source":"ORIGINAL_UNMODIFIED_PNPOLY_EXTRACTED_AT_RUNTIME",
       "case_count":len(cases),
       "seed":SEED,
       "geometry":"SYNTHETIC_ONLY",
       "original_coastext":"NOT_RUN",
       "real_full_coast_pnpoly_parity":"NOT_RUN"
    },indent=2)+"\n")


def compare(out: Path) -> None:
    expected=json.loads((out/"provenance.json").read_text())
    lines=[(out/name).read_text().splitlines() for name in
           ("fortran_results.txt","cpp_results.txt")]
    if len(lines[0])!=expected["case_count"] or len(lines[1])!=len(lines[0]):
        raise ValueError("ORIGINAL_PNPOLY_ORACLE_ROW_COUNT_MISMATCH")
    refs=[int(x) for x in lines[0]]
    native=[int(x) for x in lines[1]]
    if not all(v in (-1,0,1) for v in refs+native):
        raise ValueError("ORIGINAL_PNPOLY_ORACLE_INVALID_CLASS")
    diffs=[i for i,(a,b) in enumerate(zip(refs,native)) if a!=b]
    report={**expected,
      "first_mismatches":[{"zero_based_case":i,"original":refs[i],"cpp":native[i]}
                          for i in diffs[:10]],
      "mismatch_count":len(diffs),
      "fortran_counts":{str(v):refs.count(v) for v in (-1,0,1)},
      "cpp_counts":{str(v):native.count(v) for v in (-1,0,1)},
      "point_classification": "PASS_SYNTHETIC_SAME_INPUT_ORIGINAL_PNPOLY"
         if not diffs else "FAIL_SYNTHETIC_SAME_INPUT_ORIGINAL_PNPOLY",
      "whole_ctgproc_parity":"NOT_RUN",
    }
    (out/"oracle_report.json").write_text(json.dumps(report,indent=2)+"\n")
    if diffs:
        raise ValueError(f"ORIGINAL_PNPOLY_EXACT_CLASS_MISMATCH:{len(diffs)}")
    print(json.dumps({"status":report["point_classification"],
                      "cases":len(refs),"mismatch_count":0,
                      "original_full_ctgproc_parity":"NOT_RUN"},sort_keys=True))


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("mode",choices=("prepare","compare"))
    p.add_argument("--out",type=Path,required=True)
    args=p.parse_args()
    if args.mode=="prepare":prepare(args.out)
    else:compare(args.out)
