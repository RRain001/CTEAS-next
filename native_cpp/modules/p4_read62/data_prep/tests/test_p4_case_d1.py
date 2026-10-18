"""Offline P4 D1-A admission tests; no NOAA requests or scientific execution."""
from __future__ import annotations

import math
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import yaml

from engine.run_met.common import lon_lat_to_utm_km
from native_cpp.orchestration.plan import ContractError
from native_cpp.modules.p4_read62.data_prep.p4_case_d1 import (
    admit_staged_case, offline_igra, sha256_file,
)
from native_cpp.modules.p4_read62.data_prep.prepare_inputs import (
    commands, selected_years,
)
from native_cpp.modules.p4_read62.data_prep import run_cpp_pipeline


class IsolatedP4D1ATest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.case = self.root / "outside_repo_case_2022_2023"
        grid = self.case / "grid"
        grid.mkdir(parents=True)
        (self.case / "met").mkdir()
        self.archive = self.root / "raw_noaa"
        self.archive.mkdir()
        self.output = self.case / "met" / "upperair"
        self.lat, self.lon = 40.0, -105.0
        x, y = lon_lat_to_utm_km(self.lon, self.lat, 13, True)
        xref, yref = math.floor((x - 15.0) * 1000) / 1000, math.floor((y - 15.0) * 1000) / 1000
        self.xref = f"{xref:.3f}"
        (grid / "grid.cmn").write_text("\n".join((
            "! IMAP = UTM !", "! IUTMZN = 13 !", "! LSOHEM = N !",
            "! DATUM = WGS-84 !", f"! XREFKM = {self.xref} !",
            f"! YREFKM = {yref:.3f} !", "! NX = 20 !", "! NY = 20 !",
            "! DGRIDKM = 2.0 !", "! NZ = 9 !",
            *[f"! ZFACE = {h} !" for h in
              (0, 20, 40, 80, 160, 320, 640, 1200, 2000, 3000)]
        )) + "\n", encoding="utf-8")
        (grid / "research_time").write_text(
            "BEGIN: 20221231-180000\nEND: 20230101-060000\n", encoding="utf-8"
        )
        (grid / "center_location").write_text(
            f"latitude: {self.lat}\nlongitude: {self.lon}\n", encoding="utf-8"
        )
        self.config = {
            "schema_version": 1, "case_name": self.case.name,
            "settings": {"timezone": "UTC+0000"},
            "preprocess": {
                "grid": {
                    "utm_zone": 13, "hemisphere": "N",
                    "center": {"latitude": self.lat, "longitude": self.lon},
                    "domain": {"length_km": 40, "width_km": 40},
                    "resolution_km": 2.0, "nz": 9,
                },
                "research_time": {"begin": "20221231-180000", "end": "20230101-060000"},
                "upperair": {"station_id": "auto", "pstop_hpa": 500.0},
            },
            "puff": {"point_sources": [{
                "latitude": self.lat, "longitude": self.lon,
            }]},
        }
        self.write_case()

    def write_case(self):
        (self.case / "case.yaml").write_text(
            yaml.safe_dump(self.config, sort_keys=False), encoding="utf-8"
        )

    def admit(self):
        return admit_staged_case(self.case, self.output, self.archive,
                                 run_cpp_pipeline.REPO_ROOT)

    def test_accepts_immutable_staged_case_and_selects_both_years(self):
        hashes = self.admit()
        self.assertEqual(hashes["case_root"], str(self.case))
        self.assertEqual(hashes["grid/grid.cmn"], sha256_file(self.case / "grid/grid.cmn"))
        self.assertEqual(selected_years(None, self.case / "grid/research_time"), [2022, 2023])
        self.assertFalse(self.output.exists())

    def test_rejects_preexisting_output(self):
        self.output.mkdir()
        with self.assertRaisesRegex(ContractError, "must not preexist"):
            self.admit()

    def test_rejects_mismatch_between_stack_and_selector_center(self):
        self.config["puff"]["point_sources"][0]["longitude"] = -104.0
        self.write_case()
        with self.assertRaisesRegex(ContractError, "differs from the physical stack"):
            self.admit()

    def test_rejects_research_clock_disagreement(self):
        self.config["preprocess"]["research_time"]["end"] = "20230101-070000"
        self.write_case()
        with self.assertRaisesRegex(ContractError, "UTC mismatch"):
            self.admit()

    def test_rejects_noncanonical_origin_precision(self):
        path = self.case / "grid" / "grid.cmn"
        path.write_text(path.read_text().replace(self.xref, self.xref + "0"))
        with self.assertRaisesRegex(ContractError, "3 decimal"):
            self.admit()

    def test_rejects_immutable_case_file_symlink(self):
        file = self.case / "grid" / "research_time"
        original = self.root / "elsewhere.txt"
        file.replace(original)
        file.symlink_to(original)
        with self.assertRaisesRegex(ContractError, "symlink"):
            self.admit()

    def test_offline_archive_provenance_and_fail_closed(self):
        station = "USM00012345"
        raw = self.archive / (station + "-data.txt")
        raw.write_text("real source fixture only; no science assertion\n")
        found, reused, error = offline_igra(self.archive, station, 2022)
        self.assertEqual(found, raw)
        self.assertTrue(reused)
        self.assertIsNone(error)
        (self.archive / "2022").mkdir()
        (self.archive / "2022" / raw.name).write_text("ambiguous archive")
        path, _, error = offline_igra(self.archive, station, 2022)
        self.assertIsNone(path)
        self.assertIn("ambiguous", error["error"])
        raw.unlink()
        (self.archive / "2022" / (station + "-data.txt")).unlink()
        path, _, error = offline_igra(self.archive, station, 2022)
        self.assertIsNone(path)
        self.assertIn("missing", error["error"])

    def test_offline_archive_rejects_symlink(self):
        outside = self.root / "outside_source.txt"
        outside.write_text("no escape\n")
        (self.archive / "USM00012345-data.txt").symlink_to(outside)
        path, _, error = offline_igra(self.archive, "USM00012345", 2022)
        self.assertIsNone(path)
        self.assertIn("symlink", error["error"])

    def test_commands_forward_only_explicit_paths_with_annual_qa(self):
        cmds = commands(2022, 500.0, None, False,
                        self.case, self.output, self.archive)
        self.assertEqual(len(cmds), 3)
        self.assertIn("--offline-archive-root", cmds[0])
        self.assertIn("--case-root", cmds[0])
        self.assertIn("--upperair-root", cmds[1])
        self.assertIn("--upperair-root", cmds[2])
        self.assertTrue(any("download_igra" in word for word in cmds[0]))
        with self.assertRaisesRegex(ValueError, "cannot skip"):
            commands(2022, 500.0, None, True,
                     self.case, self.output, self.archive)

    def test_generic_runner_blocks_unsafe_final_merge_without_writes(self):
        args = ["run_cpp_pipeline", "--cpp-bin", str(self.root / "unbuilt_binary"),
                "--case-root", str(self.case),
                "--upperair-root", str(self.output),
                "--offline-archive-root", str(self.archive), "--merge-final"]
        with patch.object(sys, "argv", args), self.assertRaises(SystemExit) as caught:
            run_cpp_pipeline.main()
        self.assertEqual(caught.exception.code, 2)
        self.assertFalse(self.output.exists())


if __name__ == "__main__":
    unittest.main()
