#!/usr/bin/env python3
"""Strict original-CALPUFF read-only historical ZIOLD/ZIMAX oracle.

A separate instrumentation of original PUFFDZ records captures exactly 2
REAL*4 arguments per DGM step. This does NOT reconstruct historical ZI in
native C++; it makes all otherwise-incomparable original PUFFDZ branches
numerically testable. Vendor files are never modified.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import struct
import sys

sys.path.insert(0,str(Path(__file__).resolve().parent))
import original_puff_step_dump as base

def main() -> None:
    p=argparse.ArgumentParser()
    p.add_argument("--vendor",required=True,type=Path)
    p.add_argument("--case",required=True,type=Path)
    p.add_argument("--out",required=True,type=Path)
    p.add_argument("--compiler",required=True)
    p.add_argument("--metadata",required=True,type=Path)
    args=p.parse_args()

    # Add a second, write-only stream at exactly the original PUFFDZ return,
    # before ADVECT, RISEWIND, SETPUF or any subsequent state mutation.
    # Every existing DGM field, compiler option and original source SHA pin is
    # preserved by base.audit(). This call is appended AFTER dgmstep3.
    base.CALLS["item3_puffdz_return"] += (
        "         call dgmzi(ziold(ii),zimax(ii))\n"
    )
    base.HELPERS += """
c ---------------------------------------------------------------------
c --- Extra original ZIOLD/ZIMAX two-REAL4 stream (one per PUFFDZ call).
c --- Unit 95 is independent of the unchanged baseline DGM stream (94).
c ---------------------------------------------------------------------
      subroutine dgmzi(zin,zmx)
      real zin,zmx
      logical first
      save first
      data first/.true./
      if(first)then
         open(unit=95,file='dgm_puffdz_zi.bin',
     &        form='unformatted',access='stream',
     &        status='replace')
         first=.false.
      endif
      write(95) zin,zmx
      return
      end
"""
    evidence=base.audit(args)
    if not evidence["puff_con_identical"] or not evidence["puff_con_matches_frozen_reference"]:
        raise RuntimeError("instrumentation changed original frozen puff.con")
    reference=json.loads(args.metadata.read_text())
    expected=reference["binary"]
    dgm=args.out.resolve()/"case"/"run"/"puff"/"dgm_puffstep.bin"
    actual_size=dgm.stat().st_size
    actual_sha=base.sha256_file(dgm)
    if (actual_size!=expected["bytes"] or actual_sha!=expected["sha256"] or
            expected["records"]!=254687 or expected["record_bytes"]!=352):
        raise RuntimeError("original DGM bytes do not match frozen 143-hour baseline")
    extra=dgm.with_name("dgm_puffdz_zi.bin")
    if not extra.is_file() or extra.stat().st_size!=254687*8:
        raise RuntimeError("ZI stream not exactly 2 REAL4 per original substep")
    count=0
    with extra.open("rb") as inp:
        while pair:=inp.read(8):
            if len(pair)!=8:
                raise RuntimeError("misaligned extra REAL4 ZI stream")
            ziold,zimax=struct.unpack("<ff",pair)
            if not math.isfinite(ziold) or not math.isfinite(zimax) or ziold<0 or zimax<0:
                raise RuntimeError(f"non-finite or negative historical ZI at step {count+1}")
            count+=1
    if count!=254687:
        raise RuntimeError("ZI stream row count mismatch")
    # Pinned to the first independent 143h original write-only capture.
    # This is an extra input reference, not a native historical-ZI solution.
    original_zi_sha="3a7e519c91f26c17a649a7292435d37b09beef55f3d5d9765aace777781a14c4"
    actual_zi_sha=base.sha256_file(extra)
    if actual_zi_sha!=original_zi_sha:
        raise RuntimeError(f"original ZI oracle drift: {actual_zi_sha}")
    result={
        "status":"ORIGINAL_PUFFDZ_HISTORICAL_ZI_READ_ONLY_CAPTURED",
        "records":count,
        "raw_zi_bytes":extra.stat().st_size,
        "zi_sha256":base.sha256_file(extra),
        "original_dgm_sha256":actual_sha,
        "original_concentration_sha256":evidence["runs"]["original"]["puff_con_sha256"],
        "instrumented_concentration_sha256":evidence["runs"]["instrumented"]["puff_con_sha256"],
        "proves_native_zi_reconstruction":False,
    }
    (args.out/"puffdz-zi-provenance.json").write_text(json.dumps(result,indent=2)+"\n")
    print("P7_PUFFDZ_ORIGINAL_ZI_CAPTURE=PASS RECORDS=254687"
          " DATA_PAIRS=254687 CONCENTRATION_SHA_UNCHANGED=YES"
          " ORIGINAL_DGM_SHA_UNCHANGED=YES")
    print(json.dumps(result,indent=2))

if __name__=="__main__":
    main()
