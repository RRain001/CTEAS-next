#!/usr/bin/env python3
"""Independent unchanged original CALMET INTER2 on G23 disk-backed station
DIAGI/UP PREPDI and physically computed post-SLOPE original-format inputs.

G23 is a selected **one-hour** original-format SYNTHETIC-weather numeric
test; it is NOT full original Fortran STHEOR/MIXHTST/DIAGI parity, not an
independent full CALMET 17-stage original hour, and not a 45-field pass.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import subprocess
import tempfile
from pathlib import Path

from compare_original_inter2 import DRIVER, extract_original
from compare_g21_file_backed_original_fradj import candidate_rows

ROOT = Path(__file__).resolve().parents[4]
VENDOR = ROOT / "engine/vendor/src/CALMET_v6.5.0_L150223"
NX = NY = 12
NZ = 9
CELLS = NX * NY
UNCHANGED_INTER2_TOLERANCE_MPS = 2e-4


def parse_source(path: Path) -> tuple[dict, list[float]]:
    """Parse same 12x12x9 original-format Fortran input without guessing."""
    lines = path.read_text().splitlines()
    if len(lines) != 4 + NY + NZ + NZ * NY + NZ * NY:
        raise ValueError("G23 original vendor INTER2 input row count incorrect")
    first = lines[0].split()
    if len(first) != 10:
        raise ValueError("G23 original INTER2 first record malformed")
    nst, lvary = map(int, first[:2])
    rmin, rmax1, rmax2, rmax3, r1, r2, edit, editl = map(float, first[2:])
    if nst != 4 or lvary not in (0, 1) or edit != 999999.0 or editl != 999998.0:
        raise ValueError("G23 selected source station count/radius flags or EDIT invalid")
    if not all(math.isfinite(x) and x > 0 for x in
               (rmin, rmax1, rmax2, rmax3, r1, r2)):
        raise ValueError("G23 source radius invalid")
    nintr = [int(v) for v in lines[1].split()]
    xs = [float(v) for v in lines[2].split()]
    ys = [float(v) for v in lines[3].split()]
    if len(nintr) != NZ or any(x < 1 or x > nst for x in nintr) or (
        len(xs) != nst or len(ys) != nst
    ) or not all(math.isfinite(x) for x in xs + ys):
        raise ValueError("G23 source NINTRP or station coordinates invalid")
    for line in lines[4 : 4 + NY]:
        if len(line.split()) != NX:
            raise ValueError("G23 original GEO landuse row invalid")
        [int(v) for v in line.split()]
    for line in lines[4 + NY : 4 + NY + NZ]:
        if len(line.split()) != nst:
            raise ValueError("G23 STHEOR/DIAGI station columns invalid")
        if not all(math.isfinite(float(x)) for x in line.split()):
            raise ValueError("G23 nonfinite DIAGI station")
    begin = 4 + NY + NZ
    inputs = []
    for line in lines[begin:begin + NZ * NY]:
        x = [float(v) for v in line.split()]
        if len(x) != NX or not all(math.isfinite(v) for v in x):
            raise ValueError("G23 post-SLOPE first guess incorrect")
        inputs.extend(x)
    for line in lines[begin + NZ * NY:]:
        x = [float(v) for v in line.split()]
        if len(x) != NX or any(v != 1.0 for v in x):
            raise ValueError("G23 source RDWT observation weight not accepted")
    return dict(nstations=nst, lvary=bool(lvary), nintrp=nintr,
                station_x_km=xs, station_y_km=ys,
                rmin_km=rmin, rmax1_km=rmax1, rmax2_km=rmax2,
                rmax3_km=rmax3, r1_km=r1, r2_km=r2), inputs


def source_driver_text() -> str:
    # Only driver dimensions/horizontal resolution change.  INTER2, FMINF
    # and XMIT all come UNALTERED from the vendored Fortran original source.
    driver = DRIVER.replace("nx=50", "nx=12").replace(
        "ny=50", "ny=12").replace("dx=100.", "dx=10000.").replace(
        "dy=100.", "dy=10000.")
    if driver == DRIVER or "nx=50" in driver or "dy=100." in driver:
        raise RuntimeError("G23 original driver dimension transformation failed")
    return driver


def vendor_output(path: Path) -> dict[tuple[int, int, int], float]:
    result = {}
    for line in path.read_text().splitlines():
        parts = line.split()
        if len(parts) != 4:
            raise ValueError("G23 original vendor INTER2 output structure invalid")
        key = tuple(int(x) for x in parts[:3])
        if key in result or not (
            1 <= key[0] <= NX and 1 <= key[1] <= NY and 1 <= key[2] <= NZ
        ):
            raise ValueError("G23 original INTER2 index repeated/out of range")
        value = float(parts[3])
        if not math.isfinite(value):
            raise ValueError("G23 original INTER2 nonfinite output")
        result[key] = value
    if len(result) != CELLS * NZ:
        raise ValueError("G23 original INTER2 grid missing values")
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-prefix", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--mode", choices=("Debug", "Release"), required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    first, _ = parse_source(Path(str(args.source_prefix) + ".u.input"))
    second, _ = parse_source(Path(str(args.source_prefix) + ".v.input"))
    if first != second:
        raise ValueError("G23 original U/V have different station geometry / source deck")

    with tempfile.TemporaryDirectory(prefix="g23-original-vendor-inter2-") as tmp:
        work = Path(tmp)
        sources = extract_original(VENDOR, work)
        driver = work / "g23_vendor_driver.for"
        driver.write_text(source_driver_text())
        exe = work / "g23_original_inter2"
        opt = "-O0" if args.mode == "Debug" else "-O2"
        subprocess.run(
            ["gfortran", opt, "-std=legacy", "-fno-automatic",
             "-ffixed-line-length-none", "-fallow-argument-mismatch",
             "-I" + str(VENDOR), *[str(p) for p, _ in sources],
             str(driver), "-o", str(exe)],
            check=True, capture_output=True, text=True,
        )
        ref = {}
        for component in ("u", "v"):
            inp = Path(str(args.source_prefix) + f".{component}.input")
            output = work / f"{component}.vendor.txt"
            process = subprocess.run(
                [str(exe), str(inp), str(output)],
                cwd=work, capture_output=True, text=True,
            )
            if process.returncode:
                raise RuntimeError(
                    f"G23 literal vendor INTER2 {component} failed "
                    f"rc={process.returncode}: {process.stderr[-1800:]} "
                    f"{process.stdout[-1000:]}")
            ref[component] = vendor_output(output)
    candidate = candidate_rows(args.candidate)
    if ref["u"].keys() != candidate.keys() or (
        ref["v"].keys() != candidate.keys()
    ):
        raise ValueError("G23 independent source-vendor and C++ 3D coordinates differ")

    errors = []
    max_abs = 0.
    nontrivial = {"u": 0, "v": 0}
    for component_index, component in enumerate(("u", "v")):
        _, step1 = parse_source(
            Path(str(args.source_prefix) + f".{component}.input"))
        for key in sorted(ref[component]):
            i, j, k = key
            ix = (k - 1) * CELLS + (j - 1) * NX + (i - 1)
            original = ref[component][key]
            cpp = candidate[key][component_index]
            diff = abs(original - cpp)
            max_abs = max(max_abs, diff)
            if diff > UNCHANGED_INTER2_TOLERANCE_MPS:
                errors.append((component, key, original, cpp, diff))
            if abs(original - step1[ix]) > 1e-5:
                nontrivial[component] += 1
    record = {
        "scope": "G23 selected 2SS/2US one hour source file DIAGI+PREPDI -> literal Fortran INTER2 U/V",
        "case_type": "synthetic observations in original CALMET source files",
        "original_vendor_source_parts": [d for _, d in sources],
        "mode": args.mode,
        "stations": first["nstations"],
        "grid": [NX, NY, NZ],
        "uv_independently_compared": 2 * len(candidate),
        "nontrivial_inter2_obs_blends": nontrivial,
        "max_abs_uv_delta_mps": max_abs,
        "unchanged_original_inter2_tolerance_mps": UNCHANGED_INTER2_TOLERANCE_MPS,
        "failures": errors[:20],
        "original_fortran_upstream_stheor_diagi_independently_recomputed": False,
        "full_45_field_original_multistation_accepted": False,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(record, indent=2) + "\n")
    if errors:
        raise AssertionError(
            f"G23 original vendor INTER2 U/V mismatches={len(errors)}, "
            f"maximum={max_abs:.9g}, first={errors[:4]}")
    if not all(v > 0 for v in nontrivial.values()):
        raise AssertionError(
            "G23 unchanged Fortran INTER2 did not blend actual SS/US "
            f"observations, {nontrivial}")
    print(
        f"PASS_P6G_G23_LITERAL_ORIGINAL_INTER2 mode={args.mode} "
        f"UV_VALUES={2*len(candidate)} BLENDS_U={nontrivial['u']} "
        f"BLENDS_V={nontrivial['v']} MAX_ABS_DELTA={max_abs:.9g} "
        "UPSTREAM_ORIGINAL_STHEOR_PARITY=NOT_ACCEPTED "
        "FULL_MULTISTATION_45_FIELD=NOT_ACCEPTED"
    )


if __name__ == "__main__":
    main()
