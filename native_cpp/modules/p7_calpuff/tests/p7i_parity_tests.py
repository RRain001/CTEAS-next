#!/usr/bin/env python3
"""P7I CTSG support blocks: vendor source anchor and Fortran parity.

QATR (Romberg integrator) and TFAC (terrain flow-distortion interpolation) are
extracted verbatim from the unmodified vendor source, pinned by SHA-256,
compiled into a private oracle and compared with the C++ port over case
matrices. No concentration or dispersion physics is involved.
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
ANCHOR = f"{MODULE}/reference/p7i_source_anchor.json"
TOLERANCE_RELATIVE = 1.0e-5
TOLERANCE_ABSOLUTE = 1.0e-30
QATR_QUOTES = (
    "aux(1)=half*(fct(xl)+fct(xu))",
    "aux(i)=half*aux(i-1)+p*sm",
    "aux(ii)=aux(ii+1)+(aux(ii+1)-aux(ii))/(q-1.)",
    "delt2=ABS(y-aux(1))",
    "elseif(delt2/y .LE. eps) then",
    "elseif(delt2 .GE. delt1)then",
    "if(jj .GT. 16000) lstop=1",
)
ROTATE_QUOTES = (
    "s=SIN(ang)",
    "xp=x*c+y*s",
    "yp=-x*s+y*c",
)
TFAC_QUOTES = (
    "if(x.GT.xbegin .AND. x.LT.xend) then",
    "nposm1=INT((x-xbegin)/xspace)",
    "xfac=(x-xnpos)/xspace",
    "th=xfac*(at(1,nposp1)-at(1,npos))+at(1,npos)",
    "tu=one/(th*tl)",
)


def fail(message: str) -> None:
    print(f"P7I_SOURCE_PARITY=FAIL: {message}", file=sys.stderr)
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
        found = subprocess.run(["sh", "-c", f"command -v {candidate}"], capture_output=True, text=True)
        if found.returncode == 0:
            return found.stdout.strip()
    return None


def qatr_matrix() -> list[tuple]:
    rows: list[tuple] = []
    for code in (1, 2, 3, 4, 5):
        for lower, upper in ((0.0, 3.14159265358979), (0.0, 1.0), (1.0, 3.0), (-2.0, 2.0)):
            for dimension in (1, 5, 12, 30):
                rows.append((code, lower, upper, 1.0e-6, dimension))
    return rows


def tfac_matrix() -> list[tuple]:
    """The factor arrays must cover every node the interpolation touches, so the
    point count follows the window and spacing (the vendor reads at(1,nposp1))."""
    rows: list[tuple] = []
    for begin, end, spacing in ((1.0, 5.0, 1.0), (0.0, 4.0, 0.5)):
        points = int((end - begin) / spacing) + 2
        top = [1.0 + 0.25 * index for index in range(points)]
        lateral = [1.0 / (1.0 + index) for index in range(points)]
        for x in (begin - 0.5, begin, begin + 0.25, begin + 1.5, end - 0.25, end, end + 0.5):
            rows.append((x, begin, end, spacing, (top, lateral)))
    return rows


def parse_rows(text: str) -> dict[int, list[float]]:
    rows: dict[int, list[float]] = {}
    for line in text.splitlines():
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
    parser.add_argument("--probe", type=Path, required=True, help="built cteas_p7i_tests")
    parser.add_argument("--repo-root", type=Path, default=REPO_FALLBACK)
    parser.add_argument("--gfortran", help="explicit gfortran executable")
    parser.add_argument("--require", action="store_true",
                        help="fail instead of skipping when no Fortran compiler is available")
    args = parser.parse_args()
    if not args.probe.is_file():
        fail(f"probe binary missing: {args.probe}")
    repo = args.repo_root.resolve()
    ext = load_script(repo / MODULE / "reference/p7i_source_anchor.py", "p7i_anchor")
    vendor = repo / ext.VENDOR_SUBDIR
    manifest, spans = ext.extract(vendor)
    pinned = json.loads((repo / ANCHOR).read_text())
    if pinned != manifest:
        fail(f"vendor source drift: extracted spans/hashes differ from {ANCHOR}")
    print(f"P7I_SOURCE_ANCHOR=PASS VENDOR_SHA256={manifest['vendor_source_sha256']} "
          f"UNITS={','.join(sorted(manifest['units']))}")
    quotes = check_quotes(spans["qatr"], QATR_QUOTES, "QATR")
    quotes += check_quotes(spans["tfac"], TFAC_QUOTES, "TFAC")
    quotes += check_quotes(spans["rotate"], ROTATE_QUOTES, "ROTATE")
    print(f"P7I_QUOTED_SOURCE_STATEMENTS=PASS COUNT={quotes}")

    compiler = find_gfortran(args.gfortran)
    if compiler is not None:
        major = compiler_major(compiler)
        if major is None or major < 10:
            if args.require:
                fail(f"gfortran {compiler} is older than 10 and cannot build the vendor oracle")
            print(f"P7I_FORTRAN_ORACLE=SKIPPED_TOO_OLD_COMPILER {compiler}")
            compiler = None
    if compiler is None:
        if args.require:
            fail("no Fortran compiler available but --require was given")
        print("P7I_FORTRAN_ORACLE=SKIPPED_WITHOUT_FORTRAN")
        return 0

    with tempfile.TemporaryDirectory(prefix="p7i-oracle-") as temporary:
        stage = Path(temporary) / "stage"
        ext.stage(vendor, stage, manifest, spans)
        sources = sorted(str(path) for path in stage.glob("vendor_*.f"))
        driver = str(stage / "p7i_oracle_driver.f")
        binary = stage / "p7i_oracle"
        build = subprocess.run(
            [compiler, "-O0", "-std=legacy", "-ffixed-line-length-72", "-fallow-argument-mismatch",
             "-fno-automatic", f"-I{stage}", "-o", str(binary), *sources, driver],
            capture_output=True, text=True)
        if build.returncode != 0:
            fail(f"vendor oracle compilation failed: {build.stderr.strip()[-800:]}")
        version = subprocess.run([compiler, "--version"], capture_output=True, text=True)

        # QATR matrix.
        rows = qatr_matrix()
        case_lines = "\n".join(
            f"{index + 1} {code} {lower!r} {upper!r} {eps!r} {dimension}"
            for index, (code, lower, upper, eps, dimension) in enumerate(rows)) + "\n"
        probe_run = subprocess.run([str(args.probe), "--qatr-matrix"], input=case_lines,
                                   capture_output=True, text=True)
        if probe_run.returncode != 0:
            fail(f"probe QATR matrix failed: {probe_run.stderr.strip()}")
        oracle_run = subprocess.run([str(binary)], input="1\n" + case_lines, capture_output=True,
                                    text=True, cwd=stage)
        if oracle_run.returncode != 0:
            fail(f"vendor oracle QATR run failed: {oracle_run.stderr.strip()[-400:]}")
        probe_rows = parse_rows(probe_run.stdout)
        oracle_rows = parse_rows(oracle_run.stdout)
        worst = 0.0
        worst_case = 0
        for key in sorted(oracle_rows):
            want_value, want_status = oracle_rows[key][0], int(oracle_rows[key][1])
            got_value, got_status = probe_rows[key][0], int(probe_rows[key][1])
            if want_status != got_status:
                fail(f"QATR case {key}: status oracle={want_status} probe={got_status}")
            if not math.isfinite(want_value) or not math.isfinite(got_value):
                fail(f"QATR case {key}: non-finite oracle={want_value!r} probe={got_value!r}")
            if abs(want_value - got_value) > max(TOLERANCE_RELATIVE * abs(want_value),
                                                 TOLERANCE_ABSOLUTE):
                fail(f"QATR case {key}: oracle={want_value!r} probe={got_value!r}")
            relative = abs(want_value - got_value) / max(abs(want_value), 1.0e-30)
            if relative > worst:
                worst = relative
                worst_case = key
        print(f"P7I_QATR_ORACLE_PARITY=PASS CASES={len(rows)} TOLERANCE_REL={TOLERANCE_RELATIVE:.0e} "
              f"MAX_REL={worst:.3e} WORST_CASE={worst_case} STATUS_FLAGS_MATCH=true")

        # TFAC matrix.
        tfac_rows = tfac_matrix()
        lines: list[str] = []
        for index, (x, begin, end, spacing, factors) in enumerate(tfac_rows):
            lines.append(f"{index + 1} {x!r} {begin!r} {end!r} {spacing!r} {len(factors[0])}")
            for top, lateral in zip(factors[0], factors[1]):
                lines.append(f"{top!r} {lateral!r}")
        case_lines = "\n".join(lines) + "\n"
        probe_run = subprocess.run([str(args.probe), "--tfac-matrix"], input=case_lines,
                                   capture_output=True, text=True)
        if probe_run.returncode != 0:
            fail(f"probe TFAC matrix failed: {probe_run.stderr.strip()}")
        oracle_run = subprocess.run([str(binary)], input="2\n" + case_lines, capture_output=True,
                                    text=True, cwd=stage)
        if oracle_run.returncode != 0:
            fail(f"vendor oracle TFAC run failed: {oracle_run.stderr.strip()[-400:]}")
        probe_rows = parse_rows(probe_run.stdout)
        oracle_rows = parse_rows(oracle_run.stdout)
        worst = 0.0
        worst_case = 0
        for key in sorted(oracle_rows):
            for column, (want, got) in enumerate(zip(oracle_rows[key], probe_rows[key])):
                if abs(want - got) > max(TOLERANCE_RELATIVE * abs(want), TOLERANCE_ABSOLUTE):
                    fail(f"TFAC case {key} column {column}: oracle={want!r} probe={got!r}")
                relative = abs(want - got) / max(abs(want), 1.0e-30)
                if relative > worst:
                    worst = relative
                    worst_case = key
        print(f"P7I_TFAC_ORACLE_PARITY=PASS CASES={len(tfac_rows)} TOLERANCE_REL={TOLERANCE_RELATIVE:.0e} "
              f"MAX_REL={worst:.3e} WORST_CASE={worst_case}")
        # ROTATE matrix.
        rotate_rows = [(x, y, angle)
                       for x in (0.0, 1.0, -2.5)
                       for y in (0.0, 3.0, -1.5)
                       for angle in (0.0, 0.5, 1.5707963, -2.0, 3.1415926)]
        case_lines = "\n".join(f"{index + 1} {x!r} {y!r} {angle!r}"
                               for index, (x, y, angle) in enumerate(rotate_rows)) + "\n"
        probe_run = subprocess.run([str(args.probe), "--rotate-matrix"], input=case_lines,
                                   capture_output=True, text=True)
        if probe_run.returncode != 0:
            fail(f"probe ROTATE matrix failed: {probe_run.stderr.strip()}")
        oracle_run = subprocess.run([str(binary)], input="3\n" + case_lines, capture_output=True,
                                    text=True, cwd=stage)
        if oracle_run.returncode != 0:
            fail(f"vendor oracle ROTATE run failed: {oracle_run.stderr.strip()[-400:]}")
        probe_rows = parse_rows(probe_run.stdout)
        oracle_rows = parse_rows(oracle_run.stdout)
        worst = 0.0
        worst_case = 0
        for key in sorted(oracle_rows):
            for column, (want, got) in enumerate(zip(oracle_rows[key], probe_rows[key])):
                if abs(want - got) > max(TOLERANCE_RELATIVE * abs(want), TOLERANCE_ABSOLUTE):
                    fail(f"ROTATE case {key} column {column}: oracle={want!r} probe={got!r}")
                relative = abs(want - got) / max(abs(want), 1.0e-30)
                if relative > worst:
                    worst = relative
                    worst_case = key
        print(f"P7I_ROTATE_ORACLE_PARITY=PASS CASES={len(rotate_rows)} "
              f"TOLERANCE_REL={TOLERANCE_RELATIVE:.0e} MAX_REL={worst:.3e} WORST_CASE={worst_case}")
        print(f"P7I_FORTRAN_COMPILER={version.stdout.splitlines()[0].strip()}")
    print("P7I_CTSG_SUPPORT_PARITY_IS_NOT_A_CONCENTRATION_TEST=true")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
