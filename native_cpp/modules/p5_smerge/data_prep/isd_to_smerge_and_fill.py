#!/usr/bin/env python3
import csv
import datetime as dt
import math
import os
import re
import subprocess
import sys
from pathlib import Path
from collections import defaultdict
from .isd_lite_wind import parse_lite_winds, filename as lite_filename, sha256_file

from engine.core.paths import current_project_path, engine_path

MISSING_NUM = 9999
SCRIPT_DIR = Path(__file__).resolve().parent
BASE_DIR = current_project_path("met", "surface")
INPUT_DIR = BASE_DIR / "isd_raw"
OUTPUT_DIR = BASE_DIR / "isd2smerge_and_fill"


def parse_compound(value):
    if not value:
        return None
    return value.split(",")


def parse_tmp_c(value):
    p = parse_compound(value)
    if not p:
        return None
    try:
        v = int(p[0])
    except ValueError:
        return None
    if v == 9999:
        return None
    return v / 10.0


def parse_slp_mb(value):
    p = parse_compound(value)
    if not p:
        return None
    try:
        v = int(p[0])
    except ValueError:
        return None
    if v == 99999:
        return None
    return v / 10.0


VALID_ISD_WIND_QC = frozenset({"0", "1", "4", "5", "9"})


def parse_wind(value):
    """按字段独立解码 ISD WND(Atmos ISD_FORWARD_FILL_CALM_ARC_V1 语义)。

    - 方向与速度各自判定可用性(5 段结构 + QC 码 + 取值范围),一方缺失不再牵连另一方;
    - 速度码 0000 保留为 0.0 m/s(静风),不再改写为 0.1 m/s 北风;
    - 方向码 999 / 速度码 9999 仅把本字段置为缺失。
    """
    p = parse_compound(value)
    parts = p if p else []
    five = len(parts) == 5
    d_code = parts[0] if five else None
    d_qc = parts[1] if five else None
    s_code = parts[3] if five else None
    s_qc = parts[4] if five else None
    d = int(d_code) if d_code and re.fullmatch(r"[0-9]{3}", d_code) else None
    s10 = int(s_code) if s_code and re.fullmatch(r"[0-9]{4}", s_code) else None

    direction = None
    if d is not None and d != 999 and 0 <= d <= 360 and d_qc in VALID_ISD_WIND_QC:
        direction = float(d)
    speed = None
    if s10 is not None and s10 != 9999 and 0 <= s10 <= 9000 and s_qc in VALID_ISD_WIND_QC:
        speed = s10 / 10.0
    return direction, speed


def parse_precip_mm_1h(row):
    for k in ("AA1", "AA2", "AA3", "AA4"):
        v = row.get(k, "")
        if not v:
            continue
        p = v.split(",")
        if len(p) < 2:
            continue
        if p[0] != "01":
            continue
        if p[1] == "9999":
            return None
        try:
            mm10 = int(p[1])
        except ValueError:
            continue
        return mm10 / 10.0
    return None


def parse_cloud_tenths_from_gf1(value):
    p = parse_compound(value)
    if not p:
        return None
    code = p[0].strip()
    if len(code) == 2 and code.isdigit():
        v = int(code)
        if 0 <= v <= 9:
            return float(v)
    return None


def parse_cheight_hundreds_ft_from_cig(value):
    p = parse_compound(value)
    if not p:
        return None
    first = p[0].strip()
    if first == "99999":
        return 999.0
    try:
        meters = float(first)
    except ValueError:
        return None
    return float(round((meters * 3.28084) / 100.0))


def calc_rh(temp_c, dew_c):
    if temp_c is None or dew_c is None:
        return None
    a = math.exp((17.625 * dew_c) / (243.04 + dew_c))
    b = math.exp((17.625 * temp_c) / (243.04 + temp_c))
    if b == 0:
        return None
    rh = max(0.0, min(100.0, 100.0 * a / b))
    return float(round(rh))


def score_row(row, rounded_hour):
    report = row.get("REPORT_TYPE", "")
    d = row.get("DATE", "")
    try:
        obs = dt.datetime.fromisoformat(d)
    except ValueError:
        return (-1e18, -1e9, -1e9)
    minute_score = -abs((obs - rounded_hour).total_seconds())
    report_score = 2 if report == "FM-12" else (1 if report == "FM-16" else 0)
    slp_score = 1 if parse_slp_mb(row.get("SLP", "")) is not None else 0
    return (minute_score, report_score, slp_score)


def station_id_parts(station_text):
    m = re.match(r"^([0-9A-Za-z]{6})([0-9A-Za-z]{5})$", station_text or "")
    if m:
        return m.group(1), m.group(2)
    return "000000", "99999"


def derive_year_from_rows(rows):
    if not rows:
        return "2023"
    return str(rows[0][2])


def convert_one_isd_csv(path, output_dir):
    grouped = defaultdict(list)
    station = None
    expected = re.fullmatch(r"([0-9A-Za-z]{11})-(\d{4})\.csv", os.path.basename(path))
    if expected is None:
        raise ValueError(f"invalid NOAA station filename: {path}")
    expected_sid, expected_year = expected.groups()
    required = {"STATION", "DATE", "WND", "TMP", "DEW", "SLP"}
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        r = csv.DictReader(f)
        if not r.fieldnames or not required.issubset(r.fieldnames):
            raise ValueError(f"NOAA required field names missing: {r.fieldnames}")
        for row in r:
            if (row.get("STATION") or "").strip() != expected_sid:
                raise ValueError(f"NOAA source STATION does not match file name: {path}")
            if station is None:
                station = row.get("STATION", "")
            ds = row.get("DATE", "")
            try:
                obs = dt.datetime.fromisoformat(ds)
            except ValueError:
                continue
            h = obs.replace(minute=0, second=0, microsecond=0)
            if obs.minute <= 10:
                rounded = h
            elif obs.minute >= 50:
                rounded = h + dt.timedelta(hours=1)
            else:
                continue
            grouped[rounded].append(row)

    # Wind values MUST come exclusively from same-station/year ISD-Lite.
    # Never reuse the complete-ISD WND, even if an hour is missing in Lite.
    lite_path = INPUT_DIR / "isd_lite" / lite_filename(expected_sid, int(expected_year))
    if not lite_path.is_file():
        raise ValueError(f"mandatory ISD-Lite wind source missing: {lite_path}")
    lite_wind = parse_lite_winds(lite_path, int(expected_year), expected_sid)
    all_hours = sorted(set(grouped) | set(lite_wind))
    if not all_hours:
        raise ValueError(f"neither NOAA source has observations: {expected_sid}/{expected_year}")
    wind_source_audit = []

    out_rows = []
    for t in all_hours:
        best = max(grouped[t], key=lambda rr: score_row(rr, t)) if grouped.get(t) else {}
        temp = parse_tmp_c(best.get("TMP", ""))
        dew = parse_tmp_c(best.get("DEW", ""))
        slp = parse_slp_mb(best.get("SLP", ""))
        wind = lite_wind.get(t)
        # No implicit fallback to ISD WND; wind source is exclusively ISD-Lite.
        wdir = wind.direction_deg if wind is not None else None
        wspd = wind.speed_mps if wind is not None else None
        precip = parse_precip_mm_1h(best)
        ccover = parse_cloud_tenths_from_gf1(best.get("GF1", ""))
        cheight = parse_cheight_hundreds_ft_from_cig(best.get("CIG", ""))
        rh = calc_rh(temp, dew)
        wind_source_audit.append({
            "at_utc": t.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "source": "NOAA_ISD_LITE",
            "lite_report_present": wind is not None,
            "full_isd_report_present": bool(best),
            "wind_direction_code": wind.source_direction_code if wind else -9999,
            "wind_speed_code_tenths": wind.source_speed_code if wind else -9999,
            "wind_direction_deg": wdir if wdir is not None else 9999,
            "wind_speed_mps": wspd if wspd is not None else 9999,
            "flags": "|".join(wind.flags) if wind else "LITE_WHOLE_HOUR_MISSING",
        })

        y, m, d, h = t.year, t.month, t.day, t.hour * 100
        out_rows.append(
            [
                m,
                d,
                y,
                h,
                temp if temp is not None else MISSING_NUM,
                precip if precip is not None else MISSING_NUM,
                slp if slp is not None else MISSING_NUM,
                rh if rh is not None else MISSING_NUM,
                wdir if wdir is not None else MISSING_NUM,
                wspd if wspd is not None else MISSING_NUM,
                ccover if ccover is not None else MISSING_NUM,
                cheight if cheight is not None else MISSING_NUM,
            ]
        )

    usaf, wban = station_id_parts(station)
    year = derive_year_from_rows(out_rows)
    if year != expected_year:
        raise ValueError(f"NOAA year disagrees with filename: {path}")
    from json import loads
    selection_path = INPUT_DIR / f"station_selection_{year}.json"
    if not selection_path.is_file():
        raise ValueError(f"required P5 source-selection manifest absent: {selection_path}")
    selected = loads(selection_path.read_text(encoding="utf-8"))["stations"]
    ids = [str(row["ifstn"]) for row in selected if row["sid"] == station]
    if len(ids) != 1 or not ids[0].isdecimal():
        raise ValueError(f"NOAA identity {station} has no unique numeric SMERGE alias")
    ifstn = ids[0]
    out_name = f"{usaf}-{wban}-{year}.csv"
    os.makedirs(output_dir, exist_ok=True)
    out_path = os.path.join(output_dir, out_name)

    with open(out_path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["GENERIC", "Version", "'2.0'", "Manuallygenerated", "Timeasendinghour", ""])
        w.writerow(["Station", "ID", "='", ifstn, "Temp", "Precip", "Pressure", "RH", "Wdir10m", "Wspeed10m", "Ccover", "Cheight"])
        w.writerow(["Month", "Day", "Year", "Hour", "DegC", "mm", "mb", "%", "deg", "ms-1", "tenths", "hundreds_of_feet"])
        for r in out_rows:
            w.writerow(r)

    # Separate, source-level audit; do not alter the 3-header-line
    # SMERGE GENERIC format. Keep raw ISD-Lite hash for reproducibility.
    wind_audit_path = Path(output_dir) / f"{usaf}-{wban}-{year}_isd_lite_source_audit.csv"
    if wind_source_audit:
        with wind_audit_path.open("w", encoding="utf-8", newline="") as dest:
            writer = csv.DictWriter(dest, fieldnames=list(wind_source_audit[0]))
            writer.writeheader()
            writer.writerows(wind_source_audit)
    (Path(output_dir) / f"{usaf}-{wban}-{year}_isd_lite_source.json").write_text(
        __import__("json").dumps({
            "station": station,
            "year": int(year),
            "wind_source": "NOAA_ISD_LITE",
            "source_file": str(lite_path),
            "source_sha256": sha256_file(lite_path),
            "original_lite_hour_count": len(lite_wind),
            "original_full_isd_hour_count": len(grouped),
            "union_hour_count": len(all_hours),
            "wind_variables_only": True,
            "do_not_use_isd_wnd_fallback": True,
        }, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return out_path, len(out_rows)


def run_fill(workdir):
    interp = SCRIPT_DIR / "interpolate.py"
    venv = os.environ.get("VIRTUAL_ENV", "").strip()
    py = Path(venv) / "bin" / "python" if venv else None
    py_cmd = str(py) if (py and py.exists()) else sys.executable
    # Run as package module so relative imports resolve under staged
    # project/met/surface/isd2smerge_and_fill working directory.
    repo_root = str(SCRIPT_DIR.parents[3])
    env = dict(os.environ)
    env["PYTHONPATH"] = repo_root + os.pathsep + env.get("PYTHONPATH", "")
    cmd = [py_cmd, "-m", "native_cpp.modules.p5_smerge.data_prep.interpolate"]
    return subprocess.run(cmd, cwd=workdir, env=env, check=False)


def _fmt_num(x):
    try:
        return float(x)
    except Exception:
        return None


def normalize_filled_csv(path):
    with open(path, "r", encoding="utf-8", newline="") as f:
        lines = f.readlines()
    if len(lines) < 4:
        return

    header = lines[:3]
    rows = []
    for line in lines[3:]:
        s = line.strip()
        if not s:
            continue
        rows.append(s.split(","))

    # Column order:
    # Month,Day,Year,Hour,DegC,mm,mb,%,deg,ms-1,tenths,hundreds_of_feet
    for r in rows:
        if len(r) < 12:
            continue
        v = _fmt_num(r[5])   # Precip
        if v is not None:
            r[5] = str(int(round(v)))
        v = _fmt_num(r[6])   # Pressure
        if v is not None:
            r[6] = f"{v:.1f}"
        v = _fmt_num(r[7])   # RH
        if v is not None:
            r[7] = str(int(round(v)))
        v = _fmt_num(r[8])   # Wdir10m
        if v is not None:
            r[8] = str(int(round(v)))
        v = _fmt_num(r[10])  # Ccover
        if v is not None:
            r[10] = str(int(round(v)))
        v = _fmt_num(r[11])  # hundreds_of_feet
        if v is not None:
            r[11] = str(int(round(v)))

    with open(path, "w", encoding="utf-8", newline="") as f:
        for h in header:
            f.write(h)
        for r in rows:
            f.write(",".join(r) + "\n")


def main():
    input_dir = str(INPUT_DIR)
    output_dir = str(OUTPUT_DIR)
    os.makedirs(output_dir, exist_ok=True)

    if not os.path.isdir(input_dir):
        print(f"输入目录不存在: {input_dir}")
        return 1

    # Accept files downloaded by download_isd_by_grid.py:
    # e.g. 58321099999-2023.csv
    inputs = [
        x for x in os.listdir(input_dir)
        if x.lower().endswith(".csv") and re.fullmatch(r"[0-9A-Za-z]{11}-\d{4}\.csv", x)
    ]
    if not inputs:
        print(f"未找到符合命名规则的输入文件([11位站号]-年份.csv): {input_dir}")
        return 1

    # Unselected raw CSVs can remain as rejected fallback candidates. Never
    # pass those into SMERGE, and never process leftovers from earlier cases.
    from json import loads
    selected_names = set()
    selected_roles = {}
    for mf in INPUT_DIR.glob("station_selection_*.json"):
        data = loads(mf.read_text(encoding="utf-8"))
        year = int(data["year"])
        for row in data["stations"]:
            source_name = f"{row['sid']}-{year}.csv"
            selected_names.add(source_name)
            role = row.get("wind_treatment")
            if role not in ("COMPLETE_FILL_AND_CALM_REPLACE", "RAW_SPARSE_STANDARDIZE_ONLY"):
                raise RuntimeError(f"source selection role unknown for {source_name}: {role}")
            selected_roles[source_name] = role
    if not selected_names:
        raise RuntimeError("missing P5 source-selection manifest")
    missing = selected_names - set(inputs)
    if missing:
        raise RuntimeError(f"selected station raw CSV files missing: {sorted(missing)}")
    inputs = sorted(selected_names)
    allowed_filled = {
        x[:-4].replace(x[:11], x[:6] + "-" + x[6:11], 1) + "_filled.csv"
        for x in inputs
    }
    unselected_filled = {x for x in os.listdir(output_dir) if x.endswith("_filled.csv")} - allowed_filled
    if unselected_filled:
        raise RuntimeError(f"stale unselected filled station inputs: {sorted(unselected_filled)}")

    produced = []
    for name in sorted(inputs):
        m = re.fullmatch(r"([0-9A-Za-z]{6})([0-9A-Za-z]{5})-(\d{4})\.csv", name)
        if not m:
            continue
        usaf, wban, year = m.group(1), m.group(2), m.group(3)
        final_filled = os.path.join(output_dir, f"{usaf}-{wban}-{year}_filled.csv")
        # Role-specific caches are not interchangeable: primary filled annual
        # vectors and sparse-secondary originals have different science.
        role = selected_roles[name]
        policy_file = final_filled.replace(".csv", "_wind_audit.json")
        expected_policy = ("P5_ISD_LITE_WIND_V2_WHOLE_VECTOR_HOLD_CALM_REPLACE"
                           if role == "COMPLETE_FILL_AND_CALM_REPLACE"
                           else "P5_SPARSE_STANDARDIZE_ONLY_V1")
        policy_ok = False
        if os.path.isfile(policy_file):
            try:
                with open(policy_file, encoding="utf-8") as fd:
                    policy_ok = (__import__("json").load(fd).get("policy") == expected_policy)
            except (OSError, ValueError):
                policy_ok = False
        required_files = [final_filled]
        if role == "COMPLETE_FILL_AND_CALM_REPLACE":
            required_files += [
                final_filled.replace("_filled.csv", "_cleaned.csv"),
                final_filled.replace("_filled.csv", "_calm_interpolated.csv"),
            ]
        if (policy_ok and all(os.path.isfile(x) and os.path.getsize(x) > 0
                              for x in required_files)):
            continue

        result = convert_one_isd_csv(os.path.join(input_dir, name), output_dir)
        if not result:
            continue
        out_path, _n = result
        produced.append(out_path)

    if not produced:
        existing_filled = [
            x for x in os.listdir(output_dir)
            if x.lower().endswith("_filled.csv")
        ]
        if existing_filled:
            print(f"找到 {len(inputs)} 个站点文件, 开始逐站独立处理...")
            print(f"各站点按独立角色处理完成（次站不补小时、不插值），保存路径: {output_dir}")
            return 0
        return 1

    rc = run_fill(output_dir)
    if rc.returncode != 0:
        print("插值脚本执行失败；已生成的转换文件仍然保留。")
        return rc.returncode

    for p in produced:
        filled = p.replace(".csv", "_filled.csv")
        if not os.path.exists(filled):
            print(f"[警告] 未生成插值结果,保留中间文件以便排查: {os.path.basename(p)}")
            continue
        normalize_filled_csv(filled)
        source_match = re.fullmatch(r"([0-9A-Za-z]{6})-([0-9A-Za-z]{5})-(\d{4})\.csv", os.path.basename(p))
        if not source_match:
            raise RuntimeError(f"unexpected converted station basename {p}")
        sid, year = source_match.group(1) + source_match.group(2), source_match.group(3)
        role = selected_roles[f"{sid}-{year}.csv"]
        if role == "COMPLETE_FILL_AND_CALM_REPLACE":
            for suffix in ("_cleaned.csv", "_calm_interpolated.csv"):
                stage = filled.replace("_filled.csv", suffix)
                if not os.path.isfile(stage):
                    raise RuntimeError(f"mandatory P5 primary wind processing stage absent: {stage}")
                normalize_filled_csv(stage)
        # Sparse-secondary has ONLY *_filled.csv, with original-hour gaps.
        # Remove transient raw-union GENERIC after role-specific processing.
        if os.path.exists(p):
            os.remove(p)

    print(f"找到 {len(inputs)} 个站点文件, 开始逐站独立处理...")
    print(f"数据插值完成, 覆盖全年所有时刻, 数据保存路径: {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
