#!/usr/bin/env python3
"""P7P step bookkeeping: vendor source anchor and Fortran parity.

Builds the UNMODIFIED vendor unit `setcsig` and the generated harnesses that wrap
the verbatim SETPUF step-bookkeeping and state-update statements, then compares
them against the ported step module through the case matrices `cteas_p7p_probe`
prints.
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
ANCHOR = f"{MODULE}/reference/p7p_source_anchor.json"
TOLERANCE_RELATIVE = 1.0e-5
TOLERANCE_ABSOLUTE = 1.0e-30

QUOTES = {
    "setcsig": ("idoptys=idopty", "kstabs =kst", "if(mtauly.EQ.1) then",
                "tyidr=1./(1.62*tau)", "if(kstabs.GT.6) kstabs=6",
                "szh=syh", "call SIGTY(syh,zero,zero,dum,thfty,dhfty)",
                "ixcell =ix"),
    "inline_step": ("xttb1=xtotb(ii)", "xtte1=xttb1+distm", "tb1=tmtotb(ii)",
                    "te1=tb1+tsamp", "dmidkm=0.5*distm*dm2km", "tmid=0.5*tsamp",
                    "uavg=ws", "ukps=ws*dm2km", "lcalm=.FALSE.",
                    "if(ws.LT.wscalm) then", "lcalm=.TRUE.", "idopty=1", "idoptz=1",
                    "idw0(ii)=0", "xfinal(ii)=zero"),
    "inline_update": ("vsetl=vgrav(1,1)", "if(mtilt.EQ.1) then",
                      "ze1=ze1-vsetl*tsamp", "ze1=AMAX1(ze1,0.0)",
                      "xtotb(ii)=xtotb(ii)+distm", "tmtotb(ii)=tmtotb(ii)+tsamp",
                      "xpb(ii)=xnew", "ypb(ii)=ynew", "zpb(ii)=ze1"),
}


def fail(message: str) -> None:
    print(f"P7P_SOURCE_PARITY=FAIL: {message}", file=sys.stderr)
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


def step_matrix() -> list[tuple]:
    rows = []
    for total_distance in (0.0, 1000.0):
        for total_time in (0.0, 3600.0):
            for step_distance in (0.0, 5026.0):
                for step_seconds in (3600.0, 1800.0):
                    for wind in (0.0, 0.3, 0.5, 1.396, 10.0):
                        for downwash in (0, 4):
                            for x_final in (0.0, 163.913):
                                rows.append((total_distance, total_time, step_distance, step_seconds,
                                             0.001, wind, 0.5, downwash, x_final, 3, 3))
    return rows


def update_matrix() -> list[tuple]:
    rows = []
    for height in (0.0, 136.158):
        for settling in (0.0, 0.01):
            for tilt in (0, 1):
                for step_seconds in (3600.0, 1800.0):
                    for step_distance in (0.0, 5026.0):
                        for total_distance in (0.0, 1000.0):
                            rows.append((height, settling, tilt, step_seconds, step_distance,
                                         total_distance, 3600.0, 513.0, 3533.0))
    return rows


def setcsig_matrix() -> list[tuple]:
    rows = []
    for idopty in (1, 3):
        for urban in (0, 1):
            for stability in (1, 4, 6, 9):
                for heffter in (0, 1):
                    rows.append((idopty, 3, urban, 1.396, stability, -49.0, 0.0, 1.0, 1.0, 1.0, 1.0,
                                 70.8, 231.0, 25, 25, 1, heffter, 0))
    return rows


def parse_rows(text: str) -> dict[int, list[float]]:
    rows: dict[int, list[float]] = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("P7P_") or line.startswith("{"):
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
    print(f"P7P_{what.upper()}_ORACLE_PARITY=PASS CASES={len(oracle_rows)} "
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
    parser.add_argument("--probe", type=pathlib.Path, required=True, help="built cteas_p7p_probe")
    parser.add_argument("--repo-root", type=pathlib.Path, default=REPO_FALLBACK)
    parser.add_argument("--gfortran", help="explicit gfortran executable")
    parser.add_argument("--require", action="store_true",
                        help="fail instead of skipping when no Fortran compiler is available")
    args = parser.parse_args()
    if not args.probe.is_file():
        fail(f"probe binary missing: {args.probe}")
    repo = args.repo_root.resolve()
    ext = load_script(repo / MODULE / "reference/p7p_source_anchor.py", "p7p_anchor")
    vendor = repo / ext.VENDOR_SUBDIR
    manifest, spans = ext.extract(vendor)
    pinned = json.loads((repo / ANCHOR).read_text())
    if pinned != manifest:
        fail(f"vendor source drift: extracted spans/hashes differ from {ANCHOR}")
    print(f"P7P_SOURCE_ANCHOR=PASS VENDOR_SHA256={manifest['vendor_source_sha256']} "
          f"UNITS={','.join(sorted(manifest['units']))} "
          f"INLINE={','.join(sorted(manifest['inline']))}")
    for name, info in sorted(manifest["inline"].items()):
        print(f"P7P_INLINE_BLOCK=PASS NAME={name} UNIT={info['enclosing_unit']} "
              f"LINES={info['first_line']}-{info['last_line']} "
              f"STATEMENTS={len(info['statements'])}")
    statements = manifest["pinned_statements"]
    if [entry["statement"] for entry in statements] != ["tmtotb(ii)=tmtotb(ii)+tsamp",
                                                        "xtotb(ii)=xtotb(ii)+distm",
                                                        "zpb(ii)=ze1"]:
        fail(f"pinned statements changed: {statements}")
    print("P7P_PINNED_STATEMENTS=PASS AGE_LINE=" + str(statements[0]["line"]) +
          " DISTANCE_LINE=" + str(statements[1]["line"]) +
          " POSITION_LINE=" + str(statements[2]["line"]))
    quotes = 0
    for name, quoted in QUOTES.items():
        quotes += check_quotes(spans[name], quoted, name.upper())
    print(f"P7P_QUOTED_SOURCE_STATEMENTS=PASS COUNT={quotes}")

    compiler = find_gfortran(args.gfortran)
    if compiler is not None:
        major = compiler_major(compiler)
        if major is None or major < 10:
            if args.require:
                fail(f"gfortran {compiler} is older than 10 and cannot build the vendor oracle")
            print(f"P7P_FORTRAN_ORACLE=SKIPPED_TOO_OLD_COMPILER {compiler}")
            compiler = None
    if compiler is None:
        if args.require:
            fail("no Fortran compiler available but --require was given")
        print("P7P_FORTRAN_ORACLE=SKIPPED_WITHOUT_FORTRAN")
        return 0

    with tempfile.TemporaryDirectory(prefix="p7p-oracle-") as temporary:
        stage = pathlib.Path(temporary) / "stage"
        ext.stage(vendor, stage, manifest, spans)
        sources = sorted(str(path) for path in stage.glob("vendor_*.f"))
        binary = stage / "p7p_oracle"
        build = subprocess.run(
            [compiler, "-O0", "-std=legacy", "-ffixed-line-length-72", "-fallow-argument-mismatch",
             "-fno-automatic", f"-I{stage}", "-o", str(binary), *sources,
             str(stage / "p7p_oracle_driver.f")],
            capture_output=True, text=True)
        if build.returncode != 0:
            fail(f"vendor oracle compilation failed: {build.stderr.strip()[-800:]}")
        version = subprocess.run([compiler, "--version"], capture_output=True, text=True)

        total = 0
        for mode, flag, rows, integer_columns in (
                (1, "--step-matrix", step_matrix(), (0, 1, 2, 10)),
                (2, "--update-matrix", update_matrix(), ()),
                (3, "--setcsig-matrix", setcsig_matrix(), (0, 1, 2, 3, 4, 5, 6, 7))):
            payload = "\n".join(f"{index + 1} " + " ".join(repr(value) for value in row)
                                for index, row in enumerate(rows)) + "\n"
            oracle_rows, probe_rows = run_pair(args.probe, binary, mode, flag, payload, stage)
            total += compare(flag[2:-7], oracle_rows, probe_rows, integer_columns)
        print(f"P7P_ORACLE_PARITY_TOTAL_CASES={total}")
        print(f"P7P_FORTRAN_COMPILER={version.stdout.splitlines()[0].strip()}")
    print("P7P_STEP_PARITY_IS_NOT_A_CONCENTRATION_COMPARISON=true")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
