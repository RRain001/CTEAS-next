#!/usr/bin/env python3
"""Scratch-only original CALMET DIAGNO wind-tail stage audit.

Copies a pinned original Fortran source into new scratch, adds write-only
stream diagnostics after INTER2, SMOOTH and final WINDBC/DIVCEL/W. Does not
modify original physics, source repository, or native G26/G23/G24 guards.
An instrumented original is valid only if its entire MET.DAT is byte-for-byte
identical to the separately frozen pristine original.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import struct

ORIGINAL_SHA = "835c351d780c0200be721c2d9cbb8dc45b3a8fcd4cb8815fc47bbd26a56a7b23"
PRISTINE_MET_SHA = "a7004fbf780212d58536be3957306c2aecc53abe2e58bfec870571b12d8b8e14"
NX, NY, NZ = 82, 85, 9
NC = NX * NY
HEADER = struct.Struct("<5i")
STAGES = {90: 2 * NZ * NC, 100: 2 * NZ * NC, 110: (2 * NZ + NZ + 1) * NC}


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def emit(stage: int) -> str:
    lines = [
        "c --- S4-R1c9p scratch-only original DIAGNO WINDTAIL trace",
        "      open(unit=98,file='S4_DIAGNO_WINDTAIL.BIN',",
        "     : status='unknown',access='stream',",
        "     : form='unformatted',position='append')",
        f"      write(98) nhrz,nx,ny,nz,{stage}",
        "      write(98) (((u(i,j,k),v(i,j,k),i=1,nx),j=1,ny),k=1,nz)",
    ]
    if stage == 110:
        lines.append(
            "      write(98) (((w(i,j,k),i=1,nx),j=1,ny),k=1,nzp1)"
        )
    lines.append("      close(98)")
    return "\n".join(lines) + "\n"


def prepare(source: Path, target: Path) -> dict:
    if sha(source) != ORIGINAL_SHA:
        raise ValueError("original CALMET source SHA drift")
    target_real, parent = target.resolve(), source.parent.resolve()
    if target.exists() or target_real == parent or parent in target_real.parents:
        raise ValueError("refuse overwrite or original vendor tree")
    text = source.read_text(encoding="latin1")
    start = text.index("      subroutine diagno(")
    end = text.index("      subroutine ", start + 25)
    middle = text[start:end]
    anchors = {
        90: "C    Lake breeze region calculations",
        100: "      CALL SMOOTH(U,V,UB,VB,NSMTH)\n",
        110: "  345 CONTINUE\n",
    }
    for stage, anchor in anchors.items():
        if middle.count(anchor) != 1:
            raise ValueError(f"source DIAGNO stage {stage} anchor not unique")
        if stage == 90:
            middle = middle.replace(anchor, emit(stage) + anchor, 1)
        else:
            middle = middle.replace(anchor, anchor + emit(stage), 1)
    target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    target.write_text(text[:start] + middle + text[end:], encoding="latin1")
    return {"source_sha256": ORIGINAL_SHA, "instrumented_sha256": sha(target),
            "stage_order": list(STAGES), "physics_modified": False,
            "private_original_trace_only": True}


def parse(path: Path) -> dict:
    data = path.read_bytes()
    offset = 0
    summary = []
    for hour in range(2, 8):
        for stage, count in STAGES.items():
            if offset + HEADER.size > len(data):
                raise ValueError("truncated original wind-tail header")
            header = HEADER.unpack_from(data, offset)
            offset += HEADER.size
            if header != (hour, NX, NY, NZ, stage):
                raise ValueError(f"original wind-tail stage/clock drift {header}")
            size = 4 * count
            if offset + size > len(data):
                raise ValueError("truncated original wind-tail REAL4")
            values = struct.unpack_from("<" + str(count) + "f", data, offset)
            offset += size
            if any(not math.isfinite(x) for x in values):
                raise ValueError("original wind-tail nonfinite")
            summary.append({
                "hour_end_utc": hour, "stage": stage, "real4_count": count,
                "minimum": min(values), "maximum": max(values),
                "absmax": max(abs(v) for v in values),
            })
    if offset != len(data):
        raise ValueError("trailing original wind-tail bytes")
    return {"status": "PASS_ORIGINAL_WINDTAIL_TRACE_FORMAT_ONLY",
            "source": "scratch_instrumented_original",
            "hours": 6, "stage_events": len(summary),
            "real4_words": sum(s["real4_count"] for s in summary),
            "stage_summary": summary,
            "native_g23_g24_original_parity": "NOT_RUN",
            "g23_hour_index_gt_1_guard": "UNCHANGED",
            "s4_p6_p7": "NOT_ACCEPTED"}



def compare_final_met(trace_raw: bytes, met_hourly: list[dict[str, bytes]]) -> dict:
    """Original DIAGNO stage110 versus original OUTHR. WFACE(k)=W(k+1).

    This is an independent original-original tracing sanity gate, not native
    G23/G24 equivalence. Never compare WFACE(k) against W(k).
    """
    if len(met_hourly) != 6:
        raise ValueError("six original MET hours required")
    offset, words = 0, 0
    for h in range(6):
        for stage, count in STAGES.items():
            if offset + HEADER.size > len(trace_raw):
                raise ValueError("truncated original wind-tail header")
            header = HEADER.unpack_from(trace_raw, offset)
            offset += HEADER.size
            if header != (h + 2, NX, NY, NZ, stage):
                raise ValueError("original wind-tail clock/stage drift")
            if offset + 4 * count > len(trace_raw):
                raise ValueError("truncated original wind-tail payload")
            if stage != 110:
                offset += 4 * count
                continue
            for k in range(1, NZ + 1):
                for cell in range(NC):
                    for axis, label in (("U", f"U-LEV  {k}"),
                                        ("V", f"V-LEV  {k}")):
                        payload = met_hourly[h][label]
                        if len(payload) != NC * 4:
                            raise ValueError("original MET U/V shape drift")
                        if trace_raw[offset:offset + 4] != payload[cell*4:cell*4+4]:
                            raise ValueError(
                                f"original DIAGNO/OUTHR {axis} mismatch "
                                f"hour={h+1} layer={k} cell={cell}")
                        offset += 4
                        words += 1
            for face in range(NZ + 1):
                for cell in range(NC):
                    if face > 0:
                        payload = met_hourly[h][f"WFACE  {face}"]
                        if len(payload) != NC * 4:
                            raise ValueError("original MET WFACE shape drift")
                        if trace_raw[offset:offset+4] != payload[cell*4:cell*4+4]:
                            raise ValueError(
                                f"original DIAGNO/OUTHR WFACE mismatch "
                                f"hour={h+1} face={face} cell={cell}")
                        words += 1
                    offset += 4
    if offset != len(trace_raw):
        raise ValueError("trailing original wind-tail payload")
    if words != 6 * 3 * NZ * NC:
        raise ValueError("original DIAGNO/OUTHR compared-word count drift")
    return {
        "status": "PASS_ORIGINAL_G24_FINAL_U_V_WFACE_BITWISE",
        "real4_words": words,
        "wface_index": "original OUTHR WFACE(k)=DIAGNO W(k+1)",
        "native_g23_g24_parity": "NOT_RUN",
    }

def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="mode", required=True)
    prep = sub.add_parser("prepare")
    prep.add_argument("--original", required=True, type=Path)
    prep.add_argument("--output", required=True, type=Path)
    aud = sub.add_parser("audit")
    aud.add_argument("--trace", required=True, type=Path)
    aud.add_argument("--instrumented-met", required=True, type=Path)
    aud.add_argument("--report", required=True, type=Path)
    args = p.parse_args()
    if args.mode == "prepare":
        print(json.dumps(prepare(args.original, args.output), indent=2))
    else:
        if sha(args.instrumented_met) != PRISTINE_MET_SHA:
            raise ValueError("instrumented MET differs from pristine original")
        if args.report.exists():
            raise ValueError("refuse overwrite original trace report")
        result = parse(args.trace)
        from scripts.s4.s4r1c9m_original_water_history_parity import (
            previous_met_water_records,
        )
        result["original_stage110_vs_final_met"] = compare_final_met(
            args.trace.read_bytes(),
            previous_met_water_records(args.instrumented_met.read_bytes()))
        result["instrumented_met_sha256"] = PRISTINE_MET_SHA
        result["trace_sha256"] = sha(args.trace)
        args.report.write_text(json.dumps(result, indent=2) + "\n")
        print(result["status"], result["stage_events"], result["real4_words"])


if __name__ == "__main__":
    main()
