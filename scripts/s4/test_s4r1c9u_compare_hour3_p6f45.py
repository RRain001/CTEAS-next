"""Fail-closed independent CALMET hour3 comparator software-only tests."""
from __future__ import annotations
import math
import struct
import unittest
from scripts.s4 import s4r1c9u_compare_hour3_p6f45 as m


class TestP6F45(unittest.TestCase):
    def test_original_met_pin_present(self):
        self.assertEqual(len(m.ORIGINAL_MET_SHA), 64)

    def test_45_labels(self):
        self.assertEqual(len(m.LABELS), 45)

    def test_hour3_utc(self):
        self.assertEqual(m.THIRD_UTC, m.FIRST_UTC + 2)

    def test_frozen_wind_tolerance(self):
        self.assertEqual(m.tol("U-LEV 1 ", 1.0, 1.0), 2e-4)

    def test_frozen_mixht_tolerance(self):
        self.assertAlmostEqual(m.tol("ZI      ", 1000.0, 1000.0), 0.055)

    def test_bad_header_rejected(self):
        with self.assertRaisesRegex(ValueError, "declaration"):
            m.decode(b"", False)

    def test_bad_label_cardinality_rejected(self):
        with self.assertRaisesRegex(ValueError, "missing 45-field"):
            m.compare({}, {})

    def test_exact_real_and_integer_45fields(self):
        values = {}
        for label in m.LABELS:
            if label in ("IPGT    ", "IRH     "):
                values[label] = struct.pack("<" + str(m.NC) + "i",
                                            *([4] * m.NC))
            else:
                values[label] = struct.pack("<" + str(m.NC) + "f",
                                            *([1.0] * m.NC))
        result = m.compare(values, values)
        self.assertEqual(result["compared_values"], 45 * m.NC)
        self.assertEqual(result["frozen_tolerance_or_integer_exceedances"], 0)

    def test_integer_mismatch_rejected(self):
        values = {}
        for label in m.LABELS:
            values[label] = ((struct.pack("<i", 4) * m.NC)
                             if label in ("IPGT    ", "IRH     ")
                             else struct.pack("<f", 1.0) * m.NC)
        bad = dict(values)
        buf = bytearray(values["IPGT    "])
        struct.pack_into("<i", buf, 0, 5)
        bad["IPGT    "] = bytes(buf)
        result = m.compare(values, bad)
        self.assertEqual(result["frozen_tolerance_or_integer_exceedances"], 1)

    def test_nonfinite_rejected(self):
        values = {}
        for label in m.LABELS:
            values[label] = ((struct.pack("<i", 4) * m.NC)
                             if label in ("IPGT    ", "IRH     ")
                             else struct.pack("<f", 1.0) * m.NC)
        bad = dict(values)
        buf = bytearray(values["USTAR   "])
        struct.pack_into("<f", buf, 0, math.nan)
        bad["USTAR   "] = bytes(buf)
        with self.assertRaisesRegex(ValueError, "nonfinite"):
            m.compare(values, bad)


if __name__ == "__main__":
    unittest.main()
