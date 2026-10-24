"""Synthetic parser/negative tests only; not an original/native physics PASS."""
from __future__ import annotations
import math
from pathlib import Path
import struct
import tempfile
import unittest
from scripts.s4 import s4r1c9r_original_hour3_comp_trace as m


def payload(hour: int, stage: int) -> bytes:
    count = m.NC * (m.NZ if stage == 15 else len(m.FIELDS[stage]))
    return m.HEADER.pack(hour, stage, m.NX, m.NY, m.NZ) + (
        struct.pack("<f", 280.0) * count)


class TestCompStageParser(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "stages.bin"
        self.data = b"".join(payload(hour, stage)
                             for hour in range(2, 8)
                             for stage in m.FIELDS)
        self.path.write_bytes(self.data)

    def test_all_hours_and_stages(self):
        result = m.decode(self.path)
        self.assertEqual(len(result), 24)
        self.assertEqual(len(result[(4, 12)]), 7 * m.NC)
        self.assertEqual(len(result[(4, 15)]), 9 * m.NC)

    def test_wrong_hour(self):
        data = bytearray(self.data)
        struct.pack_into("<i", data, 0, 3)
        self.path.write_bytes(data)
        with self.assertRaisesRegex(ValueError, "clock mismatch"):
            m.decode(self.path)

    def test_wrong_stage(self):
        data = bytearray(self.data)
        struct.pack_into("<i", data, 4, 13)
        self.path.write_bytes(data)
        with self.assertRaisesRegex(ValueError, "stage/clock mismatch"):
            m.decode(self.path)

    def test_wrong_grid(self):
        data = bytearray(self.data)
        struct.pack_into("<i", data, 8, 81)
        self.path.write_bytes(data)
        with self.assertRaisesRegex(ValueError, "stage/clock mismatch"):
            m.decode(self.path)

    def test_truncated_header(self):
        self.path.write_bytes(b"\x00" * 19)
        with self.assertRaisesRegex(ValueError, "truncated"):
            m.decode(self.path)

    def test_truncated_last_field(self):
        self.path.write_bytes(self.data[:-4])
        with self.assertRaisesRegex(ValueError, "truncated"):
            m.decode(self.path)

    def test_trailing_data(self):
        self.path.write_bytes(self.data + b"x")
        with self.assertRaisesRegex(ValueError, "trailing"):
            m.decode(self.path)

    def test_nonfinite_rejected(self):
        data = bytearray(self.data)
        struct.pack_into("<f", data, m.HEADER.size, math.nan)
        self.path.write_bytes(data)
        with self.assertRaisesRegex(ValueError, "nonfinite"):
            m.decode(self.path)

    def test_temperature_range_rejected(self):
        data = bytearray(self.data)
        off = 0
        for stage in (12, 13, 14):
            off += m.HEADER.size + 4 * m.NC * len(m.FIELDS[stage])
        struct.pack_into("<f", data, off + m.HEADER.size, 100.0)
        self.path.write_bytes(data)
        with self.assertRaisesRegex(ValueError, "TEMP3D"):
            m.decode(self.path)

    def test_wrong_original_met_sha_rejected(self):
        fake_met = Path(self.tmp.name) / "met.dat"
        fake_met.write_bytes(b"not original")
        with self.assertRaisesRegex(ValueError, "differs"):
            m.audit(self.path, fake_met)

    def test_original_source_sha_rejected(self):
        fake_source = Path(self.tmp.name) / "calmet.for"
        fake_source.write_text("subroutine fake\n")
        with self.assertRaisesRegex(ValueError, "source SHA drift"):
            m.prepare(fake_source, Path(self.tmp.name) / "instrumented.for")


if __name__ == "__main__":
    unittest.main()
