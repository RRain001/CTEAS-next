"""P5 #56 strict hourly SURF quality contract tests; no NOAA measurements."""
import tempfile
import unittest
from pathlib import Path

from native_cpp.modules.p5_smerge.data_prep.surf_hourly_quality import (
    inspect_pair, _parse,
)
from native_cpp.orchestration.plan import ContractError


class SurfHourlyQualityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.raw = self.root / "raw.dat"
        self.published = self.root / "published.dat"
        self.header = (
            f"{'SURF.DAT':<16}{'2.1':<16}\n"
            "0\nNONE\nUTC+0000\n"
            "2024 59 23 0 2024 60 2 0 1\n583140\n"
        )
        self.hours = [
            ("2024 59 23 0 2024 60 0 0\n",
             "1.000 90.000 10 9999 290.000 40 1000.000 0\n"),
            ("2024 60 0 0 2024 60 1 0\n",
             "9999.000 9999.000 9999 9999 9999.000 9999 9999.000 9999\n"),
            ("2024 60 1 0 2024 60 2 0\n",
             "0.000 0.000 10 4 285.000 50 1001.000 0\n"),
        ]
        self.raw.write_text(self.header + "".join(a + b for a, b in self.hours))
        self.published.write_text(
            self.header + "".join(
                a + b.replace("10 9999 290.000", "10 0 290.000").replace(
                    "9999 9999.000", "0 9999.000")
                for a, b in self.hours
            )
        )
        self.reader = {"populated_station_hours": 2,
                       "missing_station_hours": 1,
                       "valid_wind_station_hours": 2}

    def tearDown(self):
        self.temp.cleanup()

    def inspect(self):
        return inspect_pair(
            self.raw, self.published, expected_ids=["583140"],
            expected_begin="20240228-230000",
            expected_end="20240229-020000", reader=self.reader)

    def test_leap_day_three_consecutive_hour_endings_and_field_flags(self):
        quality = self.inspect()
        self.assertEqual(len(quality["hourly_station_flags"]), 3)
        self.assertEqual([row["utc_end"] for row in quality["hourly_station_flags"]],
                         ["20240229-000000", "20240229-010000", "20240229-020000"])
        self.assertEqual(quality["raw_valid_station_hours_by_field"]["wind"], 2)
        self.assertEqual(quality["raw_to_published_cloud_fallback_count"], 2)
        self.assertEqual(quality["published_valid_station_hours_by_field"]["cloud"], 3)
        self.assertEqual(quality["raw_valid_station_hours_by_field"]["cloud"], 1)
        self.assertTrue(quality["reader_aggregate_count_agreement"])
        self.assertFalse(quality["weather_values_exported"])
        self.assertFalse(quality["hourly_station_flags"][1]["stations"][0]["raw_valid"]["temperature"])

    def test_modified_non_cloud_weather_is_rejected(self):
        self.published.write_text(
            self.published.read_text().replace("1.000 90.000", "2.000 90.000"))
        with self.assertRaisesRegex(ContractError, "beyond cloud fallback"):
            self.inspect()

    def test_unapproved_cloud_override_is_rejected(self):
        self.published.write_text(
            self.published.read_text().replace("10 4 285.000", "10 0 285.000"))
        with self.assertRaisesRegex(ContractError, "unapproved published cloud"):
            self.inspect()

    def test_reordered_hour_is_rejected(self):
        content = self.raw.read_text().replace(
            "2024 60 0 0 2024 60 1 0",
            "2024 60 1 0 2024 60 2 0")
        self.raw.write_text(content)
        with self.assertRaisesRegex(ContractError, "missing/reordered"):
            self.inspect()

    def test_missing_station_row_and_bad_reader_counts_are_rejected(self):
        self.raw.write_text(self.raw.read_text().replace(
            "0.000 0.000 10 4 285.000 50 1001.000 0\n", ""))
        with self.assertRaises(ContractError):
            self.inspect()
        self.raw.write_text(self.header + "".join(a + b for a, b in self.hours))
        self.reader["valid_wind_station_hours"] = 1
        with self.assertRaisesRegex(ContractError, "counts disagree"):
            self.inspect()

    def test_wrong_station_order_or_calendar_end_is_rejected(self):
        with self.assertRaisesRegex(ContractError, "station order"):
            inspect_pair(self.raw, self.published, expected_ids=["999999"],
                         expected_begin="20240228-230000",
                         expected_end="20240229-020000", reader=self.reader)
        with self.assertRaisesRegex(ContractError, "count outside"):
            inspect_pair(self.raw, self.published, expected_ids=["583140"],
                         expected_begin="20240228-230000",
                         expected_end="20240229-030000", reader=self.reader)


if __name__ == "__main__":
    unittest.main()
