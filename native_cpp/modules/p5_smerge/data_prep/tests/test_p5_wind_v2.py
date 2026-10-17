"""Scientific policy v2 regression: ISD-Lite full wind vectors then original-calm replacement."""
from __future__ import annotations

import unittest
import pandas as pd
from native_cpp.modules.p5_smerge.data_prep.wind_policy_v2 import (
    clean_then_replace_calms, shortest_arc_midpoint_deg, WindPolicyError,
)


def annual(year=2022):
    idx = pd.date_range(f"{year}-01-01", f"{year}-12-31 23:00", freq="h")
    df = pd.DataFrame({"deg": 9999., "ms-1": 9999.}, index=idx)
    present = pd.Series(False, index=idx)
    return df, present


def obs(df, present, hour, direction, speed):
    df.loc[hour, "deg"] = direction
    df.loc[hour, "ms-1"] = speed
    present.loc[hour] = True


class ArcTests(unittest.TestCase):
    def test_zero_180_midpoints_and_directional_clockwise_antipodal_tie(self):
        for a,b,expect in [
            (350,10,360), (360,360,360), (10,350,360),
            (170,190,180), (190,170,180), (180,180,180),
            (90,270,180), (270,90,360),
            (1,181,91), (181,1,271), (360,180,90), (180,360,270),
            (350,30,10), (30,350,10),
        ]:
            with self.subTest(a=a,b=b):
                self.assertEqual(shortest_arc_midpoint_deg(a,b),expect)
        with self.assertRaises(WindPolicyError):
            shortest_arc_midpoint_deg(0,20)


class TwoStagesTests(unittest.TestCase):
    def test_partial_invalid_uses_whole_previous_noncalm_not_current_speed(self):
        df,p=annual()
        obs(df,p,"2022-01-01 00",90,2)
        obs(df,p,"2022-01-01 01",9999,3) # entire vector invalid
        obs(df,p,"2022-01-01 02",0,0) # real calm cannot seed ffill
        obs(df,p,"2022-01-01 03",0,9999) # invalid whole pair
        obs(df,p,"2022-01-01 04",120,4)
        cleaned,modeled,audit,summary=clean_then_replace_calms(df,"deg","ms-1",p)
        self.assertEqual((cleaned.iloc[1]["deg"],cleaned.iloc[1]["ms-1"]),(90,2))
        self.assertEqual((cleaned.iloc[2]["deg"],cleaned.iloc[2]["ms-1"]),(0,0))
        self.assertEqual((cleaned.iloc[3]["deg"],cleaned.iloc[3]["ms-1"]),(90,2))
        self.assertEqual((modeled.iloc[2]["deg"],modeled.iloc[2]["ms-1"]),(105,0.5))
        self.assertEqual((modeled.iloc[3]["deg"],modeled.iloc[3]["ms-1"]),(90,2))
        self.assertEqual(summary["original_calm_hours"],1)
        self.assertEqual(summary["raw_lite_record_hours"],5)
        self.assertEqual(summary["raw_absent_hours"],8755)
        self.assertEqual(summary["original_wind_invalid_hours_including_absent"],8757)
        self.assertEqual(audit.iloc[3]["previous_valid_noncalm_utc"],df.index[0])
        self.assertEqual(audit.iloc[3]["source_case"],"ORIGINAL_WIND_INVALID")
        self.assertEqual(audit.iloc[5]["source_case"],"NO_ORIGINAL_ISD_LITE_HOUR")

    def test_contiguous_calm_segment_constant_bearing_and_half_mps(self):
        df,p=annual()
        obs(df,p,"2022-01-01 10",90,2)
        for hr in (11,12,13):
            obs(df,p,f"2022-01-01 {hr:02d}",0,0)
        obs(df,p,"2022-01-01 14",180,4)
        cleaned,model,audit,summary=clean_then_replace_calms(df,"deg","ms-1",p)
        self.assertEqual([model.iloc[i]["deg"] for i in (11,12,13)],[135]*3)
        self.assertEqual([model.iloc[i]["ms-1"] for i in (11,12,13)],[0.5]*3)
        self.assertEqual([cleaned.iloc[i]["ms-1"] for i in (11,12,13)],[0]*3)
        self.assertEqual(summary["calm_midpoint_hours"],3)
        self.assertEqual(summary["original_calm_hours"],3)
        self.assertEqual(audit.iloc[11]["calm_replacement_method"],"INTERIOR_CALM_MIDPOINT")

    def test_leading_and_trailing_calm_copy_nearest_real_vector(self):
        df,p=annual()
        obs(df,p,"2022-01-01 00",0,0)
        obs(df,p,"2022-01-01 01",360,3)
        obs(df,p,"2022-12-31 22",190,2)
        obs(df,p,"2022-12-31 23",0,0)
        cleaned,model,_,summary=clean_then_replace_calms(df,"deg","ms-1",p)
        self.assertEqual((model.iloc[0]["deg"],model.iloc[0]["ms-1"]),(360,3))
        self.assertEqual((model.iloc[-1]["deg"],model.iloc[-1]["ms-1"]),(190,2))
        self.assertEqual((cleaned.iloc[0]["deg"],cleaned.iloc[0]["ms-1"]),(0,0))
        self.assertEqual(summary["calm_leading_hours"],1)
        self.assertEqual(summary["calm_trailing_hours"],1)
        self.assertEqual(summary["original_calm_hours"],2)

    def test_360_calm_normalization_preserves_source_counter(self):
        df,p=annual()
        obs(df,p,"2022-01-01 00",350,2)
        obs(df,p,"2022-01-01 01",360,0)
        obs(df,p,"2022-01-01 02",10,4)
        clean,model,audit,summary=clean_then_replace_calms(df,"deg","ms-1",p)
        self.assertEqual((clean.iloc[1]["deg"],clean.iloc[1]["ms-1"]),(0,0))
        self.assertEqual((model.iloc[1]["deg"],model.iloc[1]["ms-1"]),(360,0.5))
        self.assertEqual(summary["original_calm_360_0_hours"],1)
        self.assertEqual(bool(audit.iloc[1]["original_calms_C3_C4"]),True)

    def test_zero_direction_positive_speed_and_partial_speed_are_invalid(self):
        df,p=annual()
        obs(df,p,"2022-01-01 00",45,1)
        obs(df,p,"2022-01-01 01",0,2)
        obs(df,p,"2022-01-01 02",90,9999)
        obs(df,p,"2022-01-01 03",9999,9999)
        clean,model,_,summary=clean_then_replace_calms(df,"deg","ms-1",p)
        for i in (1,2,3):
            self.assertEqual((clean.iloc[i]["deg"],clean.iloc[i]["ms-1"]),(45,1))
            self.assertEqual((model.iloc[i]["deg"],model.iloc[i]["ms-1"]),(45,1))
        self.assertEqual(summary["original_calm_hours"],0)

    def test_hour_absent_and_hour_present_but_both_missing_distinct(self):
        df,p=annual()
        obs(df,p,"2022-01-01 18",60,2)
        obs(df,p,"2022-01-01 20",120,3)
        obs(df,p,"2022-01-01 21",9999,9999)
        clean,_,audit,summary=clean_then_replace_calms(df,"deg","ms-1",p)
        self.assertEqual((clean.loc["2022-01-01 19","deg"],
                          clean.loc["2022-01-01 19","ms-1"]),(60,2))
        self.assertEqual((clean.loc["2022-01-01 21","deg"],
                          clean.loc["2022-01-01 21","ms-1"]),(120,3))
        self.assertEqual(audit.loc["2022-01-01 19","source_case"],"NO_ORIGINAL_ISD_LITE_HOUR")
        self.assertEqual(audit.loc["2022-01-01 21","source_case"],"ORIGINAL_WIND_INVALID")
        self.assertEqual(summary["raw_lite_record_hours"],3)

    def test_no_valid_vector_raises_for_original_calm(self):
        df,p=annual()
        obs(df,p,"2022-01-01 00",0,0)
        with self.assertRaisesRegex(WindPolicyError,"no positive observed wind"):
            clean_then_replace_calms(df,"deg","ms-1",p)

    def test_strict_leading_unfillable_hours(self):
        df,p=annual()
        obs(df,p,"2022-01-01 00",9999,3)
        obs(df,p,"2022-01-01 01",90,2)
        with self.assertRaisesRegex(WindPolicyError,"NO_PREVIOUS_NONCALM"):
            clean_then_replace_calms(df,"deg","ms-1",p,strict=True)
        cleaned,modeled,_,_=clean_then_replace_calms(df,"deg","ms-1",p,strict=False)
        self.assertEqual((cleaned.iloc[0]["deg"],cleaned.iloc[0]["ms-1"]),(9999,9999))
        self.assertEqual((modeled.iloc[0]["deg"],modeled.iloc[0]["ms-1"]),(9999,9999))

    def test_leap_year_expected_denominator(self):
        df,p=annual(2024)
        obs(df,p,"2024-01-01 00",90,2)
        _,_,_,summary=clean_then_replace_calms(df,"deg","ms-1",p)
        self.assertEqual(summary["expected_calendar_hours"],8784)
        self.assertEqual(summary["raw_lite_coverage_fraction"],1/8784)
