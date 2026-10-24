"""Frozen source SHA and strict original/native separation checks."""
import tempfile
from pathlib import Path
import unittest
from scripts.s4.s4c_compare_noaa_unified_threehour import audit,native_three_hours,digest

class ThreeHourAuditGates(unittest.TestCase):
    def test_original_native_distinct_unoccupied_report(self):
        with tempfile.TemporaryDirectory() as work:
            r=Path(work);a=r/'ref';b=r/'native';report=r/'result'
            a.write_bytes(b'one');b.write_bytes(b'two')
            with self.assertRaisesRegex(ValueError,'independent original/native'):
                audit(a,a,digest(a),digest(a),report)
            report.write_text('preserve')
            with self.assertRaisesRegex(ValueError,'independent original/native'):
                audit(a,b,digest(a),digest(b),report)
            self.assertEqual(report.read_text(),'preserve')
    def test_sha_freeze_rejects_before_reference_decoding(self):
        with tempfile.TemporaryDirectory() as work:
            r=Path(work);a=r/'ref';b=r/'native';report=r/'result'
            a.write_bytes(b'one');b.write_bytes(b'two')
            with self.assertRaisesRegex(ValueError,'frozen original/native SHA'):
                audit(a,b,'0'*64,digest(b),report)
            self.assertFalse(report.exists())
    def test_invalid_native_three_hour_format(self):
        with tempfile.TemporaryDirectory() as work:
            p=Path(work)/'bad.met';p.write_bytes(b'garbage')
            with self.assertRaises(ValueError):native_three_hours(p)

if __name__=='__main__':unittest.main()
