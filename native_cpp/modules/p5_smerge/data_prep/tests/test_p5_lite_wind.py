"""Regression for ISD-Lite-exclusive wind and CALMET-safe missing-wind policy."""
from __future__ import annotations

import csv
import gzip
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from native_cpp.modules.p5_smerge.data_prep import isd_lite_wind as lite
from native_cpp.modules.p5_smerge.data_prep import isd_to_smerge_and_fill as conv
from native_cpp.modules.p5_smerge.data_prep import interpolate as fill


def make_lite(root: Path, station="58321099999", year=2022, rows=None):
    directory = root / "isd_lite"
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / lite.filename(station, year)
    if rows is None:
        rows = ["2022 01 01 00 100 10 10100 360 10 0 -9999 -9999"]
    with gzip.open(path, "wt", encoding="ascii") as f:
        f.writelines(row + "\n" for row in rows)
    return path


class LiteFormat(unittest.TestCase):
    def test_official_units_calm_north_missing_and_inconsistency(self):
        with tempfile.TemporaryDirectory() as td:
            p=make_lite(Path(td), rows=[
                "2022 01 01 00 0 0 -9999 360 11 0 -9999 -9999",
                "2022 01 01 01 0 0 -9999 0 0 0 -9999 -9999",
                "2022 01 01 02 0 0 -9999 -9999 20 0 -9999 -9999",
                "2022 01 01 03 0 0 -9999 90 -9999 0 -9999 -9999",
                "2022 01 01 04 0 0 -9999 -9999 -9999 0 -9999 -9999",
                "2022 01 01 05 0 0 -9999 0 20 0 -9999 -9999",
            ])
            w=lite.parse_lite_winds(p,2022,"58321099999")
            at=lambda hr: w[pd.Timestamp(f"2022-01-01 {hr:02d}:00")]
            self.assertEqual((at(0).direction_deg,at(0).speed_mps),(360.,1.1))
            self.assertEqual((at(1).direction_deg,at(1).speed_mps),(0.,0.))
            self.assertEqual((at(2).direction_deg,at(2).speed_mps),(None,2.))
            self.assertEqual((at(3).direction_deg,at(3).speed_mps),(90.,None))
            self.assertEqual((at(4).direction_deg,at(4).speed_mps),(None,None))
            self.assertEqual((at(5).direction_deg,at(5).speed_mps),(None,2.))
            self.assertIn("NONZERO_SPEED_DIRECTION_ZERO_INVALID",at(5).flags)

    def test_malformed_lite_and_identity_fail_closed(self):
        with tempfile.TemporaryDirectory() as td:
            p=make_lite(Path(td),rows=["2022 01 01 00 1 2 3 4 5"])
            with self.assertRaisesRegex(ValueError,"12-column"):
                lite.parse_lite_winds(p,2022,"58321099999")
            with self.assertRaisesRegex(ValueError,"identity mismatch"):
                lite.parse_lite_winds(p,2022,"58314099999")

    def test_wind_exclusively_lite_other_variables_from_full_isd(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            p=root/"58321099999-2022.csv"
            with p.open("w",newline="") as f:
                w=csv.DictWriter(f, fieldnames=["STATION","DATE","WND","TMP","DEW","SLP","GF1","CIG","AA1"])
                w.writeheader()
                w.writerow({"STATION":"58321099999","DATE":"2022-01-01T00:00:00",
                            "WND":"090,1,N,0030,1","TMP":"+0250,1","DEW":"+0100,1",
                            "SLP":"10135,1","GF1":"05,1,1,1","CIG":"01000,1,1,1",
                            "AA1":"01,0012,3,1"})
            make_lite(root,rows=[
                "2022 01 01 00 100 0 10100 270 40 0 -9999 -9999",
                "2022 01 01 01 100 0 10100 -9999 20 0 -9999 -9999",
                "2022 01 01 02 100 0 10100 0 0 0 -9999 -9999",
            ])
            (root/"station_selection_2022.json").write_text(json.dumps({
                "stations":[{"sid":"58321099999","ifstn":"583210"}]}))
            with patch.object(conv,"INPUT_DIR",root):
                output,count=conv.convert_one_isd_csv(str(p),str(root/"ready"))
            self.assertEqual(count,3) # union of full-ISD and Lite timestamps
            with Path(output).open(newline="") as f:
                data=list(csv.reader(f))[3:]
            self.assertEqual((float(data[0][4]),float(data[0][6])),(25.0,1013.5))
            self.assertEqual((float(data[0][8]),float(data[0][9])),(270.0,4.0))
            self.assertEqual((float(data[1][4]),float(data[1][9])),(9999.0,2.0))
            self.assertEqual((float(data[2][8]),float(data[2][9])),(0.0,0.0))
            audit=list(csv.DictReader((root/"ready"/"583210-99999-2022_isd_lite_source_audit.csv").open()))
            self.assertEqual(len(audit),3)
            self.assertEqual(audit[1]["full_isd_report_present"],"False")
            self.assertEqual(audit[0]["source"],"NOAA_ISD_LITE")

    def test_no_isd_wnd_fallback_when_lite_missing(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            src=root/"58321099999-2022.csv"
            with src.open("w",newline="") as f:
                w=csv.DictWriter(f,fieldnames=["STATION","DATE","WND","TMP","DEW","SLP"])
                w.writeheader()
                w.writerow({"STATION":"58321099999","DATE":"2022-01-01T00:00:00",
                            "WND":"090,1,N,0030,1","TMP":"+0250,1","DEW":"+0100,1","SLP":"10135,1"})
            with patch.object(conv,"INPUT_DIR",root):
                with self.assertRaisesRegex(ValueError,"mandatory ISD-Lite wind"):
                    conv.convert_one_isd_csv(str(src),str(root/"ready"))


class WindReconstruction(unittest.TestCase):
    def test_speed_only_does_not_inherit_north_from_calm(self):
        ts=pd.date_range("2022-01-01",periods=4,freq="h")
        df=pd.DataFrame({"deg":[90,0,9999,180],"ms-1":[2,0,3,2]},index=ts)
        out,audit,summary=fill.fill_wind_forward_calm(df,"deg","ms-1")
        self.assertEqual(list(out["deg"]),[90,0,90,180])
        self.assertEqual(list(out["ms-1"]),[2,0,3,2])
        self.assertEqual(audit["observation_case"].iloc[2],"SPEED_ONLY")
        self.assertEqual(summary["observed_speed_only_hours"],1)

    def test_direction_only_and_both_missing_previous_values(self):
        ts=pd.date_range("2022-01-01",periods=4,freq="h")
        df=pd.DataFrame({"deg":[90,180,9999,270],"ms-1":[2,9999,9999,2.5]},index=ts)
        out,audit,summary=fill.fill_wind_forward_calm(df,"deg","ms-1")
        self.assertEqual(list(out["deg"]),[90,180,180,270])
        self.assertEqual(list(out["ms-1"]),[2,2,2,2.5])
        self.assertEqual(summary["observed_direction_only_hours"],1)
        self.assertEqual(summary["observed_both_missing_hours"],1)

    def test_unlimited_hourly_gap_and_noncalm_requires_real_direction(self):
        ts=pd.date_range("2022-01-01",periods=120,freq="h")
        df=pd.DataFrame({"deg":[0]+[9999]*119,
                         "ms-1":[0]+[9999]*118+[2]},index=ts)
        out,_,_=fill.fill_wind_forward_calm(df,"deg","ms-1")
        self.assertTrue((out["ms-1"].iloc[:119]==0).all())
        self.assertEqual(out["deg"].iloc[-1],9999)
        self.assertEqual(out["ms-1"].iloc[-1],2)

    def test_p5_calmet_calm_is_solver_not_input_clamp(self):
        ts=pd.date_range("2022-01-01",periods=3,freq="h")
        df=pd.DataFrame({"deg":[360,0,45],"ms-1":[1,0,0.2]},index=ts)
        out,_,metadata=fill.fill_wind_forward_calm(df,"deg","ms-1")
        self.assertEqual(list(out["ms-1"]),[1,0,0.2])
        self.assertEqual(list(out["deg"]),[360,0,45])
        self.assertEqual(metadata["calmet_calm_handling"],"DEFERRED_TO_ORIGINAL_CALMET_SOLVER")
