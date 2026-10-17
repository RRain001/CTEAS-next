#!/usr/bin/env python3
"""Fail-closed, read-only full DGM scan for COMP FSTEP/TLEFT behavior.

Not a native C++ full-case equivalence test. Original instrumented CALPUFF
must first match the untouched puff.con and pinned full DGM SHA.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import struct
from pathlib import Path

EXPECTED = "cbbdaa29c6222e6ca6aefe9f605ad13e7dd6d258f6ad243afcac07cb578108c6"
RECORD = struct.Struct("<24i64f")
COUNT = 254687
HOURS = 143


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dgm", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    sha = hashlib.sha256()
    seen = set()
    count = 0
    shortened = 0
    duplicate_ksam = 0
    carrying_time = 0
    nonzero_tleft = 0
    first_shortened = None
    first_reentry = None
    previous = None

    with args.dgm.open("rb") as handle:
        while (block := handle.read(RECORD.size)):
            if len(block) != RECORD.size:
                raise SystemExit("P7 original FSTEP DGM truncated record")
            sha.update(block)
            row = RECORD.unpack(block)
            packed, ii, nsam, nsstr, ksam = row[1], row[3], row[10], row[11], row[16]
            cadence, tleft, tsampsum, effective = (
                row[24 + 16], row[24 + 60], row[24 + 61], row[24 + 62]
            )
            if (
                row[0] != 1 or not 1 <= ksam <= nsam <= 99
                or not 1 <= nsstr <= nsam or ii < 1
                or not all(map(math.isfinite, (cadence, tleft, tsampsum, effective)))
                or not 0 < effective <= 3600
                or cadence <= 0
            ):
                raise SystemExit(f"P7 original FSTEP invalid DGM row {count+1}")
            key = (packed, ii, ksam)
            if key == previous:
                duplicate_ksam += 1
                if first_reentry is None:
                    first_reentry = {
                        "record": count + 1, "hour": packed,
                        "puff_slot": ii, "ksam": ksam,
                        "effective_s": effective, "tleft_s": tleft,
                    }
            if effective < cadence - 1.0e-4:
                shortened += 1
                if first_shortened is None:
                    first_shortened = {
                        "record": count + 1, "hour": packed,
                        "puff_slot": ii, "ksam": ksam,
                        "nominal_s": cadence, "effective_s": effective,
                        "wind_ms": row[24 + 11], "tleft_s": tleft,
                    }
            if abs(tleft) > 1.0e-4:
                nonzero_tleft += 1
            if tleft > effective:
                carrying_time += 1
            seen.add(packed)
            previous = key
            count += 1
    digest = sha.hexdigest()
    if digest != EXPECTED or count != COUNT or len(seen) != HOURS:
        raise SystemExit(
            "P7 original FSTEP oracle mismatch: "
            f"sha={digest} count={count} hours={len(seen)}"
        )
    result = {
        "status": "ORIGINAL_DGM_READ_ONLY_AUDIT_PASS",
        "original_sha256": digest, "records": count, "hours": len(seen),
        "steps_shorter_than_nominal": shortened,
        "consecutive_same_ksam_reentries": duplicate_ksam,
        "nonzero_tleft_records": nonzero_tleft,
        "tleft_greater_than_effective_records": carrying_time,
        "first_shortened": first_shortened, "first_reentry": first_reentry,
        "meaning": (
            "This inventories original COMP behavior; it does not establish "
            "autonomous native FSTEP, release, puff trajectory or concentration parity."
        ),
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print("P7_ORIGINAL_143H_FSTEP_FORENSICS=PASS " +
          f"RECORDS={count} HOURS={len(seen)} " +
          f"SHORTENED={shortened} REENTRIES={duplicate_ksam} " +
          f"NONZERO_TLEFT={nonzero_tleft} FIRST_SPLIT={first_shortened} " +
          "NATIVE_FULL_PARITY=NOT_YET_ACCEPTED")


if __name__ == "__main__":
    main()
