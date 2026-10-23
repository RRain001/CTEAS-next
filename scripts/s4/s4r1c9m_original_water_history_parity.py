#!/usr/bin/env python3
"""Read-only original WATER->next DIAGNO USTAR/EL carryover proof.

The original Fortran MET.DAT (post-COMP WATER output) and an independently
instrumented original DIAGNO stage-40 trace are the ONLY operands.
No original output is passed to native C++, no scientific guard is changed,
and a successful report does not claim third-hour native parity.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import struct

from scripts.s4.s4r1c8i_compare_noaa_43_real_p6f import (
    LABELS, NC, NX, NY, NZ, fortran_records,
)
from scripts.s4.s4r1c9l_original_g22_trace import HEADER, STAGE_ARRAYS

PINNED_ORIGINAL_MET_SHA = "a7004fbf780212d58536be3957306c2aecc53abe2e58bfec870571b12d8b8e14"
PINNED_TRACE_SHA = "b6d96dab81af8e9cba89ef55d386aba8082d9136aa7ef569ad0f9e39f1e31869"
PINNED_GEO_SHA = "5feaa58e5835576b3ae2c03a51e955114d620a7aeb710ded58a9f999695f602a"
PINNED_NATIVE_HOUR2_SHA = "d0612c0fee5d25baf1c640f730e6932733ffc82d6878ba56bb7ef6b157464d82"
WATER_LU = set(range(50, 56))


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(4 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def previous_met_water_records(raw: bytes) -> list[dict[str, bytes]]:
    """Strictly decode original CALMET 2.1, all six hours, no frozen replay."""
    records = fortran_records(raw)
    if len(records) < 4 or len(records[0]) != 96 or (
        records[0][:16].decode("ascii").strip() != "CALMET.DAT"
    ):
        raise ValueError("not original CALMET.DAT 2.1")
    ncom, = struct.unpack("<i", records[1])
    if not 0 <= ncom <= 10000 or len(records) < ncom + 3:
        raise ValueError("invalid original CALMET comments")
    head = records[ncom + 2]
    if len(head) != 176:
        raise ValueError("original CALMET header missing")
    meta = struct.unpack_from("<5i", head, 48) + struct.unpack_from("<4i", head, 80)
    if meta != (6, 1, NX, NY, NZ, 1, 2, 1, 0):
        raise ValueError("original CALMET grid/station/hour scope drift")
    hourly = []
    for rec in records[ncom + 3:]:
        if len(rec) < 24:
            raise ValueError("truncated original CALMET record")
        start, ssec, end, esec = struct.unpack_from("<4i", rec, 8)
        if start == end == 0:
            continue
        if len(rec) != 24 + NC * 4:
            raise ValueError("original CALMET hourly record wrong extent")
        hourly.append((rec[:8].decode("ascii"), (start, ssec, end, esec), rec[24:]))
    if len(hourly) != 6 * 45:
        raise ValueError("original CALMET must contain exactly 270 field records")
    out = []
    for h in range(6):
        group = hourly[h * 45:(h + 1) * 45]
        if [rec[0] for rec in group] != LABELS:
            raise ValueError("original CALMET field order drift")
        clock = (202215201 + h, 0, 202215201 + h, 3600)
        if any(rec[1] != clock for rec in group):
            raise ValueError("original CALMET hour clock drift")
        out.append({name: payload for name, _, payload in group})
    return out


def stage40_water_records(raw: bytes, water: set[int]) -> list[dict[str, bytes]]:
    """Verify all 30 original stage events before reading stage-40 water values."""
    if len(water) != 63 or min(water) < 0 or max(water) >= NC:
        raise ValueError("GEO water mask not 63 authentic NOAA cells")
    offset = 0
    out = []
    for h in range(6):
        hour = h + 2
        for stage, fields in STAGE_ARRAYS.items():
            if offset + HEADER.size > len(raw):
                raise ValueError("truncated original DIAGNO stage header")
            found = HEADER.unpack_from(raw, offset)
            offset += HEADER.size
            if found != (hour, NX, NY, NZ, stage):
                raise ValueError(f"original DIAGNO stage/clock drift: {found}")
            count = NC * (NZ if stage == 50 else 1) * len(fields)
            size = count * 4
            if offset + size > len(raw):
                raise ValueError("truncated original DIAGNO REAL4 payload")
            if stage == 40:
                if fields != ("qh", "ustar", "el"):
                    raise ValueError("stage-40 source field schema drift")
                qh, ustar, el = bytearray(), bytearray(), bytearray()
                for i in range(NC):
                    start = offset + 12 * i
                    qh += raw[start:start + 4]
                    ustar += raw[start + 4:start + 8]
                    el += raw[start + 8:start + 12]
                zero = struct.pack("<f", 0.0)
                if {i for i in range(NC) if qh[4*i:4*i+4] == zero} != water:
                    raise ValueError("G22 QH-zero mask != original GEO WATER")
                out.append({"ustar": bytes(ustar), "el": bytes(el)})
            offset += size
    if offset != len(raw):
        raise ValueError("original DIAGNO has extra/unconsumed trace bytes")
    return out


def compare_carryover(met: list[dict[str, bytes]],
                      stage: list[dict[str, bytes]], water: set[int]) -> dict:
    if len(met) != 6 or len(stage) != 6 or len(water) != 63:
        raise ValueError("invalid original carryover hour/water count")
    zero = struct.pack("<f", 0.0)
    if any(stage[0][key][i*4:i*4+4] != zero
           for key in ("ustar", "el") for i in water):
        raise ValueError("original first-hour G22 water must be cold zero")
    results = []
    for hour in range(1, 6):
        checks = {}
        for key, label in (("ustar", "USTAR   "), ("el", "EL      ")):
            current = stage[hour][key]
            previous = met[hour - 1][label]
            if len(current) != 4 * NC or len(previous) != 4 * NC:
                raise ValueError("original WATER array length mismatch")
            errors = [i for i in sorted(water)
                      if current[4*i:4*i+4] != previous[4*i:4*i+4]]
            checks[key] = {"matched_water_cells": 63 - len(errors),
                           "mismatched_water_cells": len(errors),
                           "first_mismatch_i_j": (
                               [errors[0] % NX + 1, errors[0] // NX + 1]
                               if errors else None)}
            if errors:
                raise ValueError(
                    f"original water history mismatch hour={hour+1} "
                    f"{key} cell={checks[key]['first_mismatch_i_j']}")
        results.append({"current_original_g22_hour_end_utc": hour + 2,
                        "previous_original_met_hour_end_utc": hour + 1,
                        "fields": checks})
    return {
        "status": "PASS_ORIGINAL_WATER_USTAR_EL_CARRYOVER_630_REAL4_BITS",
        "comparison": "PREVIOUS_HOUR_ORIGINAL_MET_POST_WATER_TO_NEXT_HOUR_ORIGINAL_DIAGNO_PRE_WATER",
        "water_cells": 63, "hour_transitions": 5,
        "bitwise_compared_words": 5 * 63 * 2,
        "hourly": results,
        "native_third_hour_g22_parity": "NOT_RUN",
        "native_water_state_lifetime": "NOT_ACCEPTED",
        "g22_hour_index_gt_1_guard": "UNCHANGED",
        "s4_p6_full_sixhour": "NOT_ACCEPTED",
        "s4_p7": "NOT_ACCEPTED",
    }


def compare_native_hour2_seed(native: dict[str, bytes],
                              original_third_stage40: dict[str, bytes],
                              water: set[int]) -> dict:
    """126 WATER REAL4 values: native hour-two output predicts hour-three
    original G22 entry state. This is NOT a native G22 stage-three execution.
    """
    from scripts.s4.s4r1c8i_compare_noaa_43_real_p6f import tol
    result = {}
    for key, label in (("ustar", "USTAR   "), ("el", "EL      ")):
        actual = native[label]
        expected = original_third_stage40[key]
        if len(actual) != NC * 4 or len(expected) != NC * 4:
            raise ValueError("native WATER history seed field length drift")
        exceeded = 0
        bitwise_equal = 0
        maximum = 0.0
        worst = None
        for index in sorted(water):
            a, = struct.unpack_from("<f", expected, 4 * index)
            b, = struct.unpack_from("<f", actual, 4 * index)
            if not (float("-inf") < a < float("inf") and
                    float("-inf") < b < float("inf")):
                raise ValueError("native/original WATER history nonfinite")
            delta = abs(a-b)
            if expected[4*index:4*index+4] == actual[4*index:4*index+4]:
                bitwise_equal += 1
            if delta > maximum:
                maximum = delta
                worst = [index % NX + 1, index // NX + 1]
            if delta > tol(label, a, b):
                exceeded += 1
        result[key] = {"words": 63, "bitwise_equal": bitwise_equal,
                       "exceed_frozen_tolerance": exceeded,
                       "max_abs": maximum, "worst_i_j": worst}
        if exceeded:
            raise ValueError(
                f"native hour2 -> original G22 hour3 WATER {key} exceeds "
                f"frozen tolerance at {exceeded} cells")
    return {
        "status": "PASS_SCOPED_NATIVE_HOUR2_TO_ORIGINAL_HOUR3_WATER_SEED_ONLY",
        "native_candidate_hour_end_utc": 3,
        "original_g22_hour_end_utc": 4,
        "fields": result, "words_compared": 126,
        "bitwise_equal_words": sum(v["bitwise_equal"] for v in result.values()),
        "native_g22_hour3_computed": False,
        "native_water_history_commit": "NOT_IMPLEMENTED",
    }


def audit(met_path: Path, trace_path: Path, geo_path: Path,
          native_hour2_path: Path | None = None) -> dict:
    hashes = {"met": sha(met_path), "trace": sha(trace_path), "geo": sha(geo_path)}
    if hashes != {
        "met": PINNED_ORIGINAL_MET_SHA,
        "trace": PINNED_TRACE_SHA,
        "geo": PINNED_GEO_SHA,
    }:
        raise ValueError("original MET, G22 trace or GEO source SHA drift")
    from native_cpp.reference.compare_p3_makegeo_dynamic import parse_geo
    grid = parse_geo(geo_path, nx=NX, ny=NY, zone=50, hem="N",
                     x0=426.590, y0=3464.125, dx=1.)
    water = {i for i, lu in enumerate(grid["category"])
             if int(lu) in WATER_LU}
    met = previous_met_water_records(met_path.read_bytes())
    stage = stage40_water_records(trace_path.read_bytes(), water)
    result = compare_carryover(met, stage, water)
    result["sha256"] = hashes
    result["source"] = "ORIGINAL_CALMET_6_5_0_ONLY"
    if native_hour2_path is not None:
        if sha(native_hour2_path) != PINNED_NATIVE_HOUR2_SHA:
            raise ValueError("native G14 hour2 P6F candidate SHA drift")
        # Native candidate is read ONLY by the independent auditor.
        # No native executable or G14 stage is invoked with original MET.
        from scripts.s4.s4r1c9g_compare_noaa_hour2_met21 import decode
        native = decode(native_hour2_path, original=False)
        result["native_hour2_seed"] = compare_native_hour2_seed(
            native, stage[2], water)
        result["native_hour2_candidate_sha256"] = PINNED_NATIVE_HOUR2_SHA
    result["native_oracle_injection"] = False
    return result


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--original-met", type=Path, required=True)
    ap.add_argument("--original-trace", type=Path, required=True)
    ap.add_argument("--geo", type=Path, required=True)
    ap.add_argument("--native-hour2-candidate", type=Path)
    ap.add_argument("--report", type=Path, required=True)
    args = ap.parse_args()
    if args.report.exists():
        raise ValueError("refusing to overwrite prior scientific report")
    result = audit(args.original_met, args.original_trace, args.geo,
                   args.native_hour2_candidate)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(result["status"])
    if "native_hour2_seed" in result:
        print(result["native_hour2_seed"]["status"])
    print("NATIVE_HOUR3_G22_PARITY=NOT_RUN")


if __name__ == "__main__":
    main()
