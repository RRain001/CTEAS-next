"""Scoped P5 regression: station decisions, NOAA field mapping, fill policies."""
from __future__ import annotations

import csv
import gzip
import json
import math
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd
from native_cpp.modules.p5_smerge.data_prep import download_isd_by_grid as d
from native_cpp.modules.p5_smerge.data_prep import isd_to_smerge_and_fill as c
from native_cpp.modules.p5_smerge.data_prep import interpolate as interp
from native_cpp.modules.p5_smerge.data_prep.station_identity import numeric_station_ids
from native_cpp.modules.p5_smerge.data_prep import isd_lite_wind as lite


def station(sid: str, lat: float, lon: float) -> d.Station:
    return d.Station(sid, lat, lon, 63.0, "test", "CN", "19900101", "20261231")


class P5SelectionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / "center").write_text("latitude: 31.94\nlongitude: 117.14\n")
        # Same published SW corner as the frozen 2022 case; no inferred lat/lon box.
        grid_lines = [
            "! IMAP = UTM !", "! IUTMZN = 50 !", "! LSOHEM = N !",
            "! DATUM = WGS-84 !", "! XREFKM = 510.885 !",
            "! YREFKM = 3531.269 !", "! DGRIDKM = 0.1 !",
            "! NX = 50 !", "! NY = 50 !", "! NZ = 9 !",
        ]
        grid_lines.extend(f"! ZFACE = {z} !" for z in
                          (0, 20, 40, 80, 160, 320, 640, 1200, 2000, 3000))
        (self.root / "grid").write_text("\n".join(grid_lines) + "\n")
        (self.root / "research_time").write_text("BEGIN: 20220101-000000\nEND: 20221231-230000\n")
        self.raw = self.root / "raw"

    def execute(self, locations: list[d.Station], available: dict[str, int],
                include_stack: bool = True, years=(2022,)):
        (self.root / "research_time").write_text(
            f"BEGIN: {min(years)}0101-000000\nEND: {max(years)}1231-230000\n"
        )
        argv = ["p5", "--center-file", str(self.root / "center"),
                "--grid-file", str(self.root / "grid"),
                "--research-time-file", str(self.root / "research_time"),
                "--out-dir", str(self.raw), "--retries", "1"]
        if include_stack:
            argv += ["--stack-lat", "31.939774444", "--stack-lon", "117.141610855"]
        def fake_download(year, sid, out, timeout):
            out.mkdir(parents=True, exist_ok=True)
            (out / f"{sid}-{year}.csv").write_text("stub\n")
            return True, "test", False
        def fake_lite_download(year, sid, out, timeout):
            out.mkdir(parents=True,exist_ok=True)
            (out / lite.filename(sid,year)).write_bytes(b"mock source")
            return True, "test", False
        def fake_lite_hours(file, year, station_id):
            count = available.get((station_id, year, "lite"),
                                  available.get((station_id, year),
                                                available.get(station_id, 0)))
            return count, d.expected_hours_in_year(year)
        def fake_hours(file, year, station_id=None):
            sid = file.name.split("-")[0]
            count = available.get((sid,year,"full"),
                                  available.get((sid,year),available.get(sid,0)))
            return count, d.expected_hours_in_year(year)
        with patch.object(d, "parse_history_txt", return_value=locations), \
             patch.object(d, "download_one", side_effect=fake_download), \
             patch.object(d, "original_coverage", side_effect=fake_hours), \
             patch.object(lite, "download_lite_one", side_effect=fake_lite_download), \
             patch.object(lite, "lite_time_coverage", side_effect=fake_lite_hours), \
             patch.object(sys, "argv", argv):
            d.main()
        result = {year: json.loads((self.raw / f"station_selection_{year}.json").read_text())
                  for year in years}
        return result[years[0]] if len(years) == 1 else result

    def test_published_utm_edges_and_corners(self):
        grid = d.load_utm_grid(self.root / "grid")
        xmin, xmax, ymin, ymax = d.utm_bounds_km(grid)
        self.assertEqual((xmin, xmax, ymin, ymax),
                         (510.885, 515.885, 3531.269, 3536.269))
        for x, y in ((xmin, ymin), (xmin, ymax), (xmax, ymin),
                     (xmax, ymax), ((xmin+xmax)/2, (ymin+ymax)/2)):
            self.assertTrue(d.contains_projected_utm_km(x, y, grid))
        # 1 millimetre outside each outer edge must be rejected.
        for x, y in ((xmin-1e-6, ymin), (xmax+1e-6, ymax),
                     (xmin, ymin-1e-6), (xmax, ymax+1e-6)):
            self.assertFalse(d.contains_projected_utm_km(x, y, grid))
        self.assertFalse(d.contains_projected_utm_km(float("nan"), ymin, grid))

    def test_source_station_uses_configured_utm_zone(self):
        grid = d.load_utm_grid(self.root / "grid")
        physical = station("58321099999", 31.939774444, 117.141610855)
        self.assertTrue(d.station_in_utm_grid(physical, grid))
        with patch.object(d, "lon_lat_to_utm_km",
                          return_value=(grid.xrefkm-0.001, grid.yrefkm)) as projection:
            self.assertFalse(d.station_in_utm_grid(physical, grid))
            projection.assert_called_once_with(
                physical.lon, physical.lat, 50, True)

    def test_selection_never_uses_geographic_centre_bbox(self):
        # A shifted display/metadata centre must not move the numerical grid.
        (self.root / "center").write_text(
            "latitude: 31.90\nlongitude: 117.10\n")
        st = [station("58321099999", 31.939774444, 117.141610855)]
        result = self.execute(st, {"58321099999": 8000})
        self.assertEqual(result["mode"], "OBSERVED")
        self.assertEqual(result["selection_geometry"],
                         "STRICT_WGS84_UTM_GRID_CMN_SW_CORNER_CLOSED_EDGES")

    def test_invalid_grid_crs_and_dimensions_rejected(self):
        path = self.root / "grid"
        original = path.read_text()
        for bad in (original.replace("IUTMZN = 50", "IUTMZN = 0"),
                    original.replace("IMAP = UTM", "IMAP = LCC"),
                    original.replace("DATUM = WGS-84", "DATUM = NAD27"),
                    original.replace("DGRIDKM = 0.1", "DGRIDKM = 0")):
            path.write_text(bad)
            with self.assertRaises(ValueError):
                d.load_utm_grid(path)
        path.write_text(original)

    def test_all_in_domain_and_real_positions(self):
        st = [station("58321099999", 31.94, 117.14),
              station("A12345ABCDE", 31.945, 117.145),
              station("58314099999", 31.4, 116.333)]
        result = self.execute(st, {s.sid: 8000 for s in st})
        self.assertEqual(result["mode"], "OBSERVED")
        self.assertEqual(len(result["stations"]), 2)
        self.assertEqual(result["station_selection_case"], "IN_DOMAIN_MULTIPLE")
        self.assertEqual(sum(x["wind_treatment"] == "COMPLETE_FILL_AND_CALM_REPLACE"
                             for x in result["stations"]), 1)
        self.assertEqual(sum(x["wind_treatment"] == "RAW_SPARSE_STANDARDIZE_ONLY"
                             for x in result["stations"]), 1)
        for row in result["stations"]:
            self.assertFalse(row["relocated"])
            self.assertEqual(row["lat"], row["source_lat"])
            self.assertEqual(row["lon"], row["source_lon"])
            self.assertEqual(row["elev"], row["source_elev"])
        self.assertEqual(len(list(self.raw.glob("*.csv"))), 2)
        self.assertEqual(len(result["stations"][1]["ifstn"]), 6 if result["stations"][1]["sid"] == "58321099999" else 7)

    def test_nearest_failing_coverage_skipped_only_one_accepted(self):
        st = [station("58321099999",31.98,116.97),
              station("58314099999",31.4,116.3),
              station("58345099999",30.0,115.0)]
        result = self.execute(st, {"58321099999":7884,"58314099999":7885,"58345099999":8760})
        self.assertEqual(result["mode"],"VIRTUAL_RELOCATED")
        self.assertEqual(len(result["stations"]),1)
        entry=result["stations"][0]
        self.assertEqual(entry["sid"],"58314099999")
        self.assertAlmostEqual(entry["lat"],31.939774444)
        self.assertAlmostEqual(entry["lon"],117.141610855)
        self.assertEqual(entry["elev"],68.0 if False else 63.0)  # source elevation unmodified
        self.assertNotEqual(entry["source_lat"],entry["lat"])
        self.assertEqual(len(list(self.raw.glob("*.csv"))),2)

    def test_single_fallback_at_boundary(self):
        st=[station("58321099999",31.98,116.97)]
        r=self.execute(st,{"58321099999":7885})
        self.assertEqual(len(r["stations"]),1)

    def test_fallback_requires_stack_not_area_center(self):
        st=[station("58321099999",31.98,116.97)]
        with self.assertRaises(SystemExit):
            self.execute(st,{"58321099999":8760},include_stack=False)

    def test_external_requires_both_full_and_lite_strict_over_90(self):
        st=[station("58321099999",31.98,116.97),
            station("58314099999",31.4,116.3)]
        counts={
            ("58321099999",2022,"lite"):8400,
            ("58321099999",2022,"full"):7884,  # exactly 90%, FAIL
            ("58314099999",2022,"lite"):8000,
            ("58314099999",2022,"full"):8000,
        }
        result=self.execute(st,counts)
        self.assertEqual(result["primary_sid"],"58314099999")
        self.assertEqual(result["station_selection_case"],"EXTERNAL_SINGLE_VIRTUAL")

    def test_equal_lite_coverage_tie_breaks_with_full_then_sid(self):
        st=[station("58321099999",31.94,117.14),
            station("58314099999",31.945,117.145)]
        counts={
            ("58321099999",2022,"lite"):8000,
            ("58314099999",2022,"lite"):8000,
            ("58321099999",2022,"full"):8100,
            ("58314099999",2022,"full"):7900,
        }
        result=self.execute(st,counts)
        self.assertEqual(result["primary_sid"],"58321099999")

    def test_leap_strict_gt90pct(self):
        self.assertEqual(d.expected_hours_in_year(2024),8784)
        self.assertFalse(7905 * 10 > 9 * 8784)
        self.assertTrue(7906 * 10 > 9 * 8784)
        self.assertFalse(7884 * 10 > 9 * 8760)
        self.assertTrue(7885 * 10 > 9 * 8760)

    def test_one_in_domain_station_even_extremely_low_coverage(self):
        st = [station("58321099999", 31.94, 117.14)]
        result = self.execute(st, {"58321099999": 15})
        self.assertEqual(result["station_selection_case"], "IN_DOMAIN_SINGLE")
        self.assertEqual(result["primary_sid"], "58321099999")
        self.assertEqual(result["stations"][0]["wind_treatment"],
                         "COMPLETE_FILL_AND_CALM_REPLACE")
        self.assertAlmostEqual(result["stations"][0]["isd_lite_coverage"], 15/8760)

    def test_multiple_in_domain_highest_lite_coverage_is_only_primary(self):
        st = [station("58321099999",31.94,117.14),
              station("58314099999",31.945,117.145),
              station("58345099999",31.946,117.146)]
        counts = {"58321099999":7600,"58314099999":8200,"58345099999":600}
        result = self.execute(st,counts)
        self.assertEqual(result["station_selection_case"],"IN_DOMAIN_MULTIPLE")
        self.assertEqual(result["primary_sid"],"58314099999")
        roles={r["sid"]:r["wind_treatment"] for r in result["stations"]}
        self.assertEqual(roles["58314099999"],"COMPLETE_FILL_AND_CALM_REPLACE")
        self.assertEqual(roles["58345099999"],"RAW_SPARSE_STANDARDIZE_ONLY")

    def test_reselection_each_calendar_year_no_sticky_primary(self):
        st = [station("58321099999",31.94,117.14),
              station("58314099999",31.945,117.145)]
        data = {
           ("58321099999",2021): 8100, ("58314099999",2021): 3000,
           ("58321099999",2022): 3000, ("58314099999",2022): 8100,
        }
        outputs=self.execute(st,data,years=(2021,2022))
        self.assertEqual(outputs[2021]["primary_sid"],"58321099999")
        self.assertEqual(outputs[2022]["primary_sid"],"58314099999")
        self.assertEqual(len(outputs[2021]["stations"]),2)
        self.assertEqual(len(outputs[2022]["stations"]),2)

    def test_external_one_station_reselected_each_year_and_strict_above(self):
        st = [station("58321099999",31.98,116.97),
              station("58314099999",31.40,116.33)]
        data = {
           ("58321099999",2021): 7900, ("58314099999",2021): 8500,
           ("58321099999",2022): 7600, ("58314099999",2022): 8200,
        }
        outputs=self.execute(st,data,years=(2021,2022))
        self.assertEqual(outputs[2021]["primary_sid"],"58321099999")
        self.assertEqual(outputs[2022]["primary_sid"],"58314099999")
        self.assertTrue(all(len(x["stations"]) == 1 for x in outputs.values()))

    def test_numeric_identity_aliases_and_duplicates(self):
        ids=numeric_station_ids(["A12345ABCDE","58321099999","58321000000"])
        self.assertEqual(len(set(ids.values())),3)
        self.assertTrue(all(x.isdecimal() for x in ids.values()))
        self.assertTrue(all(len(x)==7 for x in ids.values()))
        self.assertEqual(numeric_station_ids(["58321099999"])["58321099999"],"583210")


class P5FieldsTests(unittest.TestCase):
    def test_csv_reordered_no_temperature_wind_mixup(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            src=root/"A12345ABCDE-2022.csv"
            columns=["WND","DEW","STATION","GF1","TMP","SLP","DATE","AA1","CIG","REPORT_TYPE"]
            record={
                "WND":"090,1,N,0030,1","DEW":"+0100,1","STATION":"A12345ABCDE",
                "GF1":"05,1,1,1","TMP":"+0250,1","SLP":"10135,1",
                "DATE":"2022-01-01T12:00:00","AA1":"01,0012,3,1",
                "CIG":"01000,1,1,1","REPORT_TYPE":"FM-12"}
            with src.open("w",newline="",encoding="utf-8") as f:
                wr=csv.DictWriter(f, fieldnames=columns)
                wr.writeheader()
                wr.writerow(record)
            lite_dir=root/"isd_lite"
            lite_dir.mkdir()
            with gzip.open(lite_dir/lite.filename("A12345ABCDE",2022),"wt",encoding="ascii") as out:
                out.write("2022 01 01 12 250 100 10135 270 40 5 -9999 -9999\n")
            (root/"station_selection_2022.json").write_text(json.dumps({
                "stations":[{"sid":"A12345ABCDE","ifstn":"1777777"}]}))
            with patch.object(c,"INPUT_DIR",root):
                dest,count=c.convert_one_isd_csv(str(src),str(root/"ready"))
            self.assertEqual(count,1)
            with open(dest, newline="") as f:
                rows=list(csv.reader(f))
            self.assertEqual(rows[1][3],"1777777")
            row=rows[3]
            self.assertEqual(float(row[4]),25.0)  # TMP -> temperature
            self.assertEqual(float(row[5]),1.2)   # AA1 -> precip
            self.assertEqual(float(row[6]),1013.5) # SLP -> pressure
            self.assertEqual(float(row[8]),270.0)   # ISD-Lite direction, not full ISD WND
            self.assertEqual(float(row[9]),4.0)     # ISD-Lite speed, not full ISD WND
            self.assertEqual(float(row[10]),5.0)   # GF1 cloud

    def test_schema_rejects_positional_guess(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"58321099999-2022.csv"
            p.write_text("STATION,DATE,TMP,SLP\n58321099999,2022-01-01T00:00:00,+250,10135\n")
            with self.assertRaisesRegex(ValueError,"field names"):
                c.convert_one_isd_csv(str(p),td)


class P5MissingPolicyTests(unittest.TestCase):
    def test_arbitrary_gap_is_previous_value(self):
        raw=pd.Series([20.0]+[9999.0]*120+[21.0])
        result=interp.fill_continuous_by_gap_rule(raw)
        self.assertTrue((result.iloc[1:121]==20.0).all())
        self.assertEqual(result.iloc[-1],21.0)

    def test_initial_missing_stays_missing(self):
        filled=interp.fill_continuous_by_gap_rule(pd.Series([9999.0,9999.0,22.0,9999.0]))
        self.assertTrue(pd.isna(filled.iloc[0]))
        self.assertTrue(pd.isna(filled.iloc[1]))
        self.assertEqual(filled.iloc[3],22.0)

    def test_scheme_c_keeps_zero_and_low_speed(self):
        ts=pd.date_range("2022-01-01",periods=5,freq="h")
        df=pd.DataFrame({"deg":[350,120,30,10,9999],
                         "ms-1":[1.0,0.0,0.2,1.0,9999.0]},index=ts)
        out,audit,summary=interp.fill_wind_forward_calm(df,"deg","ms-1")
        self.assertEqual(list(out["ms-1"]),[1.0,0.0,0.2,1.0,1.0])
        self.assertEqual(list(out["deg"]),[350,0,30,10,10])
        self.assertEqual(audit["wind_direction_raw_deg"].iloc[1],120)
        self.assertEqual(audit["wind_direction_filled_deg"].iloc[1],350)  # never inherit calm WD
        self.assertEqual(audit["wind_speed_generic_m_s"].iloc[1],0)
        self.assertTrue(bool(audit["is_calm"].iloc[2]))
        self.assertFalse(bool(audit["is_exact_zero_speed"].iloc[2]))
        self.assertEqual(summary["calm_limit_usage"],"LOW_SPEED_DIAGNOSTIC_ONLY")

    def test_undefined_direction_for_exact_zero_is_canonical(self):
        ts=pd.date_range("2022-01-01",periods=4,freq="h")
        df=pd.DataFrame({"deg":[9999,9999,90,9999],
                         "ms-1":[0.0,0.0,1.0,0.0]},index=ts)
        out,audit,summary=interp.fill_wind_forward_calm(df,"deg","ms-1",strict=True)
        self.assertEqual(list(out["deg"]),[0,0,90,0])
        self.assertEqual(list(out["ms-1"]),[0.0,0.0,1.0,0.0])
        self.assertTrue(pd.isna(audit["wind_direction_raw_deg"].iloc[0]))
        self.assertEqual(summary["exact_zero_hours"],3)

    def test_leading_missing_nonzero_cannot_invent_direction(self):
        ts=pd.date_range("2022-01-01",periods=3,freq="h")
        df=pd.DataFrame({"deg":[9999,100,100],
                         "ms-1":[0.2,0.2,1.0]},index=ts)
        out,_,_=interp.fill_wind_forward_calm(df,"deg","ms-1")
        self.assertEqual(out["deg"].iloc[0],9999)
        self.assertEqual(out["ms-1"].iloc[0],0.2)
        with self.assertRaisesRegex(interp.WindPreparationError,"LEADING_MISSING"):
            interp.fill_wind_forward_calm(df,"deg","ms-1",strict=True)

    def test_original_smerge_calmet_calm_source_contract(self):
        root=Path(__file__).resolve().parents[5]
        sm=(root/"engine/vendor/src/SMERGE_v5.7.0_L121203/SMERGE.FOR").read_text(errors="replace")
        cal=(root/"engine/vendor/src/CALMET_v6.5.0_L150223/calmet.for").read_text(errors="replace")
        inp=(root/"engine/templates/met.inp").read_text(errors="replace")
        self.assertIn("elseif (jdat.eq.8) then",sm)
        self.assertIn("xws(index) = xcws",sm)
        self.assertIn("if(xws(n).eq.0.0)ncalms(n)=ncalms(n)+1",sm)
        self.assertIn("ws=max(ws,0.5)",cal)
        self.assertIn("data vk/0.4/,xcrit/0.05/,wsmin/0.001/",cal)
        self.assertIn("if (ws10(l) .lt. 0.0001) then",cal)
        self.assertIn("IF (ICALM.EQ.0) THEN",cal)
        self.assertIn("! ICALM  =  0  !",inp)


if __name__=="__main__":
    unittest.main()
