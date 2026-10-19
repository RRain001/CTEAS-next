"""Offline content check of the committed real Wolsong acquisition."""
import json
import unittest
import numpy as np
import rasterio
from scripts.s2g import p2b_wolsong_case as site

class RealDelivery(unittest.TestCase):
    def test_actual_raster_manifest_and_full_histogram(self):
        info = site.verify(site.DEFAULT)
        report = json.loads((site.DEFAULT/'verification.json').read_text())
        meta = json.loads((site.DEFAULT/'metadata.json').read_text())
        self.assertEqual(info['sha256'], '2a1a208c5386735692d788066f730c7391e87f0981e7b9ad099442af2e217711')
        self.assertEqual(info['sha256'],meta['repeat_download']['second_sha256'])
        with rasterio.open(site.DEFAULT/site.NAME) as ds:
            a=ds.read(1)
            vals,counts=np.unique(a,return_counts=True)
            hist={str(int(v)):int(c) for v,c in zip(vals,counts)}
            self.assertEqual(hist,report['classes_histogram'])
            self.assertEqual(len(hist),21)
            self.assertTrue(np.all(ds.read_masks(1)>0))
            self.assertFalse(np.isin(a,[0,250]).any())
        self.assertEqual(info['modelgrid_invalid_source_area_m2'],0)
        self.assertEqual(info['modelgrid_valid_source_area_m2'],400000000)
        self.assertTrue(report['repeat_file_bytes_equal'])
