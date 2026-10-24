"""Synthetic parser/negative tests; never scientific original-model evidence."""
import struct
import tempfile
import unittest
from pathlib import Path
from scripts.s4.s4r1c8i_compare_noaa_43_real_p6f import LABELS, NC
from scripts.s4.s4r1c9z_compare_hour4_p6f45 import read_hour, compare, digest


def record(payload):
    n = len(payload)
    return struct.pack("<i", n) + payload + struct.pack("<i", n)


def synthetic_met(hours, native_bad_integer=False, bad_clock=False):
    head=bytearray(176)
    struct.pack_into("<5i", head, 48, hours, 1, 82, 85, 9)
    struct.pack_into("<4i", head, 80, 1, 2, 1, 0)
    content=[record(b"CALMET.DAT".ljust(96, b" ")),
             record(struct.pack("<i", 0)), record(head)]
    zero=b"\x00"*(4*NC)
    for h in range(hours):
        clock=202215201+(h if hours==6 else 3)
        if bad_clock and h==0:
            clock-=1
        for label in LABELS:
            vals=bytearray(zero)
            if native_bad_integer and label=="IPGT    ":
                struct.pack_into("<i", vals, 0, 1)
            content.append(record(
                label.encode("ascii") + struct.pack(
                    "<4i", clock, 0, clock, 3600) + vals
            ))
    return b"".join(content)


class FourthHourCompareTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.orig=self.root/"original_met.dat"
        self.calc=self.root/"native_candidate.dat"
        self.report=self.root/"result.json"
        self.orig.write_bytes(synthetic_met(6))
        self.calc.write_bytes(synthetic_met(1))

    def test_full_45_field_structure(self):
        got=read_hour(self.orig, 6)
        calc=read_hour(self.calc, 1)
        self.assertEqual(list(got), LABELS)
        self.assertEqual(got,calc)

    def test_synthetic_equal_values_are_not_scientific_acceptance(self):
        result=compare(self.orig,self.calc,digest(self.orig),
                       digest(self.calc),self.report)
        self.assertEqual(result["compared_values"],313650)
        self.assertEqual(result["bitwise_equal"],313650)
        self.assertEqual(result["frozen_tolerance_or_integer_exceedances"],0)
        self.assertEqual(result["generic_p6"],"NOT_ACCEPTED")
        self.assertEqual(result["independent_science_review"],"NOT_RUN")

    def test_original_sha_pin_rejects_mutation(self):
        with self.assertRaisesRegex(ValueError,"SHA256"):
            compare(self.orig,self.calc,"0"*64,digest(self.calc),self.report)
        self.assertFalse(self.report.exists())

    def test_wrong_hour_rejected(self):
        self.calc.write_bytes(synthetic_met(1,bad_clock=True))
        with self.assertRaisesRegex(ValueError,"clock"):
            read_hour(self.calc,1)

    def test_integer_field_difference_fails_closed(self):
        self.calc.write_bytes(synthetic_met(1,native_bad_integer=True))
        result=compare(self.orig,self.calc,digest(self.orig),
                       digest(self.calc),self.report)
        self.assertEqual(result["frozen_tolerance_or_integer_exceedances"],1)
        self.assertEqual(result["status"],"FAIL_HOUR4_ORIGINAL_NATIVE_P6F45")
        self.assertEqual(result["fields"]["IPGT"]["frozen_exceedances"],1)

    def test_report_is_never_overwritten(self):
        self.report.write_text("previous audit\n")
        with self.assertRaisesRegex(ValueError,"must not exist"):
            compare(self.orig,self.calc,digest(self.orig),
                    digest(self.calc),self.report)
        self.assertEqual(self.report.read_text(),"previous audit\n")


if __name__=="__main__":
    unittest.main()
