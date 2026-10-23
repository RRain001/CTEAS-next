"""Synthetic COMP stage12 format and frozen tolerance regressions only."""
from __future__ import annotations
import math
import struct
import unittest
from scripts.s4 import s4r1c9s_compare_hour3_comp12 as m


class TestComp12(unittest.TestCase):
    def setUp(self):
        self.raw = m.HEADER.pack(4, 12, m.NX, m.NY, m.NZ) + (
            struct.pack("<f", 1.0) * (len(m.FIELDS) * m.NC))

    def test_decode_shape(self):
        self.assertEqual(len(m.native_decode(self.raw)), 7 * m.NC)

    def test_wrong_clock(self):
        raw = bytearray(self.raw)
        struct.pack_into("<i", raw, 0, 5)
        with self.assertRaisesRegex(ValueError, "clock"):
            m.native_decode(raw)

    def test_wrong_stage(self):
        raw = bytearray(self.raw)
        struct.pack_into("<i", raw, 4, 13)
        with self.assertRaisesRegex(ValueError, "clock"):
            m.native_decode(raw)

    def test_truncation(self):
        with self.assertRaisesRegex(ValueError, "shape"):
            m.native_decode(self.raw[:-4])

    def test_trailing_bytes(self):
        with self.assertRaisesRegex(ValueError, "shape"):
            m.native_decode(self.raw + b"\x00")

    def test_nonfinite(self):
        raw = bytearray(self.raw)
        struct.pack_into("<f", raw, m.HEADER.size, math.nan)
        with self.assertRaisesRegex(ValueError, "nonfinite"):
            m.native_decode(raw)

    def test_frozen_wind_limit(self):
        self.assertEqual(m.limit("ustar", 0.1, 0.2), 0.005)

    def test_frozen_mixht_limit(self):
        self.assertAlmostEqual(m.limit("zi", 1000, 1000), 0.055)

    def test_frozen_el_limit(self):
        self.assertEqual(m.limit("el", 1000, 1001), 10)

    def test_unknown_limit_rejected(self):
        with self.assertRaisesRegex(ValueError, "unregistered"):
            m.limit("unregistered", 0, 0)

    def test_exact_equal(self):
        a = (1.0,) * (7 * m.NC)
        result = m.compare(a, a)
        self.assertEqual(result["frozen_exceedances"], 0)
        self.assertEqual(result["bitwise_equal"], 7 * m.NC)

    def test_out_of_tolerance_rejected(self):
        a = (1.0,) * (7 * m.NC)
        b = list(a)
        b[5 * m.NC] = 1.1
        result = m.compare(a, tuple(b))
        self.assertEqual(result["frozen_exceedances"], 1)
        self.assertEqual(result["fields"]["ustar"]["frozen_exceedances"], 1)


if __name__ == "__main__":
    unittest.main()
