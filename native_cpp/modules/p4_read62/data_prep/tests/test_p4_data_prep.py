"""Scoped P4 selection and circular wind interpolation tests; no network access."""
import unittest
from dataclasses import replace
from types import SimpleNamespace
from engine.run_met.common import GridDef, lon_lat_to_utm_km
from engine.run_met.station_grid import contains_projected_utm_km, lon_lat_in_utm_grid
from native_cpp.modules.p5_smerge.data_prep.download_isd_by_grid import station_in_utm_grid
from native_cpp.modules.p4_read62.data_prep import download_igra as station
from native_cpp.modules.p4_read62.data_prep import parse_igra_to_csv as parse
from native_cpp.modules.p4_read62.data_prep import read as fsl

class P4ScopedTest(unittest.TestCase):
    def test_wind_direction(self):
        for module in (parse, fsl):
            f = module._interp_wind_direction
            for a,b,expected in ((350,10,0),(10,350,0),(10,190,100),(190,10,280)):
                self.assertAlmostEqual(f(a,b,0.5),expected)
            self.assertIsNone(f(None,10,0.5))
        levels = [
            {'pressure_hPa':600,'geopotential height_m':1000,'wind direction_degree':350},
            {'pressure_hPa':400,'geopotential height_m':2000,'wind direction_degree':10}]
        profiles = parse._ensure_target_pressure_level(levels,500)
        target = [r for r in profiles if r['pressure_hPa']==500]
        self.assertEqual(len(target),1)
        self.assertEqual(target[0]['wind direction_degree'],0)

    def test_coverage_strict(self):
        self.assertFalse(station.coverage_passes(584,730))
        self.assertTrue(station.coverage_passes(585,730))
        self.assertFalse(station.coverage_passes(585,732))
        self.assertTrue(station.coverage_passes(586,732))

    @staticmethod
    def hefei_grid():
        x, y = lon_lat_to_utm_km(117.14, 31.94, 50, True)
        return GridDef(
            imap="UTM", iutmzn=50, lsohem="N", datum="WGS-84",
            xrefkm=x-2.5, yrefkm=y-2.5, nx=50, ny=50,
            dgridkm=0.1, nz=1, zfaces=[0.0, 20.0])

    def test_inside_outside_and_yearly_reselection(self):
        stations = [
            dict(id="A", lat=31.94, lon=117.14, first_year=2021, last_year=2024),
            dict(id="B", lat=31.95, lon=117.15, first_year=2022, last_year=2024),
            dict(id="NEAR", lat=31.94, lon=117.22, first_year=2021, last_year=2024),
            dict(id="FAR", lat=31.94, lon=117.35, first_year=2021, last_year=2024),
            dict(id="EXPIRED", lat=31.94, lon=117.14, first_year=2021, last_year=2021)]
        grid = self.hefei_grid()
        inside, outside = station.candidate_groups(stations, 31.94, 117.14, grid, 2022)
        self.assertEqual({x["id"] for x in inside}, {"A", "B"})
        self.assertEqual([x["id"] for x in outside], ["NEAR", "FAR"])
        self.assertEqual({x["id"] for x in station.candidate_groups(
            stations, 31.94, 117.14, grid, 2021)[0]}, {"A", "EXPIRED"})
        self.assertEqual({x["id"] for x in station.candidate_groups(
            stations, 31.94, 117.14, grid, 2023)[0]}, {"A", "B"})

    def test_p4_p5_share_exact_closed_utm_bounds(self):
        grid = self.hefei_grid()
        for x in (grid.xrefkm, grid.xrefkm+grid.nx*grid.dgridkm):
            for y in (grid.yrefkm, grid.yrefkm+grid.ny*grid.dgridkm):
                self.assertTrue(contains_projected_utm_km(x, y, grid))
        self.assertFalse(contains_projected_utm_km(grid.xrefkm-1e-6, grid.yrefkm, grid))
        self.assertFalse(contains_projected_utm_km(float("nan"), grid.yrefkm, grid))
        points = [(117.14, 31.94), (117.22, 31.94), (117.15, 31.95),
                  (117.14, 85.0), (117.14, -81.0)]
        for lon, lat in points:
            self.assertEqual(
                lon_lat_in_utm_grid(lon, lat, grid),
                station_in_utm_grid(SimpleNamespace(lon=lon, lat=lat), grid))
        shifted = replace(grid, xrefkm=grid.xrefkm+20)
        self.assertTrue(lon_lat_in_utm_grid(117.14, 31.94, grid))
        self.assertFalse(lon_lat_in_utm_grid(117.14, 31.94, shifted))

if __name__ == '__main__':
    unittest.main()
