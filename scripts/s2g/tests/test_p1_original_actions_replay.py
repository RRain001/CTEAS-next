"""No original proprietary source in PR tests; verify fail-closed evidence runner."""
import tempfile
import unittest
from pathlib import Path
from scripts.s2g.p1_original_actions_replay import (
    ORIGINAL_REV,OriginalReplayError,validate_original_checkout,hash_file,
    StringCode,VENDOR_REL
)

class OriginalReplaySourceContract(unittest.TestCase):
    def test_frozen_cteas_commit_exact(self):
        self.assertEqual(ORIGINAL_REV,"dfad99a78ed84d655e21411c9d25eb0d2583bf13")
        self.assertIn("engine.preprocess.terrel.auto_select_srtm_to_terrel",
                      StringCode.UPDATE_CONTROL)
        self.assertIn("update_terrel(",StringCode.UPDATE_CONTROL)

    def test_invalid_vendor_source_refused(self):
        with tempfile.TemporaryDirectory() as t:
            with self.assertRaises(OriginalReplayError):
                validate_original_checkout(Path(t))
            vendor=Path(t)/VENDOR_REL
            vendor.mkdir(parents=True)
            for name in ("terrel.for","terrel.inp","CONTROL.TRL",
                         "CALUTILS.FOR","COORDLIB.FOR","tiffinfo.for"):
                (vendor/name).write_text("A"*500)
            with self.assertRaisesRegex(OriginalReplayError,"version"):
                validate_original_checkout(Path(t))

    def test_versioned_real_source_fixture_only(self):
        with tempfile.TemporaryDirectory() as t:
            vendor=Path(t)/VENDOR_REL
            vendor.mkdir(parents=True)
            for name in ("terrel.for","terrel.inp","CONTROL.TRL",
                         "CALUTILS.FOR","COORDLIB.FOR","tiffinfo.for"):
                (vendor/name).write_text("A"*500)
            (vendor/"terrel.for").write_text("TERREL 7.0.0 Level 141010 "+"x"*500)
            self.assertEqual(validate_original_checkout(Path(t)),vendor)

    def test_nonexistent_or_symlink_sha_refused(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t)
            with self.assertRaises(OriginalReplayError):
                hash_file(root/"nonexistent.for")
            real=root/"original.for"
            real.write_bytes(b"hello")
            link=root/"alias.for"
            link.symlink_to(real)
            with self.assertRaises(OriginalReplayError):
                hash_file(link)

if __name__=="__main__":
    unittest.main()
