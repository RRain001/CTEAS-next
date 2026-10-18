"""#56 D2-A original NOAA selector offline transport: synthetic software tests only."""
from __future__ import annotations

import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

from native_cpp.modules.p5_smerge.data_prep import download_isd_by_grid as p5
from native_cpp.modules.p5_smerge.data_prep import isd_lite_wind as lite
from native_cpp.modules.p5_smerge.data_prep import p5_case_producer as producer
from native_cpp.orchestration.plan import ContractError
from native_cpp.modules.p5_smerge.data_prep.tests.test_case_archive_gate import P5ArchiveGateTests


class P5OfflineSelectionTests(unittest.TestCase):
    def setUp(self):
        self.fixture = P5ArchiveGateTests(methodName="test_single_station_evidence_is_software_only")
        self.fixture.setUp()
        self.root = self.fixture.root
        self.raw = self.fixture.raw
        (self.root / "grid/center_location").write_text(
            "latitude: 31.939774444\nlongitude: 117.141610855\n", encoding="utf-8")
        self.in1 = p5.Station("58314099999", 31.939774444, 117.141610855, 26.,
                              "in1", "CH", "20200101", "20251231")
        self.in2 = p5.Station("58321099999", 31.939774444, 117.142610855, 26.,
                              "in2", "CH", "20200101", "20251231")
        self.out1 = p5.Station("61234099999", 32.6, 116.0, 26.,
                               "out1", "CH", "20200101", "20251231")
        self.out2 = p5.Station("61235099999", 33.6, 115.0, 26.,
                               "out2", "CH", "20200101", "20251231")

    def tearDown(self):
        self.fixture.tearDown()

    def archive(self, station, year=2022):
        (self.raw / f"{station.sid}-{year}.csv").write_bytes(b"synthetic full ISD\n")
        (self.raw / "isd_lite" / lite.filename(station.sid, year)).write_bytes(b"synthetic lite\n")

    def select(self, stations, *, coverage=None):
        coverage = coverage or {}
        argv = ["download_isd_by_grid", "--offline",
                "--grid-file", str(self.root / "grid/grid.cmn"),
                "--center-file", str(self.root / "grid/center_location"),
                "--research-time-file", str(self.root / "grid/research_time"),
                "--history-file", str(self.fixture.history),
                "--out-dir", str(self.raw),
                "--stack-lat", "31.939774444", "--stack-lon", "117.141610855"]
        def full(path, year, sid):
            hours = p5.expected_hours_in_year(year)
            return coverage.get((sid, year, "full"), 8000), hours
        def wind(path, year, sid):
            hours = p5.expected_hours_in_year(year)
            return coverage.get((sid, year, "lite"), 8100), hours
        with (patch.object(p5, "parse_history_txt", return_value=stations),
              patch.object(p5, "original_coverage", side_effect=full),
              patch.object(lite, "lite_time_coverage", side_effect=wind),
              patch.object(p5, "download_one", side_effect=AssertionError("NETWORK-FULL")),
              patch.object(lite, "download_lite_one", side_effect=AssertionError("NETWORK-LITE")),
              patch.object(sys, "argv", argv)):
            return p5.main()

    def test_leap_year_crossyear_primary_switch_stable_ifstn(self):
        # 2024 is leap-year: 8784 original UTC hours. Both real-format
        # source products remain associated with their original station IDs.
        time = self.root / "grid/research_time"
        time.write_text("BEGIN:20231231-230000\nEND:20240301-010000\n")
        for yr in (2023, 2024):
            for station in (self.in1, self.in2):
                self.archive(station, yr)
        self.assertEqual(self.select([self.in1, self.in2], coverage={
            (self.in1.sid, 2023, "full"): 8580,
            (self.in1.sid, 2023, "lite"): 8600,
            (self.in2.sid, 2023, "full"): 8300,
            (self.in2.sid, 2023, "lite"): 8300,
            (self.in1.sid, 2024, "full"): 8350,
            (self.in1.sid, 2024, "lite"): 8400,
            (self.in2.sid, 2024, "full"): 8700,
            (self.in2.sid, 2024, "lite"): 8750,
        }), 0)
        selection = [json.loads((self.raw / f"station_selection_{yr}.json").read_text())
                     for yr in (2023, 2024)]
        self.assertEqual([p["primary_sid"] for p in selection],
                         [self.in1.sid, self.in2.sid])
        self.assertEqual({r["ifstn"] for r in selection[0]["stations"]},
                         {r["ifstn"] for r in selection[1]["stations"]})
        self.assertTrue(all(r["expected_hours"] == 8784
                            for r in selection[1]["stations"]))
        self.assertEqual(
            [[r["sid"] for r in p["stations"]
              if r["wind_treatment"] == "COMPLETE_FILL_AND_CALM_REPLACE"]
             for p in selection],
            [[self.in1.sid], [self.in2.sid]]
        )

    def test_leap_year_virtual_90_percent_exact_gate(self):
        # Strict 90% of 8784 requires at least 7906 unique original hours.
        (self.root / "grid/research_time").write_text(
            "BEGIN:20240228-000000\nEND:20240301-000000\n")
        self.archive(self.out1, 2024)
        with self.assertRaisesRegex(SystemExit, "source selection failed"):
            self.select([self.out1], coverage={
                (self.out1.sid, 2024, "full"): 7905,
                (self.out1.sid, 2024, "lite"): 8500,
            })
        self.assertEqual(self.select([self.out1], coverage={
            (self.out1.sid, 2024, "full"): 7906,
            (self.out1.sid, 2024, "lite"): 8500,
        }), 0)
        mf = json.loads((self.raw / "station_selection_2024.json").read_text())
        self.assertEqual(mf["mode"], "VIRTUAL_RELOCATED")
        self.assertEqual(mf["stations"][0]["expected_hours"], 8784)

    def test_one_and_three_in_domain_stations_without_fixed_cap(self):
        self.archive(self.in1)
        self.assertEqual(self.select([self.in1]), 0)
        one = json.loads((self.raw / "station_selection_2022.json").read_text())
        self.assertEqual(len(one["stations"]), 1)
        third = p5.Station("58322099999", 31.939774444, 117.143610855,
                           26., "in3", "CH", "20200101", "20251231")
        self.archive(self.in2)
        self.archive(third)
        self.assertEqual(self.select([self.in1, self.in2, third]), 0)
        many = json.loads((self.raw / "station_selection_2022.json").read_text())
        self.assertEqual(len(many["stations"]), 3)
        self.assertEqual(len({r["ifstn"] for r in many["stations"]}), 3)

    def test_generic_reselection_rejects_case_without_stack_or_prior_metadata(self):
        # The full #42 case must authorize the actual stack; center_location
        # alone is NOT a substitute for a source coordinate.
        with self.assertRaisesRegex(ContractError, "single-stack latitude/longitude"):
            producer.replay_annual_selection_offline(self.fixture.case, self.fixture.history)
        self.archive(self.in1)
        self.select([self.in1])
        with self.assertRaisesRegex(ContractError, "fresh selector metadata"):
            producer.replay_annual_selection_offline(self.fixture.case, self.fixture.history)

    def test_in_domain_two_stations_ranked_by_lite_no_network(self):
        self.archive(self.in1)
        self.archive(self.in2)
        self.assertEqual(self.select([self.in1, self.in2], coverage={
            (self.in1.sid, 2022, "lite"): 8050,
            (self.in2.sid, 2022, "lite"): 8200,
        }), 0)
        mf = json.loads((self.raw / "station_selection_2022.json").read_text())
        self.assertEqual(mf["primary_sid"], self.in2.sid)
        self.assertEqual(len(mf["stations"]), 2)
        self.assertEqual({r["sid"] for r in mf["stations"]}, {self.in1.sid, self.in2.sid})

    def test_virtual_strict_gt90_both_and_original_location(self):
        self.archive(self.out1)
        self.assertEqual(self.select([self.out1], coverage={
            (self.out1.sid, 2022, "full"): 8200,
            (self.out1.sid, 2022, "lite"): 8100,
        }), 0)
        mf = json.loads((self.raw / "station_selection_2022.json").read_text())
        self.assertEqual(mf["mode"], "VIRTUAL_RELOCATED")
        row = mf["stations"][0]
        self.assertTrue(row["relocated"])
        self.assertEqual(row["source_lat"], self.out1.lat)
        self.assertEqual(row["lat"], 31.939774444)

    def test_missing_nearer_candidate_fails_instead_of_skipping(self):
        self.archive(self.out2)
        with self.assertRaisesRegex(SystemExit, "OFFLINE_UNRESOLVED_CANDIDATE"):
            self.select([self.out1, self.out2])
        self.assertFalse((self.raw / "station_selection_2022.json").exists())

    def test_no_in_domain_missing_selected_station_fails(self):
        self.archive(self.in1)
        with self.assertRaisesRegex(SystemExit, "OFFLINE_UNRESOLVED_CANDIDATE"):
            self.select([self.in1, self.in2])

    def test_virtual_exact_90_percent_fails(self):
        self.archive(self.out1)
        with self.assertRaisesRegex(SystemExit, "source selection failed"):
            self.select([self.out1], coverage={
                (self.out1.sid, 2022, "full"): 7884,
                (self.out1.sid, 2022, "lite"): 8100,
            })

    def test_missing_lite_fails_without_network(self):
        (self.raw / f"{self.in1.sid}-2022.csv").write_bytes(b"synthetic full only\n")
        (self.raw / "isd_lite" / lite.filename(self.in1.sid, 2022)).unlink()
        with self.assertRaisesRegex(SystemExit, "OFFLINE_UNRESOLVED_CANDIDATE"):
            self.select([self.in1])


if __name__ == "__main__":
    unittest.main()
