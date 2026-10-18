"""#56 D1-A offline, synthetic admission checks. Never download NOAA or run SMERGE."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from native_cpp.modules.p5_smerge.data_prep.case_archive_gate import admit_p5_archive
from native_cpp.orchestration.plan import ContractError


class P5ArchiveGateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="p5-d1a-")
        self.root = Path(self.tmp.name) / "newsite_2022"
        (self.root / "grid").mkdir(parents=True)
        self.raw = self.root / "met/surface/isd_raw"
        (self.raw / "isd_lite").mkdir(parents=True)
        self.case = self.root / "case.yaml"
        self.grid = self.root / "grid/grid.cmn"
        self.clock = self.root / "grid/research_time"
        self.history = Path(self.tmp.name) / "isd-history.txt"
        self.history.write_text("Synthetic header for SHA custody only\n", encoding="utf-8")
        self.grid.write_text("\n".join((
            "! IMAP = UTM !", "! DATUM = WGS-84 !", "! IUTMZN = 50 !",
            "! LSOHEM = N !", "! XREFKM = 510.885 !", "! YREFKM = 3531.269 !",
            "! DGRIDKM = 0.100 !", "! NX = 50 !", "! NY = 50 !",
            "! NZ = 1 !", "! ZFACE = 0 !", "! ZFACE = 100 !", "")), encoding="utf-8")
        self.clock.write_text("BEGIN:20220101-000000\nEND:20220101-030000\n", encoding="utf-8")
        self.case.write_text("""
case_name: newsite_2022
settings:
  timezone: UTC+0000
preprocess:
  grid:
    utm_zone: 50
    hemisphere: N
    nz: 1
    resolution_km: 0.1
    domain: {length_km: 5, width_km: 5}
    center: {latitude: 31.939774444, longitude: 117.141610855}
  research_time:
    begin: 20220101-000000
    end: 20220101-030000
""".lstrip(), encoding="utf-8")
        self.station("58314099999", 2022)

    def tearDown(self):
        self.tmp.cleanup()

    def station(self, sid, year, *, virtual=False, full=8000, lite=8100):
        from native_cpp.modules.p5_smerge.data_prep.isd_lite_wind import filename
        import datetime as dt
        hours = int((dt.datetime(year + 1, 1, 1) - dt.datetime(year, 1, 1)).total_seconds() // 3600)
        (self.raw / f"{sid}-{year}.csv").write_bytes(b"SYNTHETIC FULL ISD SOURCE\n")
        wind = self.raw / "isd_lite" / filename(sid, year)
        wind.write_bytes(b"SYNTHETIC LITE SOURCE\n")
        return {
            "sid": sid, "ifstn": sid[:6], "name": "test station",
            "lat": 31.939774444, "lon": 117.141610855,
            "source_lat": (32.5 if virtual else 31.939774444),
            "source_lon": (116.0 if virtual else 117.141610855),
            "relocated": virtual,
            "expected_hours": hours,
            "full_isd_raw_hours": full, "isd_lite_raw_hours": lite,
            "wind_treatment": "COMPLETE_FILL_AND_CALM_REPLACE",
            "wind_isd_lite": {
                "filename": wind.name,
                "sha256": hashlib.sha256(wind.read_bytes()).hexdigest()
            },
        }

    def manifest(self, year, rows, *, virtual=False):
        primary = sorted(rows, key=lambda s: (-s["isd_lite_raw_hours"],
                                             -s["full_isd_raw_hours"], s["sid"]))[0]["sid"]
        for row in rows:
            row["wind_treatment"] = ("COMPLETE_FILL_AND_CALM_REPLACE"
                                     if row["sid"] == primary else "RAW_SPARSE_STANDARDIZE_ONLY")
        path = self.raw / f"station_selection_{year}.json"
        path.write_text(json.dumps({
            "year": year,
            "mode": "VIRTUAL_RELOCATED" if virtual else "OBSERVED",
            "selection_geometry": "STRICT_WGS84_UTM_GRID_CMN_SW_CORNER_CLOSED_EDGES",
            "utm_zone": 50, "utm_hemisphere": "N",
            "utm_bounds_km": [510.885, 515.885, 3531.269, 3536.269],
            "primary_sid": primary, "stations": rows,
        }), encoding="utf-8")
        return path

    def gate(self):
        return admit_p5_archive(self.case, self.raw, self.history)

    def test_single_station_evidence_is_software_only(self):
        self.manifest(2022, [self.station("58314099999", 2022)])
        proof = self.gate()
        self.assertEqual(proof["status"], "INPUT_CHECKED")
        self.assertEqual(proof["P5_NATIVE_SURF"], "NOT_RUN")
        self.assertEqual(proof["P5_ORIGINAL_PARITY"], "NOT_RUN")
        self.assertEqual(proof["requested_hour_labels_inclusive"], 4)
        self.assertFalse(proof["science_acceptance"])
        self.assertEqual(len(proof["years"][0]["stations"]), 1)

    def test_missing_or_tampered_lite_fails_closed(self):
        self.manifest(2022, [self.station("58314099999", 2022)])
        wind = self.raw / "isd_lite/583140-99999-2022.gz"
        wind.write_bytes(b"CHANGED\n")
        with self.assertRaisesRegex(ContractError, "changed"):
            self.gate()
        wind.unlink()
        with self.assertRaisesRegex(ContractError, "missing"):
            self.gate()

    def test_strict_virtual_both_gt90(self):
        row = self.station("58314099999", 2022, virtual=True, full=7884, lite=8100)
        self.manifest(2022, [row], virtual=True)
        with self.assertRaisesRegex(ContractError, "strictly >90"):
            self.gate()
        row["full_isd_raw_hours"] = 7885
        self.manifest(2022, [row], virtual=True)
        self.assertEqual(self.gate()["years"][0]["mode"], "VIRTUAL_RELOCATED")

    def test_actual_primary_is_annual_lite_rank_and_roles(self):
        a = self.station("58314099999", 2022, full=8100, lite=8000)
        b = self.station("58321099999", 2022, full=7000, lite=8200)
        mf = self.manifest(2022, [a, b])
        self.assertEqual(self.gate()["years"][0]["primary_sid"], "58321099999")
        payload = json.loads(mf.read_text())
        payload["primary_sid"] = "58314099999"
        mf.write_text(json.dumps(payload))
        with self.assertRaisesRegex(ContractError, "primary ranking"):
            self.gate()

    def test_cross_year_station_identity_is_stable_but_primary_may_switch(self):
        self.clock.write_text("BEGIN:20221231-230000\nEND:20230101-020000\n")
        case = self.case.read_text()
        case = case.replace("20220101-000000", "20221231-230000")
        case = case.replace("20220101-030000", "20230101-020000")
        self.case.write_text(case)
        a22 = self.station("58314099999", 2022, full=8000, lite=8200)
        b22 = self.station("58321099999", 2022, full=8300, lite=8100)
        a23 = self.station("58314099999", 2023, full=8000, lite=7900)
        b23 = self.station("58321099999", 2023, full=8100, lite=8200)
        self.manifest(2022, [a22, b22])
        self.manifest(2023, [a23, b23])
        proof = self.gate()
        self.assertEqual([y["primary_sid"] for y in proof["years"]],
                         ["58314099999", "58321099999"])
        mf = self.raw / "station_selection_2023.json"
        data = json.loads(mf.read_text())
        data["stations"][0]["ifstn"] = "999999"
        mf.write_text(json.dumps(data))
        with self.assertRaisesRegex(ContractError, "identity/effective position conflict"):
            self.gate()

    def test_same_zone_wrong_footprint_is_not_reused(self):
        mf = self.manifest(2022, [self.station("58314099999", 2022)])
        data = json.loads(mf.read_text())
        data["utm_bounds_km"][0] += 1.0
        mf.write_text(json.dumps(data))
        with self.assertRaisesRegex(ContractError, "footprint differs"):
            self.gate()

    def test_no_worktree_or_legacy_case_alias(self):
        self.manifest(2022, [self.station("58314099999", 2022)])
        with self.assertRaisesRegex(ContractError, "staged in this case"):
            admit_p5_archive(self.case, Path(self.tmp.name), self.history)
        self.clock.write_text("BEGIN:20220101-000000\nEND:20220101-033000\n")
        with self.assertRaisesRegex(ContractError, "whole UTC hours"):
            self.gate()


if __name__ == "__main__":
    unittest.main()
