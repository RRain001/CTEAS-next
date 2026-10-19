"""Issue #53 P2-B native D3: synthetic GSHHS Full L1 area split, override, SHA, missing.
Run with /usr/bin/python3 (python3-gdal from apt) after building cteas_p2_glc_lu_dat.
This is software verification ONLY; the fake GSHHS shapefile is NOT official GSHHG.
"""
from __future__ import annotations
import csv
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

try:
    from osgeo import gdal, ogr, osr
except ImportError:
    gdal = ogr = osr = None

ROOT = Path(__file__).resolve().parents[3]
POLICY = ROOT / "docs/plans/ISSUE53_GLC35_USGS38_USER_SELECTED_20261019.json"
REAL_TIFF = ROOT / "data/landcover/glc_fcs30d/v1_2022/hefei/hefei_2022_30m.tif"
BIN = os.environ.get("CTEAS_P2B_NATIVE_BIN")

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

@unittest.skipUnless(gdal is not None and BIN, "requires apt python3-gdal and CTEAS_P2B_NATIVE_BIN")
class NativeP2BGSHHSTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.tif = self.base / "glc_2022_30m.tif"
        driver = gdal.GetDriverByName("GTiff")
        ds = driver.Create(str(self.tif), 6, 6, 1, gdal.GDT_Byte)
        self.assertIsNotNone(ds)
        ds.SetGeoTransform([500000.0, 30.0, 0.0, 3500180.0, 0.0, -30.0])
        utm = osr.SpatialReference()
        utm.ImportFromEPSG(32650)
        ds.SetProjection(utm.ExportToWkt())
        a = bytearray([210] * 36)
        # Three non-water classes on the 100×100m model cell:
        # 183→77:900m², 184→77:900m², 190→16:900m².
        a[5 * 6 + 0] = 183
        a[4 * 6 + 1] = 184
        a[3 * 6 + 2] = 190
        import numpy as np
        ds.GetRasterBand(1).WriteArray(np.asarray(a, dtype="uint8").reshape(6, 6))
        ds.FlushCache()
        ds = None
        self.shp = self.base / "GSHHS_f_L1.shp"

    def shoreline(self, minx=499900.0, maxx=500050.0):
        # A synthetic polygon created in projected metres, then encoded as WGS84,
        # as in a real GSHHS Full L1 coastline; this does NOT invent real coastline.
        name = "GSHHS_f_L1"
        driver = ogr.GetDriverByName("ESRI Shapefile")
        ds = driver.CreateDataSource(str(self.shp))
        utm = osr.SpatialReference()
        utm.ImportFromEPSG(32650)
        utm.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
        geo = osr.SpatialReference()
        geo.ImportFromEPSG(4326)
        geo.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
        layer = ds.CreateLayer(name, geo, ogr.wkbPolygon)
        ring = ogr.Geometry(ogr.wkbLinearRing)
        for x, y in [(minx, 3499900), (maxx, 3499900),
                     (maxx, 3500200), (minx, 3500200), (minx, 3499900)]:
            ring.AddPoint_2D(x, y)
        polygon = ogr.Geometry(ogr.wkbPolygon)
        polygon.AddGeometry(ring)
        polygon.Transform(osr.CoordinateTransformation(utm, geo))
        feat = ogr.Feature(layer.GetLayerDefn())
        feat.SetGeometry(polygon)
        self.assertEqual(layer.CreateFeature(feat), 0)
        feat = None
        ds = None

    def call(self, *, bad_policy=None, bad_tif=None, expected_sha=None):
        p = bad_policy or POLICY
        t = bad_tif or self.tif
        out = self.base / ("result_" + str(len(list(self.base.glob("result_*")))))
        args = [BIN, str(t), expected_sha or sha(t), str(self.shp), sha(self.shp),
                str(p), sha(p), str(out), "32650", "500.000", "3500.000",
                "0.100", "1", "1"]
        run = subprocess.run(args, text=True, capture_output=True, check=False)
        return run, out

    def read_lu(self, path):
        lines = path.read_text().splitlines()
        self.assertEqual(len(lines), 12)
        self.assertEqual(lines[0].split()[:2], ["LU.DAT", "2.1"])
        self.assertEqual(lines[10].split(), [str(x) for x in [
            11,12,13,14,15,16,17,21,22,23,24,31,32,33,41,42,43,
            51,52,53,54,55,61,62,71,72,73,74,75,76,77,81,82,83,84,85,91,92]])
        fields = lines[11].split()
        self.assertEqual(fields[:2], ["1", "1"])
        self.assertEqual(fields[-1], ".")
        return [float(x) for x in fields[2:-1]]

    def test_crossing_coastline_35_to_38_exact_area(self):
        self.shoreline()
        run, out = self.call()
        self.assertEqual(run.returncode, 0, run.stderr)
        values = self.read_lu(out / "lu.dat")
        mapping = {id: values[k] for k, id in enumerate([
            11,12,13,14,15,16,17,21,22,23,24,31,32,33,41,42,43,
            51,52,53,54,55,61,62,71,72,73,74,75,76,77,81,82,83,84,85,91,92])}
        self.assertAlmostEqual(mapping[52], .350, places=3)
        self.assertAlmostEqual(mapping[55], .380, places=3)
        self.assertAlmostEqual(mapping[77], .180, places=3)
        self.assertAlmostEqual(mapping[16], .090, places=3)
        self.assertAlmostEqual(sum(values), 1., places=6)
        manifest = json.loads((out / "p2_b_d3_manifest.json").read_text())
        self.assertAlmostEqual(manifest["usgs52_inland_water_area_m2"], 3500., delta=.2)
        self.assertAlmostEqual(manifest["usgs55_ocean_water_area_m2"], 3800., delta=.2)
        self.assertEqual(manifest["evidence_status"], "PRODUCED_UNVERIFIED")
        self.assertEqual(manifest["original_makegeo_38_to_14_parity"], "NOT_RUN")
        self.assertEqual(manifest["gshhg_zip_sha256_verification"], "NOT_RUN_IN_THIS_CLI")

    def test_all_land_water_52(self):
        self.shoreline(499900., 500200.)
        run, out = self.call()
        self.assertEqual(run.returncode, 0, run.stderr)
        v = self.read_lu(out / "lu.dat")
        self.assertAlmostEqual(v[18], .730, places=3)  # USGS52 index 18
        self.assertAlmostEqual(v[21], 0., places=3)  # USGS55 index 21

    def test_all_sea_water_55(self):
        self.shoreline(499900., 499950.)
        run, out = self.call()
        self.assertEqual(run.returncode, 0, run.stderr)
        v = self.read_lu(out / "lu.dat")
        self.assertAlmostEqual(v[18], 0., places=3)
        self.assertAlmostEqual(v[21], .730, places=3)

    def test_reject_tiff_sha_and_policy_override(self):
        self.shoreline()
        run, out = self.call(expected_sha="0"*64)
        self.assertNotEqual(run.returncode, 0)
        self.assertFalse(out.exists())
        policy = json.loads(POLICY.read_text())
        for row in policy["fixed_classes"]:
            if row["glc_code"] == 183:
                row["usgs_code"] = 62
        bad = self.base / "bad_policy.json"
        bad.write_text(json.dumps(policy))
        run, _ = self.call(bad_policy=bad)
        self.assertNotEqual(run.returncode, 0)
        self.assertIn("P2B_POLICY_USER_OVERRIDE_DRIFT", run.stderr)

    def test_reject_missing_glc_instead_of_autofilling_sea(self):
        self.shoreline()
        ds = gdal.Open(str(self.tif), gdal.GA_Update)
        ds.GetRasterBand(1).WriteRaster(0, 5, 1, 1, b"\x00")
        ds = None
        run, _ = self.call()
        self.assertNotEqual(run.returncode, 0)
        self.assertIn("P2_GLC_NODATA_OR_MASKED_INTERSECTION", run.stderr)

if __name__ == "__main__":
    unittest.main()
