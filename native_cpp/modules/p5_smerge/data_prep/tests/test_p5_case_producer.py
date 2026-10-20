"""P5 #56 D1-B isolated path/control and source-hour preflight software tests.

All fixture NOAA bytes are synthetic and MUST NOT constitute scientific PASS.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from native_cpp.modules.p5_smerge.data_prep import p5_case_producer as p
from native_cpp.modules.p5_smerge.data_prep import p5_case_paths
from native_cpp.modules.p5_smerge.data_prep.tests.test_case_archive_gate import P5ArchiveGateTests
from native_cpp.orchestration.plan import ContractError


class P5ProducerContractTests(unittest.TestCase):
    def setUp(self):
        self.fixture = P5ArchiveGateTests(methodName="test_single_station_evidence_is_software_only")
        self.fixture.setUp()
        self.row = self.fixture.station("58314099999", 2022)
        self.fixture.manifest(2022, [self.row])
        self.root = self.fixture.root
        self.native = Path(self.fixture.tmp.name) / "native"
        self.native.write_bytes(b"FAKE-BIN - admission tests do NOT execute")
        self.template = Path(self.fixture.tmp.name) / "template.inp"
        self.template.write_text("SYNTHETIC - not executable SMERGE control", encoding="utf-8")

    def tearDown(self):
        self.fixture.tearDown()

    def test_admitted_preselected_source_hours_recount_no_write(self):
        with (patch.object(p, "original_coverage", return_value=(8000, 8760)),
              patch.object(p, "lite_time_coverage", return_value=(8100, 8760))):
            result = p.produce(self.fixture.case, self.fixture.history,
                               self.native, self.template, admit_only=True)
        self.assertEqual(result["status"], "INPUT_CHECKED")
        self.assertEqual(result["P5_NATIVE_SURF"], "NOT_RUN")
        self.assertEqual(result["P5_GENERIC_CASE_EXECUTION"], "NOT_RUN")
        self.assertEqual(result["P5_SOURCE_SELECTION"], "PRESELECTED_MANIFEST_RAW_HOURS_RECOUNTED")
        self.assertEqual(result["independent_raw_hour_coverage"]["58314099999/2022"]["raw_source_recount"], "PASS")
        self.assertFalse((self.root / "run/smerge").exists())
        self.assertFalse((self.root / "evidence/p5.json").exists())

    def test_recount_rejects_declared_coverage_mismatch(self):
        with (patch.object(p, "original_coverage", return_value=(7999, 8760)),
              patch.object(p, "lite_time_coverage", return_value=(8100, 8760))):
            with self.assertRaisesRegex(ContractError, "differs from actual"):
                p.preflight(self.fixture.case, self.fixture.history, self.native, self.template)

    def test_fresh_outputs_and_preexisting_evidence_fail_closed(self):
        run = self.root / "run/smerge"
        run.mkdir(parents=True)
        with self.assertRaisesRegex(ContractError, "fresh output"):
            p.preflight(self.fixture.case, self.fixture.history, self.native, self.template)
        run.rmdir()
        evidence = self.root / "evidence"
        evidence.mkdir()
        (evidence / "p5.json").write_text("{}")
        with self.assertRaisesRegex(ContractError, "fresh output"):
            p.preflight(self.fixture.case, self.fixture.history, self.native, self.template)

    def test_stage_env_does_not_choose_global_project_current(self):
        with patch.dict(os.environ, {
            p5_case_paths.ROOT_ENV: str(self.root),
            p5_case_paths.HISTORY_ENV: str(self.fixture.history),
        }):
            self.assertEqual(p5_case_paths.case_root(), self.root)
            self.assertEqual(p5_case_paths.history_file(), self.fixture.history)
        other = Path(self.fixture.tmp.name) / "missing"
        with patch.dict(os.environ, {
            p5_case_paths.ROOT_ENV: str(other),
            p5_case_paths.HISTORY_ENV: str(self.fixture.history),
        }):
            with self.assertRaisesRegex(ValueError, "independent case"):
                p5_case_paths.case_root()

    def test_isolated_environment_cannot_silently_use_default_project_or_history(self):
        # Any one-sided staging declaration used to fall back to
        # project/current or the engine's default ISD station history.
        for name,value in (
            (p5_case_paths.ROOT_ENV, str(self.root)),
            (p5_case_paths.HISTORY_ENV, str(self.fixture.history)),
        ):
            with self.subTest(variable=name), patch.dict(os.environ, {name: value}, clear=True):
                with self.assertRaisesRegex(ValueError, "declared together"):
                    p5_case_paths.case_root()
                with self.assertRaisesRegex(ValueError, "declared together"):
                    p5_case_paths.history_file()
        with patch.dict(os.environ, {
            p5_case_paths.ROOT_ENV: str(self.root),
            p5_case_paths.HISTORY_ENV: "",
        }, clear=True):
            with self.assertRaisesRegex(ValueError, "cannot be empty"):
                p5_case_paths.case_root()
            with self.assertRaisesRegex(ValueError, "cannot be empty"):
                p5_case_paths.history_file()

    def test_control_clock_and_alias_and_original_options(self):
        start = "2022"
        controls = [
            "! JDAT = 8 !", "! IOFORM = 2 !", "! IOPACK = 0 !",
            "! LPREV = F !", "! LPCALC = F !", "! ABTZ = UTC+0000 !",
            "! NFF = 1 !",
            "! IBYR = 2022 !", "! IBMO = 1 !", "! IBDY = 1 !",
            "! IBHR = 0 !", "! IBSEC = 0 !",
            "! IEYR = 2022 !", "! IEMO = 1 !", "! IEDY = 1 !",
            "! IEHR = 3 !", "! IESEC = 0 !",
            "! SFCMET = station.csv !", "! IFSTN = 583140 !",
            "! XELEV = 20 !", "! ASTZ = UTC+0000 ! !END!",
        ]
        control = Path(self.fixture.tmp.name) / "valid.inp"
        control.write_text("\n".join(controls) + "\n")
        from datetime import datetime
        first, last = datetime(2022, 1, 1, 0), datetime(2022, 1, 1, 3)
        self.assertEqual(p.check_hour_ending_control(control, first, last, {"583140"}), ["583140"])
        text = control.read_text()
        control.write_text(text.replace("! IEHR = 3 !", "! IEHR = 2 !"))
        with self.assertRaisesRegex(ContractError, "end clock"):
            p.check_hour_ending_control(control, first, last, {"583140"})
        control.write_text(text.replace("! IOFORM = 2 !", "! IOFORM = 1 !"))
        with self.assertRaisesRegex(ContractError, "unsupported SMERGE option"):
            p.check_hour_ending_control(control, first, last, {"583140"})
        control.write_text(text)
        with self.assertRaisesRegex(ContractError, "identities inconsistent"):
            p.check_hour_ending_control(control, first, last, {"999999"})

    def test_staged_case_input_symlinks_denied(self):
        staged = self.root / "met/surface/isd_raw/isd_lite/583140-99999-2022.gz"
        staged.unlink()
        staged.symlink_to(self.template)
        with self.assertRaisesRegex(ContractError, "symlink"):
            p.preflight(self.fixture.case, self.fixture.history, self.native, self.template)


if __name__ == "__main__":
    unittest.main()
