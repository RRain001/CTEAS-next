"""Frozen source SHA and strict original/native separation checks."""
import tempfile
from pathlib import Path
import unittest
from scripts.s4.s4c_compare_noaa_unified_threehour import audit,native_three_hours,native_prefix_hours,digest

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
    def test_prefix_gate_rejects_out_of_range_without_reading(self):
        with tempfile.TemporaryDirectory() as work:
            p=Path(work)/'no.dat'
            for hours in (0,1,2,7,12):
                with self.assertRaisesRegex(ValueError,'only 3..6h'):
                    native_prefix_hours(p,hours)

    def test_fourhour_sha_rejects_before_decode(self):
        with tempfile.TemporaryDirectory() as work:
            r=Path(work);a=r/'orig';b=r/'native';report=r/'result'
            a.write_bytes(b'original');b.write_bytes(b'native')
            with self.assertRaisesRegex(ValueError,'frozen original/native SHA'):
                audit(a,b,digest(a),'0'*64,report,4)
            self.assertFalse(report.exists())

    def test_fivehour_sha_rejects_before_decode(self):
        with tempfile.TemporaryDirectory() as work:
            r=Path(work);a=r/'orig';b=r/'native';report=r/'result'
            a.write_bytes(b'original');b.write_bytes(b'native')
            with self.assertRaisesRegex(ValueError,'frozen original/native SHA'):
                audit(a,b,digest(a),'0'*64,report,5)
            self.assertFalse(report.exists())

    def test_invalid_native_three_hour_format(self):
        with tempfile.TemporaryDirectory() as work:
            p=Path(work)/'bad.met';p.write_bytes(b'garbage')
            with self.assertRaises(ValueError):native_three_hours(p)

if __name__=='__main__':unittest.main()
