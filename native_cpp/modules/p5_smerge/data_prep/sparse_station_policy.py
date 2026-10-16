"""P5 auxiliary IN-DOMAIN station: SMERGE GENERIC-ready, NO imputation.

Original station observation timestamps are retained verbatim: never invent
an absent whole hour, never forward-fill any meteorological field, and do not
replace observed calm winds. The chosen primary station uses the separate
complete annual wind_policy_v2.py instead.

All missing numeric fields use SMERGE GENERIC's 9999 (not ISD-Lite's -9999).
If either wind component is missing or invalid, BOTH are set to 9999.
"""
from __future__ import annotations
import numpy as np
import pandas as pd

POLICY = "P5_SPARSE_STANDARDIZE_ONLY_V1"
MISSING = 9999.0
FIELDS = ("DegC", "mm", "mb", "%", "deg", "ms-1", "tenths",
          "hundreds_of_feet")


def standardize_sparse_station(source: pd.DataFrame):
    """Return (observed-hour-only DataFrame, per-hour audit, year summary).

    Input is the RAW merged NOAA GENERIC table indexed by UTC hours, before
    any model-data previous-value filling. Numeric 0/0 and 360/0 are calms.
    """
    if not isinstance(source.index, pd.DatetimeIndex):
        raise ValueError("sparse station requires UTC datetime index")
    if source.index.has_duplicates or not source.index.is_monotonic_increasing:
        raise ValueError("sparse station source hours must be unique and ordered")
    if source.empty:
        raise ValueError("sparse station contains no source observations")
    if len(set(source.index.year)) != 1:
        raise ValueError("sparse station output must be single calendar year")
    if not {"deg", "ms-1"}.issubset(source.columns):
        raise ValueError("sparse station missing mandatory wind columns")

    out = source.copy()
    for field in FIELDS:
        if field in out.columns:
            vals = pd.to_numeric(out[field], errors="coerce")
            vals = vals.replace([float("inf"), float("-inf"), -9999., 9999.], np.nan)
            out[field] = vals.fillna(MISSING)
    direction = out["deg"]
    speed = out["ms-1"]
    noncalm = direction.gt(0) & direction.le(360) & speed.gt(0) & speed.lt(MISSING)
    calm = (direction.eq(0) | direction.eq(360)) & speed.eq(0)
    invalid = ~(noncalm | calm)
    out.loc[calm, ["deg", "ms-1"]] = [0., 0.]
    out.loc[invalid, ["deg", "ms-1"]] = [MISSING, MISSING]

    for field in ("Month", "Day", "Year", "Hour"):
        if field not in out.columns:
            raise ValueError(f"sparse station required time field absent: {field}")
    year = int(out.index[0].year)
    expected = 8784 if pd.Timestamp(year,12,31).is_leap_year else 8760
    audit = pd.DataFrame({
        "observed_merged_hour_present": True,
        "raw_wind_direction_deg": direction,
        "raw_wind_speed_mps": speed,
        "original_valid_noncalm": noncalm,
        "original_calm": calm,
        "original_invalid_wind_pair": invalid,
        "out_wind_direction_deg": out["deg"],
        "out_wind_speed_mps": out["ms-1"],
        "wind_was_forward_filled": False,
        "calm_was_interpolated": False,
    }, index=out.index)
    summary = {
        "policy": POLICY,
        "role": "RAW_SPARSE_STANDARDIZE_ONLY",
        "year": year,
        "expected_calendar_hours": expected,
        "merged_source_hour_rows": len(source),
        "rows_created_for_absent_hours": 0,
        "observed_complete_noncalm_hours": int(noncalm.sum()),
        "observed_calm_hours": int(calm.sum()),
        "invalid_wind_pair_hours": int(invalid.sum()),
        "wind_pair_missing_sentinel": 9999,
        "nonwind_missing_sentinel": 9999,
        "wind_forward_filled_hours": 0,
        "calm_interpolated_hours": 0,
        "missing_data_filled": False,
    }
    return out, audit, summary
