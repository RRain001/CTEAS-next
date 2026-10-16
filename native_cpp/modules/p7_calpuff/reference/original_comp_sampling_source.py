#!/usr/bin/env python3
"""Read-only vendor COMP sampling-order print. This is NOT numerical parity."""
from __future__ import annotations
import hashlib, pathlib, re, sys
EXPECTED="da40372cab1c181158d0ee5faac16f678e876fc14415073c38c8e3bdabfbc568"
def main():
    path=pathlib.Path(sys.argv[1])
    raw=path.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=EXPECTED:
        raise SystemExit("P7 original CALPUFF source changed unexpectedly")
    lines=raw.decode("latin-1").splitlines()
    for name,lo,hi in [
        ("COMP_OLD_CADENCE",10115,10162),
        ("COMP_NEW_CADENCE",10163,10230),
        ("COMP_NEW_CADENCE_CONTINUED",10231,10353),
        ("COMP_KSAM_TLEFT_SCHEDULER",10354,10444),
        ("COMP_ACTUAL_SUBSTEP",10445,10598),
        ("COMP_SUBSTEP_STATE",10600,10765),
        ("COMP_STEPUF_PHASE",10895,10980),
        ("COMP_HOUR_END",11340,11480),
        ("COMP_PUFF_OFFGRID_AND_CLEANUP",11400,11558),
        ("POINTS1_ROLLDN_SWAP_CALLS",15978,16036),
        ("VENDOR_ROLLDN_AND_SWAP",19095,19354),
    ]:
        print(f"P7_ORIGINAL_{name} BEGIN L{lo}-L{hi}")
        for i in range(lo-1,hi):
            print(f"{i+1:6d} {lines[i]}")
        print(f"P7_ORIGINAL_{name} END")
    for term in ("CALL SWAP(", "CALL ROLLDN(", "SUBROUTINE ROLLDN(", "SUBROUTINE SWAP("):
        sites=[i+1 for i,l in enumerate(lines) if term in l.upper()]
        print(f"P7_ORIGINAL_FIND {term} LINES={sites[:45]}")
    print("P7_COMP_ORIGINAL_SOURCE_SHA=PASS")
    print("P7_COMP_MXSAM99_NATIVE_PHYSICS=NOT_YET_ACCEPTED")
if __name__=="__main__": main()
