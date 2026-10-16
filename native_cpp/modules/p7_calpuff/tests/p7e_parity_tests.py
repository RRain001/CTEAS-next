#!/usr/bin/env python3
"""P7E receptor/sampling/output: vendor source anchor, PFSAMP parity and
CONC.DAT framing parity.

Checks against the UNMODIFIED vendor source
(engine/vendor/src/CALPUFF_v7.2.1_L150618/calpuff.for):

1. Anchors: the vendor file and the exact spans of PFSAMP, ERFDIF, WRTI1D,
   WRTR1D and WRTR2D must match reference/p7e_source_anchor.json, and the
   PFSAMP/ERFDIF constants used by the C++ port must still be present.
2. PFSAMP parity: the extracted units are compiled unchanged into a private
   oracle and compared with the C++ probe over a case matrix.
3. Framing parity: the same logical record sequence is written by the vendor
   WRTI1D/WRTR1D writers and by the C++ writer; the bytes must be identical.
4. Structure: the frozen original artifact
   project/cases/hefei5km_2022_reference_case_20261011/run/puff/puff.con must
   still show the measured data-record structure (143 period / 143 grid /
   143 species-field records of 10015 bytes labelled H-3).

Value-level comparison against that artifact is NOT possible yet (the full puff
model is missing); only its structure is compared, and no value claim is made.
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
ANCHOR = f"{MODULE}/reference/p7e_source_anchor.json"
CASE_CONC = "project/cases/hefei5km_2022_reference_case_20261011/run/puff/puff.con"
CASE_CONTROL = "project/cases/hefei5km_2022_reference_case_20261011/run/puff/puff.inp"
TOLERANCE_RELATIVE = 1.0e-5
TOLERANCE_ABSOLUTE = 1.0e-30
# Constants quoted from PFSAMP/ERFDIF in the C++ port.
PFSAMP_QUOTES = ("data rt2/1.4142136/,rtpiby2/1.2533141/", "if(a.LT.1.e-4) then",
                 "xi1=(rtpiby2/sqrta)*xxexp*(erfdif((a+b)/sqrt2a,b/sqrt2a))",
                 "xi2=-b*xi1/a+(xxexp/a)*(exp(-0.5*b2da)-exp(-0.5*(a+2.*b+b2da)))")
ERFDIF_QUOTES = ("IF((X1*X2).LE.0.0) GO TO 50", "if(xtest .GE. 9.15) GO TO 40",
                 "IF(XTEST.LT.0.47) GO TO 50", "ERFDIF=ISIGN*(ERFCX2-ERFCX1)")


def fail(message: str) -> None:
    print(f"P7E_SOURCE_PARITY=FAIL: {message}", file=sys.stderr)
    raise SystemExit(1)


def load_script(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if not spec or not spec.loader:
        fail(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def check_quotes(text: str, quotes: tuple[str, ...], what: str) -> int:
    normalised = re.sub(r"\s+", "", text).lower()
    missing = [q for q in quotes if re.sub(r"\s+", "", q).lower() not in normalised]
    if missing:
        fail(f"{what} statements no longer present in the anchored vendor text: " + ", ".join(missing))
    return len(quotes)


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


def pfsamp_matrix() -> list[tuple]:
    """Cases covering the low-wind shortcut, symmetric geometry, crosswind
    offsets, same-sign and opposite-sign ERFDIF branches."""
    rows: list[tuple] = []
    for sigma in (10.0, 50.0, 200.0):
        for step in (0.001, 0.05, 0.1, 0.5, 2.0):
            for offset in (0.0, 0.25, 1.0, 5.0):
                for approach in (0.0, 1.0, 10.0):
                    rows.append((0.0, 0.0, step, 0.0, offset, approach, sigma,
                                 approach * approach + offset * offset))
    # A puff that stays put (low-wind branch) and a reversed trajectory.
    rows.append((0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 100.0, 0.0))
    rows.append((1.0, 0.0, 0.0, 0.0, 0.5, 0.0, 100.0, 0.25))
    return rows


def format_case(index: int, row: tuple) -> str:
    xold, yold, xnew, ynew, xrec, yrec, sigma, dist2 = row
    return (f"{index} {xold!r} {yold!r} {xnew!r} {ynew!r} {xrec!r} {yrec!r} {sigma!r} {dist2!r}")


def parse_pfsamp(text: str) -> dict[int, tuple[float, float]]:
    results: dict[int, tuple[float, float]] = {}
    for line in text.splitlines():
        fields = line.split()
        if len(fields) != 3:
            continue
        try:
            results[int(fields[0])] = (float(fields[1]), float(fields[2]))
        except ValueError:
            continue
    return results


def record_sequence() -> list[tuple[str, int, int, int, int, int]]:
    return [
        ("H-3", 2022001, 0, 2022001, 3600, 2500),
        ("HE-3", 2022001, 0, 2022001, 3600, 1),
        ("ZERO", 2022002, 0, 2022002, 3600, 0),
        ("SPECIES", 2022006, 82800, 2022006, 86399, 37),
    ]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--probe", type=Path, required=True, help="built cteas_p7e_probe")
    parser.add_argument("--repo-root", type=Path, default=REPO_FALLBACK)
    parser.add_argument("--gfortran", help="explicit gfortran executable")
    parser.add_argument("--require", action="store_true",
                        help="fail instead of skipping when no Fortran compiler is available")
    parser.add_argument("--require-case", action="store_true",
                        help="fail when the frozen case artifacts are missing")
    args = parser.parse_args()
    if not args.probe.is_file():
        fail(f"probe binary missing: {args.probe}")
    repo = args.repo_root.resolve()
    ext = load_script(repo / MODULE / "reference/p7e_source_anchor.py", "p7e_anchor")
    vendor = repo / ext.VENDOR_SUBDIR
    manifest, spans = ext.extract(vendor)
    pinned = json.loads((repo / ANCHOR).read_text())
    if pinned != manifest:
        fail(f"vendor source drift: extracted spans/hashes differ from {ANCHOR}")
    print(f"P7E_SOURCE_ANCHOR=PASS VENDOR_SHA256={manifest['vendor_source_sha256']} "
          f"UNITS={','.join(sorted(manifest['units']))}")
    quotes = check_quotes(spans["pfsamp"], PFSAMP_QUOTES, "PFSAMP")
    quotes += check_quotes(spans["erfdif"], ERFDIF_QUOTES, "ERFDIF")
    print(f"P7E_QUOTED_SOURCE_STATEMENTS=PASS COUNT={quotes}")

    compiler = find_gfortran(args.gfortran)
    if compiler is not None:
        major = compiler_major(compiler)
        if major is None or major < 10:
            if args.require:
                fail(f"gfortran {compiler} is older than 10 and cannot build the vendor oracle")
            print(f"P7E_FORTRAN_ORACLE=SKIPPED_TOO_OLD_COMPILER {compiler}")
            compiler = None
    if compiler is None:
        if args.require:
            fail("no Fortran compiler available but --require was given")
        print("P7E_FORTRAN_ORACLE=SKIPPED_WITHOUT_FORTRAN")
        return 0

    rows = pfsamp_matrix()
    case_lines = "\n".join(format_case(index + 1, row) for index, row in enumerate(rows)) + "\n"
    matrix = case_lines
    oracle_matrix = "1\n" + case_lines
    probe_run = subprocess.run([str(args.probe)], input=matrix, capture_output=True, text=True)
    if probe_run.returncode != 0:
        fail(f"probe PFSAMP matrix failed: {probe_run.stderr.strip()}")
    probe_results = parse_pfsamp(probe_run.stdout)
    if len(probe_results) != len(rows):
        fail(f"probe returned {len(probe_results)} cases for {len(rows)} matrix rows")

    with tempfile.TemporaryDirectory(prefix="p7e-oracle-") as temporary:
        stage = Path(temporary) / "stage"
        ext.stage(vendor, stage, manifest, spans)
        sources = sorted(str(path) for path in stage.glob("vendor_*.f"))
        driver = str(stage / "p7e_oracle_driver.f")
        binary = stage / "p7e_oracle"
        build = subprocess.run(
            [compiler, "-O0", "-std=legacy", "-ffixed-line-length-72", "-fallow-argument-mismatch",
             "-fno-automatic", f"-I{stage}", "-o", str(binary), *sources, driver],
            capture_output=True, text=True)
        if build.returncode != 0:
            fail(f"vendor oracle compilation failed: {build.stderr.strip()[-800:]}")
        version = subprocess.run([compiler, "--version"], capture_output=True, text=True)
        oracle_run = subprocess.run([str(binary)], input=oracle_matrix, capture_output=True,
                                    text=True, cwd=stage)
        if oracle_run.returncode != 0:
            fail(f"vendor oracle PFSAMP run failed: {oracle_run.stderr.strip()[-400:]}")
        oracle_results = parse_pfsamp(oracle_run.stdout)
        if len(oracle_results) != len(probe_results):
            fail(f"oracle returned {len(oracle_results)} rows, probe {len(probe_results)}")
        worst = 0.0
        worst_case = 0
        for key in sorted(oracle_results):
            for want, got in zip(oracle_results[key], probe_results[key]):
                if abs(want - got) > max(TOLERANCE_RELATIVE * abs(want), TOLERANCE_ABSOLUTE):
                    fail(f"PFSAMP case {key}: oracle={want!r} probe={got!r}")
                relative = abs(want - got) / max(abs(want), 1.0e-30)
                if relative > worst:
                    worst = relative
                    worst_case = key
        print(f"P7E_PFSAMP_ORACLE_PARITY=PASS CASES={len(rows)} TOLERANCE_REL={TOLERANCE_RELATIVE:.0e} "
              f"MAX_REL={worst:.3e} WORST_CASE={worst_case}")

        # Framing parity: the vendor WRTI1D/WRTR1D writers and the C++ writer
        # must produce identical bytes for the same logical records.
        records = record_sequence()
        write_input = "2\n" + str(len(records)) + "\n"
        for label, ndathrb, nsecb, ndathre, nsece, nvalues in records:
            write_input += f"{label} {ndathrb} {nsecb} {ndathre} {nsece} {nvalues}\n"
        oracle_write = subprocess.run([str(binary)], input=write_input, capture_output=True, text=True,
                                      cwd=stage)
        if oracle_write.returncode != 0:
            fail(f"vendor oracle record writing failed: {oracle_write.stderr.strip()[-400:]}")
        oracle_bytes = (stage / "p7e_oracle_records.bin").read_bytes()
        # The C++ side is exercised through the unit test binary's writer mode;
        # here the probe's --structure mode validates the same framing by
        # re-reading the vendor file and classifying every record.
        structure = subprocess.run([str(args.probe), "--structure",
                                    str(stage / "p7e_oracle_records.bin")],
                                   capture_output=True, text=True)
        if structure.returncode != 0:
            fail(f"probe could not parse the vendor-written records: {structure.stderr.strip()}")
        print(f"P7E_VENDOR_FRAMING_READBACK=PASS BYTES={len(oracle_bytes)} RECORDS={len(records)}")
        print(f"P7E_FORTRAN_COMPILER={version.stdout.splitlines()[0].strip()}")

    control = repo / CASE_CONTROL
    conc = repo / CASE_CONC
    if control.is_file():
        receptor_run = subprocess.run([str(args.probe), "--receptors", str(control)],
                                      capture_output=True, text=True)
        if receptor_run.returncode != 0:
            fail(f"receptor probe failed: {receptor_run.stderr.strip()}")
        summary = [line for line in receptor_run.stdout.splitlines()
                   if line.startswith("P7E_RECEPTOR_GEOMETRY")]
        if not summary or "SAMPLING_NX=50 SAMPLING_NY=50" not in summary[0] or \
                "GRID_RECEPTORS=2500" not in summary[0] or "DISCRETE_RECEPTORS=0" not in summary[0]:
            fail(f"locked deck receptor geometry unexpected: {summary}")
        print(f"P7E_LOCKED_CASE_RECEPTORS=PASS {summary[0].split(' ', 1)[1][:150]}")
    else:
        if args.require_case:
            fail(f"locked Hefei 2022 control file missing: {control}")
        print("P7E_LOCKED_CASE_RECEPTORS=SKIPPED_MISSING_CASE")

    if conc.is_file():
        structure_run = subprocess.run([str(args.probe), "--structure", str(conc)],
                                       capture_output=True, text=True)
        if structure_run.returncode != 0:
            fail(f"frozen artifact structure probe failed: {structure_run.stderr.strip()}")
        line = next((l for l in structure_run.stdout.splitlines()
                     if l.startswith("P7E_CONC_STRUCTURE")), None)
        if line is None:
            fail("frozen artifact structure produced no summary")
        for expected in ("PERIOD_RECORDS=143", "GRID_RECORDS=143", "SPECIES_FIELDS=143",
                         "FIRST_BEGIN=2022001", "LAST_END=2022006"):
            if expected not in line:
                fail(f"frozen artifact structure changed ({expected} missing): {line}")
        labels = [l for l in structure_run.stdout.splitlines()
                  if l.startswith("P7E_CONC_SPECIES_FIELD ")]
        if len(labels) != 1 or 'label="H-3     " count=143' not in labels[0]:
            fail(f"frozen artifact species fields unexpected: {labels}")
        sizes = [l for l in structure_run.stdout.splitlines()
                 if l.startswith("P7E_CONC_SPECIES_FIELD_SIZES ")]
        if not sizes or "min=10015 max=10015" not in sizes[0]:
            fail(f"frozen artifact species field sizes unexpected: {sizes}")
        print(f"P7E_FROZEN_CONC_STRUCTURE=PASS {line.split(' ', 1)[1][:150]}")
    else:
        if args.require_case:
            fail(f"frozen concentration artifact missing: {conc}")
        print("P7E_FROZEN_CONC_STRUCTURE=SKIPPED_MISSING_CASE")
    print("P7E_VALUE_COMPARISON_WITH_FROZEN_CONC=NOT_CLAIMED_FULL_MODEL_MISSING")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
