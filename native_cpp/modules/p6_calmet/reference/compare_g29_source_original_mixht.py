#!/usr/bin/env python3
"""G29A: independent literal original CALMET MIXHT on G26B 2SS/2US input.

Consumes the EXACT input recorded before the C++ G26B MIXHT call, including
PREPDI physical AA/BB, per-cell source NEARU, G23 station-cell DPTT, and
previous committed COMP ZI/ZICONV/DPTT. The C++ result is read separately.
No C++ MIXHT output is used to prepare original Fortran inputs.

This accepts only a selected synthetic-observation first hour, all-land,
IUPT=-1, 12x12, 2 upper stations, IMIXH=1. It does NOT constitute full
multi-hour original CALMET 45-field / P6F scientific acceptance.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import subprocess
import sys
import tempfile
from pathlib import Path

MODULE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(MODULE / "p6e" / "reference"))
import compare_original_mixht_observed_mc as oracle

VENDOR = MODULE.parents[2] / "engine" / "vendor" / "src" / "CALMET_v6.5.0_L150223" / "calmet.for"
NX, NY, NS, MAXLEV = 12, 12, 2, 10
# Reuse the already frozen P6E MIXHT physical tolerances; do not loosen.
ABS, REL = oracle.ABS, oracle.REL


def read_source(path: Path):
    data = path.read_text().splitlines()
    if len(data) < 4:
        raise ValueError("G29A missing source input")
    header = data[0].split()
    if len(header) != 5:
        raise ValueError("G29A invalid source header")
    cases, nx, ny, ns, nlev = (int(x) for x in header)
    if (cases, nx, ny, ns) != (1, NX, NY, NS) or not 2 <= nlev <= MAXLEV:
        raise ValueError("G29A source geometry/stations/levels unsupported")
    expected_rows = 2 + ns + 2 * ns * nlev + nx * ny
    if len(data) != expected_rows:
        raise ValueError(f"G29A truncated original input: {len(data)} vs {expected_rows}")
    control = data[1].split()
    if len(control) != 13 or int(control[0]) != -1 or int(control[-1]) != 1:
        raise ValueError("G29A only original IUPT=-1 IMIXH=1 branch accepted")
    vals = [float(x) for x in control]
    if not all(map(math.isfinite, vals)):
        raise ValueError("G29A invalid source scalar control")
    if int(vals[11]) != 3600:
        raise ValueError("G29A requires one-hour source COMP step")
    justa = [int(data[k]) for k in range(2, 2 + ns)]
    if not all(k in (-1, 1) for k in justa):
        raise ValueError("G29A inconsistent PREPDI JUSTA")
    start = 2 + ns
    for row in data[start: start + 2 * ns * nlev]:
        pair = row.split()
        if len(pair) != 2 or not all(math.isfinite(float(z)) for z in pair):
            raise ValueError("G29A invalid original AA/BB thermal source")
    nearu = {}
    source_dist = dict(stable=0, convection=0, upper1=0, upper2=0,
                       aa_older=0, bb_older=0, nonzero_prior_dptt=0)
    for row in data[start + 2 * ns * nlev:]:
        x = row.split()
        if len(x) != 11:
            raise ValueError("G29A source grid missing input fields")
        values = [float(t) for t in x]
        if not all(map(math.isfinite, values)):
            raise ValueError("G29A nonfinite original source grid")
        qh, ustar, el, rho, cmech, fcori, land, near, zi, ziconv, dptt = values
        near = int(near)
        if near not in (1, 2) or int(land) != land or land in range(50, 61):
            raise ValueError("G29A unsupported original source cell")
        if ustar <= 0 or rho <= 0 or cmech <= 0 or fcori <= 0:
            raise ValueError("G29A invalid original source thermodynamics")
        source_dist["upper" + str(near)] += 1
        source_dist["stable" if qh < 0 else "convection"] += 1
        source_dist["nonzero_prior_dptt"] += dptt != 0
        if qh >= 0:
            source_dist["aa_older" if justa[near - 1] > 0 else "bb_older"] += 1
    if min(source_dist["upper1"], source_dist["upper2"]) == 0:
        raise RuntimeError("G29A did not exercise both physically selected US sites")
    return {"rows": len(data), "nlev": nlev, "justa": justa,
            "distribution": source_dist}


def read_native(path: Path):
    with path.open(newline="") as stream:
        rows = list(csv.DictReader(stream))
    if len(rows) != NX * NY:
        raise ValueError("G29A incomplete 144-cell C++ candidate")
    result = {}
    for row in rows:
        if set(row) != {"i", "j", "zi_m", "ziconv_m", "dptt_k"}:
            raise ValueError("G29A unexpected C++ candidate columns")
        key = (int(row["i"]), int(row["j"]))
        val = (float(row["zi_m"]), float(row["ziconv_m"]), float(row["dptt_k"]))
        if (key in result or not 1 <= key[0] <= NX or not 1 <= key[1] <= NY
                or not all(map(math.isfinite, val))):
            raise ValueError("G29A duplicate/invalid C++ cell or value")
        result[key] = val
    return result


def parse_vendor_grid(output: str):
    parsed = []
    for row in output.splitlines():
        columns = row.split()
        if len(columns) != 6:
            raise RuntimeError("G29A malformed original vendor result")
        key = tuple(int(x) for x in columns[:3])
        value = tuple(float(x) for x in columns[3:])
        if not all(map(math.isfinite, value)):
            raise RuntimeError("G29A original Fortran returned nonfinite MIXHT")
        parsed.append((key, value))
    if len(parsed) != NX * NY:
        raise RuntimeError("G29A vendor MIXHT missing grid cells")
    return parsed


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=("Debug", "Release"), required=True)
    ap.add_argument("--source-prefix", type=Path, required=True)
    ap.add_argument("--require-convection", action="store_true")
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()

    original_input = Path(str(args.source_prefix) + ".source.input")
    native_file = Path(str(args.source_prefix) + ".native.csv")
    meta = read_source(original_input)
    candidate = read_native(native_file)
    if args.require_convection and (
        meta["distribution"]["convection"] == 0 or
        meta["distribution"]["aa_older"] + meta["distribution"]["bb_older"] == 0
    ):
        raise RuntimeError("G29A requires real daytime original MIXHT branch")

    blob = VENDOR.read_bytes()
    sha = hashlib.sha1(b"blob " + str(len(blob)).encode() + b"\0" + blob).hexdigest()
    if sha != oracle.BLOB:
        raise RuntimeError("G29A original frozen CALMET source blob changed")
    source, portions = oracle.source(blob)
    # Only dimensional guard is specialized; the untouched original MIXHT,
    # MIXDT, MIXHMC, MIXHBG routines remain the reference authority.
    params = oracle.PARAMS.replace("mxnx=5,mxny=4", "mxnx=12,mxny=12")
    driver = oracle.DRIVER.replace(
        "if(nx.ne.5.or.ny.ne.4.or.ns.ne.2.or.nlev.ne.10)stop 66",
        "if(nx.ne.12.or.ny.ne.12.or.ns.ne.2.or.nlev.lt.2.or.nlev.gt.10)stop 66"
    )
    if params == oracle.PARAMS or driver == oracle.DRIVER:
        raise RuntimeError("G29A source comparator dimensional anchors moved")

    with tempfile.TemporaryDirectory(prefix="cteas-g29a-literal-mixht-") as temp:
        work = Path(temp)
        for filename, data in (
            ("params.met", params),
            ("ziparm.met", (VENDOR.parent / "ziparm.met").read_text()),
            ("upmet.met", (VENDOR.parent / "upmet.met").read_text()),
            ("gen.met", (VENDOR.parent / "gen.met").read_text()),
            ("original.for", source),
            ("driver.for", driver),
        ):
            (work / filename).write_text(data)
        exe = work / "g29a_original"
        opt = "-O0" if args.mode == "Debug" else "-O2"
        compiled = subprocess.run(
            ["gfortran", opt, "-std=legacy", "-fno-automatic",
             "-ffixed-line-length-none", "-I" + str(work),
             str(work / "original.for"), str(work / "driver.for"), "-o", str(exe)],
            text=True, capture_output=True)
        if compiled.returncode:
            raise RuntimeError("G29A literal original Fortran compile failure:\n" +
                               compiled.stderr[-4000:])
        process = subprocess.run([str(exe)], input=original_input.read_text(),
                                 text=True, capture_output=True)
        if process.returncode:
            raise RuntimeError("G29A literal original Fortran execution failed:\n" +
                               (process.stderr + process.stdout)[-4000:])
        expected = parse_vendor_grid(process.stdout)
    # The vendor driver produces exactly 144 rows for this selected case.
    if len(expected) != NX * NY:
        raise RuntimeError("G29A original Fortran returned incomplete source grid")

    errors = [0.0, 0.0, 0.0]
    mismatch = 0
    examples = []
    for (case, i, j), original in expected:
        if case != 1 or (i, j) not in candidate:
            raise RuntimeError("G29A Fortran/C++ grid ordinal mismatch")
        value = candidate[i, j]
        for k, (ref, got) in enumerate(zip(original, value)):
            error = abs(ref - got)
            errors[k] = max(errors[k], error)
            if error > ABS[k] + REL * abs(ref):
                mismatch += 1
                if len(examples) < 20:
                    examples.append({"i": i, "j": j, "field": k,
                                     "original": ref, "cpp": got, "abs_error": error})
    verdict = {
        "status": "PASS" if mismatch == 0 else "FAIL",
        "scope": "G29A selected 2SS/2US 12x12 first-hour pre-AVEMIX source GRID MIXHT, all land; no G14 hour commit, P6F or multihour vendor acceptance",
        "mode": args.mode,
        "cases": 1, "cells": NX * NY, "scalar_checks": 3 * NX * NY,
        "max_abs_ZI_ZICONV_DPTT": errors,
        "frozen_abs_tolerance": ABS, "frozen_rel_tolerance": REL,
        "source": meta, "mismatches": mismatch,
        "first_mismatches": examples,
        "original_vendor_blob": sha,
        "original_source_routines": portions,
        "input_sha256": hashlib.sha256(original_input.read_bytes()).hexdigest(),
        "candidate_sha256": hashlib.sha256(native_file.read_bytes()).hexdigest(),
        "bb_older_current_hour_covered": meta["distribution"]["bb_older"] > 0,
        "previous_comp_nonzero_dptt_covered": meta["distribution"]["nonzero_prior_dptt"] > 0,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(verdict, indent=2) + "\n")
    print(json.dumps(verdict, indent=2))
    if mismatch:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
