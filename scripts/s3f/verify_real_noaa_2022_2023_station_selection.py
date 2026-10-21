#!/usr/bin/env python3
"""S3-F: genuine NOAA two-station/two-year P4/P5 selector verification ONLY.

P4 observations are two unmodified, archived IGRA period-of-record files.
P5 observations are authoritative archived NOAA or live NOAA original ISD and
ISD-Lite bytes. Production selectors, ranking, annual selection, calendars and
metadata remain unchanged. P4 HTTP transport is replaced with local raw POR
lookup; P5 transport uses the real NOAA endpoint for missing originals.

NEVER runs, compiles or uses P6 CALMET or P7 CALPUFF.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
import shutil
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from engine.run_met.common import lon_lat_to_utm_km
from engine.run_met.station_grid import load_strict_utm_grid, lon_lat_in_utm_grid
from native_cpp.modules.p4_read62.data_prep import download_igra as p4
from native_cpp.modules.p5_smerge.data_prep import download_isd_by_grid as p5
from native_cpp.modules.p5_smerge.data_prep.isd_lite_wind import filename as lite_filename

HEFEI = ROOT / "project/cases/hefei5km_2022_reference_case_20261011"
SMOKE = ROOT / "project/cases/smoke5d_coldstart_20260701"
YEARS = (2022, 2023)
P4_STATIONS = ("CHM00058203", "CHM00058424")
P5_STATIONS = ("58314099999", "58321099999")


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda: f.read(1024 * 1024), b""):
            h.update(b)
    return h.hexdigest()


def generate_grid(folder: Path, positions: list[tuple[float, float]]) -> tuple[Path, Path, Path]:
    """Build independent *actual* WGS84 UTM domain, origin exactly 3 decimals km."""
    pts = [lon_lat_to_utm_km(lon, lat, 50, True) for lat, lon in positions]
    xref = math.floor((min(x for x, _ in pts) - 10.0) * 1000) / 1000
    yref = math.floor((min(y for _, y in pts) - 10.0) * 1000) / 1000
    dgrid = 1.0
    nx = math.ceil(max(x for x, _ in pts) - xref) + 10
    ny = math.ceil(max(y for _, y in pts) - yref) + 10
    assert all(xref < x < xref + nx * dgrid and yref < y < yref + ny * dgrid for x, y in pts)
    folder.mkdir(parents=True, exist_ok=True)
    geo = folder / "grid.cmn"
    fields = [
        "! IMAP = UTM !", "! IUTMZN = 50 !", "! LSOHEM = N !",
        "! DATUM = WGS-84 !", f"! XREFKM = {xref:.3f} !",
        f"! YREFKM = {yref:.3f} !", "! DGRIDKM = 1.0 !",
        f"! NX = {nx} !", f"! NY = {ny} !", "! NZ = 9 !",
    ] + [f"! ZFACE = {z} !" for z in (0, 20, 40, 80, 160, 320, 640, 1200, 2000, 3000)]
    geo.write_text("\n".join(fields) + "\n", encoding="utf-8")
    grid = load_strict_utm_grid(geo, context="S3-F")
    assert f"{grid.xrefkm:.3f}" == f"{xref:.3f}"
    assert f"{grid.yrefkm:.3f}" == f"{yref:.3f}"
    assert all(lon_lat_in_utm_grid(lon, lat, grid) for lat, lon in positions)
    center = folder / "center_location"
    latitude = sum(lat for lat, _ in positions) / len(positions)
    longitude = sum(lon for _, lon in positions) / len(positions)
    center.write_text(f"latitude: {latitude:.9f}\nlongitude: {longitude:.9f}\n", encoding="utf-8")
    research = folder / "research_time"
    research.write_text("BEGIN: 20220101-000000\nEND: 20231231-230000\n", encoding="utf-8")
    return geo, center, research


def p4_check(root: Path) -> dict:
    history = p4.load_station_list(ROOT / "engine/resources/igra/igra2-station-list.txt")
    ids = {s["id"]: s for s in history if s["id"] in P4_STATIONS}
    assert set(ids) == set(P4_STATIONS), ids
    grid_file, center, _ = generate_grid(root / "grid", [(s["lat"], s["lon"]) for s in ids.values()])
    grid = load_strict_utm_grid(grid_file)
    # Two authentic archived IGRA POR data streams, unmodified.
    raws = {
        "CHM00058203": SMOKE / "met/upperair/2023/CHM00058203-data.txt",
        "CHM00058424": HEFEI / "met/upperair/2022/CHM00058424-data.txt",
    }
    assert all(p.is_file() and p.stat().st_size > 10_000 for p in raws.values())
    for year in YEARS:
        inside, _ = p4.candidate_groups(history, ids[P4_STATIONS[0]]["lat"],
                                         ids[P4_STATIONS[0]]["lon"], grid, year)
        assert {s["id"] for s in inside} == set(P4_STATIONS), (year, [s["id"] for s in inside])

    def source_transport(sid, year_dir):
        assert sid in raws, f"Unexpected in-domain P4 station: {sid}"
        return raws[sid], True, None

    yearly = []
    for year in YEARS:
        with patch.object(p4, "DATA_ROOT", root / "upperair"), \
             patch.object(p4, "current_project_path", side_effect=lambda *p: (root / "grid").joinpath(*p[1:]) if p and p[0] == "grid" else root.joinpath(*p)), \
             patch.object(p4, "download_igra_data", side_effect=source_transport), \
             patch.object(sys, "argv", ["download_igra", "--year", str(year), "--pstop", "500"]):
            assert p4.main() == 0, f"P4 selection failure in {year}"
        report = json.loads((root / "upperair" / str(year) / "p4_station_selection_audit.json").read_text())
        listed = report["selected"]
        # Auditable multi-site evidence: raw QC, not merely a catalog entry.
        assert report["in_domain_candidates"] == 2 and len(listed) == 2, (year, report)
        assert {x["id"] for x in listed} == set(P4_STATIONS)
        assert all(x["site_type"] == "OBSERVED" and x["coverage"] > .80 for x in listed)
        assert all(x["effective_lat"] == x["source_lat"] and x["effective_lon"] == x["source_lon"] for x in listed)
        yearly.append({
            "year": year,
            "mode": "REAL_IN_DOMAIN_MULTIPLE",
            "original_slot_count": {x["id"]: x["valid_original_slots"] for x in listed},
            "raw_coverage": {x["id"]: x["coverage"] for x in listed},
            "chosen": sorted(x["id"] for x in listed),
        })
    return {"yearly": yearly, "raw_sha256": {sid: digest(f) for sid, f in raws.items()},
            "grid_origin_km": [f"{grid.xrefkm:.3f}", f"{grid.yrefkm:.3f}"],
            "catalog": "authentic IGRA station list, no candidate filtering",
            "transport": "offline authentic archived NOAA IGRA original POR bytes"}


def p5_check(root: Path) -> dict:
    history_file = ROOT / "engine/resources/isd/isd-history.txt"
    history = p5.parse_history_txt(history_file)
    ids = {s.sid: s for s in history if s.sid in P5_STATIONS}
    assert set(ids) == set(P5_STATIONS), ids
    grid_file, center, research = generate_grid(root / "grid", [(s.lat, s.lon) for s in ids.values()])
    grid = load_strict_utm_grid(grid_file)
    # Use entire authoritative catalog, not mock candidate lists.
    for year in YEARS:
        within = [s for s in history if p5.station_in_utm_grid(s, grid)
                  and p5.covers_interval(s.begin, s.end,
                                        __import__("datetime").datetime(year, 1, 1),
                                        __import__("datetime").datetime(year, 12, 31, 23))]
        assert {s.sid for s in within} == set(P5_STATIONS), (year, [s.sid for s in within])

    raw = root / "surface"
    raw.mkdir(parents=True, exist_ok=True)
    # Reuse authentic 2022/2023 LUOGANG raw CSV from existing cases when available.
    copies = {
        raw / "58321099999-2022.csv": HEFEI / "met/surface/isd_raw/58321099999-2022.csv",
        raw / "58321099999-2023.csv": SMOKE / "met/surface/isd_raw/58321099999-2023.csv",
        raw / "isd_lite" / lite_filename("58321099999", 2022):
            HEFEI / "met/surface/isd_raw/isd_lite" / lite_filename("58321099999", 2022),
    }
    for dst, src in copies.items():
        assert src.is_file() and src.stat().st_size > 0
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dst)

    positions = [(s.lat, s.lon) for s in ids.values()]
    stack_lat = sum(x for x, _ in positions) / len(positions)
    stack_lon = sum(y for _, y in positions) / len(positions)
    argv = [
        "download_isd_by_grid", "--center-file", str(center), "--grid-file", str(grid_file),
        "--research-time-file", str(research), "--history-file", str(history_file),
        "--out-dir", str(raw), "--stack-lat", f"{stack_lat:.9f}",
        "--stack-lon", f"{stack_lon:.9f}", "--timeout", "45", "--retries", "1",
    ]
    with patch.object(sys, "argv", argv):
        try:
            assert p5.main() == 0
        except SystemExit as exc:
            # The upstream selector writes the factual per-candidate source
            # decisions into short-lived scratch; preserve only bounded
            # failure reasons, never silently fill missing real NOAA hours.
            report = raw / "download_report_2022.json"
            if report.is_file():
                record = json.loads(report.read_text(encoding="utf-8"))
                reasons = [{
                    "sid": row["sid"],
                    "full": row.get("raw_annual_coverage"),
                    "lite": row.get("isd_lite_wind_original_hour_coverage"),
                    "full_success": row.get("full_isd_download_success"),
                    "lite_success": row.get("isd_lite_wind_download_success"),
                } for row in record.get("candidates", [])]
                raise RuntimeError(
                    "S4G_ACTUAL_NOAA_P5_REDOWNLOAD_BLOCKED " +
                    json.dumps(reasons, ensure_ascii=False, sort_keys=True)
                ) from exc
            raise
    yearly = []
    for year in YEARS:
        m = json.loads((raw / f"station_selection_{year}.json").read_text())
        report = json.loads((raw / f"download_report_{year}.json").read_text())
        assert m["station_selection_case"] == "IN_DOMAIN_MULTIPLE" and m["mode"] == "OBSERVED"
        assert len(m["stations"]) == 2 and {s["sid"] for s in m["stations"]} == set(P5_STATIONS)
        sorted_by_source = sorted(m["stations"], key=lambda s: (
            -s["isd_lite_raw_hours"], -s["full_isd_raw_hours"], s["sid"]))
        assert sorted_by_source[0]["sid"] == m["primary_sid"]
        assert sum(s["wind_treatment"] == "COMPLETE_FILL_AND_CALM_REPLACE" for s in m["stations"]) == 1
        assert all(not s["relocated"] and s["source_lat"] == s["lat"] and s["source_lon"] == s["lon"]
                   for s in m["stations"])
        assert all(s["isd_lite_raw_hours"] > 0 and s["full_isd_raw_hours"] > 0 for s in m["stations"])
        assert len(report["candidates"]) == 2
        yearly.append({
            "year": year, "primary_sid": m["primary_sid"],
            "source_annual_counts": {s["sid"]: {
                "full": s["full_isd_raw_hours"], "lite": s["isd_lite_raw_hours"],
                "expected": s["expected_hours"], "role": s["wind_treatment"],
                "ifstn": s["ifstn"],
            } for s in m["stations"]},
        })
    for sid in P5_STATIONS:
        aliases = {item["source_annual_counts"][sid]["ifstn"] for item in yearly}
        assert len(aliases) == 1, (sid, aliases)
    primary_changed = yearly[0]["primary_sid"] != yearly[1]["primary_sid"]
    raw_hashes = {}
    for year in YEARS:
        for sid in P5_STATIONS:
            for path in (raw / f"{sid}-{year}.csv", raw / "isd_lite" / lite_filename(sid, year)):
                assert path.is_file()
                raw_hashes[str(path.relative_to(raw))] = digest(path)
    return {
        "yearly": yearly, "primary_changed_naturally": primary_changed,
        "real_primary_switch": "PASS_OBSERVED" if primary_changed else "NO_REAL_SWITCH_OBSERVED",
        "raw_sha256": raw_hashes, "catalog": "original full NOAA ISD history, no filtering",
        "grid_origin_km": [f"{grid.xrefkm:.3f}", f"{grid.yrefkm:.3f}"],
        "transport": "real NOAA original hourly CSV and ISD-Lite (3 cached genuine source files)",
    }


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="cteas-s3f-genuine-noaa-") as td:
        root = Path(td)
        a = p4_check(root / "p4")
        b = p5_check(root / "p5")
    report = {
        "status": "PASS_REAL_NOAA_2_STATIONS_2_YEARS_SELECTION_ONLY",
        "scientific_scope": "two separate physically enclosing UTM grid footprints; NEVER Hefei frozen 5km",
        "calendar_years": YEARS, "P4": a, "P5": b,
        "numerical_physics": {"P6": "NOT_RUN", "P7": "NOT_RUN"},
        "no_main_case_geometry_changes": True,
    }
    output = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("s3f-real-noaa-selection.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("S3F_REAL_NOAA_MULTIYEAR_SELECTION_RESULT=" + report["status"])
    print("S3F_REAL_NOAA_PRIMARY_SWITCH=" + b["real_primary_switch"])
    print("S3F_EVIDENCE=" + str(output))


if __name__ == "__main__":
    main()
