"""#54: no network, independent checks for explicit true SRTMGL1 bulk transport."""
from __future__ import annotations
import math
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
import rasterio
from rasterio.transform import from_origin
from scripts.s2g.p1_real_actions_case import stage_case
from scripts.s2g.p1_terrain_source import prepare, P1SourceError
from scripts.s2g.p1_opentopo_bulk import tiles_for_bbox, OpenTopoBulkError

class BulkFallbackAdmissionTests(unittest.TestCase):
    def test_only_exact_open_topography_srtmgl1_one_degree_sheets(self):
        bbox={"west":114.97,"east":115.03,"south":31.91,"north":31.98}
        self.assertEqual(tiles_for_bbox(bbox),["N31E114.tif","N31E115.tif"])
        self.assertEqual(tiles_for_bbox({"west":115.0,"east":115.03,
                                         "south":31.91,"north":31.98}),["N31E115.tif"])
        with self.assertRaises(OpenTopoBulkError):
            tiles_for_bbox({"west":114,"east":118.1,"south":30,"north":34.2})
        with self.assertRaises(OpenTopoBulkError):
            tiles_for_bbox({"west":114,"east":115,"south":60,"north":61})

    def test_http_406_no_fallback_by_default(self):
        with tempfile.TemporaryDirectory() as td:
            case=stage_case(Path(td))
            out=case/"geo/terrel/source_disabled"
            with patch.dict(os.environ,{"OPENTOPOGRAPHY_API_KEY":"FAKE_OFFLINE"}):
                with patch("scripts.s2g.p1_terrain_source._download_api",
                           side_effect=P1SourceError(
                               "OpenTopography HTTP 406 [UNCLASSIFIED_PROVIDER_REJECTION]")):
                    with self.assertRaisesRegex(P1SourceError,"HTTP 406"):
                        prepare(case/"grid/grid.cmn",out,"opentopography")
            self.assertFalse(out.exists())

    def test_401_no_silent_fallback_even_when_opted_in(self):
        with tempfile.TemporaryDirectory() as td:
            case=stage_case(Path(td))
            out=case/"geo/terrel/source_denied"
            with patch.dict(os.environ,{"OPENTOPOGRAPHY_API_KEY":"FAKE_OFFLINE"}):
                with patch("scripts.s2g.p1_terrain_source._download_api",
                           side_effect=P1SourceError(
                               "OpenTopography HTTP 401 [API_KEY_REJECTED]")):
                    with patch("scripts.s2g.p1_opentopo_bulk.fetch_and_crop") as fallback:
                        with self.assertRaisesRegex(P1SourceError,"HTTP 401"):
                            prepare(case/"grid/grid.cmn",out,"opentopography",
                                    allow_public_bulk_fallback=True)
                        fallback.assert_not_called()
            self.assertFalse(out.exists())

    def test_opted_in_406_uses_same_1arcsec_route_b_manifest(self):
        with tempfile.TemporaryDirectory() as td:
            case=stage_case(Path(td))
            out=case/"geo/terrel/source_recovered"
            def fake_official_bulk(box,scratch,dest,*,max_pixels,max_bytes):
                px=1/3600
                left=math.floor((box["west"]-0.006)/px)*px
                top=math.ceil((box["north"]+0.006)/px)*px
                width=math.ceil((box["east"]+0.006-left)/px)
                height=math.ceil((top-(box["south"]-0.006))/px)
                with rasterio.open(dest,"w",driver="GTiff",width=width,height=height,
                                   count=1,dtype="int16",crs="EPSG:4326",
                                   transform=from_origin(left,top,px,px),
                                   nodata=-32768) as f:
                    f.write(np.full((height,width),77,dtype="int16"),1)
                from scripts.s2g.p1_terrain_source import check_raster
                return [check_raster(dest)]
            with patch.dict(os.environ,{"OPENTOPOGRAPHY_API_KEY":"FAKE_OFFLINE"}):
                with patch("scripts.s2g.p1_terrain_source._download_api",
                           side_effect=P1SourceError(
                               "OpenTopography HTTP 406 [UNCLASSIFIED_PROVIDER_REJECTION]")):
                    with patch("scripts.s2g.p1_opentopo_bulk.fetch_and_crop",
                               side_effect=fake_official_bulk) as fallback:
                        data=prepare(case/"grid/grid.cmn",out,"opentopography",
                                     allow_public_bulk_fallback=True)
                        fallback.assert_called_once()
            self.assertEqual(data["mode"],"opentopography")
            self.assertEqual(data["dataset"],"SRTMGL1")
            self.assertEqual(data["transport"],"opentopography_official_public_s3_bulk")
            self.assertTrue(data["bulk_recovery_used"])
            self.assertEqual(data["case_window_nodata_pixels"],0)
            self.assertFalse(data["ready_for_generic_P1_physics"])
            self.assertEqual(data["selected_tif_properties"]["resolution_degrees"][0],1/3600)

if __name__=="__main__":
    unittest.main()
