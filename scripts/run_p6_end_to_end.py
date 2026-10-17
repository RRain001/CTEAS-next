#!/usr/bin/env python3
"""FORENSIC P6G multi-pass validator (NOT the original one-pass COMP/DIAGNO). P6D wind producer -> P6F CALMET.DAT writer -> P6E
`emit-realcase` -> 45-field comparison against the frozen 2022 reference.

One command runs the whole chain and prints a per-field verdict table plus a
JSON evidence file:

    python3 scripts/run_p6_end_to_end.py \
        --case project/cases/hefei5km_2022_reference_case_20261011 \
        --bin-dir /home/lhy/build/g6/bin \
        --work /home/lhy/build/g6/work

Every segment is driven twice with a different wind provenance and both
verdict sets are reported side by side:

  A  reconstructed wind  : P6D's U/V (`blend`) + W (`w_face`) written into a
                           CALMET.DAT 2.1 by P6F `write-from-p6d` and fed to
                           P6E `emit-realcase --wind-file`.
  B  original wind       : the frozen `met.dat`'s own U/V/W fed to the same
                           `emit-realcase`, the control baseline.

The A/B table (candidate_B as reference, candidate_A as candidate) is the
end-to-end error that the P6D wind-reconstruction segment introduces once it
propagates through the P6E micrometeorology chain.

An auxiliary table compares the P6F-reconstructed CALMET.DAT itself against
the frozen file, which is where the 27 P6D-owned U/V/W fields are judged
(P6E `emit-realcase` never writes them; it only consumes them as input).

Nothing here invents values: a segment that fails closed aborts the run with
the tool's own error and the report stays unwritten.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import subprocess
import sys
import time

FROZEN_MET_SHA256 = (
    "b1823cda92280888d70b00961ab39486036a3086e18637fff21efb4f4b237d30")
FROZEN_PUFF_INP_SHA256 = (
    "cf5cca70cb75b1aac92f86fdc100500e901a8b904d056c73b2330175793532bc")

# The exact hourly sequence the frozen case declares: 2022-01-01T00:00Z ->
# 2022-01-06T23:00Z, 143 one-hour intervals.
FROZEN_HOURS = 143
FROZEN_INTERVALS = 143
FROZEN_CELLS = 50 * 50
FROZEN_FIELDS_PER_HOUR = 45

P6D_TARGET = "cteas_p6_realcase_wind_field"
P6F_TARGET = "cteas_p6f_calmet_dat21_writer"
P6E_TARGET = "p6e_calmet_dat21"
BRIDGE_TARGET = "p6e_p6c_hourly_bridge"

# Where each standalone CMake project lives, relative to the repository root.
P6D_PROJECT = "native_cpp/modules/p6_calmet"
P6F_PROJECT = "native_cpp/modules/p6_calmet/p6f"
P6E_PROJECT = "native_cpp/modules/p6_calmet/p6e"


def sha256_of(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


class Failure(RuntimeError):
    pass


def run(argv, log: pathlib.Path, stage: str):
    """Run one chain segment, tee stdout/stderr to `log`, fail closed."""
    started = time.time()
    proc = subprocess.run([str(a) for a in argv], capture_output=True, text=True)
    elapsed = time.time() - started
    log.parent.mkdir(parents=True, exist_ok=True)
    log.write_text(
        "$ " + " ".join(str(a) for a in argv) + "\n"
        + f"# exit={proc.returncode} elapsed_s={elapsed:.3f}\n"
        + "---- stdout ----\n" + proc.stdout
        + "---- stderr ----\n" + proc.stderr)
    print(f"[{stage}] {elapsed:7.2f} s  exit={proc.returncode}")
    if proc.returncode != 0:
        raise Failure(
            f"{stage} failed (exit {proc.returncode}); see {log}\n"
            + proc.stdout[-2000:] + proc.stderr[-2000:])
    return proc, elapsed


def run_compare(tool, reference, candidate, out_json, log, stage):
    """`p6e_calmet_dat21 compare`: exit 1 means numeric exceedances, not an
    error, so only the JSON body decides."""
    proc = subprocess.run(
        [str(tool), "compare", "--reference", str(reference),
         "--candidate", str(candidate), "--out", str(out_json)],
        capture_output=True, text=True)
    log.parent.mkdir(parents=True, exist_ok=True)
    log.write_text(
        f"$ {tool} compare --reference {reference} --candidate {candidate}\n"
        + f"# exit={proc.returncode}\n"
        + "---- stdout ----\n" + proc.stdout
        + "---- stderr ----\n" + proc.stderr)
    try:
        report = json.loads(proc.stdout)
    except json.JSONDecodeError as error:
        raise Failure(
            f"{stage} comparator did not return JSON (exit {proc.returncode}): "
            f"{error}\n{proc.stderr[-2000:]}") from error
    return report


def verdict_of(entry: dict) -> str:
    if entry["denominator"] == 0.0:
        if entry["missing_candidate"] > 0.0 or entry["missing_reference"] > 0.0:
            return "NOT_PRODUCED"
        return "NO_DATA"
    return "PASS" if entry["exceedances"] == 0.0 else "FAIL"


def table_from(comparison: dict) -> list:
    rows = []
    for entry in comparison["fields"]:
        rows.append({
            "label": entry["label"],
            "denominator": entry["denominator"],
            "missing_reference": entry["missing_reference"],
            "missing_candidate": entry["missing_candidate"],
            "max_abs_error": entry["max_abs_error"],
            "max_rel_error": entry["max_rel_error"],
            "abs_limit": entry["abs_limit"],
            "rel_limit": entry["rel_limit"],
            "exceedances": entry["exceedances"],
            "verdict": verdict_of(entry),
        })
    return rows


def fmt(value: float) -> str:
    if value == 0.0:
        return "0"
    if abs(value) < 1e-3 or abs(value) >= 1e4:
        return f"{value:.5g}"
    return f"{value:.6g}"


def print_table(title: str, rows: list) -> None:
    print()
    print(title)
    print(f"{'field':<11} {'denominator':>12} {'miss(ref/cand)':>15} "
          f"{'max_abs':>13} {'max_rel':>12} {'tolerance':>22} {'exceed':>8}  verdict")
    for row in rows:
        misses = f"{int(row['missing_reference'])}/{int(row['missing_candidate'])}"
        tolerance = f"{fmt(row['abs_limit'])}+{fmt(row['rel_limit'])}*|ref|"
        print(f"{row['label']:<11} {int(row['denominator']):>12} {misses:>15} "
              f"{fmt(row['max_abs_error']):>13} {fmt(row['max_rel_error']):>12} "
              f"{tolerance:>22} {int(row['exceedances']):>8}  {row['verdict']}")


def build(repo: pathlib.Path, build_dir: pathlib.Path, jobs: int,
          build_type: str, cxx: str) -> dict:
    """Configure and build the four standalone targets."""
    build_dir.mkdir(parents=True, exist_ok=True)
    # One CMake project per build directory; p6e hosts two targets.
    projects = {
        "p6d": (repo / P6D_PROJECT, [P6D_TARGET]),
        "p6f": (repo / P6F_PROJECT, [P6F_TARGET]),
        "p6e": (repo / P6E_PROJECT, [P6E_TARGET, BRIDGE_TARGET]),
    }
    binaries = {}
    for name, (project, targets) in projects.items():
        target_dir = build_dir / name
        configure = ["cmake", "-S", str(project), "-B", str(target_dir),
                     "-DCMAKE_BUILD_TYPE=" + build_type]
        if cxx:
            configure.append("-DCMAKE_CXX_COMPILER=" + cxx)
        subprocess.run(configure, check=True)
        for target in targets:
            subprocess.run(
                ["cmake", "--build", str(target_dir), "--target", target,
                 "-j", str(jobs)],
                check=True)
            binary = target_dir / target
            if not binary.is_file():
                raise Failure(f"build produced no {binary}")
            binaries[target] = binary
    return binaries


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--repo", default=None,
                        help="repository root (default: parent of this script)")
    parser.add_argument("--case", default=None,
                        help="reference case root (default: <repo>/project/cases/"
                             "hefei5km_2022_reference_case_20261011)")
    parser.add_argument("--met-dat", default=None,
                        help="frozen reference CALMET.DAT (default: <case>/run/met/met.dat)")
    parser.add_argument("--geo-dat", default=None,
                        help="GEO.DAT 2.1 (default: <case>/geo/makegeo/geo.dat)")
    parser.add_argument("--surf-dat", default=None,
                        help="SURF.DAT 2.1 (default: <case>/met/surface/final/surf.dat)")
    parser.add_argument("--up-dat", default=None,
                        help="UP.DAT 2.1 (default: <case>/met/upperair/final/up_58424.dat)")
    parser.add_argument("--up-station", type=int, default=58424)
    parser.add_argument("--work", default="p6g-end-to-end-work",
                        help="scratch/output directory (created)")
    parser.add_argument("--build-dir", default=None,
                        help="if set, configure+build the four targets into it")
    parser.add_argument("--build-type", default="Debug",
                        help="CMAKE_BUILD_TYPE for --build-dir (default Debug, "
                             "the module's documented -Werror build)")
    parser.add_argument("--cxx", default="g++-12",
                        help="CMAKE_CXX_COMPILER for --build-dir; the modules "
                             "need a C++20 toolchain (default g++-12, empty "
                             "string = let CMake choose)")
    parser.add_argument("--bin-dir", default=None,
                        help="directory holding the four pre-built binaries")
    parser.add_argument("--p6d-bin", default=None)
    parser.add_argument("--p6f-bin", default=None)
    parser.add_argument("--p6e-bin", default=None)
    parser.add_argument("--bridge-bin", default=None)
    parser.add_argument("--require-native-single-pass", action="store_true",
                        help="fail closed: multi-pass P6D/P6E cannot certify original COMP/DIAGNO")
    parser.add_argument("--hours", type=int, default=FROZEN_HOURS)
    parser.add_argument("--jobs", type=int, default=8)
    parser.add_argument("--original-gamma-dir", default=None,
                        help="DIAGNOSTIC ONLY: source-traced original 143h GAMMA *.f32 "
                             "for independent FRADJ-state bisection")
    parser.add_argument("--original-gamma-manifest", default=None,
                        help="required paired source-pinned gamma_source_manifest.json")
    parser.add_argument("--original-similt-station-dir", default=None,
                        help="FORENSIC ONLY: original source-extracted 143h "
                             "REAL4 EL and ZII as received by SIMILT")
    parser.add_argument("--original-similt-station-manifest", default=None,
                        help="required byte-verified original source station state proof")
    parser.add_argument("--export-native-comp-state", action="store_true",
                        help="write candidate A's native per-hour P6E COMP ZI/ZICONV/DPTT for next-hour P6D state bisection; NOT source injected")
    parser.add_argument("--reuse-p6d", action="store_true",
                        help="reuse an existing <work>/p6d product instead of "
                             "re-running the producer")
    args = parser.parse_args()
    if args.require_native_single_pass:
        raise Failure("this forensic multi-pass script cannot certify an independently native single-pass COMP/DIAGNO solver")

    repo = pathlib.Path(args.repo).resolve() if args.repo else \
        pathlib.Path(__file__).resolve().parent.parent
    case = pathlib.Path(args.case).resolve() if args.case else \
        repo / "project/cases/hefei5km_2022_reference_case_20261011"
    met_dat = pathlib.Path(args.met_dat).resolve() if args.met_dat else case / "run/met/met.dat"
    geo_dat = pathlib.Path(args.geo_dat).resolve() if args.geo_dat else case / "geo/makegeo/geo.dat"
    surf_dat = pathlib.Path(args.surf_dat).resolve() if args.surf_dat else \
        case / "met/surface/final/surf.dat"
    up_dat = pathlib.Path(args.up_dat).resolve() if args.up_dat else \
        case / "met/upperair/final/up_58424.dat"
    work = pathlib.Path(args.work).resolve()
    work.mkdir(parents=True, exist_ok=True)

    bins = {}
    if args.build_dir:
        bins = build(repo, pathlib.Path(args.build_dir).resolve(), args.jobs,
                     args.build_type, args.cxx)
    overrides = {
        P6D_TARGET: args.p6d_bin,
        P6F_TARGET: args.p6f_bin,
        P6E_TARGET: args.p6e_bin,
        BRIDGE_TARGET: args.bridge_bin,
    }
    if args.bin_dir:
        for target in (P6D_TARGET, P6F_TARGET, P6E_TARGET, BRIDGE_TARGET):
            bins.setdefault(target, pathlib.Path(args.bin_dir).resolve() / target)
    for target, override in overrides.items():
        if override:
            bins[target] = pathlib.Path(override).resolve()
    for target in (P6D_TARGET, P6F_TARGET, P6E_TARGET, BRIDGE_TARGET):
        if target not in bins or not bins[target].is_file():
            raise Failure(
                f"missing binary for {target}: pass --bin-dir/--build-dir "
                f"or --{target}-bin")
    for path, label in ((met_dat, "frozen met.dat"), (geo_dat, "GEO.DAT"),
                        (surf_dat, "SURF.DAT"), (up_dat, "UP.DAT")):
        if not path.is_file():
            raise Failure(f"{label} not found: {path}")

    gamma_provenance = None
    if bool(args.original_gamma_dir) != bool(args.original_gamma_manifest):
        raise Failure("original GAMMA directory and source proof must be supplied together")
    if args.original_gamma_dir:
        gamma_dir = pathlib.Path(args.original_gamma_dir).resolve()
        proof_file = pathlib.Path(args.original_gamma_manifest).resolve()
        if not proof_file.is_file() or not gamma_dir.is_dir():
            raise Failure("original GAMMA oracle directory/manifest unavailable")
        gamma_provenance = json.loads(proof_file.read_text())
        if (gamma_provenance.get("status") != "PASS_ORIGINAL_GAMMA_SOURCE_REAL4"
                or not gamma_provenance.get("met_dat_byte_identical")
                or not gamma_provenance.get("met_dat_matches_frozen_reference")
                or gamma_provenance.get("pin", {}).get("original_git_blob")
                   != "437f43bb7f0e51a1919e56664663e1a046986ed0"):
            raise Failure("original GAMMA write-only source/unchanged MET.DAT proof invalid")
        records = gamma_provenance.get("gamma", {}).get("records", [])
        if len(records) != args.hours:
            raise Failure("original GAMMA reference hours do not match P6D run")
        for row in records:
            name = gamma_dir / f"gamma_{row['hour']}.f32"
            if not name.is_file() or name.stat().st_size != 50*50*4 or (
                    sha256_of(name) != row["sha256"]):
                raise Failure("original source GAMMA bytes differ from trace: " + str(name))
        print("[gamma-oracle] FORTRAN ORIGINAL-REFERENCE DIAGNOSTIC ONLY "
              f"({len(records)} hours; source MET.DAT bitwise unchanged)")

    similt_proof = None
    if bool(args.original_similt_station_dir) != bool(args.original_similt_station_manifest):
        raise Failure("original SIMILT station dir and manifest must be supplied together")
    if args.original_similt_station_dir:
        source_dir = pathlib.Path(args.original_similt_station_dir).resolve()
        manifest_path = pathlib.Path(args.original_similt_station_manifest).resolve()
        if not source_dir.is_dir() or not manifest_path.is_file():
            raise Failure("original SIMILT station manifest/data unavailable")
        similt_proof = json.loads(manifest_path.read_text())
        if (similt_proof.get("status")!="PASS_ORIGINAL_SIMILT_ZII_EL_SOURCE_REAL4"
                or not similt_proof.get("original_and_instrumented_met_dat_byte_identical")
                or similt_proof.get("original_git_blob")
                   != "437f43bb7f0e51a1919e56664663e1a046986ed0"
                or similt_proof.get("reference_met_dat_sha256") != FROZEN_MET_SHA256
                or similt_proof.get("hours") != args.hours
                or similt_proof.get("station_1_based") != {"is":26,"js":26,"ns":1}):
            raise Failure("SIMILT station proof is not tied to frozen original Fortran")
        for key, hashkey in (("zii_file","zii_sha256"),("el_file","el_sha256")):
            file=source_dir/similt_proof[key]
            if file.stat().st_size!=args.hours*4 or sha256_of(file)!=similt_proof[hashkey]:
                raise Failure("SIMILT source REAL4 file hash/length mismatch: "+str(file))
        print("[similt-oracle] ORIGINAL FORTRAN STATION ZII/EL, "
              "FOR DIAGNOSTIC USE ONLY; NOT NATIVE C++ MIXHTST/ELUSTR2")

    timings = {}
    started = time.time()

    # ---- input identity: the frozen reference is pinned, not trusted -------
    met_sha = sha256_of(met_dat)
    if met_sha != FROZEN_MET_SHA256:
        raise Failure("frozen met.dat SHA-256 mismatch: " + met_sha)
    puff_inp = case / "run/puff/puff.inp"
    puff_sha = sha256_of(puff_inp) if puff_inp.is_file() else None
    if puff_sha is not None and puff_sha != FROZEN_PUFF_INP_SHA256:
        raise Failure("frozen puff.inp SHA-256 mismatch: " + puff_sha)

    # ---- 1. P6D wind producer --------------------------------------------
    p6d_fields = work / "p6d"
    if args.reuse_p6d and (p6d_fields / "metadata.json").is_file():
        if gamma_provenance is not None or similt_proof is not None:
            raise Failure("--reuse-p6d forbidden with source-traced original state")
        print("[p6d] reusing existing product")
    else:
        p6d_cmd = [bins[P6D_TARGET], "--case", case, "--out", p6d_fields,
                   "--hours", args.hours]
        if gamma_provenance is not None:
            p6d_cmd.extend(["--gamma", pathlib.Path(args.original_gamma_dir).resolve()])
        if similt_proof is not None:
            source_dir = pathlib.Path(args.original_similt_station_dir).resolve()
            p6d_cmd.extend([
                "--zii-cell", source_dir/similt_proof["zii_file"],
                "--el-cell", source_dir/similt_proof["el_file"],
            ])
        _, elapsed = run(p6d_cmd, work / "logs/p6d.log", "p6d")
        timings["p6d_s"] = elapsed
    p6d_metadata = json.loads((p6d_fields / "metadata.json").read_text())

    # ---- 2. P6F writer: P6D arrays -> CALMET.DAT 2.1 ----------------------
    reconstructed = work / "p6f/reconstructed_wind.dat"
    reconstructed.parent.mkdir(parents=True, exist_ok=True)
    _, elapsed = run(
        [bins[P6F_TARGET], "write-from-p6d",
         "--fields", p6d_fields, "--variant", "blend", "--w-field", "w_face",
         "--statics-from", met_dat, "--met-fields-from", met_dat,
         "--irtype", "1", "--out", reconstructed,
         "--report", work / "p6f/report.json"],
        work / "logs/p6f.log", "p6f")
    timings["p6f_s"] = elapsed
    p6f_report = json.loads((work / "p6f/report.json").read_text())

    # ---- 3. observation bridge (P6C SURF.DAT/UP.DAT -> hourly CSV) --------
    hourly_csv = work / "bridge/hourly.csv"
    hourly_csv.parent.mkdir(parents=True, exist_ok=True)
    _, elapsed = run(
        [bins[BRIDGE_TARGET], surf_dat, up_dat, str(args.up_station), hourly_csv],
        work / "logs/bridge.log", "bridge")
    timings["bridge_s"] = elapsed

    # ---- 4. P6E consumer, case A (reconstructed wind) ---------------------
    candidate_a = work / "A/candidate.dat"
    candidate_a.parent.mkdir(parents=True, exist_ok=True)
    p6e_A_cmd=[bins[P6E_TARGET], "emit-realcase", "--reference", met_dat,
         "--observations", hourly_csv, "--wind-file", reconstructed,
         "--geo-file", geo_dat, "--out", candidate_a,
         "--report", work / "A/candidate.json"]
    if args.export_native_comp_state:
        p6e_A_cmd.extend(["--state-prefix", work / "A/native_comp",
                             "--station-flux-csv", p6d_fields / "station_elustr2.csv"])
    _, elapsed = run(p6e_A_cmd, work / "logs/p6e_A.log", "p6e-A")
    timings["p6e_A_s"] = elapsed

    # ---- 5. P6E consumer, case B (original wind, control baseline) --------
    candidate_b = work / "B/candidate.dat"
    candidate_b.parent.mkdir(parents=True, exist_ok=True)
    _, elapsed = run(
        [bins[P6E_TARGET], "emit-realcase", "--reference", met_dat,
         "--observations", hourly_csv, "--wind-file", met_dat,
         "--geo-file", geo_dat, "--out", candidate_b,
         "--report", work / "B/candidate.json"],
        work / "logs/p6e_B.log", "p6e-B")
    timings["p6e_B_s"] = elapsed

    # ---- 6. per-field verdicts -------------------------------------------
    compare_a = run_compare(bins[P6E_TARGET], met_dat, candidate_a,
                            work / "compare_A.json", work / "logs/compare_A.log",
                            "compare-A")
    compare_b = run_compare(bins[P6E_TARGET], met_dat, candidate_b,
                            work / "compare_B.json", work / "logs/compare_B.log",
                            "compare-B")
    compare_ab = run_compare(bins[P6E_TARGET], candidate_b, candidate_a,
                             work / "compare_AB.json", work / "logs/compare_AB.log",
                             "compare-AB")
    compare_wind = run_compare(bins[P6E_TARGET], met_dat, reconstructed,
                               work / "compare_wind.json",
                               work / "logs/compare_wind.log", "compare-wind")

    rows_a = table_from(compare_a)
    rows_b = table_from(compare_b)
    rows_ab = table_from(compare_ab)
    rows_wind = table_from(compare_wind)

    for name, comparison in (("A", compare_a), ("B", compare_b)):
        if comparison["intervals"] != FROZEN_INTERVALS or \
                comparison["fields_per_hour"] != FROZEN_FIELDS_PER_HOUR:
            raise Failure(
                f"candidate {name} has {comparison['intervals']} intervals x "
                f"{comparison['fields_per_hour']} fields, expected "
                f"{FROZEN_INTERVALS} x {FROZEN_FIELDS_PER_HOUR}")
    if len(rows_a) != FROZEN_FIELDS_PER_HOUR:
        raise Failure(f"comparison A reports {len(rows_a)} fields, expected "
                      f"{FROZEN_FIELDS_PER_HOUR}")

    # ---- 7. report --------------------------------------------------------
    report = {
        "scientific_acceptance": "NOT_PASS",
        "native_single_pass_comp_diagno": False,
        "original_reference_backfill": {"p6f_statics": True, "p6f_met_fields": True},
        "scientific_limitation": "Forensic multi-pass with frozen original met.dat backfill; not an independent CALMET.DAT",
        "status": "PASS" if all(
            r["verdict"] in ("PASS", "NOT_PRODUCED") for r in rows_a + rows_b)
            else "FAIL_NUMERIC",
        "reference": {
            "case": str(case), "met_dat": str(met_dat),
            "met_dat_sha256": met_sha,
            "met_dat_sha256_expected": FROZEN_MET_SHA256,
            "puff_inp_sha256": puff_sha,
            "intervals": compare_a["intervals"],
            "fields_per_hour": compare_a["fields_per_hour"],
            "cells": FROZEN_CELLS,
        },
        "wind_provenance": {
            "A": {"source": "P6D blend U/V + w_face written by P6F",
                  "p6d_product": str(p6d_fields),
                  "p6f_calmet_dat": str(reconstructed),
                  "p6f_calmet_dat_sha256": sha256_of(reconstructed),
                  "p6f_report": p6f_report},
            "B": {"source": "frozen met.dat U/V/W", "wind_file": str(met_dat)},
        },
        "p6d_metadata": p6d_metadata,
        "forensic_original_gamma": {
            "mode": ("SOURCE_TRACED_ORIGINAL_REAL4_DIAGNOSTIC_ONLY"
                     if gamma_provenance is not None else "NOT_SUPPLIED"),
            "is_self_contained_cpp_calmet": False if gamma_provenance else None,
            "source_proof": (
                sha256_of(pathlib.Path(args.original_gamma_manifest))
                if gamma_provenance is not None else None),
            "original_met_dat_byte_identical": (
                gamma_provenance["met_dat_byte_identical"]
                if gamma_provenance is not None else None),
        },
        "forensic_original_similt_station": {
            "mode": ("ORIGINAL_FORTRAN_SIMILT_ZII_EL_REFERENCE_ONLY"
                     if similt_proof is not None else "NOT_SUPPLIED"),
            "self_contained_cpp_state_physics": False if similt_proof is not None else None,
            "manifest_sha256": (
                sha256_of(pathlib.Path(args.original_similt_station_manifest))
                if similt_proof is not None else None),
            "station_cell": similt_proof.get("station_1_based") if similt_proof else None,
        },
        "field_table": {
            "A_reconstructed_wind": rows_a,
            "B_original_wind": rows_b,
            "A_minus_B_wind_segment_delta": rows_ab,
            "aux_reconstructed_calmet_dat": rows_wind,
        },
        "timings_s": timings,
        "total_s": time.time() - started,
    }
    report_path = work / "p6g_report.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n")

    print()
    print(f"reference met.dat sha256 = {met_sha}")
    print(f"A wind source  : {reconstructed} "
          f"sha256={report['wind_provenance']['A']['p6f_calmet_dat_sha256']}")
    print(f"B wind source  : {met_dat} (frozen)")
    print(f"report         : {report_path}")
    print("SCIENTIFIC_ACCEPTANCE=NOT_PASS: forensic multi-pass and reference backfill")
    print_table("A) reconstructed wind  vs frozen met.dat", rows_a)
    print_table("B) original wind (control) vs frozen met.dat", rows_b)
    print_table("A - B) error the P6D wind segment propagates through P6E", rows_ab)
    print_table("AUX) P6F-reconstructed CALMET.DAT vs frozen met.dat", rows_wind)

    counts = {}
    for name, rows in (("A", rows_a), ("B", rows_b), ("A-B", rows_ab)):
        for row in rows:
            counts[(name, row["verdict"])] = counts.get((name, row["verdict"]), 0) + 1
    print()
    for name in ("A", "B", "A-B"):
        summary = ", ".join(
            f"{verdict}={counts.get((name, verdict), 0)}"
            for verdict in ("PASS", "FAIL", "NOT_PRODUCED", "NO_DATA"))
        print(f"{name:>4}: {summary}  (of {len(rows_a)} fields)")
    print(f"total wall time: {report['total_s']:.2f} s")
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Failure as error:
        print(f"P6G_END_TO_END_BLOCKED: {error}", file=sys.stderr)
        sys.exit(3)