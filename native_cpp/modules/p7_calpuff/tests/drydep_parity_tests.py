#!/usr/bin/env python3
"""P7F MDRY=1 dry deposition: vendor source anchor and Fortran parity.

Checks against the UNMODIFIED vendor source
(engine/vendor/src/CALPUFF_v7.2.1_L150618):

1. Source anchors: the vendor file and the exact spans of the dry deposition
   units (compiled: VDCOMP, VDP; anchored read-only: DRY, DRYI, RDVD, VDP1)
   must match reference/drydep_source_anchor.json, the /DRYGAS/ constants must
   equal the values compiled into the C++ module, and the DRYI formulas that
   are ported by hand must still be present verbatim in the anchored text.
2. Numerical parity: VDCOMP and VDP are extracted unchanged and compiled with
   gfortran into a private oracle, then compared with the C++ probe over a
   deterministic case matrix that exercises every resistance branch.
3. When the locked Hefei 2022 case is present, its deck is audited: MDRY=1,
   H-3 computed gas, HE-3 without dry removal.

This is a deposition-velocity contract only: no puff advection, concentration,
wet removal or chemistry is involved.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import math
import re
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_FALLBACK = Path(__file__).resolve().parents[4]
MODULE = "native_cpp/modules/p7_calpuff"
ANCHOR = f"{MODULE}/reference/drydep_source_anchor.json"
CASE_CONTROL = "project/cases/hefei5km_2022_reference_case_20261011/run/puff/puff.inp"
TOLERANCE_RELATIVE = 1.0e-5
TOLERANCE_ABSOLUTE = 1.0e-12
# /DRYGAS/ and /DRYGAS/-adjacent constants as compiled in the C++ module.
EXPECTED_CONSTANTS = {
    "pconst": 2.3e-8,
    "bmax": 2.5e-6,
    "bmin": 0.1e-6,
    "qswmax": 600.0,
    "dconst1": 2.0,
    "dconst2": 0.6666667,
    "dconst3": 4.8e-4,
    "dconst4": 0.6666667,
}
# DRYI statements the C++ port reproduces; whitespace is normalised before the
# comparison so only the formulas themselves are pinned.
DRYI_QUOTES = (
    "pdiff(i)=pdiff(i)*1.e-4",
    "rm(i)=rm(i)*1.e2",
    "rcutr=rcutr*1.e2",
    "rgr=rgr*1.e2",
    "zref=AMIN1(zgrid1,10.)",
    "sc=vair/pdiff(i)",
    "rd1(i)=dconst1*sc**dconst2/vk",
    "rcut(i)=rcutr*ratio",
    "rgg(i)=rgr*ratio",
    "rgw1(i)=henry(i)/(alphas(i)*dconst3)",
    "data vair/0.15e-4/,vk/0.4/",
)


def fail(message: str) -> None:
    print(f"P7F_DRYDEP_SOURCE_PARITY=FAIL: {message}", file=sys.stderr)
    raise SystemExit(1)


def load_script(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if not spec or not spec.loader:
        fail(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def join_continuations(text: str) -> list[str]:
    statements: list[str] = []
    for line in text.splitlines():
        mark = line[5] if len(line) > 5 else " "
        if mark not in (" ", "0") and statements:
            statements[-1] += " " + line[6:]
        else:
            statements.append(line)
    return statements


def vendor_constants(text: str) -> dict[str, float]:
    values: dict[str, float] = {}
    for statement in join_continuations(text):
        lowered = statement.lstrip().lower()
        if not lowered.startswith("data"):
            continue
        body = statement[statement.lower().find("data") + 4:]
        for match in re.finditer(r"([a-zA-Z][a-zA-Z0-9_]*)\s*/([^/]*)/", body):
            name = match.group(1).lower()
            if name not in EXPECTED_CONSTANTS:
                continue
            entries = [item.strip() for item in match.group(2).split(",") if item.strip()]
            if len(entries) != 1:
                continue
            values[name] = float(entries[0].replace("D", "E").replace("d", "e"))
    return values


def check_dryi_quotes(dryi_text: str) -> int:
    normalised = re.sub(r"\s+", "", dryi_text).lower()
    missing = [quote for quote in DRYI_QUOTES
               if re.sub(r"\s+", "", quote).lower() not in normalised]
    if missing:
        fail("DRYI formulas no longer present in the anchored vendor text: " + ", ".join(missing))
    return len(DRYI_QUOTES)


def compiler_major(compiler: str) -> int | None:
    run = subprocess.run([compiler, "-dumpversion"], capture_output=True, text=True)
    if run.returncode != 0:
        return None
    text = run.stdout.strip().split(".")[0]
    return int(text) if text.isdigit() else None


def find_gfortran(explicit: str | None) -> str | None:
    candidates = [explicit] if explicit else ["gfortran-13", "gfortran-12", "gfortran-11", "gfortran"]
    for candidate in candidates:
        if not candidate:
            continue
        found = subprocess.run(["sh", "-c", f"command -v {candidate}"], capture_output=True,
                               text=True)
        if found.returncode == 0:
            return found.stdout.strip()
    return None


def case_matrix() -> list[tuple]:
    """Stratified matrix covering every VDCOMP branch."""
    rows: list[tuple] = []
    for zref in (1.0, 10.0):
        for vegetation in (1, 2, 3):
            for land_use, u10, v10 in ((10, 0.0, 0.0), (10, 3.0, 4.0), (550, 0.0, 0.0),
                                       (550, 5.0, 0.0)):
                for roughness in (0.01, 0.1):
                    for temperature in (270.0, 283.0, 308.0, 315.0):
                        for ustar in (0.05, 0.3):
                            for monin in (-1.0e9, -10.0, 0.0, 100.0, 100000.0):
                                for leaf_area in (0.0, 2.0):
                                    for radiation in (0.0, 300.0, 1200.0):
                                        rows.append((vegetation, u10, v10, land_use, roughness,
                                                     temperature, ustar, monin, leaf_area, radiation,
                                                     zref))
    return rows


def format_case(index: int, row: tuple) -> str:
    vegetation, u10, v10, land_use, roughness, temperature, ustar, monin, leaf_area, radiation, zref = row
    # lid height, sampling step, mixing height, w*
    return (f"{index} {vegetation} {u10!r} {v10!r} {land_use} 500 599 {roughness!r} "
            f"{temperature!r} {ustar!r} {monin!r} {leaf_area!r} {radiation!r} {zref!r} "
            f"500.0 3600.0 500.0 0.5")


SETUP_LINE = "30.0 10.0 8.0 2.0 0.6666667 4.8e-4 2.3e-8 1.0e-7 2.5e-6 600.0"
SPECIES_LINES = (
    "2",
    "1 0.1509 1.0 8.0 0.0 0.04",   # H-3 from the locked Hefei 2022 deck
    "0 0.0 1.0 1.0 0.0 0.0",       # HE-3, no dry removal
)


def parse_results(text: str) -> dict[tuple[int, int], float]:
    results: dict[tuple[int, int], float] = {}
    for line in text.splitlines():
        fields = line.split()
        if len(fields) != 3:
            continue
        try:
            results[(int(fields[0]), int(fields[1]))] = float(fields[2])
        except ValueError:
            continue
    return results


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--probe", type=Path, required=True, help="built cteas_p7f_drydep_probe")
    parser.add_argument("--repo-root", type=Path, default=REPO_FALLBACK)
    parser.add_argument("--gfortran", help="explicit gfortran executable")
    parser.add_argument("--require", action="store_true",
                        help="fail instead of skipping when no Fortran compiler is available")
    parser.add_argument("--require-case", action="store_true",
                        help="fail when the locked Hefei 2022 control file is missing")
    args = parser.parse_args()
    if not args.probe.is_file():
        fail(f"probe binary missing: {args.probe}")
    repo = args.repo_root.resolve()
    ext = load_script(repo / MODULE / "reference/drydep_source_anchor.py", "p7f_drydep_anchor")
    vendor = repo / ext.VENDOR_SUBDIR
    manifest, compiled, anchored = ext.extract(vendor)
    pinned = json.loads((repo / ANCHOR).read_text())
    if pinned != manifest:
        fail(f"vendor dry deposition source drift: extracted spans/hashes differ from {ANCHOR}; "
             "re-audit the vendor source before trusting the oracle")
    print(f"P7F_DRYDEP_SOURCE_ANCHOR=PASS VENDOR_SHA256={manifest['vendor_source_sha256']} "
          f"COMPILED={','.join(sorted(manifest['compiled_units']))} "
          f"ANCHORED={','.join(sorted(manifest['anchored_units']))}")

    observed = vendor_constants(anchored["block_data"])
    for name, expected in EXPECTED_CONSTANTS.items():
        if name not in observed:
            fail(f"vendor BLOCK DATA no longer declares {name}")
        if abs(observed[name] - expected) > 1e-12 * max(abs(expected), 1e-30):
            fail(f"{name}: vendor {observed[name]!r} != module {expected!r}")
    print(f"P7F_DRYDEP_VENDOR_CONSTANTS=PASS COUNT={len(EXPECTED_CONSTANTS)} "
          f"PCONST={observed['pconst']} DCONST1={observed['dconst1']} "
          f"DCONST2={observed['dconst2']} DCONST3={observed['dconst3']}")
    quotes = check_dryi_quotes(anchored["dryi"])
    print(f"P7F_DRYDEP_DRYI_FORMULAS=PASS QUOTED_STATEMENTS={quotes}")

    compiler = find_gfortran(args.gfortran)
    if compiler is not None:
        major = compiler_major(compiler)
        if major is None or major < 10:
            if args.require:
                fail(f"gfortran {compiler} is older than 10 and cannot build the vendor oracle")
            print(f"P7F_DRYDEP_FORTRAN_ORACLE=SKIPPED_TOO_OLD_COMPILER {compiler}")
            compiler = None
    if compiler is None:
        if args.require:
            fail("no Fortran compiler available but --require was given")
        print("P7F_DRYDEP_FORTRAN_ORACLE=SKIPPED_WITHOUT_FORTRAN")
        return 0

    rows = case_matrix()
    matrix = "\n".join([SETUP_LINE, *SPECIES_LINES] +
                       [format_case(index + 1, row) for index, row in enumerate(rows)]) + "\n"
    probe_run = subprocess.run([str(args.probe)], input=matrix, capture_output=True, text=True)
    if probe_run.returncode != 0:
        fail(f"probe case matrix failed: {probe_run.stderr.strip()}")
    probe_results = parse_results(probe_run.stdout)
    if len(probe_results) != 2 * len(rows):
        fail(f"probe returned {len(probe_results)} rows for {2 * len(rows)} expected")

    with tempfile.TemporaryDirectory(prefix="p7f-drydep-oracle-") as temporary:
        stage = Path(temporary) / "stage"
        ext.stage(vendor, stage, manifest, compiled)
        sources = sorted(str(path) for path in stage.glob("vendor_*.f"))
        driver = str(stage / "drydep_oracle_driver.f")
        binary = stage / "drydep_oracle"
        build = subprocess.run(
            [compiler, "-O0", "-std=legacy", "-ffixed-line-length-72", "-fallow-argument-mismatch",
             "-fno-automatic", f"-I{stage}", "-o", str(binary), *sources, driver],
            capture_output=True, text=True)
        if build.returncode != 0:
            fail(f"vendor oracle compilation failed: {build.stderr.strip()[-800:]}")
        version = subprocess.run([compiler, "--version"], capture_output=True, text=True)
        oracle_run = subprocess.run([str(binary)], input=matrix, capture_output=True, text=True,
                                    cwd=stage)
        if oracle_run.returncode != 0:
            fail(f"vendor oracle run failed: {oracle_run.stderr.strip()[-400:]}")
        oracle_results = parse_results(oracle_run.stdout)
        if len(oracle_results) != len(probe_results):
            fail(f"oracle returned {len(oracle_results)} rows, probe {len(probe_results)}")

        worst_relative = 0.0
        worst_key = (0, 0)
        for key in sorted(oracle_results):
            want = oracle_results[key]
            got = probe_results[key]
            if math.isnan(want) and math.isnan(got):
                continue
            if not math.isfinite(want) or not math.isfinite(got):
                fail(f"case {key}: oracle={want!r} probe={got!r}")
            if abs(want - got) > max(TOLERANCE_RELATIVE * abs(want), TOLERANCE_ABSOLUTE):
                fail(f"case {key}: oracle={want!r} probe={got!r} tolerance rel={TOLERANCE_RELATIVE}")
            relative = abs(want - got) / max(abs(want), 1.0e-30)
            if relative > worst_relative:
                worst_relative = relative
                worst_key = key
        print(f"P7F_DRYDEP_FORTRAN_ORACLE_PARITY=PASS CASES={len(rows)} SPECIES=2 "
              f"TOLERANCE_REL={TOLERANCE_RELATIVE:.0e} MAX_REL={worst_relative:.3e} "
              f"WORST_CASE={worst_key[0]}")
        print(f"P7F_DRYDEP_FORTRAN_COMPILER={version.stdout.splitlines()[0].strip()}")

    control = repo / CASE_CONTROL
    if control.is_file():
        audit_run = subprocess.run([str(args.probe), "--audit", str(control)], capture_output=True,
                                   text=True)
        if audit_run.returncode != 0:
            fail(f"real-deck dry deposition audit failed: {audit_run.stderr.strip()}")
        summary = [line for line in audit_run.stdout.splitlines() if line.startswith("P7F_DRYDEP_OPTION_AUDIT")]
        if not summary:
            fail("real-deck audit produced no summary line")
        line = summary[0]
        for expected in ("MDRY=1", "GAS_SPECIES=1", "NON_DEPOSITED=1", "UNSUPPORTED=0",
                         "ZREF_M=10"):
            if expected not in line:
                fail(f"real-deck audit missing {expected}: {line}")
        print(f"P7F_REAL_DECK_DRYDEP_AUDIT=PASS {line.split(' ', 1)[1][:160]}")
    else:
        if args.require_case:
            fail(f"locked Hefei 2022 control file missing: {control}")
        print(f"P7F_REAL_DECK_DRYDEP_AUDIT=SKIPPED_MISSING_CASE {CASE_CONTROL}")
    print("P7F_DRYDEP_SOURCE_PARITY_IS_NOT_A_CONCENTRATION_TEST=true")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
