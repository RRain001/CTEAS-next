"""Bounded synthetic tests: no real GSHHG or full coastal science is invoked."""
from __future__ import annotations
import tempfile
import unittest
from pathlib import Path
from osgeo import ogr
from scripts.s2g import p2b_wolsong_mixed_coast_audit as audit


class TestWolsongMixedGeometryAudit(unittest.TestCase):
    def test_polygon_intersection_keeps_both_sides(self):
        land = audit.square(0, 0, 10, 10)
        water = audit.square(8, 2, 12, 8)
        self.assertAlmostEqual(water.GetArea(), 24.)
        self.assertAlmostEqual(audit.land_piece_area(land, water), 12.)
        self.assertAlmostEqual(water.GetArea() - audit.land_piece_area(land, water), 12.)
        distant = audit.square(11, 0, 12, 1)
        self.assertEqual(audit.land_piece_area(land, distant), 0.)

    def test_source_pixel_partial_overlap(self):
        land = audit.square(0, 0, 50, 50)
        # A rectangular 30m raster pixel straddles land edge by 15m.
        pixel = audit.square(35, 30, 65, 60)
        self.assertAlmostEqual(audit.land_piece_area(land, pixel), 15 * 20)

    def test_original_format_mixed_and_out_of_order_rejection(self):
        categories = [52, 55] + list(range(100, 136))
        header = [
            "LU.DAT          2.1 test", "2", "mock", "mock", "FRACTION",
            "UTM", "52N", "WGS-84", "200 200", "KM M",
            " ".join(str(c) for c in categories)]
        values = ["0.000"] * 38
        values[0], values[1] = "0.300", "0.700"
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "lu.dat"
            with path.open("w") as stream:
                stream.write("\n".join(header) + "\n")
                for row in range(40000):
                    i, j = row % 200 + 1, row // 200 + 1
                    stream.write(f"{i:5d}{j:5d} " + " ".join(values) + " .\n")
            mixed, with52 = audit.read_mixed_lu(path)
            self.assertEqual(len(mixed), 40000)
            self.assertEqual(len(with52), 40000)
            self.assertEqual((mixed[0]["i"], mixed[0]["j"]), (1, 1))
            text = path.read_text()
            text = text.replace("    1    1 ", "    2    1 ", 1)
            path.write_text(text)
            with self.assertRaisesRegex(ValueError, "LU_ROW_GRID_ORDER"):
                audit.read_mixed_lu(path)


if __name__ == "__main__":
    unittest.main()
