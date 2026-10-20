"""S2-B #169: P2-A B-0 orchestration *contract*, not Fortran science.

No original GLCC data is bundled. Native producer responses are deliberately
mocked for software/attestation negative tests; genuine 156 MB tests run in
the separate PR Actions job with pinned LFS source.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from native_cpp.orchestration import p2a_case_producer as producer
from native_cpp.orchestration.plan import ContractError


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class P2ACaseAdapterTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(prefix="s2b-p2a-admit-")
        self.addCleanup(tmp.cleanup)
        self.directory = Path(tmp.name)
        self.root = self.directory / "newsite_2022"
        (self.root / "grid").mkdir(parents=True)
        self.case = self.root / "case.yaml"
        self.grid = self.root / "grid/grid.cmn"
        self.time = self.root / "grid/research_time"
        self.img = self.directory / "synthetic.img"
        self.img.write_bytes(b"NO-REAL-GLCC-DATA")
        self.raw_bin = self.directory / "synthetic-raw-bin"
        self.lu_bin = self.directory / "synthetic-lu-bin"
        self.raw_bin.write_bytes(b"test binary placeholder")
        self.lu_bin.write_bytes(b"test writer placeholder")
        self.grid.write_text(
            "! IMAP = UTM !\n! DATUM = WGS-84 !\n! IUTMZN = 50 !\n"
            "! LSOHEM = N !\n! XREFKM = 510.885 !\n! YREFKM = 3531.269 !\n"
            "! DGRIDKM = 0.100 !\n! NX = 50 !\n! NY = 50 !\n"
            "! NZ = 1 !\n! ZFACE = 0 !\n! ZFACE = 100 !\n",
            encoding="utf-8")
        self.time.write_text("BEGIN:20221231-230000\nEND:20230101-020000\n",
                             encoding="utf-8")
        self.case.write_text(
            "case_name: newsite_2022\nsettings:\n  timezone: UTC+0000\n"
            "preprocess:\n  grid:\n    utm_zone: 50\n    hemisphere: N\n"
            "    nz: 1\n    resolution_km: 0.1\n"
            "    domain:\n      length_km: 5\n      width_km: 5\n"
            "    center:\n      latitude: 31.939774444\n"
            "      longitude: 117.141610855\n"
            "  research_time:\n    begin: 20221231-230000\n"
            "    end: 20230101-020000\n", encoding="utf-8")

    def invoke(self):
        return producer.produce(case_yaml=self.case, glcc_img=self.img,
                                raw_bin=self.raw_bin, lu_bin=self.lu_bin)

    def fake_native(self, command: list[str], root: Path, label: str) -> None:
        self.assertEqual(root, self.root)
        if "direct-LAEA" in label:
            self.assertEqual(command[-1], "--production-direct")
            self.assertEqual(command[3], "32650")
            self.assertEqual(command[4:6], ["510.885", "3531.269"])
            self.assertEqual(command[7:9], ["50", "50"])
            output = Path(command[2])
            output.mkdir()
            (output / producer.RAW_NAME).write_text("i,j,samples\n1,1,4\n")
            (output / producer.HITS_NAME).write_text("i,j,samples\n1,1,4\n")
            raw = {
                "producer": "cteas_p2_glcc_raw",
                "source_product": "USGS_GLCC_EURASIA_1992_1993_ORIGINAL_1KM",
                "source_sha256": producer.GLCC_SHA256,
                "source_size_bytes": producer.GLCC_SIZE_BYTES,
                "method": producer.METHOD_UTM50,
                "utm_epsg": 32650, "nx": 50, "ny": 50,
                "xrefkm": "510.885", "yrefkm": "3531.269",
                "mesh": 20, "dgridkm": 0.1,
                "fractions_filename": producer.RAW_NAME,
                "fractions_csv_sha256": sha(output / producer.RAW_NAME),
                "hits_csv_sha256": sha(output / producer.HITS_NAME),
                "included": 4,
                "evidence_status": "PRODUCED_UNVERIFIED",
                "official_GLAZAS_parity": "NOT_RUN",
                "lu_dat": "NOT_RUN", "p3_geo_dat": "NOT_RUN",
            }
            (output / "p2_manifest.json").write_text(json.dumps(raw))
        else:
            self.assertIn("GLCC D3", label)
            output = Path(command[-1])
            output.mkdir()
            (output / "lu.dat").write_text("SYNTHETIC LU NOT SCIENTIFIC\n")
            raw_output = Path(command[1]).parent
            d3 = {
                "producer": "cteas_p2_glcc_lu_dat",
                "source_kind": "P2_A_GLCC_HISTORICAL_24_TO_USGS92_38",
                "source_sha256": producer.GLCC_SHA256,
                "input_d1_csv_sha256": sha(raw_output / producer.RAW_NAME),
                "input_d1_method": producer.METHOD_UTM50,
                "rows": 2500, "classes": 38, "total_samples": 4,
                "evidence_status": "PRODUCED_UNVERIFIED",
                "original_GLAZAS_parity": "NOT_RUN",
                "p3_geo_dat": "NOT_RUN",
                "lu_dat_sha256": sha(output / "lu.dat"),
            }
            if getattr(self, "tamper", False):
                d3["rows"] = 2499
            (output / "p2_d3_manifest.json").write_text(json.dumps(d3))

    def test_unpinned_fake_source_is_never_accepted(self):
        with self.assertRaisesRegex(ContractError, "official 156MB"):
            self.invoke()
        self.assertFalse((self.root / "geo").exists())

    def test_b0_grid_case_disagreement_blocks_before_source(self):
        self.grid.write_text(self.grid.read_text().replace("510.885", "510.886"))
        with self.assertRaisesRegex(ContractError, "mismatch|disagreement"):
            self.invoke()
        self.assertFalse((self.root / "geo").exists())

    def test_case_manifest_and_byte_sha_staged_with_mocked_native_only(self):
        with patch.object(producer, "GLCC_SIZE_BYTES", self.img.stat().st_size), \
             patch.object(producer, "GLCC_SHA256", sha(self.img)), \
             patch.object(producer, "_run", side_effect=self.fake_native):
            record = self.invoke()
            self.assertEqual(record["status"], "P2A_GENERIC_CASE_PRODUCED_UNVERIFIED")
            self.assertEqual((record["nx"], record["ny"], record["mesh"]), (50, 50, 20))
            self.assertEqual(record["original_science"], "NOT_RUN")
            self.assertEqual(record["method"], producer.METHOD_UTM50)
            self.assertEqual((record["research_begin_utc"], record["research_end_utc"]),
                             ("20221231-230000", "20230101-020000"))
            self.assertEqual(record, json.loads((self.root / "evidence/p2.json").read_text()))
            self.assertEqual(record["lu_dat_sha256"], sha(
                self.root / "geo/ctgproc/p2a_case/lu/lu.dat"))
            with self.assertRaisesRegex(ContractError, "already used"):
                self.invoke()

    def test_inconsistent_native_manifest_blocks_evidence_publish(self):
        self.tamper = True
        with patch.object(producer, "GLCC_SIZE_BYTES", self.img.stat().st_size), \
             patch.object(producer, "GLCC_SHA256", sha(self.img)), \
             patch.object(producer, "_run", side_effect=self.fake_native):
            with self.assertRaisesRegex(ContractError, "D3 LU manifest disagrees"):
                self.invoke()
        self.assertFalse((self.root / "evidence/p2.json").exists())

    def test_over_budget_grid_is_not_ran(self):
        self.grid.write_text(self.grid.read_text().replace("NX = 50", "NX = 600")
                             .replace("NY = 50", "NY = 500"))
        self.case.write_text(self.case.read_text()
                             .replace("length_km: 5", "length_km: 60")
                             .replace("width_km: 5", "width_km: 50"))
        with self.assertRaisesRegex(ContractError, "250000-cell"):
            self.invoke()


if __name__ == "__main__":
    unittest.main()
