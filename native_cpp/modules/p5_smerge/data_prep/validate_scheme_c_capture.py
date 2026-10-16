#!/usr/bin/env python3
"""P5 v2 real-input validator, historically named validate_scheme_c_capture.

Verify the final CALMET-bound GENERIC matches the SECOND scientific stage;
the first stage preserves actual NOAA calm. No claim of full Fortran parity.
"""
from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime
from pathlib import Path


EXPECTED_POLICY = "P5_ISD_LITE_WIND_V2_WHOLE_VECTOR_HOLD_CALM_REPLACE"
FIELD_HEADER = "Month,Day,Year,Hour,DegC,mm,mb,%,deg,ms-1,tenths,hundreds_of_feet"


def _read_generic(path: Path):
    with path.open(encoding="utf-8", newline="") as stream:
        hdr = [next(stream).strip() for _ in range(3)]
        rows = list(csv.reader(stream))
    if hdr[2] != FIELD_HEADER:
        raise ValueError(f"GENERIC schema changed: {hdr[2]}")
    by_hour = {}
    for row in rows:
        if len(row) != 12:
            raise ValueError(f"unexpected row width: {row}")
        dt = datetime(int(row[2]), int(row[0]), int(row[1]), int(row[3]) // 100)
        if dt in by_hour:
            raise ValueError(f"duplicate GENERIC UTC hour: {dt}")
        by_hour[dt] = row
    return hdr, by_hour


def run(case_root: Path, expected_hours: int = 144) -> dict:
    base = case_root / "met" / "surface"
    selection = sorted((base / "isd_raw").glob("station_selection_*.json"))
    if len(selection) != 1:
        raise ValueError(f"expected one calendar-year manifest: {selection}")
    m = json.loads(selection[0].read_text(encoding="utf-8"))
    stations = m.get("stations", [])
    if len(stations) != 1 or not stations[0]["relocated"]:
        raise ValueError("reference case must have exactly one virtual station")
    station = stations[0]
    prefix = f"{station['sid'][:6]}-{station['sid'][6:]}-{m['year']}"
    prepared = base / "isd2smerge_and_fill"
    cleaned = prepared / f"{prefix}_cleaned.csv"
    interpolated = prepared / f"{prefix}_calm_interpolated.csv"
    audit = prepared / f"{prefix}_filled_wind_audit.csv"
    metadata = audit.with_suffix(".json")
    ready = base / "isd2smerge_ready" / f"{station['sid'][:6]}-{station['sid'][6:]}.csv"
    final_full = prepared / f"{prefix}_filled.csv"
    for path in (cleaned, interpolated, audit, metadata, ready, final_full):
        if not path.is_file():
            raise FileNotFoundError(f"missing P5 v2 mandatory stage: {path}")
    c_head, c_rows = _read_generic(cleaned)
    i_head, i_rows = _read_generic(interpolated)
    f_head, f_rows = _read_generic(final_full)
    r_head, r_rows = _read_generic(ready)
    if i_rows != f_rows:
        raise ValueError("full-year downstream *_filled differs from calm-interpolated stage")
    for path, expected_stage, expected_status in (
        (cleaned, "cleaned", "数据清洗和缺测处理完毕"),
        (interpolated, "calm_interpolated", "静风插值处理完毕"),
    ):
        status_path = path.with_suffix(".stage.json")
        if not status_path.is_file():
            raise FileNotFoundError(f"missing scientific-stage status: {status_path}")
        marker = json.loads(status_path.read_text(encoding="utf-8"))
        if marker.get("stage") != expected_stage or marker.get("status") != expected_status:
            raise ValueError(f"wrong scientific-stage marker: {marker}")
    if int(r_head[1].split(",")[3]) != int(station["ifstn"]):
        raise ValueError("station identity changed")
    if len(r_rows) != expected_hours:
        raise ValueError(f"expected {expected_hours} ready hours, got {len(r_rows)}")
    if len(c_rows) != len(i_rows) or len(c_rows) not in (8760, 8784):
        raise ValueError("stage1 and stage2 must have full calendar-year coverage")
    if c_rows.keys() != i_rows.keys():
        raise ValueError("stage1/stage2 time axes differ")
    details = json.loads(metadata.read_text(encoding="utf-8"))
    if details.get("policy") != EXPECTED_POLICY:
        raise ValueError(f"unexpected wind policy {details.get('policy')}")
    if details["original_calm_hours"] != details["original_calm_0_0_hours"] + details["original_calm_360_0_hours"]:
        raise ValueError("source calm accounting broken")
    with audit.open(encoding="utf-8", newline="") as stream:
        audit_rows = {datetime.fromisoformat(x["at_utc"].rstrip("Z")): x for x in csv.DictReader(stream)}
    if len(audit_rows) != len(c_rows):
        raise ValueError("hourly audit missing source hours")
    calm_checked = 0
    held_checked = 0
    for when, before in c_rows.items():
        after = i_rows[when]
        info = audit_rows[when]
        is_calm = info["original_calms_C3_C4"] == "True"
        raw_missing = info["original_lite_hour_present"] == "False"
        if float(before[8]) == 9999 or float(before[9]) == 9999:
            if info["cleaned_complete_vector"] != "False":
                raise ValueError(f"false cleaned vector validity: {when}")
        if is_calm:
            calm_checked += 1
            if float(before[8]) != 0 or float(before[9]) != 0:
                raise ValueError(f"original calm missing from stage1: {when}")
            if not (0 < float(after[8]) <= 360 and float(after[9]) > 0):
                raise ValueError(f"calm not replaced in stage2: {when}")
            method = info["calm_replacement_method"]
            if method == "INTERIOR_CALM_MIDPOINT" and float(after[9]) != 0.5:
                raise ValueError(f"interior calm must be 0.5 m/s: {when}")
            if method not in ("INTERIOR_CALM_MIDPOINT","LEADING_CALM_NEXT_VALID","TRAILING_CALM_PREVIOUS_VALID"):
                raise ValueError(f"unrecognized calm endpoint handling {when}")
        elif before[8:10] != after[8:10]:
            raise ValueError(f"noncalm changed between stages: {when}")
        if info["whole_vector_was_held"] == "True":
            held_checked += 1
        if when in r_rows:
            ready_row = r_rows[when]
            if ready_row[8:10] != after[8:10]:
                raise ValueError(f"ready wind differs from calm-interpolated stage: {when}")
            if abs(float(info["model_direction_deg"]) - float(ready_row[8])) > 0.50001:
                raise ValueError(f"audit model WD mismatch: {when}")
            if abs(float(info["model_speed_mps"]) - float(ready_row[9])) > 0.001:
                raise ValueError(f"audit model WS mismatch: {when}")
    if calm_checked != details["original_calm_hours"]:
        raise ValueError("original calm count differs from actual source rows")
    if len(r_rows) and not all(x in i_rows for x in r_rows):
        raise ValueError("ready time missing in annual stage2")
    return {
        "policy": EXPECTED_POLICY,
        "station": station["sid"],
        "annual_hours": len(c_rows),
        "ready_hours": len(r_rows),
        "raw_original_isd_lite_hours": details["raw_lite_record_hours"],
        "raw_absent_hours": details["raw_absent_hours"],
        "raw_wind_invalid_hours": details["original_wind_invalid_hours_including_absent"],
        "original_calm_hours": calm_checked,
        "whole_vector_held_hours": held_checked,
        "matched_ready_vs_stage2_hours": len(r_rows),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--case-root", type=Path, default=Path("project/current"))
    ap.add_argument("--expected-hours", type=int, default=144)
    ap.add_argument("--report", type=Path)
    args = ap.parse_args()
    info = run(args.case_root, args.expected_hours)
    print("P5_WIND_V2_TWO_STAGE_REAL_DATA=PASS", json.dumps(info, sort_keys=True))
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(info, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
