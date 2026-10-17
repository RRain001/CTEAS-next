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

from engine.core.paths import current_project_path, engine_path

MISSING_NUM = 9999
SCRIPT_DIR = engine_path("preprocess", "smerge_surf_data")
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
    with open(path, "r", encoding="utf-8", newline="") as f:
        r = csv.DictReader(f)
        for row in r:
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

    if not grouped:
        return None

    out_rows = []
    for t in sorted(grouped):
        best = max(grouped[t], key=lambda rr: score_row(rr, t))
        temp = parse_tmp_c(best.get("TMP", ""))
        dew = parse_tmp_c(best.get("DEW", ""))
        slp = parse_slp_mb(best.get("SLP", ""))
        wdir, wspd = parse_wind(best.get("WND", ""))
        precip = parse_precip_mm_1h(best)
        ccover = parse_cloud_tenths_from_gf1(best.get("GF1", ""))
        cheight = parse_cheight_hundreds_ft_from_cig(best.get("CIG", ""))
        rh = calc_rh(temp, dew)

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
    out_name = f"{usaf}-{wban}-{year}.csv"
    os.makedirs(output_dir, exist_ok=True)
    out_path = os.path.join(output_dir, out_name)

    with open(out_path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["GENERIC", "Version", "'2.0'", "Manuallygenerated", "Timeasendinghour", ""])
        w.writerow(["Station", "ID", "='", usaf, "Temp", "Precip", "Pressure", "RH", "Wdir10m", "Wspeed10m", "Ccover", "Cheight"])
        w.writerow(["Month", "Day", "Year", "Hour", "DegC", "mm", "mb", "%", "deg", "ms-1", "tenths", "hundreds_of_feet"])
        for r in out_rows:
            w.writerow(r)

    return out_path, len(out_rows)


def run_fill(workdir):
    interp = SCRIPT_DIR / "interpolate.py"
    venv = os.environ.get("VIRTUAL_ENV", "").strip()
    py = Path(venv) / "bin" / "python" if venv else None
    py_cmd = str(py) if (py and py.exists()) else sys.executable
    cmd = [py_cmd, str(interp)]
    return subprocess.run(cmd, cwd=workdir, check=False)


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

    produced = []
    for name in sorted(inputs):
        m = re.fullmatch(r"([0-9A-Za-z]{6})([0-9A-Za-z]{5})-(\d{4})\.csv", name)
        if not m:
            continue
        usaf, wban, year = m.group(1), m.group(2), m.group(3)
        final_filled = os.path.join(output_dir, f"{usaf}-{wban}-{year}_filled.csv")
        if os.path.exists(final_filled) and os.path.getsize(final_filled) > 0:
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
            print(f"数据插值完成, 覆盖全年所有时刻, 数据保存路径: {output_dir}")
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
        # Remove intermediate generic CSV; keep only *_filled.csv output.
        if os.path.exists(p):
            os.remove(p)

    print(f"找到 {len(inputs)} 个站点文件, 开始逐站独立处理...")
    print(f"数据插值完成, 覆盖全年所有时刻, 数据保存路径: {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
