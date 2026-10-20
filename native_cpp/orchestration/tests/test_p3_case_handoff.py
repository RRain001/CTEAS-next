"""#46 D1-C native P1 (geographic TIFF) + P2-C (UTM 30m) + P3 (GEO).
All rasters are synthetic *real-format*. This is SOFTWARE ONLY, not real
new-site source product or independent original MAKEGEO scientific parity.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch

from native_cpp.orchestration.p2c_case_producer import produce as p2c_produce
from native_cpp.orchestration.p3_case_handoff import produce as p3_produce, make_control
from native_cpp.orchestration.plan import ContractError

try:
    from osgeo import gdal, osr
    from pyproj import Transformer
except ImportError:
    gdal = osr = Transformer = None

ROOT = Path(__file__).resolve().parents[3]
POLICY = ROOT / "docs/plans/ISSUE53_GLC35_USGS38_USER_SELECTED_20261019.json"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


@unittest.skipUnless(gdal is not None and Transformer is not None and
                     all(os.environ.get(k) for k in
                         ("CTEAS_P1_BIN", "CTEAS_P2C_BIN", "CTEAS_P12_BIN", "CTEAS_P3_BIN")),
                     "requires native binaries, GDAL and pyproj")
class SameGridSyntheticNativeP3(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix="p3-b0-d1c-")
        self.addCleanup(temp.cleanup)
        self.home = Path(temp.name)
        self.case = self.home / "newsite_2022"
        (self.case/"grid").mkdir(parents=True)
        self.x0,self.y0 = 510885.,3531269.
        self.nx,self.ny = 4,3
        wgs = Transformer.from_crs(32650,4326,always_xy=True)
        lon, lat = wgs.transform(self.x0+self.nx*50.,self.y0+self.ny*50.)
        (self.case/"case.yaml").write_text(
            "case_name: newsite_2022\nsettings:\n  timezone: UTC+0000\n"
            "preprocess:\n  grid:\n    utm_zone: 50\n    hemisphere: N\n"
            "    nz: 1\n    resolution_km: 0.100\n"
            "    domain:\n      length_km: 0.400\n      width_km: 0.300\n"
            f"    center:\n      latitude: {lat:.12f}\n      longitude: {lon:.12f}\n"
            "  research_time:\n    begin: 20221231-230000\n"
            "    end: 20230101-020000\n",encoding="utf-8")
        (self.case/"grid/grid.cmn").write_text(
            "! IMAP = UTM !\n! DATUM = WGS-84 !\n! IUTMZN = 50 !\n"
            "! LSOHEM = N !\n! XREFKM = 510.885 !\n! YREFKM = 3531.269 !\n"
            "! DGRIDKM = 0.100 !\n! NX = 4 !\n! NY = 3 !\n"
            "! NZ = 1 !\n! ZFACE = 0 !\n! ZFACE = 100 !\n",encoding="utf-8")
        (self.case/"grid/research_time").write_text(
            "BEGIN:20221231-230000\nEND:20230101-020000\n",encoding="utf-8")
        utm = osr.SpatialReference()
        utm.ImportFromEPSG(32650)
        utm.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
        self.land = self.home/"synthetic-land-30m-utm50.tif"
        ds = gdal.GetDriverByName("GTiff").Create(str(self.land),24,20,1,gdal.GDT_Byte)
        self.assertIsNotNone(ds)
        ds.SetProjection(utm.ExportToWkt())
        ds.SetGeoTransform((510825.,30.,0.,3531669.,0.,-30.))
        ds.GetRasterBand(1).SetNoDataValue(0.)
        ds.GetRasterBand(1).WriteRaster(0,0,24,20,
            struct.pack("B",52)*480,buf_type=gdal.GDT_Byte)
        ds=None
        # Actual P1 requires geographic WGS84 GeoTIFF pixel centres, so
        # synthesize a real-format geographic raster over the same UTM site.
        corners=[wgs.transform(x,y) for x in (self.x0-150.,self.x0+550.)
                 for y in (self.y0-150.,self.y0+450.)]
        west=min(q[0] for q in corners)-.001
        east=max(q[0] for q in corners)+.001
        south=min(q[1] for q in corners)-.001
        north=max(q[1] for q in corners)+.001
        geo = osr.SpatialReference()
        geo.ImportFromEPSG(4326)
        geo.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
        self.terrain=self.home/"synthetic-srtm-wgs84.tif"
        ds=gdal.GetDriverByName("GTiff").Create(str(self.terrain),100,100,1,gdal.GDT_Int16)
        self.assertIsNotNone(ds)
        ds.SetProjection(geo.ExportToWkt())
        ds.SetGeoTransform((west,(east-west)/100.,0.,north,0.,-(north-south)/100.))
        ds.GetRasterBand(1).WriteRaster(0,0,100,100,
            struct.pack("<h",125)*10000,buf_type=gdal.GDT_Int16)
        ds=None
        self.p1=Path(os.environ["CTEAS_P1_BIN"])
        self.p2=Path(os.environ["CTEAS_P2C_BIN"])
        self.dat=Path(os.environ["CTEAS_P12_BIN"])
        self.p3=Path(os.environ["CTEAS_P3_BIN"])

    def stage_p2(self):
        proof=p2c_produce(case_yaml=self.case/"case.yaml",
            tif=self.land,tif_sha256=digest(self.land),
            policy=POLICY,mode="inland",native_bin=self.p2)
        self.assertEqual(proof["status"],"P2C_GENERIC_CASE_PRODUCED_UNVERIFIED")
        return proof

    def run_p3(self,**changed):
        values=dict(case_yaml=self.case/"case.yaml",p1_tif=self.terrain,
            p1_tif_sha256=digest(self.terrain),p1_bin=self.p1,
            dat_bin=self.dat,p3_bin=self.p3,p2_kind="C")
        values.update(changed)
        return p3_produce(**values)

    def test_same_grid_true_cpp_P1_P2C_P3_end_to_end_software(self):
        self.stage_p2()
        proof=self.run_p3()
        self.assertEqual(proof["status"],"P3_NATIVE_SAME_CASE_PRODUCED_UNVERIFIED")
        self.assertEqual((proof["nx"],proof["ny"],proof["utm_epsg"]),(4,3,32650))
        stage=self.case/"geo/makegeo/p3_case"
        terrain=stage/"terrain.csv"
        self.assertEqual(len(terrain.read_text().splitlines()),13)
        self.assertEqual(proof["geo_dat_sha256"],digest(stage/"geo.dat"))
        self.assertEqual(proof["terrel_dat_sha256"],digest(stage/"terrel.dat"))
        self.assertEqual(proof["p2_lu_dat_sha256"],
            digest(self.case/"geo/ctgproc/p2c_case/lu.dat"))
        self.assertEqual(proof,
            json.loads((self.case/"evidence/p3.json").read_text()))
        rows=(stage/"p3.csv").read_text().splitlines()
        self.assertEqual(len(rows),13)
        self.assertEqual(stage.joinpath("geo.dat").read_text().splitlines()[7].split(),
                         ["4","3","510.885","3531.269","0.100","0.100"])
        self.assertEqual(proof["p3_original_makegeo_science"],"NOT_RUN")
        with self.assertRaisesRegex(ContractError,"already exists"):
            self.run_p3()

    def test_source_and_case_sha_tampering_fail_before_p1(self):
        self.stage_p2()
        with self.assertRaisesRegex(ContractError,"SHA mismatch"):
            self.run_p3(p1_tif_sha256="0"*64)
        self.assertFalse((self.case/"geo/makegeo/p3_case").exists())
        self.case.joinpath("grid/research_time").write_text(
            "BEGIN:20220101-000000\nEND:20220101-030000\n")
        with self.assertRaisesRegex(ContractError,"disagrees"):
            self.run_p3()
        self.assertFalse((self.case/"evidence/p3.json").exists())

    def test_p2_native_lu_mutation_fails_closed(self):
        self.stage_p2()
        lu=self.case/"geo/ctgproc/p2c_case/lu.dat"
        lu.write_bytes(lu.read_bytes()+b"tamper")
        with self.assertRaisesRegex(ContractError,"provenance/case/source grid mismatch"):
            self.run_p3()
        self.assertFalse((self.case/"geo/makegeo/p3_case").exists())


class ControlGuard(unittest.TestCase):
    def test_control_only_changes_geography_keys(self):
        from native_cpp.orchestration.p3_case_handoff import APPROVED_TEMPLATE
        from types import SimpleNamespace
        t=APPROVED_TEMPLATE.read_text()
        case=SimpleNamespace(utm_zone=52,hemisphere="N",xrefkm_text="533.215",
             yrefkm_text="3942.629",nx=4,ny=3,dgridkm=.1)
        out=make_control(t,case)
        self.assertIn("! IUTMZN = 52 !",out)
        self.assertIn("! NX = 4 !",out)
        with self.assertRaisesRegex(ContractError,"missing/duplicate"):
            make_control(t+"\n! NX = 200 !\n",case)


if __name__=="__main__":
    unittest.main()
