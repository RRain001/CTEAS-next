"""G1A file-backed P6 source handoff software gates: NO CALMET execution."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

from engine.run_met.common import lon_lat_to_utm_km
from native_cpp.orchestration.plan import ContractError
from native_cpp.orchestration.p6_g19_handoff import prepare_g19, execute_source_preflight
from native_cpp.orchestration.tests import test_site_plan as g0_fixture


class SourceFileHandoffTests(unittest.TestCase):
    def setUp(self):
        # Reuse a proven, non-Hefei UTM13 real-geometric two-year metadata
        # fixture. Only test source bytes are placeholders. The separate
        # G19 C++ CTest verifies actual original GEO/SURF/UP record parsers.
        self.fixture = g0_fixture.DynamicNonHefeiContractTests(
            "test_non_hefei_case_is_read_only_and_p6_p7_blocked")
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.c = self.fixture
        self.root = self.c.case_root
        self.deck = self.root / "run/met/met.inp"
        self.geo = self.root / "geo/makegeo/geo.dat"
        self.surf = self.root / "met/surface/final/surf.dat"
        self.up = self.root / "met/upperair/final"
        for p in (self.deck, self.geo, self.surf, self.up / "up_12345.dat",
                  self.up / "up_23456.dat"):
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(b"ORIGINAL_FORMAT_RECORDS_REQUIRE_G19_CPP_PARSE\n")
        self.write_deck()

    def projected(self, point):
        x, y = lon_lat_to_utm_km(point[1], point[0], 13, True)
        return f"{x:.3f}", f"{y:.3f}"

    def write_deck(self, modify=None):
        x1, y1 = self.projected(self.c.a)
        x2, y2 = self.projected(self.c.b)
        lines = [
            "! NX = 20 !", "! NY = 20 !", "! NZ = 9 !",
            "! IUTMZN = 13 !", "! UTMHEM = N !", "! DGRIDKM = 2.0 !",
            f"! XORIGKM = {self.c.xref:.3f} !",
            f"! YORIGKM = {self.c.yref:.3f} !",
            "! NSSTA = 2 !", "! NUSTA = 2 !",
            f"! SS1 = 'FIRST' 7246901 {x1} {y1} 0 10.0 !",
            f"! SS2 = 'SECOND' 7247001 {x2} {y2} 0 10.0 !",
            f"! US1 = 'FIRST' 12345 {x1} {y1} 0 !",
            f"! US2 = 'SECOND' 23456 {x2} {y2} 0 !",
        ]
        if modify:
            modify(lines)
        self.deck.write_text("\n".join(lines) + "\n")

    def plan(self, executable=None):
        return prepare_g19(self.c.yaml_path, self.c.p4, self.c.p5,
                           self.root, executable)

    def test_valid_dynamic_station_geometry_and_sha_without_physics(self):
        before = {p: p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
        result = self.plan()
        self.assertEqual(
            result["status"], "P6_G19_DYNAMIC_SOURCE_ROLES_HASH_VERIFIED_NATIVE_SOURCE_NOT_RUN")
        self.assertEqual(result["ordered_upper_station_ids"],
                         ["USM00012345", "USM00023456"])
        self.assertEqual(result["ordered_surface_station_ids"],
                         ["72469099999", "72470099999"])
        self.assertEqual(result["grid"]["nx"], 20)
        self.assertEqual(len(result["roles"]), 5)
        self.assertFalse(result["model_executed"])
        self.assertFalse(result["ready"])
        self.assertFalse(result["native_input_parsed"])
        self.assertEqual(result["P6D_P6E_P6F"], "NOT_RUN")
        self.assertEqual(result["source_authenticity"],
                         "NOT_AUTHENTICATED_BY_THIS_INPUT_MANIFEST_VALIDATOR")
        self.assertEqual(before, {p: p.read_bytes() for p in self.root.rglob("*") if p.is_file()})

    def test_reject_mismatched_grid_origin(self):
        self.write_deck(lambda lines: lines.__setitem__(
            6, f"! XORIGKM = {self.c.xref+1:.3f} !"))
        with self.assertRaisesRegex(ContractError, "XORIGKM"):
            self.plan()

    def test_reject_deck_extra_station(self):
        self.write_deck(lambda lines: lines.__setitem__(9, "! NUSTA = 3 !"))
        with self.assertRaisesRegex(ContractError, "NUSTA"):
            self.plan()

    def test_reject_deck_wrong_upper_alias(self):
        self.write_deck(lambda lines: lines.__setitem__(
            -2, "! US1 = 'FIRST' 58424 400.00 4400.00 0 !"))
        with self.assertRaisesRegex(ContractError, "does not match selected"):
            self.plan()

    def test_reject_deck_wrong_surface_alias(self):
        self.write_deck(lambda lines: lines.__setitem__(
            -4, "! SS1 = 'FIRST' 583210 400.00 4400.00 0 !"))
        with self.assertRaisesRegex(ContractError, "mismatches P5 IFSTN"):
            self.plan()

    def test_reject_utm_mismapped_station_coordinate(self):
        self.write_deck(lambda lines: lines.__setitem__(
            -1, "! US2 = 'SECOND' 23456 300.000 4490.000 0 !"))
        with self.assertRaisesRegex(ContractError, "projected position"):
            self.plan()

    def test_reject_missing_station_file(self):
        (self.up / "up_12345.dat").unlink()
        with self.assertRaisesRegex(ContractError, "missing or empty"):
            self.plan()

    def test_reject_source_symlink(self):
        self.geo.unlink()
        self.geo.symlink_to(self.surf)
        with self.assertRaisesRegex(ContractError, "symlink"):
            self.plan()

    def test_reject_cross_year_stations_not_in_one_deck(self):
        p = self.c.p4 / "2023/p4_station_selection_audit.json"
        doc = json.loads(p.read_text())
        doc["selected"][1]["id"] = "USM00034567"
        p.write_text(json.dumps(doc))
        with self.assertRaisesRegex(ContractError, "cannot silently change p4"):
            self.plan()

    def test_reject_one_upper_when_g19_only_2_to_6(self):
        for year in (2022, 2023):
            path = self.c.p4 / str(year) / "p4_station_selection_audit.json"
            doc = json.loads(path.read_text())
            doc["selected"] = doc["selected"][:1]
            path.write_text(json.dumps(doc))
        with self.assertRaisesRegex(ContractError, "only accepts 2-6 real upper-air"):
            self.plan()

    def test_input_preflight_failure_never_marked_as_science_pass(self):
        exe = self.c.root.parent / "mock_native_g19"
        exe.write_text("#!/bin/sh\necho 'REJECT: malformed GEO/SURF/UP'; exit 1\n")
        exe.chmod(0o700)
        req = self.plan(exe)
        with self.assertRaisesRegex(ContractError, "rejected"):
            execute_source_preflight(req)

    def test_stubbed_input_only_g19_result_not_model_execution(self):
        # This checks ONLY stdout/exit gating. Native parser science remains
        # subject to separately compiled real C++ G19 source CTest.
        exe = self.c.root.parent / "mock_native_g19"
        exe.write_text("#!/bin/sh\\necho PASS_P6G_G19_FILE_SOURCE_CONTRACT\\n"
                       "echo 'NX=20 NY=20 DGRID_KM=2.0 UTM_ZONE=13 UTM_HEM=N'\\n"
                       "echo 'NSSTA=2 NUSTA=2 HOURS=1'\\n"
                       "echo 'SS_IDS=7246901,7247001'\\n"
                       "echo 'US_IDS=12345,23456'\\nexit 0\\n")
        exe.chmod(0o700)
        req = self.plan(exe)
        res = execute_source_preflight(req)
        self.assertTrue(res["native_input_parsed"])
        self.assertFalse(res["model_executed"])
        self.assertFalse(res["ready"])
        self.assertEqual(res["scientific_acceptance"], "NOT_EVALUATED")

    def test_cli_dry_run_refuses_unparsed_g19_roles(self):
        proc = subprocess.run([
            sys.executable, "-m", "native_cpp.orchestration.p6_g19_handoff",
            "--case-yaml", str(self.c.yaml_path),
            "--p4-selection-root", str(self.c.p4),
            "--p5-selection-root", str(self.c.p5),
        ], capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertFalse(payload["native_input_parsed"])
        self.assertFalse(payload["model_executed"])
        self.deck.unlink()
        proc = subprocess.run([
            sys.executable, "-m", "native_cpp.orchestration.p6_g19_handoff",
            "--case-yaml", str(self.c.yaml_path),
            "--p4-selection-root", str(self.c.p4),
            "--p5-selection-root", str(self.c.p5),
        ], capture_output=True, text=True)
        self.assertEqual(proc.returncode, 2)
        self.assertEqual(json.loads(proc.stdout)["status"], "BLOCKED_P6_G19_DYNAMIC_INPUT")


if __name__ == "__main__":
    unittest.main()
