"""Test that provider HTTP rejection yields only safe category, not secret/body."""
from __future__ import annotations
import io
import json
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import patch
from scripts.s2g.p1_terrain_source import _download_api,P1SourceError
from scripts.s2g import p1_real_actions_case as actions

class ProviderErrorRedaction(unittest.TestCase):
    def simulate(self,provider_body:bytes):
        class Opener:
            def open(self,req,timeout):
                raise urllib.error.HTTPError(req.full_url,406,"Not Acceptable",{},
                                              io.BytesIO(provider_body))
        box={"north":32.0,"south":31.9,"east":115.05,"west":114.95}
        with tempfile.TemporaryDirectory() as td:
            with patch("urllib.request.build_opener",return_value=Opener()):
                with self.assertRaises(P1SourceError) as caught:
                    _download_api(box,Path(td)/"fail.tif","SECRET_WILL_NEVER_LOG",
                                  max_bytes=1_000_000)
        error=str(caught.exception)
        self.assertNotIn("SECRET_WILL_NEVER_LOG",error)
        self.assertNotIn("portal.opentopography",error)
        self.assertNotIn("PRIVATE_BODY",error)
        self.assertIn("HTTP 406",error)
        return error

    def test_key_rejection_redacted(self):
        e=self.simulate(b"Invalid API key SECRET_WILL_NEVER_LOG PRIVATE_BODY")
        self.assertIn("[API_KEY_REJECTED]",e)

    def test_quota_rejection_redacted(self):
        e=self.simulate(b"daily limit exceeded SECRET_WILL_NEVER_LOG PRIVATE_BODY")
        self.assertIn("[QUOTA_OR_RATE_LIMIT]",e)

    def test_unknown_406_redacted(self):
        e=self.simulate(b"406 not acceptable PRIVATE_BODY SECRET_WILL_NEVER_LOG")
        self.assertIn("[UNCLASSIFIED_PROVIDER_REJECTION]",e)

    def test_safe_gl3_bulk_404_recognized_without_url(self):
        d=actions.classify_source_failure(
            P1SourceError("official public SRTM tile HTTP 404, body withheld"))
        self.assertEqual(d["source_failure_stage"],"S3_BULK_DOWNLOAD")
        self.assertEqual(d["source_failure_reason_code"],"BULK_TILE_HTTP_REJECTED")
        self.assertEqual(d["source_provider_http_code"],404)

    def test_safe_gl3_raster_validation_recognized(self):
        cases={
          "OpenTopography returned resolution inconsistent with requested DEM":
              ("GEOTIFF_VALIDATION","SOURCE_RESOLUTION_MISMATCH"),
          "P1 source missing valid int16 NoData metadata":
              ("GEOTIFF_VALIDATION","SOURCE_NODATA_METADATA_MISSING"),
          "P1 source mosaic/DEM does not cover buffered case bbox":
              ("CASE_RASTER_ADMISSION","SOURCE_COVERAGE_INSUFFICIENT"),
          "P1 DEM has 23 NoData pixels in buffered case; use --allow-nodata only after documenting void handling":
              ("CASE_RASTER_ADMISSION","CASE_NODATA_PRESENT"),
          "OpenTopography network/IO error (request URL withheld)":
              ("OPENTOPOGRAPHY_API","API_NETWORK_IO_ERROR"),
          "OPENTOPOGRAPHY_API_KEY is not configured":
              ("SOURCE_PRECHECK","API_KEY_MISSING"),
        }
        for message,expected in cases.items():
            with self.subTest(message=message):
                d=actions.classify_source_failure(P1SourceError(message))
                self.assertEqual((d["source_failure_stage"],d["source_failure_reason_code"]),expected)
                self.assertIsNone(d["source_provider_http_code"])

    def test_untrusted_source_error_never_leaks_body_or_key(self):
        secret="SECRET_FAKE_012345"
        raw="blocked at https://portal.opentopography.org/?API_Key="+secret
        d=actions.classify_source_failure(P1SourceError(raw))
        self.assertEqual(d["source_failure_reason_code"],"UNCLASSIFIED_SOURCE_FAILURE")
        self.assertNotIn(secret,json.dumps(d))
        self.assertNotIn("portal.opentopography",json.dumps(d))

    def test_gl3_blocked_run_writes_staged_safe_diagnostic(self):
        with tempfile.TemporaryDirectory() as td:
            report=Path(td)/"blocked.json"
            with patch.object(actions,"run",side_effect=P1SourceError(
                    "official public SRTM tile HTTP 404, body withheld")):
                rc=actions.main(["--root",str(Path(td)/"case"),"--route",
                                 "P1_B_90M_DOWNLOAD","--binary",str(Path(td)/"native"),
                                 "--report",str(report)])
            obj=json.loads(report.read_text())
            self.assertEqual(rc,2)
            self.assertEqual(obj["source_failure_stage"],"S3_BULK_DOWNLOAD")
            self.assertEqual(obj["source_failure_reason_code"],"BULK_TILE_HTTP_REJECTED")
            self.assertEqual(obj["source_provider_http_code"],404)
            self.assertFalse(obj["native_p1_executed"])
            self.assertFalse(obj["original_terrel_executed"])

    def test_blocked_real_run_writes_secret_free_metadata(self):
        with tempfile.TemporaryDirectory() as td:
            report=Path(td)/"evidence.json"
            with patch.object(actions,"run",
                              side_effect=P1SourceError(
                              "OpenTopography HTTP 406 [API_KEY_REJECTED]; key, URL and body withheld")):
                rc=actions.main(["--root",str(Path(td)/"case"),
                                 "--route","P1_B_30M_DOWNLOAD",
                                 "--binary",str(Path(td)/"missing-native"),
                                 "--report",str(report)])
            self.assertEqual(rc,2)
            obj=json.loads(report.read_text())
            self.assertEqual(obj["source_provider_http_code"],406)
            self.assertEqual(obj["provider_failure_category"],"API_KEY_REJECTED")
            self.assertEqual(obj["source_failure_stage"],"OPENTOPOGRAPHY_API")
            self.assertEqual(obj["source_failure_reason_code"],"API_HTTP_REJECTED")
            self.assertEqual(obj["native_p1_executed"],False)
            self.assertEqual(obj["science_acceptance"],"NOT_ACCEPTED")
            self.assertNotIn("SECRET",report.read_text())

if __name__=="__main__":
    unittest.main()
