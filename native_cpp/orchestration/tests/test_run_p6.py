"""Isolated execution-control tests: never runs CALMET physics."""
from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from subprocess import CompletedProcess

from native_cpp.orchestration.plan import CASE_ID, ContractError
from native_cpp.orchestration.run_p6 import BINARIES, execute, prepare


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class P6ScopedRunnerTests(unittest.TestCase):
    def setUp(self) -> None:
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.base = Path(temp.name)
        self.root = self.base / CASE_ID
        self.root.mkdir()
        self.case_yaml = self.root / "case.yaml"
        self.case_yaml.write_text("not-a-real-case: mock\n", encoding="utf-8")
        self.manifest = self.base / "manifest.json"
        self.manifest.write_text("{}", encoding="utf-8")
        self.work = self.base / "p6_work"
        self.executable = self.base / "fake_native_executable"
        self.executable.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        self.executable.chmod(0o700)
        self.bin6 = {role: self.executable for role in BINARIES}
        self.bin143 = {**self.bin6, "p6f_writer": self.executable}
        self.planner = patch(
            "native_cpp.orchestration.run_p6.plan_case",
            return_value={"case_yaml_sha256": "0" * 64},
        )
        self.artifacts = patch(
            "native_cpp.orchestration.run_p6.preflight",
            return_value={"verified_artifacts": {"p3_geo": {"sha256": "1" * 64}}},
        )
        self.planner.start()
        self.artifacts.start()
        self.addCleanup(self.planner.stop)
        self.addCleanup(self.artifacts.stop)

    def request(self, hours: int = 6) -> dict:
        return prepare(self.case_yaml, self.manifest, self.work,
                       self.bin143 if hours == 143 else self.bin6, hours)

    def test_dry_plan_contains_no_original_met_reliance(self) -> None:
        doc = self.request()
        self.assertEqual(doc["status"], "P6_LAUNCH_PLAN_NOT_EXECUTED")
        self.assertIn("--p6e-source-builder", doc["command"])
        self.assertNotIn("--p6f-direct-hourly", doc["command"])
        self.assertFalse(doc["model_executed"])
        self.assertFalse(doc["legacy_fallback"])
        self.assertFalse(self.work.exists())

    def test_full_143_hour_stages_independent_header(self) -> None:
        doc = self.request(143)
        self.assertIn("--p6f-direct-hourly", doc["command"])
        self.assertIn("--p6f-writer", doc["command"])
        self.assertEqual(doc["hours"], 143)

    def test_wrong_binary_or_hours_refused(self) -> None:
        with self.assertRaises(ContractError):
            prepare(self.case_yaml, self.manifest, self.work, self.bin6, 143)
        with self.assertRaises(ContractError):
            prepare(self.case_yaml, self.manifest, self.work, self.bin6, 144)
        with self.assertRaises(ContractError):
            prepare(self.case_yaml, self.manifest, self.work,
                    {**self.bin6, "p6f_writer": self.executable}, 6)

    def test_original_reference_met_forbidden(self) -> None:
        ref = self.root / "run/met/met.dat"
        ref.parent.mkdir(parents=True)
        ref.write_bytes(b"frozen original")
        with self.assertRaisesRegex(ContractError, "BLOCKED_ORIGINAL_MET_DEPENDENCY"):
            self.request()

    def test_existing_workdir_and_case_overlap_refused(self) -> None:
        self.work.mkdir()
        with self.assertRaisesRegex(ContractError, "work must be"):
            self.request()
        self.work.rmdir()
        with self.assertRaisesRegex(ContractError, "overlap"):
            prepare(self.case_yaml, self.manifest, self.root / "bad",
                    self.bin6, 6)

    def fake_run(self, args: list[str], independent: bool = False) -> CompletedProcess:
        self.work.mkdir()
        met = self.work / "native_causal_calmet.dat"
        met.write_bytes(b"native-hour-field-payload")
        original = {
            "hours_completed": 143 if independent else 6,
            "native_wind": True,
            "native_previous_hour_comp_state": True,
            "original_met_role": "NOT_REQUIRED_NOT_OPENED_BY_NATIVE_EXECUTION",
            "p6e_reference_is_geo_deck_metadata_only": True,
            "native_calmet_dat_sha256": digest(met.read_bytes()),
            "p6f_header_from_native_hour_manifest": independent,
        }
        if independent:
            native = self.work / "native_causal_independent_header_calmet.dat"
            native.write_bytes(b"independent-native-header")
            original["independent_p6f_header_sha256"] = digest(native.read_bytes())
        (self.work / "native_cpp_hourly_manifest.json").write_text(
            json.dumps(original), encoding="utf-8"
        )
        return CompletedProcess(args, 0, stdout="ok", stderr="")

    def test_fake_success_still_not_science_accepted(self) -> None:
        req = self.request()
        with patch("native_cpp.orchestration.run_p6.subprocess.run",
                   side_effect=lambda a, **k: self.fake_run(a)):
            result = execute(req)
        self.assertEqual(result["status"], "P6_EXECUTED_SCIENCE_NOT_ACCEPTED")
        self.assertEqual(result["scientific_acceptance"], "NOT_EVALUATED")
        self.assertTrue((self.work / "s2c_execution_evidence.json").is_file())

    def test_143_fake_header_check(self) -> None:
        req = self.request(143)
        with patch("native_cpp.orchestration.run_p6.subprocess.run",
                   side_effect=lambda a, **k: self.fake_run(a, independent=True)):
            result = execute(req)
        self.assertEqual(result["hours_completed"], 143)
        self.assertEqual(result["scientific_acceptance"], "NOT_EVALUATED")
        self.assertIn("independent_native_met_sha256", result)

    def test_nonzero_exit_refuses_publishing(self) -> None:
        req = self.request()
        with patch("native_cpp.orchestration.run_p6.subprocess.run",
                   return_value=CompletedProcess([], 3)):
            with self.assertRaisesRegex(ContractError, "exit 3"):
                execute(req)
        self.assertFalse((self.work / "s2c_execution_evidence.json").exists())


if __name__ == "__main__":
    unittest.main()
