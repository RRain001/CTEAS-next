#!/usr/bin/env python3
"""Pinpoint first original CALMET COMP divergence with unchanged native C++ physics.

Use committed, SHA-verified, write-only original Fortran DGMSTATE snapshots.
Compare them to actual per-hour causal P6E .f32 state files, not reference wind
injected into the C++ candidate. Stage 1 is after ELUSTR and before MIXHT;
stage 3 is after MIXHT; stage 4 is after AVEMIX; stage 5 is after WSTARR.

This forensic reports both any bitwise REAL*4 drift and source-comparator
tolerance exceedances for USTAR/EL/WSTAR. It changes no physics or tolerance.
"""
from __future__ import annotations

import argparse
from array import array
import hashlib
import json
import math
from pathlib import Path
import struct
import sys

HEAD = struct.Struct("<8i")
FIELDS = {
    1: (("QH", "q_flux"), ("USTAR", "ustar"), ("EL", "el"),
        ("RHO", None), ("TEMP2D", None)),
    2: (("ZICONV_BEFORE_MIXHT", None), ("DPTT_BEFORE_MIXHT", "pre_mixht.dptt")),
    3: (("ZI_BEFORE_AVEMIX", "pre_avemix.zi"),
        ("ZICONV_BEFORE_AVEMIX", "pre_avemix.ziconv"), ("DPTT_AFTER_MIXHT", "dptt")),
    4: (("ZI_AFTER_AVEMIX", "zi"), ("ZICONV_AFTER_AVEMIX", "ziconv")),
    5: (("WSTAR", "wstar"), ("ZICONV_AFTER_WSTARR", "ziconv")),
}
SCIENCE_TOLERANCE = {"USTAR": (3e-5, 5e-5),
                     "EL": (0.04, 5e-5),
                     "WSTAR": (2e-5, 3e-5)}
COUNT = 2500
EXPECTED_SOURCE_SHA = "e6b8ab309f81ddc3015dc750272eeb2ee8289a2d34563b364884d9e443be6ece"


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(4 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def floats(data: bytes) -> array:
    if len(data) != COUNT * 4:
        raise ValueError(f"bad 50x50 original REAL*4 record: {len(data)}")
    values = array("f")
    values.frombytes(data)
    if sys.byteorder != "little":
        values.byteswap()
    if len(values) != COUNT:
        raise ValueError("malformed float array")
    return values


def native(path: Path) -> array:
    if not path.is_file():
        raise FileNotFoundError(f"required causal native COMP export absent: {path}")
    return floats(path.read_bytes())


def stats_template() -> dict:
    return {"compared": 0, "nonzero": 0, "max_abs": 0.0, "rms_sum": 0.0,
            "first_nonzero": None, "tolerance_exceedances": 0,
            "first_exceedance": None, "max_error_position": None}


def collect(rec: dict, src: array, dst: array, hour: int, name: str) -> None:
    for idx, (a, b) in enumerate(zip(src, dst, strict=True)):
        if not (math.isfinite(a) and math.isfinite(b)):
            raise ValueError(f"nonfinite {name} at hour={hour + 1} cell={idx + 1}")
        diff = abs(a - b)
        rec["compared"] += 1
        rec["rms_sum"] += diff * diff
        if diff:
            rec["nonzero"] += 1
            pos = {"hour": hour + 1, "i": idx % 50 + 1, "j": idx // 50 + 1,
                   "original": a, "native": b, "difference": diff}
            if rec["first_nonzero"] is None:
                rec["first_nonzero"] = pos
            if diff > rec["max_abs"]:
                rec["max_abs"] = diff
                rec["max_error_position"] = pos
            if name in SCIENCE_TOLERANCE:
                ab, rel = SCIENCE_TOLERANCE[name]
                # Original comparator uses independently frozen absolute and
                # relative limits. A source value near zero is covered by abs.
                if diff > ab and diff > rel * max(abs(a), abs(b)):
                    rec["tolerance_exceedances"] += 1
                    if rec["first_exceedance"] is None:
                        rec["first_exceedance"] = pos


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--source", required=True, type=Path)
    p.add_argument("--source-meta", required=True, type=Path)
    p.add_argument("--native-work", required=True, type=Path)
    p.add_argument("--hours", type=int, default=14)
    p.add_argument("--out", required=True, type=Path)
    args = p.parse_args()
    if not 1 <= args.hours <= 143:
        raise ValueError("hours must be in 1..143")
    meta = json.loads(args.source_meta.read_text())
    if digest(args.source) != EXPECTED_SOURCE_SHA or (
        meta["binary"]["sha256"] != EXPECTED_SOURCE_SHA
    ):
        raise ValueError("frozen original Fortran source DGMSTATE hash mismatch")
    if meta["binary"]["hours"] != 143 or meta["grid"]["nx"] != 50 or meta["grid"]["ny"] != 50:
        raise ValueError("original dump dimensions/hours are not frozen Hefei")
    state = {}
    with args.source.open("rb") as source:
        for h in range(args.hours):
            for phase in range(1, 6):
                header = source.read(HEAD.size)
                if len(header) != HEAD.size:
                    raise ValueError("truncated original COMP trace header")
                kpt, nh, year, jul, hour, sec, nx, ny = HEAD.unpack(header)
                if (kpt, nh, year, nx, ny) != (phase, h + 1, 2022, 50, 50):
                    raise ValueError(f"bad original COMP record order {kpt, nh, year, nx, ny}")
                for name, filename in FIELDS[phase]:
                    field = floats(source.read(COUNT * 4))
                    if filename is None:
                        continue
                    work = args.native_work / f"hour_{h:03d}" / f"comp.{filename}.f32"
                    cand = native(work)
                    key = f"P{phase}:{name}"
                    rec = state.setdefault(key, stats_template())
                    collect(rec, field, cand, h, name)
        if not source.read(1):
            # For partial 14h reads, more original hours must remain.
            if args.hours < 143:
                raise ValueError("original trace lacks further hours")
    for v in state.values():
        v["rms"] = math.sqrt(v.pop("rms_sum") / v["compared"])
    first = sorted(
        (dict(phase=key, **value["first_nonzero"]) for key, value in state.items()
         if value["first_nonzero"] is not None),
        key=lambda q: (q["hour"], int(q["phase"].split(":")[0][1:])))
    report = {
        "status": "FORENSIC_ONLY_NOT_P6E_ACCEPTANCE",
        "source": "frozen Fortran 143h DGMSTATE, audited write-only; SHA-256 locked",
        "candidate": "native C++ P6D->P6E single-clock causal history",
        "hours_checked": args.hours,
        "source_sha256": EXPECTED_SOURCE_SHA,
        "first_native_comp_divergence": first[0] if first else None,
        "fields": state,
        "scientific_tolerances_unchanged": SCIENCE_TOLERANCE,
        "full_143h_science": "NOT_CLAIMED",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    print("FIRST_ORIGINAL_COMP_DIVERGENCE", report["first_native_comp_divergence"])
    for name, result in state.items():
        print(name, "nonzero", result["nonzero"],
              "max_abs", result["max_abs"], "rms", result["rms"],
              "exceedances", result["tolerance_exceedances"],
              "first_exceed", result["first_exceedance"])


if __name__ == "__main__":
    main()
