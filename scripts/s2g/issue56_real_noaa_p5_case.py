#!/usr/bin/env python3
"""#56 real NOAA staged-case P5 generic entrypoint: manually dispatched only.

Input is the existing independently acquired S3-F authentic original ISD +
ISD-Lite 2022/2023 evidence. This script creates NEW real UTM cases, replays
the original annual selector OFFLINE, executes the actual D1-B P5 native
producer, and optionally calls the independent C++ P6 SURF source reader.

The stages do not run P6 fields or P7, and do not compare to original Fortran
SMERGE: neither SCIENCE_ACCEPTED nor a generic scientific parity claim.
Never stage frozen Hefei weather as a new site or publish NOAA originals.
"""
from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

import yaml

from engine.run_met.station_grid import load_strict_utm_grid, lon_lat_in_utm_grid
from native_cpp.orchestration.case_admission import admit_case, verify_immutable
from native_cpp.orchestration.plan import FROZEN_MET_CONTROLS, FROZEN_PUFF_CONTROLS
from native_cpp.modules.p5_smerge.data_prep.isd_lite_wind import filename as lite_filename
from native_cpp.modules.p5_smerge.data_prep.download_isd_by_grid import (
    parse_center, parse_history_txt,
)
from native_cpp.modules.p5_smerge.data_prep.p5_case_producer import produce
from scripts.s3f.verify_real_noaa_2022_2023_station_selection import (
    ROOT, P5_STATIONS, YEARS, digest, p5_check,
)

SCENARIOS = {
    "year2022": ("20220601-000000", "20220602-000000", (2022,)),
    "year2023": ("20230601-000000", "20230602-000000", (2023,)),
    "crossyear": ("20221231-230000", "20230101-030000", (2022, 2023)),
}


def _case_dict(name: str, grid, center_lat: float, center_lon: float,
               first: str, last: str) -> dict:
    """Retain #42 approved physics/profile; meteorology is emission-independent."""
    return {
        "schema_version": 1,
        "case_name": name,
        "settings": {"timezone": "UTC+0000", "pstop_hpa_default": 500},
        "preprocess": {
            "grid": {
                "utm_zone": grid.iutmzn, "hemisphere": grid.lsohem,
                "nz": grid.nz, "resolution_km": grid.dgridkm,
                "domain": {"length_km": grid.nx * grid.dgridkm,
                           "width_km": grid.ny * grid.dgridkm},
                "center": {"latitude": center_lat, "longitude": center_lon},
            },
            "research_time": {"begin": first, "end": last},
            "upperair": {"pstop_hpa": 500, "auto_select_all": True, "station_id": "auto"},
            "surface": {"auto_select_all": True},
        },
        "met": {
            "options": dict(FROZEN_MET_CONTROLS),
            "station_selection": {
                "isurft_mode": "spatial", "iupt_mode": "spatial", "iupwnd_mode": "spatial",
            },
        },
        "puff": {
            "options": dict(FROZEN_PUFF_CONTROLS),
            "point_sources": [{
                "name": "NEW_SITE_STACK",
                "latitude": center_lat, "longitude": center_lon,
                "stack_height_m": 70.8, "base_elev_m": 0.0,
                "stack_diameter_m": 1.6, "exit_velocity_mps": 17.26,
                "exit_temp_k": 298.15, "building_downwash_flag": 0.0,
                "zpltfm_m": 0.0, "fmfac": 1.0,
                "emissions": [833967.5291730086, 0.0],
            }],
        },
    }


def stage_case(verified_p5: Path, work_root: Path, scenario: str) -> tuple[Path, dict]:
    """Make a fresh physical copy of all original needed bytes outside repo.

    Selector metadata is intentionally NOT copied, forcing D2-A to reselect
    the true catalog and re-count original NOAA hourly coverage for the new
    case. This function itself does not run a model or call the network.
    """
    if scenario not in SCENARIOS:
        raise ValueError("unsupported P5 authentic NOAA scenario")
    if not work_root.is_absolute() or work_root.resolve().is_relative_to(ROOT):
        raise ValueError("independent scratch must be absolute and outside repository")
    begin, end, years = SCENARIOS[scenario]
    if work_root.is_symlink() or not work_root.is_dir():
        raise ValueError("P5 scratch root missing or symlinked")
    case_name = "issue56_huoshan_xinqiao_" + scenario
    case = work_root / case_name
    case.mkdir(exist_ok=False)
    src_grid = verified_p5 / "grid"
    grid = load_strict_utm_grid(src_grid / "grid.cmn", context="Issue56 authentic grid")
    center_lon, center_lat = parse_center(src_grid / "center_location")
    if not lon_lat_in_utm_grid(center_lon, center_lat, grid):
        raise ValueError("original S3-F center is not inside actual numeric UTM grid")
    geo = case / "grid"
    geo.mkdir()
    for name in ("grid.cmn", "center_location"):
        original = src_grid / name
        destination = geo / name
        if original.is_symlink() or not original.is_file():
            raise ValueError("S3-F grid is absent/symlinked")
        shutil.copyfile(original, destination)
        if digest(original) != digest(destination):
            raise ValueError("S3-F grid copy SHA mismatch")
    (geo / "research_time").write_text(
        "BEGIN:" + begin + "\nEND:" + end + "\n", encoding="utf-8"
    )
    config = _case_dict(case_name, grid, center_lat, center_lon, begin, end)
    (case / "case.yaml").write_text(
        yaml.safe_dump(config, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    admission = admit_case(case / "case.yaml")
    raw = case / "met/surface/isd_raw"
    lite_dir = raw / "isd_lite"
    lite_dir.mkdir(parents=True)
    hashes = {}
    source_raw = verified_p5 / "surface"
    for year in years:
        for sid in P5_STATIONS:
            for relative in (f"{sid}-{year}.csv", "isd_lite/" + lite_filename(sid, year)):
                original = source_raw / relative
                dest = raw / relative
                if original.is_symlink() or not original.is_file():
                    raise FileNotFoundError("real NOAA original missing/symlinked: " + str(original))
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(original, dest)
                if digest(dest) != digest(original):
                    raise ValueError("NOAA source bytes changed while staging: " + relative)
                hashes[relative] = digest(dest)
    verify_immutable(admission)
    assert not (case / "run/smerge").exists()
    assert not list(raw.glob("station_selection_*.json"))
    return case, {
        "case_name": case_name, "scenario": scenario,
        "raw_noaa_sha256": hashes, "year_scope": list(years),
        "case_yaml_sha256": admission.case_sha256,
        "grid_cmn_sha256": admission.grid_sha256,
        "research_time_sha256": admission.time_sha256,
        "selected_source_product": "genuine original NOAA full ISD + ISD-Lite",
    }


def _native_surf_preflight(reader: Path, case: Path, result: dict) -> dict:
    """Independent source reader only, not G19 or a P6 field."""
    if reader.is_symlink() or not reader.is_file():
        raise FileNotFoundError("independent C++ source preflight binary unavailable")
    expected_hours = result["SURF_hour_ending_expected_records"]
    order = result["ordered_ifstn"]
    input_surf = case / "run/smerge/surf.dat"
    command = [str(reader), str(input_surf), str(expected_hours), *order]
    proc = subprocess.run(command, capture_output=True, text=True, timeout=120)
    if proc.returncode or "PASS_P6G_REAL_NOAA_NATIVE_SURF_SOURCE_HOURLY" not in proc.stdout:
        raise RuntimeError("C++ independent SURF source reader rejected P5 native output: "
                           + proc.stdout[-500:] + proc.stderr[-500:])
    return {"source_reader": "PASS_SCOPED_INPUT_ONLY",
            "expected_hour_ending_records": expected_hours,
            "ordered_ifstn": order, "stdout_tail": proc.stdout[-700:]}


def run(native: Path, reader: Path, scenario: str) -> dict:
    for binary in (native, reader):
        if not binary.is_absolute() or binary.is_symlink() or not binary.is_file():
            raise FileNotFoundError("explicit native executable must be an absolute regular file")
    history = ROOT / "engine/resources/isd/isd-history.txt"
    template = ROOT / "engine/templates/smerge.inp"
    if not history.is_file() or not template.is_file():
        raise FileNotFoundError("official original history or SMERGE template missing")
    requested = list(SCENARIOS) if scenario == "all" else [scenario]
    with tempfile.TemporaryDirectory(prefix="cteas-issue56-real-noaa-") as td:
        independent = Path(td)
        source = independent / "verified"
        provenance = p5_check(source)
        if set(P5_STATIONS) != set(provenance["yearly"][0]["source_annual_counts"]):
            raise RuntimeError("S3-F did not verify both genuine original NOAA identities")
        results = []
        for selected in requested:
            case, staging = stage_case(source, independent, selected)
            producer = produce(case / "case.yaml", history, native, template,
                               offline_reselect=True)
            annual = producer["years"]
            if set(y["year"] for y in annual) != set(SCENARIOS[selected][2]):
                raise RuntimeError("P5 delivered selection year count mismatch")
            for year in annual:
                if {s["sid"] for s in year["stations"]} != set(P5_STATIONS):
                    raise RuntimeError("P5 real source selector changed expected station set")
                if year["mode"] != "OBSERVED":
                    raise RuntimeError("genuine in-domain station suddenly became virtual")
            read_result = _native_surf_preflight(reader, case, producer)
            results.append({
                **staging,
                "P5_GENERIC_CASE_EXECUTION": producer["P5_GENERIC_CASE_EXECUTION"],
                "P5_NATIVE_SURF": producer["P5_NATIVE_SURF"],
                "P5_ORIGINAL_PARITY": "NOT_RUN",
                "P5_TO_G19": "NOT_RUN",
                "raw_native_surf_sha256": producer["raw_native_surf_sha256"],
                "published_surf_sha256": producer["published_surf_sha256"],
                "ordered_ifstn": producer["ordered_ifstn"],
                "annual_primary": {str(y["year"]): y["primary_sid"] for y in annual},
                "sm_input_control_sha256":
                    producer["produced_output_sha256"]["run/smerge/smerge.inp"],
                "source_reader": read_result,
                "producer_step_exits": {s["stage"]: s["exit_code"]
                                       for s in producer["producer_steps"]},
                "science_acceptance": False,
            })
    return {
        "status": "ISSUE56_REAL_NOAA_STAGED_SURF_PRODUCED_UNVERIFIED",
        "case_scope": "real Huoshan/Luogang(Xinqiao) 2022/2023 only",
        "science_acceptance": False,
        "input_provenance": provenance,
        "scenarios": results,
        "P6_NUMERICAL": "NOT_RUN", "P7": "NOT_RUN",
        "ORIGINAL_SMERGE_PARITY": "NOT_RUN", "G19_JOINT": "NOT_RUN",
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Manual authentic NOAA P5 new-case native SURF replay")
    ap.add_argument("--native-p5-bin", required=True, type=Path)
    ap.add_argument("--native-surf-preflight-bin", required=True, type=Path)
    ap.add_argument("--scenario", choices=[*SCENARIOS, "all"], default="all")
    ap.add_argument("--evidence-out", required=True, type=Path)
    args = ap.parse_args(argv)
    try:
        result = run(args.native_p5_bin, args.native_surf_preflight_bin, args.scenario)
        target = args.evidence_out
        if target.is_symlink() or target.exists():
            raise ValueError("do not overwrite existing authentic-source evidence")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                          encoding="utf-8")
        print("ISSUE56_REAL_NOAA_STAGE=" + result["status"])
        return 0
    except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired) as exc:
        print("ISSUE56_REAL_NOAA_STAGE=BLOCKED reason=" + str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
