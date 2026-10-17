"""No-PySide smoke tests for independent G5 GUI and native-only routing."""
from __future__ import annotations

import os
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from engine.gui_g5 import case_setup, pipeline
from engine.run_met.station_grid import load_strict_utm_grid, lon_lat_in_utm_grid


class G5IsolationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.case_root = self.folder / "cases" / "G5_TEST"
        with patch.object(case_setup, "CASES_ROOT", self.folder / "cases"):
            case_setup.create_case("G5_TEST")
        self.data = case_setup.initial_config("G5_TEST")

    def readiness(self, stage: str, resume=False):
        with patch.object(pipeline, "case_dir", return_value=self.case_root), \
             patch.object(pipeline, "current_case_name", return_value="G5_TEST"):
            return pipeline.stage_readiness(stage, self.data, "G5_TEST", resume)

    def test_native_reference_only_never_accepted_as_generic(self):
        for stage in ("preprocess", "upperair", "met", "puff", "all"):
            good, reason = self.readiness(stage)
            self.assertFalse(good, (stage, reason))
            self.assertTrue(reason)
        self.assertFalse(self.readiness("surface")[0])
        self.assertFalse(self.readiness("surface", resume=True)[0])

    def test_case_grid_utm_geometry_separate_stack_and_domain(self):
        grid = load_strict_utm_grid(self.case_root / "grid/grid.cmn", context="G5")
        self.assertEqual((grid.nx, grid.ny, grid.nz), (50, 50, 9))
        self.assertEqual(grid.dgridkm, 1.0)
        self.assertEqual(len(grid.zfaces), 10)
        self.assertTrue(lon_lat_in_utm_grid(117.0, 32.0, grid))
        self.assertFalse(lon_lat_in_utm_grid(117.8, 32.0, grid))
        self.data["preprocess"]["stack"] = {"longitude": 117.8, "latitude": 32.0}
        pipeline.validate_case(self.data)
        with self.assertRaises(ValueError):
            pipeline.validate_case({**self.data, "preprocess": {
                **self.data["preprocess"], "stack": {}}})

    def test_edited_centre_reprojects_stack_across_utm_zone(self):
        # The disk grid starts in UTM 50N. Editing case.yaml to Japan
        # must publish UTM 54N and immediately use 54N for source x/y.
        old_grid = load_strict_utm_grid(self.case_root / "grid/grid.cmn")
        self.assertEqual(old_grid.iutmzn, 50)
        self.data["preprocess"]["grid"]["center"] = {
            "longitude": 139.0, "latitude": 35.0}
        self.data["preprocess"]["stack"] = {
            "longitude": 139.02, "latitude": 35.01}
        x, y = case_setup.projected_stack_utm_km(self.data)
        case_setup.write_case_grid(self.case_root, self.data)
        new_grid = load_strict_utm_grid(self.case_root / "grid/grid.cmn")
        self.assertEqual(new_grid.iutmzn, 54)
        self.assertTrue(lon_lat_in_utm_grid(139.02, 35.01, new_grid))
        self.assertLess(abs(x - (new_grid.xrefkm + 25)), 5)
        self.assertLess(abs(y - (new_grid.yrefkm + 25)), 5)

    def test_grid_respects_configured_layers_and_rejects_bad_zface(self):
        g = self.data["preprocess"]["grid"]
        g["nz"] = 3
        g["vertical_levels_m"] = [50, 500, 1500]
        case_setup.write_case_grid(self.case_root, self.data)
        grid = load_strict_utm_grid(self.case_root / "grid/grid.cmn")
        self.assertEqual(grid.zfaces, [0, 50, 500, 1500])
        g["vertical_levels_m"] = [50, 50, 1500]
        with self.assertRaises(ValueError):
            case_setup.write_case_grid(self.case_root, self.data)

    def test_p5_requires_explicit_native_binary_and_uses_stack(self):
        fake_exe = self.folder / "cteas_p5_smerge"
        fake_exe.write_text("#!/bin/sh\nexit 0\n")
        fake_exe.chmod(0o755)
        self.data["preprocess"]["stack"] = {"latitude": 32.01, "longitude": 117.02}
        with patch.dict(os.environ, {"CTEAS_G5_P5_BIN": str(fake_exe)}):
            ready, reason = self.readiness("surface")
            self.assertTrue(ready, reason)
            cmd = pipeline.native_command("surface", self.data)
            self.assertIn("native_cpp.modules.p5_smerge.data_prep.prepare_inputs", cmd)
            self.assertIn("--native-cpp-bin", cmd)
            self.assertEqual(cmd[cmd.index("--stack-lat")+1], "32.01")
            self.assertEqual(cmd[cmd.index("--stack-lon")+1], "117.02")
            self.assertNotIn("engine.orchestrator.cli", " ".join(cmd))
        self.assertFalse(self.readiness("surface")[0])

    def test_no_original_orchestrator_in_new_gui(self):
        src = Path("engine/gui_g5/workbench.py").read_text(encoding="utf-8")
        self.assertIn("engine.gui_g5.pipeline", src)
        self.assertIn("engine.gui_g5.app", src)
        self.assertNotIn("engine.orchestrator.cli", src)
        cli = Path("engine/gui_g5/pipeline.py").read_text(encoding="utf-8")
        self.assertNotIn('"-m", "engine.run_met.run_met"', cli)
        self.assertNotIn('"-m", "engine.run_puff.run_puff"', cli)
        self.assertEqual(set(pipeline.STAGES), {
            "preprocess", "upperair", "surface", "met", "puff", "all"})

    def test_case_mismatch_blocks_native_execution(self):
        with patch.object(pipeline, "case_dir", return_value=self.case_root), \
             patch.object(pipeline, "current_case_name", return_value="ANOTHER_CASE"):
            ready, reason = pipeline.stage_readiness("surface", self.data, "G5_TEST")
        self.assertFalse(ready)
        self.assertIn("project/current", reason)


if __name__ == "__main__":
    unittest.main()
