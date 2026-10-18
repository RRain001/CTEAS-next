"""S2-G0 new-site contract: controlled metadata fixtures, never NOAA authenticity proof."""
from __future__ import annotations

import copy
import json
import math
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

from engine.run_met.common import lon_lat_to_utm_km
from native_cpp.orchestration.plan import (
    CASE_ID, ContractError, FROZEN_MET_CONTROLS, FROZEN_PUFF_CONTROLS,
)
from native_cpp.orchestration.site_plan import plan_site


class DynamicNonHefeiContractTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.case_root = self.root / "new_site_utmn13_2022_2023"
        self.grid_dir = self.case_root / "grid"
        self.grid_dir.mkdir(parents=True)
        self.a = (40.0000, -105.0000)
        self.b = (40.1050, -104.9800)
        x, y = lon_lat_to_utm_km(self.a[1], self.a[0], 13, True)
        self.xref = math.floor((x - 15.0) * 1000) / 1000
        self.yref = math.floor((y - 15.0) * 1000) / 1000
        self.field = (self.grid_dir / "grid.cmn")
        self.field.write_text("\n".join((
            "! IMAP = UTM !", "! IUTMZN = 13 !", "! LSOHEM = N !",
            "! DATUM = WGS-84 !",
            f"! XREFKM = {self.xref:.3f} !", f"! YREFKM = {self.yref:.3f} !",
            "! NX = 20 !", "! NY = 20 !", "! DGRIDKM = 2.0 !",
            "! NZ = 9 !", *[f"! ZFACE = {z} !" for z in
                (0, 20, 40, 80, 160, 320, 640, 1200, 2000, 3000)],
        )) + "\n")
        self.case = {
            "schema_version": 1, "case_name": self.case_root.name,
            "settings": {"timezone": "UTC+0000"},
            "preprocess": {
                "grid": {
                    "utm_zone": 13, "hemisphere": "N",
                    "center": {"latitude": self.a[0], "longitude": self.a[1]},
                    "domain": {"length_km": 40, "width_km": 40},
                    "resolution_km": 2.0, "nz": 9,
                },
                "research_time": {"begin": "20220101-000000", "end": "20231231-230000"},
                "upperair": {"station_id": "auto", "pstop_hpa": 500},
                "surface": {"auto_select_all": True},
            },
            "met": {"options": copy.deepcopy(FROZEN_MET_CONTROLS)},
            "puff": {
                "options": copy.deepcopy(FROZEN_PUFF_CONTROLS),
                "point_sources": [{
                    "name": "TEST_STACK",
                    "latitude": self.a[0], "longitude": self.a[1],
                    "stack_height_m": 40.0, "stack_diameter_m": 1.6,
                    "exit_velocity_mps": 12.0, "exit_temp_k": 300.0,
                    "emissions": [1.0, 0.0],
                }],
            },
        }
        self.yaml_path = self.case_root / "case.yaml"
        self.p4 = self.root / "p4"
        self.p5 = self.root / "p5"
        self.reset_files()

    def reset_files(self):
        self.yaml_path.write_text(yaml.safe_dump(self.case, sort_keys=False))
        for year in (2022, 2023):
            ydir = self.p4 / str(year)
            ydir.mkdir(parents=True, exist_ok=True)
            obs = []
            for sid, (lat, lon), count in (
                ("USM00012345", self.a, 729 if year == 2022 else 727),
                ("USM00023456", self.b, 728 if year == 2022 else 730),
            ):
                obs.append({
                    "id": sid, "site_type": "OBSERVED", "source_lat": lat,
                    "source_lon": lon, "effective_lat": lat, "effective_lon": lon,
                    "valid_original_slots": count, "coverage": count / 730,
                })
            (ydir / "p4_station_selection_audit.json").write_text(
                json.dumps({"year": year, "in_domain_candidates": 2,
                            "selected": obs}) + "\n")
            sdir = self.p5
            sdir.mkdir(parents=True, exist_ok=True)
            stations = []
            for sid, (lat, lon), alias, full, lite in (
                ("72469099999", self.a, "7246901", 8700 if year == 2022 else 7900,
                 8690 if year == 2022 else 7850),
                ("72470099999", self.b, "7247001", 8000 if year == 2022 else 8750,
                 7900 if year == 2022 else 8700),
            ):
                stations.append({
                    "sid": sid, "lat": lat, "lon": lon,
                    "source_lat": lat, "source_lon": lon, "elev": 10.0,
                    "source_elev": 10.0, "relocated": False, "ifstn": alias,
                    "expected_hours": 8760, "full_isd_raw_hours": full,
                    "isd_lite_raw_hours": lite, "full_isd_coverage": full / 8760,
                    "isd_lite_coverage": lite / 8760,
                    "wind_treatment": "COMPLETE_FILL_AND_CALM_REPLACE"
                        if (sid == ("72469099999" if year == 2022 else "72470099999"))
                        else "RAW_SPARSE_STANDARDIZE_ONLY",
                })
            (sdir / f"station_selection_{year}.json").write_text(
                json.dumps({"year": year, "mode": "OBSERVED",
                            "station_selection_case": "IN_DOMAIN_MULTIPLE",
                            "primary_sid": "72469099999" if year == 2022 else "72470099999",
                            "stations": stations}) + "\n")

    def plan(self):
        return plan_site(self.yaml_path, self.p4, self.p5)

    def change_p4(self, mutate, year=2022):
        f = self.p4 / str(year) / "p4_station_selection_audit.json"
        j = json.loads(f.read_text())
        mutate(j)
        f.write_text(json.dumps(j))

    def change_p5(self, mutate, year=2022):
        f = self.p5 / f"station_selection_{year}.json"
        j = json.loads(f.read_text())
        mutate(j)
        f.write_text(json.dumps(j))

    def test_non_hefei_case_is_read_only_and_p6_p7_blocked(self):
        before = {p: p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
        result = self.plan()
        self.assertEqual(result["status"], "SITE_STATION_INPUTS_VERIFIED_P6_P7_BLOCKED")
        self.assertFalse(result["ready"])
        self.assertFalse(result["model_executed"])
        self.assertFalse(result["legacy_fallback"])
        self.assertEqual(result["selector_source_authenticity"],
                         "NOT_AUTHENTICATED_BY_THIS_INPUT_MANIFEST_VALIDATOR")
        self.assertEqual(result["grid"]["crs"], "WGS84_UTM13N")
        self.assertEqual(result["grid"]["nx"], 20)
        self.assertEqual(result["research_time"]["calendar_years_with_source_selection"],
                         [2022, 2023])
        self.assertEqual([x["id"] for x in result["stages"]],
                         ["p1", "p2", "p3", "p4", "p5", "p6", "p7"])
        self.assertTrue(all(not x["execute"] for x in result["stages"]))
        self.assertEqual([x["primary"] for x in result["selector_manifest_evidence"]["p5"]],
                         ["72469099999", "72470099999"])
        self.assertEqual(before, {p: p.read_bytes() for p in self.root.rglob("*") if p.is_file()})

    def test_refuse_frozen_case_masquerade(self):
        self.case["case_name"] = CASE_ID
        self.reset_files()
        with self.assertRaisesRegex(ContractError, "case_name"):
            self.plan()

    def test_refuse_origin_precision_change(self):
        self.field.write_text(self.field.read_text().replace(
            f"{self.xref:.3f}", f"{self.xref:.4f}"))
        with self.assertRaisesRegex(ContractError, "3 decimal"):
            self.plan()

    def test_refuse_case_grid_mismatch(self):
        self.case["preprocess"]["grid"]["resolution_km"] = 1.0
        self.reset_files()
        with self.assertRaisesRegex(ContractError, "spacing"):
            self.plan()

    def test_refuse_bad_utm_zone(self):
        self.case["preprocess"]["grid"]["utm_zone"] = 50
        self.reset_files()
        with self.assertRaisesRegex(ContractError, "UTM"):
            self.plan()

    def test_refuse_outside_stack(self):
        self.case["puff"]["point_sources"][0]["longitude"] = -110
        self.reset_files()
        with self.assertRaisesRegex(ContractError, "stack outside"):
            self.plan()

    def test_refuse_disabled_physics_option_expansion(self):
        self.case["puff"]["options"]["iwet"] = 1
        self.reset_files()
        with self.assertRaisesRegex(ContractError, "iwet"):
            self.plan()

    def test_refuse_historical_fixed_station(self):
        self.case["preprocess"]["upperair"]["station_id"] = "CHM00058424"
        self.reset_files()
        with self.assertRaisesRegex(ContractError, "historical 58424"):
            self.plan()

    def test_refuse_missing_real_selector_manifest(self):
        (self.p4 / "2023/p4_station_selection_audit.json").unlink()
        with self.assertRaises(ContractError):
            self.plan()

    def test_refuse_fabricated_p4_source_count(self):
        self.change_p4(lambda j: j["selected"][0].update(
            valid_original_slots=500, coverage=500 / 730))
        with self.assertRaisesRegex(ContractError, "<=80%"):
            self.plan()

    def test_refuse_p4_spoofed_source_position(self):
        self.change_p4(lambda j: j["selected"][0].update(source_lon=-109.0))
        with self.assertRaisesRegex(ContractError, "outside domain"):
            self.plan()

    def test_refuse_wrong_p5_year(self):
        self.change_p5(lambda j: j.update(year=2021))
        with self.assertRaisesRegex(ContractError, "wrong manifest year"):
            self.plan()

    def test_refuse_p5_false_primary_ranking(self):
        self.change_p5(lambda j: j.update(primary_sid="72470099999"))
        with self.assertRaisesRegex(ContractError, "ranking"):
            self.plan()

    def test_refuse_p5_alias_drift(self):
        self.change_p5(lambda j: j["stations"][0].update(ifstn="9999999"), year=2023)
        with self.assertRaisesRegex(ContractError, "changed between"):
            self.plan()

    def test_refuse_false_p5_source_hours(self):
        self.change_p5(lambda j: j["stations"][0].update(full_isd_raw_hours=8761))
        with self.assertRaisesRegex(ContractError, "annual hours"):
            self.plan()

    def test_refuse_malformed_p5_virtual_station(self):
        self.change_p5(lambda j: j["stations"][1].update(
            relocated=True, lat=self.a[0], lon=self.a[1]))
        with self.assertRaisesRegex(ContractError, "virtual fallback"):
            self.plan()

    def test_cli_json_fail_closed_and_no_execution(self):
        a = [sys.executable, "-m", "native_cpp.orchestration.site_plan",
             "--case-yaml", str(self.yaml_path),
             "--p4-selection-root", str(self.p4),
             "--p5-selection-root", str(self.p5)]
        p = subprocess.run(a, capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(json.loads(p.stdout)["ready"], False)
        self.yaml_path.unlink()
        p = subprocess.run(a, capture_output=True, text=True)
        self.assertEqual(p.returncode, 2)
        self.assertEqual(json.loads(p.stdout)["status"], "BLOCKED_NONHEFEI_INPUT_CONTRACT")


if __name__ == "__main__":
    unittest.main()
