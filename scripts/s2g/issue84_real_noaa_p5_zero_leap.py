#!/usr/bin/env python3
"""Issue #84 real Wolsong zero-in-domain + observed 2024 leap-day P5 parity.

Manually dispatched only. Never reuses Hefei weather or synthetic observations.
All original-source bytes are temporary, SHA-pinned to source-screen Run
#39247024823. Reuses the existing #56 producer and independent comparison.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys
import tempfile

import yaml

from engine.run_met.station_grid import load_strict_utm_grid
from native_cpp.modules.p5_smerge.data_prep import download_isd_by_grid as full
from native_cpp.modules.p5_smerge.data_prep import isd_lite_wind as lite
from native_cpp.modules.p5_smerge.data_prep.p5_case_producer import produce
from native_cpp.modules.p5_smerge.data_prep.p5_handoff import build_p5_handoff
from scripts.s2g.issue84_noaa_source_screen import (
    WOLSONG, feb29_hours_full, make_frozen_grid, sha256,
)
from scripts.s2g.issue56_real_noaa_p5_case import (
    _case_dict, _native_surf_preflight, compare_original_smerge,
)

ROOT = Path(__file__).resolve().parents[2]
SID = "47152099999"
YEAR = 2024
# Frozen, independently retrieved original NOAA objects from #84 D0 manual
# Run #39247024823. Any NOAA revision is a blocker, not silently accepted.
EXPECTED_SHA = {
    "full_isd_csv": "9740198e2df44eb8d99ec49ee779f3d000bf5dfd49a2cc526a9600ea00e23eed",
    "isd_lite_gzip": "ed8ec2563d380fe72cc185f7ef7400cedc80963a69e6c31d0a03a64fd4b0bd04",
}
BEGIN = "20240228-000000"
END = "20240301-000000"
EXPECTED_SURF_HOURS = 48


def stage_real_case(scratch: Path) -> tuple[Path, dict]:
    """Stage one authentic NOAA station against #119's frozen UTM footprint."""
    case = scratch / "wolsong_2024_real_zero_virtual_leap"
    case.mkdir()
    grid_dir = case / "grid"
    grid_dir.mkdir()
    grid_file = grid_dir / "grid.cmn"
    make_frozen_grid(grid_file)
    grid = load_strict_utm_grid(grid_file, context="Issue84 original zero virtual leap")
    (grid_dir / "center_location").write_text(
        f"latitude: {WOLSONG['lat']:.9f}\nlongitude: {WOLSONG['lon']:.9f}\n",
        encoding="utf-8",
    )
    (grid_dir / "research_time").write_text(
        f"BEGIN: {BEGIN}\nEND: {END}\n", encoding="utf-8",
    )
    config = _case_dict(
        case.name, grid, WOLSONG["lat"], WOLSONG["lon"], BEGIN, END,
    )
    (case / "case.yaml").write_text(
        yaml.safe_dump(config, sort_keys=False, allow_unicode=True), encoding="utf-8",
    )

    history_path = ROOT / "engine/resources/isd/isd-history.txt"
    history = full.parse_history_txt(history_path)
    from datetime import datetime
    first, last = datetime(2024, 1, 1), datetime(2024, 12, 31, 23)
    annual_catalog = [
        s for s in history
        if full.covers_interval(s.begin, s.end, first, last)
    ]
    inside = [s.sid for s in annual_catalog if full.station_in_utm_grid(s, grid)]
    if inside:
        raise RuntimeError("Wolsong 2024 zero-in-domain gate failed: " + repr(inside))
    nearest = sorted(
        annual_catalog,
        key=lambda s: (full.haversine_km(
            WOLSONG["lat"], WOLSONG["lon"], s.lat, s.lon), s.sid),
    )
    if not nearest or nearest[0].sid != SID:
        raise RuntimeError("ULSAN no longer the nearest original NOAA full-year station")

    raw = case / "met/surface/isd_raw"
    raw.mkdir(parents=True)
    lite_dir = raw / "isd_lite"
    lite_dir.mkdir()
    ok_full, why_full, _ = full.download_one(YEAR, SID, raw, timeout=90)
    ok_lite, why_lite, _ = lite.download_lite_one(YEAR, SID, lite_dir, timeout=90)
    if not (ok_full and ok_lite):
        raise RuntimeError(f"original NOAA source unavailable: full={why_full}, lite={why_lite}")
    csv_path = raw / f"{SID}-{YEAR}.csv"
    gz_path = lite_dir / lite.filename(SID, YEAR)
    hashes = {"full_isd_csv": sha256(csv_path), "isd_lite_gzip": sha256(gz_path)}
    if hashes != EXPECTED_SHA:
        raise RuntimeError("real NOAA original SHA changed from D0: " + repr(hashes))
    full_hours, denominator = full.original_coverage(csv_path, YEAR, SID)
    lite_hours, lite_denominator = lite.lite_time_coverage(gz_path, YEAR, SID)
    leap_full = feb29_hours_full(csv_path, YEAR, SID)
    leap_lite = sum(
        instant.month == 2 and instant.day == 29
        for instant in lite.parse_lite_winds(gz_path, YEAR, SID)
    )
    if (denominator != 8784 or lite_denominator != 8784
            or full_hours != 8612 or lite_hours != 8612
            or leap_full != 24 or leap_lite != 24
            or full_hours / 8784 <= .90 or lite_hours / 8784 <= .90):
        raise RuntimeError(
            f"original source science gate failed: {full_hours}/{lite_hours} "
            f"of {denominator}/{lite_denominator}, leap={leap_full}/{leap_lite}"
        )
    return case, {
        "case_name": case.name,
        "real_site": WOLSONG, "original_source_station_sid": SID,
        "catalog_in_domain_count": len(inside),
        "actual_catalog_nearest_station_sid": nearest[0].sid,
        "source_distance_to_representative_km": round(full.haversine_km(
            WOLSONG["lat"], WOLSONG["lon"], nearest[0].lat, nearest[0].lon), 3),
        "source_urls": {
            "full_isd_csv": full.station_url(YEAR, SID),
            "isd_lite_gzip": lite.source_url(SID, YEAR),
        },
        "original_noaa_sha256": hashes, "isd_history_sha256": sha256(history_path),
        "grid_cmn_sha256": sha256(grid_file),
        "case_yaml_sha256": sha256(case / "case.yaml"),
        "research_time_sha256": sha256(grid_dir / "research_time"),
        "raw_calendar_denominator": denominator,
        "raw_original_full_hours": full_hours, "raw_original_lite_hours": lite_hours,
        "raw_feb29_full_hours": leap_full, "raw_feb29_lite_hours": leap_lite,
        "raw_sources_both_strict_gt90pct": True,
        "original_noaa_archives_redistributed": False,
    }


def run(native: Path, reader: Path, original: Path) -> dict:
    for path in (native, reader, original):
        if not path.is_absolute() or path.is_symlink() or not path.is_file():
            raise ValueError("all original/native/read binaries must be absolute regular files")
    with tempfile.TemporaryDirectory(prefix="cteas-issue84-real-2024-") as folder:
        scratch = Path(folder)
        case, source = stage_real_case(scratch)
        product = produce(
            case / "case.yaml",
            ROOT / "engine/resources/isd/isd-history.txt",
            native,
            ROOT / "engine/templates/smerge.inp",
            offline_reselect=True,
        )
        annual = product["years"]
        if len(annual) != 1 or annual[0]["year"] != YEAR:
            raise RuntimeError("producer did not reselect exact 2024 annual source")
        if (annual[0]["mode"] != "VIRTUAL_RELOCATED"
                or annual[0]["primary_sid"] != SID
                or len(annual[0]["stations"]) != 1
                or annual[0]["stations"][0]["sid"] != SID
                or not annual[0]["stations"][0]["relocated"]):
            raise RuntimeError("actual production P5 did not select one genuine virtual ULSAN station")
        if product["SURF_hour_ending_expected_records"] != EXPECTED_SURF_HOURS:
            raise RuntimeError("P5 (BEGIN,END] 2024 leap-hour count mismatch")
        read_result = _native_surf_preflight(reader, case, product)
        handoff = build_p5_handoff(case, product, read_result)
        parity = compare_original_smerge(original, case, product, scratch)
        if not parity["byte_identical"]:
            raise RuntimeError("original/native same-GENERIC RAW SURF differs")
        return {
            "status": "ISSUE84_REAL_2024_ZERO_VIRTUAL_LEAP_RAW_ORIGINAL_NATIVE_SCOPED_PARITY_PASS",
            "science_scope": (
                "Wolsong #119 fixed 20x20km UTM52N, 2024-02-28 00 UTC "
                "through 2024-03-01 00 UTC, true NOAA ULSAN single virtual "
                "station, JDAT8 IOFORM2 IOPACK0 LPREV-F LPCALC-F UTC only"
            ),
            "science_acceptance": "SCOPED_P5_RAW_SURF_ONLY",
            "source": source,
            "actual_producer_mode": annual[0]["mode"],
            "actual_producer_primary": annual[0]["primary_sid"],
            "ordered_ifstn": product["ordered_ifstn"],
            "original_vs_native": parity,
            "source_preflight": read_result,
            "handoff": handoff,
            "published_surf_sha256": product["published_surf_sha256"],
            "raw_native_surf_sha256": product["raw_native_surf_sha256"],
            "p5_to_g19": "NOT_RUN",
            "p6_numerical": "NOT_RUN", "p7": "NOT_RUN",
            "natural_primary_switch": "NOT_RUN",
            "real_one_or_three_in_domain": "NOT_RUN",
            "wet_deposition": "NOT_RUN",
        }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--native-p5-bin", required=True, type=Path)
    parser.add_argument("--native-surf-preflight-bin", required=True, type=Path)
    parser.add_argument("--original-smerge-bin", required=True, type=Path)
    parser.add_argument("--evidence-out", required=True, type=Path)
    args = parser.parse_args()
    try:
        result = run(
            args.native_p5_bin, args.native_surf_preflight_bin, args.original_smerge_bin,
        )
        if args.evidence_out.exists() or args.evidence_out.is_symlink():
            raise ValueError("real scientific evidence destination already exists")
        args.evidence_out.parent.mkdir(parents=True, exist_ok=True)
        args.evidence_out.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n",
                                     encoding="utf-8")
        print("ISSUE84_REAL_NOAA_ZERO_LEAP=" + result["status"])
        return 0
    except (ValueError, RuntimeError, OSError, subprocess.TimeoutExpired, KeyError) as exc:
        print("ISSUE84_REAL_NOAA_ZERO_LEAP=BLOCKED reason=" + str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
