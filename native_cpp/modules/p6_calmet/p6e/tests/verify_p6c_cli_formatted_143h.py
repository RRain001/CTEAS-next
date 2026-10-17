#!/usr/bin/env python3
"""E17: read genuine P6C SURF.DAT 2.1 / UP.DAT 2.1 FORMAT shapes end to end.

Inputs are generated synthetic observations, not actual Hefei 2022 values.
The test uses only the same parsers and selected P6C->P6E CLI used
for real files. CI acceptance does NOT imply original COMP meteorology.
"""
import argparse
import csv
import hashlib
import math
import subprocess
import tempfile
from pathlib import Path

HOURS = 143
STATION = 58424
NLEV = 10
PROFILE_HEIGHTS_M = (0, 80, 160, 300, 500, 800, 1200, 2000, 3000, 4200)
PRESSURE_HPA = (1000, 985, 968, 940, 906, 850, 790, 700, 600, 500)


def surface_file(path: Path) -> None:
    lines = [
        "SURF.DAT        2.1             Hour Start and End Times with Seconds",
        "   1",
        "E17 synthetic P6C SURF formatted compatibility test",
        "NONE    ",
        "UTC+0000",
        " 2022   1   0     0  2022   6  23     0    1",
        "   58321",
    ]
    for n in range(HOURS):
        day, hour = 1 + n // 24, n % 24
        next_day, next_hour = 1 + (n + 1) // 24, (n + 1) % 24
        lines.append(f"2022 {day} {hour} 0 2022 {next_day} {next_hour} 0")
        code = 0 if n == 70 else 9999
        lines.append(f"3.0 150.0 722 5 {285 + n % 6} 65 1008.1 {code}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def level_group(st: int, lev: int) -> str:
    z = 120 + PROFILE_HEIGHTS_M[lev]
    t = 301.0 - 0.007 * PROFILE_HEIGHTS_M[lev] + st * 0.2
    p = PRESSURE_HPA[lev]
    return f"   {p:6.1f}/{z:5d}/{t:5.1f}/{110:3d}/{3:3d}"


def upper_file(path: Path) -> None:
    lines = [
        "UP.DAT          2.1             Hour Start and End Times with Seconds",
        "   1",
        "E17 synthetic P6C UP formatted compatibility test",
        "NONE    ",
        "UTC+0000",
        " 2022    1    0    0 2022    6   23    0 500.    2    1",
        "     F    F    F    F",
    ]
    for sounding in range(13):
        day, hour = 1 + sounding // 2, 12 * (sounding % 2)
        stamp = f"{2022:4d}{1:4d}{day:3d}{hour:3d}{0:5d}"
        lines.append(f"   6201  {STATION:8d}    {stamp}    {stamp}"
                     f"{NLEV:5d}   {NLEV:5d}")
        groups = [level_group(sounding, k) for k in range(NLEV)]
        if not all(len(g) == 29 for g in groups):
            raise AssertionError("RDUPN synthetic group not 29 chars")
        for index in range(0, len(groups), 4):
            lines.append("".join(groups[index:index + 4]))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run(exe: Path, surf: Path, upper: Path, out: Path, station: int):
    return subprocess.run(
        [str(exe), str(surf), str(upper), str(station), str(out)],
        text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )


def verify(exe: Path) -> None:
    with tempfile.TemporaryDirectory(prefix="cteas-p6e-e17-") as dirname:
        root = Path(dirname)
        surf, upper, output = (root / "SURF.DAT", root / "UP.DAT", root / "hourly.csv")
        surface_file(surf)
        upper_file(upper)
        result = run(exe, surf, upper, output, STATION)
        if result.returncode:
            raise AssertionError(
                "Original-format synthetic P6C->P6E CLI failed: "
                + result.stderr[-3000:]
            )
        if "hours=143" not in result.stdout:
            raise AssertionError("CLI did not report 143 source hours")
        with output.open(newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
        if len(rows) != HOURS:
            raise AssertionError("E17 missing 143 formatted case rows")
        swapped = 0
        missing = 0
        observed_zero = 0
        for n, row in enumerate(rows):
            expected_hour = n + 1
            if int(row["hour_index"]) != expected_hour:
                raise AssertionError("E17 hourly order drift")
            if int(row["rdsn_source_row"]) != expected_hour:
                raise AssertionError("E17 RDSN record row drift")
            if int(row["upper_station_id"]) != STATION:
                raise AssertionError("E17 upper station ID drift")
            observed = int(row["precipitation_observed"])
            code = int(row["precipitation_code"])
            if n == 70:
                if (observed, code) != (1, 0):
                    raise AssertionError("E17 observed zero precipitation lost")
                observed_zero += 1
            else:
                if (observed, code) != (0, 9999):
                    raise AssertionError("E17 missing precipitation invented")
                missing += 1
            if int(row["humidity_pct"]) != 65:
                raise AssertionError("E17 humidity reader misaligned")
            if float(row["air_temperature_k"]) != 285 + n % 6:
                raise AssertionError("E17 surface temperature misread")
            justa = int(row["justa"])
            older = int(row["chronological_old_index"])
            newer = int(row["chronological_new_index"])
            physical_aa = int(row["physical_aa_index"])
            physical_bb = int(row["physical_bb_index"])
            if justa == 1:
                if (physical_aa, physical_bb) != (older, newer):
                    raise AssertionError("E17 positive JUSTA physical AA/BB drift")
            elif justa == -1:
                if (physical_aa, physical_bb) != (newer, older):
                    raise AssertionError("E17 negative JUSTA physical AA/BB drift")
                swapped += 1
            else:
                raise AssertionError("E17 invalid JUSTA")
            if int(row["past_s"]) + int(row["to_go_s"]) != 43200:
                raise AssertionError("E17 12h source bracket mismatch")
            if int(row["gap_s"]) != 43200:
                raise AssertionError("E17 gap mismatch")
            for label in ("physical_aa_face2_k", "physical_bb_face2_k"):
                t = float(row[label])
                if not math.isfinite(t) or not 270 < t < 315:
                    raise AssertionError("E17 invalid interpolated face temperature")
        if missing != 142 or observed_zero != 1 or swapped < 50:
            raise AssertionError("E17 critical source branch coverage insufficient")
        first = hashlib.sha256(output.read_bytes()).hexdigest()
        rerun = run(exe, surf, upper, output, STATION)
        if rerun.returncode or hashlib.sha256(output.read_bytes()).hexdigest() != first:
            raise AssertionError("E17 CLI output not deterministic")
        wrong_station = run(exe, surf, upper, root / "rejected.csv", 58321)
        if wrong_station.returncode == 0:
            raise AssertionError("E17 wrong UP station incorrectly accepted")
        print(
            "PASS_P6E_E17_FORMATTED_SYNTHETIC_143H_CLI",
            "hours=143",
            f"swapped={swapped}",
            f"missing_precip={missing}",
            f"observed_zero={observed_zero}",
            f"sha256={first}",
            "REAL_2022_INPUTS_NOT_TESTED=1",
        )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cpp", type=Path, required=True)
    args = ap.parse_args()
    verify(args.cpp.resolve())


if __name__ == "__main__":
    main()
