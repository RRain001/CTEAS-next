"""P5 wind policy v2: full-vector previous-valid hold, then original-calm replacement.

This module never reads ISD WND/C/V/N. Wind originates from ISD-Lite.
All time axes are one calendar year of UTC hours. The two scientific stages
are distinct: cleaned observations (original calm retained), followed by
model-input replacement of ONLY originally observed calm hours.
"""
from __future__ import annotations

import math
import numpy as np
import pandas as pd


class WindPolicyError(ValueError):
    pass


def shortest_arc_midpoint_deg(before: float, after: float) -> int:
    """Shortest-circular-arc midpoint in (0,360].

    Exactly opposite bearings have two equally short arcs. Choose the
    CLOCKWISE arc from the earlier to the later observation (+90 degrees
    from the earlier bearing), as explicitly required by the user.
    """
    a, b = float(before), float(after)
    if not (0 < a <= 360 and 0 < b <= 360):
        raise WindPolicyError("wind endpoints must be in (0,360]")
    separation = abs((b - a + 180.0) % 360.0 - 180.0)
    if math.isclose(separation, 180.0, abs_tol=1e-9):
        # Wind bearings increase clockwise; reversing endpoints changes
        # the selected semicircle. 1 -> 181 gives 91, not 180.
        midpoint = (a + 90.0) % 360.0
        integer = math.floor(midpoint + 0.5) % 360
        return 360 if integer == 0 else integer
    delta = (b - a + 180.0) % 360.0 - 180.0
    midpoint = (a + delta / 2.0) % 360.0
    # Source file degree resolution is integer. Half-degree ties round upward.
    integer = math.floor(midpoint + 0.5) % 360
    return 360 if integer == 0 else integer


def _runs(boolean_mask):
    mask = np.asarray(boolean_mask, dtype=bool)
    result = []
    pos = 0
    while pos < len(mask):
        if not mask[pos]:
            pos += 1
            continue
        stop = pos
        while stop + 1 < len(mask) and mask[stop + 1]:
            stop += 1
        result.append((pos, stop))
        pos = stop + 1
    return result


def clean_then_replace_calms(df: pd.DataFrame, dir_col: str, spd_col: str,
                             original_lite_presence: pd.Series | None = None,
                             strict: bool = False):
    """Return (cleaned, calm_interpolated, per-hour audit, annual summary).

    Invalid or partly missing source wind -> missing WHOLE pair -> last
    complete OBSERVED noncalm vector, unlimited duration; observed calms
    are preserved in cleaned but NEVER seed missing-data carry.
    """
    if not df.index.is_monotonic_increasing or not df.index.is_unique:
        raise WindPolicyError("hour index must be sorted and unique")
    if len(df) < 1:
        raise WindPolicyError("empty hourly wind")
    index = df.index
    if not isinstance(index, pd.DatetimeIndex):
        raise WindPolicyError("hour index must be pandas DatetimeIndex")
    if not all(t.year == index[0].year for t in index):
        raise WindPolicyError("each wind operation must be single-year")
    expected = pd.date_range(f"{index[0].year}-01-01 00:00:00",
                             f"{index[0].year}-12-31 23:00:00", freq="h")
    if not index.equals(expected):
        raise WindPolicyError("year must include every calendar-hour before cleaning")
    if original_lite_presence is None:
        # Explicit caller must mark whether the original ISD-Lite hour exists.
        raise WindPolicyError("missing original ISD-Lite hourly record-presence evidence")
    presence = original_lite_presence.reindex(index).fillna(False).astype(bool)
    wind_d = pd.to_numeric(df[dir_col], errors="coerce").replace([9999, -9999], np.nan)
    wind_s = pd.to_numeric(df[spd_col], errors="coerce").replace([9999, -9999], np.nan)
    positive = wind_s.gt(0) & wind_d.gt(0) & wind_d.le(360)
    calm_standard = presence & wind_d.eq(0) & wind_s.eq(0)
    calm_360 = presence & wind_d.eq(360) & wind_s.eq(0)
    original_calm = calm_standard | calm_360
    # Every other record is unusable as an observed complete vector.
    invalid = ~(positive | original_calm)
    positive = positive & presence
    invalid = ~(positive | original_calm)
    # Use only true observed POSITIVE wind pairs for historical forward hold.
    direction_seed = wind_d.where(positive)
    speed_seed = wind_s.where(positive)
    valid_time = pd.Series(index.where(positive), index=index)
    seed_time = pd.to_datetime(valid_time).ffill()
    hold_dir = direction_seed.ffill()
    hold_speed = speed_seed.ffill()
    cleaned_direction = hold_dir.mask(original_calm, 0.0)
    cleaned_speed = hold_speed.mask(original_calm, 0.0)

    # A raw observed calm remains calm even when no previous positive wind.
    # A missing hour without a previous positive wind remains missing (9999).
    outstanding = invalid & (hold_dir.isna() | hold_speed.isna())
    if strict and outstanding.any():
        bad_hours = index[outstanding]
        raise WindPolicyError(
            f"INVALID_WIND_NO_PREVIOUS_NONCALM_VECTOR: {len(bad_hours)} "
            f"hours, first={bad_hours[0]}, last={bad_hours[-1]}")
    cleaned = df.copy()
    cleaned[dir_col] = cleaned_direction.fillna(9999.0)
    cleaned[spd_col] = cleaned_speed.fillna(9999.0)

    # Stage 2: only original C3/C4 calm hours are replaced. Each continuous
    # observed calm run gets ONE constant midpoint direction and WS=0.5.
    # Endpoints are actual valid noncalm OBSERVATIONS, not held / synthetic.
    out_dir = cleaned_direction.copy()
    out_speed = cleaned_speed.copy()
    boundary_case = pd.Series("", index=index, dtype="object")
    left_src = pd.Series(pd.NaT, index=index, dtype="datetime64[ns]")
    right_src = pd.Series(pd.NaT, index=index, dtype="datetime64[ns]")
    runs = _runs(original_calm.to_numpy())
    valid_positions = np.flatnonzero(positive.to_numpy())
    if not len(valid_positions) and runs:
        raise WindPolicyError("CANNOT_REPLACE_CALM: year has no positive observed wind endpoint")
    for left, right in runs:
        lhs = valid_positions[valid_positions < left]
        rhs = valid_positions[valid_positions > right]
        before = int(lhs[-1]) if len(lhs) else None
        after = int(rhs[0]) if len(rhs) else None
        if before is not None and after is not None:
            angle = shortest_arc_midpoint_deg(wind_d.iloc[before], wind_d.iloc[after])
            label = "INTERIOR_CALM_MIDPOINT"
            model_speed = 0.5
        elif before is None and after is not None:
            # Leading original calm: use subsequent REAL observed noncalm vector.
            angle = int(wind_d.iloc[after])
            label = "LEADING_CALM_NEXT_VALID"
            model_speed = float(wind_s.iloc[after])
        elif before is not None and after is None:
            # Trailing original calm: use preceding REAL observed noncalm vector.
            angle = int(wind_d.iloc[before])
            label = "TRAILING_CALM_PREVIOUS_VALID"
            model_speed = float(wind_s.iloc[before])
        else:
            raise WindPolicyError("CANNOT_REPLACE_CALM: no valid endpoints")
        out_dir.iloc[left:right + 1] = angle
        out_speed.iloc[left:right + 1] = model_speed
        boundary_case.iloc[left:right + 1] = label
        if before is not None:
            left_src.iloc[left:right + 1] = index[before]
        if after is not None:
            right_src.iloc[left:right + 1] = index[after]
    interpolated = df.copy()
    interpolated[dir_col] = out_dir.fillna(9999.0)
    interpolated[spd_col] = out_speed.fillna(9999.0)

    # A valid stage-2 pair must be a real moving bearing (0,360] and WS>0,
    # or a partial 9999 sentinel pair whose missingness is reported.
    final_complete = out_dir.gt(0) & out_dir.le(360) & out_speed.gt(0)
    clean_complete = ((cleaned_direction.gt(0) & cleaned_speed.gt(0)) |
                      (cleaned_direction.eq(0) & cleaned_speed.eq(0)))
    if (out_dir.eq(0) & out_speed.gt(0)).any():
        raise WindPolicyError("produced invalid (WD=0, WS>0) final vector")
    if (original_calm & ~(out_speed.gt(0) & out_dir.gt(0))).any():
        raise WindPolicyError("failed to replace original calm")

    native_presence_count = int(presence.sum())
    num_hours = len(index)
    missing_hours = num_hours - native_presence_count
    calm_hours = int(original_calm.sum())
    invalid_hours = int(invalid.sum())
    age = (pd.Series(index, index=index) - seed_time).dt.total_seconds() / 3600
    event = pd.Series("VALID_POSITIVE_OBSERVATION", index=index, dtype="object")
    event.loc[original_calm] = "ORIGINAL_CALM"
    event.loc[invalid & presence] = "ORIGINAL_WIND_INVALID"
    event.loc[~presence] = "NO_ORIGINAL_ISD_LITE_HOUR"
    audit = pd.DataFrame({
        "original_lite_hour_present": presence,
        "original_direction_deg": wind_d,
        "original_speed_mps": wind_s,
        "source_case": event,
        "original_calms_C3_C4": original_calm,
        "original_calm_standard": calm_standard,
        "original_calm_360": calm_360,
        "whole_vector_was_held": invalid & hold_dir.notna(),
        "previous_valid_noncalm_utc": seed_time,
        "previous_valid_noncalm_age_hours": age,
        "cleaned_direction_deg": cleaned_direction,
        "cleaned_speed_mps": cleaned_speed,
        "cleaned_complete_vector": clean_complete,
        "calm_replacement_method": boundary_case,
        "calm_left_valid_utc": left_src,
        "calm_right_valid_utc": right_src,
        "model_direction_deg": out_dir,
        "model_speed_mps": out_speed,
        "model_complete_vector": final_complete,
    }, index=index)
    summary = {
        "policy": "P5_ISD_LITE_WIND_V2_WHOLE_VECTOR_HOLD_CALM_REPLACE",
        "year": index[0].year,
        "expected_calendar_hours": num_hours,
        "raw_lite_record_hours": native_presence_count,
        "raw_lite_coverage_fraction": native_presence_count / num_hours,
        "raw_absent_hours": missing_hours,
        "raw_absent_fraction": missing_hours / num_hours,
        "original_wind_invalid_hours_including_absent": invalid_hours,
        "original_wind_invalid_fraction": invalid_hours / num_hours,
        "original_calm_hours": calm_hours,
        "original_calm_fraction": calm_hours / num_hours,
        "original_calm_0_0_hours": int(calm_standard.sum()),
        "original_calm_360_0_hours": int(calm_360.sum()),
        "original_valid_positive_hours": int(positive.sum()),
        "missing_wind_held_hours": int((invalid & hold_dir.notna()).sum()),
        "missing_wind_unfilled_hours": int(outstanding.sum()),
        "cleaned_complete_wind_hours": int(clean_complete.sum()),
        "final_complete_wind_hours": int(final_complete.sum()),
        "calm_runs": len(runs),
        "calm_midpoint_hours": int((boundary_case == "INTERIOR_CALM_MIDPOINT").sum()),
        "calm_leading_hours": int((boundary_case == "LEADING_CALM_NEXT_VALID").sum()),
        "calm_trailing_hours": int((boundary_case == "TRAILING_CALM_PREVIOUS_VALID").sum()),
        "max_noncalm_wind_previous_hold_age_hours": (
            float(age[invalid].max()) if age[invalid].notna().any() else None),
        "cleaned_status": "数据清洗和缺测处理完毕",
        "interpolated_status": "静风插值处理完毕",
        "antipodal_direction_tie_policy": "CLOCKWISE_FROM_LEFT_ENDPOINT_PLUS_90_DEGREES",
        "interior_calm_speed_mps": 0.5,
        "boundary_calm_speed_policy": "COPY_NEAREST_REAL_NONCALM_VECTOR",
    }
    return cleaned, interpolated, audit, summary
