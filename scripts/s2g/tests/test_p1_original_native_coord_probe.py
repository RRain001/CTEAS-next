"""#54 offline tests. Synthetic coordinates only; no original vendor or DEM."""
import math
from pathlib import Path
import shutil
import tempfile
import unittest

from scripts.s2g.p1_original_native_coord_probe import (
    CPP_ANCHOR, CPP_SUM_ANCHOR, DirectNativeProbeError,
    diagnostic_cpp_copy, compare_direct_traces, execute_native_diagnostic
)

class DirectNativeProbeOfflineTests(unittest.TestCase):
    def test_scratch_copy_preserves_production_source_and_rejects_second_write(self):
        with tempfile.TemporaryDirectory() as temp:
            d=Path(temp)
            original=d/"terrain_grid.cpp"
            content=("#include <ogr_spatialref.h>\n"+CPP_SUM_ANCHOR+"\n"+
                     CPP_ANCHOR+"\n")
            original.write_text(content)
            patched=d/"scratch.cpp"
            diagnostic_cpp_copy(original,patched)
            self.assertEqual(original.read_text(),content)
            self.assertIn("p1_native_pixel_coords.txt",patched.read_text())
            self.assertIn("p1_forensic_trace",patched.read_text())
            with self.assertRaises(DirectNativeProbeError):
                diagnostic_cpp_copy(original,patched)
            with self.assertRaises(DirectNativeProbeError):
                diagnostic_cpp_copy(d/"nonexistent",d/"unused")

    def test_real_cell_assignments_not_neighbor_pair_guesses(self):
        with tempfile.TemporaryDirectory() as temp:
            d=Path(temp)
            a=d/"fortran.txt"
            b=d/"cpp.txt"
            a.write_text("1 1 1 1 100 200\n2 1 2 1 220 200\n3 1 0 0 600 700\n")
            b.write_text(
                "1 1 1 1 100 200 115 31 100 200\n"
                "2 1 3 1 220.25 200 115 31 220 200\n"
                "3 1 1 1 600 700 115 31 600 700\n")
            grid={"nx":3,"ny":3}
            res=compare_direct_traces(original_trace=a,native_trace=b,grid=grid)
            self.assertTrue(res["source_pixel_set_exact_match"])
            self.assertEqual(res["trace_records"],3)
            self.assertEqual(res["original_inside_hits"],2)
            self.assertEqual(res["direct_native_inside_hits"],3)
            self.assertEqual(res["original_vs_DIRECT_CPP_cell_mismatches_BOTH_INSIDE"],1)
            self.assertEqual(res["direct_native_inside_only"],1)
            self.assertEqual(res["cell_mismatch_axes"]["E_W/NO_N_S"],1)
            self.assertEqual(res["max_abs_easting_difference_m"],0.25)
            self.assertEqual(res["science_acceptance"],"NOT_ACCEPTED")
            b.write_text("1 1 1 1 100 200 115 31 100 200\n")
            with self.assertRaises(DirectNativeProbeError):
                compare_direct_traces(original_trace=a,native_trace=b,grid=grid)
            with self.assertRaises(DirectNativeProbeError):
                compare_direct_traces(original_trace=a,native_trace=b,grid=grid,max_records=0)

    @unittest.skipUnless(shutil.which("g++") and shutil.which("gdal-config"),
                         "requires native GDAL toolchain")
    def test_exact_native_cpp_function_runs_synthetic_tiff_in_scratch(self):
        import numpy as np
        import rasterio
        from rasterio.transform import from_origin
        from pyproj import Transformer
        with tempfile.TemporaryDirectory() as temp:
            d=Path(temp)
            src=d/"synthetic-wgs84.tif"
            lon,lat=115.0,31.0
            dlon=1.0/36000.0
            with rasterio.open(src,"w",driver="GTiff",height=3,width=3,
                               count=1,dtype="int16",nodata=-32768,
                               crs="EPSG:4326",
                               transform=from_origin(lon,lat,dlon,dlon)) as tif:
                tif.write(np.full((3,3),42,dtype="int16"),1)
            x,y=Transformer.from_crs(
                "EPSG:4326","EPSG:32650",always_xy=True).transform(
                    lon+dlon/2,lat-dlon/2)
            grid={"xrefkm":f"{(x-30)/1000:.3f}",
                  "yrefkm":f"{(y-30)/1000:.3f}",
                  "nx":1,"ny":1,"dgridkm":"0.100",
                  "zone":50,"hemisphere":"N"}
            trace=execute_native_diagnostic(selected=src,grid=grid,workspace=d)
            rows=trace.read_text().splitlines()
            self.assertEqual(len(rows),9)
            self.assertTrue(all(len(row.split())==10 for row in rows))
            self.assertTrue(all(int(row.split()[2])==1 and
                                int(row.split()[3])==1 for row in rows))
            self.assertTrue(trace.is_relative_to(d))
            self.assertTrue((d/"forensic_native_cpp/terrain_grid.cpp").is_file())

if __name__=="__main__":
    unittest.main()
