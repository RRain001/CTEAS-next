#!/usr/bin/env python3
"""S2-G1B-B1: genuine archived NOAA Anqing -> native READ62 -> original UP.DAT.

Runs exactly one six-hour non-Hefei 2023 P4 input-only acceptance in an
isolated temporary scratch case, without modifying any repository case
selection, project/current, site GEO/SURF, P6 meteorology or P7 concentrations.

Transport supplies UNMODIFIED NOAA period-of-record bytes already retained in
the archived reference case. It is not a mocked NOAA observation or invented
soundings. The unchanged source P4 annual selector, CSV cleaner and FSL
writer run on this original raw file. The actual C++ P4 writer produces the
UP.DAT, which the original copied normalizer formats, and independent
C++ P6 read_upper_dynamic checks exact every-hour AA/BB brackets.

This proves ONLY real P4 UP input science/preflight, not complete G19 or P6.
"""
from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import math
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from engine.run_met.station_grid import load_strict_utm_grid
from native_cpp.modules.p4_read62.data_prep import download_igra as p4
from native_cpp.modules.p4_read62.data_prep import parse_igra_to_csv as parser
from native_cpp.modules.p4_read62.data_prep import read as fsl_converter
from native_cpp.modules.p4_read62.data_prep import run_cpp_pipeline as driver
from native_cpp.modules.p4_read62.data_prep import merge_final_upperair as normalizer
from native_cpp.modules.p5_smerge.data_prep import download_isd_by_grid as p5
from scripts.s3f.verify_real_noaa_2022_2023_station_selection import (
    HEFEI, P5_STATIONS, generate_grid, digest
)

ROOT = Path(__file__).resolve().parents[2]
ORIGINAL_NOAA = HEFEI / "met/upperair/2022/CHM00058424-data.txt"
ORIGINAL_STATION = "CHM00058424"
WMO = "58424"
YEARS = {2022: 728, 2023: 730}
MODEL_HOURS = 6
# Explicit genuine before/after 00/12 UTC soundings, never duplicate,
# extrapolate or silently manufacture a missing original sounding.


def require_binary(path: Path) -> Path:
    if path.is_symlink() or not path.is_file():
        raise ValueError("explicit native binary missing or symlink")
    return path.absolute()


def _invoke_main(main, argv: list[str]) -> None:
    with patch.object(sys, "argv", argv):
        result = main()
        if result not in (0, None):
            raise RuntimeError(f"P4 source algorithm declined: {argv[0]} ({result})")


def _timestamp(value: datetime) -> str:
    return value.strftime("%Y-%m-%dT%H:00Z")


def run(native_p4: Path, native_up_reader: Path, year: int) -> dict:
    if year not in YEARS:
        raise ValueError("only separately source-backed NOAA 2022/2023 years accepted")
    model_start = datetime(year, 6, 1, 1, tzinfo=timezone.utc)
    up_start = datetime(year, 6, 1, 0, tzinfo=timezone.utc)
    up_end = datetime(year, 6, 2, 12, tzinfo=timezone.utc)
    p4bin = require_binary(native_p4)
    checker = require_binary(native_up_reader)
    if not ORIGINAL_NOAA.is_file() or ORIGINAL_NOAA.stat().st_size < 20_000_000:
        raise FileNotFoundError("archived genuine original NOAA IGRA Anqing POR missing")
    sha_original = digest(ORIGINAL_NOAA)

    history = p5.parse_history_txt(ROOT / "engine/resources/isd/isd-history.txt")
    ground = {s.sid: s for s in history if s.sid in P5_STATIONS}
    if set(ground) != set(P5_STATIONS):
        raise ValueError("P5 authentic NOAA catalog lacks one selected ground station")
    positions = [(s.lat, s.lon) for s in ground.values()]

    with tempfile.TemporaryDirectory(prefix="s2g-g1bb-authentic-igra-p4-") as td:
        scratch = Path(td)
        case = scratch / f"independent_huoshan_xinqiao_noaa_{year}"
        grid_path, center_path, _ = generate_grid(case / "grid", positions)
        grid = load_strict_utm_grid(grid_path, context="S2-G1B-B1")
        center_text = center_path.read_text()
        lat = float(re.search(r"latitude:\s*([-\d.]+)", center_text).group(1))
        lon = float(re.search(r"longitude:\s*([-\d.]+)", center_text).group(1))
        catalog = p4.load_station_list(
            ROOT / "engine/resources/igra/igra2-station-list.txt")
        inside, outside = p4.candidate_groups(catalog, lat, lon, grid, year)
        if inside or not outside or outside[0]["id"] != ORIGINAL_STATION:
            raise RuntimeError("non-Hefei domain does not select original external Anqing")
        upper_root = case / "met/upperair"
        upper_root.mkdir(parents=True)

        def original_noaa_transport(sid: str, _out: Path):
            if sid != ORIGINAL_STATION:
                raise RuntimeError("unexpected source: refuse substitute NOAA station")
            return ORIGINAL_NOAA, True, None

        def case_path(*parts: str) -> Path:
            return case.joinpath(*parts)

        # The official current-case global is NEVER touched. Bind actual
        # producer globals only in this Python process to isolated scratch.
        with contextlib.ExitStack() as stack:
            for module, name, value in (
                (p4, "DATA_ROOT", upper_root),
                (p4, "current_project_path", case_path),
                (p4, "download_igra_data", original_noaa_transport),
                (parser, "DATA_ROOT", upper_root),
                (fsl_converter, "DATA_ROOT", upper_root),
                (driver, "current_project_path", case_path),
            ):
                stack.enter_context(patch.object(module, name, value))
            _invoke_main(p4.main, ["download_igra", "--year", str(year),
                                    "--pstop", "500", "--yes"])
            audit_path = upper_root / str(year) / "p4_station_selection_audit.json"
            audit = json.loads(audit_path.read_text(encoding="utf-8"))
            stations = audit.get("selected", [])
            if len(stations) != 1:
                raise RuntimeError("real P4 input expected exactly one selected external station")
            st = stations[0]
            if (st.get("id") != ORIGINAL_STATION or
                    st.get("site_type") != "VIRTUAL_RELOCATED" or
                    st.get("valid_original_slots") != YEARS[year] or
                    st.get("coverage", 0) <= .80):
                raise RuntimeError("Anqing original annual coverage/identity deviated")
            if (not math.isclose(st["effective_lat"], lat, abs_tol=1e-7) or
                    not math.isclose(st["effective_lon"], lon, abs_tol=1e-7)):
                raise RuntimeError("relocated source not at new site effective position")
            _invoke_main(parser.main, ["parse_igra_to_csv", "--year", str(year),
                                       "--pstop", "500", "--yes"])
            _invoke_main(fsl_converter.main, ["read", "--year", str(year)])
            jobs = driver.station_jobs(
                year, 500., p4bin, up_start.replace(tzinfo=None),
                up_end.replace(tzinfo=None))
            if len(jobs) != 1 or jobs[0]["station_id"] != WMO:
                raise RuntimeError("original 2023 IGRA-to-native-READ62 station job wrong")
            job = jobs[0]
            fsl = Path(job["input_fsl"])
            raw_native = Path(job["output_updat"])
            if not fsl.is_file() or fsl.stat().st_size < 1024:
                raise RuntimeError("real NOAA FSL preparation returned no source records")
            raw_native.parent.mkdir(parents=True, exist_ok=True)
            result = subprocess.run(job["command"], check=False,
                                    capture_output=True, text=True, timeout=120)
            if result.returncode != 0 or "P4_CPP_UPDAT_OK" not in result.stdout:
                raise RuntimeError("native READ62 failed: " + result.stderr[-1800:])
            # The retained original normalizer removes original warning
            # lines and truncates max level count WITHOUT synthesizing any
            # new 00/12 sounding or running any original Fortran program.
            source_lines = raw_native.read_text(encoding="utf-8").splitlines()
            normalized, clipped = normalizer.normalize_updat_records(
                source_lines, WMO, raw_native)
            calmet_up = scratch / f"up_real_anqing_{year}.dat"
            calmet_up.write_text("\n".join(normalized) + "\n", encoding="utf-8")
            actual_raw_sha = digest(ORIGINAL_NOAA)
            if actual_raw_sha != sha_original:
                raise RuntimeError("original retained NOAA POR changed during production")

            first_end = model_start + timedelta(hours=1)
            last_end = model_start + timedelta(hours=MODEL_HOURS)
            verify = subprocess.run([
                str(checker), str(calmet_up), WMO,
                str(int(first_end.timestamp())), str(int(last_end.timestamp()))
            ], check=False, text=True, capture_output=True, timeout=90)
            if verify.returncode != 0 or (
                    "PASS_P6G_REAL_NOAA_UP_SOURCE_TIME_BRACKETS" not in verify.stdout):
                raise RuntimeError("native G19 UP reader rejected original NOAA bytes: "
                                   + verify.stderr[-1800:])
            if f"WMO={WMO}" not in verify.stdout or f"HOURS={MODEL_HOURS}" not in verify.stdout:
                raise RuntimeError("native original UP reader proof identity/clock mismatch")


            # Two independent fail-closed checks on the SAME genuine file:
            # wrong declared source WMO and a later simulation hour with
            # no real next sounding MUST fail without fabricating records.
            bad_station = subprocess.run([
                str(checker), str(calmet_up), "58425",
                str(int(first_end.timestamp())), str(int(last_end.timestamp()))
            ], check=False, text=True, capture_output=True, timeout=90)
            if bad_station.returncode == 0 or "BLOCKED_P6G_NOAA_UP_SOURCE_PREFLIGHT" not in bad_station.stderr:
                raise RuntimeError("P6 original UP source falsely accepted wrong WMO identity")
            impossible_last = up_end + timedelta(hours=18)
            bad_bracket = subprocess.run([
                str(checker), str(calmet_up), WMO,
                str(int(first_end.timestamp())), str(int(impossible_last.timestamp()))
            ], check=False, text=True, capture_output=True, timeout=90)
            if bad_bracket.returncode == 0 or "BLOCKED_P6G_NOAA_UP_SOURCE_PREFLIGHT" not in bad_bracket.stderr:
                raise RuntimeError("P6 UP parser fabricated future 00/12 source sounding")

            return {
                "status": "G1BB1_REAL_NOAA_ANQING_NATIVE_P4_UP_SOURCE_PASS_SCOPED",
                "case": "non-Hefei Huoshan/Xinqiao-centred WGS84 UTM50N",
                "grid_cmn_sha256": digest(grid_path),
                "grid_origin_km": [f"{grid.xrefkm:.3f}", f"{grid.yrefkm:.3f}"],
                "source_provenance": "unaltered archived authentic NOAA IGRA POR",
                "source_station": ORIGINAL_STATION, "wmo": WMO,
                "source_lat": st["source_lat"], "source_lon": st["source_lon"],
                "effective_lat": st["effective_lat"], "effective_lon": st["effective_lon"],
                "calendar_year": year, "original_valid_slots": st["valid_original_slots"],
                "original_expected_slots": 730,
                "selected_audit_sha256": digest(audit_path),
                "original_noaa_por_sha256": sha_original,
                "original_noaa_por_bytes": ORIGINAL_NOAA.stat().st_size,
                "original_fsl_sha256": digest(fsl),
                "native_read62_executable_sha256": digest(p4bin),
                "native_up_preflight_executable_sha256": digest(checker),
                "native_raw_up_sha256": digest(raw_native),
                "normalized_up_sha256": digest(calmet_up),
                "normalizer_clipped_99level_soundings": clipped,
                "model_first_hour": _timestamp(model_start),
                "model_hours_checked": MODEL_HOURS,
                "writer_start": _timestamp(up_start),
                "writer_end": _timestamp(up_end),
                "native_P4_output": result.stdout[-1200:],
                "independent_P6_up_source_parser": verify.stdout[-1200:],
                "negative_wrong_wmo": "BLOCKED_AS_EXPECTED",
                "negative_missing_future_bracket": "BLOCKED_AS_EXPECTED",
                "P3_GEO": "NOT_PRODUCED",
                "P5_SURF": "NOT_PRODUCED",
                "G19_FULL_SOURCE": "BLOCKED_NO_NEW_SITE_GEO_SURF",
                "P6D_P6E_P6F": "NOT_RUN",
                "P7": "NOT_RUN",
                "G5": "NOT_RUN",
                "full_site_science_accepted": False,
            }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Actual original NOAA native P4 UP.DAT short input-only test")
    p.add_argument("--year", type=int, required=True, choices=sorted(YEARS))
    p.add_argument("--native-p4-bin", required=True, type=Path)
    p.add_argument("--native-up-preflight-bin", required=True, type=Path)
    p.add_argument("--evidence-out", required=True, type=Path)
    a = p.parse_args(argv)
    try:
        report = run(a.native_p4_bin, a.native_up_preflight_bin, a.year)
        if a.evidence_out.is_symlink():
            raise ValueError("evidence output symlink prohibited")
        a.evidence_out.parent.mkdir(parents=True, exist_ok=True)
        a.evidence_out.write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8")
        print("S2G_G1BB1=" + report["status"])
        print("P3=NOT_PRODUCED P5=NOT_PRODUCED G19_FULL_SOURCE=BLOCKED")
        print("P6_PHYSICS=NOT_RUN P7=NOT_RUN")
        return 0
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as exc:
        print(json.dumps({
            "status": "BLOCKED_REAL_NOAA_NATIVE_P4_UP_SOURCE",
            "error": str(exc), "P6_PHYSICS": "NOT_RUN", "P7": "NOT_RUN",
        }, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
