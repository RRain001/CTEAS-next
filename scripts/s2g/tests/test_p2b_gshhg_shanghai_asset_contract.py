"""Non-science tests for GSHHG Release cache and Shanghai coastal site data contract."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from scripts.s2g import gshhg_v237_cache as coast
from scripts.s2g import glc_fcs30d_shanghai_acquire as site

ROOT=Path(__file__).resolve().parents[3]

class TestPinnedGshhg(unittest.TestCase):
    def test_official_archived_sha_and_reproducible_restore_sources(self):
        self.assertEqual(coast.SHA256,"8dbbe7e071e77e9e75f2d639239099ebca8d5c16d6a07df8169729d49f15cf41")
        self.assertEqual(coast.L1_SHA256,"121435427911ea80624802e0f352d777eaf6ba6966ca5f07e687650e95329fd9")
        self.assertEqual(coast.EXTENSIONS,(".shp",".shx",".dbf",".prj"))
        self.assertTrue(coast.RELEASE.startswith("https://github.com/RRain001/CTEAS-next/releases/download/"))
        self.assertTrue(coast.OFFICIAL.startswith("https://github.com/GenericMappingTools/gshhg-gmt/releases/download/"))
    def test_invalid_archive_never_accepted_from_cache(self):
        with tempfile.TemporaryDirectory() as d:
            z=Path(d)/coast.NAME
            z.write_bytes(b"not official GSHHG")
            with self.assertRaisesRegex(ValueError,"GSHHG_ARCHIVE_SHA256_MISMATCH"):
                coast.valid_zip(z)
            with self.assertRaises(ValueError):
                coast.verify(Path(d))
    def test_empty_cache_fails_closed_without_network(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError):
                coast.verify(Path(d))

class TestShanghaiCandidate(unittest.TestCase):
    def test_coastal_site_grid_contract(self):
        self.assertEqual(site.ZONE,32651)
        self.assertEqual((site.NX,site.NY), (50,50))
        self.assertEqual((site.X0,site.Y0,site.STEP),(400655.,3485184.,100.))
        self.assertEqual(site.GRID,[400655.,3485184.,405655.,3490184.])
        self.assertEqual(site.YEAR,2022)
        self.assertEqual(site.BAND,"b23")
        self.assertIn("GLC-FCS30D/annual",site.ASSET)
        wgs=site.corners(site.GRID)
        self.assertEqual(len(wgs),4)
        self.assertTrue(all(121.8<x<122.2 and 31.3<y<31.8 for x,y in wgs))
    def test_source_missing_fails_without_any_eecalls(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(FileNotFoundError):
                site.verify(Path(d))
    def test_no_real_data_claim_is_committed(self):
        self.assertFalse((site.DEFAULT/site.NAME).exists(),
            "If genuine Shanghai TIFF is added, update scope to actual test result.")

class TestManualOnlyWorkflows(unittest.TestCase):
    def test_both_data_workflows_cannot_start_on_pull_request(self):
        try:
            import yaml
        except ModuleNotFoundError:
            self.skipTest("PyYAML unavailable in bare local Python")
        paths=[".github/workflows/issue53-gshhg-publish-project-release.yml",
               ".github/workflows/issue46-p2b-shanghai-real-coastal-2022.yml"]
        for p in paths:
            doc=yaml.safe_load((ROOT/p).read_text())
            events=doc.get("on",doc.get(True))
            self.assertEqual(events,{"workflow_dispatch":None})
    def test_no_secret_earth_engine_in_ci(self):
        text=(ROOT/".github/workflows/issue46-p2b-shanghai-real-coastal-2022.yml").read_text()
        self.assertNotIn("ee.Initialize",text)
        self.assertNotIn("secrets.",text)
        self.assertIn("BLOCKED_REAL_SHANGHAI_GLC2022_NOT_PRESENT",text)

if __name__=="__main__":
    unittest.main()
