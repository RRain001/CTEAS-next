"""No-network checks for explicit OpenTopography GL1/GL3 same-product bulk transport."""
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
from scripts.s2g.p1_opentopo_bulk import tiles_for_bbox, _tile_url, OpenTopoBulkError

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

    def test_gl3_bulk_urls_use_official_latitude_bands(self):
        # 2026-10-19 official S3 ListObjectsV2: northern tiles require
        # an intermediate North/ folder, while South has no latitude band.
        root="https://opentopography.s3.sdsc.edu/raster/SRTM_GL3/SRTM_GL3_srtm/"
        self.assertEqual(
            _tile_url("N29E115.tif","SRTMGL3"),
            root+"North/North_0_29/N29E115.tif")
        self.assertEqual(
            _tile_url("N30E115.tif","SRTMGL3"),
            root+"North/North_30_60/N30E115.tif")
        self.assertEqual(
            _tile_url("N31E114.tif","SRTMGL3"),
            root+"North/North_30_60/N31E114.tif")
        self.assertEqual(
            _tile_url("N31E115.tif","SRTMGL3"),
            root+"North/North_30_60/N31E115.tif")
        self.assertEqual(
            _tile_url("S01E006.tif","SRTMGL3"),
            root+"South/S01E006.tif")
        self.assertEqual(
            _tile_url("S01E115.tif","SRTMGL3"),
            root+"South/S01E115.tif")
        self.assertEqual(
            _tile_url("N31E115.tif","SRTMGL1"),
            "https://opentopography.s3.sdsc.edu/raster/SRTM_GL1/"
            "SRTM_GL1_srtm/N31E115.tif")
        with self.assertRaises(OpenTopoBulkError):
            _tile_url("../secret.tif","SRTMGL3")
        with self.assertRaises(OpenTopoBulkError):
            tiles_for_bbox({"west":114,"east":115,"south":31,"north":32},dem="OTHER")

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
            def fake_official_bulk(box,scratch,dest,*,max_pixels,max_bytes,dem="SRTMGL1"):
                self.assertEqual(dem,"SRTMGL1")
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
            self.assertNotIn("official_dataset_documentation",data)
            self.assertEqual(data["transport"],"opentopography_official_public_s3_bulk")
            self.assertTrue(data["bulk_recovery_used"])
            self.assertEqual(data["case_window_nodata_pixels"],0)
            self.assertFalse(data["ready_for_generic_P1_physics"])
            self.assertEqual(data["selected_tif_properties"]["resolution_degrees"][0],1/3600)

    def test_opted_in_gl3_406_uses_same_product_bulk_only(self):
        with tempfile.TemporaryDirectory() as td:
            case=stage_case(Path(td))
            out=case/"geo/terrel/source_gl3_recovery"
            seen=[]
            def fake_gl3_bulk(box,scratch,dest,*,max_pixels,max_bytes,dem="SRTMGL1"):
                seen.append(dem)
                px=3/3600
                left=math.floor((box["west"]-0.006)/px)*px
                top=math.ceil((box["north"]+0.006)/px)*px
                width=math.ceil((box["east"]+0.006-left)/px)
                height=math.ceil((top-(box["south"]-0.006))/px)
                with rasterio.open(dest,"w",driver="GTiff",width=width,height=height,
                                   count=1,dtype="int16",crs="EPSG:4326",
                                   transform=from_origin(left,top,px,px),nodata=-32768) as f:
                    f.write(np.full((height,width),77,dtype="int16"),1)
                from scripts.s2g.p1_terrain_source import check_raster
                return [check_raster(dest)]
            with patch.dict(os.environ,{"OPENTOPOGRAPHY_API_KEY":"FAKE_OFFLINE"}):
                with patch("scripts.s2g.p1_terrain_source._download_api",
                           side_effect=P1SourceError(
                               "OpenTopography HTTP 406 [UNCLASSIFIED_PROVIDER_REJECTION]")):
                    with patch("scripts.s2g.p1_opentopo_bulk.fetch_and_crop",
                               side_effect=fake_gl3_bulk):
                        data=prepare(case/"grid/grid.cmn",out,"opentopography",
                                     dem="SRTMGL3",allow_public_bulk_fallback=True)
            self.assertEqual(seen,["SRTMGL3"])
            self.assertEqual(data["dataset"],"SRTMGL3")
            self.assertEqual(data["transport"],"opentopography_official_public_s3_bulk")
            self.assertEqual(data["requested_resolution_arcsec"],3.0)
            self.assertEqual(data["selected_tif_properties"]["resolution_degrees"][0],3/3600)
            self.assertTrue((out/"srtmgl3_90m.tif").is_file())
            self.assertFalse((out/"srtmgl1_30m.tif").exists())
            evidence=data["official_dataset_documentation"]
            self.assertEqual(evidence["provider_product"],"SRTM_GL3")
            self.assertEqual(evidence["nasa_product_family"],"SRTMGL3.003")
            self.assertEqual(evidence["declared_vertical_crs"],"EPSG:5773")
            self.assertEqual(evidence["declared_vertical_datum"],"EGM96 geoid")
            self.assertEqual(evidence["declared_vertical_units"],"m")
            self.assertEqual(evidence["evidence_level"],"OFFICIAL_COLLECTION_METADATA_ONLY")
            self.assertFalse(evidence["tile_matches_independent_nasa_granule"])
            self.assertFalse(evidence["tile_independent_published_checksum_verified"])
            self.assertFalse(evidence["tiff_embedded_vertical_crs_verified"])
            self.assertFalse(evidence["vertical_conversion_applied"])
            self.assertFalse(data["source_product_version_authenticated"])
            self.assertFalse(data["height_vertical_datum_authenticated"])

if __name__=="__main__":
    unittest.main()
