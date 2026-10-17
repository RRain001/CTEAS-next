#!/usr/bin/env python3
"""P7R MCTADJ=2 terrain constraints: vendor source anchor and Fortran parity.

Builds the UNMODIFIED vendor units CTADJ2 and WALLTRAP with a hand-written driver
that supplies deterministic terrain lookups and fills the /GRID/ and /METHD/ state,
then compares them against the ported terrain module through the case matrices
`cteas_p7r_probe` prints.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import math
import pathlib
import re
import subprocess
import sys
import tempfile

REPO_FALLBACK = pathlib.Path(__file__).resolve().parents[4]
MODULE = "native_cpp/modules/p7_calpuff"
ANCHOR = f"{MODULE}/reference/p7r_source_anchor.json"
TOLERANCE_RELATIVE = 1.0e-5
TOLERANCE_ABSOLUTE = 1.0e-30

QUOTES = {
    "ctadj2": ("r=AMIN1(1.0,r)", "call GETCELL('CTADJ2_1    ','GRIDIJ',1,xold,yold,zero,zero,",
               "call GETELEV(xold,yold,elold)", "rise=elnew-elold", "if(rise.GT.zero) then",
               "rlf=AMAX1(relief(1,icello,jcello,mdo),", "eltop=AMAX1(relief(5,icello,jcello,mdo),",
               "if(delx.LE.small .OR. arise.LE.small) then", "slope=rise/delx",
               "elds=eltop-ws/bvf", "fracz=(elds-elold)/rise",
               "fraczs=(zpold-1.8*szold)/(rise+1.8*(sznew-szold))", "etabyh=AMAX1(0.1,zp/rlf)",
               "fri=AMIN1(one,fri)", "etabyl=two*etabyh*aslope", "strat=fri*etabyh",
               "trig=sinln/(cosln-expnl)", "xbyl=-SQRT(third*(one+two*aslope*(one-expnli)/etabyl))",
               "tz=one/tzi", "dtz=-dxbyl*(two*aslope*tzsq/(etabyl*(one+xbyl2)**2)) *",
               "strain=SQRT(strain)"),
    "walltrap": ("data rcrit/0.4/", "if(bvf.LE.zero) goto 500",
                 "eltop=AMAX1(relief(5,ixb,jyb,mdb),relief(5,ixe,jye,mde))",
                 "elds=eltop-ws/bvf", "zgrid=z/dzval", "if(izbot.EQ.0) then",
                 "if(izbot.GE.mxvalz) goto 500", "if(ivalw(iztop,ixb,jyb,mdb).EQ.-1) goto 500",
                 "rb=syb/wb", "re=sye/we", "if(AMAX1(rb,re).LE.rcrit) then",
                 "elseif(AMIN1(rb,re).GE.rcrit) then", "sye=syb",
                 "frac=AMAX1(zero,(syb-rcrit*wb)/((we-wb)*rcrit-(sye-syb)))",
                 "sye=syb+f*(sye-syb)"),
}


def fail(message: str) -> None:
    print(f"P7R_SOURCE_PARITY=FAIL: {message}", file=sys.stderr)
    raise SystemExit(1)


def load_script(path: pathlib.Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def check_quotes(text: str, quotes: tuple[str, ...], what: str) -> int:
    normalised = re.sub(r"\s+", "", text).lower()
    for quote in quotes:
        if re.sub(r"\s+", "", quote).lower() not in normalised:
            fail(f"{what}: quoted vendor statement is missing: {quote}")
    return len(quotes)


def compiler_major(compiler: str) -> int | None:
    run = subprocess.run([compiler, "-dumpversion"], capture_output=True, text=True)
    if run.returncode != 0:
        return None
    text = run.stdout.strip()
    return int(text) if text.isdigit() else None


def find_gfortran(explicit: str | None) -> str | None:
    candidates = [explicit] if explicit else ["gfortran-13", "gfortran-12", "gfortran-11", "gfortran"]
    for candidate in candidates:
        if candidate and subprocess.run(["which", candidate], capture_output=True).returncode == 0:
            return candidate
    return None


def ctadj2_matrix() -> list[tuple]:
    rows = []
    for ratio in (0.5, 1.0, 4.0):
        for zpold in (10.0, 70.0):
            for szold in (1.0, 5.0):
                for bvf in (0.0, 0.02, 0.05):
                    for grid in (0.1, 1.0):
                        for relief_pair in ((100.0, 120.0), (10.0, 200.0), (0.0, 0.0)):
                            for elevation_pair in ((50.0, 80.0), (100.0, 20.0)):
                                # 5 relief values for the old cell, then 5 for the new cell.
                                rows.append((ratio, zpold, 0.1, 0.5, 0.9, 0.5, szold, bvf, 1.4,
                                             grid, relief_pair[0], relief_pair[0], relief_pair[0],
                                             relief_pair[0], relief_pair[0], relief_pair[1],
                                             relief_pair[1], relief_pair[1], relief_pair[1],
                                             relief_pair[1], elevation_pair[0], elevation_pair[1]))
    return rows


def walltrap_matrix() -> list[tuple]:
    rows = []
    for syb, sye in ((500.0, 600.0), (500.0, 300.0), (100.0, 300.0), (0.0, 0.0)):
        for z in (10.0, 25.0, 1000.0):
            for bvf in (0.0, 0.05):
                for widths in ((10, 10, 10, 10, 10, 10), (-1, 10, 10, 10, 10, 10),
                               (10, 10, 10, 2, 2, 2)):
                    for elevations in ((50.0, 80.0), (100.0, 20.0)):
                        rows.append((syb, sye, z, 0.1, 0.5, 0.9, 0.5, bvf, 1.4, 10.0, 100.0,
                                     widths[0], widths[1], widths[2], widths[3], widths[4],
                                     widths[5], elevations[0], elevations[1], 100.0, 120.0))
    return rows


def parse_rows(text: str) -> dict[int, list[float]]:
    rows: dict[int, list[float]] = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("P7R_") or line.startswith("{"):
            continue
        fields = line.split()
        if len(fields) < 2:
            continue
        try:
            rows[int(fields[0])] = [float(value) for value in fields[1:]]
        except ValueError:
            continue
    return rows


def compare(what: str, oracle_rows: dict[int, list[float]], probe_rows: dict[int, list[float]],
            integer_columns: tuple[int, ...] = ()) -> int:
    if sorted(oracle_rows) != sorted(probe_rows):
        fail(f"{what}: case sets differ (oracle {len(oracle_rows)}, probe {len(probe_rows)})")
    worst = 0.0
    worst_absolute = 0.0
    worst_case = 0
    for key in sorted(oracle_rows):
        want_row = oracle_rows[key]
        got_row = probe_rows[key]
        if len(want_row) != len(got_row):
            fail(f"{what} case {key}: column count {len(want_row)} vs {len(got_row)}")
        for column, (want, got) in enumerate(zip(want_row, got_row)):
            if column in integer_columns:
                if int(want) != int(got):
                    fail(f"{what} case {key} column {column}: oracle={want!r} probe={got!r}")
                continue
            if not math.isfinite(want) or not math.isfinite(got):
                fail(f"{what} case {key} column {column}: non-finite {want!r} / {got!r}")
            if abs(want - got) > max(TOLERANCE_RELATIVE * abs(want), TOLERANCE_ABSOLUTE):
                fail(f"{what} case {key} column {column}: oracle={want!r} probe={got!r}")
            worst_absolute = max(worst_absolute, abs(want - got))
            relative = abs(want - got) / max(abs(want), 1.0e-30)
            if relative > worst:
                worst = relative
                worst_case = key
    print(f"P7R_{what.upper()}_ORACLE_PARITY=PASS CASES={len(oracle_rows)} "
          f"COLUMNS={len(next(iter(oracle_rows.values())))} MISMATCHES=0 "
          f"TOLERANCE_REL={TOLERANCE_RELATIVE:.0e} MAX_REL={worst:.3e} "
          f"MAX_ABS={worst_absolute:.3e} WORST_CASE={worst_case}")
    return len(oracle_rows)


def run_pair(probe: pathlib.Path, oracle: pathlib.Path, mode: int, probe_flag: str, payload: str,
             cwd: pathlib.Path) -> tuple[dict, dict]:
    probe_run = subprocess.run([str(probe), probe_flag], input=payload, capture_output=True,
                               text=True)
    if probe_run.returncode != 0:
        fail(f"{probe_flag}: probe failed: {probe_run.stderr.strip()[-400:]}")
    oracle_run = subprocess.run([str(oracle)], input=f"{mode}\n{payload}", capture_output=True,
                                text=True, cwd=cwd)
    if oracle_run.returncode != 0:
        fail(f"oracle mode {mode} failed: {oracle_run.stderr.strip()[-400:]}")
    return parse_rows(oracle_run.stdout), parse_rows(probe_run.stdout)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--probe", type=pathlib.Path, required=True, help="built cteas_p7r_probe")
    parser.add_argument("--repo-root", type=pathlib.Path, default=REPO_FALLBACK)
    parser.add_argument("--gfortran", help="explicit gfortran executable")
    parser.add_argument("--require", action="store_true",
                        help="fail instead of skipping when no Fortran compiler is available")
    args = parser.parse_args()
    if not args.probe.is_file():
        fail(f"probe binary missing: {args.probe}")
    repo = args.repo_root.resolve()
    ext = load_script(repo / MODULE / "reference/p7r_source_anchor.py", "p7r_anchor")
    vendor = repo / ext.VENDOR_SUBDIR
    manifest, spans = ext.extract(vendor)
    pinned = json.loads((repo / ANCHOR).read_text())
    if pinned != manifest:
        fail(f"vendor source drift: extracted spans/hashes differ from {ANCHOR}")
    print(f"P7R_SOURCE_ANCHOR=PASS VENDOR_SHA256={manifest['vendor_source_sha256']} "
          f"UNITS={','.join(sorted(manifest['units']))} "
          f"PINNED={','.join(sorted(manifest['pinned_units']))}")
    pinned_units = manifest["pinned_units"]
    if pinned_units["trelief"]["calls"] != ["teravg"]:
        fail(f"TRELIEF call closure changed: {pinned_units['trelief']['calls']}")
    print("P7R_PINNED_UNITS=PASS TRELIEF_LINES=" +
          f"{pinned_units['trelief']['first_line']}-{pinned_units['trelief']['last_line']} " +
          "TRELIEF_CALLS=teravg GETELEV_LINES=" +
          f"{pinned_units['getelev']['first_line']}-{pinned_units['getelev']['last_line']} " +
          "GETCELL_LINES=" +
          f"{pinned_units['getcell']['first_line']}-{pinned_units['getcell']['last_line']}")
    quotes = 0
    for name, quoted in QUOTES.items():
        quotes += check_quotes(spans[name], quoted, name.upper())
    print(f"P7R_QUOTED_SOURCE_STATEMENTS=PASS COUNT={quotes}")

    compiler = find_gfortran(args.gfortran)
    if compiler is not None:
        major = compiler_major(compiler)
        if major is None or major < 10:
            if args.require:
                fail(f"gfortran {compiler} is older than 10 and cannot build the vendor oracle")
            print(f"P7R_FORTRAN_ORACLE=SKIPPED_TOO_OLD_COMPILER {compiler}")
            compiler = None
    if compiler is None:
        if args.require:
            fail("no Fortran compiler available but --require was given")
        print("P7R_FORTRAN_ORACLE=SKIPPED_WITHOUT_FORTRAN")
        return 0

    with tempfile.TemporaryDirectory(prefix="p7r-oracle-") as temporary:
        stage = pathlib.Path(temporary) / "stage"
        ext.stage(vendor, stage, manifest, spans)
        sources = sorted(str(path) for path in stage.glob("vendor_*.f"))
        binary = stage / "p7r_oracle"
        build = subprocess.run(
            [compiler, "-O0", "-std=legacy", "-ffixed-line-length-72", "-fallow-argument-mismatch",
             "-fno-automatic", f"-I{stage}", "-o", str(binary), *sources,
             str(stage / "p7r_oracle_driver.f")],
            capture_output=True, text=True)
        if build.returncode != 0:
            fail(f"vendor oracle compilation failed: {build.stderr.strip()[-800:]}")
        version = subprocess.run([compiler, "--version"], capture_output=True, text=True)

        total = 0
        for mode, flag, rows, integer_columns in (
                (1, "--ctadj2-matrix", ctadj2_matrix(), (3,)),
                (2, "--walltrap-matrix", walltrap_matrix(), (1,))):
            payload = "\n".join(f"{index + 1} " + " ".join(repr(value) for value in row)
                                for index, row in enumerate(rows)) + "\n"
            oracle_rows, probe_rows = run_pair(args.probe, binary, mode, flag, payload, stage)
            total += compare(flag[2:-7], oracle_rows, probe_rows, integer_columns)
        print(f"P7R_ORACLE_PARITY_TOTAL_CASES={total}")
        print(f"P7R_FORTRAN_COMPILER={version.stdout.splitlines()[0].strip()}")
    print("P7R_TERRAIN_PARITY_IS_NOT_A_CONCENTRATION_COMPARISON=true")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
