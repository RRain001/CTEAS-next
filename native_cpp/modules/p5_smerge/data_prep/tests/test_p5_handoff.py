"""#56 D4 source-only handoff contract tests, synthetic data not science."""
from __future__ import annotations

import csv
from pathlib import Path
import unittest

from native_cpp.modules.p5_smerge.data_prep.p5_handoff import build_p5_handoff, sha256
from native_cpp.modules.p5_smerge.data_prep.tests.test_case_archive_gate import P5ArchiveGateTests
from native_cpp.orchestration.plan import ContractError


class P5HandoffTests(unittest.TestCase):
    def setUp(self):
        self.fixture = P5ArchiveGateTests(methodName="test_single_station_evidence_is_software_only")
        self.fixture.setUp()
        self.fixture.manifest(2022, [self.fixture.station("58314099999", 2022)])
        self.producer = self.fixture.gate()
        self.case = self.fixture.root
        raw = self.case / "run/smerge/surf.dat"
        raw.parent.mkdir(parents=True)
        raw.write_bytes(b"SYNTHETIC RAW SURF FOR QA ONLY\n")
        published = self.case / "met/surface/final/surf.dat"
        published.parent.mkdir(parents=True)
        published.write_bytes(b"SYNTHETIC CLOUD-ADJUSTED SURF\n")
        self.csv = published.parent / "stations.csv"
        with self.csv.open("w", encoding="utf-8", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=[
                "station_id", "station_name", "lat", "lon", "xelev_m",
                "tz_hour", "anem_m", "source_file"])
            writer.writeheader()
            writer.writerow({
                "station_id": "583140", "station_name": "test", "lat": "31.939774444",
                "lon": "117.141610855", "xelev_m": "26", "tz_hour": "0",
                "anem_m": "10.0", "source_file": "met/surface/isd2smerge_ready/583140-99999.csv",
            })
        self.ready = self.case / "met/surface/isd2smerge_ready/583140-99999.csv"
        self.ready.parent.mkdir(parents=True)
        self.ready.write_bytes(b"SYNTHETIC GENERIC FOR PATH CUSTODY ONLY\\n")
        self.producer.update({
            "P5_NATIVE_SURF": "PRODUCED_UNVERIFIED",
            "ordered_ifstn": ["583140"],
            "raw_native_surf_sha256": sha256(raw),
            "published_surf_sha256": sha256(published),
            "produced_output_sha256": {
                "met/surface/final/stations.csv": sha256(self.csv),
                "met/surface/isd2smerge_ready/583140-99999.csv": sha256(self.ready),
            },
        })
        self.reader = {
            "source_reader": "PASS_SCOPED_INPUT_ONLY",
            "stdout_tail": (
                "PASS_P6G_REAL_NOAA_NATIVE_SURF_SOURCE_HOURLY "
                "HOURS=3 NSSTA=1 POPULATED_STATION_HOURS=2 "
                "MISSING_STATION_HOURS=1 VALID_WIND_STATION_HOURS=2 "
                "SS_IDS=583140 P6_PHYSICS=NOT_RUN"
            ),
        }

    def tearDown(self):
        self.fixture.tearDown()

    def test_station_annual_noaa_sha_and_distinct_raw_published_bytes(self):
        handoff = build_p5_handoff(self.case, self.producer, self.reader)
        self.assertTrue(handoff["handoff_validated"])
        self.assertEqual(handoff["hour_ending_records"], 3)
        self.assertEqual(handoff["ordered_ifstn"], ["583140"])
        self.assertEqual(handoff["annual_noaa_selections"][0]["primary_sid"], "58314099999")
        self.assertEqual(handoff["P5_TO_G19"], "NOT_RUN")
        self.assertNotEqual(handoff["raw_native_surf"]["sha256"],
                            handoff["published_surf"]["sha256"])
        self.assertFalse(handoff["science_acceptance"])

    def test_changed_noaa_or_surf_sha_rejected(self):
        source = self.case / "met/surface/isd_raw/58314099999-2022.csv"
        source.write_bytes(b"NOT ORIGINAL NO LONGER MATCHING CLAIM\n")
        with self.assertRaisesRegex(ContractError, "original NOAA source SHA changed"):
            build_p5_handoff(self.case, self.producer, self.reader)
        source.write_bytes(b"SYNTHETIC FULL ISD SOURCE\n")
        (self.case / "run/smerge/surf.dat").write_bytes(b"CHANGED SCIENCE\n")
        with self.assertRaisesRegex(ContractError, "SURF source custody changed"):
            build_p5_handoff(self.case, self.producer, self.reader)

    def test_bad_station_alias_and_case_sha_rejected(self):
        self.producer["ordered_ifstn"] = ["999999"]
        with self.assertRaisesRegex(ContractError, "station/time mismatch"):
            build_p5_handoff(self.case, self.producer, self.reader)
        self.producer["ordered_ifstn"] = ["583140"]
        self.producer["grid_sha256"] = "incorrect"
        with self.assertRaisesRegex(ContractError, "immutable B0 SHA mismatch"):
            build_p5_handoff(self.case, self.producer, self.reader)

    def test_station_coordinate_or_hourly_source_count_rejected(self):
        content = self.csv.read_text()
        self.csv.write_text(content.replace("31.939774444", "30.0"))
        self.producer["produced_output_sha256"]["met/surface/final/stations.csv"] = sha256(self.csv)
        with self.assertRaisesRegex(ContractError, "published coordinates differ"):
            build_p5_handoff(self.case, self.producer, self.reader)
        self.csv.write_text(content)
        self.producer["produced_output_sha256"]["met/surface/final/stations.csv"] = sha256(self.csv)
        self.reader["stdout_tail"] = self.reader["stdout_tail"].replace(
            "MISSING_STATION_HOURS=1", "MISSING_STATION_HOURS=0")
        with self.assertRaisesRegex(ContractError, "completeness count inconsistent"):
            build_p5_handoff(self.case, self.producer, self.reader)

    def test_station_generic_path_escape_or_changed_bytes_rejected(self):
        content = self.csv.read_text()
        self.csv.write_text(content.replace(
            "met/surface/isd2smerge_ready/583140-99999.csv", "../../other-case/station.csv"))
        self.producer["produced_output_sha256"]["met/surface/final/stations.csv"] = sha256(self.csv)
        with self.assertRaisesRegex(ContractError, "untrusted GENERIC"):
            build_p5_handoff(self.case, self.producer, self.reader)
        self.csv.write_text(content)
        self.producer["produced_output_sha256"]["met/surface/final/stations.csv"] = sha256(self.csv)
        self.ready.write_bytes(b"GENERATED FILE TAMPERED AFTER P5 PRODUCTION\\n")
        with self.assertRaisesRegex(ContractError, "GENERIC source SHA mismatch"):
            build_p5_handoff(self.case, self.producer, self.reader)

    def test_sparse_original_fortran_eof_adapter_is_hashed_and_allowed(self):
        # A secondary may point to the approved run/smerge EOF compatibility
        # adapter, not the immutable ready CSV. This is *not* a new hourly obs.
        rel = "run/smerge/original_smerge_sparse_runtime/583140-99999.csv"
        adapter = self.case / rel
        adapter.parent.mkdir(parents=True)
        adapter.write_bytes(b"SYNTHETIC ORIGINAL EOF ADAPTER ONLY\\n")
        content = self.csv.read_text()
        self.csv.write_text(content.replace(
            "met/surface/isd2smerge_ready/583140-99999.csv", rel))
        self.producer["produced_output_sha256"]["met/surface/final/stations.csv"] = sha256(self.csv)
        self.producer["produced_output_sha256"][rel] = sha256(adapter)
        self.assertTrue(build_p5_handoff(self.case, self.producer, self.reader)["handoff_validated"])
        adapter.write_bytes(b"TAMPERED ORIGINAL EOF ADAPTER\\n")
        with self.assertRaisesRegex(ContractError, "GENERIC source SHA mismatch"):
            build_p5_handoff(self.case, self.producer, self.reader)

    def test_source_reader_mismatch_or_annual_primary_drift_rejected(self):
        self.reader["stdout_tail"] = (
            self.reader["stdout_tail"].replace("HOURS=3", "HOURS=4")
            .replace("MISSING_STATION_HOURS=1", "MISSING_STATION_HOURS=2")
        )
        with self.assertRaisesRegex(ContractError, "station/time mismatch"):
            build_p5_handoff(self.case, self.producer, self.reader)
        self.reader["stdout_tail"] = (
            self.reader["stdout_tail"].replace("HOURS=4", "HOURS=3")
            .replace("MISSING_STATION_HOURS=2", "MISSING_STATION_HOURS=1")
        )
        self.producer["years"][0]["primary_sid"] = "nonexistent"
        with self.assertRaisesRegex(ContractError, "annual primary source"):
            build_p5_handoff(self.case, self.producer, self.reader)


if __name__ == "__main__":
    unittest.main()
