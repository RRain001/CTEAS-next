"""Small parser/comparator negative controls, not physical equivalence."""
import struct
import unittest

from scripts.s4.s4r1c9n_compare_hour3_g22_trace import (
    compare_words, extract, compare, NC, NZ,
)
from scripts.s4.s4r1c9l_original_g22_trace import STAGE_ARRAYS


class TestG66Audit(unittest.TestCase):
    def test_bitwise_equal(self):
        raw = struct.pack("<" + str(NC) + "f", *([1.5] * NC))
        self.assertEqual(compare_words(raw, raw, 1, 0, {0})["bitwise_equal"], NC)

    def test_one_bit_change_rejected(self):
        original = struct.pack("<" + str(NC) + "f", *([1.0] * NC))
        native = bytearray(original)
        struct.pack_into("<I", native, 0, struct.unpack_from("<I", original)[0] + 1)
        result = compare_words(original, bytes(native), 1, 0, {0})
        self.assertEqual(result["bitwise_unequal"], 1)
        self.assertEqual(result["water_bitwise_unequal"], 1)

    def test_nonfinite_rejected(self):
        with self.assertRaisesRegex(ValueError, "nonfinite"):
            compare_words(struct.pack("<" + str(NC) + "f", *([float("nan")] * NC)),
                          b"\0" * (4 * NC), 1, 0, {0})

    def test_length_rejected(self):
        with self.assertRaisesRegex(ValueError, "length"):
            compare_words(b"\x00", b"\x00", 1, 0, {0})

    def test_wrong_header_rejected(self):
        with self.assertRaisesRegex(ValueError, "wrong hour"):
            extract(struct.pack("<5i", 3, 82, 85, 9, 10), (4,))

    def test_truncated_header_rejected(self):
        with self.assertRaisesRegex(ValueError, "truncated header"):
            extract(b"\x00" * 10, (4,))

    def test_truncated_payload_rejected(self):
        with self.assertRaisesRegex(ValueError, "truncated REAL4"):
            extract(struct.pack("<5i", 4, 82, 85, 9, 10), (4,))

    def test_trailing_bytes_rejected(self):
        b = bytearray()
        for stage, fields in STAGE_ARRAYS.items():
            b += struct.pack("<5i", 4, 82, 85, 9, stage)
            b += b"\0" * (NC * (NZ if stage == 50 else 1) * len(fields) * 4)
        self.assertEqual(len(extract(bytes(b), (4,))), 1)
        with self.assertRaisesRegex(ValueError, "trailing"):
            extract(bytes(b) + b"x", (4,))

    def test_missing_water_mask_rejected(self):
        with self.assertRaisesRegex(ValueError, "WATER mask"):
            compare({}, {}, set())

    def test_pre_registered_tolerances_are_fixed(self):
        from scripts.s4.s4r1c9n_compare_hour3_g22_trace import frozen_limit
        self.assertEqual(frozen_limit("temp2d", 300), 0.001)
        self.assertEqual(frozen_limit("qsw", 300), 0.005)
        self.assertEqual(frozen_limit("qh", 300), 0.25)
        self.assertEqual(frozen_limit("rho", 1.2), 0.0001)
        self.assertEqual(frozen_limit("ustar", 0.3), 0.005)
        self.assertEqual(frozen_limit("el", -100), 1.0)
        self.assertEqual(frozen_limit("uslope", 0.5), 0.0002)
        with self.assertRaisesRegex(ValueError, "unregistered"):
            frozen_limit("arbitrary", 1.0)

    def test_one_ulp_within_registered_temperature_limit(self):
        orig = struct.pack("<" + str(NC) + "f", *([300.0] * NC))
        native = bytearray(orig)
        struct.pack_into("<I", native, 0, struct.unpack_from("<I", orig)[0] + 1)
        stats = compare_words(orig, bytes(native), 1, 0, {0}, "temp2d")
        self.assertEqual(stats["bitwise_unequal"], 1)
        self.assertEqual(stats["frozen_tolerance_exceedances"], 0)

    def test_water_history_one_ulp_rejected_even_if_within_tolerance(self):
        b = bytearray()
        for stage, fields in STAGE_ARRAYS.items():
            b += struct.pack("<5i", 4, 82, 85, 9, stage)
            b += bytes([0]) * (NC * (NZ if stage == 50 else 1) * len(fields) * 4)
        orig = extract(bytes(b), (4,))[4]
        nat = dict(orig)
        mutated = bytearray(nat[40])
        # 1-ULP difference in WATER USTAR: numerically tiny, but native
        # previous-hour state must be bitwise identical to original carry.
        struct.pack_into("<I", mutated, 4, 1)
        nat[40] = bytes(mutated)
        res = compare(orig, nat, set(range(63)))
        self.assertEqual(res["frozen_tolerance_exceedances"], 0)
        self.assertFalse(res["water_ustar_el_native_history_bitwise_equal"])
        self.assertEqual(res["status"], "FAIL_FROZEN_G22_INTERMEDIATES")

    def test_one_field_difference_not_pass(self):
        b = bytearray()
        for stage, fields in STAGE_ARRAYS.items():
            b += struct.pack("<5i", 4, 82, 85, 9, stage)
            b += b"\0" * (NC * (NZ if stage == 50 else 1) * len(fields) * 4)
        orig = extract(bytes(b), (4,))[4]
        nat = dict(orig)
        mutated = bytearray(nat[40])
        struct.pack_into("<f", mutated, 4, 1.0)
        nat[40] = bytes(mutated)
        res = compare(orig, nat, set(range(63)))
        self.assertEqual(res["status"], "FAIL_FROZEN_G22_INTERMEDIATES")
        self.assertEqual(res["frozen_tolerance_exceedances"], 1)
        self.assertEqual(res["fields"]["40:ustar"]["water_bitwise_unequal"], 1)


if __name__ == "__main__":
    unittest.main()
