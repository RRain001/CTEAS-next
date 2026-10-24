"""Tests SHA freeze and independent two-hour file admission."""
import tempfile
from pathlib import Path
import unittest
from scripts.s4.s4c_compare_noaa_unified_twohour import audit,native_two_hours,digest

class TwoHourAuditTest(unittest.TestCase):
    def test_reject_same_or_occupied_original_report(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);one=root/'original';two=root/'native';report=root/'report'
            one.write_bytes(b'a');two.write_bytes(b'b')
            with self.assertRaisesRegex(ValueError,'independent originals'):
                audit(one,one,digest(one),digest(one),report)
            report.write_text('keep')
            with self.assertRaisesRegex(ValueError,'independent originals'):
                audit(one,two,digest(one),digest(two),report)
            self.assertEqual(report.read_text(),'keep')
    def test_reject_wrong_sha_before_parse(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);one=root/'original';two=root/'native';report=root/'report'
            one.write_bytes(b'one');two.write_bytes(b'two')
            with self.assertRaisesRegex(ValueError,'frozen original/native SHA'):
                audit(one,two,digest(one),'0'*64,report)
            self.assertFalse(report.exists())
    def test_reject_wrong_native_format(self):
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp)/'bad.dat';p.write_bytes(b'garbage')
            with self.assertRaises(ValueError):
                native_two_hours(p)

if __name__=='__main__':
    unittest.main()
