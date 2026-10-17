#!/usr/bin/env python3
"""P7V advection: vendor source anchor and Fortran parity.

Builds the UNMODIFIED vendor units `zfind`, `advwnd`, `advect` and `puffdz` with a
hand-written driver, then compares them against the ported advection module through
the case matrices `cteas_p7v_probe` prints. POWLAW (METFM 2/3) and XTPRF (METFM 4/5)
are hard-failing stubs in the oracle: they are off the locked deck's path.
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
ANCHOR = f"{MODULE}/reference/p7v_source_anchor.json"
TOLERANCE_RELATIVE = 1.0e-5
TOLERANCE_ABSOLUTE = 1.0e-30

QUOTES = {
    "zfind": ("do 10 i=2,nzp1", "if(z.lt.zface(i))then", "ilayer=i-1", "ilayer=nzp1-1"),
    "advwnd": ("call zfind(zabot,zface,nzp1,IBOT)", "call zfind(zatop,zface,nzp1,ITOP)",
               "if(IBOT.eq.ITOP)then", "if(zabot.lt.zface(1))zabot=zface(1)",
               "if(zabot.gt.zface(nzp1))zabot=zface(nzp1)", "if(zatop.lt.zface(1))zatop=zface(1)",
               "if(zatop.gt.zface(nzp1))zatop=zface(nzp1)", "delz=zface(ibot+1)-zabot",
               "delz=zatop-zface(itop)", "UAVE=sumu/sumz", "VAVE=sumv/sumz"),
    "advect": ("if(metfm.LE.3) then", "u(iz)=umet(ix,iy,iz,mdom)", "v(iz)=vmet(ix,iy,iz,mdom)",
               "call ADVWND(u,v,zface,nzp1,zbot,ztop,uadv,vadv)",
               "call POWLAW(ht,zgpt(1),wsold,plx,ws)", "call XTPRF(nzprf,ssprf,zprf,ztop,"),
    "puffdz": ("if(mod(icode,2).eq.1)then", "sigmaz=sigzb(ii)", "zbot=htmet-sigmaz",
               "ztop=htmet+sigmaz", "if(dpbl.GT.htmet) then", "ztop=amin1(ztop,dpbl)",
               "ztop=zimax(ii)", "zbot=zface(ilayer)", "ztop=zface(ilayer+1)",
               "if(qutot.GT.(2.*qmtot)) zbot=ziold(ii)*(1-2.*qmtot/qutot)",
               "PUFFDZ: Bottom EXCEEDS Top!"),
}


def fail(message: str) -> None:
    print(f"P7V_SOURCE_PARITY=FAIL: {message}", file=sys.stderr)
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


def faces(nz: int, spacing: float, first: float = 0.0) -> list[float]:
    return [first + index * spacing for index in range(nz + 1)]


def zfind_matrix() -> list[list[float]]:
    rows: list[list[float]] = []
    cases = [
        (5, -5.0), (5, 0.0), (5, 49.999), (5, 50.0), (5, 50.001), (5, 120.0),
        (5, 199.999), (5, 200.0), (5, 499.999), (5, 500.0), (5, 900.0),
        (9, 0.5), (9, 450.0), (9, 3600.0),
    ]
    for nz, z in cases:
        row = [nz, *faces(nz, 50.0), z]
        rows.append(row)
    return rows


def advwnd_matrix() -> list[list[float]]:
    rows: list[list[float]] = []
    # ADVECT refuses an inverted span (fail-closed), so mode 3 keeps only
    # monotone spans; mode 2 exercises the clamped depths.
    profiles = [
        (5, 40.0, 260.0), (5, 0.0, 500.0), (5, 10.0, 40.0), (5, 120.0, 120.0),
        (5, -10.0, 40.0), (5, 480.0, 700.0), (5, 60.0, 90.0),
        (9, 12.5, 4.0), (9, 0.0, 0.0), (9, 3590.0, 900.0),
    ]
    for nz, zbot, ztop in profiles:
        face = faces(nz, 50.0)
        u = [1.0 + 0.25 * index for index in range(nz)]
        v = [0.5 + 0.5 * index for index in range(nz)]
        rows.append([nz, *face, *u, *v, zbot, ztop])
    return rows


def puffdz_matrix() -> list[list[float]]:
    # icode lpuff istab ilayer htmet dpbl sigzb sigze ziold zimax zfbot zftop nspec qu
    return [
        [1, 1, 4, 2, 70.8, 231.0, 5.0, 5.0, 231.0, 231.0, 100.0, 200.0, 2, 0.0],
        [1, 1, 4, 2, 70.8, 50.0, 5.0, 5.0, 231.0, 231.0, 100.0, 200.0, 2, 0.0],
        [1, 1, 4, 2, 70.8, 50.0, 5.0, 5.0, 60.0, 231.0, 100.0, 200.0, 2, 0.0],
        [1, 1, 4, 2, 70.8, 50.0, 5.0, 5.0, 60.0, 40.0, 100.0, 200.0, 2, 0.0],
        [1, 1, 5, 2, 70.8, 231.0, 5.0, 5.0, 231.0, 231.0, 100.0, 200.0, 2, 0.0],
        [3, 1, 4, 2, 70.8, 50.0, 5.0, 5.0, 231.0, 231.0, 100.0, 200.0, 2, 0.0],
        [1, 0, 4, 2, 70.8, 231.0, 5.0, 9.0, 231.0, 231.0, 100.0, 200.0, 2, 0.0],
        [1, 1, 4, 2, 2.0, 231.0, 5.0, 5.0, 231.0, 231.0, 100.0, 200.0, 2, 0.0],
        [2, 1, 4, 2, 70.8, 231.0, 5.0, 5.0, 231.0, 231.0, 100.0, 200.0, 2, 0.0],
        [12, 0, 4, 2, 70.8, 231.0, 5.0, 9.0, 231.0, 231.0, 100.0, 200.0, 2, 0.0],
        [4, 1, 4, 2, 70.8, 231.0, 5.0, 5.0, 231.0, 231.0, 100.0, 200.0, 2, 0.0],
        [14, 0, 4, 2, 70.8, 231.0, 5.0, 9.0, 231.0, 231.0, 100.0, 200.0, 2, 0.0],
        [6, 1, 4, 2, 70.8, 231.0, 5.0, 5.0, 231.0, 231.0, 0.0, 0.0, 2, 3.0],
        [16, 0, 4, 2, 70.8, 231.0, 5.0, 9.0, 231.0, 231.0, 0.0, 0.0, 2, 3.0],
        [6, 1, 4, 2, 70.8, 231.0, 5.0, 5.0, 231.0, 231.0, 0.0, 0.0, 4, 30.0],
        [6, 1, 4, 2, 70.8, 231.0, 5.0, 5.0, 231.0, 231.0, 0.0, 0.0, 4, 1.0],
        [2, 1, 6, 2, 70.8, 231.0, 5.0, 5.0, 231.0, 400.0, 100.0, 200.0, 2, 0.0],
    ]


def payload(mode: int, rows: list[list[float]]) -> str:
    """Emit the oracle's record grammar: header, then one record per array."""
    lines = []
    for index, row in enumerate(rows):
        if mode == 1:
            nz = int(row[0])
            lines.append(f"{index + 1} {nz}")
            lines.append(" ".join(repr(value) for value in row[1:2 + nz]))
            lines.append(repr(row[2 + nz]))
        elif mode in (2, 3):
            nz = int(row[0])
            lines.append(f"{index + 1} {nz}")
            lines.append(" ".join(repr(value) for value in row[1:2 + nz]))
            lines.append(" ".join(repr(value) for value in row[2 + nz:2 + 2 * nz]))
            lines.append(" ".join(repr(value) for value in row[2 + 2 * nz:2 + 3 * nz]))
            lines.append(" ".join(repr(value) for value in row[2 + 3 * nz:4 + 3 * nz]))
        else:
            fields = [repr(value) for value in row]
            fields[1] = "T" if row[1] else "F"   # LPUFF is LOGICAL in the vendor grammar
            lines.append(f"{index + 1} " + " ".join(fields))
    return "\n".join(lines) + "\n"


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
    parser.add_argument("--probe", type=pathlib.Path, required=True, help="built cteas_p7v_probe")
    parser.add_argument("--repo-root", type=pathlib.Path, default=REPO_FALLBACK)
    parser.add_argument("--gfortran", help="explicit gfortran executable")
    parser.add_argument("--require", action="store_true",
                        help="fail instead of skipping when no Fortran compiler is available")
    args = parser.parse_args()
    if not args.probe.is_file():
        fail(f"probe binary missing: {args.probe}")
    repo = args.repo_root.resolve()
    ext = load_script(repo / MODULE / "reference/p7v_source_anchor.py", "p7v_anchor")
    vendor = repo / ext.VENDOR_SUBDIR
    manifest, spans = ext.extract(vendor)
    pinned = json.loads((repo / ANCHOR).read_text())
    if pinned != manifest:
        fail(f"vendor source drift: extracted spans/hashes differ from {ANCHOR}")
    print(f"P7V_SOURCE_ANCHOR=PASS VENDOR_SHA256={manifest['vendor_source_sha256']} "
          f"UNITS={','.join(sorted(manifest['units']))}")
    quotes = 0
    for name, wanted in QUOTES.items():
        quotes += check_quotes(spans[name], wanted, name.upper())
    print(f"P7V_QUOTED_SOURCE_STATEMENTS=PASS COUNT={quotes}")

    compiler = find_gfortran(args.gfortran)
    if compiler is not None:
        major = compiler_major(compiler)
        if major is None or major < 10:
            if args.require:
                fail(f"gfortran {compiler} is older than 10 and cannot build the vendor oracle")
            print(f"P7V_FORTRAN_ORACLE=SKIPPED_TOO_OLD_COMPILER {compiler}")
            compiler = None
    if compiler is None:
        if args.require:
            fail("no Fortran compiler available but --require was given")
        print("P7V_FORTRAN_ORACLE=SKIPPED_WITHOUT_FORTRAN")
        return 0

    advwnd_rows = advwnd_matrix()
    matrices = {1: zfind_matrix(), 2: advwnd_rows,
                3: [row for row in advwnd_rows if row[-1] >= row[-2]], 4: puffdz_matrix()}
    with tempfile.TemporaryDirectory(prefix="p7v-oracle-") as temporary:
        stage = pathlib.Path(temporary) / "stage"
        ext.stage(vendor, stage, manifest, spans)
        sources = sorted(str(path) for path in stage.glob("vendor_*.f"))
        binary = stage / "p7v_oracle"
        build = subprocess.run(
            [compiler, "-O0", "-std=legacy", "-ffixed-line-length-72", "-fallow-argument-mismatch",
             "-fno-automatic", f"-I{stage}", "-o", str(binary), *sources,
             str(stage / "p7v_oracle_driver.f")],
            capture_output=True, text=True)
        if build.returncode != 0:
            fail(f"vendor oracle compilation failed: {build.stderr.strip()[-800:]}")
        version = subprocess.run([compiler, "--version"], capture_output=True, text=True)

        for mode in sorted(matrices):
            rows = matrices[mode]
            body = payload(mode, rows)
            probe_run = subprocess.run([str(args.probe), "--mode", str(mode)], input=body,
                                       capture_output=True, text=True)
            if probe_run.returncode != 0:
                fail(f"mode {mode}: probe failed: {probe_run.stderr.strip()[-400:]}")
            oracle_run = subprocess.run([str(binary)], input=f"{mode}\n{body}", capture_output=True,
                                        text=True, cwd=stage)
            if oracle_run.returncode != 0:
                fail(f"mode {mode}: oracle failed: {oracle_run.stderr.strip()[-400:]}")
            probe_rows = parse_rows(probe_run.stdout)
            oracle_rows = parse_rows(oracle_run.stdout)
            if sorted(oracle_rows) != sorted(probe_rows):
                fail(f"mode {mode}: case sets differ (oracle {len(oracle_rows)}, "
                     f"probe {len(probe_rows)})")
            worst = 0.0
            worst_case = 0
            for key in sorted(oracle_rows):
                want_row = oracle_rows[key]
                got_row = probe_rows[key]
                if len(want_row) != len(got_row):
                    fail(f"mode {mode} case {key}: column count {len(want_row)} vs {len(got_row)}")
                for column, (want, got) in enumerate(zip(want_row, got_row)):
                    if not math.isfinite(want) or not math.isfinite(got):
                        fail(f"mode {mode} case {key} column {column}: non-finite {want!r}/{got!r}")
                    if abs(want - got) > max(TOLERANCE_RELATIVE * abs(want), TOLERANCE_ABSOLUTE):
                        fail(f"mode {mode} case {key} column {column}: oracle={want!r} "
                             f"probe={got!r}")
                    relative = abs(want - got) / max(abs(want), 1.0e-30)
                    if relative > worst:
                        worst = relative
                        worst_case = key
            name = {1: "ZFIND", 2: "ADVWND", 3: "ADVECT", 4: "PUFFDZ"}[mode]
            print(f"P7V_{name}_ORACLE_PARITY=PASS CASES={len(oracle_rows)} "
                  f"COLUMNS={len(next(iter(oracle_rows.values())))} MISMATCHES=0 "
                  f"TOLERANCE_REL={TOLERANCE_RELATIVE:.0e} MAX_REL={worst:.3e} "
                  f"WORST_CASE={worst_case}")
        print(f"P7V_FORTRAN_COMPILER={version.stdout.splitlines()[0].strip()}")
    print("P7V_ADVECTION_PARITY_IS_NOT_A_CONCENTRATION_COMPARISON=true")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
