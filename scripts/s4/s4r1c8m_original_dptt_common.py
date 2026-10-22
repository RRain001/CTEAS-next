#!/usr/bin/env python3
"""S4-R1c8m: SHA-pinned real NOAA six-hour original /tjump/ DPTT audit.

Original CALMET physics is untouched. A disposable source copy receives
only a COMMON declaration in COMP and write-only pre-DIAGNO/post-AVEMIX
DPTT snapshots. The native G54 candidate is computed WITHOUT access to
these snapshots. No six-hour native G14 or G26/P7 admission.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import struct
import subprocess
import tempfile
from pathlib import Path

BLOB = "437f43bb7f0e51a1919e56664663e1a046986ed0"
NX, NY, NC, NH = 82, 85, 82 * 85, 6
TRACE = "s4r1c8m-original-dptt-common.bin"
HEAD = struct.Struct("<5i")
PLANE = struct.Struct("<" + str(NC) + "f")
ROW = HEAD.size + PLANE.size
FIVE = struct.Struct("<" + str(5*NC) + "f")
ABS_DPTT_K = 5e-3
REL_DPTT = 5e-5
ANCHORS = {
    3608: "      include 'params.met'",
    3609: "c",
    3610: "      real ziconv(mxnx,mxny)",
    4511: "      call diagno(nhrze,nhrind,gamma,um,vm,nowsta,zowsta,",
    4717: "      endif",
    4719: "c",
}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source(path: Path) -> list[str]:
    digest = subprocess.run(
        ["git", "hash-object", str(path)], text=True,
        capture_output=True, check=True
    ).stdout.strip()
    if digest != BLOB:
        raise ValueError("G61 immutable original CALMET source blob drift")
    lines = path.read_text().splitlines(keepends=True)
    for index, value in ANCHORS.items():
        if lines[index-1].rstrip("\r\n") != value:
            raise ValueError(f"G61 original CALMET pinned L{index} changed")
    if "      common /tjump/ dptt(mxnx,mxny)" not in lines[1744]:
        raise ValueError("G61 genuine source BLOCK DATA /tjump/ declaration changed")
    return lines


def snapshot(stage: int) -> str:
    return (
        f"      open(unit=91,file='{TRACE}',\n"
        "     1 form='unformatted',access='stream',status='unknown',\n"
        "     2 position='append')\n"
        f"      write(91) 61,nhrze,{stage},nx,ny\n"
        "      write(91) ((dptt(i,j),i=1,nx),j=1,ny)\n"
        "      close(unit=91)\n"
    )


def prepare(vendor: Path, destination: Path, receipt: Path) -> None:
    lines = source(vendor)
    # COMP does not itself declare /tjump/; the SAME COMMON is present
    # in BLOCK DATA and MIXHT. Bring it into scope without modifying
    # one physical statement or assigning a DPTT value.
    additions = {
        3610: "      common /tjump/ dptt(mxnx,mxny)\n",
        4511: snapshot(1),  # before DIAGNO sees previous common
        4719: snapshot(2),  # after true COMP LAND MIXHT + AVEMIX
    }
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text("".join(
        additions.get(n, "") + row for n, row in enumerate(lines, 1)
    ))
    receipt.parent.mkdir(parents=True, exist_ok=True)
    receipt.write_text(json.dumps({
        "status": "PREPARED_SHA_PINNED_WRITE_ONLY_DPTT_COMMON",
        "vendor_git_blob": BLOB, "vendor_sha256": sha(vendor),
        "scratch_sha256": sha(destination),
        "only_inserted_common_declaration": True,
        "physical_statements_changed": False,
        "trace_before_original_lines": [4511, 4719],
        "native_dptt_accepted": False,
    }, indent=2, sort_keys=True)+"\n")
    print("S4R1C8M_ORIGINAL_DPTT_SOURCE_PIN=PASS")


def decode(path: Path):
    data = path.read_bytes()
    if len(data) != NH*2*ROW:
        raise ValueError("G61 sixhour two-stage source DPTT trace extent changed")
    result = {}
    for h in range(2, 8):
        for stage in (1, 2):
            offset = ((h-2)*2 + stage-1)*ROW
            header = HEAD.unpack_from(data, offset)
            if header != (61, h, stage, NX, NY):
                raise ValueError(f"G61 original source DPTT clock/stage drift {header}")
            values = PLANE.unpack_from(data, offset+HEAD.size)
            if not all(math.isfinite(v) and abs(v) < 1000 for v in values):
                raise ValueError("G61 original DPTT COMMON nonphysical source values")
            result[h, stage] = values
    return result


def check_handoff(data) -> dict:
    # DPTT is a persistent /tjump/ COMMON, rather than output record
    # or ZICONV. Check actual previous POST -> next PRE without
    # assuming nonzero/calm/tiny constants.
    differs = 0
    worst = None
    for h in range(3, 8):
        before = data[h, 1]
        after = data[h-1, 2]
        for idx, (current, prev) in enumerate(zip(before, after, strict=True)):
            if struct.pack("<f", current) != struct.pack("<f", prev):
                differs += 1
                if worst is None:
                    worst = {"hour": h, "i": idx%NX+1, "j": idx//NX+1,
                             "previous_post": prev, "current_pre": current}
    return {
        "source_six_hours": list(range(2, 8)),
        "source_pre_post_stage_pairs": NH*NC,
        "source_handoff_comparisons": (NH-1)*NC,
        "source_handoff_nonidentical_cells": differs,
        "first_source_handoff_difference": worst,
        "per_hour_dptt_nonzero_after_comp": {
            str(h): sum(x != 0.0 for x in data[h, 2]) for h in range(2, 8)
        },
        "per_hour_post_dptt_min_k": {
            str(h): min(data[h, 2]) for h in range(2, 8)
        },
        "per_hour_post_dptt_max_k": {
            str(h): max(data[h, 2]) for h in range(2, 8)
        },
    }


def verify(vendor: Path, pristine: Path, scratch: Path,
           trace: Path, report: Path) -> None:
    source(vendor)
    if sha(pristine) != sha(scratch):
        raise ValueError("G61 DPTT scratch original changed the 6h x45 MET")
    states = decode(trace)
    receipt = check_handoff(states)
    ok = receipt["source_handoff_nonidentical_cells"] == 0
    full = {
        "status": ("PASS_SOURCE_ORIGINAL_SIXHOUR_DPTT_COMMON_HANDOFF"
                   if ok else "FAIL_SOURCE_ORIGINAL_DPTT_HANDOFF"),
        "original_vendor_git_blob": BLOB,
        "original_vendor_sha256": sha(vendor),
        "original_pristine_sixhour_met_sha256": sha(pristine),
        "original_scratch_sixhour_met_sha256": sha(scratch),
        "original_sixhour_45_met_byte_identical": True,
        "original_dptt_trace_sha256": sha(trace),
        "physical_fortran_equations_changed": False,
        "original_values_in_native_forcing": False,
        "native_dptt_original_parity": "NOT_RUN",
        "native_g14_sixhour_causal": "NOT_ACCEPTED",
        "g26_p7": "NOT_ACCEPTED",
        **receipt,
    }
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(full, sort_keys=True, indent=2)+"\n")
    print("S4R1C8M_ORIGINAL_6H_DPTT=" + full["status"])
    print("S4R1C8M_ORIGINAL_DPTT_HANDOFF_NONIDENTICAL="+str(
        receipt["source_handoff_nonidentical_cells"]))
    print("S4R1C8M_ORIGINAL_6H45_MET=BYTE_IDENTICAL")
    print("S4R1C8M_NATIVE_G14_G26_P7=NOT_ACCEPTED")
    if not ok:
        raise ValueError("G61 original source DPTT temporal COMMON handoff changed")


def compare_arrays(original, native) -> dict:
    if len(original) != NC or len(native) != NC:
        raise ValueError("G61 original/native DPTT array incomplete")
    residual_max, above, worst = 0.0, 0, None
    first = []
    for i, (o, n) in enumerate(zip(original, native, strict=True)):
        if not all(math.isfinite(v) and abs(v) < 1000 for v in (o, n)):
            raise ValueError("G61 nonphysical native/original DPTT value")
        residual = abs(o-n)
        if residual > residual_max:
            residual_max = residual
            worst = {"i": i%NX+1, "j": i//NX+1,
                     "original_dptt_k": o, "native_dptt_k": n,
                     "abs_error_k": residual}
        if residual > ABS_DPTT_K+REL_DPTT*max(abs(o), abs(n)):
            above += 1
            if len(first) < 16:
                first.append({"i": i%NX+1, "j": i//NX+1,
                              "original": o, "native": n,
                              "error_k": residual})
    return {"source_native_dptt_compared": NC,
            "source_native_above_frozen_tolerance": above,
            "frozen_abs_dptt_tolerance_k": ABS_DPTT_K,
            "frozen_rel_dptt_tolerance": REL_DPTT,
            "max_abs_dptt_error_k": residual_max,
            "worst_dptt": worst, "first_exceedances": first,
            "native_firsthour_dptt_nonzero": sum(x != 0 for x in native),
            "original_firsthour_dptt_nonzero": sum(x != 0 for x in original)}


def compare(original_trace: Path, original_receipt: Path, original_met: Path,
            native_g54: Path, native_g54_receipt: Path,
            g60_receipt: Path, report: Path) -> bool:
    r = json.loads(original_receipt.read_text())
    g = json.loads(native_g54_receipt.read_text())
    h = json.loads(g60_receipt.read_text())
    if (r.get("status") != "PASS_SOURCE_ORIGINAL_SIXHOUR_DPTT_COMMON_HANDOFF"
        or r.get("original_dptt_trace_sha256") != sha(original_trace)
        or r.get("original_pristine_sixhour_met_sha256") != sha(original_met)
        or r.get("original_sixhour_45_met_byte_identical") is not True
        or r.get("source_handoff_nonidentical_cells") != 0
        or r.get("original_vendor_git_blob") != BLOB
        or g.get("status") != "PASS_SCOPED_REAL_NOAA_NATIVE_MIXHT_AND_AVEMIX"
        or g.get("native_source_only_candidate_sha256") != sha(native_g54)
        or g.get("above_frozen_tolerance") != 0
        or h.get("status") !=
            "PASS_SOURCE_SCOPED_FIRSTHOUR_NATIVE_COMP_MEMORY_ZI_ZICONV"
        or h.get("native_g54_memory_sha256") != sha(native_g54)
        or h.get("original_6h45_met_sha256") != sha(original_met)
        or h.get("above_frozen_tolerance") != 0):
        raise ValueError("G61 original/native independent source receipts absent/stale")
    if native_g54.stat().st_size != FIVE.size:
        raise ValueError("G61 native G54 five memory plane extent drift")
    source_states = decode(original_trace)
    actual_dptt = source_states[2, 2]
    physical = FIVE.unpack(native_g54.read_bytes())
    calculated_dptt = physical[4*NC:5*NC]
    measured = compare_arrays(actual_dptt, calculated_dptt)
    ok = measured["source_native_above_frozen_tolerance"] == 0
    result = {
        "status": ("PASS_FIRSTHOUR_SOURCE_NATIVE_DPTT_COMMON_PARITY"
                   if ok else "FAIL_FIRSTHOUR_SOURCE_NATIVE_DPTT_COMMON_PARITY"),
        "scope": "REAL_NOAA_2SS1US_82x85_9L_FIRSTHOUR_ONLY",
        "source_original_6hour_trace_sha256": sha(original_trace),
        "source_original_pristine_met_sha256": sha(original_met),
        "native_original_source_only_g54_sha256": sha(native_g54),
        "source_original_sixhour_common_handoff": "PASS_ORIGINAL_ONLY",
        "original_trace_used_as_native_input": False,
        "fortran_physics_changed": False,
        "firsthour_postcomp_g14_transaction": "NOT_ACCEPTED",
        "native_hour_two_to_six_dptt": "NOT_RUN",
        "sixhour_native_g14_p6f": "NOT_ACCEPTED",
        "g26_p7": "NOT_ACCEPTED",
        **measured,
    }
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(result, indent=2, sort_keys=True)+"\n")
    print("S4R1C8M_NATIVE_DPTT=" + result["status"])
    print("S4R1C8M_DPTT_ABOVE_TOLERANCE=" + str(
        measured["source_native_above_frozen_tolerance"]))
    print("S4R1C8M_G14_6H_G26_P7=NOT_ACCEPTED")
    return ok


def selftest() -> None:
    with tempfile.TemporaryDirectory() as d:
        out = Path(d)/TRACE
        with out.open("wb") as f:
            for h in range(2, 8):
                for stage in (1, 2):
                    f.write(HEAD.pack(61, h, stage, NX, NY))
                    f.write(PLANE.pack(*([2.5]*NC)))
        parsed = decode(out)
        passed = check_handoff(parsed)
        assert passed["source_handoff_nonidentical_cells"] == 0
        data = bytearray(out.read_bytes())
        data[8] = 7
        out.write_bytes(data)
        try:
            decode(out)
        except ValueError:
            pass
        else:
            raise AssertionError("G61 accepted forged stage number")
    zeros = [0.0]*NC
    assert compare_arrays(zeros, zeros)["source_native_above_frozen_tolerance"] == 0
    altered = zeros.copy()
    altered[31] = 1
    assert compare_arrays(zeros, altered)["source_native_above_frozen_tolerance"] == 1
    altered[31] = float("nan")
    try:
        compare_arrays(zeros, altered)
    except ValueError:
        pass
    else:
        raise AssertionError("G61 accepted nonfinite native DPTT")
    print("S4R1C8M_ORIGINAL_NATIVE_DPTT_NEGATIVE_TESTS=PASS")


def main() -> None:
    p = argparse.ArgumentParser()
    commands = p.add_subparsers(dest="mode", required=True)
    keys = {
        "prepare": ("vendor", "destination", "receipt"),
        "verify": ("vendor", "pristine", "scratch", "trace", "report"),
        "compare": ("original-trace", "original-receipt", "original-met",
                    "native-g54", "native-g54-receipt", "g60-receipt", "report"),
        "selftest": (),
    }
    for mode, fields in keys.items():
        command = commands.add_parser(mode)
        for field in fields:
            command.add_argument("--"+field, required=True, type=Path)
    args = p.parse_args()
    if args.mode == "prepare":
        prepare(args.vendor, args.destination, args.receipt)
    elif args.mode == "verify":
        verify(args.vendor, args.pristine, args.scratch, args.trace, args.report)
    elif args.mode == "compare":
        if not compare(
            args.original_trace, args.original_receipt, args.original_met,
            args.native_g54, args.native_g54_receipt, args.g60_receipt,
            args.report
        ):
            raise SystemExit(3)
    else:
        selftest()


if __name__ == "__main__":
    main()
