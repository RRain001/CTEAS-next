#!/usr/bin/env python3
"""S3-E selection-only reproducibility: genuine archived observations, offline.

This deliberately bounds the NOAA candidate catalog to the archived source
station for source-backed eligibility. Multi-station/multi-year decisions are
tested separately with controlled/mock observations, NOT passed off as real.
Never invokes P6/P7 or uses network transport.
"""
from __future__ import annotations

import csv
import hashlib
import json
import re
import shutil
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

from engine.run_met.station_grid import load_strict_utm_grid, lon_lat_in_utm_grid
from native_cpp.modules.p4_read62.data_prep import download_igra as p4
from native_cpp.modules.p5_smerge.data_prep import download_isd_by_grid as p5
from native_cpp.modules.p5_smerge.data_prep import isd_lite_wind as lite

REPO = Path(__file__).resolve().parents[2]
CASE = REPO / "project/cases/hefei5km_2022_reference_case_20261011"
P4_ID = "CHM00058424"
P5_ID = "58321099999"


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for part in iter(lambda: f.read(1024 * 1024), b""):
            h.update(part)
    return h.hexdigest()


def run() -> dict:
    grid_file = CASE / "grid/grid.cmn"
    grid_text = grid_file.read_text()
    for field, value in (("XREFKM", "510.885"), ("YREFKM", "3531.269")):
        m = re.search(r"!\\s*" + field + r"\\s*=\\s*([0-9]+\\.[0-9]+)\\s*!", grid_text)
        assert m is not None and m.group(1) == value, (field, m.group(1) if m else None)
    grid = load_strict_utm_grid(grid_file, context="S3-E")
    assert grid.iutmzn == 50 and grid.lsohem == "N"
    center_lat, center_lon = p4.parse_center(CASE / "grid/center_location")
    source4 = CASE / "met/upperair/2022/CHM00058424-data.txt"
    source5full = CASE / "met/surface/isd_raw/58321099999-2022.csv"
    source5lite = CASE / "met/surface/isd_raw/isd_lite/583210-99999-2022.gz"
    assert all(p.is_file() for p in (source4, source5full, source5lite))

    # Read actual NOAA station catalogs, not fictitious station coordinates.
    igra_catalog = p4.load_station_list(REPO / "engine/resources/igra/igra2-station-list.txt")
    p4st = next(s for s in igra_catalog if s["id"] == P4_ID and s["first_year"] <= 2022 <= s["last_year"])
    isd_catalog = p5.parse_history_txt(REPO / "engine/resources/isd/isd-history.txt")
    p5st = next(s for s in isd_catalog if s.sid == P5_ID)
    assert not lon_lat_in_utm_grid(p4st["lon"], p4st["lat"], grid), "P4 selected source unexpectedly inside frozen 5km domain"
    assert not p5.station_in_utm_grid(p5st, grid), "P5 selected source unexpectedly inside frozen 5km domain"

    with tempfile.TemporaryDirectory(prefix="cteas-s3e-p4p5-only-") as td:
        temp = Path(td)
        p4out = temp / "p4"
        p5out = temp / "p5"
        def archived_p4_download(sid, out_dir):
            assert sid == P4_ID, sid
            return source4, True, None

        with patch.object(p4, "DATA_ROOT", p4out), \\
             patch.object(p4, "load_station_list", return_value=[p4st]), \\
             patch.object(p4, "download_igra_data", side_effect=archived_p4_download), \\
             patch.object(sys, "argv", ["download_igra", "--year", "2022", "--pstop", "500"]):
            assert p4.main() == 0

        p4audit = json.loads((p4out / "2022/p4_station_selection_audit.json").read_text())
        assert len(p4audit["selected"]) == 1
        row4 = p4audit["selected"][0]
        assert row4["id"] == P4_ID and row4["site_type"] == "VIRTUAL_RELOCATED"
        assert row4["valid_original_slots"] == 728 and p4audit["checked"][0]["expected_slots"] == 730
        assert row4["coverage"] > .80 and p4audit["in_domain_candidates"] == 0
        assert abs(row4["effective_lat"] - center_lat) < 1e-9
        assert abs(row4["effective_lon"] - center_lon) < 1e-9
        assert abs(row4["source_lat"] - p4st["lat"]) < 1e-6

        def archived_full(year, sid, out_dir, timeout):
            assert year == 2022 and sid == P5_ID
            out_dir.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source5full, out_dir / f"{sid}-{year}.csv")
            return True, "offline authentic archived full ISD", True

        def archived_lite(year, sid, out_dir, timeout):
            assert year == 2022 and sid == P5_ID
            out_dir.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source5lite, out_dir / lite.filename(sid, year))
            return True, "offline authentic archived ISD-Lite", True

        args = [
            "download_isd_by_grid", "--year", "2022",
            "--center-file", str(CASE / "grid/center_location"),
            "--grid-file", str(grid_file),
            "--research-time-file", str(CASE / "grid/research_time"),
            "--out-dir", str(p5out),
            "--stack-lat", str(center_lat), "--stack-lon", str(center_lon),
            "--retries", "1"
        ]
        with patch.object(p5, "parse_history_txt", return_value=[p5st]), \\
             patch.object(p5, "download_one", side_effect=archived_full), \\
             patch.object(lite, "download_lite_one", side_effect=archived_lite), \\
             patch.object(sys, "argv", args):
            assert p5.main() == 0
        report5 = json.loads((p5out / "download_report_2022.json").read_text())
        selected5 = json.loads((p5out / "station_selection_2022.json").read_text())
        assert report5["station_selection_case"] == "EXTERNAL_SINGLE_VIRTUAL"
        assert selected5["primary_sid"] == P5_ID
        assert len(selected5["stations"]) == 1
        st5 = selected5["stations"][0]
        assert st5["full_isd_raw_hours"] == st5["isd_lite_raw_hours"] == 8692
        assert st5["expected_hours"] == 8760
        assert st5["relocated"] and st5["wind_data_source"] == "NOAA_ISD_LITE"
        assert st5["wind_treatment"] == "COMPLETE_FILL_AND_CALM_REPLACE"
        assert st5["source_lat"] == p5st.lat and st5["source_lon"] == p5st.lon
        assert abs(st5["lat"] - center_lat) < 1e-8
        assert abs(st5["lon"] - center_lon) < 1e-8
        assert report5["candidates"][0]["strict_external_gt90_both_sources"]

    return {
        "status": "PASS_SOURCE_BACKED_SELECTED_STATION_ONLY",
        "case": "hefei5km_2022_reference_case_20261011",
        "source_type": "authentic NOAA archived observation bytes, authentic NOAA station catalogs",
        "transport": "offline copied cached source bytes (mocked transport ONLY)",
        "candidate_scope": "bounded to already archived P4 and P5 source identities; global discovery not accepted",
        "utm_origin_km": ["510.885", "3531.269"],
        "utm_precision_decimal_places": 3,
        "p4": {"sid": P4_ID, "original_valid_sounding_slots": 728, "expected": 730, "virtual": True,
               "sha256": digest(source4)},
        "p5": {"sid": P5_ID, "original_full_hours": 8692, "original_lite_hours": 8692, "expected": 8760,
               "virtual": True, "sha256_full": digest(source5full), "sha256_lite": digest(source5lite)},
        "not_accepted": ["full global NOAA station discovery", "real in-domain multi-station full observations",
                         "naturally observed multi-year primary switching", "P6", "P7", "G5"],
    }


if __name__ == "__main__":
    data = run()
    if len(sys.argv) > 1:
        output = Path(sys.argv[1])
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(data, indent=2) + "\\n", encoding="utf-8")
    print(json.dumps(data, indent=2))
