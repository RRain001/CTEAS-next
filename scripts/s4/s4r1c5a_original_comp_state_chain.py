#!/usr/bin/env python3
"""S4-R1c5a: independent original CALMET six-hour actual ZI/ZICONV handoff.

Trace the *real* Fortran COMP state at the boundary immediately BEFORE
DIAGNO and AFTER MIXHT+AVEMIX, in a SHA-verified disposable vendor copy.
No original field is input to native C++ or P6F in this workflow.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from pathlib import Path
import subprocess

BLOB = "437f43bb7f0e51a1919e56664663e1a046986ed0"
TRACE = "s4r1c5a-original-six-hour-zi-ziconv.txt"
NX, NY, HOURS = 82, 85, 6

def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def source_lines(path: Path) -> list[str]:
    digest = subprocess.run(
        ["git", "hash-object", str(path)], capture_output=True, text=True,
        check=True).stdout.strip()
    if digest != BLOB:
        raise ValueError("Unapproved original CALMET Fortran source blob: " + digest)
    rows = path.read_text().splitlines()
    anchors = {
        4511: "      call diagno(nhrze,nhrind,gamma,um,vm,nowsta,zowsta,",
        4715: "         call avemix(nx,ny,mnmdav,hafang,dgrid,u(1,1,ilevzi),",
        4717: "      endif",
        4719: "c",
    }
    for ln, expected in anchors.items():
        if rows[ln - 1] != expected:
            raise ValueError(f"Original COMP source anchor {ln} drifted")
    if any(line.strip().startswith(("9884 ", "9885 ")) for line in rows):
        raise ValueError("Original Fortran scratch FORMAT label collision")
    return rows

def patch(vendor: Path, dest: Path, receipt: Path) -> None:
    rows = source_lines(vendor)
    # In original COMP, ZICONV is NEVER written before DIAGNO call;
    # DIAGNO's prior committed field and post-MIXHT/AVEMIX field are
    # recorded separately, using true current model ending hour NHRZE.
    def instrument(stage: int) -> list[str]:
        label = 9883 + stage
        return [
            f"      open(unit=95,file='{TRACE}',",
            "     1     status='unknown',position='append',action='write')",
            "      do j=1,ny",
            "      do i=1,nx",
            f"      write(95,{label}) nhrze,{stage},i,j,zi(i,j),ziconv(i,j)",
            "      enddo",
            "      enddo",
            f" {label} format(4(i6,1x),2(es23.15,1x))",
            "      close(unit=95)",
        ]
    injected = []
    for ln, row in enumerate(rows, start=1):
        if ln == 4511:
            injected.extend(instrument(1))
        if ln == 4719:
            injected.extend(instrument(2))
        injected.append(row)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text("\n".join(injected) + "\n")
    receipt.parent.mkdir(parents=True, exist_ok=True)
    receipt.write_text(json.dumps({
        "status": "R1C5A_UNMODIFIED_VENDOR_COMP_STATE_WRITEONLY",
        "original_blob": BLOB, "original_sha256": sha(vendor),
        "scratch_sha256": sha(dest), "injected_original_line_before": [4511, 4719],
        "only_scratch_patched": True,
        "full_native_G21_sixhour": "NOT_ACCEPTED",
    }, indent=2, sort_keys=True) + "\n")
    print("S4R1C5A_SHA_PINNED_SOURCE_STAGE_INSTRUMENT=PASS")

def check_trace(path: Path) -> dict:
    before = {}
    after = {}
    parsed = 0
    with path.open() as f:
        for line in f:
            vals = line.strip().split()
            if len(vals) != 6:
                raise ValueError(f"Malformed COMP state row {parsed}: {vals!r}")
            hour, stage, i, j = map(int, vals[:4])
            if hour not in range(2, 8) or stage not in (1, 2) or not (
                1 <= i <= NX and 1 <= j <= NY
            ):
                raise ValueError(f"Unexpected COMP hour/stage/cell {vals[:4]}")
            z, ziconv = (float(v.replace("D", "E")) for v in vals[4:])
            # Original first-hour PRE-COMP ZI is not an accepted initial
            # condition; it is not a numerical comparison reference.
            if not math.isfinite(ziconv) or not math.isfinite(z):
                raise ValueError("Non-finite original COMP state")
            key = hour, i, j
            bucket = before if stage == 1 else after
            if key in bucket:
                raise ValueError(f"Duplicate hour/stage/gridcell {key}")
            bucket[key] = z, ziconv
            parsed += 1
    n = NX * NY * HOURS
    if len(before) != n or len(after) != n or parsed != n * 2:
        raise ValueError(f"Incomplete real original COMP state rows {len(before)}+{len(after)}")
    maxerr = {"ziconv": [0.0, None], "zi": [0.0, None]}
    changed = {"ziconv": 0, "zi": 0}
    nonzero_hour = {}
    for h in range(2, 8):
        nonzero_hour[str(h)] = {
            "pre_ziconv_positive": sum(before[h, i, j][1] > 0
                for i in range(1, NX + 1) for j in range(1, NY + 1)),
            "post_ziconv_positive": sum(after[h, i, j][1] > 0
                for i in range(1, NX + 1) for j in range(1, NY + 1)),
            "post_zi_positive": sum(after[h, i, j][0] > 0
                for i in range(1, NX + 1) for j in range(1, NY + 1)),
        }
        if h == 2:
            continue
        for i in range(1, NX + 1):
            for j in range(1, NY + 1):
                prev = after[h - 1, i, j]
                current = before[h, i, j]
                for k, label in enumerate(("zi", "ziconv")):
                    err = abs(current[k] - prev[k])
                    if err:
                        changed[label] += 1
                    if err > maxerr[label][0]:
                        maxerr[label] = [err, [h, i, j]]
    return {
        "original_6_hour_stage_rows": parsed,
        "source_pair_count": NX * NY * (HOURS - 1),
        "original_prev_hour_to_pre_diagno_max_abs_residual": maxerr,
        "changed_prev_hour_to_next_hour_cells": changed,
        "original_nonzero_cells_per_hour": nonzero_hour,
    }

def verify(vendor: Path, original_met: Path, scratch_met: Path,
           original_trace: Path, output: Path) -> None:
    source_lines(vendor)
    if sha(original_met) != sha(scratch_met):
        raise ValueError("Scratch original 6h x 45 CALMET.DAT mutated")
    result = check_trace(original_trace)
    maxima = result["original_prev_hour_to_pre_diagno_max_abs_residual"]
    # Both arrays are original COMP COMMON state, not native code.
    # They must be unchanged at the immediately following pre-DIAGNO.
    # An observed difference must remain a SCIENCE BLOCKER, not an excuse
    # to inject either original state into C++.
    ok = maxima["zi"][0] == 0 and maxima["ziconv"][0] == 0
    result.update({
        "status": "PASS_ORIGINAL_REFERENCE_ONLY" if ok else "FAIL_ORIGINAL_STATE_HANDOFF",
        "reference_type": "AUTHENTIC_FORTRAN_COMP_PRE_DIAGNO_POST_MIXHT_AVEMIX",
        "vendor_original_git_blob": BLOB,
        "vendor_original_sha256": sha(vendor),
        "unchanged_original_calmet_6h_45_field_sha256": sha(original_met),
        "unchanged_original_calmet_byte_identical": True,
        "hour_ends_utc": [
            "2022-06-01T02:00:00Z", "2022-06-01T03:00:00Z",
            "2022-06-01T04:00:00Z", "2022-06-01T05:00:00Z",
            "2022-06-01T06:00:00Z", "2022-06-01T07:00:00Z"
        ],
        "real_noaa_2ss_1us_82x85_9_layer_water_cells": 63,
        "original_fields_injected_into_native_cpp": False,
        "native_previous_zi_ziconv_sixhour": "NOT_RUN",
        "native_g21_g39_sixhour": "NOT_RUN",
        "native_g24_g26_p7": "NOT_ACCEPTED",
    })
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print("S4R1C5A_ORIGINAL_SIX_HOUR_COMP_STATE_HANDOFF", result["status"])
    print("S4R1C5A_ORIGINAL_MAX_PREPOST", json.dumps(maxima, sort_keys=True))
    if not ok:
        raise ValueError("Original COMP internal ZI/ZICONV temporal state chain is not direct; diagnose actual intervening write")
    print("S4R1C5A_TRUE_NOAA_ORIGINAL_STATE_HISTORY=PASS_REFERENCE_ONLY")
    print("S4R1C5A_NATIVE_6H_ZICONV_G21_G24_G26=NOT_ACCEPTED")

def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="command", required=True)
    a = sub.add_parser("prepare")
    for key in ("vendor", "dest", "receipt"):
        a.add_argument("--" + key, type=Path, required=True)
    v = sub.add_parser("verify")
    for key in ("vendor", "original-met", "scratch-met", "original-trace", "report"):
        v.add_argument("--" + key, type=Path, required=True)
    x = p.parse_args()
    if x.command == "prepare":
        patch(x.vendor, x.dest, x.receipt)
    else:
        verify(x.vendor, x.original_met, x.scratch_met, x.original_trace, x.report)
if __name__ == "__main__":
    main()
