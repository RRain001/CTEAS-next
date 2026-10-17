"""Annual station roles: sparse auxiliaries never fill or interpolate."""
import csv
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from native_cpp.modules.p5_smerge.data_prep import interpolate as i
from native_cpp.modules.p5_smerge.data_prep import generate_smerge_input_sections as g
from native_cpp.modules.p5_smerge.data_prep.sparse_station_policy import (
    standardize_sparse_station, POLICY,
)


class SparseStationTests(unittest.TestCase):
    def observations(self):
        t = pd.to_datetime([
            "2022-01-01 18:00", "2022-01-01 20:00",
            "2022-01-01 21:00", "2022-01-01 22:00",
            "2022-01-01 23:00", "2022-01-02 00:00"])
        df = pd.DataFrame({
            "Month":[1]*6,"Day":[1]*5+[2],"Year":[2022]*6,
            "Hour":[1800,2000,2100,2200,2300,0],
            "DegC":[20,-9999,23,24,25,26],
            "mm":[9999,9999,0,2,9999,0],
            "mb":[1000,9999,9999,9999,1001,1002],
            "%":[40,9999,50,50,50,50],
            "deg":[90,360,-9999,360,0,30],
            "ms-1":[2,0,4,0,0,9999],
            "tenths":[6,9999,9999,9999,1,2],
            "hundreds_of_feet":[5,9999,9999,9999,3,4],
        }, index=t)
        return df

    def test_original_hour_gap_19_is_not_constructed(self):
        raw=self.observations()
        out,audit,meta=standardize_sparse_station(raw)
        self.assertEqual(list(out.index), list(raw.index))
        self.assertNotIn(pd.Timestamp("2022-01-01 19:00"),out.index)
        self.assertEqual(meta["rows_created_for_absent_hours"],0)
        self.assertEqual(meta["policy"],POLICY)
        self.assertEqual(meta["wind_forward_filled_hours"],0)
        self.assertEqual(meta["calm_interpolated_hours"],0)

    def test_arbitrary_multi_hour_multi_day_sparse_gaps_never_reindexed(self):
        # 18->20 is just one example; ANY absent hours remain absent,
        # including 37-hour, multi-month and year-edge spans.
        source_hours = pd.to_datetime([
            "2022-01-01 00:00",
            "2022-01-03 09:00",
            "2022-05-10 13:00",
            "2022-12-31 23:00",
        ])
        df = pd.DataFrame({
            "Month": source_hours.month, "Day": source_hours.day,
            "Year": source_hours.year, "Hour": source_hours.hour * 100,
            "deg": [45., 360., 0., 180.],
            "ms-1": [3., 0., 0., 2.],
            "DegC": [20., 9999., 22., 23.],
        }, index=source_hours)
        result, audit, summary = standardize_sparse_station(df)
        self.assertTrue(result.index.equals(source_hours))
        self.assertEqual(len(result), 4)
        self.assertNotIn(pd.Timestamp("2022-01-02 00:00"), result.index)
        self.assertNotIn(pd.Timestamp("2022-04-01 00:00"), result.index)
        self.assertNotIn(pd.Timestamp("2022-12-31 22:00"), result.index)
        self.assertEqual(summary["rows_created_for_absent_hours"], 0)
        self.assertEqual(summary["wind_forward_filled_hours"], 0)
        self.assertEqual(summary["calm_interpolated_hours"], 0)
        self.assertEqual(tuple(result.iloc[1][["deg","ms-1"]]), (0.,0.))
        self.assertEqual(tuple(result.iloc[2][["deg","ms-1"]]), (0.,0.))
        self.assertEqual(result.iloc[1]["DegC"], 9999.)

    def test_smerge_missing_sentinel_is_9999_for_pair_and_nonwind(self):
        out,_,meta=standardize_sparse_station(self.observations())
        self.assertEqual(tuple(out.loc["2022-01-01 21",["deg","ms-1"]]),(9999.,9999.))
        self.assertEqual(tuple(out.loc["2022-01-02 00",["deg","ms-1"]]),(9999.,9999.))
        self.assertEqual(out.loc["2022-01-01 20","DegC"],9999.)
        self.assertEqual(out.loc["2022-01-01 20","mb"],9999.)
        self.assertEqual(out.loc["2022-01-01 18","DegC"],20.)
        self.assertEqual(out.loc["2022-01-01 21","DegC"],23.)
        self.assertEqual(meta["invalid_wind_pair_hours"],2)
        self.assertFalse(meta["missing_data_filled"])

    def test_two_original_calm_codes_both_remain_zero_speed(self):
        out,audit,meta=standardize_sparse_station(self.observations())
        self.assertEqual(tuple(out.loc["2022-01-01 20",["deg","ms-1"]]),(0.,0.))
        self.assertEqual(tuple(out.loc["2022-01-01 22",["deg","ms-1"]]),(0.,0.))
        self.assertEqual(tuple(out.loc["2022-01-01 23",["deg","ms-1"]]),(0.,0.))
        self.assertEqual(meta["observed_calm_hours"],3)
        self.assertTrue(bool(audit.loc["2022-01-01 22","original_calm"]))

    def test_smerge_date_interval_does_not_require_any_valid_wind(self):
        with tempfile.TemporaryDirectory() as td:
            file=Path(td)/"583140-99999.csv"
            with file.open("w",newline="") as f:
                w=csv.writer(f)
                w.writerow(["GENERIC","Version","'2.0'","Manuallygenerated","Timeasendinghour",""])
                w.writerow(["Station","ID","='","583140","Temp","Precip","Pressure","RH","Wdir10m","Wspeed10m","Ccover","Cheight"])
                w.writerow(["Month","Day","Year","Hour","DegC","mm","mb","%","deg","ms-1","tenths","hundreds_of_feet"])
                w.writerow([1,1,2022,1800,9999,9999,9999,9999,9999,9999,9999,9999])
                w.writerow([1,1,2022,2000,9999,9999,9999,9999,9999,9999,9999,9999])
            begin,end=g.detect_time_range_from_any_source_hour(file)
            self.assertEqual(begin,pd.Timestamp("2022-01-01 18:00"))
            self.assertEqual(end,pd.Timestamp("2022-01-01 20:00"))
            self.assertEqual(g.detect_global_period([("583140","99999",file)]),(begin,end))

    def test_original_fortran_eof_terminal_is_runtime_only_no_interior_fill(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            source=root/"ready/583140-99999.csv"
            source.parent.mkdir()
            with source.open("w",newline="") as f:
                w=csv.writer(f)
                w.writerow(["GENERIC","Version","'2.0'","Manuallygenerated","Timeasendinghour",""])
                w.writerow(["Station","ID","='","583140","Temp","Precip","Pressure","RH","Wdir10m","Wspeed10m","Ccover","Cheight"])
                w.writerow(["Month","Day","Year","Hour","DegC","mm","mb","%","deg","ms-1","tenths","hundreds_of_feet"])
                w.writerow([1,1,2022,1800,20,0,1000,50,60,2,5,10])
                w.writerow([1,1,2022,2000,21,0,1000,50,9999,9999,5,10])
            original_bytes=source.read_bytes()
            with patch.object(g,"OUTPUT_DIR",root/"run/smerge"):
                runtime=g.stage_original_smerge_terminal_record(
                    [("583140","99999",source)],
                    pd.Timestamp("2022-01-01 23:00"))
            self.assertEqual(source.read_bytes(),original_bytes)
            self.assertEqual(len(runtime),1)
            self.assertNotEqual(runtime[0][2],source)
            with runtime[0][2].open(newline="") as f:
                rows=list(csv.reader(f))
            self.assertEqual([int(float(r[3])) for r in rows[3:]],[1800,2000,2300])
            self.assertNotIn(1900,[int(float(r[3])) for r in rows[3:]])
            self.assertEqual([float(v) for v in rows[-1][4:]], [9999.]*8)

    def test_real_generic_3_header_file_and_manifest_role(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            source=root/"isd2smerge_and_fill"
            source.mkdir()
            raw=root/"isd_raw"
            raw.mkdir()
            sid="58314099999"
            manifest={
                "year":2022,"primary_sid":"58321099999",
                "stations":[
                    {"sid":"58321099999","wind_treatment":"COMPLETE_FILL_AND_CALM_REPLACE"},
                    {"sid":sid,"wind_treatment":"RAW_SPARSE_STANDARDIZE_ONLY"},
                ],
            }
            (raw/"station_selection_2022.json").write_text(json.dumps(manifest))
            input_path=source/"583140-99999-2022.csv"
            sample=self.observations()
            with input_path.open("w",newline="") as f:
                w=csv.writer(f)
                w.writerow(["GENERIC","Version","'2.0'","Manuallygenerated","Timeasendinghour",""])
                w.writerow(["Station","ID","='","583140","Temp","Precip","Pressure","RH","Wdir10m","Wspeed10m","Ccover","Cheight"])
                w.writerow(["Month","Day","Year","Hour","DegC","mm","mb","%","deg","ms-1","tenths","hundreds_of_feet"])
                w.writerows(sample.itertuples(index=False,name=None))
            self.assertEqual(i.read_selection_role(input_path),"RAW_SPARSE_STANDARDIZE_ONLY")
            h,data,audit,meta=i.process_sparse_station(input_path)
            result=i.save_sparse_station(input_path,h,data)
            self.assertTrue(Path(result).is_file())
            self.assertFalse(Path(result.replace("_filled.csv","_cleaned.csv")).exists())
            with Path(result).open(newline="") as f:
                records=list(csv.reader(f))
            self.assertEqual(len(records), 3+len(sample))
            self.assertEqual(records[2], ["Month","Day","Year","Hour","DegC","mm","mb","%","deg","ms-1","tenths","hundreds_of_feet"])
            self.assertEqual(float(records[4][8]),0.)
            self.assertEqual(float(records[5][8]),9999.)
            stage=json.loads(Path(result.replace(".csv",".stage.json")).read_text())
            self.assertEqual(stage["wind_policy"],POLICY)
            self.assertEqual(stage["missing_sentinel"],9999)


if __name__=="__main__":
    unittest.main()
