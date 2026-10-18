"""No original/vendor source in ordinary PR; test exact integer TIFF repack only."""
import tempfile
import unittest
from pathlib import Path

import numpy as np
import rasterio
from rasterio.transform import from_origin

from scripts.s2g.p1_original_actions_replay import (
    lossless_uncompressed_legacy_tiff,OriginalReplayError
)

class OriginalReaderTIFFPackagingTests(unittest.TestCase):
    def test_real_integer_source_values_identical_after_no_compression(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)
            source=folder/"source_compressed.tif"
            dest=folder/"original_compatible.tif"
            vals=(np.arange(2047,dtype=np.int16).reshape(23,89)*3)-1400
            vals[8:12,25:31]=-32768
            with rasterio.open(
                source,"w",driver="GTiff",count=1,
                height=23,width=89,dtype="int16",crs="EPSG:4326",
                transform=from_origin(115.0,31.95,1/3600,1/3600),
                nodata=-32768,compress="deflate"
            ) as data:
                data.write(vals,1)
            with rasterio.open(source) as src:
                self.assertIsNotNone(src.compression)
                source_data=src.read(1)
                source_transform=src.transform
            from scripts.s2g.p1_terrain_source import sha256
            original_hash=sha256(source)
            att=lossless_uncompressed_legacy_tiff(source,dest)
            self.assertTrue(att["pixel_values_identical"])
            self.assertTrue(att["scientific_method_unchanged"])
            self.assertEqual(att["compressed_source_sha256"],original_hash)
            self.assertEqual(sha256(source),original_hash)
            self.assertNotEqual(sha256(dest),original_hash)
            with rasterio.open(dest) as converted:
                self.assertIsNone(converted.compression)
                self.assertEqual(converted.transform,source_transform)
                self.assertEqual(converted.crs.to_epsg(),4326)
                self.assertEqual(converted.nodata,-32768)
                np.testing.assert_array_equal(converted.read(1),source_data)
            with self.assertRaisesRegex(OriginalReplayError,"already exists"):
                lossless_uncompressed_legacy_tiff(source,dest)

if __name__=="__main__":
    unittest.main()
