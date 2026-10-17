"""Portable negative/positive tests for the S2 read-only handoff integrity gate."""
from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from native_cpp.orchestration.handoff_gate import EXPECTED, PROFILE, preflight
from native_cpp.orchestration.plan import CASE_ID, ContractError


class HandoffGateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.root = self.base / "scratch"
        self.root.mkdir()
        self.manifest = self.base / "manifest.json"

    def seed(self, consumer: str = "p6") -> dict:
        artifacts = {}
        for role, (path, producer) in EXPECTED[consumer].items():
            data = (role + "\n" + consumer + "\n").encode()
            target = self.root / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
            artifacts[role] = {
                "path": path, "sha256": hashlib.sha256(data).hexdigest(),
                "bytes": len(data), "producer": producer,
            }
        doc = {
            "schema_version": 1,
            "case_name": CASE_ID,
            "science_profile": PROFILE,
            "source_head": "8db06be2884b620955a11b32e444396e4bbeef29",
            "artifacts": artifacts,
        }
        self.save(doc)
        return doc

    def save(self, document: dict) -> None:
        self.manifest.write_text(json.dumps(document), encoding="utf-8")

    def test_native_p6_artifacts_only_no_execution(self) -> None:
        self.seed()
        result = preflight(self.root, self.manifest, "p6")
        self.assertEqual(result["status"], "INPUT_INTEGRITY_VERIFIED_ONLY")
        self.assertEqual(len(result["verified_artifacts"]), 6)
        self.assertFalse(result["model_executed"])
        self.assertFalse(result["ready_to_execute"])
        self.assertEqual(result["scientific_acceptance"], "NOT_EVALUATED")

    def test_p7_has_different_required_roles(self) -> None:
        self.seed("p7")
        self.assertEqual(len(preflight(self.root, self.manifest, "p7")["verified_artifacts"]), 2)
        with self.assertRaises(ContractError):
            preflight(self.root, self.manifest, "p6")

    def test_absent_station_metadata_refused(self) -> None:
        doc = self.seed()
        path = self.root / doc["artifacts"]["p5_station_metadata"]["path"]
        path.unlink()
        with self.assertRaisesRegex(ContractError, "absent"):
            preflight(self.root, self.manifest, "p6")
        self.seed()
        doc = json.loads(self.manifest.read_text(encoding="utf-8"))
        path = self.root / doc["artifacts"]["p4_station_metadata"]["path"]
        path.write_bytes(b"wrong station")
        with self.assertRaisesRegex(ContractError, "bytes/hash mismatch"):
            preflight(self.root, self.manifest, "p6")

    def test_corrupted_scientific_input_refused(self) -> None:
        doc = self.seed()
        (self.root / doc["artifacts"]["p3_geo"]["path"]).write_bytes(b"not-accepted")
        with self.assertRaisesRegex(ContractError, "bytes/hash mismatch"):
            preflight(self.root, self.manifest, "p6")

    def test_wrong_producer_and_out_of_scope_refused(self) -> None:
        doc = self.seed()
        doc["artifacts"]["p4_upper"]["producer"] = "ORIGINAL_FORTRAN"
        self.save(doc)
        with self.assertRaises(ContractError):
            preflight(self.root, self.manifest, "p6")
        doc["artifacts"]["p4_upper"]["producer"] = "P4_NATIVE"
        doc["science_profile"] = "HEFEI_2022_WET"
        self.save(doc)
        with self.assertRaises(ContractError):
            preflight(self.root, self.manifest, "p6")

    def test_no_missing_roles_or_unexpected_fields(self) -> None:
        doc = self.seed()
        del doc["artifacts"]["p5_surface"]
        self.save(doc)
        with self.assertRaises(ContractError):
            preflight(self.root, self.manifest, "p6")
        doc = self.seed()
        doc["legacy_fallback"] = True
        self.save(doc)
        with self.assertRaises(ContractError):
            preflight(self.root, self.manifest, "p6")

    def test_path_traversal_and_symlink_refused(self) -> None:
        doc = self.seed()
        doc["artifacts"]["p3_geo"]["path"] = "../geo.dat"
        self.save(doc)
        with self.assertRaises(ContractError):
            preflight(self.root, self.manifest, "p6")
        doc = self.seed()
        link = self.root / doc["artifacts"]["p3_geo"]["path"]
        link.unlink()
        try:
            link.symlink_to(self.manifest)
        except (NotImplementedError, OSError):
            self.skipTest("symlinks unavailable on this host")
        with self.assertRaises(ContractError):
            preflight(self.root, self.manifest, "p6")

    def test_noncanonical_manifest_and_empty_input_refused(self) -> None:
        doc = self.seed()
        doc["schema_version"] = True
        self.save(doc)
        with self.assertRaises(ContractError):
            preflight(self.root, self.manifest, "p6")
        doc = self.seed()
        doc["artifacts"]["p3_geo"]["bytes"] = 0
        self.save(doc)
        with self.assertRaises(ContractError):
            preflight(self.root, self.manifest, "p6")


if __name__ == "__main__":
    unittest.main()
