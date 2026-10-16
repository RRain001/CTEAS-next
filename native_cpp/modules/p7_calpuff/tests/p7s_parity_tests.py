#!/usr/bin/env python3
"""P7S terrain-state producers: vendor source anchor and Fortran parity.

Builds the UNMODIFIED vendor units TERAVG, TRELIEF and GETELEV with a hand-written
driver that fills /METHD/ from the case line and stubs GETCELL, then compares them
against the ported module through the case matrices `cteas_p7s_probe` prints.
Each case is two records: a header, then the nx*ny elevation grid.
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
ANCHOR = f"{MODULE}/reference/p7s_source_anchor.json"
TOLERANCE_RELATIVE = 1.0e-5
TOLERANCE_ABSOLUTE = 1.0e-30

QUOTES = {
    "teravg": ("data zero/0.0/, tan225/0.4142136/", "if(i0.EQ.i) then",
               "idel=INT(FLOAT(jdel)*tan225)", "elseif(j0.EQ.j) then",
               "elseif((j-j0).EQ.(i-i0)) then", "elseif((j-j0).EQ.-(i-i0)) then",
               "if(MOD(ii,2).EQ.0 .AND. MOD(jj,2).EQ.0) then", "elavg=tsum/nsum"),
    "trelief": ("data zero/0.0/, one/1.0/, beta/1.0/", "do md=1,ngrid",
                "reliefi=delh1", "rr=ABS(delh/delh1-one)", "if(rr.LE.beta) then",
                "rplus=ABS(reliefi+reliefd)", "rminus=ABS(reliefi-reliefd)",
                "relief(1,i,j,md)=rplus", "rise=AMAX1(rise,reliefi)",
                "rise=AMAX1(rise,-reliefd)", "relief(5,i,j,md)=elev(i,j,md)+rise"),
    "getelev": ("call GETCELL('GETELEV     ','GRIDIJ',1,x,y,zero,zero,i,j,md)",
                "if(nxm(md).eq.1 .AND. nym(md).eq.1) then",
                "xmd=x*nestfac(md)-rnxnest0(md)", "ixll=(xmd+0.5)", "ixll=min0(ixll,nxm1)",
                "t=(xmd-(ixll-0.5))", "z=onemt*onemu*elev(ixll,iyll,md)"),
}


def fail(message: str) -> None:
    print(f"P7S_SOURCE_PARITY=FAIL: {message}", file=sys.stderr)
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
            elif kind == "ramp_x":
                values.append(100.0 * i)
            elif kind == "hill":
                values.append(100.0 - 10.0 * abs(i - (nx + 1) / 2) - 5.0 * abs(j - (ny + 1) / 2))
            else:
                values.append(float(10 * i + j))
    return values


def teravg_matrix() -> list[tuple]:
    rows = []
    for nx, ny in ((3, 3), (4, 5), (5, 4)):
        for kind in ("flat", "ramp_x", "hill", "ramp"):
            for i0 in (1, 2, nx):
                for j0 in (1, 2, ny):
                    for i in (1, (nx + 1) // 2, nx):
                        for j in (1, (ny + 1) // 2, ny):
                            if i0 == i or j0 == j or (j0 - j) == (i0 - i) or (j0 - j) == -(i0 - i):
                                rows.append((nx, ny, i0, j0, i, j, grid(nx, ny, kind)))
    return rows


def trelief_matrix() -> list[tuple]:
    rows = []
    for nx, ny in ((3, 3), (4, 4), (5, 3), (2, 5)):
        for kind in ("flat", "ramp_x", "hill", "ramp"):
            rows.append((nx, ny, grid(nx, ny, kind)))
    return rows


def getelev_matrix() -> list[tuple]:
    rows = []
    for nx, ny in ((3, 3), (4, 4), (1, 1), (1, 4)):
        for kind in ("flat", "ramp_x", "hill"):
            for x in (1.0, 1.5, 2.0, nx - 0.5):
                for y in (1.5, (ny + 1) / 2):
                    rows.append((nx, ny, x, y, grid(nx, ny, kind)))
    return rows


def parse_rows(text: str) -> dict[int, list[float]]:
    rows: dict[int, list[float]] = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("P7S_") or line.startswith("{"):
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
    print(f"P7S_{what.upper()}_ORACLE_PARITY=PASS CASES={len(oracle_rows)} "
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
    parser.add_argument("--probe", type=pathlib.Path, required=True, help="built cteas_p7s_probe")
    parser.add_argument("--repo-root", type=pathlib.Path, default=REPO_FALLBACK)
    parser.add_argument("--gfortran", help="explicit gfortran executable")
    parser.add_argument("--require", action="store_true",
                        help="fail instead of skipping when no Fortran compiler is available")
    args = parser.parse_args()
    if not args.probe.is_file():
        fail(f"probe binary missing: {args.probe}")
    repo = args.repo_root.resolve()
    ext = load_script(repo / MODULE / "reference/p7s_source_anchor.py", "p7s_anchor")
    vendor = repo / ext.VENDOR_SUBDIR
    manifest, spans = ext.extract(vendor)
    pinned = json.loads((repo / ANCHOR).read_text())
    if pinned != manifest:
        fail(f"vendor source drift: extracted spans/hashes differ from {ANCHOR}")
    print(f"P7S_SOURCE_ANCHOR=PASS VENDOR_SHA256={manifest['vendor_source_sha256']} "
          f"UNITS={','.join(sorted(manifest['units']))} "
          f"PINNED={','.join(sorted(manifest['pinned_units']))}")
    pinned_units = manifest["pinned_units"]
    if pinned_units["vwidth"]["calls"]:
        fail(f"VWIDTH call closure changed: {pinned_units['vwidth']['calls']}")
    print("P7S_PINNED_UNITS=PASS GETCELL_LINES=" +
          f"{pinned_units['getcell']['first_line']}-{pinned_units['getcell']['last_line']} " +
          "VWIDTH_LINES=" +
          f"{pinned_units['vwidth']['first_line']}-{pinned_units['vwidth']['last_line']} " +
          "VWIDTH_CALLS=none")
    quotes = 0
    for name, quoted in QUOTES.items():
        quotes += check_quotes(spans[name], quoted, name.upper())
    print(f"P7S_QUOTED_SOURCE_STATEMENTS=PASS COUNT={quotes}")

    compiler = find_gfortran(args.gfortran)
    if compiler is not None:
        major = compiler_major(compiler)
        if major is None or major < 10:
            if args.require:
                fail(f"gfortran {compiler} is older than 10 and cannot build the vendor oracle")
            print(f"P7S_FORTRAN_ORACLE=SKIPPED_TOO_OLD_COMPILER {compiler}")
            compiler = None
    if compiler is None:
        if args.require:
            fail("no Fortran compiler available but --require was given")
        print("P7S_FORTRAN_ORACLE=SKIPPED_WITHOUT_FORTRAN")
        return 0

    with tempfile.TemporaryDirectory(prefix="p7s-oracle-") as temporary:
        stage = pathlib.Path(temporary) / "stage"
        ext.stage(vendor, stage, manifest, spans)
        sources = sorted(str(path) for path in stage.glob("vendor_*.f"))
        binary = stage / "p7s_oracle"
        build = subprocess.run(
            [compiler, "-O0", "-std=legacy", "-ffixed-line-length-72", "-fallow-argument-mismatch",
             "-fno-automatic", f"-I{stage}", "-o", str(binary), *sources,
             str(stage / "p7s_oracle_driver.f")],
            capture_output=True, text=True)
        if build.returncode != 0:
            fail(f"vendor oracle compilation failed: {build.stderr.strip()[-800:]}")
        version = subprocess.run([compiler, "--version"], capture_output=True, text=True)

        total = 0
        for mode, flag, rows in ((1, "--teravg-matrix", teravg_matrix()),
                                 (2, "--trelief-matrix", trelief_matrix()),
                                 (3, "--getelev-matrix", getelev_matrix())):
            lines = []
            for index, row in enumerate(rows):
                header = " ".join(repr(value) for value in row[:-1])
                lines.append(f"{index + 1} {header}")
                lines.append(" ".join(repr(value) for value in row[-1]))
            payload = "\n".join(lines) + "\n"
            oracle_rows, probe_rows = run_pair(args.probe, binary, mode, flag, payload, stage)
            total += compare(flag[2:-7], oracle_rows, probe_rows)
        print(f"P7S_ORACLE_PARITY_TOTAL_CASES={total}")
        print(f"P7S_FORTRAN_COMPILER={version.stdout.splitlines()[0].strip()}")
    print("P7S_TERRAIN_STATE_PARITY_IS_NOT_A_CONCENTRATION_COMPARISON=true")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
