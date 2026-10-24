"""Offline policy tests: exact-SHA Ubuntu native full never substitutes science."""
from pathlib import Path
import json
import tempfile
import unittest
from unittest import mock

from scripts.ci import cteas_native_full as native


class NativeFullEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.worktree = self.root / "worktree"
        (self.worktree / "native_cpp").mkdir(parents=True)
        (self.worktree / "native_cpp" / "CMakeLists.txt").write_text("project(native)\n")
        self.sha = "a" * 40
        self.report = self.root / "run"
        self.report.mkdir()
        self.manifest = self.report / "manifest.json"
        self.record = {
            "profile": native.PROFILE,
            "context": native.CONTEXT,
            "source_sha": self.sha,
            "worktree": str(self.worktree),
            "run_id": "native-test",
            "jobs": 3,
            "python_executable": "/usr/bin/python3",
            "status": "PASS_SOFTWARE_SCOPED",
            "exit_code": 0,
            "scientific_acceptance": "NOT_RUN",
            "docker_delivery": "DEFERRED_UNTIL_POST_S5",
            "steps": [],
        }
        for name, cmd in native.commands(self.worktree, self.report / "build", 3, "/usr/bin/python3"):
            log = self.report / (name + ".log")
            log.write_text("PASS " + name + "\n")
            self.record["steps"].append({
                "name": name, "command": cmd, "exit_code": 0,
                "log_sha256": native.digest(log),
            })
        self.patcher = mock.patch.object(native, "clean_sha", return_value=self.sha)
        self.patcher.start()
        self.addCleanup(self.patcher.stop)
        self.save()

    def save(self):
        self.manifest.write_text(json.dumps(self.record))

    def test_exact_sha_complete_software_receipt(self):
        self.assertEqual(native.verify(self.manifest, self.sha)["source_sha"], self.sha)

    def test_missing_required_step_rejected(self):
        self.record["steps"].pop()
        self.save()
        with self.assertRaisesRegex(ValueError, "required steps"):
            native.verify(self.manifest)

    def test_failed_test_rejected(self):
        self.record["steps"][0]["exit_code"] = 1
        self.save()
        with self.assertRaisesRegex(ValueError, "Failed"):
            native.verify(self.manifest)

    def test_modified_test_command_rejected(self):
        self.record["steps"][2]["command"] = ["true"]
        self.save()
        with self.assertRaisesRegex(ValueError, "command list"):
            native.verify(self.manifest)

    def test_modified_log_rejected(self):
        (self.report / "ctest-all.log").write_text("edited")
        with self.assertRaisesRegex(ValueError, "modified native full log"):
            native.verify(self.manifest)

    def test_old_sha_rejected(self):
        with self.assertRaisesRegex(ValueError, "differ"):
            native.verify(self.manifest, "b" * 40)

    def test_scientific_claim_rejected(self):
        self.record["scientific_acceptance"] = "PASS"
        self.save()
        with self.assertRaisesRegex(ValueError, "cannot assert"):
            native.verify(self.manifest)

    def test_docker_claim_rejected(self):
        self.record["docker_delivery"] = "PASS"
        self.save()
        with self.assertRaisesRegex(ValueError, "not Docker"):
            native.verify(self.manifest)

    def test_partial_smoke_not_accepted(self):
        self.record["status"] = "DEV_PASS"
        self.save()
        with self.assertRaisesRegex(ValueError, "not successful"):
            native.verify(self.manifest)

    def test_dirty_worktree_rejected(self):
        self.patcher.stop()
        with mock.patch.object(native, "git", side_effect=["a" * 40, " M scripts/s4/test.py"]):
            with self.assertRaisesRegex(ValueError, "clean committed"):
                native.clean_sha(self.worktree)
        self.patcher.start()


if __name__ == "__main__":
    unittest.main()
