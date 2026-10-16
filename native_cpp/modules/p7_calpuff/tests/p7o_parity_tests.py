#!/usr/bin/env python3
"""P7O release scheduler: vendor source anchor and Fortran parity.

Builds the UNMODIFIED vendor unit `inject` and the generated harnesses that wrap
the verbatim POINTS1 release-cadence and release-state statements, then compares
them against the ported release module through the case matrices
`cteas_p7o_probe` prints.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import math
import pathlib
import re
import subprocess
import struct
import sys
import tempfile

REPO_FALLBACK = pathlib.Path(__file__).resolve().parents[4]
MODULE = "native_cpp/modules/p7_calpuff"
ANCHOR = f"{MODULE}/reference/p7o_source_anchor.json"
TOLERANCE_RELATIVE = 1.0e-5
TOLERANCE_ABSOLUTE = 1.0e-30

QUOTES = {
    "inject": ("if(fmix.NE.1.0 .and. fmix.NE.0.0) then", "qm(ispec,np)=qtotal*fmix",
               "qu(ispec,np)=qtotal-qm(ispec,np)", "ipufcd(np)=5+mfact0",
               "elseif(heff.LE.dpbl)then", "ipufcd(np)=1+mfact0",
               "if(istab.GE.5) then", "zimax(np)=ziunlm",
               "qm(ispec,np)=q(ispec)*dt", "qu(ispec,np)=q(ispec)*dt"),
    "inline_cadence": ("npnew=wsnew*xtmp1(md)+1", "npnew=max0(npnew,1)",
                       "npnew=min0(npnew,mxnew)", "dt=dthr/float(npnew)"),
    "inline_release_state": ("xpb(np)=xpt1grd(i)", "zfinal(np)=heff", "zpb(np)=heff",
                             "zpe(np)=heff", "fb(np)=fluxb", "fm(np)=fluxm",
                             "stipdw(np)=tipdw", "isplit(np)=1", "temit0(np)=dt",
                             "srat0(np)=1.0", "irlsnum(np)=j", "isrcnum(np)=i",
                             "isrctyp(np)=itype"),
}


def fail(message: str) -> None:
    print(f"P7O_SOURCE_PARITY=FAIL: {message}", file=sys.stderr)
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


def inject_matrix() -> list[tuple]:
    rows = []
    for species in (1, 2, 3):
        for duration in (900.0, 1800.0, 3600.0):
            for step_index in (0, 10):
                for effective in (50.0, 136.158, 400.0):
                    for mixing in (231.0, 500.0):
                        for mixed_fraction in (0.0, 0.25, 1.0):
                            for stability in (1, 4, 5, 6):
                                for gaussian in (0, 1):
                                    rows.append((species, duration, step_index, effective, 700.0,
                                                 mixing, mixed_fraction, stability, gaussian,
                                                 8.34e5, 1.0e3, 0.0))
    return rows


def cadence_matrix() -> list[tuple]:
    rows = []
    for wind in (0.0, 0.1, 1.396, 5.0, 10.0, 25.0):
        for interval in (0.25, 1.0, 2.0):
            for max_puffs in (1, 3, 99):
                for hour in (3600.0, 7200.0):
                    rows.append((wind, interval, max_puffs, hour))
    return rows


def state_matrix() -> list[tuple]:
    rows = []
    for release_index in (1, 2):
        for source_type in (1, 2):
            for downwash in (0, 4):
                for stability in (1, 4, 5, 6):
                    rows.append((513.385, 3533.769, 0.0, 1.0, 1.0, 136.158, 163.913, 100.0,
                                 6.9035, 178.51, 163.913, 163.913, 65.358, 65.358, 0.0, 70.8,
                                 17.26, 1.6, 1800.0, 1.396, stability, 0.0, 0, 1.0, 1.0, -49.0,
                                 0.5, downwash, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0, 1.0,
                                 release_index, 1, source_type))
    return rows


def parse_rows(text: str) -> dict[int, list[float]]:
    rows: dict[int, list[float]] = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("P7O_") or line.startswith("{"):
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
            integer_columns: tuple[int, ...] = (), *, exact_real4: bool = False) -> int:
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
            if exact_real4:
                # POINTS1 state is unqualified REAL in original /PUFF/.
                # Its emitted ES20.12 decimal round-trips uniquely to REAL*4;
                # the C++ diagnostic must contain that *same stored float*.
                # No tolerance or blanket DOUBLE precision promotion allowed.
                source_bits = struct.pack("!f", want)
                cpp_bits = struct.pack("!f", got)
                if source_bits != cpp_bits:
                    fail(f"{what} case {key} column {column}: "
                         f"original REAL4={source_bits.hex()} C++ REAL4={cpp_bits.hex()} "
                         f"oracle={want!r} probe={got!r}")
            if abs(want - got) > max(TOLERANCE_RELATIVE * abs(want), TOLERANCE_ABSOLUTE):
                fail(f"{what} case {key} column {column}: oracle={want!r} probe={got!r}")
            worst_absolute = max(worst_absolute, abs(want - got))
            relative = abs(want - got) / max(abs(want), 1.0e-30)
            if relative > worst:
                worst = relative
                worst_case = key
    print(f"P7O_{what.upper()}_ORACLE_PARITY=PASS CASES={len(oracle_rows)} "
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
    parser.add_argument("--probe", type=pathlib.Path, required=True, help="built cteas_p7o_probe")
    parser.add_argument("--repo-root", type=pathlib.Path, default=REPO_FALLBACK)
    parser.add_argument("--gfortran", help="explicit gfortran executable")
    parser.add_argument("--require", action="store_true",
                        help="fail instead of skipping when no Fortran compiler is available")
    args = parser.parse_args()
    if not args.probe.is_file():
        fail(f"probe binary missing: {args.probe}")
    repo = args.repo_root.resolve()
    ext = load_script(repo / MODULE / "reference/p7o_source_anchor.py", "p7o_anchor")
    vendor = repo / ext.VENDOR_SUBDIR
    manifest, spans = ext.extract(vendor)
    pinned = json.loads((repo / ANCHOR).read_text())
    if pinned != manifest:
        fail(f"vendor source drift: extracted spans/hashes differ from {ANCHOR}")
    print(f"P7O_SOURCE_ANCHOR=PASS VENDOR_SHA256={manifest['vendor_source_sha256']} "
          f"UNITS={','.join(sorted(manifest['units']))} "
          f"INLINE={','.join(sorted(manifest['inline']))}")
    for name, info in sorted(manifest["inline"].items()):
        print(f"P7O_INLINE_BLOCK=PASS NAME={name} UNIT={info['enclosing_unit']} "
              f"LINES={info['first_line']}-{info['last_line']} "
              f"STATEMENTS={len(info['statements'])}")
    age = manifest["puff_age"]["statements"]
    if [entry["unit"] for entry in age] != ["swap", "setpuf"]:
        fail(f"puff-age statements changed: {age}")
    print("P7O_PUFF_AGE=PASS SWAP_ZEROES_TMTOTB=" + str(age[0]["line"]) +
          " SETPUF_ADDS_TSAMP=" + str(age[1]["line"]))
    quotes = 0
    for name, quoted in QUOTES.items():
        quotes += check_quotes(spans[name], quoted, name.upper())
    print(f"P7O_QUOTED_SOURCE_STATEMENTS=PASS COUNT={quotes}")

    compiler = find_gfortran(args.gfortran)
    if compiler is not None:
        major = compiler_major(compiler)
        if major is None or major < 10:
            if args.require:
                fail(f"gfortran {compiler} is older than 10 and cannot build the vendor oracle")
            print(f"P7O_FORTRAN_ORACLE=SKIPPED_TOO_OLD_COMPILER {compiler}")
            compiler = None
    if compiler is None:
        if args.require:
            fail("no Fortran compiler available but --require was given")
        print("P7O_FORTRAN_ORACLE=SKIPPED_WITHOUT_FORTRAN")
        return 0

    with tempfile.TemporaryDirectory(prefix="p7o-oracle-") as temporary:
        stage = pathlib.Path(temporary) / "stage"
        ext.stage(vendor, stage, manifest, spans)
        sources = sorted(str(path) for path in stage.glob("vendor_*.f"))
        binary = stage / "p7o_oracle"
        build = subprocess.run(
            [compiler, "-O0", "-std=legacy", "-ffixed-line-length-72", "-fallow-argument-mismatch",
             "-fno-automatic", f"-I{stage}", "-o", str(binary), *sources,
             str(stage / "p7o_oracle_driver.f")],
            capture_output=True, text=True)
        if build.returncode != 0:
            fail(f"vendor oracle compilation failed: {build.stderr.strip()[-800:]}")
        version = subprocess.run([compiler, "--version"], capture_output=True, text=True)

        total = 0
        for mode, flag, rows, integer_columns in (
                (1, "--inject-matrix", inject_matrix(), (0, 1)),
                (2, "--cadence-matrix", cadence_matrix(), (1, 2)),
                (3, "--state-matrix", state_matrix(), (18, 24, 26, 32, 43, 44, 45))):
            payload = "\n".join(f"{index + 1} " + " ".join(repr(value) for value in row)
                                for index, row in enumerate(rows)) + "\n"
            oracle_rows, probe_rows = run_pair(args.probe, binary, mode, flag, payload, stage)
            total += compare(flag[2:-7], oracle_rows, probe_rows, integer_columns,
                             exact_real4=(mode == 3))
        print(f"P7O_ORACLE_PARITY_TOTAL_CASES={total}")
        print(f"P7O_FORTRAN_COMPILER={version.stdout.splitlines()[0].strip()}")
    print("P7O_RELEASE_STATE_REAL4_BITWISE=PASS")
    print("P7O_RELEASE_PARITY_IS_NOT_A_CONCENTRATION_COMPARISON=true")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
