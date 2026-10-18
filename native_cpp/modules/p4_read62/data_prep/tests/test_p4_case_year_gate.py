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


if __name__ == "__main__":
    unittest.main()
