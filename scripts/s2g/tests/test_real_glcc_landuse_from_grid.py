"""S2-G1B-B3 GLCC source-only unit tests; NO native P2/CTGPROC physics."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.s2g.real_glcc_landuse_from_grid import (
    SOURCE_BYTES, LanduseSourceError, digest, grid_window, prepare,
    validate_source,
)
from engine.preprocess.ctgproc.auto_select_landuse_to_ctgproc import parse_grid_cmn
from scripts.crop_terrain_landuse_data import GLCC_NY, GLCC_NX


class GlccGridSourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix="s2g-glcc-synthetic-")
        cls.base = Path(cls.temp.name)
        cls.grid = cls.base / "grid.cmn"
        cls.grid.write_text(
            "\n".join([
                "! IMAP = UTM !", "! IUTMZN = 50 !", "! LSOHEM = N !",
                "! DATUM = WGS-84 !", "! XREFKM = 510.885 !",
                "! YREFKM = 3531.269 !", "! NX = 2 !", "! NY = 2 !",
                "! DGRIDKM = 0.1 !", "! NZ = 9 !",
            ])+"\n", encoding="utf-8")
        cls.window, cls.utm, cls.grid_meta = grid_window(
            parse_grid_cmn(cls.grid), 1.5)
        cls.src = cls.base / "synthetic_glcc_raw_uint8.img"
        with cls.src.open("wb") as f:
            # Sparse file with the documented original full byte layout;
            # NOT real NOAA/USGS GLCC scientific observations.
            f.truncate(SOURCE_BYTES)
        cls.i = cls.window["i0"]
        cls.j = cls.window["j0"]
        with cls.src.open("r+b") as f:
            cls._write_cell(f, cls.i, cls.j, 1)
            cls._write_cell(f, cls.i+1, cls.j, 16)
        cls.good_sha = digest(cls.src)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    @staticmethod
    def _write_cell(fd, i, j, value):
        fd.seek((GLCC_NY-j)*GLCC_NX+i-1)
        fd.write(bytes([value]))

    def output(self, suffix):
        return self.base / suffix

    def test_source_window_dynamic_and_categories(self):
        result = prepare(
            self.grid, self.src, self.output("realistic_source_test"),
            mesh_cells=2, expected_sha=self.good_sha)
        self.assertEqual(result["classified_pixels"], 2)
        self.assertEqual(result["raw_class_counts"]["1"], 1)
        self.assertEqual(result["raw_class_counts"]["16"], 1)
        self.assertEqual(result["water_class_translated"], 52)
        self.assertEqual(result["output_points_estimated"], 8)
        points = (self.output("realistic_source_test")/"glcc.generic.txt").read_text().splitlines()
        self.assertEqual(points[0].strip(), "GENERIC.LANDUSE 1.0")
        self.assertEqual(int(points[6]), 38)
        self.assertEqual(len(points)-8, 8)
        codes = {int(s.split()[0]) for s in points[8:]}
        self.assertEqual(codes, {16, 52})
        self.assertEqual(result["native_P2_lu_dat"], "NOT_RUN")
        self.assertFalse(result["ready"])
        meta = json.loads((self.output("realistic_source_test")/"glcc_source_manifest.json").read_text())
        self.assertEqual(meta["original_sha256"], self.good_sha)
        self.assertEqual(digest(self.src), self.good_sha)

    def test_dry_run_does_not_produce_source(self):
        target=self.output("dry-run-p2")
        result=prepare(self.grid,self.src,target,mesh_cells=2,
                       expected_sha=self.good_sha,dry_run=True)
        self.assertEqual(result["classified_pixels"],2)
        self.assertFalse(target.exists())

    def test_lfs_pointer_rejected(self):
        pointer=self.base/"pointer.img"
        pointer.write_text("version https://git-lfs.github.com/spec/v1\n"
                           "oid sha256:deadbeef\nsize 156000000\n")
        with self.assertRaisesRegex(LanduseSourceError,"156000000|exactly"):
            validate_source(pointer)

    def test_wrong_sha_rejected_no_outputs(self):
        target=self.output("invalid-sha")
        with self.assertRaisesRegex(LanduseSourceError,"SHA256 mismatch"):
            prepare(self.grid,self.src,target,mesh_cells=2)
        self.assertFalse(target.exists())

    def test_no_outside_24th_class_silent_mapping(self):
        modified=self.base/"invalid_raw.img"
        with modified.open("wb") as f:
            f.truncate(SOURCE_BYTES)
        with modified.open("r+b") as f:
            self._write_cell(f,self.i,self.j,25)
        target=self.output("invalid-category")
        with self.assertRaisesRegex(LanduseSourceError,"unknown class"):
            prepare(self.grid,modified,target,mesh_cells=2,expected_sha=digest(modified))
        self.assertFalse(target.exists())

    def test_blank_source_rejected_not_interpreted_as_open_sea(self):
        modified=self.base/"zero_classes.img"
        with modified.open("wb") as f:
            f.truncate(SOURCE_BYTES)
        target=self.output("all-zero")
        with self.assertRaisesRegex(LanduseSourceError,"no classified pixels"):
            prepare(self.grid,modified,target,mesh_cells=2,expected_sha=digest(modified))
        self.assertFalse(target.exists())

    def test_mesh_resource_budget_fail_closed(self):
        target=self.output("oversized")
        with self.assertRaisesRegex(LanduseSourceError,"exceeds"):
            prepare(self.grid,self.src,target,mesh_cells=20,
                    max_points=5,expected_sha=self.good_sha)
        self.assertFalse(target.exists())

    def test_bad_kilometer_origin_precision_rejected(self):
        wrong=self.base/"submeter-origin.cmn"
        wrong.write_text(self.grid.read_text().replace(
            "XREFKM = 510.885", "XREFKM = 510.8854"))
        with self.assertRaisesRegex(LanduseSourceError,"XREFKM"):
            prepare(wrong,self.src,self.output("bad-origin"),
                    mesh_cells=2,expected_sha=self.good_sha)

    def test_refuse_overwriting_existing_case(self):
        target=self.output("existing-case")
        target.mkdir(exist_ok=True)
        with self.assertRaisesRegex(LanduseSourceError,"must not exist"):
            prepare(self.grid,self.src,target,mesh_cells=2,
                    expected_sha=self.good_sha)


if __name__ == "__main__":
    unittest.main()
