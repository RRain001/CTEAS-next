"""Fail-closed isolated tests for fourth-hour native COMP trace comparator."""
import struct
import tempfile
from pathlib import Path
import unittest

from scripts.s4.s4r1c9x_compare_hour4_comp15 import (
    native_decode, audit, FIELDS, HEADER, NC, NX, NY, NZ
)


class Hour4CompAuditTests(unittest.TestCase):
    def stage12(self, hour=5, stage=12):
        return HEADER.pack(hour, stage, NX, NY, NZ) + (
            struct.pack("<" + str(NC * len(FIELDS[12])) + "f",
                        *([0.0] * (NC * len(FIELDS[12]))))
        )

    def test_valid_stage12_trace_has_no_trailing_bytes(self):
        self.assertEqual(list(native_decode(self.stage12(),
                                            stage_count=1)), [12])

    def test_wrong_hour_rejected(self):
        with self.assertRaisesRegex(ValueError, "clock"):
            native_decode(self.stage12(hour=4), stage_count=1)

    def test_wrong_stage_rejected(self):
        with self.assertRaisesRegex(ValueError, "stage"):
            native_decode(self.stage12(stage=13), stage_count=1)

    def test_truncation_and_trailing_rejected(self):
        for data in (self.stage12()[:-1], self.stage12() + b"\x00"):
            with self.assertRaises(ValueError):
                native_decode(data, stage_count=1)

    def test_unsupported_stage_count_rejected(self):
        with self.assertRaises(ValueError):
            native_decode(self.stage12(), stage_count=2)

    def test_nonfinite_rejected(self):
        data = bytearray(self.stage12())
        struct.pack_into("<f", data, HEADER.size, float("nan"))
        with self.assertRaisesRegex(ValueError, "nonfinite"):
            native_decode(bytes(data), stage_count=1)

    def test_identity_alias_rejected_before_file_read(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "same.bin"
            with self.assertRaisesRegex(ValueError, "alias"):
                audit(p, p, "0" * 64, stage_count=1)


if __name__ == "__main__":
    unittest.main()
