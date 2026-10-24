"""Offline checks against the committed real raster; no Earth Engine import/auth."""
import json
from pathlib import Path
import tempfile
import unittest
import numpy as np
import rasterio
from scripts.s2g.glc_fcs30d_acquire import ROOT, DATA, geometry, inspect, verify

class AcquisitionTests(unittest.TestCase):
    def test_real_committed_delivery(self):
        result = verify(ROOT/DATA)
        self.assertGreater(len(result['classes_histogram']),1)
        self.assertEqual(result['nodata_fraction'],0)

    def test_frozen_grid(self):
        self.assertEqual(geometry()['original_bounds_utm_m'],[510885,3531269,515885,3536269])

    def test_reject_unknown_class_wrong_crs_and_shift(self):
        with rasterio.open(ROOT/DATA/'hefei_2022_30m.tif') as ds:
            profile, pixels = ds.profile,ds.read()
        for mutation in ('class','crs','shift'):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as temp:
                p, a = profile.copy(),pixels.copy()
                if mutation=='class':
                    a[0,0,0]=99
                elif mutation=='crs':
                    p['crs']='EPSG:32649'
                else:
                    p['transform']=p['transform']*rasterio.Affine.translation(100,0)
                path = Path(temp)/'bad.tif'
                with rasterio.open(path,'w',**p) as output:
                    output.write(a)
                with self.assertRaises(ValueError):
                    inspect(path,geometry()['buffered_bounds_utm_m'])

    def test_projection_corner_roundoff_is_not_grid_drift(self):
        # Different PROJ versions vary at the last WGS84 decimal places.
        # A 1e-14 degree change is a coordinate serialization artifact;
        # it must not weaken the pixel SHA or exact projected UTM grid.
        with tempfile.TemporaryDirectory() as temp:
            destination = Path(temp)
            source = ROOT / DATA
            (destination / 'hefei_2022_30m.tif').write_bytes(
                (source / 'hefei_2022_30m.tif').read_bytes())
            meta = json.loads((source / 'metadata.json').read_text())
            meta['original_corners_wgs84'][1][1] += 1e-14
            (destination / 'metadata.json').write_text(json.dumps(meta))
            self.assertEqual(verify(destination)['nodata_fraction'], 0)
            meta['original_corners_wgs84'][1][1] += 1e-8
            (destination / 'metadata.json').write_text(json.dumps(meta))
            with self.assertRaisesRegex(ValueError, 'original_corners_wgs84'):
                verify(destination)
            meta = json.loads((source / 'metadata.json').read_text())
            meta['grid_sha256'] = '0' * 64
            (destination / 'metadata.json').write_text(json.dumps(meta))
            with self.assertRaisesRegex(ValueError, 'grid_sha256'):
                verify(destination)

    def test_reject_metadata_sha_tamper(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            source = ROOT/DATA
            (directory/'hefei_2022_30m.tif').write_bytes((source/'hefei_2022_30m.tif').read_bytes())
            meta = json.loads((source/'metadata.json').read_text())
            meta['sha256']='0'*64
            (directory/'metadata.json').write_text(json.dumps(meta))
            with self.assertRaisesRegex(ValueError,'sha256'):
                verify(directory)

if __name__=='__main__':
    unittest.main()
