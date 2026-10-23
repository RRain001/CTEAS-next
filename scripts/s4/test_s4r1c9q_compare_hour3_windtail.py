"""Software-only negative/format tests; no external science PASS claimed."""
from __future__ import annotations
import math
import struct
import unittest
from scripts.s4 import s4r1c9q_compare_hour3_windtail as m


def one(stage=90, hour=4, val=1.0):
    count = m.COUNTS[stage]
    return m.HEADER.pack(hour, m.NX, m.NY, m.NZ, stage) + (
        struct.pack("<f", val) * count)


class TestNativeWindTailTrace(unittest.TestCase):
    def test_three_native_stages(self):
        result = m.decode(one(90) + one(100) + one(110),
                          (4,), (90, 100, 110))
        self.assertEqual(set(result), {(4, 90), (4, 100), (4, 110)})

    def test_wrong_clock_rejected(self):
        with self.assertRaisesRegex(ValueError, "wrong source hour"):
            m.decode(one(hour=3), (4,), (90,))

    def test_wrong_stage_rejected(self):
        with self.assertRaisesRegex(ValueError, "wrong source hour"):
            m.decode(one(stage=100), (4,), (90,))

    def test_short_header_rejected(self):
        with self.assertRaisesRegex(ValueError, "truncated"):
            m.decode(b"\x00" * 19, (4,), (90,))

    def test_truncated_payload_rejected(self):
        with self.assertRaisesRegex(ValueError, "truncated"):
            m.decode(one()[:-1], (4,), (90,))

    def test_trailing_data_rejected(self):
        with self.assertRaisesRegex(ValueError, "trailing"):
            m.decode(one() + b"x", (4,), (90,))

    def test_bitwise_identical(self):
        payload = struct.pack("<f", 1.25) * m.COUNTS[90]
        stats = m.compare(payload, payload, 90)
        self.assertEqual(stats["u"]["bitwise_equal"], m.NC * m.NZ)
        self.assertEqual(stats["v"]["frozen_exceedances"], 0)

    def test_frozen_tolerance_is_strict(self):
        payload = bytearray(struct.pack("<f", 1.0) * m.COUNTS[90])
        altered = bytearray(payload)
        struct.pack_into("<f", altered, 0, 1.0003)
        stats = m.compare(payload, altered, 90)
        self.assertEqual(stats["u"]["frozen_exceedances"], 1)
        self.assertEqual(stats["v"]["frozen_exceedances"], 0)

    def test_subthreshold_difference_not_frozen_exceedance(self):
        payload = bytearray(struct.pack("<f", 1.0) * m.COUNTS[90])
        altered = bytearray(payload)
        struct.pack_into("<f", altered, 0, 1.0001)
        stats = m.compare(payload, altered, 90)
        self.assertEqual(stats["u"]["frozen_exceedances"], 0)
        self.assertEqual(stats["u"]["bitwise_equal"], m.NC * m.NZ - 1)

    def test_nan_rejected(self):
        payload = bytearray(struct.pack("<f", 1.0) * m.COUNTS[90])
        altered = bytearray(payload)
        struct.pack_into("<f", altered, 0, math.nan)
        with self.assertRaisesRegex(ValueError, "nonfinite"):
            m.compare(payload, altered, 90)

    def test_shape_rejected(self):
        with self.assertRaisesRegex(ValueError, "shape"):
            m.compare(b"x", b"x", 90)

    def test_wface_channel_size(self):
        payload = struct.pack("<f", 0.0) * m.COUNTS[110]
        stats = m.compare(payload, payload, 110)
        self.assertEqual(stats["w"]["count"], 10 * m.NC)
        self.assertEqual(stats["w"]["frozen_exceedances"], 0)


if __name__ == "__main__":
    unittest.main()
