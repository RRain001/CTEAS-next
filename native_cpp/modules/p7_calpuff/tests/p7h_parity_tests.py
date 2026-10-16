#!/usr/bin/env python3
"""P7H vertical coupling: vendor source anchor and Fortran parity.

Checks against the UNMODIFIED vendor source
(engine/vendor/src/CALPUFF_v7.2.1_L150618/calpuff.for):

1. Anchors: the vendor file and the exact spans of VCBAR, VCOUP, CTADJ (plus
   GETELEV/GETCELL, which VCBAR references and which the oracle links) must
   match reference/p7h_source_anchor.json, and the constants/formulas the C++
   port reproduces must still be present verbatim.
2. VCOUP parity and VCBAR parity: the extracted units are compiled unchanged
   into a private oracle and compared with the C++ probe over case matrices
   that exercise the well-mixed, elevated-receptor, unlimited-lid,
   strong-trapping, puff/slug and plume-tilt branches.

This is a coupling-coefficient contract only: no concentration, deposition or
chemistry is involved.
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
ANCHOR = f"{MODULE}/reference/p7h_source_anchor.json"
TOLERANCE_RELATIVE = 1.0e-5
TOLERANCE_ABSOLUTE = 1.0e-30
VCOUP_QUOTES = (
    "data small/1.0e-10/,srttpi/2.5066283/,pi/3.1415926/",
    "data zunlim/9.9e10/",
    "data szcut/1.0e-2/",
    "if((sz/hlid).gt.0.63) go to 15",
    "szsb = -0.5*(pi*sz/hlid)**2",
    "vcoup = expz/(srttpi*sz1)",
)
VCBAR_QUOTES = (
    "vcbar=vcbar+third*vcoup(icode,zgr,zp,szm1,hlid,hlidmax)",
    "vcbar=vcbar+third*vcoup(icode,zgr,zp,szb1,hlid,hlidmax)",
    "vcbar=vcbar+third*vcoup(icode,zgr,zp,sze1,hlid,hlidmax)",
    "vcbar=vcbar+fourth*vcoup(icode,zgr,zp,szb1,hlid,hlidmax)",
    "vcbar=vcbar+fourth*vcoup(icode,zgr,zp,szb2,hlid,hlidmax)",
    "vcbar=vcbar+fourth*vcoup(icode,zgr,zp,sze1,hlid,hlidmax)",
    "vcbar=vcbar+fourth*vcoup(icode,zgr,zp,sze2,hlid,hlidmax)",
    "hlidmax=hlid",
)
CTADJ_QUOTES = (
    "zrterr = AMIN1(zterr-zbase,zstak)",
    "zpa=AMAX1(zmin, (zht - zrterr))",
    "zpa=zht-(1.-ppcoef)*AMIN1(zht,delzr)",
)


def fail(message: str) -> None:
    print(f"P7H_SOURCE_PARITY=FAIL: {message}", file=sys.stderr)
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
        found = subprocess.run(["sh", "-c", f"command -v {candidate}"], capture_output=True,
                               text=True)
        if found.returncode == 0:
            return found.stdout.strip()
    return None


def vcoup_matrix() -> list[tuple]:
    rows: list[tuple] = []
    for code in (1, 2, 4, 6, 11, 12, 16, 99):
        for receptor in (0.0, 25.0, 150.0, 400.0):
            for source in (0.0, 50.0, 120.0, 300.0):
                for sigma in (0.005, 5.0, 50.0, 200.0, 900.0):
                    for lid, lid_max in ((100.0, 100.0), (500.0, 800.0), (50.0, 300.0)):
                        rows.append((code, receptor, source, sigma, lid, lid_max))
    return rows


def vcbar_matrix() -> list[tuple]:
    rows: list[tuple] = []
    for slug in (0, 1):
        for code in (1, 2):
            for mtilt in (0, 1):
                for lid in (100.0, 500.0):
                    for z in ((0.0, 50.0), (20.0, 120.0), (300.0, 350.0)):
                        for sigma in ((10.0, 40.0), (60.0, 200.0)):
                            rows.append((slug, code, mtilt, lid, z[0], z[1], sigma[0], sigma[1]))
    return rows


def format_vcoup(index: int, row: tuple) -> str:
    code, receptor, source, sigma, lid, lid_max = row
    return f"{index} {code} {receptor!r} {source!r} {sigma!r} {lid!r} {lid_max!r}"


def format_vcbar(index: int, row: tuple) -> str:
    slug, code, mtilt, lid, z_begin, z_end, sigma_begin, sigma_end = row
    zfinal = 150.0
    vsetl = 0.1
    tb1, te1, tb2, te2 = 100.0, 200.0, 120.0, 220.0
    # icase slug code mctadj mtilt hlid ppcoef dgridi ht0 elbase
    #       zb1 ze1 szb1 szm1 sze1 zb2 ze2 szb2 sze2 tb1 te1 tb2 te2 zfinal vsetl
    return (f"{index} {slug} {code} 2 {mtilt} {lid!r} 1.0 0.1 70.8 40.0 "
            f"{z_begin!r} {z_end!r} {sigma_begin!r} {0.5 * (sigma_begin + sigma_end)!r} {sigma_end!r} "
            f"{z_begin!r} {z_end!r} {sigma_begin!r} {sigma_end!r} "
            f"{tb1!r} {te1!r} {tb2!r} {te2!r} {zfinal!r} {vsetl!r}")


def parse_results(text: str) -> dict[int, float]:
    results: dict[int, float] = {}
    for line in text.splitlines():
        fields = line.split()
        if len(fields) != 2:
            continue
        try:
            results[int(fields[0])] = float(fields[1])
        except ValueError:
            continue
    return results


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--probe", type=Path, required=True, help="built cteas_p7e_probe")
    parser.add_argument("--repo-root", type=Path, default=REPO_FALLBACK)
    parser.add_argument("--gfortran", help="explicit gfortran executable")
    parser.add_argument("--require", action="store_true",
                        help="fail instead of skipping when no Fortran compiler is available")
    args = parser.parse_args()
    if not args.probe.is_file():
        fail(f"probe binary missing: {args.probe}")
    repo = args.repo_root.resolve()
    ext = load_script(repo / MODULE / "reference/p7h_source_anchor.py", "p7h_anchor")
    vendor = repo / ext.VENDOR_SUBDIR
    manifest, spans = ext.extract(vendor)
    pinned = json.loads((repo / ANCHOR).read_text())
    if pinned != manifest:
        fail(f"vendor source drift: extracted spans/hashes differ from {ANCHOR}")
    print(f"P7H_SOURCE_ANCHOR=PASS VENDOR_SHA256={manifest['vendor_source_sha256']} "
          f"UNITS={','.join(sorted(manifest['units']))}")
    quotes = check_quotes(spans["vcoup"], VCOUP_QUOTES, "VCOUP")
    quotes += check_quotes(spans["vcbar"], VCBAR_QUOTES, "VCBAR")
    quotes += check_quotes(spans["ctadj"], CTADJ_QUOTES, "CTADJ")
    print(f"P7H_QUOTED_SOURCE_STATEMENTS=PASS COUNT={quotes}")

    compiler = find_gfortran(args.gfortran)
    if compiler is not None:
        major = compiler_major(compiler)
        if major is None or major < 10:
            if args.require:
                fail(f"gfortran {compiler} is older than 10 and cannot build the vendor oracle")
            print(f"P7H_FORTRAN_ORACLE=SKIPPED_TOO_OLD_COMPILER {compiler}")
            compiler = None
    if compiler is None:
        if args.require:
            fail("no Fortran compiler available but --require was given")
        print("P7H_FORTRAN_ORACLE=SKIPPED_WITHOUT_FORTRAN")
        return 0

    with tempfile.TemporaryDirectory(prefix="p7h-oracle-") as temporary:
        stage = Path(temporary) / "stage"
        ext.stage(vendor, stage, manifest, spans)
        sources = sorted(str(path) for path in stage.glob("vendor_*.f"))
        driver = str(stage / "p7h_oracle_driver.f")
        binary = stage / "p7h_oracle"
        build = subprocess.run(
            [compiler, "-O0", "-std=legacy", "-ffixed-line-length-72", "-fallow-argument-mismatch",
             "-fno-automatic", f"-I{stage}", "-o", str(binary), *sources, driver],
            capture_output=True, text=True)
        if build.returncode != 0:
            fail(f"vendor oracle compilation failed: {build.stderr.strip()[-800:]}")
        version = subprocess.run([compiler, "--version"], capture_output=True, text=True)

        for label, rows, formatter, mode, probe_flag in (
                ("VCOUP", vcoup_matrix(), format_vcoup, "1", "--vcoup-matrix"),
                ("VCBAR", vcbar_matrix(), format_vcbar, "2", "--vcbar-matrix")):
            case_lines = "\n".join(formatter(index + 1, row) for index, row in enumerate(rows)) + "\n"
            probe_run = subprocess.run([str(args.probe), probe_flag], input=case_lines,
                                       capture_output=True, text=True)
            if probe_run.returncode != 0:
                fail(f"probe {label} matrix failed: {probe_run.stderr.strip()}")
            probe_results = parse_results(probe_run.stdout)
            oracle_run = subprocess.run([str(binary)], input=mode + "\n" + case_lines,
                                        capture_output=True, text=True, cwd=stage)
            if oracle_run.returncode != 0:
                fail(f"vendor oracle {label} run failed: {oracle_run.stderr.strip()[-400:]}")
            oracle_results = parse_results(oracle_run.stdout)
            if len(probe_results) != len(rows) or len(oracle_results) != len(rows):
                fail(f"{label}: probe {len(probe_results)} / oracle {len(oracle_results)} rows for "
                     f"{len(rows)} cases")
            worst = 0.0
            worst_case = 0
            for key in sorted(oracle_results):
                want = oracle_results[key]
                got = probe_results[key]
                if math.isnan(want) and math.isnan(got):
                    continue
                if not math.isfinite(want) or not math.isfinite(got):
                    fail(f"{label} case {key}: oracle={want!r} probe={got!r}")
                if abs(want - got) > max(TOLERANCE_RELATIVE * abs(want), TOLERANCE_ABSOLUTE):
                    fail(f"{label} case {key}: oracle={want!r} probe={got!r} "
                         f"tolerance rel={TOLERANCE_RELATIVE}")
                relative = abs(want - got) / max(abs(want), 1.0e-30)
                if relative > worst:
                    worst = relative
                    worst_case = key
            print(f"P7H_{label}_ORACLE_PARITY=PASS CASES={len(rows)} "
                  f"TOLERANCE_REL={TOLERANCE_RELATIVE:.0e} MAX_REL={worst:.3e} WORST_CASE={worst_case}")
        print(f"P7H_FORTRAN_COMPILER={version.stdout.splitlines()[0].strip()}")
    print("P7H_COUPLING_PARITY_IS_NOT_A_CONCENTRATION_TEST=true")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
