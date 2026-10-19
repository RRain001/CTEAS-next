"""#123 D6-A offline synthetic tests: no original source or scientific parity."""
from __future__ import annotations

import io
from pathlib import Path
import struct
import tempfile
import unittest

from scripts.s2g import issue123_original_full_header_screen as screen


def poly(identifier=0, *, points=3, level=1, area=123,
         west=129_350_000, east=129_600_000,
         south=35_550_000, north=35_900_000, version=15):
    flag = level | (version << 8)
    header = struct.pack(">11i", identifier, points, flag, west,
                         east, south, north, area, area, -1, -1)
    return header + struct.pack(">" + "ii" * points, *([0, 0] * points))


class TestOriginalFullHeaderScreen(unittest.TestCase):
    def test_realistic_full_header_and_wolsong_candidates(self):
        b = poly(0) + poly(1, west=80_000_000, east=90_000_000) + poly(
            2, points=0, area=0) + poly(3, level=2, south=34_000_000, north=35_000_000)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "gshhs_f.b"
            path.write_bytes(b)
            report = screen.scan_binary(path)
        self.assertEqual(report["polygon_count"], 4)
        self.assertEqual(report["candidate_bbox_count"], 1)
        self.assertEqual(report["zero_area_count"], 1)
        self.assertEqual(report["candidate_sample"][0]["id"], 0)
        self.assertEqual(report["scanned_bytes"], len(b))

    def test_malformed_or_truncated_records_are_rejected(self):
        bad = [
            b"short", poly()[:-1],
            poly(level=5), poly(version=3),
            poly(points=2), poly(south=40_000_000, north=30_000_000),
            poly() + b"xx",
        ]
        for data in bad:
            with self.subTest(length=len(data)):
                with tempfile.TemporaryDirectory() as tmp:
                    path = Path(tmp) / "bad.b"
                    path.write_bytes(data)
                    with self.assertRaisesRegex(ValueError, "D6A_"):
                        screen.scan_binary(path)

    def test_no_candidates_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "gshhs_f.b"
            path.write_bytes(poly(west=100_000_000, east=110_000_000))
            with self.assertRaisesRegex(ValueError, "NO_WOLSONG"):
                screen.scan_binary(path)

    def test_header_screen_does_not_imply_full_original_coastext(self):
        self.assertIn("NOT_COASTEXT", screen.STATUS)
        self.assertEqual(screen.WOLSONG_XREFKM, 533.215)
        self.assertEqual(screen.WOLSONG_YREFKM, 3942.629)
        h = screen.parse_header(poly()[:44])
        self.assertEqual(h["version"], 15)
        self.assertEqual(h["level"], 1)
        self.assertFalse(screen.overlaps_diagnostic_box(
            {**h, "west": 140, "east": 141}))


if __name__ == "__main__":
    unittest.main()
