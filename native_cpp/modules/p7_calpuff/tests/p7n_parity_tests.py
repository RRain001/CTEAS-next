#!/usr/bin/env python3
"""P7N plume rise: vendor source anchor and Fortran parity.

Builds the UNMODIFIED vendor units extracted by
reference/p7n_source_anchor.py (STKTIP, PRB, PRM, PRFIN, PRFPP, GRISE and the
generated harness around the verbatim POINTS1 flux statements) together with
reference/p7n_oracle_driver.f and compares them against the ported rise module
through the case matrices `cteas_p7n_probe` prints.
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
ANCHOR = f"{MODULE}/reference/p7n_source_anchor.json"
TOLERANCE_RELATIVE = 1.0e-5
TOLERANCE_ABSOLUTE = 1.0e-30

QUOTES = {
    "stktip": ("if(fluxm.EQ.0.0) then", "hdw=AMIN1(hs,(3.*diam))",
               "hdw=AMIN1(hs,(2.*diam*(1.5-vbyws)))"),
    "prb": ("if(x.le.0.0.or.fb.le.0.0)then", "zb=(1.6*(fb*x*x)**0.333333)/wsstk",
            "zb=amin1(zb,zfinb)"),
    "prm": ("betaj=0.333333+(wsstk/vexit)", "zmfnu=3.*diam*vexit/wsstk",
            "zm=(3.*fm*sin(sqrts*x/wsstk)/(betaj*betaj*wsstk*", "zm=amin1(zm,zmfnu)"),
    "prfin": ("data wsstk0/1.0/", "xfinb=119.*fb**0.4", "zfinb=38.71*fb**0.6/wsstk",
              "zfinb=21.425*fb**0.75/wsstk", "xfinb=2.0715*wsstk/sqrts",
              "zfinv=4.*fb2**0.25/s**0.375", "xfinm=1.57080*wsstk/sqrts",
              "if(fm.EQ.0.0) then", "xfin=amax1(xfinb,xfinm)"),
    "prfpp": ("data g/9.80665/", "zi=hmix-hs", "rise0=0.67*zi",
              "peninv=u*(g*ti/ta)*zi*zi/fb", "fmix=0.08*peninv-pen+0.08",
              "rise1=zi*(1.-0.33*fmix)", "zfin=AMIN1(zfin,rise1)",
              "hmax=hmix+2.*(rise2-zi)"),
    "grise": ("risefac=1.0", "method=1", "call prm(diam0(ipnum),exitw0(ipnum),fm(ipnum),ws0(ipnum),",
              "call prb(fb(ipnum),ws0(ipnum),x,xbfin(ipnum),zbfin(ipnum),",
              "rise=AMAX1(risem,riseb)", "htgrise=ht0(ipnum)+rise-stipdw(ipnum)",
              "htgrise=AMAX1(0.0,htgrise)", "risefac=rise/zfrise",
              "risefac=AMAX1(risefac,0.0)"),
}


def fail(message: str) -> None:
    print(f"P7N_SOURCE_PARITY=FAIL: {message}", file=sys.stderr)
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


def stktip_matrix() -> list[tuple]:
    rows = []
    for stack_height in (70.8, 5.0, 1.0):
        for diameter in (1.6, 3.0):
            for momentum_flux in (0.0, 300.0):
                for exit_velocity in (0.0, 1.0, 5.0, 17.26):
                    for wind in (0.5, 1.4, 10.0):
                        rows.append((stack_height, diameter, momentum_flux, exit_velocity, wind))
    return rows


def prfin_matrix() -> list[tuple]:
    rows = []
    for exit_velocity in (17.26, 5.0):
        for diameter in (1.6, 3.0):
            for momentum_flux in (0.0, 300.0):
                for buoyancy_flux in (0.0, 30.0, 1200.0):
                    for wind in (0.5, 1.4, 10.0):
                        for stability in (1, 4, 5, 6):
                            rows.append((exit_velocity, diameter, momentum_flux, buoyancy_flux, wind,
                                         stability, 0.02))
    return rows


def prm_matrix() -> list[tuple]:
    rows = []
    for exit_velocity in (17.26, 5.0):
        for momentum_flux in (0.0, 300.0):
            for wind in (0.5, 1.4):
                for stability in (4, 5):
                    for x in (0.0, 500.0, 5000.0):
                        rows.append((1.6, exit_velocity, momentum_flux, wind, stability, 0.02, x,
                                     3000.0, 12.0))
    return rows


def prb_matrix() -> list[tuple]:
    rows = []
    for buoyancy_flux in (0.0, 30.0, 1200.0):
        for wind in (0.5, 1.4):
            for x in (0.0, 500.0, 10000.0):
                rows.append((buoyancy_flux, wind, x, 4000.0, 20.0))
    return rows


def prfpp_matrix() -> list[tuple]:
    rows = []
    for final_rise in (10.0, 30.0, 200.0):
        for mixing_height in (50.0, 231.0, 400.0):
            for gradient in (0.005, 0.02):
                rows.append((final_rise, 1200.0, 1.4, 70.8, mixing_height, 279.15, gradient, 0.6))
    return rows


def flux_matrix() -> list[tuple]:
    rows = []
    for diameter in (1.6, 3.0):
        for exit_velocity in (0.0, 17.26):
            for stack_temperature in (298.15, 350.0):
                for excess in (0.0, 19.0):
                    for factor in (0.0, 1.0):
                        rows.append((diameter, exit_velocity, stack_temperature, excess, 279.15,
                                     factor))
    return rows


def grise_matrix() -> list[tuple]:
    """(source_type, idw0, imet, mrise, mshear, x, zfinal, zfrise, ht0, diam0, exitw0,
    ws0, istab0, sqrts0, fm, xmfin, zmfin, fb, xbfin, zbfin, stipdw)"""
    rows = []
    for stability in (1, 4, 5, 6):
        for x in (100.0, 1000.0, 10000.0):
            for downwash in (0, 1):
                for tip_downwash in (0.0, 2.0):
                    for full_rise in (0.0, 200.0):
                        rows.append((1, downwash, 1, 1, 0, x, 200.0, full_rise, 70.8, 1.6, 17.26,
                                     1.4, stability, 0.02, 300.0, 3000.0, 12.0, 1200.0, 4000.0,
                                     60.0, tip_downwash))
    # PRIME cavity plume (method 0) uses the stored final height.
    for x in (100.0, 1000.0):
        rows.append((1, 4, 1, 1, 0, x, 200.0, 200.0, 70.8, 1.6, 17.26, 1.4, 4, 0.02, 300.0,
                     3000.0, 12.0, 1200.0, 4000.0, 60.0, 0.0))
    return rows


def parse_rows(text: str) -> dict[int, list[float]]:
    rows: dict[int, list[float]] = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("P7N_") or line.startswith("{"):
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
    print(f"P7N_{what.upper()}_ORACLE_PARITY=PASS CASES={len(oracle_rows)} "
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
    parser.add_argument("--probe", type=pathlib.Path, required=True, help="built cteas_p7n_probe")
    parser.add_argument("--repo-root", type=pathlib.Path, default=REPO_FALLBACK)
    parser.add_argument("--gfortran", help="explicit gfortran executable")
    parser.add_argument("--require", action="store_true",
                        help="fail instead of skipping when no Fortran compiler is available")
    args = parser.parse_args()
    if not args.probe.is_file():
        fail(f"probe binary missing: {args.probe}")
    repo = args.repo_root.resolve()
    ext = load_script(repo / MODULE / "reference/p7n_source_anchor.py", "p7n_anchor")
    vendor = repo / ext.VENDOR_SUBDIR
    manifest, spans = ext.extract(vendor)
    pinned = json.loads((repo / ANCHOR).read_text())
    if pinned != manifest:
        fail(f"vendor source drift: extracted spans/hashes differ from {ANCHOR}")
    print(f"P7N_SOURCE_ANCHOR=PASS VENDOR_SHA256={manifest['vendor_source_sha256']} "
          f"UNITS={','.join(sorted(manifest['units']))} "
          f"INLINE={manifest['inline']['name']}")
    print(f"P7N_INLINE_BLOCK=PASS UNIT={manifest['inline']['enclosing_unit']} "
          f"LINES={manifest['inline']['first_line']}-{manifest['inline']['last_line']} "
          f"STATEMENTS={len(manifest['inline']['statements'])}")
    quotes = 0
    for name, quoted in QUOTES.items():
        quotes += check_quotes(spans[name], quoted, name.upper())
    quotes += check_quotes(spans["inline_flux"], tuple(manifest["inline"]["statements"]),
                           "POINTS1_FLUX")
    print(f"P7N_QUOTED_SOURCE_STATEMENTS=PASS COUNT={quotes}")

    compiler = find_gfortran(args.gfortran)
    if compiler is not None:
        major = compiler_major(compiler)
        if major is None or major < 10:
            if args.require:
                fail(f"gfortran {compiler} is older than 10 and cannot build the vendor oracle")
            print(f"P7N_FORTRAN_ORACLE=SKIPPED_TOO_OLD_COMPILER {compiler}")
            compiler = None
    if compiler is None:
        if args.require:
            fail("no Fortran compiler available but --require was given")
        print("P7N_FORTRAN_ORACLE=SKIPPED_WITHOUT_FORTRAN")
        return 0

    with tempfile.TemporaryDirectory(prefix="p7n-oracle-") as temporary:
        stage = pathlib.Path(temporary) / "stage"
        ext.stage(vendor, stage, manifest, spans)
        sources = sorted(str(path) for path in stage.glob("vendor_*.f"))
        binary = stage / "p7n_oracle"
        build = subprocess.run(
            [compiler, "-O0", "-std=legacy", "-ffixed-line-length-72", "-fallow-argument-mismatch",
             "-fno-automatic", f"-I{stage}", "-o", str(binary), *sources,
             str(stage / "p7n_oracle_driver.f")],
            capture_output=True, text=True)
        if build.returncode != 0:
            fail(f"vendor oracle compilation failed: {build.stderr.strip()[-800:]}")
        version = subprocess.run([compiler, "--version"], capture_output=True, text=True)

        total = 0
        for mode, flag, rows, integer_columns in (
                (1, "--stktip-matrix", stktip_matrix(), ()),
                (2, "--prfin-matrix", prfin_matrix(), ()),
                (3, "--prm-matrix", prm_matrix(), ()),
                (4, "--prb-matrix", prb_matrix(), ()),
                (5, "--prfpp-matrix", prfpp_matrix(), ()),
                (6, "--flux-matrix", flux_matrix(), ()),
                (7, "--grise-matrix", grise_matrix(), ())):
            payload = "\n".join(f"{index + 1} " + " ".join(repr(value) for value in row)
                                for index, row in enumerate(rows)) + "\n"
            oracle_rows, probe_rows = run_pair(args.probe, binary, mode, flag, payload, stage)
            total += compare(flag[2:-7], oracle_rows, probe_rows, integer_columns)
        print(f"P7N_ORACLE_PARITY_TOTAL_CASES={total}")
        print(f"P7N_FORTRAN_COMPILER={version.stdout.splitlines()[0].strip()}")
    print("P7N_PLUME_RISE_PARITY_IS_NOT_A_CONCENTRATION_COMPARISON=true")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
