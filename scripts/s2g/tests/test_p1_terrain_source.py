"""P1 source admission ONLY, generated real GeoTIFF tiles + fake API transport.

Tests do NOT download OpenTopography data and do NOT execute native P1.
"""
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

from scripts.s2g import p1_terrain_source as p1


class P1SourcesTest(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix="p1-source-test-")
        self.root=Path(self.tmp.name)
        self.grid=self.root/"grid.cmn"
        self.grid.write_text("\n".join([
            "! IMAP = UTM !", "! IUTMZN = 50 !", "! LSOHEM = N !",
            "! DATUM = WGS-84 !", "! XREFKM = 510.885 !",
            "! YREFKM = 3531.269 !", "! NX = 3 !", "! NY = 3 !",
            "! DGRIDKM = 0.1 !",
        ])+"\n")
        self.box=p1.case_bbox(self.grid)
        self.pixel=0.0001
        self.left=math.floor((self.box["west"]-0.003)/self.pixel)*self.pixel
        self.top=math.ceil((self.box["north"]+0.003)/self.pixel)*self.pixel
        # 150px 1st + 150px 2nd: guaranteed include both sides of small footprint.
        self.a=self.tile("part_a.tif", 0,150,130)
        self.b=self.tile("part_b.tif",150,150,130)
        self.all=self.tile("entire.tif",0,300,130)

    def tearDown(self):
        self.tmp.cleanup()

    def tile(self,name,start_col,width,value, *,res=None,crs="EPSG:4326",
             height=300,nodata=-32768):
        pixel=self.pixel if res is None else res
        path=self.root/name
        with rasterio.open(
            path,"w",driver="GTiff",width=width,height=height,
            count=1,dtype="int16",crs=crs,
            transform=from_origin(self.left+start_col*self.pixel,self.top,pixel,pixel),
            nodata=nodata,
        ) as dst:
            dst.write(np.full((height,width),value,dtype=np.int16),1)
        return path

    def target(self,suffix):
        return self.root/suffix

    def test_local_single_no_extra_crop_or_copy(self):
        path=self.target("one_source")
        out=p1.prepare(self.grid,path,"local",tifs=[self.all])
        self.assertEqual(out["mode"],"local")
        self.assertEqual(out["selected_tif"],str(self.all.absolute()))
        self.assertFalse(out["mosaic_created"])
        self.assertEqual(out["case_window_nodata_pixels"],0)
        self.assertEqual(out["p1_native_science"],"NOT_RUN_FROZEN_HEFEI_CLI")
        self.assertEqual(json.loads((path/"p1_source_manifest.json").read_text())["selected_tif_sha256"],
                         p1.sha256(self.all))
        self.assertFalse((path/"p1_local_mosaic.tif").exists())

    def test_local_multi_creates_integrity_checked_unified_tiff(self):
        result=p1.prepare(self.grid,self.target("combined"),"local",tifs=[self.a,self.b])
        self.assertEqual(len(result["source_tifs"]),2)
        self.assertTrue(result["mosaic_created"])
        self.assertEqual(result["case_window_nodata_pixels"],0)
        resultfile=self.target("combined/p1_local_mosaic.tif")
        self.assertTrue(resultfile.is_file())
        self.assertEqual(p1.sha256(resultfile),result["selected_tif_sha256"])
        with rasterio.open(resultfile) as ds:
            self.assertEqual(ds.dtypes[0],"int16")
            self.assertEqual(int(ds.nodata),-32768)
            self.assertEqual(np.unique(ds.read(1)).tolist(),[130])

    def test_local_directory_scanned_without_sources_overwritten(self):
        src=self.root/"source-dir"
        src.mkdir()
        t=src/"sample.tif"
        shutil.copy2(self.all,t)
        before=p1.sha256(t)
        out=p1.prepare(self.grid,self.target("directory"),"local",tif_dir=src)
        self.assertEqual(len(out["source_tifs"]),1)
        self.assertEqual(out["source_tifs"][0]["sha256"],before)
        self.assertEqual(p1.sha256(t),before)

    def test_refuse_existing_output(self):
        self.target("not-empty").mkdir()
        with self.assertRaisesRegex(p1.P1SourceError,"already exists"):
            p1.prepare(self.grid,self.target("not-empty"),"local",tifs=[self.all])

    def test_refuse_gap_and_keep_staged_case_absent(self):
        left=self.tile("gap_a.tif",0,60,130)
        right=self.tile("gap_b.tif",160,140,130)
        dest=self.target("gap")
        with self.assertRaisesRegex(p1.P1SourceError,"NoData"):
            p1.prepare(self.grid,dest,"local",tifs=[left,right])
        self.assertFalse(dest.exists())

    def test_refuse_misaligned_resolution(self):
        mismatch=self.tile("different_pixel.tif",150,150,130,res=.0002)
        dest=self.target("different-res")
        with self.assertRaisesRegex(p1.P1SourceError,"spacing/alignment"):
            p1.prepare(self.grid,dest,"local",tifs=[self.a,mismatch])
        self.assertFalse(dest.exists())

    def test_refuse_wrong_crs(self):
        wrong=self.tile("bad-crs.tif",0,300,130,crs="EPSG:3857")
        with self.assertRaisesRegex(p1.P1SourceError,"EPSG:4326"):
            p1.prepare(self.grid,self.target("bad-crs-output"),"local",tifs=[wrong])

    def test_refuse_overlap_disagree(self):
        conflicting=self.tile("conflict.tif",149,151,131)
        dest=self.target("conflict-out")
        with self.assertRaisesRegex(p1.P1SourceError,"disagree"):
            p1.prepare(self.grid,dest,"local",tifs=[self.a,conflicting])
        self.assertFalse(dest.exists())

    def test_refuse_api_without_secret_even_when_case_valid(self):
        with patch.dict(os.environ,{p1.SECRET_ENV:""},clear=False):
            with self.assertRaisesRegex(p1.P1SourceError,p1.SECRET_ENV):
                p1.prepare(self.grid,self.target("api-no-secret"),"opentopography")

    def test_api_uses_env_only_and_never_writes_key(self):
        seen={}
        fakekey="TEST_SECRET_NOT_REAL_KEY"
        def fake_download(box,path,key,*,max_bytes,timeout=150):
            seen["key"]=key
            seen["box"]=box
            shutil.copyfile(self.all,path)
        dest=self.target("api-mock")
        with patch.dict(os.environ,{p1.SECRET_ENV:fakekey}):
            with patch.object(p1,"_download_api",side_effect=fake_download):
                result=p1.prepare(self.grid,dest,"opentopography")
        self.assertEqual(seen["key"],fakekey)
        self.assertEqual(result["dataset"],"SRTMGL1")
        self.assertEqual(result["mode"],"opentopography")
        self.assertFalse(result["api_key_logged"])
        self.assertNotIn(fakekey,(dest/"p1_source_manifest.json").read_text())
        self.assertTrue((dest/"srtmgl1_30m.tif").exists())

    def test_api_preflight_rejects_tif_mode_mixing(self):
        with self.assertRaisesRegex(p1.P1SourceError,"must not silently mix"):
            p1.prepare(self.grid,self.target("mixed"),"opentopography",tifs=[self.a])

    def test_api_preflight_rejects_overlarge_pixel_budget_without_network(self):
        with self.assertRaisesRegex(p1.P1SourceError,"pixel"):
            p1.prepare(self.grid,self.target("budget"),"opentopography",max_pixels=1)

    def test_api_http_error_sanitized(self):
        import urllib.error
        from urllib.request import Request
        class ErrorOpener:
            def open(self, request,timeout):
                raise urllib.error.HTTPError(request.full_url,403,"forbidden",{},None)
        dest=self.target("test_api_output.tif")
        with patch("scripts.s2g.p1_terrain_source.urllib.request.build_opener",
                   return_value=ErrorOpener()):
            with self.assertRaises(p1.P1SourceError) as e:
                p1._download_api(self.box,dest,"FAKE_SECRET",max_bytes=4096)
        self.assertNotIn("FAKE_SECRET",str(e.exception))
        self.assertIn("HTTP 403",str(e.exception))

    def test_api_provider_is_hardcoded_to_30m_srtm(self):
        self.assertEqual(p1.DATASET,"SRTMGL1")
        self.assertIn("opentopography.org",p1.BASE)
        self.assertEqual(p1.SECRET_ENV,"OPENTOPOGRAPHY_API_KEY")


if __name__=="__main__":
    unittest.main()
