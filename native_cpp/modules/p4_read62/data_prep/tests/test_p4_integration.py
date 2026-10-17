"""Black-box P4 station-selection and fixed-width FSL regression, with mocked downloads."""
import calendar
import csv
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from engine.run_met.common import GridDef, lon_lat_to_utm_km

from native_cpp.modules.p4_read62.data_prep import download_igra as downloader
from native_cpp.modules.p4_read62.data_prep import parse_igra_to_csv as parser
from native_cpp.modules.p4_read62.data_prep import read as converter
from native_cpp.modules.p4_read62.data_prep.prepare_inputs import selected_years


def sample_station(sid, lat, lon, first=2020, last=2026):
    return dict(id=sid, name=sid, lat=lat, lon=lon, elev_m=62.0,
                first_year=first, last_year=last)


class SelectionIntegrationTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.stations = [
            sample_station("AAA00058424", 31.94, 117.14),
            sample_station("BBB00058238", 31.95, 117.15),
            sample_station("NEAR00058400", 31.94, 117.22),
            sample_station("FAR00058333", 31.94, 117.33),
        ]

    def select(self, year, counts, stations=None):
        stations = self.stations if stations is None else stations

        def scan(path, station_id, y, elevation_m, pstop):
            valid = counts.get((y, station_id), 0)
            exp = (366 if calendar.isleap(y) else 365) * 2
            return dict(valid_original_slots=valid, expected_slots=exp,
                        coverage=valid / exp, eligible=valid * 5 > exp * 4,
                        soundings_cleaned=valid, soundings_dropped=0)

        x, y = lon_lat_to_utm_km(117.14, 31.94, 50, True)
        grid = GridDef("UTM", 50, "N", "WGS-84", x-2.5, y-2.5, 50, 50, 0.1, 1, [0.0, 20.0])
        fake_raw = lambda sid, out: (self.root / (sid + "-data.txt"), False, None)
        with patch.object(downloader, "DATA_ROOT", self.root), \
             patch.object(downloader, "parse_center", return_value=(31.94, 117.14)), \
             patch.object(downloader, "load_strict_utm_grid", return_value=grid), \
             patch.object(downloader, "load_station_list", return_value=stations), \
             patch.object(downloader, "download_igra_data", side_effect=fake_raw), \
             patch.object(parser, "observed_year_coverage", side_effect=scan), \
             patch.object(sys, "argv", ["download_igra", "--year", str(year), "--pstop", "500"]):
            result = downloader.main()
        csv_path = self.root / str(year) / "upperair_station_used_list.txt"
        audit_path = self.root / str(year) / "p4_station_selection_audit.json"
        with csv_path.open(newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        return result, rows, json.loads(audit_path.read_text(encoding="utf-8"))

    def test_multiple_inside_keep_original_coordinates(self):
        rc, rows, audit = self.select(2022, {
            (2022, "AAA00058424"): 730, (2022, "BBB00058238"): 585,
            (2022, "NEAR00058400"): 730})
        self.assertEqual(rc, 0)
        self.assertEqual({x["id"] for x in rows}, {"AAA00058424", "BBB00058238"})
        self.assertTrue(all(x["site_type"] == "OBSERVED" for x in rows))
        self.assertTrue(all(x["lat"] == x["source_lat"] and x["lon"] == x["source_lon"] for x in rows))
        self.assertEqual(len(audit["selected"]), 2)
        self.assertEqual(audit["selection_geometry"], "STRICT_WGS84_UTM_GRID_CMN_SW_CORNER_CLOSED_EDGES")

    def test_none_inside_nearest_qualifying_single_proxy(self):
        rc, rows, audit = self.select(2022, {
            (2022, "AAA00058424"): 584, (2022, "BBB00058238"): 30,
            (2022, "NEAR00058400"): 584, (2022, "FAR00058333"): 600})
        self.assertEqual(rc, 0)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["id"], "FAR00058333")
        self.assertEqual(rows[0]["site_type"], "VIRTUAL_RELOCATED")
        self.assertEqual((float(rows[0]["lat"]), float(rows[0]["lon"])), (31.94, 117.14))
        self.assertNotEqual(rows[0]["lon"], rows[0]["source_lon"])
        self.assertEqual(rows[0]["elev_m"], "62.0")
        self.assertEqual(len(audit["checked"]), 4)

    def test_annual_reselection_not_first_year_locked(self):
        counts = {(2022, "AAA00058424"): 700, (2022, "BBB00058238"): 700,
                  (2023, "AAA00058424"): 100, (2023, "BBB00058238"): 700}
        _, rows2022, _ = self.select(2022, counts)
        _, rows2023, _ = self.select(2023, counts)
        self.assertEqual({r["id"] for r in rows2022}, {"AAA00058424", "BBB00058238"})
        self.assertEqual([r["id"] for r in rows2023], ["BBB00058238"])

    def test_no_qualifying_station_explicit_failure(self):
        rc, rows, audit = self.select(2022, {})
        self.assertEqual(rc, 2)
        self.assertEqual(rows, [])
        self.assertTrue(all(s["status"] == "REJECTED_COVERAGE_NOT_GT80" for s in audit["checked"]))


class FslAndProfileRegressions(unittest.TestCase):
    def test_fixed_width_longitude_limits_precision(self):
        for digits in (3, 4, 5, 6):
            # F6.2 plus a1 hemisphere cannot accept longitude 117.1416 with >2 decimals.
            self.assertGreater(len(f"{117.141610855:.{digits}f}"), 6)
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            profile = base / "58424_2022010100.csv"
            profile.write_text(
                "pressure_hPa,geopotential height_m,temperature_C,dew point temperature_C,wind direction_degree,wind speed_m/s\n"
                "1000,62,20,15,350,5\n"
                "500,5200,-25,-30,10,10\n", encoding="utf-8")
            output = base / "58424.txt"
            stats = converter.convert_csv_profiles_to_fsl(
                base, output, "58424", "31.94N", "117.14E", "62", "2022", 500.0
            )
            self.assertEqual(stats["processed_profiles"], 1)
            header = output.read_text(encoding="utf-8").splitlines()[1]
            self.assertEqual(header[21:28].strip(), "31.94")
            self.assertEqual(header[28], "N")
            self.assertEqual(header[29:35].strip(), "117.14")
            self.assertEqual(header[35], "E")

    def test_existing_00_12_slot_cloning_unchanged(self):
        with tempfile.TemporaryDirectory() as td:
            folder = Path(td)
            original = folder / "58424_2022010112.csv"
            original.write_text("wind\n123\n", encoding="utf-8")
            summary = parser.ensure_year_completeness(folder, "58424", 2022)
            generated = folder / "58424_2022010100.csv"
            self.assertEqual(generated.read_text(), original.read_text())
            self.assertTrue(summary["filled_same_day"] >= 1)


if __name__ == "__main__":
    unittest.main()
