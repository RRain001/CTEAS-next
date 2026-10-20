"""Offline real-source verification and fail-closed provenance/missing checks."""
import json
from pathlib import Path
import shutil
import tempfile
import unittest

import numpy as np
import rasterio

from scripts.s2g.issue160_hefei20km_glc_acquire import (
    NAME, OUT, ROOT, geometry, inspect, verify,
)


class Hefei20kmSourceTests(unittest.TestCase):
    def test_real_source(self):
        result = verify(OUT)
        self.assertEqual(result["gate"], "HEFEI_20KM_GLC_FCS30D_2022_SOURCE_VERIFIED")
        self.assertEqual(result["sha256"], "ee5cefc27827d84f0aa42d0e014e211fcfef67f2bffc43185d17897d840d2e58")
        info = inspect(OUT / NAME, geometry())
        self.assertEqual(sum(info["all_35_classes_histogram"].values()), info["valid_pixel_count"])
        self.assertEqual(len(info["all_35_classes_histogram"]), 35)

    def test_old_five_km_rejected(self):
        old = ROOT / "data/landcover/glc_fcs30d/v1_2022/hefei/hefei_2022_30m.tif"
        with self.assertRaisesRegex(ValueError, "FULL_20KM_PLUS_BUFFER_COVERAGE"):
            inspect(old, geometry())

    def test_repeat_and_source_provenance_tampering_rejected(self):
        original = json.loads((OUT / "metadata.json").read_text())
        for field, replacement in (("band", "b22"), ("image_ids", []),
                                   ("resampling", "bilinear"),
                                   ("repeat_download", {**original["repeat_download"],
                                                        "second_mask_sha256": "0" * 64})):
            with self.subTest(field=field), tempfile.TemporaryDirectory() as temp:
                directory = Path(temp)
                shutil.copyfile(OUT / NAME, directory / NAME)
                (directory / "metadata.json").write_text(json.dumps({**original, field: replacement}))
                with self.assertRaises(ValueError):
                    verify(directory)

    def test_fill_and_mask_are_preserved_and_unknown_valid_class_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "synthetic.tif"
            with rasterio.open(OUT / NAME) as source:
                profile = source.profile.copy()
                data = np.full(source.shape, 210, dtype=np.uint8)
            data[0, :3] = [0, 250, 210]
            mask = np.full(data.shape, 255, dtype=np.uint8)
            mask[0, 0] = mask[0, 2] = 0
            with rasterio.Env(GDAL_TIFF_INTERNAL_MASK=True):
                with rasterio.open(path, "w", **profile) as output:
                    output.write(data, 1)
                    output.write_mask(mask)
            info = inspect(path, geometry())
            self.assertEqual(info["nodata_or_fill_count"], 3)
            self.assertEqual(info["masked_pixel_count"], 2)
            self.assertEqual(info["fill_code_counts"], {"0": 1, "250": 1})
            self.assertEqual(info["source_glc210_pixel_count"], data.size - 3)
            with rasterio.open(path, "r+") as output:
                data[1, 0] = 99
                output.write(data, 1)
            with self.assertRaisesRegex(ValueError, "UNEXPECTED_CLASS"):
                inspect(path, geometry())

    def test_only_inverse_proj_diagnostics_allow_final_bit_variation(self):
        original = json.loads((OUT / "metadata.json").read_text())
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            shutil.copyfile(OUT / NAME, directory / NAME)
            metadata = directory / "metadata.json"
            original["buffer_corners_wgs84"][0][0] += 1e-12
            metadata.write_text(json.dumps(original))
            verify(directory)
            original["buffer_corners_wgs84"][0][0] += 1e-8
            metadata.write_text(json.dumps(original))
            with self.assertRaisesRegex(ValueError, "GEOMETRY_DRIFT_buffer_corners_wgs84"):
                verify(directory)
            original = json.loads((OUT / "metadata.json").read_text())
            original["model_bounds_utm_m"][0] += 1e-8
            metadata.write_text(json.dumps(original))
            with self.assertRaisesRegex(ValueError, "GEOMETRY_DRIFT_model_bounds_utm_m"):
                verify(directory)


if __name__ == "__main__":
    unittest.main()
