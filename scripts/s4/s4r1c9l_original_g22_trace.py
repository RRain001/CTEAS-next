#!/usr/bin/env python3
"""Scratch-only CALMET 6.5.0 DIAGNO G22 source-stage trace.

No original source, private meteorological inputs or instrumented binaries
are distributed by this script. It refuses any unpinned source and only
writes a modified Fortran copy to a caller-provided, new scratch path.

The instrumented original is a *diagnostic* authority; compare its final
MET.DAT against the uninstrumented original byte-for-byte before interpreting
intermediate traces. This is NOT C++ scientific acceptance.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import struct

ORIGINAL_SHA = "835c351d780c0200be721c2d9cbb8dc45b3a8fcd4cb8815fc47bbd26a56a7b23"
HEADER = struct.Struct("<5i")
NX, NY, NZ = 82, 85, 9
STAGE_ARRAYS = {
    10: ("temp2d",),
    20: ("temp2d", "qh", "qsw"),
    30: ("rho",),
    40: ("qh", "ustar", "el"),
    50: ("uslope", "vslope"),
}
# Each event writes a 5-int header, then interleaved grid-cell REAL4 values.
# For stage 50, values are interleaved by i,j,k (Fortran storage order).
ANCHORS = {
    10: (
        "         call surfvar(ug(1,1,1),vg(1,1,1),tprog,temp2d,irh2d,ipcode2d,0)\n",
        "         call surfvar(ug(1,1,1),vg(1,1,1),tprog,temp2d,irh2d,ipcode2d,0)\n"
    ),
    20: (
        "         call heatfx(sinalpc,nears,temp2d,icc,ilandu,iwat1,\n"
        "ccec101006     1              iwat2,nx,ny,icloud,ccgrid,qh,qsw)\n"
        "     1              iwat2,nx,ny,mcloud,ccgrid,qh,qsw)\n",
        "         call heatfx(sinalpc,nears,temp2d,icc,ilandu,iwat1,\n"
        "ccec101006     1              iwat2,nx,ny,icloud,ccgrid,qh,qsw)\n"
        "     1              iwat2,nx,ny,mcloud,ccgrid,qh,qsw)\n"
    ),
    30: (
        "         if (itprog.lt.2) call airden(pres,temp2d,rho)\n"
        "         call elustr(z0,ug,vg,zmid(1),nears,",
        "         if (itprog.lt.2) call airden(pres,temp2d,rho)\n"
        "         call elustr(z0,ug,vg,zmid(1),nears,"
    ),
    40: (
        "     2               nx,ny,mcloud,ccgrid,ipsifcn,qh,ustar,el)\n"
        "      elseif(isfcmet.EQ.1) then",
        "     2               nx,ny,mcloud,ccgrid,ipsifcn,qh,ustar,el)\n"
        "      elseif(isfcmet.EQ.1) then"
    ),
    50: (
        "      if (ISLOPE.EQ.1)CALL SLOPE(USLOPE,VSLOPE,HTOPO,ISURFT,TINF,TEMP2D,\n"
        "     :                           HMAX)\n",
        "      if (ISLOPE.EQ.1)CALL SLOPE(USLOPE,VSLOPE,HTOPO,ISURFT,TINF,TEMP2D,\n"
        "     :                           HMAX)\n"
    ),
}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def trace_lines(stage: int) -> str:
    # The source arrays are declared in DIAGNO; no change to original physics.
    # Use unique units per event to avoid Fortran record markers.
    fields = STAGE_ARRAYS[stage]
    header = [
        "c --- S4-R1c9l scratch-only independent original DIAGNO trace",
        "      open(unit=97,file='S4_DIAGNO_G22.BIN',",
        "     : status='unknown',access='stream',",
        "     : form='unformatted',position='append')",
        f"      write(97) nhrz,nx,ny,nz,{stage}",
    ]
    if stage == 50:
        header.append(
            "      write(97) (((uslope(i,j,k),vslope(i,j,k),"
            "i=1,nx),j=1,ny),k=1,nz)"
        )
    else:
        field_expr = ",".join(f"{name}(i,j)" for name in fields)
        header.append(f"      write(97) (({field_expr},i=1,nx),j=1,ny)")
    header.append("      close(97)")
    return "\n".join(header) + "\n"


def prepare(source: Path, target: Path) -> dict:
    if sha(source) != ORIGINAL_SHA:
        raise ValueError("original CALMET Fortran SHA drift")
    original_dir = source.parent.resolve()
    target_real = target.resolve()
    if (target.exists() or target_real == original_dir or
            original_dir in target_real.parents):
        raise ValueError("refuse existing target or original vendor directory")
    text = source.read_text(encoding="latin1")
    start = text.index("      subroutine diagno(")
    end = text.index("      subroutine ", start + 25)
    before, middle, after = text[:start], text[start:end], text[end:]
    assert len(ANCHORS) == 5
    for stage in (10, 20, 30, 40, 50):
        anchor, replacement = ANCHORS[stage]
        if middle.count(anchor) != 1:
            raise ValueError(f"source stage {stage} anchor not unique")
        # For 20/30/40 insert before the subsequent statement; for 10/50
        # insert after the call. All are only in the ISFCMET=0 source path.
        if stage == 10 or stage == 50:
            middle = middle.replace(anchor, replacement + trace_lines(stage), 1)
        else:
            idx = middle.index(anchor)
            # Stage20 after the final HEATFX continuation, not inside
            # its argument list. Stage30 after AIRDEN, 40 after ELUSTR.
            cut = idx + len(anchor) if stage == 20 else idx + anchor.index("\n") + 1
            middle = middle[:cut] + trace_lines(stage) + middle[cut:]
    target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    target.write_text(before + middle + after, encoding="latin1")
    return {
        "source_sha256": ORIGINAL_SHA,
        "instrumented_sha256": sha(target),
        "stages": {str(k): list(v) for k, v in STAGE_ARRAYS.items()},
        "purpose": "independent_original_stage_trace_only",
        "original_physics_modified": False,
    }


def parse(trace: Path) -> dict:
    data = trace.read_bytes()
    offset, events = 0, []
    while offset < len(data):
        if offset + HEADER.size > len(data):
            raise ValueError("truncated G22 event header")
        hour, nx, ny, nz, stage = HEADER.unpack_from(data, offset)
        offset += HEADER.size
        if (nx, ny, nz) != (NX, NY, NZ) or stage not in STAGE_ARRAYS:
            raise ValueError(f"invalid original trace event {(hour,nx,ny,nz,stage)}")
        count = nx * ny * (nz if stage == 50 else 1) * len(STAGE_ARRAYS[stage])
        byte_count = count * 4
        if offset + byte_count > len(data):
            raise ValueError("truncated G22 REAL4 array")
        payload = data[offset:offset + byte_count]
        offset += byte_count
        # Parse only summary statistics, no restricted data copied to Git.
        values = struct.unpack("<" + str(count) + "f", payload)
        stride = len(STAGE_ARRAYS[stage])
        summaries = {}
        for i, name in enumerate(STAGE_ARRAYS[stage]):
            series = values[i::stride]
            if not all(math.isfinite(value) for value in series):
                raise ValueError(f"nonfinite original trace stage={stage} {name}")
            summaries[name] = {
                "min": min(series), "max": max(series),
                "nonzero_count": sum(v != 0.0 for v in series),
            }
        events.append({"hour": hour, "stage": stage, "arrays": summaries})
    if not events or len(events) % len(STAGE_ARRAYS):
        raise ValueError("missing or partial original DIAGNO hour")
    hours = []
    for i in range(0, len(events), len(STAGE_ARRAYS)):
        group = events[i:i + len(STAGE_ARRAYS)]
        if [event["stage"] for event in group] != list(STAGE_ARRAYS):
            raise ValueError("DIAGNO source stage order changed")
        if len({event["hour"] for event in group}) != 1:
            raise ValueError("DIAGNO hour changed within source stage")
        hours.append(group[0]["hour"])
    if len(hours) != 6 or any(
            b != a + 1 for a, b in zip(hours, hours[1:])):
        raise ValueError(f"expected 6 consecutive source hours, got {hours}")
    return {"status": "PASS_ORIGINAL_STAGE_TRACE_FORMAT_ONLY",
            "trace_sha256": sha(trace), "hours": hours,
            "events": events, "independent_native_parity": "NOT_RUN",
            "production_admission": "NOT_ACCEPTED"}



def verify(source: Path, trace: Path, pristine: Path, instrumented: Path,
           geo: Path, deck: Path, surface: Path, upper: Path) -> dict:
    """Original-only source-stage proof, never a native C++ acceptance."""
    if sha(source) != ORIGINAL_SHA:
        raise ValueError("original Fortran source drift")
    if sha(pristine) != sha(instrumented) or not pristine.stat().st_size:
        raise ValueError("instrumentation changed original MET.DAT bytes")
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from native_cpp.reference.compare_p3_makegeo_dynamic import parse_geo
    grid = parse_geo(geo, nx=NX, ny=NY, zone=50, hem="N",
                     x0=426.590, y0=3464.125, dx=1.)
    water = {i for i, lu in enumerate(grid["category"])
             if 50 <= int(lu) <= 55}
    if len(water) != 63:
        raise ValueError("true original GEO water mask changed")
    audit = parse(trace)
    if audit["hours"] != [2, 3, 4, 5, 6, 7]:
        raise ValueError("original model clock not NOAA 02–07 UTC")
    raw = trace.read_bytes()
    offset = 0
    water_state = []
    for hour in audit["hours"]:
        record = {"original_hour_end_utc": hour}
        for stage, names in STAGE_ARRAYS.items():
            h, nx, ny, nz, tag = HEADER.unpack_from(raw, offset)
            offset += HEADER.size
            if (h, nx, ny, nz, tag) != (hour, NX, NY, NZ, stage):
                raise ValueError("original stage/clock changed during water audit")
            count = NX * NY * (NZ if stage == 50 else 1) * len(names)
            vals = struct.unpack_from("<" + str(count) + "f", raw, offset)
            offset += count * 4
            if stage == 40:
                qh = vals[::3]
                ustar = vals[1::3]
                el = vals[2::3]
                if {i for i, q in enumerate(qh) if q == 0.0} != water:
                    raise ValueError("original QH zero mask differs from GEO water")
                record["water_ustar_nonzero"] = sum(
                    ustar[i] != 0.0 for i in water)
                record["water_el_nonzero"] = sum(el[i] != 0.0 for i in water)
                record["water_ustar_min_mps"] = min(ustar[i] for i in water)
                record["water_ustar_max_mps"] = max(ustar[i] for i in water)
            if stage == 50:
                nonzero = 0
                for k in range(NZ):
                    for i in water:
                        index = 2 * (k * NX * NY + i)
                        nonzero += int(vals[index] != 0.0)
                        nonzero += int(vals[index + 1] != 0.0)
                record["water_slope_nonzero_components"] = nonzero
        if record["water_slope_nonzero_components"]:
            raise ValueError("unexpected original WATER SLOPE effect")
        water_state.append(record)
    if offset != len(raw):
        raise ValueError("original trace has unconsumed trailing bytes")
    if (water_state[0]["water_ustar_nonzero"] != 0 or
            any(x["water_ustar_nonzero"] != 63 for x in water_state[1:])):
        raise ValueError("unexpected original water friction history")
    audit.update({
        "status": "PASS_ORIGINAL_G22_TRACE_BYTE_IDENTICAL_ONLY",
        "reference_met_sha256": sha(pristine),
        "instrumented_met_sha256": sha(instrumented),
        "source_sha256": sha(source),
        "input_sha256": {
            "geo": sha(geo), "deck": sha(deck),
            "surface": sha(surface), "upper": sha(upper),
        },
        "geo_water_cells": len(water),
        "water_state": water_state,
        "original_source_modified": False,
        "native_third_hour_g22_numerical_parity": "NOT_RUN",
        "third_hour_g22_production": "NOT_ACCEPTED",
    })
    return audit

def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="command", required=True)
    prep = sub.add_parser("prepare")
    prep.add_argument("--source", type=Path, required=True)
    prep.add_argument("--output", type=Path, required=True)
    audit = sub.add_parser("audit")
    audit.add_argument("--trace", type=Path, required=True)
    audit.add_argument("--report", type=Path, required=True)
    checked = sub.add_parser("verify")
    for name in ("source", "trace", "pristine", "instrumented", "geo",
                 "deck", "surface", "upper", "report"):
        checked.add_argument("--" + name, type=Path, required=True)
    args = p.parse_args()
    if args.command == "prepare":
        print(json.dumps(prepare(args.source, args.output), indent=2))
    else:
        if args.report.exists():
            raise ValueError("refuse overwrite existing trace report")
        result = (parse(args.trace) if args.command == "audit" else
                  verify(args.source, args.trace, args.pristine,
                         args.instrumented, args.geo, args.deck,
                         args.surface, args.upper))
        args.report.write_text(json.dumps(result, indent=2) + "\n")
        print(f"{result['status']} {args.report}")


if __name__ == "__main__":
    main()
