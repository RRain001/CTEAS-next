#!/usr/bin/env python3
"""G29B: literal original CALMET TEMP3D vs same-hour G26B 2SS/2US field.

Use actual post-AVEMIX source ZICONV, source face-temperature AA/BB,
READCF IRAD, station coordinates and surface temperature. Do not use C++
temperature output as original input. Restricted to source 00/12 UTC
land-only observed-temperature first hour (ITPROG=0, NOWSTA=0).
This is NOT an accepted whole-hour 45-field, multihour or P6F gate.
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
import compare_original_temp3d_observed_land as oracle

VENDOR = MODULE.parents[2] / "engine" / "vendor" / "src" / "CALMET_v6.5.0_L150223" / "calmet.for"
NX, NY, NZ, NS = 12, 12, 9, 2
ABS_TOL_K, REL_TOL = oracle.ABS_TOL_K, oracle.REL_TOL


def check_source(path: Path):
    rows = path.read_text().splitlines()
    expected = 2 + (NZ + 1) + NS + NS * (NZ + 1) + NX * NY
    if len(rows) != expected or [int(x) for x in rows[0].split()] != [1, NX, NY, NZ, NS]:
        raise ValueError("G29B incorrect source TEMP3D grid / sounding counts")
    config = rows[1].split()
    if len(config) != 3:
        raise ValueError("G29B IRAD / UTC clock / spacing absent")
    irad, hour, spacing = int(config[0]), int(config[1]), float(config[2])
    if irad not in (1, 2) or not 0 <= hour <= 12 or spacing != 10000.0:
        raise ValueError("G29B unsupported literal TEMP3D READCF")
    face = [float(x) for x in rows[2:2 + NZ + 1]]
    if (not all(map(math.isfinite, face)) or
            any(face[i + 1] <= face[i] for i in range(NZ))):
        raise ValueError("G29B nonmonotonic original faces")
    stations = rows[2 + NZ + 1:2 + NZ + 1 + NS]
    justa = []
    coords = []
    for line in stations:
        x = line.split()
        if len(x) != 3:
            raise ValueError("G29B missing source station coordinate")
        j, sx, sy = int(x[0]), float(x[1]), float(x[2])
        if j not in (-1, 1) or not all(math.isfinite(z) for z in (sx, sy)):
            raise ValueError("G29B invalid source physical AA/BB choice")
        justa.append(j)
        coords.append((sx, sy))
    sounding_start = 2 + (NZ + 1) + NS
    for line in rows[sounding_start:sounding_start + NS * (NZ + 1)]:
        terms = line.split()
        if len(terms) != 2 or not all(180 < float(x) < 350 for x in terms):
            raise ValueError("G29B original 2UP face temperature missing")
    convective_cells = 0
    for line in rows[sounding_start + NS * (NZ + 1):]:
        val = line.split()
        if len(val) != 2 or not all(map(math.isfinite, map(float, val))):
            raise ValueError("G29B original TEMP2D and ZICONV absent")
        t, zi = (float(x) for x in val)
        if not 180 < t < 350 or zi < 0:
            raise ValueError("G29B nonphysical original TEMP2D/ZICONV")
        convective_cells += zi > 0
    return {"irad": irad, "hour_in_00_12_utc": hour,
            "dgrid_m": spacing, "justa": justa, "station_xy_m": coords,
            "convective_cells": convective_cells, "source_rows": len(rows)}


def read_candidate(path: Path):
    with path.open(newline="") as stream:
        rows = list(csv.DictReader(stream))
    if len(rows) != NX * NY * NZ:
        raise ValueError("G29B native 1296 T-LEV candidates missing")
    values = {}
    for row in rows:
        if set(row) != {"i", "j", "k", "temp_k"}:
            raise ValueError("G29B C++ TEMP3D candidate fields inconsistent")
        key = int(row["i"]), int(row["j"]), int(row["k"])
        temp = float(row["temp_k"])
        if (key in values or not 1 <= key[0] <= NX or
                not 1 <= key[1] <= NY or not 1 <= key[2] <= NZ or
                not math.isfinite(temp)):
            raise ValueError("G29B invalid native T-LEV ordinal")
        values[key] = temp
    return values


def read_vendor(output):
    values = {}
    for row in output.splitlines():
        fields = row.split()
        if len(fields) != 5:
            raise RuntimeError("G29B original TEMP3D output schema mismatch")
        case, i, j, k = (int(x) for x in fields[:4])
        temp = float(fields[4])
        key = (i, j, k)
        if case != 1 or key in values or not math.isfinite(temp):
            raise RuntimeError("G29B original vendor source returned duplicate/invalid cell")
        values[key] = temp
    if len(values) != NX * NY * NZ:
        raise RuntimeError("G29B original vendor did not calculate all 1296 T-LEV values")
    return values


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=("Debug", "Release"), required=True)
    ap.add_argument("--source-prefix", type=Path, required=True)
    ap.add_argument("--require-convection", action="store_true")
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    input_file = Path(str(args.source_prefix) + ".source.input")
    native_file = Path(str(args.source_prefix) + ".native.csv")
    meta = check_source(input_file)
    native = read_candidate(native_file)
    if args.require_convection and meta["convective_cells"] == 0:
        raise RuntimeError("G29B daytime branch has no convective mixing-layer cells")

    raw = VENDOR.read_bytes()
    sha = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
    if sha != oracle.BLOB:
        raise RuntimeError("G29B original TEMP3D CALMET vendor blob drift")
    original, loc = oracle.original_full_temp3d(raw)
    params = oracle.PARAMS.replace(
        "mxnx=5,mxny=4,mxnz=6,mxnzp1=7,mxus=2",
        "mxnx=12,mxny=12,mxnz=9,mxnzp1=10,mxus=2")
    if params == oracle.PARAMS:
        raise RuntimeError("G29B immutable selected Fortran driver geometry drift")
    with tempfile.TemporaryDirectory(prefix="cteas-g29b-original-temp3d-") as temp:
        work = Path(temp)
        for name, data in (
            ("params.met", params),
            ("original_temp3d.for", original),
            ("driver.for", oracle.DRIVER),
        ):
            (work / name).write_text(data)
        for name in ("grid.met", "met1.met", "upmet.met", "tmp.met",
                     "geo.met", "ovrwat.met"):
            (work / name).write_text("c test-only original COMMON scope\n")
        exe = work / "g29b_original"
        opt = "-O0" if args.mode == "Debug" else "-O2"
        compiled = subprocess.run(
            ["gfortran", opt, "-std=legacy", "-fno-automatic",
             "-ffixed-line-length-none", "-I" + str(work),
             str(work / "original_temp3d.for"), str(work / "driver.for"),
             "-o", str(exe)],
            text=True, capture_output=True)
        if compiled.returncode:
            raise RuntimeError("G29B literal original TEMP3D compilation failed:\n" +
                               compiled.stderr[-4000:])
        proc = subprocess.run(
            [str(exe)], input=input_file.read_text(), text=True, capture_output=True)
        if proc.returncode:
            raise RuntimeError("G29B original TEMP3D execution failed:\n" +
                               (proc.stderr + proc.stdout)[-4000:])
        expected = read_vendor(proc.stdout)

    errors = [0.0] * NZ
    failures = 0
    first = []
    for key, vendor in expected.items():
        if key not in native:
            raise RuntimeError("G29B native T-LEV cell missing")
        got = native[key]
        d = abs(vendor - got)
        errors[key[2] - 1] = max(errors[key[2] - 1], d)
        if d > ABS_TOL_K + REL_TOL * abs(vendor):
            failures += 1
            if len(first) < 20:
                first.append(dict(ijk=key, original_k=vendor, cpp_k=got, abs_diff_k=d))
    result = {
        "status": "PASS" if failures == 0 else "FAIL",
        "mode": args.mode, "cells": NX * NY, "levels": NZ,
        "temperature_scalar_comparisons": NX * NY * NZ,
        "max_abs_error_k_each_level": errors,
        "frozen_abs_tolerance_k": ABS_TOL_K,
        "frozen_rel_tolerance": REL_TOL,
        "branch": meta, "mismatches": failures, "first_mismatches": first,
        "original_git_blob": sha, "literal_original_temp3d_lines": loc,
        "source_sha256": hashlib.sha256(input_file.read_bytes()).hexdigest(),
        "native_sha256": hashlib.sha256(native_file.read_bytes()).hexdigest(),
        "scope": "G29B source 2SS/2US 12x12x9 TEMP3D observed land 00/12Z first-hour only, post AVEMIX ZICONV; no G14 commit or 45-field source parity"
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
