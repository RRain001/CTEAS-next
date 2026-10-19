"""#84 offline software contracts only: no NOAA network and no science PASS."""
from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest

from engine.run_met.station_grid import load_strict_utm_grid, lon_lat_in_utm_grid
from native_cpp.modules.p5_smerge.data_prep.download_isd_by_grid import expected_hours_in_year
from scripts.s2g.issue84_noaa_source_screen import WOLSONG, eligible_years, make_frozen_grid


class Issue84NoaaSourceScreenOffline(unittest.TestCase):
    def test_2024_leap_year_denominator(self) -> None:
        self.assertEqual(expected_hours_in_year(2023), 8760)
        self.assertEqual(expected_hours_in_year(2024), 8784)

    def test_new_2024_station_not_dropped_by_union_history(self) -> None:
        station = SimpleNamespace(begin="20240101", end="20261231")
        self.assertEqual(eligible_years(station, [2023, 2024]), [2024])
        station_old = SimpleNamespace(begin="20210101", end="20231231")
        self.assertEqual(eligible_years(station_old, [2023, 2024]), [2023])

    def test_frozen_wolsong_three_decimal_utm_origin(self) -> None:
        with TemporaryDirectory() as scratch:
            grid_path = Path(scratch) / "grid.cmn"
            make_frozen_grid(grid_path)
            text = grid_path.read_text(encoding="utf-8")
            self.assertIn("XREFKM = 533.215", text)
            self.assertIn("YREFKM = 3942.629", text)
            grid = load_strict_utm_grid(grid_path, context="issue84 offline grid")
            self.assertEqual(grid.nx, 200)
            self.assertEqual(grid.ny, 200)
            self.assertTrue(lon_lat_in_utm_grid(WOLSONG["lon"], WOLSONG["lat"], grid))


if __name__ == "__main__":
    unittest.main()
