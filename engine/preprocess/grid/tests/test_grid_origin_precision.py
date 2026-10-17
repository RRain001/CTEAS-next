"""UTM grid origins are numerically quantized to 0.001 km, not just printed."""
from __future__ import annotations

import math
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from engine.preprocess.grid import configure_grid_cmn as target


class GridOriginPrecisionTests(unittest.TestCase):
    def test_canonical_three_decimal_grid_origin(self):
        self.assertEqual(target.canonical_grid_origin_km(510.8846439571007), 510.885)
        self.assertEqual(target.canonical_grid_origin_km(3531.2689269678035), 3531.269)
        self.assertEqual(f"{target.canonical_grid_origin_km(510.8846439571007):.3f}", "510.885")
        for bad in (math.inf, -math.inf, math.nan):
            with self.assertRaisesRegex(ValueError, "GRID_ORIGIN_PRECISION"):
                target.canonical_grid_origin_km(bad)

    def test_update_grid_requires_quantized_values(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "grid.cmn"
            path.write_text(
                "! XREFKM =  0.000  !\n! YREFKM =  0.000  !\n"
                "! IUTMZN =  50  !\n! DGRIDKM =  0.1  !\n"
                "! NX =  50  !\n! NY =  50  !\n! NZ =  9  !\n",
                encoding="utf-8",
            )
            params = dict(zone=50, hemisphere="N", xref_km=510.885,
                          yref_km=3531.269, dgrid_km=0.1, nx=50, ny=50, nz=9)
            with patch.object(target, "GRID_CMN", path):
                target.update_grid_file(**params)
                original = path.read_bytes()
                self.assertIn(b"510.885", original)
                self.assertIn(b"3531.269", original)
                for field, value in (
                    ("xref_km", 510.8846439571007),
                    ("yref_km", 3531.2689269678035),
                ):
                    with self.subTest(field=field):
                        bad = dict(params, **{field: value})
                        with self.assertRaisesRegex(ValueError, "GRID_ORIGIN_PRECISION"):
                            target.update_grid_file(**bad)
                        self.assertEqual(path.read_bytes(), original)

    def test_main_uses_quantized_origin_before_grid_writer(self):
        config = {
            "longitude": 117.141610855, "latitude": 31.939774444,
            "length_km": 5, "width_km": 5, "dgrid_km": 0.1, "nz": 9,
            "begin_text": "20220101-000000", "end_text": "20220106-230000",
        }
        conversion = {
            "zone": 50, "hemisphere": "N", "x_km": 513.3846439571007,
            "y_km": 3533.7689269678035,
        }
        with patch.object(target, "sync_grid_templates_from_source"), \
             patch.object(target, "load_case_config", return_value={}), \
             patch.object(target, "load_preprocess_grid_config", return_value=config), \
             patch.object(target, "convert_lon_lat", return_value=conversion), \
             patch.object(target, "update_grid_file") as grid, \
             patch.object(target, "update_center_location"), \
             patch.object(target, "update_research_time"):
            self.assertEqual(target.main(), 0)
            args = grid.call_args.kwargs
            self.assertEqual(args["xref_km"], 510.885)
            self.assertEqual(args["yref_km"], 3531.269)


if __name__ == "__main__":
    unittest.main()
