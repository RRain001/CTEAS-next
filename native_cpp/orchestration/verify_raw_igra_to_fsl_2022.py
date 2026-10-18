#!/usr/bin/env python3
"""S3-D: reproduce the selected P4 FSL from archived real NOAA IGRA.

No network, no project/current, no original-case writes. Scoped to exactly
2022/CHM00058424 and the archived selected provenance record. This does NOT
attest downloader/station discovery or P5 NOAA->GENERIC science.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import subprocess
from pathlib import Path

from native_cpp.modules.p4_read62.data_prep import parse_igra_to_csv, read

CASE_ID = "hefei5km_2022_reference_case_20261011"
STATION = "CHM00058424"
FSL_STATION = "58424"
RAW_FILE = "CHM00058424-data.txt"
YEAR = 2022
PSTOP = 500.0
RAW_RELATIVE = f"met/upperair/{YEAR}/{RAW_FILE}"
STATION_RELATIVE = f"met/upperair/{YEAR}/upperair_station_used_list.txt"
PSTOP_RELATIVE = f"met/upperair/{YEAR}/pstop_hpa.txt"
FSL_RELATIVE = f"met/upperair/{YEAR}/igra2fsl/{FSL_STATION}.txt"


def insist(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as src:
        for b in iter(lambda: src.read(1024 * 1024), b""):
            h.update(b)
    return h.hexdigest()


def git_blob(repo: Path, rel: str, head: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", f"{head}:{rel}"],
        check=True, capture_output=True, text=True, timeout=15,
    ).stdout.strip()
    insist(bool(re.fullmatch(r"[0-9a-f]{40}", result)), "GIT_BLOB_INVALID")
    return result


def assert_immutable(repo: Path, path: Path, head: str) -> dict:
    insist(not path.is_symlink() and path.is_file(),
           f"CASE_SOURCE_MISSING_OR_SYMLINK {path}")
    rel = path.relative_to(repo).as_posix()
    actual = subprocess.run(
        ["git", "-C", str(repo), "hash-object", str(path)],
        check=True, capture_output=True, text=True, timeout=40,
    ).stdout.strip()
    expected = git_blob(repo, rel, head)
    insist(actual == expected, f"RAW_INPUT_NOT_AT_PINNED_GIT_BLOB {rel}")
    return {"git_blob": expected, "sha256": sha256(path),
            "bytes": path.stat().st_size, "path": rel}


def preflight(repo: Path, case: Path, head: str) -> dict:
    insist(bool(re.fullmatch(r"[0-9a-f]{40}", head)), "BAD_SOURCE_SHA")
    expected_head = subprocess.check_output(
        ["git", "-C", str(repo), "rev-parse", "HEAD"], text=True
    ).strip()
    insist(head == expected_head, "SOURCE_HEAD_MISMATCH")
    insist(case.name == CASE_ID and case.resolve() == (
        repo / "project/cases" / CASE_ID).resolve(),
        "CASE_NOT_CANONICAL")
    insist(not case.is_symlink(), "CASE_SYMLINK_FORBIDDEN")
    paths = {
        "raw_igra": case / RAW_RELATIVE,
        "station_selection": case / STATION_RELATIVE,
        "pstop": case / PSTOP_RELATIVE,
        "frozen_fsl": case / FSL_RELATIVE,
    }
    sources = {name: assert_immutable(repo, path, head)
               for name, path in paths.items()}
    insist(paths["pstop"].read_text().strip() == "500.0",
           "PSTOP_NOT_LOCKED_500HPA")
    with paths["station_selection"].open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    insist(len(rows) == 1, "EXPECTED_EXACTLY_ONE_SELECTED_IGRA_STATION")
    row = rows[0]
    insist(row["id"] == STATION and row["year"] == "2022",
           "WRONG_IGRA_STATION_YEAR")
    insist(Path(row["raw_txt"]).name == RAW_FILE,
           "STATION_RAW_FILENAME_MISMATCH")
    # The historic absolute path in the station CSV was a former developer
    # checkout. Only the already checked Git case-local file is authorized.
    insist(Path(row["raw_txt"]).is_absolute(),
           "HISTORIC_STATION_SELECTION_SCHEMA_CHANGED")
    lat, lon, elevation = (float(row[k]) for k in ("lat", "lon", "elev_m"))
    insist((lat, lon, elevation) == (31.9398, 117.1416, 62.0),
           "LOCKED_IGRA_STATION_GEOMETRY_CHANGED")
    return {"files": sources, "station": {"id": STATION,
            "selected_year": YEAR, "effective_lat": lat, "effective_lon": lon,
            "elevation_m": elevation, "historic_raw_path_ignored": True}}


def replay(repo: Path, case: Path, work: Path, head: str) -> dict:
    report = preflight(repo, case, head)
    insist(not work.exists() and work.parent.is_dir() and
           not work.resolve().is_relative_to(case.resolve()) and
           not case.resolve().is_relative_to(work.resolve()),
           "WORKDIR_MUST_BE_NEW_AND_OUTSIDE_CASE")
    work.mkdir()
    raw = case / RAW_RELATIVE
    profiles = work / "cleaned-original-2022"
    stats = parse_igra_to_csv.convert_igra_to_csv(
        raw, profiles, FSL_STATION, YEAR, 62.0, PSTOP)
    original = sorted(
        p for p in profiles.glob(f"{FSL_STATION}_*.csv")
        if p.stem.endswith(("00", "12")) and
           p.stem.split("_", 1)[-1].startswith("2022"))
    original_slots = len(original)
    expected_slots = 2 * 365
    insist(original_slots * 5 > expected_slots * 4,
           "OBSERVED_00_12_IGRA_COVERAGE_NOT_GREATER_THAN_80PCT")
    filled = parse_igra_to_csv.ensure_year_completeness(
        profiles, FSL_STATION, YEAR, dropped_slots=stats.get("dropped_slots"))
    newly_generated_fsl = work / "58424-replayed-from-raw-igra.txt"
    outcome = read.convert_csv_profiles_to_fsl(
        csv_dir=profiles,
        output_path=newly_generated_fsl,
        station_id=FSL_STATION,
        latitude="31.94N", longitude="117.14E",
        elevation="62", target_year=str(YEAR),
        # Archive predates P4EXACT_LAT/P4EXACT_LON header additions.
        # Only this independent archive-parity comparator emits the legacy
        # FSL records. Preserve modern exact-coordinate production support.
        min_pressure_hpa=PSTOP, exact_lat=None,
        exact_lon=None, coord_digits=6)
    new_sha = sha256(newly_generated_fsl)
    reference = case / FSL_RELATIVE
    frozen_sha = report["files"]["frozen_fsl"]["sha256"]
    equal = new_sha == frozen_sha and (
        newly_generated_fsl.stat().st_size == reference.stat().st_size)
    report.update({
        "schema": "CTEAS_S3D_2022_IGRA_RAW_TO_FSL_V1",
        "source_head": head,
        "selection_policy": "STRICT_GT_80PCT_CLEANED_ORIGINAL_00_12_PROFILES",
        "original_slots": original_slots,
        "expected_original_slots": expected_slots,
        "original_coverage": original_slots/expected_slots,
        "cleaned_original_profile_stats": {
            k: v for k,v in stats.items() if k != "dropped_slots"},
        "cloned_profile_summary": filled,
        "fsl_output_summary": outcome,
        "replayed_fsl": {"sha256": new_sha,
            "bytes": newly_generated_fsl.stat().st_size},
        "reference_fsl": {"sha256": frozen_sha,
            "bytes": reference.stat().st_size},
        "byte_exact": equal,
        "legacy_fsl_header_encoding_for_original_parity": True,
        "fsl_p4exact_header_extensions_written": False,
        "raw_igra_station_discovery_recomputed": False,
        "raw_isd_to_generic_recomputed": False,
        "native_p4_to_p7_recomputed": False,
    })
    audit = work / "raw_igra_fsl_science.json"
    audit.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n",
                     encoding="utf-8")
    insist(equal, "S3D_IGRA_RAW_TO_FSL_BYTE_MISMATCH")
    print(f"S3D_2022_IGRA_ORIGINAL_VALID_COVERAGE={original_slots}/{expected_slots}")
    print("S3D_2022_IGRA_RAW_TO_FSL_BYTES=PASS")
    print("S3D_IGRA_RAW_TO_FSL_SCOPE=STATION_58424_YEAR_2022_PSTOP_500")
    return report


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--repo",type=Path,required=True)
    p.add_argument("--case",type=Path,required=True)
    p.add_argument("--work",type=Path,required=True)
    p.add_argument("--source-head",required=True)
    p.add_argument("--preflight-only",action="store_true")
    args=p.parse_args()
    repo=args.repo.resolve()
    case=args.case.resolve()
    if args.preflight_only:
        info=preflight(repo,case,args.source_head)
        print("S3D_ARCHIVED_IGRA_INPUTS_PINNED=PASS",
              info["files"]["raw_igra"]["sha256"])
    else:
        replay(repo,case,args.work.absolute(),args.source_head)


if __name__=="__main__":
    main()
