"""Issue #84 genuine Wolsong/ULSAN 2024 replay entrypoint contracts, offline only."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from engine.run_met.station_grid import load_strict_utm_grid
from native_cpp.modules.p5_smerge.data_prep import download_isd_by_grid as full
from scripts.s2g.issue84_noaa_source_screen import WOLSONG, make_frozen_grid
from scripts.s2g.issue84_real_noaa_p5_zero_leap import (
    BEGIN, END, EXPECTED_SHA, EXPECTED_SURF_HOURS, SID,
)

ROOT = Path(__file__).resolve().parents[3]


class Issue84RealZeroLeapOffline(unittest.TestCase):
    def test_authentic_original_hash_declarations(self) -> None:
        self.assertEqual(set(EXPECTED_SHA), {"full_isd_csv", "isd_lite_gzip"})
        self.assertTrue(all(len(value) == 64 and
                            all(c in "0123456789abcdef" for c in value)
                            for value in EXPECTED_SHA.values()))

    def test_2024_calendar_and_hour_ending(self) -> None:
        self.assertEqual(full.expected_hours_in_year(2024), 8784)
        begin = datetime.strptime(BEGIN, "%Y%m%d-%H%M%S")
        end = datetime.strptime(END, "%Y%m%d-%H%M%S")
        self.assertEqual((end - begin).total_seconds() / 3600,
                         EXPECTED_SURF_HOURS)
        self.assertLess(begin, datetime(2024, 2, 29))
        self.assertGreater(end, datetime(2024, 2, 29, 23))

    def test_real_catalog_zero_and_nearest_offdomain_station(self) -> None:
        with TemporaryDirectory() as td:
            grid_path = Path(td) / "grid.cmn"
            make_frozen_grid(grid_path)
            grid = load_strict_utm_grid(grid_path, context="Issue84 Wolsong test")
            history = full.parse_history_txt(
                ROOT / "engine/resources/isd/isd-history.txt"
            )
            first, last = datetime(2024, 1, 1), datetime(2024, 12, 31, 23)
            candidates = [
                station for station in history if full.covers_interval(
                    station.begin, station.end, first, last
                )
            ]
            self.assertEqual([
                station.sid for station in candidates
                if full.station_in_utm_grid(station, grid)
            ], [])
            nearest = min(candidates, key=lambda station: (
                full.haversine_km(WOLSONG["lat"], WOLSONG["lon"],
                                  station.lat, station.lon),
                station.sid,
            ))
            self.assertEqual(nearest.sid, SID)


if __name__ == "__main__":
    unittest.main()
