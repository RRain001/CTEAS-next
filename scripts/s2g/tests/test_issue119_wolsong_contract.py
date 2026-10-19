"""Issue #119 Wolsong: offline tests only; never use authentic coast/data as synthetic evidence."""
from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

import numpy as np
import rasterio
from rasterio.transform import from_origin
from pyproj import Transformer
from scripts.s2g import p2b_wolsong_case as site

ROOT = Path(__file__).resolve().parents[3]

def fake_tif(target: Path, value=210):
    # 20km / 30m is non-integral. Include true partially intersecting border pixels.
    transform = from_origin(site.X0-45.,site.Y0+site.NY*site.STEP+45.,30.,30.)
    with rasterio.open(target,"w",driver="GTiff",height=672,width=672,
                       count=1,dtype="uint8",crs=f"EPSG:{site.EPSG}",
                       transform=transform,nodata=0) as ds:
        ds.write(np.full((672,672),value,dtype="uint8"),1)

def fake_shore(path: Path, xmax: float):
    from osgeo import ogr,osr
    wgs = osr.SpatialReference()
    wgs.ImportFromEPSG(4326)
    wgs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    ds = ogr.GetDriverByName("ESRI Shapefile").CreateDataSource(str(path))
    layer = ds.CreateLayer("GSHHS_f_L1",wgs,ogr.wkbPolygon)
    projected_to_geo = Transformer.from_crs(site.EPSG,4326,always_xy=True)
    x0,y0,x1,y1 = site.GRID
    coords = [(x0-1000.,y0-1000.),(xmax,y0-1000.),(xmax,y1+1000.),
              (x0-1000.,y1+1000.),(x0-1000.,y0-1000.)]
    ring = ogr.Geometry(ogr.wkbLinearRing)
    for x,y in coords:
        lon,lat = projected_to_geo.transform(x,y)
        ring.AddPoint(lon,lat)
    poly = ogr.Geometry(ogr.wkbPolygon)
    poly.AddGeometry(ring)
    f = ogr.Feature(layer.GetLayerDefn())
    f.SetGeometry(poly)
    layer.CreateFeature(f)
    f = layer = ds = None

class TestWolsongSource(unittest.TestCase):
    def test_geometry_and_stack_location_is_only_representative(self):
        self.assertEqual((site.EPSG,site.NX,site.NY,site.STEP), (32652,200,200,100.))
        self.assertEqual((site.X0,site.Y0), (533215.,3942629.))
        self.assertEqual(site.GRID,[533215.,3942629.,553215.,3962629.])
        self.assertEqual(site.TOTAL_AREA,400_000_000.)
        xy = Transformer.from_crs(4326,site.EPSG,always_xy=True).transform(129.477780,35.716670)
        self.assertLess(abs(xy[0]-(site.X0+10000.)),1.)
        self.assertLess(abs(xy[1]-(site.Y0+10000.)),1.)
        self.assertIn("NOT_EXACT_STACK",site.BASE["stack_location_status"])

    def test_all_source_pixel_overlap_valid_and_sha_bound(self):
        with tempfile.TemporaryDirectory() as d:
            directory=Path(d)
            fake_tif(directory/site.NAME)
            report=site.inspect(directory/site.NAME)
            self.assertAlmostEqual(report["modelgrid_valid_source_area_m2"],site.TOTAL_AREA,places=4)
            self.assertAlmostEqual(report["modelgrid_glc210_source_area_m2"],site.TOTAL_AREA,places=4)
            self.assertEqual(report["modelgrid_invalid_source_area_m2"],0)
            (directory/"metadata.json").write_text(json.dumps({
                **site.BASE,**report, "license":"CC-BY-4.0",
                "repeat_download":{"pixels_equal":True}
            }))
            self.assertEqual(site.verify(directory)["sha256"],report["sha256"])
            meta={**site.BASE,**report,"license":"CC-BY-4.0",
                  "repeat_download":{"pixels_equal":True}}
            # PROJ library variants can differ by a few nanodegrees.
            close_corners=[pair[:] for pair in site.BASE["wgs84_corners"]]
            close_corners[0][0]+=5e-9
            (directory/"metadata.json").write_text(json.dumps({
                **meta,"wgs84_corners":close_corners}))
            self.assertEqual(site.verify(directory)["sha256"],report["sha256"])
            # An actual point shift (~1 m), malformed data, and exact metric
            # grid drift must still be rejected.
            close_corners[0][0]+=1e-5
            (directory/"metadata.json").write_text(json.dumps({
                **meta,"wgs84_corners":close_corners}))
            with self.assertRaisesRegex(ValueError,"PROVENANCE_DRIFT:wgs84_corners"):
                site.verify(directory)
            (directory/"metadata.json").write_text(json.dumps({
                **meta,"wgs84_corners":[["not a coordinate",1]]}))
            with self.assertRaisesRegex(ValueError,"PROVENANCE_DRIFT:wgs84_corners"):
                site.verify(directory)
            (directory/"metadata.json").write_text(json.dumps({
                **meta,"x0_m":42.
            }))
            with self.assertRaisesRegex(ValueError,"PROVENANCE_DRIFT"):
                site.verify(directory)

    def test_positive_area_mask_even_if_pixel_center_outside_grid(self):
        with tempfile.TemporaryDirectory() as d:
            target=Path(d)/site.NAME
            fake_tif(target)
            # Top-left outside pixel does not matter; bottom-left border intersects.
            with rasterio.open(target,"r+") as ds:
                a=ds.read(1)
                a[1,1] = 0  # Near NW 20km edge: overlap > 0, centre may be outside.
                ds.write(a,1)
            with self.assertRaisesRegex(ValueError,"MASK_OR_FILL_INTERSECTS_MODEL_GRID"):
                site.inspect(target)

    def test_missing_source_fails_without_earthengine(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(FileNotFoundError):
                site.verify(Path(d))

class TestCoastGeometry(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            from osgeo import ogr
            cls.ogr = ogr
        except ImportError:
            raise unittest.SkipTest("python3-gdal required for offline geometry tests")

    def test_crossing_half_domain_and_independent_area_diagnostics(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/"GSHHS_f_L1.shp"
            fake_shore(path,site.X0+10000.)
            r=site.coast_diagnostic(path)
            self.assertEqual(r["status"],"CROSSES_COAST")
            self.assertEqual(r["intersecting_polygon_count"],1)
            self.assertGreater(r["union_land_area_m2"],0.48*site.TOTAL_AREA)
            self.assertLess(r["union_land_area_m2"],0.52*site.TOTAL_AREA)
            self.assertAlmostEqual(r["sea_area_m2"]+r["union_land_area_m2"],site.TOTAL_AREA)

    def test_all_land_is_not_coastal_pass(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/"GSHHS_f_L1.shp"
            fake_shore(path,site.X0+30000.)
            r=site.coast_diagnostic(path)
            self.assertEqual(r["status"],"NO_SEA_WITHIN_DOMAIN")

    def test_offsite_polygon_fails_closed_not_assumed_real_ocean(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/"GSHHS_f_L1.shp"
            fake_shore(path,site.X0-2000.)
            r=site.coast_diagnostic(path)
            self.assertNotEqual(r["status"],"CROSSES_COAST")

class TestManualWorkflow(unittest.TestCase):
    def test_science_workflow_can_only_be_manually_triggered(self):
        try:
            import yaml
        except ImportError:
            self.skipTest("PyYAML unavailable")
        path=ROOT/".github/workflows/issue119-wolsong-p2b-real-coast.yml"
        doc=yaml.safe_load(path.read_text())
        self.assertEqual(set(doc.get("on",doc.get(True)).keys()), {"workflow_dispatch"})
        contents=path.read_text()
        self.assertNotIn("ee.Initialize",contents)
        self.assertNotIn("secrets.",contents)
        self.assertIn("coastline_only",contents)
        self.assertIn("full_p2b",contents)

if __name__=="__main__":
    unittest.main()
