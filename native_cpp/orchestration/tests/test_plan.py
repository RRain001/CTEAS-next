"""S2-2A1 read-only planner tests; no original vendor or GUI dependency."""
from __future__ import annotations
import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

from native_cpp.orchestration.plan import CASE_ID, ContractError, plan_case

ROOT = Path(__file__).resolve().parents[3]
FROZEN = ROOT / "project" / "cases" / CASE_ID / "case.yaml"


class NativeCasePlanTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.frozen = yaml.safe_load(FROZEN.read_text())

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / CASE_ID
        self.root.mkdir()
        self.yaml = self.root / "case.yaml"

    def put(self, data=None):
        self.yaml.write_text(yaml.safe_dump(self.frozen if data is None else data))
        return self.yaml

    def test_valid_frozen_plan_is_never_executable(self):
        result = plan_case(self.put())
        self.assertEqual(result["case_name"], CASE_ID)
        self.assertEqual(result["grid"]["nx"], 50)
        self.assertEqual(result["status"], "DRY_RUN_ONLY_EXECUTION_BLOCKED")
        self.assertFalse(result["ready"])
        self.assertFalse(result["legacy_fallback"])
        self.assertFalse(result["outputs_published"])
        self.assertEqual(len(result["stages"]), 7)
        self.assertTrue(all(x["status"] == "BLOCKED" and not x["execute"]
                            for x in result["stages"]))
        self.assertEqual([x["id"] for x in result["stages"]],
                         ["p1", "p2", "p3", "p4", "p5", "p6", "p7"])
        self.assertEqual([x["dependencies"] for x in result["stages"] if x["id"] == "p6"],
                         [["p3", "p4", "p5"]])
        self.assertEqual(sorted(p.name for p in self.root.iterdir()), ["case.yaml"])

    def test_source_data_is_not_mutated(self):
        original = FROZEN.read_bytes()
        result = plan_case(FROZEN)
        self.assertEqual(FROZEN.read_bytes(), original)
        self.assertEqual(len(result["case_yaml_sha256"]), 64)

    def test_reject_other_case_identity(self):
        case = copy.deepcopy(self.frozen)
        case["case_name"] = "another_case"
        with self.assertRaisesRegex(ContractError, "supported frozen"):
            plan_case(self.put(case))

    def test_reject_grid_and_crs_outside_scope(self):
        case = copy.deepcopy(self.frozen)
        case["preprocess"]["grid"]["nz"] = 11
        with self.assertRaisesRegex(ContractError, "frozen Hefei"):
            plan_case(self.put(case))

    def test_reject_unsupported_rainfall_and_wet_deposition(self):
        for group, key in (("met", "npsta"), ("puff", "iwet")):
            case = copy.deepcopy(self.frozen)
            case[group]["options"][key] = 1
            with self.subTest(group=group):
                with self.assertRaisesRegex(ContractError, "frozen Hefei"):
                    plan_case(self.put(case))

    def test_reject_time_window_change(self):
        case = copy.deepcopy(self.frozen)
        case["preprocess"]["research_time"]["end"] = "20220107-000000"
        with self.assertRaisesRegex(ContractError, "reference window"):
            plan_case(self.put(case))

    def test_reject_station_change(self):
        case = copy.deepcopy(self.frozen)
        case["preprocess"]["upperair"]["station_id"] = "CHM00000001"
        with self.assertRaisesRegex(ContractError, "station"):
            plan_case(self.put(case))

    def test_reject_source_change(self):
        case = copy.deepcopy(self.frozen)
        case["puff"]["point_sources"][0]["stack_height_m"] = 51
        with self.assertRaisesRegex(ContractError, "frozen Hefei"):
            plan_case(self.put(case))

    def test_reject_path_traversal(self):
        case = copy.deepcopy(self.frozen)
        case["paths"]["run_met_dir"] = "project/current/../../../private"
        with self.assertRaisesRegex(ContractError, "escapes"):
            plan_case(self.put(case))

    def test_reject_nonfinite_and_boolean_dimensions(self):
        for value in (float("nan"), True):
            case = copy.deepcopy(self.frozen)
            case["preprocess"]["grid"]["nz"] = value
            with self.subTest(value=repr(value)):
                with self.assertRaises(ContractError):
                    plan_case(self.put(case))

    def test_cli_valid_is_json_and_invalid_fails_closed(self):
        proc = subprocess.run(
            [sys.executable, "-m", "native_cpp.orchestration.plan",
             "--case-yaml", str(self.put())], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertFalse(json.loads(proc.stdout)["ready"])
        proc = subprocess.run(
            [sys.executable, "-m", "native_cpp.orchestration.plan",
             "--case-yaml", str(self.root / "missing.yaml")], cwd=ROOT,
            capture_output=True, text=True)
        self.assertEqual(proc.returncode, 2, proc.stderr)
        self.assertEqual(json.loads(proc.stdout)["status"], "BLOCKED_INVALID_OR_UNSUPPORTED_CASE")


if __name__ == "__main__":
    unittest.main()
