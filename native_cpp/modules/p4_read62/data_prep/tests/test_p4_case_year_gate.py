"""Synthetic-format software gates only; these are NOT genuine NOAA observations."""
from __future__ import annotations

import calendar
import csv
import json
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

from native_cpp.orchestration.plan import ContractError
from native_cpp.modules.p4_read62.data_prep.p4_case_d1 import sha256_file
from native_cpp.modules.p4_read62.data_prep.p4_case_final import publish_source_only_candidate
from native_cpp.modules.p4_read62.data_prep.p4_case_year_gate import (
    admit_annual_source_lineage, boundary_years, writer_window,
)

START = datetime(2022, 12, 31, 18)
END = datetime(2023, 1, 1, 6)
SID = "USM00058424"
WMO = "58424"


def all_original_slots(year):
    t = datetime(year, 1, 1)
    stop = datetime(year + 1, 1, 1)
    result = []
    while t < stop:
        result.append(t.strftime("%Y%m%d%H"))
        t += timedelta(hours=12)
    return result


class AnnualAuthenticP4GateTest(unittest.TestCase):
    def setUp(self):
        t = tempfile.TemporaryDirectory()
        self.addCleanup(t.cleanup)
        self.root = Path(t.name)
        self.upper = self.root / "upperair"
        self.upper.mkdir()
        self.archive = self.root / "archive"
        self.archive.mkdir()
        self.raw = self.archive / (SID + "-data.txt")
        self.raw.write_text("synthetic test fixture, never NOAA science\n")
        self.audit = {}
        self.rows = {}
        self.jobs = []
        for year in (2022, 2023):
            basedir = self.upper / str(year)
            (basedir / "igra2fsl").mkdir(parents=True)
            (basedir / (SID + "_igra_every_moment")).mkdir()
            (basedir / "fsl_data").mkdir()
            slots = all_original_slots(year)
            self.audit[year] = {
                "year": year,
                "selected": [{
                    "id": SID, "site_type": "OBSERVED",
                    "source_lat": 40.0, "source_lon": -105.0,
                    "effective_lat": 40.0, "effective_lon": -105.0,
                    "valid_original_slots": len(slots),
                    "coverage": 1.0, "original_utc_slots": slots,
                    "raw_sha256": sha256_file(self.raw),
                }]
            }
            self.rows[year] = [{
                "id": SID, "name": "TEST-ONLY", "lat": "40.0", "lon": "-105.0",
                "elev_m": "100.0", "year": str(year),
                "source_lat": "40.0", "source_lon": "-105.0",
                "site_type": "OBSERVED", "raw_txt": str(self.raw),
                "valid_original_slots": str(len(slots)),
                "expected_slots": str((366 if calendar.isleap(year) else 365) * 2),
                "raw_coverage": "1.0", "distance_km": "0",
            }]
            name = f"{WMO}_{year}010100.csv"
            (basedir / (SID + "_igra_every_moment") / name).write_text("test,profile\n1,2\n")
            fsl = basedir / "igra2fsl" / (WMO + ".txt")
            fsl.write_text("mock fixed-width FSL input for software contract\n")
            self.jobs.append({
                "station_id": WMO, "source_station_id": SID,
                "input_fsl": str(fsl),
                "output_updat": str(basedir / "fsl_data" / f"up_{WMO}_{year}.dat"),
            })
        self.save()

    def save(self):
        for year in (2022, 2023):
            basedir = self.upper / str(year)
            (basedir / "p4_station_selection_audit.json").write_text(json.dumps(self.audit[year]))
            with (basedir / "upperair_station_used_list.txt").open("w", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=list(self.rows[year][0]))
                writer.writeheader()
                writer.writerows(self.rows[year])

    def gate(self):
        return admit_annual_source_lineage(self.jobs, self.upper, self.archive,
                                           START, END)

    def test_boundary_years_and_writer_window(self):
        self.assertEqual(writer_window(START, END),
                         (datetime(2022, 12, 31, 12), datetime(2023, 1, 1, 12)))
        self.assertEqual(boundary_years(START, END), [2022, 2023])
        self.assertEqual(boundary_years(datetime(2023, 1, 1, 0),
                                        datetime(2023, 12, 31, 23)), [2023, 2024])

    def test_all_authentic_hourly_brackets_in_two_years(self):
        result = self.gate()
        self.assertEqual(result["status"], "INPUT_CHECKED_SOURCE_AND_BRACKETS_ONLY")
        self.assertEqual(result["station_wmo"], [WMO])
        self.assertEqual(result["hour_ending_count"], 12)
        self.assertTrue(result["real_aa_bb_each_hour"])
        self.assertEqual(result["years_with_boundary_inputs"], [2022, 2023])

    def test_missing_real_future_bracket_rejected_even_with_cloned_csv(self):
        second = self.audit[2023]["selected"][0]
        second["original_utc_slots"].remove("2023010112")
        second["valid_original_slots"] -= 1
        self.rows[2023][0]["valid_original_slots"] = str(second["valid_original_slots"])
        self.save()
        with self.assertRaisesRegex(ContractError, "missing genuine AA/BB"):
            self.gate()

    def test_cross_year_station_identity_change_rejected(self):
        self.audit[2023]["selected"][0]["effective_lon"] = -104.0
        self.rows[2023][0]["lon"] = "-104.0"
        self.save()
        with self.assertRaisesRegex(ContractError, "changed real/effective"):
            self.gate()

    def test_source_mutation_after_yearly_selection_rejected(self):
        self.raw.write_text("mutated after selection\n")
        with self.assertRaisesRegex(ContractError, "source changed"):
            self.gate()

    def test_lost_original_slot_provenance_rejected(self):
        self.audit[2022]["selected"][0].pop("original_utc_slots")
        self.save()
        with self.assertRaisesRegex(ContractError, "lacks immutable original"):
            self.gate()

    def test_name_collisions_and_annual_selection_mismatch_fail_closed(self):
        self.rows[2023][0]["id"] = "USM00058425"
        self.save()
        with self.assertRaisesRegex(ContractError, "does not match QA"):
            self.gate()


    def _raw_up(self, year, soundings):
        """Faithful 6201/level syntax; synthetic records, not scientific data."""
        header = [
            "UP.DAT          2.1", "   1", "Produced by READ62 Version: 5.661",
            "NONE    ", "UTC+0000",
            " 2022 365 12 0 2023 1 12 0 500. 2 1",
            "     F    F    F    F",
        ]
        for when in soundings:
            h = "   6201  " + f"{int(WMO):8d}"
            for _ in range(2):
                h += "    " + f"{when.year:4d}{when.month:4d}{when.day:3d}{when.hour:3d}{0:5d}"
            h += f"{2:5d}   {2:5d}"
            header.append(h)
            header.append("   1000.0/  100./293.2/180/  5   500.0/ 5200./273.2/200/  7")
        raw = self.upper / str(year) / "fsl_data" / f"up_{WMO}_{year}.dat"
        raw.write_text("\n".join(header) + "\n", encoding="utf-8")
        return raw

    def test_candidate_final_has_authentic_header_and_no_cloned_record(self):
        self._raw_up(2022, [datetime(2022, 12, 31, 12)])
        self._raw_up(2023, [datetime(2023, 1, 1, 0), datetime(2023, 1, 1, 12)])
        proof = publish_source_only_candidate(
            self.jobs, self.gate(), self.upper, START, END)
        self.assertEqual(proof["status"], "PRODUCED_UNVERIFIED")
        self.assertEqual(proof["station_count"], 1)
        self.assertEqual(proof["files"][0]["soundings"], 3)
        self.assertEqual(proof["p4_to_g19"], "NOT_RUN")
        text = (self.upper / "final" / f"up_{WMO}.dat").read_text()
        self.assertEqual(text.count("6201"), 3)
        self.assertIn("500.", text)
        self.assertTrue((self.upper / "final" / "stations.csv").is_file())

    def test_candidate_rejects_unrequested_cloned_or_extra_time_without_publish(self):
        self._raw_up(2022, [datetime(2022, 12, 31, 0), datetime(2022, 12, 31, 12)])
        self._raw_up(2023, [datetime(2023, 1, 1, 0), datetime(2023, 1, 1, 12)])
        with self.assertRaisesRegex(ContractError, "unrequested original time"):
            publish_source_only_candidate(self.jobs, self.gate(), self.upper, START, END)
        self.assertFalse((self.upper / "final").exists())

    def test_candidate_rejects_missing_required_00_12_native_record(self):
        self._raw_up(2022, [datetime(2022, 12, 31, 12)])
        self._raw_up(2023, [datetime(2023, 1, 1, 0)])
        with self.assertRaisesRegex(ContractError, "missing or extra genuine"):
            publish_source_only_candidate(self.jobs, self.gate(), self.upper, START, END)
        self.assertFalse((self.upper / "final").exists())


if __name__ == "__main__":
    unittest.main()
