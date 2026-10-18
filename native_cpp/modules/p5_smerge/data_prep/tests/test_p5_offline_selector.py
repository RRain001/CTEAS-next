"""#56 D2-A original NOAA selector offline transport: synthetic software tests only."""
from __future__ import annotations

import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

from native_cpp.modules.p5_smerge.data_prep import download_isd_by_grid as p5
from native_cpp.modules.p5_smerge.data_prep import isd_lite_wind as lite
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
            return coverage.get((sid, year, "full"), 8000), 8760
        def wind(path, year, sid):
            return coverage.get((sid, year, "lite"), 8100), 8760
        with (patch.object(p5, "parse_history_txt", return_value=stations),
              patch.object(p5, "original_coverage", side_effect=full),
              patch.object(lite, "lite_time_coverage", side_effect=wind),
              patch.object(p5, "download_one", side_effect=AssertionError("NETWORK-FULL")),
              patch.object(lite, "download_lite_one", side_effect=AssertionError("NETWORK-LITE")),
              patch.object(sys, "argv", argv)):
            return p5.main()

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
        with self.assertRaisesRegex(SystemExit, "OFFLINE_UNRESOLVED_CANDIDATE"):
            self.select([self.in1])


if __name__ == "__main__":
    unittest.main()
