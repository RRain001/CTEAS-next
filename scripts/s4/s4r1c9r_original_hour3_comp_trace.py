#!/usr/bin/env python3
"""Scratch-only, SHA-pinned original CALMET COMP stage12–15 sixhour trace.

No original source is modified in place, no arithmetic is altered, and
instrumented original MET.DAT must match independently frozen pristine MET.
Original stage arrays are private and never input to native C++.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from pathlib import Path
import struct

ORIGINAL_SHA = "835c351d780c0200be721c2d9cbb8dc45b3a8fcd4cb8815fc47bbd26a56a7b23"
ORIGINAL_MET_SHA = "a7004fbf780212d58536be3957306c2aecc53abe2e58bfec870571b12d8b8e14"
G22_TRACE_SHA = "b6d96dab81af8e9cba89ef55d386aba8082d9136aa7ef569ad0f9e39f1e31869"
GEO_SHA = "5feaa58e5835576b3ae2c03a51e955114d620a7aeb710ded58a9f999695f602a"
NX, NY, NZ = 82, 85, 9
NC = NX * NY
HEADER = struct.Struct("<5i")
FIELDS = {
    12: ("zi", "ziconv", "qh", "temp2d", "rho", "ustar", "el"),
    13: ("zi", "ziconv"),
    14: ("wstar",),
    15: ("temp3d",),
}
PINS = {
    4692: "        call mixht(el,ustar,qh,nx,ny,rho,nhrzb,nearu,iupt,",
    4701: "c",
    4715: "         call avemix(nx,ny,mnmdav,hafang,dgrid,u(1,1,ilevzi),",
    4719: "c",
    4744: "         call wstarr(ziconv,qh,temp2d,rho,ilandu,iwat1,iwat2,nx,ny,",
    4750: "      endif",
    4766: "             call temp3d(nyrze,njulze,nhrze,nsecze,temp2d,ziconv,",
    4772: "          endif",
}
# Inject before the following original line (after the prior statement).
AFTER = {4701: 12, 4719: 13, 4751: 14, 4773: 15}


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def emit(stage: int) -> str:
    arrays = {
        12: ("zi", "ziconv", "qh", "temp2d", "rho", "ustar", "el"),
        13: ("zi", "ziconv"),
        14: ("wstar",),
        15: ("ztemp",),
    }[stage]
    lines = [
        "c S4-R1c9r original COMP write-only stage oracle",
        "      open(unit=97,file='S4_COMP_STAGE12_15.BIN',",
        "     : status='unknown',access='stream',",
        "     : form='unformatted',position='append')",
        f"      write(97) nhrze,{stage},nx,ny,nz",
    ]
    for array in arrays:
        if array == "ztemp":
            lines.append(
                "      write(97) (((ztemp(i,j,k),i=1,nx),j=1,ny),k=1,nz)"
            )
        else:
            lines.append(
                f"      write(97) (({array}(i,j),i=1,nx),j=1,ny)"
            )
    lines.append("      close(97)")
    return "\n".join(lines) + "\n"


def prepare(original: Path, scratch: Path) -> dict:
    if sha(original) != ORIGINAL_SHA:
        raise ValueError("original CALMET source SHA drift")
    if scratch.exists() or original.resolve() == scratch.resolve():
        raise ValueError("refuse overwriting original/scratch source")
    if original.parent.resolve() in scratch.resolve().parents:
        raise ValueError("refuse instrumenting original vendor directory")
    rows = original.read_text(encoding="latin1").splitlines(keepends=True)
    for lineno, expected in PINS.items():
        if rows[lineno - 1].rstrip("\r\n") != expected:
            raise ValueError(f"original COMP anchor L{lineno} drift")
    scratch.parent.mkdir(parents=True, exist_ok=True)
    scratch.write_text("".join(emit(AFTER[i]) + line if i in AFTER else line
                               for i, line in enumerate(rows, 1)),
                       encoding="latin1")
    return {"original_sha256": ORIGINAL_SHA,
            "instrumented_sha256": sha(scratch),
            "source_arithmetic_modified": False,
            "stages": [12, 13, 14, 15]}


def decode(path: Path) -> dict:
    raw = path.read_bytes()
    offset = 0
    result = {}
    for hour in range(2, 8):
        for stage, names in FIELDS.items():
            if offset + HEADER.size > len(raw):
                raise ValueError("truncated original COMP header")
            header = HEADER.unpack_from(raw, offset)
            offset += HEADER.size
            if header != (hour, stage, NX, NY, NZ):
                raise ValueError(f"original COMP stage/clock mismatch {header}")
            count = NC * (NZ if stage == 15 else len(names))
            size = 4 * count
            if offset + size > len(raw):
                raise ValueError("truncated original COMP stage array")
            values = struct.unpack_from("<" + str(count) + "f", raw, offset)
            offset += size
            if any(not math.isfinite(value) for value in values):
                raise ValueError("original COMP nonfinite REAL4")
            if stage == 15 and any(not 180 <= value <= 350 for value in values):
                raise ValueError("original COMP TEMP3D outside plausible Kelvin")
            result[(hour, stage)] = values
    if offset != len(raw):
        raise ValueError("trailing original COMP stage data")
    return result


def audit(trace: Path, original_met: Path,
          g22_trace: Path | None = None, geo: Path | None = None) -> dict:
    if sha(original_met) != ORIGINAL_MET_SHA:
        raise ValueError("instrumented original MET differs from pristine original")
    if g22_trace is None or geo is None:
        raise ValueError("independent original G22/GEO provenance required")
    if sha(g22_trace) != G22_TRACE_SHA or sha(geo) != GEO_SHA:
        raise ValueError("original G22/GEO SHA drift")
    from scripts.s4.s4r1c9n_compare_hour3_g22_trace import extract
    from native_cpp.reference.compare_p3_makegeo_dynamic import parse_geo
    g22 = extract(g22_trace.read_bytes(), tuple(range(2, 8)))[4][40]
    grid = parse_geo(geo, nx=NX, ny=NY, zone=50, hem="N",
                     x0=426.590, y0=3464.125, dx=1.)
    water = [i for i, lu in enumerate(grid["category"])
             if 50 <= int(lu) <= 55]
    if len(water) != 63:
        raise ValueError("original GEO WATER mask drift")
    stages = decode(trace)
    counts = {str(stage): len(stages[(4, stage)]) for stage in FIELDS}
    assert counts == {"12": 7 * NC, "13": 2 * NC,
                      "14": NC, "15": 9 * NC}
    # Stage12 is AFTER original COMP WATER and LAND MIXHT, not the
    # incoming G14 prior state. Do not confuse it with DIAGNO stage40.
    deltas = {}
    for name, comp_field, diagno_field in (("ustar", 5, 1), ("el", 6, 2)):
        diffs = []
        bitwise = 0
        for cell in water:
            a = stages[(4, 12)][comp_field * NC + cell]
            braw = g22[(3 * cell + diagno_field) * 4:
                       (3 * cell + diagno_field + 1) * 4]
            b, = struct.unpack("<f", braw)
            if struct.pack("<f", a) == braw:
                bitwise += 1
            diffs.append(a - b)
        deltas[name] = {"water_cells": len(water),
                        "bitwise_equal": bitwise,
                        "min_signed_delta": min(diffs),
                        "max_signed_delta": max(diffs),
                        "mean_signed_delta": sum(diffs) / len(diffs)}
    if deltas["ustar"]["bitwise_equal"] != 0 or (
            deltas["el"]["bitwise_equal"] != 63):
        raise ValueError("original COMP WATER USTAR/EL stage provenance drift")
    return {
        "status": "PASS_ORIGINAL_HOUR3_COMP_STAGE12_15_SOURCE_ONLY",
        "original_source_sha256": ORIGINAL_SHA,
        "original_met_sha256": ORIGINAL_MET_SHA,
        "original_trace_sha256": sha(trace),
        "hour3_stage_real4_counts": counts,
        "all_sixhour_stage_records": len(stages),
        "all_sixhour_real4_count": sum(len(v) for v in stages.values()),
        "hour3_comp_stage12_water_vs_original_diagno_stage40": deltas,
        "hour3_comp_stage12_is_after_water_and_land_mixht": True,
        "original_g22_trace_sha256": G22_TRACE_SHA,
        "original_geo_sha256": GEO_SHA,
        "hour3_stage12_zi_mean": sum(stages[(4, 12)][:NC]) / NC,
        "hour3_stage13_zi_mean": sum(stages[(4, 13)][:NC]) / NC,
        "hour3_wstar_max": max(stages[(4, 14)]),
        "hour3_temp3d_min": min(stages[(4, 15)]),
        "hour3_temp3d_max": max(stages[(4, 15)]),
        "original_native_hour3_comp_parity": "NOT_RUN",
        "hour3_g14_commit": "NOT_RUN",
        "s4_p6_p7": "NOT_ACCEPTED",
        "independent_science_review": "NOT_RUN",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="mode", required=True)
    p = commands.add_parser("prepare")
    p.add_argument("--original", type=Path, required=True)
    p.add_argument("--scratch", type=Path, required=True)
    p.add_argument("--receipt", type=Path, required=True)
    p = commands.add_parser("audit")
    p.add_argument("--trace", type=Path, required=True)
    p.add_argument("--original-met", type=Path, required=True)
    p.add_argument("--g22-trace", type=Path, required=True)
    p.add_argument("--geo", type=Path, required=True)
    p.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    if args.mode == "prepare":
        if args.receipt.exists():
            raise ValueError("refuse overwrite preparation receipt")
        result = prepare(args.original, args.scratch)
    else:
        if args.report.exists():
            raise ValueError("refuse overwrite original COMP audit")
        result = audit(args.trace, args.original_met,
                       args.g22_trace, args.geo)
    output = args.receipt if args.mode == "prepare" else args.report
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n")
    print(result["status"] if "status" in result else "PASS_PREPARED_ORIGINAL_COMP")


if __name__ == "__main__":
    main()
