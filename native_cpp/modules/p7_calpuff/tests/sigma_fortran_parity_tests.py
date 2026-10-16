#!/usr/bin/env python3
"""P7D dispersion coefficients: vendor source anchor and Fortran parity.

Two independent checks against the UNMODIFIED vendor source
(engine/vendor/src/CALPUFF_v7.2.1_L150618):

1. Table/section anchors: the vendor file and the exact spans of the MDISP=3
   dispersion units must match reference/sigma_source_anchor.json, and every
   PG/MP constant read out of the vendor DATA statements must equal the table
   compiled into the C++ probe (bit-exact as REAL*4), with the sigma-z segment
   junctions recomputed from the vendor A/B pairs using the SIGSET rule.
2. Numerical parity: the extracted vendor units are compiled unchanged with
   gfortran (P4/P7 harness convention: -std=legacy -ffixed-line-length-72
   -fallow-argument-mismatch -fno-automatic) into a private oracle and compared
   with the C++ probe over a deterministic case matrix.

The comparison is a dispersion-coefficient (sigma) contract only: no puff
advection, concentration, deposition or chemistry is involved.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import math
import re
import struct
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_FALLBACK = Path(__file__).resolve().parents[4]
MODULE = "native_cpp/modules/p7_calpuff"
ANCHOR = f"{MODULE}/reference/sigma_source_anchor.json"
TOLERANCE_RELATIVE = 1.0e-5
TOLERANCE_ABSOLUTE = 1.0e-6
FLOAT32 = struct.Struct("<f")
# Fortran REAL*4 comparison of a parsed decimal literal.
def as_float32(value: float) -> float:
    return FLOAT32.unpack(FLOAT32.pack(value))[0]


def fail(message: str) -> None:
    print(f"P7D_SIGMA_SOURCE_PARITY=FAIL: {message}", file=sys.stderr)
    raise SystemExit(1)


def load_script(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if not spec or not spec.loader:
        fail(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def join_continuations(text: str) -> list[str]:
    """Fixed-form continuation lines carry a non-blank, non-zero col-6 mark."""
    statements: list[str] = []
    for line in text.splitlines():
        mark = line[5] if len(line) > 5 else " "
        if mark not in (" ", "0") and statements:
            statements[-1] += " " + line[6:]
        else:
            statements.append(line)
    return statements


def split_data_statement(statement: str) -> dict[str, list[str]]:
    body = statement[statement.lower().find("data") + 4 :]
    groups: dict[str, list[str]] = {}
    for match in re.finditer(r"([a-zA-Z][a-zA-Z0-9_]*)\s*/([^/]*)/", body):
        name = match.group(1).lower()
        values = [item.strip() for item in match.group(2).split(",") if item.strip()]
        groups.setdefault(name, []).extend(values)
    return groups


def parse_loaded_values(name: str, entries: list[str]) -> list[float]:
    values: list[float] = []
    for entry in entries:
        repeat = 1
        text = entry
        if "*" in text:
            count, text = text.split("*", 1)
            count = count.strip()
            if not count.isdigit():
                fail(f"vendor DATA group {name}: symbolic repeat count {count!r} is not supported")
            repeat = int(count)
            text = text.strip()
        try:
            value = float(text.replace("D", "E").replace("d", "e"))
        except ValueError:
            fail(f"vendor DATA group {name}: unparsable value {entry!r}")
        values.extend([value] * repeat)
    return values


def vendor_tables(units: dict[str, str], vendor: Path) -> dict[str, list[float]]:
    # Only the dispersion constants are read, and only from the unit that owns
    # them, so unrelated BLOCK DATA groups (some of which use symbolic repeat
    # counts such as mxspec*1.0E-07) are never touched.
    sources = {
        "ayurb": "block_data", "xiyurb": "block_data", "azurb": "block_data",
        "xizurb": "block_data", "nzbrur": "block_data", "xzbrur": "block_data",
        "azrur": "block_data", "bzrur": "block_data", "ayt": "block_data",
        "azt": "block_data", "aypgt": "block_data", "bypgt": "block_data",
        "syh": "block_data", "szh": "block_data", "c": "sigty", "d": "sigty",
    }
    counts = {
        "ayurb": 6, "xiyurb": 6, "azurb": 6, "xizurb": 6, "nzbrur": 6,
        "xzbrur": 60, "azrur": 60, "bzrur": 60, "ayt": 1, "azt": 6,
        "aypgt": 6, "bypgt": 6, "syh": 1, "szh": 1, "c": 6, "d": 6,
    }
    grouped: dict[str, dict[str, list[str]]] = {}
    for unit, text in units.items():
        for statement in join_continuations(text):
            if not statement.lstrip().lower().startswith("data"):
                continue
            for name, entries in split_data_statement(statement).items():
                grouped.setdefault(name, {}).setdefault(unit, []).extend(entries)
    tables: dict[str, list[float]] = {}
    for name, unit in sources.items():
        entries = grouped.get(name, {}).get(unit)
        if entries is None:
            fail(f"vendor unit {unit} no longer declares the dispersion DATA group {name}")
        values = parse_loaded_values(name, entries)
        if len(values) != counts[name]:
            fail(f"vendor DATA group {name} has {len(values)} values, expected {counts[name]}")
        tables[name] = values
    return tables


def probe_dump(probe: Path) -> dict[str, list[float]]:
    run = subprocess.run([str(probe), "--dump-tables"], capture_output=True, text=True)
    if run.returncode != 0:
        fail(f"probe --dump-tables failed: {run.stderr.strip()}")
    dump: dict[str, list[tuple[int, float]]] = {}
    for line in run.stdout.splitlines():
        fields = line.split()
        if len(fields) != 4 or fields[0] != "P7D_TABLE":
            continue
        dump.setdefault(fields[1], []).append((int(fields[2]), float(fields[3])))
    ordered: dict[str, list[float]] = {}
    for name, entries in dump.items():
        entries.sort()
        ordered[name] = [value for _, value in entries]
    return ordered


def compare_tables(vendor: dict[str, list[float]], dump: dict[str, list[float]]) -> int:
    mapping = {
        "ayurb": "ayurb", "xiyurb": "xiyurb", "azurb": "azurb", "xizurb": "xizurb",
        "nzbrur": "nzbrur", "azrur": "azrur", "bzrur": "bzrur",
        "ayt": "ayt", "azt": "azt", "aypgt": "aypgt", "bypgt": "bypgt",
        "syh": "syh", "szh": "szh", "c": "cy", "d": "dy",
    }
    # XZBRUR is compared after the SIGSET junction recomputation below, because
    # the vendor DATA sentinels are overwritten for every real junction.
    compared = 0
    for vendor_name, dump_name in mapping.items():
        expected = [as_float32(value) for value in vendor[vendor_name]]
        observed = dump.get(dump_name, [])
        if len(expected) != len(observed):
            fail(f"{vendor_name}: vendor has {len(expected)} values, probe has {len(observed)}")
        for index, (want, got) in enumerate(zip(expected, observed)):
            if as_float32(got) != want:
                fail(f"{vendor_name}[{index}]: vendor {want!r} != probe {got!r}")
            compared += 1
    # SIGSET junction rule: recompute XZBRUR from the vendor A/B pairs.
    segments = [int(value) for value in vendor["nzbrur"]]
    junctions = [as_float32(value) for value in vendor["xzbrur"]]
    recomputed = list(junctions)
    for class_index, count in enumerate(segments):
        base = class_index * 10
        for j in range(1, count):
            first, second = base + j - 1, base + j
            ratio = as_float32(as_float32(vendor["azrur"][first]) / as_float32(vendor["azrur"][second]))
            difference = as_float32(as_float32(vendor["bzrur"][second]) -
                                    as_float32(vendor["bzrur"][first]))
            cut = 1.0e20
            if difference > 0.0:
                cut = math.pow(ratio, as_float32(1.0) / difference)
            elif difference < 0.0:
                cut = math.pow(as_float32(1.0) / ratio, -1.0 / difference)
            recomputed[first] = as_float32(cut)
    worst = 0.0
    for index, (want, got) in enumerate(zip(recomputed, dump["xzbrur"])):
        deviation = abs(want - got) / max(abs(want), 1.0e-12)
        worst = max(worst, deviation)
        # The SIGSET junction is computed through powf in REAL*4 inside the
        # vendor routine; the recomputation here goes through double pow, so a
        # few float32 ulps of slack are expected (measured below and printed).
        if deviation > 1.0e-5:
            fail(f"xzbrur[{index}]: SIGSET junction {want!r} != probe {got!r} "
                 f"relative deviation {deviation:.3e}")
        compared += 1
    print(f"P7D_SIGMA_JUNCTION_RECOMPUTATION=MAX_REL={worst:.3e}")
    return compared


def case_matrix() -> list[tuple]:
    rows: list[tuple] = []
    speed = 3.0
    def add(urban, stability, mhftsz, sigy0, sigz0, dx, dt, zht, sytdep, avefac, yr, zaf, zb):
        rows.append((urban, stability, mhftsz, speed, sigy0, sigz0, dx, dt, zht, sytdep, avefac,
                     yr, zaf, zb))
    for stability in range(1, 7):
        for urban in (0, 1):
            for dx in (0.01, 0.05, 0.1, 0.2, 0.5, 1.0, 2.0, 5.0, 10.0, 20.0, 50.0, 100.0):
                add(urban, stability, 0, 0.0, 0.0, dx, dx * 1000.0 / speed, 0.0, 550.0, 1.0, 1.0,
                    1.0, -1000.0)
            for sigma in (1.0, 10.0, 100.0, 400.0):
                for dx in (0.0, 0.5, 5.0, 50.0):
                    add(urban, stability, 0, sigma, sigma, dx, dx * 1000.0 / speed, 0.0, 550.0, 1.0,
                        1.0, 1.0, -1000.0)
            for sytdep in (300.0, 550.0, 2000.0):
                for dt in (0.0, 100.0, 1000.0, 5000.0, 20000.0):
                    add(urban, stability, 0, 0.0, 0.0, dt * 0.003, dt, 0.0, sytdep, 1.0, 1.0, 1.0,
                        -1000.0)
            for avefac in (1.0, 1.5, 0.8):
                add(urban, stability, 0, 0.0, 0.0, 1.0, 333.333333, 0.0, 550.0, avefac, 1.0, 1.0,
                    -1000.0)
            for factors in ((1.2723, 1.4273, 0.028197), (1.5, 2.0, 0.05), (0.8, 0.5, -1000.0)):
                add(urban, stability, 0, 0.0, 0.0, 1.0, 333.333333, 0.0, 550.0, 1.0, *factors)
            for dx in (1.0, 100.0):
                add(urban, stability, 0, 25.0, 25.0, dx, dx * 1000.0 / speed, 50.0, 550.0, 1.0, 1.0,
                    1.0, -1000.0)
    return rows


def format_case(index: int, row: tuple) -> str:
    urban, stability, mhftsz, speed, sigy0, sigz0, dx, dt, zht, sytdep, avefac, yr, zaf, zb = row
    return (f"{index} 3 3 {urban} {stability} {mhftsz} {speed!r} {sigy0!r} {sigz0!r} {dx!r} {dt!r} "
            f"{zht!r} {sytdep!r} {avefac!r} {yr!r} {zaf!r} {zb!r}")


def parse_results(text: str) -> dict[int, list[float]]:
    results: dict[int, list[float]] = {}
    for line in text.splitlines():
        fields = line.split()
        if len(fields) != 8:
            continue
        try:
            results[int(fields[0])] = [float(value) for value in fields[1:]]
        except ValueError:
            continue
    return results


def find_gfortran(explicit: str | None) -> str | None:
    candidates = [explicit] if explicit else ["gfortran-13", "gfortran-12", "gfortran-11", "gfortran"]
    for candidate in candidates:
        if not candidate:
            continue
        found = subprocess.run(["sh", "-c", f"command -v {candidate}"], capture_output=True, text=True)
        if found.returncode == 0:
            return found.stdout.strip()
    return None


def compiler_major(compiler: str) -> int | None:
    run = subprocess.run([compiler, "-dumpversion"], capture_output=True, text=True)
    if run.returncode != 0:
        return None
    text = run.stdout.strip().split(".")[0]
    return int(text) if text.isdigit() else None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--probe", type=Path, required=True, help="built cteas_p7d_sigma_probe")
    parser.add_argument("--repo-root", type=Path, default=REPO_FALLBACK)
    parser.add_argument("--gfortran", help="explicit gfortran executable")
    parser.add_argument("--require", action="store_true",
                        help="fail instead of skipping when no Fortran compiler is available")
    args = parser.parse_args()
    if not args.probe.is_file():
        fail(f"probe binary missing: {args.probe}")
    repo = args.repo_root.resolve()
    anchor_path = repo / ANCHOR
    ext = load_script(repo / MODULE / "reference/sigma_source_anchor.py", "p7d_sigma_anchor")
    vendor = repo / ext.VENDOR_SUBDIR
    manifest, spans = ext.extract(vendor)
    pinned = json.loads(anchor_path.read_text())
    if pinned != manifest:
        fail("vendor dispersion source drift: extracted spans/hashes differ from "
             f"{anchor_path}; re-audit the vendor source before trusting the oracle")
    print(f"P7D_SIGMA_SOURCE_ANCHOR=PASS VENDOR_SHA256={manifest['vendor_source_sha256']} "
          f"UNITS={','.join(sorted(manifest['units']))}")

    tables = vendor_tables(spans, vendor)
    dump = probe_dump(args.probe)
    compared = compare_tables(tables, dump)
    print(f"P7D_SIGMA_VENDOR_TABLE_PARITY=PASS VALUES={compared} "
          f"INCLUDING_SIGSET_JUNCTIONS=true")

    compiler = find_gfortran(args.gfortran)
    if compiler is not None:
        major = compiler_major(compiler)
        if major is None or major < 10:
            # The vendor fixed-form sources need -fallow-argument-mismatch, which
            # only GNU Fortran 10+ accepts (same gate as the P7A reference build).
            if args.require:
                fail(f"gfortran {compiler} is older than 10 and cannot build the vendor oracle")
            print(f"P7D_SIGMA_FORTRAN_ORACLE=SKIPPED_TOO_OLD_COMPILER {compiler}")
            compiler = None
    if compiler is None:
        if args.require:
            fail("no Fortran compiler available but --require was given")
        print("P7D_SIGMA_FORTRAN_ORACLE=SKIPPED_WITHOUT_FORTRAN")
        return 0

    rows = case_matrix()
    matrix = "\n".join(format_case(index + 1, row) for index, row in enumerate(rows)) + "\n"
    probe_run = subprocess.run([str(args.probe)], input=matrix, capture_output=True, text=True)
    if probe_run.returncode != 0:
        fail(f"probe case matrix failed: {probe_run.stderr.strip()}")
    probe_results = parse_results(probe_run.stdout)
    if len(probe_results) != len(rows):
        fail(f"probe returned {len(probe_results)} cases for {len(rows)} matrix rows")

    with tempfile.TemporaryDirectory(prefix="p7d-sigma-oracle-") as temporary:
        stage = Path(temporary) / "stage"
        ext.stage(vendor, stage, manifest, spans)
        sources = sorted(str(path) for path in stage.glob("vendor_*.f"))
        driver = str(stage / "sigma_oracle_driver.f")
        binary = stage / "sigma_oracle"
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
        if len(oracle_results) != len(rows):
            fail(f"oracle returned {len(oracle_results)} cases for {len(rows)} matrix rows")

        worst_relative = 0.0
        worst_case = 0
        columns = ("sigma_y", "vtime_y", "vdist_y", "sigma_z", "vtime_z", "vdist_z", "thfty")
        for index in sorted(oracle_results):
            expected = oracle_results[index]
            observed = probe_results[index]
            for column, (want, got) in enumerate(zip(expected, observed)):
                if math.isnan(want) and math.isnan(got):
                    continue
                if not math.isfinite(want) or not math.isfinite(got):
                    fail(f"case {index} {columns[column]}: oracle={want!r} probe={got!r}")
                if abs(want - got) > max(TOLERANCE_RELATIVE * abs(want), TOLERANCE_ABSOLUTE):
                    fail(f"case {index} {columns[column]}: oracle={want!r} probe={got!r} "
                         f"tolerance rel={TOLERANCE_RELATIVE}")
                relative = abs(want - got) / max(abs(want), 1.0e-12)
                if relative > worst_relative:
                    worst_relative = relative
                    worst_case = index
        print(f"P7D_SIGMA_FORTRAN_ORACLE_PARITY=PASS CASES={len(rows)} "
              f"COLUMNS={len(columns)} TOLERANCE_REL={TOLERANCE_RELATIVE:.0e} "
              f"MAX_REL={worst_relative:.3e} WORST_CASE={worst_case}")
        print(f"P7D_SIGMA_FORTRAN_COMPILER={version.stdout.splitlines()[0].strip()}")
    print("P7D_SIGMA_SOURCE_PARITY_IS_NOT_A_CONCENTRATION_TEST=true")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
