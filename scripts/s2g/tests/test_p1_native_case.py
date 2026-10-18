"""#54 synthetic source=>native P1 end-to-end; NOT a real DEM/original parity test."""
from __future__ import annotations
import json
import math
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np
import rasterio
from rasterio.transform import from_origin

from scripts.s2g import p1_terrain_source as source
from scripts.s2g.p1_native_case import run_case, LOCAL_PRODUCTS
from native_cpp.orchestration.plan import ContractError


class NativeCaseTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix="issue54-p1-d1b-")
        self.base=Path(self.temp.name)
        self.case_dir=self.base/"newsite_2022"
        grid_dir=self.case_dir/"grid"
        grid_dir.mkdir(parents=True)
        (self.case_dir/"geo/terrel").mkdir(parents=True)
        self.grid=grid_dir/"grid.cmn"
        self.grid.write_text("\n".join((
            "! IMAP = UTM !","! IUTMZN = 50 !","! LSOHEM = N !",
            "! DATUM = WGS-84 !","! XREFKM = 510.885 !",
            "! YREFKM = 3531.269 !","! NX = 50 !","! NY = 50 !",
            "! DGRIDKM = 0.100 !","! NZ = 1 !",
            "! ZFACE = 0 !","! ZFACE = 100 !","")),encoding="utf-8")
        (grid_dir/"research_time").write_text(
            "BEGIN:20220101-000000\nEND:20220101-030000\n",encoding="utf-8")
        self.case=self.case_dir/"case.yaml"
        self.case.write_text("""
case_name: newsite_2022
settings:
  timezone: UTC+0000
preprocess:
  grid:
    utm_zone: 50
    hemisphere: N
    nz: 1
    resolution_km: 0.1
    domain:
      length_km: 5
      width_km: 5
    center:
      latitude: 31.939774444
      longitude: 117.141610855
  research_time:
    begin: 20220101-000000
    end: 20220101-030000
""".lstrip(),encoding="utf-8")
        self.binary=Path(os.environ.get("P1_CASE_BINARY","/nonexistent")).absolute()
        if not self.binary.is_file():
            self.fail("P1_CASE_BINARY required for native end-to-end CI")
        self.box=source.case_bbox(self.grid)

    def tearDown(self):
        self.temp.cleanup()

    def fixture(self, name, arcsec):
        pixel=arcsec/3600
        b=self.box
        left=math.floor((b["west"]-0.004)/pixel)*pixel
        top=math.ceil((b["north"]+0.004)/pixel)*pixel
        width=math.ceil((b["east"]+0.004-left)/pixel)
        height=math.ceil((top-(b["south"]-0.004))/pixel)
        path=self.base/name
        with rasterio.open(path,"w",driver="GTiff",width=width,height=height,
                           count=1,dtype="int16",crs="EPSG:4326",
                           transform=from_origin(left,top,pixel,pixel),
                           nodata=-32768) as dst:
            dst.write(np.full((height,width),123,dtype=np.int16),1)
        return path

    def run_terrain(self, manifest, product, name="p1_native"):
        return run_case(case_yaml=self.case,source_manifest=manifest,
                        source_product=product,binary=self.binary,
                        out_dir=self.case_dir/"geo/terrel"/name)

    def test_local_3arcsec_single_and_immutable_hashes(self):
        tiff=self.fixture("srtm_3arcsec.tif",3)
        stage=self.base/"source_local"
        source.prepare(self.grid,stage,"local",tifs=[tiff])
        report=self.run_terrain(stage/"p1_source_manifest.json","CGIAR-CSI-SRTM-v4.1")
        self.assertEqual(report["status"],"PRODUCED_UNVERIFIED")
        self.assertEqual(report["route"],"P1_A_90M_LOCAL")
        self.assertEqual(report["row_count"],2500)
        self.assertEqual(report["science_acceptance"],"NOT_RUN")
        self.assertGreater(report["source_pixel_hits"],2500)
        self.assertTrue((self.case_dir/"geo/terrel/p1_native/terrain.csv").is_file())

    def test_cached_srtmgl1_offline_mock_is_unverified(self):
        tiff=self.fixture("synthetic_1arcsec.tif",1)
        stage=self.base/"source_api_mock"
        def fake_download(bbox,destination,key,*,max_bytes,timeout=150):
            shutil.copyfile(tiff,destination)
        with patch.dict(os.environ,{source.SECRET_ENV:"SYNTHETIC_KEY_NOT_REAL"}):
            with patch.object(source,"_download_api",side_effect=fake_download):
                source.prepare(self.grid,stage,"opentopography")
        report=self.run_terrain(stage/"p1_source_manifest.json","SRTMGL1")
        self.assertEqual(report["route"],"P1_B_30M_DOWNLOAD")
        self.assertEqual(report["science_acceptance"],"NOT_RUN")
        self.assertEqual(report["row_count"],2500)

    def test_refuse_wrong_route_and_sha_and_no_output(self):
        tiff=self.fixture("srtm_3arcsec.tif",3)
        stage=self.base/"source_local"
        source.prepare(self.grid,stage,"local",tifs=[tiff])
        manifest=stage/"p1_source_manifest.json"
        with self.assertRaisesRegex(ContractError,"declared 3-arc-sec"):
            self.run_terrain(manifest,"SRTMGL1")
        self.assertFalse((self.case_dir/"geo/terrel/p1_native").exists())
        data=json.loads(manifest.read_text(encoding="utf-8"))
        data["selected_tif_sha256"]="0"*64
        manifest.write_text(json.dumps(data),encoding="utf-8")
        with self.assertRaisesRegex(ContractError,"SHA differs"):
            self.run_terrain(manifest,"CGIAR-CSI-SRTM-v4.1")
        self.assertFalse((self.case_dir/"geo/terrel/p1_native").exists())

    def test_refuse_wrong_resolution_and_time(self):
        tiff=self.fixture("wrong_1arcsec.tif",1)
        stage=self.base/"source_local"
        source.prepare(self.grid,stage,"local",tifs=[tiff])
        manifest=stage/"p1_source_manifest.json"
        with self.assertRaisesRegex(ContractError,"angular resolution"):
            self.run_terrain(manifest,"NASA-SRTMGL3-v003")
        self.assertFalse((self.case_dir/"geo/terrel/p1_native").exists())
        (self.case_dir/"grid/research_time").write_text(
            "BEGIN:20220101-000000\nEND:20220101-040000\n",encoding="utf-8")
        with self.assertRaisesRegex(ContractError,"disagrees"):
            self.run_terrain(manifest,"NASA-SRTMGL3-v003")


if __name__=="__main__":
    unittest.main()
