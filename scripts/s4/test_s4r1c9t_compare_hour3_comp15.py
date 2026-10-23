"""Software-only schema and frozen-tolerance negative tests."""
from __future__ import annotations
import math
import struct
import unittest
from scripts.s4 import s4r1c9t_compare_hour3_comp15 as m


def synthetic() -> bytes:
    raw = bytearray()
    for stage, fields in m.FIELDS.items():
        count = m.NC * (m.NZ if stage == 15 else len(fields))
        raw.extend(m.HEADER.pack(4, stage, m.NX, m.NY, m.NZ))
        raw.extend(struct.pack("<f", 1.0) * count)
    return bytes(raw)


class TestComp15(unittest.TestCase):
    def setUp(self):
        self.raw = synthetic()

    def test_decode_stages(self):
        result = m.native_decode(self.raw)
        self.assertEqual(list(result), [12, 13, 14, 15])

    def test_wrong_clock(self):
        b = bytearray(self.raw)
        struct.pack_into("<i", b, 0, 5)
        with self.assertRaisesRegex(ValueError, "clock"):
            m.native_decode(b)

    def test_truncated(self):
        with self.assertRaisesRegex(ValueError, "truncated"):
            m.native_decode(self.raw[:-4])

    def test_trailing(self):
        with self.assertRaisesRegex(ValueError, "trailing"):
            m.native_decode(self.raw + b"\x00")

    def test_nonfinite(self):
        b = bytearray(self.raw)
        struct.pack_into("<f", b, m.HEADER.size, math.nan)
        with self.assertRaisesRegex(ValueError, "nonfinite"):
            m.native_decode(b)

    def test_exact_equal(self):
        n = m.NC * m.NZ
        a = (290.0,) * n
        result = m.compare_stage(15, a, a)
        self.assertEqual(result["frozen_exceedances"], 0)
        self.assertEqual(result["bitwise_equal"], n)

    def test_temp_frozen_exceedance(self):
        n = m.NC * m.NZ
        a = (290.0,) * n
        b = list(a)
        b[0] = 290.001
        result = m.compare_stage(15, a, tuple(b))
        self.assertEqual(result["frozen_exceedances"], 1)

    def test_wstar_frozen_exceedance(self):
        a = (0.5,) * m.NC
        b = list(a)
        b[0] = 0.501
        result = m.compare_stage(14, a, tuple(b))
        self.assertEqual(result["frozen_exceedances"], 1)

    def test_stage13_shape(self):
        with self.assertRaisesRegex(ValueError, "size"):
            m.compare_stage(13, (1.0,), (1.0,))


if __name__ == "__main__":
    unittest.main()
