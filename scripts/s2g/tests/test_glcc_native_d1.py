#!/usr/bin/env python3
"""#53 D1: synthetic original-layout IMG, native direct C++ vs prior Python GEN.

Synthetic equality does not establish real 156MB source or original GLAZAS parity.
"""
import csv
import hashlib
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from types import SimpleNamespace

from rasterio.warp import transform as crs_transform

from engine.preprocess.ctgproc.auto_select_landuse_to_ctgproc import parse_grid_cmn
from scripts.s2g.real_glcc_landuse_from_grid import grid_window, prepare

GRID = Path("project/cases/hefei5km_2022_reference_case_20261011/grid/grid.cmn")
SIZE = 156_000_000
NX, NY = 13000, 12000


def source_write(raw, i, j, code):
    assert 1 <= i <= NX and 1 <= j <= NY
    with raw.open("r+b") as stream:
        stream.seek((NY-j)*NX+(i-1))
        stream.write(bytes([code]))


def output_rows(path):
    with path.open(newline="") as stream:
        return list(csv.DictReader(stream))


def sha256(path):
    h=hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda:stream.read(1<<20),b""):
            h.update(block)
    return h.hexdigest()


class NativeGlccD1(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw_driver=Path(os.environ["P2_GLCC_TEST_DRIVER"]).resolve()
        cls.gen_driver=Path(os.environ["P2_GEN_CLI"]).resolve()

    def test_sparse_full_layout_same_source(self):
        with tempfile.TemporaryDirectory(prefix="glcc-d1-synthetic-") as d:
            root=Path(d)
            source=root/"eausgs2_0la.img"
            with source.open("wb") as stream:
                stream.truncate(SIZE)
            win,_,_=grid_window(parse_grid_cmn(GRID),1.5)
            # Source 0 is MISSING; raw 16 is WATER (USGS 52).
            for j in range(win["j0"],win["j1"]+1):
                for i in range(win["i0"],win["i1"]+1):
                    source_write(source,i,j,(0,1,16,2,18)[(i+2*j)%5])
            native_csv=root/"native.csv"
            cmd=[str(self.raw_driver),str(source),"32650","510885","3531269",
                 "100","50","50","20",str(native_csv)]
            run=subprocess.run(cmd,capture_output=True,text=True,check=True)
            self.assertIn("GLCC_RAW0=",run.stdout)
            self.assertIn("GLCC_RAW16=",run.stdout)
            prep=prepare(GRID,source,root/"reference",mesh_cells=20,
                         expected_sha=sha256(source),max_points=3_000_000)
            self.assertEqual(prep["generic"]["n_points"],prep["output_points_estimated"])
            gen=root/"reference"/"glcc.generic.txt"
            gen_csv=root/"gen_reference.csv"
            subprocess.run([str(self.gen_driver),str(gen),"510.885","3531.269",
                            str(gen_csv)],check=True,capture_output=True,text=True)
            native_rows,ref_rows=output_rows(native_csv),output_rows(gen_csv)
            self.assertEqual(len(native_rows),2500)
            self.assertEqual(len(ref_rows),2500)
            categories=[name for name in native_rows[0] if name.startswith("cat")]
            self.assertEqual(len(categories),38)
            self.assertIn("cat52",categories)
            total_native=total_ref=0
            max_delta=0.
            for a,b in zip(native_rows,ref_rows):
                self.assertEqual((a["i"],a["j"]),(b["i"],b["j"]))
                self.assertEqual(a["samples"],b["samples"])
                total_native+=int(a["samples"])
                total_ref+=int(b["samples"])
                for key in categories:
                    self.assertEqual(a[key]=="MISSING",b[key]=="MISSING")
                    if a[key]!="MISSING":
                        delta=abs(float(a[key])-float(b[key]))
                        max_delta=max(max_delta,delta)
                        self.assertLessEqual(delta,0.0005,(key,a["i"],a["j"],delta))
            self.assertGreater(total_native,0)
            self.assertEqual(total_native,total_ref)
            print(f"P2_GLCC_D1_SYNTHETIC_GEN_EQUIVALENCE=PASS cells=2500 points={total_native} max_abs_diff={max_delta:.9g}")

    def test_direct_multi_zone_and_southern_engineering_only(self):
        """Independent synthetic source windows in Japan and Indonesia.

        These tests prove bounded WGS84-UTM program execution, source-pixel
        provenance and exact in-code direct/probe category conservation, not
        original CTGPROC parity outside the frozen Hefei science case.
        """
        cases = (
            ("japan-utm54n", 139.70, 35.70, 32654, 40, 60, 200, 10),
            ("sumatra-utm47s", 98.67, -2.99, 32747, 30, 40, 150, 20),
        )
        with tempfile.TemporaryDirectory(prefix="glcc-cross-utm-") as tmp:
            root=Path(tmp)
            for label,lon,lat,epsg,nx,ny,spacing_m,mesh in cases:
                with self.subTest(location=label,epsg=epsg,mesh=mesh):
                    projected_x,projected_y=crs_transform(
                        "EPSG:4326",f"EPSG:{epsg}",[lon],[lat])
                    x0=round(projected_x[0]-nx*spacing_m/2)
                    y0=round(projected_y[0]-ny*spacing_m/2)
                    grid=SimpleNamespace(imap="UTM",
                        lsohem="N" if epsg<32700 else "S",
                        iutmzn=epsg%100,datum="WGS-84",
                        nx=nx,ny=ny,dgridkm=spacing_m/1000.,
                        xrefkm=x0/1000.,yrefkm=y0/1000.)
                    win,_,_=grid_window(grid,1.5)
                    source=root/f"{label}.img"
                    with source.open("wb") as stream:
                        stream.truncate(SIZE)
                    # The true 13,000x12,000 north-to-south raw file layout
                    # is independently populated for each geographic region.
                    with source.open("r+b") as stream:
                        for j in range(win["j0"],win["j1"]+1):
                            stream.seek((NY-j)*NX+(win["i0"]-1))
                            stream.write(bytes(
                                1+((i+2*j)%24)
                                for i in range(win["i0"],win["i1"]+1)))
                    output=root/f"{label}.csv"
                    cmd=[str(self.raw_driver),str(source),str(epsg),
                         str(x0),str(y0),str(spacing_m),
                         str(nx),str(ny),str(mesh),str(output)]
                    run=subprocess.run(cmd,capture_output=True,
                                       text=True,timeout=120)
                    self.assertEqual(run.returncode,0,run.stderr)
                    self.assertIn("TEST_SYNTHETIC_ONLY INCLUDED=",run.stdout)
                    rows=output_rows(output)
                    self.assertEqual(len(rows),nx*ny)
                    included=sum(int(row["samples"]) for row in rows)
                    self.assertGreater(included,0,(label,win))
                    self.assertTrue(all(
                        row["cat11"]=="MISSING" if int(row["samples"])==0
                        else row["cat11"]!="MISSING"
                        for row in rows))
                    print(f"GLCC_MULTI_UTM_SOFTWARE_ONLY=PASS {label} "
                          f"epsg={epsg} grid={nx}x{ny} step_m={spacing_m} "
                          f"mesh={mesh} synthetic_included={included} "
                          "ORIGINAL_GLAZAS=NOT_RUN")

    def test_bad_input_rejected(self):
        with tempfile.TemporaryDirectory(prefix="glcc-d1-bad-") as d:
            root=Path(d)
            pointer=root/"pointer.img"
            pointer.write_text("version https://git-lfs.github.com/spec/v1\n")
            target=root/"reject.csv"
            cmd=[str(self.raw_driver),str(pointer),"32650","510885","3531269",
                 "100","50","50","20",str(target)]
            p=subprocess.run(cmd,capture_output=True,text=True)
            self.assertNotEqual(p.returncode,0)
            self.assertIn("156MB",p.stderr)
            self.assertFalse(target.exists())
            raw=root/"invalid.img"
            with raw.open("wb") as stream:
                stream.truncate(SIZE)
            win,_,_=grid_window(parse_grid_cmn(GRID),1.5)
            source_write(raw,(win["i0"]+win["i1"])//2,
                         (win["j0"]+win["j1"])//2,25)
            q=subprocess.run([str(self.raw_driver),str(raw),"32650","510885",
                              "3531269","100","50","50","20",str(target)],
                             capture_output=True,text=True)
            self.assertNotEqual(q.returncode,0)
            self.assertIn("INVALID_RAW_CATEGORY",q.stderr)
            self.assertFalse(target.exists())


if __name__=="__main__":
    unittest.main()
