#!/usr/bin/env python3
"""S3 bounded, immutable-file native P4/P5 writer-lineage evidence.

Runs the genuine C++ writers on preserved 2022 FSL and 2022 six-day SMERGE
GENERIC inputs, and compares bytes against the *separate* frozen originals.
This deliberately does NOT claim raw NOAA -> FSL/GENERIC reproduction,
P4 final UP.DAT merging, or any P6 physics acceptance.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path, PurePosixPath

CASE_ID = "hefei5km_2022_reference_case_20261011"
FSL = "met/upperair/2022/igra2fsl/58424.txt"
FSL_OUTPUT = "met/upperair/2022/fsl_data/up_58424_2022.dat"
SURF_INPUT = "met/surface/isd2smerge_ready/583210-99999.csv"
SURF_CONTROL = "run/smerge/smerge.inp"
SURF_OUTPUT = "run/smerge/surf.dat"
SOURCE_ROLE_FILES = {
    "p4_igra_fsl": FSL,
    "p4_frozen_full_2022_updat": FSL_OUTPUT,
    "p4_frozen_calmet_final_updat": "met/upperair/final/up_58424.dat",
    "p4_frozen_station_meta": "met/upperair/final/stations.csv",
    "p4_original_read62_deck": "run/read62/read62.inp",
    "p5_generic": SURF_INPUT,
    "p5_frozen_smerge_deck": SURF_CONTROL,
    "p5_frozen_surfdat": SURF_OUTPUT,
    "p5_frozen_calmet_final_surfdat": "met/surface/final/surf.dat",
    "p5_frozen_station_meta": "met/surface/final/stations.csv",
    "research_time": "grid/research_time",
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def file_source(path: Path) -> dict[str, object]:
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"required source absent or symlink: {path}")
    return {"sha256": sha256(path), "bytes": path.stat().st_size}


def checked_file(root: Path, name: str) -> Path:
    path = root
    for part in PurePosixPath(name).parts:
        path = path / part
        if path.is_symlink():
            raise ValueError(f"source contains symlink: {name}")
    file_source(path)
    return path


def run_checked(command: list[str], cwd: Path, audit: Path) -> None:
    result = subprocess.run(command, cwd=cwd, capture_output=True, text=True,
                            check=False, timeout=180)
    audit.write_text(
        "command=" + json.dumps(command, ensure_ascii=True) + "\n"
        + f"exit={result.returncode}\n"
        + "stdout:\n" + result.stdout + "\nstderr:\n" + result.stderr,
        encoding="utf-8",
    )
    if result.returncode != 0:
        raise ValueError("real native writer failed, see audit: " + audit.name)


def byte_identity(candidate: Path, reference: Path, role: str) -> dict[str, object]:
    observed = file_source(candidate)
    frozen = file_source(reference)
    if observed != frozen:
        raise ValueError(f"{role} original-vs-native output bytes or SHA256 mismatch")
    return {"status": "EXACT_BYTE_PARITY", "native": observed, "frozen": frozen}


def run(case: Path, p4: Path, p5: Path, work: Path, source_head: str) -> dict[str, object]:
    if not re.fullmatch(r"[0-9a-f]{40}", source_head):
        raise ValueError("not an exact source commit SHA")
    if case.name != CASE_ID or not case.is_dir() or case.is_symlink():
        raise ValueError("not the locked 2022 Hefei case")
    for binary in (p4, p5):
        if not binary.is_file() or binary.is_symlink() or not os.access(binary, os.X_OK):
            raise ValueError("native P4/P5 producer binary unavailable or symlink")
    if work.exists() or not work.parent.is_dir() or work.parent.is_symlink():
        raise ValueError("scratch must be new beneath an existing real directory")
    if work.resolve().is_relative_to(case.resolve()) or case.resolve().is_relative_to(work.resolve()):
        raise ValueError("case and scratch must be isolated")
    inputs = {role: file_source(checked_file(case, path))
              for role, path in SOURCE_ROLE_FILES.items()}
    if checked_file(case, "grid/research_time").read_text().strip() != (
            "BEGIN:20220101-000000\nEND:20220106-230000"):
        raise ValueError("not frozen six-day research time")
    control = checked_file(case, SURF_CONTROL).read_text(encoding="utf-8")
    required_control = {
        "NFF": "1", "SURFDAT": "surf.dat", "JDAT": "8",
        "IOFORM": "2", "IOPACK": "0", "LPREV": "F",
        "SFCMET": "../../met/surface/isd2smerge_ready/583210-99999.csv",
        "IFSTN": "583210", "ASTZ": "UTC+0000",
    }
    for key, wanted in required_control.items():
        found = re.findall(r"!\s*" + key + r"\s*=\s*([^!]+)!", control,
                           flags=re.IGNORECASE)
        if len(found) != 1 or found[0].strip() != wanted:
            raise ValueError(f"P5 unsupported control {key} ({found}); no option fallback")
    work.mkdir()
    (work / "audit").mkdir()
    # P4 original FSL for full year, not the postprocessed CALMET UP.DAT.
    up = work / "native-2022-unmerged-up.dat"
    run_checked(
        [str(p4.resolve()), str(checked_file(case, FSL).resolve()), str(up),
         "2022-01-01T00:00Z", "2022-12-31T23:00Z", "500", "58424"],
        work, work / "audit" / "p4-native-writer.log",
    )
    p4_result = byte_identity(up, checked_file(case, FSL_OUTPUT), "P4 full-year READ62")
    # S3-B: Run the EXISTING scoped P4 final CALMET merge from the genuinely
    # new C++ full-year UP.DAT. Imported merger globals are rebound only to a
    # wholly isolated scratch root, not the repository's project/current.
    scratch_year = work / FSL_OUTPUT
    scratch_year.parent.mkdir(parents=True)
    shutil.copyfile(up, scratch_year)
    scratch_station = work / "met/upperair/2022/upperair_station_used_list.txt"
    scratch_station.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(checked_file(case, "met/upperair/2022/upperair_station_used_list.txt"),
                    scratch_station)
    scratch_period = work / "grid/research_time"
    scratch_period.parent.mkdir(parents=True)
    shutil.copyfile(checked_file(case, "grid/research_time"), scratch_period)
    repo_root = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(repo_root))
    merge_path = repo_root / "native_cpp/modules/p4_read62/data_prep/merge_final_upperair.py"
    module_spec = importlib.util.spec_from_file_location("s3_scoped_p4_final_merge", merge_path)
    if module_spec is None or module_spec.loader is None:
        raise ValueError("P4 scoped merge source missing")
    merge = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(merge)
    merge.CASE_ROOT = work
    merge.UPPERAIR_ROOT = work / "met/upperair"
    merge.RESEARCH_TIME_FILE = scratch_period
    merge.FINAL_STATIONS_CSV = work / "met/upperair/final/stations.csv"
    begin, end = merge.parse_research_time(scratch_period)
    station_files = merge.collect_station_files([2022])
    station_meta = merge.collect_station_metadata([2022])
    if set(station_files) != {"58424"} or set(station_meta) != {"58424"}:
        raise ValueError("P4 final merge source station selection mismatch")
    final_dir = work / "met/upperair/final"
    final_up = merge.merge_station_files("58424", station_files["58424"],
                                         begin, end, final_dir)
    merge.write_station_metadata_csv(final_dir, station_meta)
    p4_final_result = byte_identity(final_up,
                                    checked_file(case, "met/upperair/final/up_58424.dat"),
                                    "P4 actual CALMET UP.DAT")
    p4_final_station_result = byte_identity(
        merge.FINAL_STATIONS_CSV,
        checked_file(case, "met/upperair/final/stations.csv"),
        "P4 actual CALMET stations.csv",
    )
    # Stage the P5 control and GENERIC in their original relative positions.
    # Do not run P5 against original case (would overwrite its frozen surf.dat).
    target_deck = work / SURF_CONTROL
    target_deck.parent.mkdir(parents=True)
    shutil.copyfile(checked_file(case, SURF_CONTROL), target_deck)
    target_input = work / SURF_INPUT
    target_input.parent.mkdir(parents=True)
    shutil.copyfile(checked_file(case, SURF_INPUT), target_input)
    if file_source(target_deck) != inputs["p5_frozen_smerge_deck"] or (
        file_source(target_input) != inputs["p5_generic"]
    ):
        raise ValueError("P5 stage copy diverged from frozen inputs")
    run_checked([str(p5.resolve()), str(target_deck.resolve())], work,
                work / "audit" / "p5-native-writer.log")
    surf = work / SURF_OUTPUT
    p5_result = byte_identity(surf, checked_file(case, SURF_OUTPUT),
                              "P5 six-day SURF.DAT")
    p5_final_result = byte_identity(surf,
                                    checked_file(case, "met/surface/final/surf.dat"),
                                    "P5 CALMET final SURF.DAT")
    report = {
        "schema": "CTEAS_S3_FROZEN_INTERMEDIATE_NATIVE_WRITER_V1",
        "status": "PASS_SCOPED_P4_FINAL_AND_P5_CPP_WRITER_BYTE_IDENTITY",
        "case": CASE_ID, "source_head": source_head,
        "p4_source_path": FSL, "p4_control": "JDAT2_IFMT1_PSTOP500_FULL_2022",
        "p5_source_path": SURF_INPUT,
        "p5_control": "JDAT8_IOFORM2_2022_01_01_TO_06",
        "grid_origin_xrefkm": "510.885", "grid_origin_yrefkm": "3531.269",
        "native_executables": {"p4_read62": file_source(p4),
                               "p5_smerge": file_source(p5)},
        "input_roles": inputs,
        "p4_intermediate_full_year": p4_result,
        "p4_final_calmet_updat": p4_final_result,
        "p4_final_calmet_station_metadata": p4_final_station_result,
        "p4_final_merge_source_sha256": sha256(merge_path),
        "p5_intermediate_six_days": p5_result,
        "p5_final_six_days": p5_final_result,
        "p4_final_updat_reproduced_this_run": True,
        "raw_igra_to_fsl_reproduced_this_run": False,
        "raw_isd_to_generic_reproduced_this_run": False,
        "native_p6_rerun_with_new_p4p5": False,
        "scientific_acceptance": "INTERMEDIATE_BYTES_ONLY_NOT_P6_SCIENCE",
        "frozen_calmet_updat_only_hashed_not_recomputed": False,
    }
    (work / "audit" / "lineage.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("S3_P4_FULL_YEAR_NATIVE_READ62_BYTE_IDENTITY=PASS")
    print("S3_P4_FINAL_CALMET_UPDAT_AND_STATIONS_BYTE_IDENTITY=PASS")
    print("S3_P5_SIX_DAY_NATIVE_SMERGE_BYTE_IDENTITY=PASS")
    print("S3_P4_P5_FINAL_STATUS=" + report["status"])
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", required=True, type=Path)
    parser.add_argument("--p4", required=True, type=Path)
    parser.add_argument("--p5", required=True, type=Path)
    parser.add_argument("--work", required=True, type=Path)
    parser.add_argument("--source-head", required=True)
    args = parser.parse_args()
    run(args.case.resolve(), args.p4.resolve(), args.p5.resolve(),
        args.work.absolute(), args.source_head)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
