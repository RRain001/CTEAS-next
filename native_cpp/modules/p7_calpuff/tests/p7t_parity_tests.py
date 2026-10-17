#!/usr/bin/env python3
"""P7T VWIDTH: vendor source anchor and Fortran parity.

Builds the UNMODIFIED vendor unit `vwidth` with a hand-written driver that fills
/METHD/ and /GRIDNEST/ from the case line, then compares it against the ported
valley-width module through the case matrix `cteas_p7t_probe` prints. Each case is
two records: a header, then the nx*ny elevation grid.
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
ANCHOR = f"{MODULE}/reference/p7t_source_anchor.json"
TOLERANCE_RELATIVE = 1.0e-5
TOLERANCE_ABSOLUTE = 1.0e-30

QUOTES = {
    "vwidth": ("data big/9000./", "data dzmin/10./, qahit/0.5/", "do md=1,ngrid",
               "ivalw(k,i,j,md)=-1", "dzval=(zmax-zmin)/FLOAT(mxvalz)",
               "dzval=AMAX1(dzmin,dzval)", "if(k.GT.1 .AND. .NOT.lwidth .AND. dzval.GT.dzmin) then",
               "dzval=delz/FLOAT(mxvalz)", "if(ivalw(k-1,i,j,md).EQ.-1) goto 500",
               "ztarget=elev(i,j,md)+delz", "iqa=NINT(FLOAT(ixmax-ixmin)*qahit)+1",
               "lookNS=jy", "lookNS=lookNS-jy", "lookEW=ix", "lookEW=lookEW-ix",
               "itest=lookNS*lookEW", "ivalw(k,i,j,md)=MAX0(lookNS,lookEW)",
               "ivalw(k,i,j,md)=MIN0(lookNS,lookEW)", "if(ivalw(k,i,j,md).GT.1) lwidth=.TRUE.",
               "if(ivalw(k,i,j,md).NE.-1 .AND. ivalw(k,i,j,md).LT.2)then"),
}


def fail(message: str) -> None:
    print(f"P7T_SOURCE_PARITY=FAIL: {message}", file=sys.stderr)
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


def grid(nx: int, ny: int, kind: str) -> list[float]:
    values = []
    for j in range(1, ny + 1):
        for i in range(1, nx + 1):
            if kind == "flat":
                values.append(50.0)
            elif kind == "valley_ew":
                values.append(100.0 if (i == 1 or i == nx) else 25.0)
            elif kind == "valley_ns":
                values.append(100.0 if (j == 1 or j == ny) else 25.0)
            elif kind == "basin":
                edge = min(i, j, nx + 1 - i, ny + 1 - j)
                values.append(25.0 + 20.0 * edge)
            else:
                values.append(float(10 * i + j))
    return values


def valley_matrix() -> list[tuple]:
    rows = []
    for nx, ny in ((5, 5), (7, 7), (9, 5), (4, 8)):
        for kind in ("flat", "valley_ew", "valley_ns", "basin", "ramp"):
            rows.append((nx, ny, grid(nx, ny, kind)))
    return rows


def parse_rows(text: str) -> dict[int, list[float]]:
    rows: dict[int, list[float]] = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("P7T_") or line.startswith("{"):
            continue
        fields = line.split()
        if len(fields) < 2:
            continue
        try:
            rows[int(fields[0])] = [float(value) for value in fields[1:]]
        except ValueError:
            continue
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--probe", type=pathlib.Path, required=True, help="built cteas_p7t_probe")
    parser.add_argument("--repo-root", type=pathlib.Path, default=REPO_FALLBACK)
    parser.add_argument("--gfortran", help="explicit gfortran executable")
    parser.add_argument("--require", action="store_true",
                        help="fail instead of skipping when no Fortran compiler is available")
    args = parser.parse_args()
    if not args.probe.is_file():
        fail(f"probe binary missing: {args.probe}")
    repo = args.repo_root.resolve()
    ext = load_script(repo / MODULE / "reference/p7t_source_anchor.py", "p7t_anchor")
    vendor = repo / ext.VENDOR_SUBDIR
    manifest, spans = ext.extract(vendor)
    pinned = json.loads((repo / ANCHOR).read_text())
    if pinned != manifest:
        fail(f"vendor source drift: extracted spans/hashes differ from {ANCHOR}")
    print(f"P7T_SOURCE_ANCHOR=PASS VENDOR_SHA256={manifest['vendor_source_sha256']} "
          f"UNITS={','.join(sorted(manifest['units']))} "
          f"PRODUCES={','.join(manifest['produced'])}")
    quotes = check_quotes(spans["vwidth"], QUOTES["vwidth"], "VWIDTH")
    print(f"P7T_QUOTED_SOURCE_STATEMENTS=PASS COUNT={quotes}")

    compiler = find_gfortran(args.gfortran)
    if compiler is not None:
        major = compiler_major(compiler)
        if major is None or major < 10:
            if args.require:
                fail(f"gfortran {compiler} is older than 10 and cannot build the vendor oracle")
            print(f"P7T_FORTRAN_ORACLE=SKIPPED_TOO_OLD_COMPILER {compiler}")
            compiler = None
    if compiler is None:
        if args.require:
            fail("no Fortran compiler available but --require was given")
        print("P7T_FORTRAN_ORACLE=SKIPPED_WITHOUT_FORTRAN")
        return 0

    with tempfile.TemporaryDirectory(prefix="p7t-oracle-") as temporary:
        stage = pathlib.Path(temporary) / "stage"
        ext.stage(vendor, stage, manifest, spans)
        sources = sorted(str(path) for path in stage.glob("vendor_*.f"))
        binary = stage / "p7t_oracle"
        build = subprocess.run(
            [compiler, "-O0", "-std=legacy", "-ffixed-line-length-72", "-fallow-argument-mismatch",
             "-fno-automatic", f"-I{stage}", "-o", str(binary), *sources,
             str(stage / "p7t_oracle_driver.f")],
            capture_output=True, text=True)
        if build.returncode != 0:
            fail(f"vendor oracle compilation failed: {build.stderr.strip()[-800:]}")
        version = subprocess.run([compiler, "--version"], capture_output=True, text=True)

        rows = valley_matrix()
        lines = []
        for index, row in enumerate(rows):
            lines.append(f"{index + 1} {row[0]} {row[1]}")
            lines.append(" ".join(repr(value) for value in row[2]))
        payload = "\n".join(lines) + "\n"
        probe_run = subprocess.run([str(args.probe), "--valley-matrix"], input=payload,
                                   capture_output=True, text=True)
        if probe_run.returncode != 0:
            fail(f"probe failed: {probe_run.stderr.strip()[-400:]}")
        oracle_run = subprocess.run([str(binary)], input=f"1\n{payload}", capture_output=True,
                                    text=True, cwd=stage)
        if oracle_run.returncode != 0:
            fail(f"oracle failed: {oracle_run.stderr.strip()[-400:]}")
        probe_rows = parse_rows(probe_run.stdout)
        oracle_rows = parse_rows(oracle_run.stdout)
        if sorted(oracle_rows) != sorted(probe_rows):
            fail(f"case sets differ (oracle {len(oracle_rows)}, probe {len(probe_rows)})")
        worst = 0.0
        worst_case = 0
        for key in sorted(oracle_rows):
            want_row = oracle_rows[key]
            got_row = probe_rows[key]
            if len(want_row) != len(got_row):
                fail(f"case {key}: column count {len(want_row)} vs {len(got_row)}")
            for column, (want, got) in enumerate(zip(want_row, got_row)):
                if not math.isfinite(want) or not math.isfinite(got):
                    fail(f"case {key} column {column}: non-finite {want!r} / {got!r}")
                if abs(want - got) > max(TOLERANCE_RELATIVE * abs(want), TOLERANCE_ABSOLUTE):
                    fail(f"case {key} column {column}: oracle={want!r} probe={got!r}")
                relative = abs(want - got) / max(abs(want), 1.0e-30)
                if relative > worst:
                    worst = relative
                    worst_case = key
        print(f"P7T_VWIDTH_ORACLE_PARITY=PASS CASES={len(oracle_rows)} "
              f"COLUMNS={len(next(iter(oracle_rows.values())))} MISMATCHES=0 "
              f"TOLERANCE_REL={TOLERANCE_RELATIVE:.0e} MAX_REL={worst:.3e} WORST_CASE={worst_case}")
        print(f"P7T_FORTRAN_COMPILER={version.stdout.splitlines()[0].strip()}")
    print("P7T_VALLEY_WIDTH_PARITY_IS_NOT_A_CONCENTRATION_COMPARISON=true")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
