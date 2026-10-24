"""S4-C original/native independent comparison evidence fail-close tests."""
import tempfile
from pathlib import Path
import unittest
from scripts.s4.s4c_compare_noaa_unified_firsthour import audit, digest

class FirsthourAuditGate(unittest.TestCase):
    def test_forbid_same_file_and_existing_report(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            raw=root/'met.dat';raw.write_bytes(b'a')
            other=root/'trial.dat';other.write_bytes(b'b')
            report=root/'audit.json'
            with self.assertRaisesRegex(ValueError,'Original and native must differ'):
                audit(raw,raw,digest(raw),digest(raw),report)
            self.assertFalse(report.exists())
            report.write_text('preserve')
            with self.assertRaisesRegex(ValueError,'Original and native must differ'):
                audit(raw,other,digest(raw),digest(other),report)
            self.assertEqual(report.read_text(),'preserve')

    def test_frozen_sha_mismatch_rejected_before_decode(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            raw=root/'met.dat';raw.write_bytes(b'original')
            other=root/'trial.dat';other.write_bytes(b'native')
            report=root/'audit.json'
            with self.assertRaisesRegex(ValueError,'frozen SHA256'):
                audit(raw,other,'0'*64,digest(other),report)
            self.assertFalse(report.exists())

if __name__=='__main__':
    unittest.main()
