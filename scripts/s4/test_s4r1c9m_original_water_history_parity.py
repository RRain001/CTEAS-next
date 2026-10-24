#!/usr/bin/env python3
"""No-private-input regressions for the original WATER history auditor."""
from __future__ import annotations

import struct
import unittest

from scripts.s4.s4r1c9m_original_water_history_parity import (
    NC, NX, compare_carryover, compare_native_hour2_seed,
    previous_met_water_records, stage40_water_records,
)
from scripts.s4.s4r1c9l_original_g22_trace import STAGE_ARRAYS, HEADER


class WaterHistoryTests(unittest.TestCase):
    @staticmethod
    def fixture():
        mask = set(range(63))
        zero = struct.pack("<f", 0.0)
        def vec(value: float) -> bytes:
            return struct.pack("<f", value) * NC
        met = [{"USTAR   ": vec(float(i+1)),
                "EL      ": vec(float(i+100))} for i in range(6)]
        stage = [{"ustar": vec(0.0), "el": vec(0.0)}]
        stage += [{"ustar": met[i]["USTAR   "], "el": met[i]["EL      "]}
                  for i in range(5)]
        assert len(zero) == 4
        return met, stage, mask

    def test_five_transitions_and_exact_630_words(self):
        met, stage, mask = self.fixture()
        r = compare_carryover(met, stage, mask)
        self.assertEqual(r["bitwise_compared_words"], 630)
        self.assertEqual(len(r["hourly"]), 5)
        self.assertEqual(r["native_third_hour_g22_parity"], "NOT_RUN")

    def test_single_water_ustar_bit_rejected(self):
        met, stage, mask = self.fixture()
        mutated = bytearray(stage[2]["ustar"])
        mutated[4 * 18] ^= 1
        stage[2]["ustar"] = bytes(mutated)
        with self.assertRaisesRegex(ValueError, "hour=3 ustar cell"):
            compare_carryover(met, stage, mask)

    def test_single_water_el_bit_rejected(self):
        met, stage, mask = self.fixture()
        mutated = bytearray(stage[1]["el"])
        mutated[4 * 8 + 2] ^= 1
        stage[1]["el"] = bytes(mutated)
        with self.assertRaisesRegex(ValueError, "hour=2 el cell"):
            compare_carryover(met, stage, mask)

    def test_first_hour_cold_water_state_required(self):
        met, stage, mask = self.fixture()
        stage[0]["ustar"] = met[0]["USTAR   "]
        with self.assertRaisesRegex(ValueError, "cold zero"):
            compare_carryover(met, stage, mask)

    def test_wrong_cardinality_rejected(self):
        met, stage, mask = self.fixture()
        mask.remove(62)
        with self.assertRaisesRegex(ValueError, "hour/water count"):
            compare_carryover(met, stage, mask)

    def test_trace_clock_and_truncation_fail_closed(self):
        water = set(range(63))
        def stage_payload(stage, fields):
            if stage == 40:
                vals = []
                for i in range(NC):
                    vals.extend((0.0 if i in water else 1.0, 0.0, 0.0))
                return struct.pack("<" + str(len(vals)) + "f", *vals)
            count = NC * (9 if stage == 50 else 1) * len(fields)
            return b"\x00" * (count * 4)
        parts = []
        for hour in range(2, 8):
            for stage, fields in STAGE_ARRAYS.items():
                parts.append(HEADER.pack(hour, NX, 85, 9, stage))
                parts.append(stage_payload(stage, fields))
        valid = b"".join(parts)
        self.assertEqual(len(stage40_water_records(valid, water)), 6)
        with self.assertRaisesRegex(ValueError, "truncated"):
            stage40_water_records(valid[:-1], water)
        broken = bytearray(valid)
        struct.pack_into("<i", broken, 0, 5)
        with self.assertRaisesRegex(ValueError, "clock drift"):
            stage40_water_records(bytes(broken), water)

    def test_native_hour2_seed_matches_original_hour3_126_words(self):
        met, stage, water = self.fixture()
        native = {"USTAR   ": met[1]["USTAR   "],
                  "EL      ": met[1]["EL      "]}
        result = compare_native_hour2_seed(native, stage[2], water)
        self.assertEqual(result["words_compared"], 126)
        self.assertEqual(result["bitwise_equal_words"], 126)
        self.assertEqual(result["fields"]["ustar"]["max_abs"], 0.0)
        self.assertFalse(result["native_g22_hour3_computed"])

    def test_native_hour2_seed_science_exceedance_rejected(self):
        met, stage, water = self.fixture()
        native = {"USTAR   ": met[1]["USTAR   "],
                  "EL      ": met[1]["EL      "]}
        altered = bytearray(native["USTAR   "])
        struct.pack_into("<f", altered, 12 * 4, 1234.0)
        native["USTAR   "] = bytes(altered)
        with self.assertRaisesRegex(ValueError, "frozen tolerance"):
            compare_native_hour2_seed(native, stage[2], water)

    def test_native_hour2_seed_nonfinite_rejected(self):
        met, stage, water = self.fixture()
        native = {"USTAR   ": met[1]["USTAR   "],
                  "EL      ": met[1]["EL      "]}
        altered = bytearray(native["EL      "])
        struct.pack_into("<f", altered, 8 * 4, float("nan"))
        native["EL      "] = bytes(altered)
        with self.assertRaisesRegex(ValueError, "nonfinite"):
            compare_native_hour2_seed(native, stage[2], water)

    def test_met_decoder_rejects_empty_and_corrupt(self):
        with self.assertRaises(ValueError):
            previous_met_water_records(b"")
        with self.assertRaises(ValueError):
            previous_met_water_records(b"\x00" * 128)


if __name__ == "__main__":
    unittest.main()
