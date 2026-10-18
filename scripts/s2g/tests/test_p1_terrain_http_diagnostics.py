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
            self.assertEqual(obj["native_p1_executed"],False)
            self.assertEqual(obj["science_acceptance"],"NOT_ACCEPTED")
            self.assertNotIn("SECRET",report.read_text())

if __name__=="__main__":
    unittest.main()
