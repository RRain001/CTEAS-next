"""Offline #54 source-provenance test: no vendor Fortran, no actual DEM."""
import tempfile
import unittest
from pathlib import Path

import numpy as np
import rasterio
from rasterio.transform import from_origin
from pyproj import Transformer

from scripts.s2g.p1_original_coord_probe import (
    diagnostic_copy, diagnose_trace, _cell_index, CoordinateProbeError,
    OPEN_ANCHOR, POINT_ANCHOR
)


class OriginalCoordinateProbeOfflineTests(unittest.TestCase):
    def test_historical_source_instrumented_only_in_fresh_scratch(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)
            source=path/"terrel.for"
            untouched=("! real historical skeleton\n"+OPEN_ANCHOR+"\n"
                       +POINT_ANCHOR+"\n      end\n")
            source.write_text(untouched)
            debug=path/"probe.for"
            diagnostic_copy(source,debug)
            self.assertEqual(source.read_text(),untouched)
            self.assertIn("call cellind(xdist,ydist,dels",debug.read_text())
            self.assertIn("p1_original_coords.txt",debug.read_text())
            self.assertEqual(debug.read_text().count(POINT_ANCHOR),1)
            with self.assertRaises(CoordinateProbeError):
                diagnostic_copy(source,debug)
            source.write_text(OPEN_ANCHOR+"\n")
            with self.assertRaises(CoordinateProbeError):
                diagnostic_copy(source,path/"refuse.for")

    def test_independent_pixel_trace_projection_proxy_and_forced_boundary_shift(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            tif=root/"synthetic.tif"
            # Two pixels, both well within the test UTM50N source; no
            # blocked/original binary or network request is needed here.
            with rasterio.open(tif,"w",driver="GTiff",height=3,width=3,
                                count=1,dtype="int16",nodata=-32768,
                                crs="EPSG:4326",
                                transform=from_origin(115.0,31.94,
                                                      1/3600,1/3600)) as ds:
                ds.write(np.full((3,3),42,dtype=np.int16),1)
            tr=Transformer.from_crs("EPSG:4326","EPSG:32650",always_xy=True)
            x0,y0=tr.transform(115.0+0.5/3600,31.94-0.5/3600)
            # Use a legitimate domain surrounding that particular pixel,
            # with rounded origin at three-decimal kilometre precision.
            grid={
                "zone":50,"hemisphere":"N",
                "xrefkm":f"{(x0/1000-0.3):.3f}",
                "yrefkm":f"{(y0/1000-0.3):.3f}",
                "nx":10,"ny":10,"dgridkm":0.1
            }
            factor=float(np.float32(0.001))
            projected=[]
            for px in (0,1):
                lon=float(np.float32(np.float32(115.0+.5/3600)+
                                     np.float32(px)*np.float32(1/3600)))
                lat=float(np.float32(31.94-.5/3600))
                x,y=tr.transform(lon,lat)
                east=float(np.float32(np.float32(x*factor)*np.float32(1000)))
                north=float(np.float32(np.float32(y*factor)*np.float32(1000)))
                projected.append((east,north))
            line=[]
            for i,(east,north) in enumerate(projected,1):
                ix,iy=_cell_index(east,north,grid)
                # Deliberately alter one original assignment while keeping
                # coordinates the same: detector must not confuse projection
                # deltas with CELLIND mismatch.
                if i==2:ix+=1
                line.append(f"{i} 1 {ix} {iy} {east:.9f} {north:.9f}")
            trace=root/"legacy-coords.txt"
            trace.write_text("\n".join(line)+"\n")
            result=diagnose_trace(trace=trace,selected_tif=tif,grid=grid)
            self.assertEqual(result["trace_records"],2)
            self.assertEqual(result["original_vs_proj_proxy_cell_mismatches_BOTH_INSIDE"],1)
            self.assertEqual(result["original_inside_hits"],2)
            self.assertEqual(result["proj_proxy_inside_hits"],2)
            self.assertEqual(result["both_outside"],0)
            self.assertTrue(result["inside_outside_classifications_sum_to_trace"])
            self.assertEqual(result["cell_mismatch_axes"]["E_W/NO_N_S"],1)
            self.assertEqual(result["science_acceptance"],"NOT_ACCEPTED")
            self.assertFalse(result["pixel_trace_artifact_uploaded"])

    def test_trace_is_strict_and_bounded(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            trace=root/"trace.txt"
            trace.write_text("garbage\n")
            tif=root/"geo.tif"
            with rasterio.open(tif,"w",driver="GTiff",height=1,width=1,
                                count=1,dtype="int16",nodata=-32768,
                                crs="EPSG:4326",
                                transform=from_origin(115,31,1/3600,1/3600)) as ds:
                ds.write(np.array([[2]],dtype="int16"),1)
            grid={"zone":50,"hemisphere":"N","xrefkm":"500.000",
                  "yrefkm":"3400.000","nx":2,"ny":2,"dgridkm":0.1}
            with self.assertRaises(CoordinateProbeError):
                diagnose_trace(trace=trace,selected_tif=tif,grid=grid)
            trace.write_text("1 1 1 1 1000 1000\n1 1 1 1 1000 1000\n")
            with self.assertRaises(CoordinateProbeError):
                diagnose_trace(trace=trace,selected_tif=tif,grid=grid,max_records=1)

if __name__=="__main__":
    unittest.main()
