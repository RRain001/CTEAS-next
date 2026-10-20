"""S2-B synthetic *software-only* original-style P2-C dynamic site test."""
import hashlib
import json
import os
from pathlib import Path
import struct
import tempfile
import unittest

from native_cpp.orchestration.p2c_case_producer import produce
from native_cpp.orchestration.plan import ContractError
try:
    from osgeo import gdal, osr
except ImportError:
    gdal = osr = None

ROOT = Path(__file__).resolve().parents[3]
POLICY = ROOT / "docs/plans/ISSUE53_GLC35_USGS38_USER_SELECTED_20261019.json"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


@unittest.skipUnless(gdal is not None and os.getenv("CTEAS_P2C_BIN"),
                     "requires GDAL and a compiled native P2-C CLI")
class DynamicP2C(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix="s2b-dynamic-")
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.case = self.root / "case_alt"
        (self.case / "grid").mkdir(parents=True)
        crs = osr.SpatialReference()
        crs.ImportFromEPSG(32650)
        crs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
        geo = osr.SpatialReference()
        geo.ImportFromEPSG(4326)
        geo.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
        lon, lat, _ = osr.CoordinateTransformation(crs, geo).TransformPoint(
            511085, 3531419)
        (self.case / "case.yaml").write_text(
            "case_name: case_alt\nsettings:\n  timezone: UTC+0000\n"
            "preprocess:\n  grid:\n    utm_zone: 50\n    hemisphere: N\n"
            "    nz: 1\n    resolution_km: 0.100\n"
            "    domain:\n      length_km: 0.400\n      width_km: 0.300\n"
            f"    center:\n      latitude: {lat:.12f}\n      longitude: {lon:.12f}\n"
            "  research_time:\n    begin: 20221231-230000\n"
            "    end: 20230101-020000\n", encoding="utf-8")
        (self.case / "grid/grid.cmn").write_text(
            "! IMAP = UTM !\n! DATUM = WGS-84 !\n! IUTMZN = 50 !\n"
            "! LSOHEM = N !\n! XREFKM = 510.885 !\n! YREFKM = 3531.269 !\n"
            "! DGRIDKM = 0.100 !\n! NX = 4 !\n! NY = 3 !\n"
            "! NZ = 1 !\n! ZFACE = 0 !\n! ZFACE = 100 !\n", encoding="utf-8")
        (self.case / "grid/research_time").write_text(
            "BEGIN: 20221231-230000\nEND: 20230101-020000\n", encoding="utf-8")
        self.tif = self.root / "synthetic-30m.tif"
        ds = gdal.GetDriverByName("GTiff").Create(str(self.tif), 18, 18, 1, gdal.GDT_Byte)
        self.assertIsNotNone(ds)
        ds.SetProjection(crs.ExportToWkt())
        ds.SetGeoTransform((510800., 30., 0., 3531769., 0., -30.))
        ds.GetRasterBand(1).SetNoDataValue(0.)
        ds.GetRasterBand(1).WriteRaster(
            0, 0, 18, 18, struct.pack("B", 52) * 324, buf_type=gdal.GDT_Byte)
        ds = None

    def call_native(self, **changes):
        opts = dict(case_yaml=self.case / "case.yaml", tif=self.tif,
                    tif_sha256=sha(self.tif), policy=POLICY, mode="inland",
                    native_bin=Path(os.environ["CTEAS_P2C_BIN"]))
        opts.update(changes)
        return produce(**opts)

    def test_real_native_4_by_3_and_sha_evidence(self):
        result = self.call_native()
        self.assertEqual(result["status"], "P2C_GENERIC_CASE_PRODUCED_UNVERIFIED")
        self.assertEqual((result["nx"], result["ny"]), (4, 3))
        self.assertEqual(result["research_end_utc"], "20230101-020000")
        out = self.case / "geo/ctgproc/p2c_case"
        manifest = json.loads((out / "p2c_glc30m_manifest.json").read_text())
        self.assertEqual(manifest["fraction_fields"], 456)
        self.assertEqual(manifest["nonempty_cells"], 12)
        self.assertEqual(manifest["water55_hits"], 0)
        self.assertEqual(result["lu_dat_sha256"], sha(out / "lu.dat"))
        self.assertEqual(result, json.loads((self.case / "evidence/p2.json").read_text()))
        with self.assertRaisesRegex(ContractError, "already used"):
            self.call_native()

    def test_input_tampering_and_inland_coast_fail_closed(self):
        with self.assertRaisesRegex(ContractError, "SHA|source"):
            self.call_native(tif_sha256="0" * 64)
        with self.assertRaisesRegex(ContractError, "forbids"):
            self.call_native(bln=self.tif, bln_sha256=sha(self.tif))
        self.assertFalse((self.case / "geo/ctgproc/p2c_case").exists())


if __name__ == "__main__":
    unittest.main()
