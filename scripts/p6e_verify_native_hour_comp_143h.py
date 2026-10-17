#!/usr/bin/env python3
"""P6E 143h real-code migration gate: legacy COMP vs native shared-hour COMP.

This runs native C++ P6D station ELUSTR2 once to produce scientific input for
BOTH P6E paths, but still supplies original frozen MET.DAT winds to P6E.
A bit-identical comparison establishes that the native COMP-hour state
migration did not alter E42's existing formulas. It is NOT P6D↔P6E one-pass
physics, not P6D U/V/W acceptance, and not independently produced MET.DAT.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import subprocess
import sys

ORIGINAL_MET_SHA = "b1823cda92280888d70b00961ab39486036a3086e18637fff21efb4f4b237d30"


def run(argv: list[object], log: pathlib.Path) -> None:
    proc = subprocess.run([str(x) for x in argv], capture_output=True, text=True)
    log.write_text(
        "$ " + " ".join(map(str, argv)) + "\n" +
        f"exit={proc.returncode}\n" + proc.stdout + "\n" + proc.stderr
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"{argv[0]} failed ({proc.returncode}); {log}: {proc.stderr[-1400:]}"
        )


def sha(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1048576), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--case", type=pathlib.Path, required=True)
    p.add_argument("--p6d", type=pathlib.Path, required=True)
    p.add_argument("--p6e", type=pathlib.Path, required=True)
    p.add_argument("--bridge", type=pathlib.Path, required=True)
    p.add_argument("--work", type=pathlib.Path, required=True)
    args = p.parse_args()
    case, work = args.case.resolve(), args.work.resolve()
    work.mkdir(parents=True, exist_ok=True)
    met = case / "run/met/met.dat"
    surf = case / "met/surface/final/surf.dat"
    upper = case / "met/upperair/final/up_58424.dat"
    geo = case / "geo/makegeo/geo.dat"
    for file in (met, surf, upper, geo):
        if not file.is_file():
            raise RuntimeError(f"missing frozen case input: {file}")
    if sha(met) != ORIGINAL_MET_SHA:
        raise RuntimeError("original CALMET.DAT SHA drift")

    p6d_out = work / "p6d"
    p6d_out.mkdir(exist_ok=True)
    run([args.p6d, "--case", case, "--hours", "143", "--out", p6d_out],
        work / "p6d.log")
    station_flux = p6d_out / "station_elustr2.csv"
    if not station_flux.is_file() or len(station_flux.read_text().splitlines()) != 144:
        raise RuntimeError("expected 143 native station ELUSTR2 hours")

    observation = work / "hourly.csv"
    run([args.bridge, surf, upper, "58424", observation],
        work / "bridge.log")
    base_cmd = [
        args.p6e, "emit-realcase",
        "--reference", met, "--observations", observation,
        "--wind-file", met, "--geo-file", geo,
        "--station-flux-csv", station_flux,
        "--dptt-refresh", "0",
    ]
    legacy = work / "legacy_comp.dat"
    native = work / "native_comp.dat"
    run(base_cmd + ["--out", legacy, "--report", work / "legacy_report.json"],
        work / "legacy.log")
    run(base_cmd + [
        "--native-hour-comp", "1", "--out", native,
        "--report", work / "native_report.json",
        "--state-prefix", work / "native_comp_state"
    ], work / "native.log")
    a, b = sha(legacy), sha(native)
    evidence = {
        "status": "PASS_P6E_COMP_MIGRATION_BIT_IDENTICAL" if a == b else "FAIL_P6E_COMP_MIGRATION",
        "hours": 143,
        "native_p6d_station_elustr2": str(station_flux),
        "same_wind_source_for_both": "frozen_original_calmet.dat",
        "legacy_sha256": a, "native_hour_comp_sha256": b,
        "byte_identical": a == b,
        "p6d_p6e_original_hourly_single_pass": False,
        "p6d_full_uvw": "NOT_PASS",
        "p6g_full_45_native_fields": "NOT_PASS",
    }
    (work / "migration_evidence.json").write_text(json.dumps(evidence, indent=2) + "\n")
    print(json.dumps(evidence, indent=2))
    return 0 if a == b else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as error:
        print(f"BLOCKED_P6E_COMP_MIGRATION: {error}", file=sys.stderr)
        sys.exit(3)
