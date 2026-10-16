#!/usr/bin/env python3
"""P7W RISEWIND: vendor source anchor and Fortran parity.

Builds the UNMODIFIED vendor unit `risewind` with a hand-written driver whose
GRISE and ADVECT are deterministic stubs (the already-closed P7N and P7V units are
exercised separately), then compares it against the ported rise-wind module through
the case matrix `cteas_p7w_probe --rise-wind` prints. The stubs isolate RISEWIND's
own iteration: the rise trajectory, the rise/fall layer selection, the final-rise
blend and the NCOUNT refinement.
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
ANCHOR = f"{MODULE}/reference/p7w_source_anchor.json"
TOLERANCE_RELATIVE = 1.0e-5
TOLERANCE_ABSOLUTE = 1.0e-30

QUOTES = {
    "risewind": ("data ucalm/0.001/", "ufnl=uadv", "vfnl=vadv", "if(LPUFF) then",
                 "xbeg=xtotb(ii)", "xbeg=half*(xtotb(ii)+xtote(ii))",
                 "if(xbeg.LT.xfinal(ii)) then", "rbeg=zfinal(ii)", "rtop=rbeg+dzb",
                 "rbot=rbeg-dzb", "rbot=AMAX1(rbot,zero)", "wsb=SQRT(ub**2+vb**2)",
                 "ws=AMAX1(wsb,ucalm)", "icount=icount+1", "dxb=ws*dt", "xend=xbeg+dxb",
                 "if(rend.GE.rbeg) then", "ffinal=one-xfinal(ii)/xend",
                 "uadv=(one-ffinal)*ugr+ffinal*ufnl", "ws=SQRT(uadv**2+vadv**2)",
                 "if(icount.LT.ncount) goto 10"),
}


def fail(message: str) -> None:
    print(f"P7W_SOURCE_PARITY=FAIL: {message}", file=sys.stderr)
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
    try:
        version = subprocess.run([compiler, "--version"], capture_output=True, text=True).stdout
    except OSError:
        return None
    match = re.search(r"(\d+)(?:\.\d+)*", version)
    return int(match.group(1)) if match else None


def find_gfortran(explicit: str | None) -> str | None:
    for candidate in ([explicit] if explicit else []) + ["gfortran-16", "gfortran-15",
                                                         "gfortran-14", "gfortran-13",
                                                         "gfortran-12", "gfortran-11",
                                                         "gfortran"]:
        if candidate is None:
            continue
        try:
            subprocess.run([candidate, "--version"], capture_output=True, check=True)
            return candidate
        except (OSError, subprocess.CalledProcessError):
            continue
    return None


def rise_wind_matrix() -> list[list[float]]:
    # icase xbeg xfinal zfinal dzb dt ufnl vfnl ncount h0 hr lr a0 a1 a2 b0 b1 b2
    stub = [70.8, 120.0, 400.0, -0.5, 0.1, 0.2, 1.0, 0.3, -0.1]
    rows: list[list[float]] = []
    cases = [
        # xbeg, xfinal, zfinal, dzb, dt, ufnl, vfnl, ncount
        (1200.0, 1000.0, 190.8, 10.0, 60.0, 1.0, 2.0, 2),     # fully risen
        (1000.0, 1000.0, 190.8, 10.0, 60.0, 1.0, 2.0, 2),     # exactly at final rise
        (0.0, 1000.0, 190.8, 10.0, 60.0, 1.0, 2.0, 2),        # at release
        (100.0, 1500.0, 190.8, 8.0, 30.0, 1.0, 1.0, 2),       # rising, 2 passes
        (100.0, 1500.0, 190.8, 8.0, 30.0, 1.0, 1.0, 1),       # rising, 1 pass
        (100.0, 1500.0, 190.8, 8.0, 30.0, 1.0, 1.0, 5),       # rising, 5 passes
        (500.0, 400.0, 120.0, 0.0, 120.0, -1.0, 0.5, 3),      # zero depth
        (0.0, 50.0, 90.0, 40.0, 3600.0, 0.0, 0.0, 2),         # zero wind, long step
        (0.0, 1.0e6, 200.0, 5.0, 10.0, 3.0, -3.0, 2),         # far from final rise
        (250.0, 300.0, 150.0, 20.0, 100.0, 0.25, 0.75, 4),    # small dzb, 4 passes
        (900.0, 3000.0, 300.0, 50.0, 600.0, -2.0, 4.0, 2),    # wide layer
        (0.0, 100.0, 100.0, 5.0, 1000.0, 0.0, 0.0, 2),        # calm floor
    ]
    for case in cases:
        rows.append(list(case) + stub)
    return rows


def parse_rows(text: str) -> dict[int, list[float]]:
    rows: dict[int, list[float]] = {}
    for line in text.splitlines():
        parts = line.split()
        if not parts:
            continue
        try:
            key = int(parts[0])
            rows[key] = [float(part) for part in parts[1:]]
        except ValueError:
            continue
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--probe", type=pathlib.Path, required=True, help="built cteas_p7w_probe")
    parser.add_argument("--repo-root", type=pathlib.Path, default=REPO_FALLBACK)
    parser.add_argument("--gfortran", help="explicit gfortran executable")
    parser.add_argument("--require", action="store_true",
                        help="fail instead of skipping when no Fortran compiler is available")
    args = parser.parse_args()
    if not args.probe.is_file():
        fail(f"probe binary missing: {args.probe}")
    repo = args.repo_root.resolve()
    ext = load_script(repo / MODULE / "reference/p7w_source_anchor.py", "p7w_anchor")
    vendor = repo / ext.VENDOR_SUBDIR
    manifest, spans = ext.extract(vendor)
    pinned = json.loads((repo / ANCHOR).read_text())
    if pinned != manifest:
        fail(f"vendor source drift: extracted spans/hashes differ from {ANCHOR}")
    print(f"P7W_SOURCE_ANCHOR=PASS VENDOR_SHA256={manifest['vendor_source_sha256']} "
          f"UNITS={','.join(sorted(manifest['units']))} "
          f"OPEN={','.join(sorted(manifest['open_units']))}")
    quotes = check_quotes(spans["risewind"], QUOTES["risewind"], "RISEWIND")
    print(f"P7W_QUOTED_SOURCE_STATEMENTS=PASS COUNT={quotes}")

    compiler = find_gfortran(args.gfortran)
    if compiler is not None:
        major = compiler_major(compiler)
        if major is None or major < 10:
            if args.require:
                fail(f"gfortran {compiler} is older than 10 and cannot build the vendor oracle")
            print(f"P7W_FORTRAN_ORACLE=SKIPPED_TOO_OLD_COMPILER {compiler}")
            compiler = None
    if compiler is None:
        if args.require:
            fail("no Fortran compiler available but --require was given")
        print("P7W_FORTRAN_ORACLE=SKIPPED_WITHOUT_FORTRAN")
        return 0

    rows = rise_wind_matrix()
    with tempfile.TemporaryDirectory(prefix="p7w-oracle-") as temporary:
        stage = pathlib.Path(temporary) / "stage"
        ext.stage(vendor, stage, manifest, spans)
        sources = sorted(str(path) for path in stage.glob("vendor_*.f"))
        binary = stage / "p7w_oracle"
        build = subprocess.run(
            [compiler, "-O0", "-std=legacy", "-ffixed-line-length-72", "-fallow-argument-mismatch",
             "-fno-automatic", f"-I{stage}", "-o", str(binary), *sources,
             str(stage / "p7w_oracle_driver.f")],
            capture_output=True, text=True)
        if build.returncode != 0:
            fail(f"vendor oracle compilation failed: {build.stderr.strip()[-800:]}")
        version = subprocess.run([compiler, "--version"], capture_output=True, text=True)

        body = "\n".join(f"{index + 1} " + " ".join(repr(value) for value in row)
                         for index, row in enumerate(rows)) + "\n"
        probe_run = subprocess.run([str(args.probe), "--rise-wind"], input=body,
                                   capture_output=True, text=True)
        if probe_run.returncode != 0:
            fail(f"probe failed: {probe_run.stderr.strip()[-400:]}")
        oracle_run = subprocess.run([str(binary)], input=body, capture_output=True, text=True,
                                    cwd=stage)
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
        print(f"P7W_RISEWIND_ORACLE_PARITY=PASS CASES={len(oracle_rows)} "
              f"COLUMNS={len(next(iter(oracle_rows.values())))} MISMATCHES=0 "
              f"TOLERANCE_REL={TOLERANCE_RELATIVE:.0e} MAX_REL={worst:.3e} "
              f"WORST_CASE={worst_case} STUBBED_DEPENDENCIES=GRISE,ADVECT")
        print(f"P7W_FORTRAN_COMPILER={version.stdout.splitlines()[0].strip()}")
    print("P7W_RISEWIND_PARITY_IS_NOT_A_CONCENTRATION_COMPARISON=true")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
