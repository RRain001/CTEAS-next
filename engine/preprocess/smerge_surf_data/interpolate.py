import json
import os
import re
import numpy as np
import pandas as pd


def read_station_csv(file_path):
    """读取3行头的站点CSV"""
    with open(file_path, "r", encoding="utf-8") as f:
        header_lines = [f.readline().rstrip("\n") for _ in range(3)]

    columns = [x.strip() for x in header_lines[2].split(",")]
    df = pd.read_csv(file_path, skiprows=3, header=None, names=columns)
    return header_lines, columns, df


def build_hourly_index(df):
    """构造时间索引并补齐全年逐小时"""
    hour_val = (df["Hour"].astype(float) / 100).astype(int)
    dt = pd.to_datetime(
        {
            "year": df["Year"].astype(int),
            "month": df["Month"].astype(int),
            "day": df["Day"].astype(int),
            "hour": hour_val,
        }
    )

    out = df.copy()
    out["Datetime"] = dt
    out = out.set_index("Datetime").sort_index()

    year = int(out["Year"].mode().iloc[0])
    full_index = pd.date_range(f"{year}-01-01 00:00:00", f"{year}-12-31 23:00:00", freq="h")
    out = out.reindex(full_index)
    return out


def _missing_runs(mask):
    """返回缺失段列表[(start, end), ...], end为闭区间"""
    runs = []
    n = len(mask)
    i = 0
    while i < n:
        if not mask[i]:
            i += 1
            continue
        start = i
        while i + 1 < n and mask[i + 1]:
            i += 1
        runs.append((start, i))
        i += 1
    return runs


def fill_continuous_by_gap_rule(series):
    """
    连续变量补值规则：
    <=2小时: 线性插值
    3-6小时: 时间插值
    >6小时: 年平均值
    """
    s = pd.to_numeric(series, errors="coerce").copy()
    # 统一缺测码
    s = s.replace(9999, np.nan)

    linear_interp = s.interpolate(method="linear", limit_area="inside")
    time_interp = s.interpolate(method="time", limit_area="inside")
    annual_mean = s.mean(skipna=True)

    filled = s.copy()
    miss_mask = filled.isna().to_numpy()
    runs = _missing_runs(miss_mask)

    for st, ed in runs:
        gap_len = ed - st + 1
        idx_slice = filled.index[st : ed + 1]
        if gap_len <= 2:
            filled.loc[idx_slice] = linear_interp.loc[idx_slice]
        elif gap_len <= 6:
            filled.loc[idx_slice] = time_interp.loc[idx_slice]
        else:
            filled.loc[idx_slice] = annual_mean

    # 边界等仍未补上的，统一用年平均兜底
    if not np.isnan(annual_mean):
        filled = filled.fillna(annual_mean)

    return filled


CALM_LIMIT_M_S = 0.5


class WindPreparationError(ValueError):
    """Atmos 同型错误:稳定错误码 + 时段范围,不做静默替换。"""

    def __init__(self, code, ranges):
        super().__init__(code)
        self.code = code
        self.ranges = ranges

    @property
    def station_less_ranges(self):
        return [
            {key: value for key, value in item.items() if key != "station_id"}
            for item in self.ranges
        ]


def fill_wind_forward_calm(df, dir_col, spd_col, strict=False):
    """Atmos ISD_FORWARD_FILL_CALM_ARC_V1:逐字段前向保持 + 静风最短弧。

    与旧实现(u/v 时间插值 + 全年均值兜底)的差异:
    - 逐字段只沿用上一个可用原始值(整点缺报也沿用),每个填充值记录来源时刻;
    - 静风按填充后速度 < 0.5 m/s 判定,报文类型码不参与;
    - 静风段风向 = 两端非静风填充风向的最短弧,m/(L+1) 分配,精确 180° 顺时针;
    - 主表速度取计算口径:静风小时写 0.5 m/s(SMERGE/CALMET 输入),非静风写实际
      填充速度;审计文件保留 0.0 的 filled/statistics 值;
    - 前置缺失 / 贴区间边界静风段:strict=True 抛 WindPreparationError(Atmos 语义),
      否则保留前向保持值并在审计中标出。
    """
    index = df.index
    direction = pd.to_numeric(df[dir_col], errors="coerce").replace(9999, np.nan)
    speed = pd.to_numeric(df[spd_col], errors="coerce").replace(9999, np.nan)

    dir_src = pd.Series(pd.NaT, index=index).astype("datetime64[ns]")
    dir_src[direction.notna()] = index[direction.notna()]
    spd_src = pd.Series(pd.NaT, index=index).astype("datetime64[ns]")
    spd_src[speed.notna()] = index[speed.notna()]

    direction_filled = direction.ffill()
    speed_filled = speed.ffill()
    dir_src = dir_src.ffill()
    spd_src = spd_src.ffill()

    leading = []
    for field, filled in (("wind_direction", direction_filled), ("wind_speed", speed_filled)):
        count = int(filled.isna().sum())
        if not count:
            continue
        if not bool(filled.iloc[:count].isna().all()):
            raise ValueError("前向保持后仍存在区间内部缺失")
        leading.append({
            "field": field,
            "start_utc": index[0],
            "end_utc_inclusive": index[count - 1],
            "hours": count,
        })

    calm_mask = (speed_filled < CALM_LIMIT_M_S).fillna(False).to_numpy()
    runs = _missing_runs(calm_mask)
    statistic_direction = direction_filled.copy()
    method = pd.Series("FILLED_NONCALM_FIELD", index=index, dtype="object")
    segment = pd.Series(pd.NA, index=index, dtype="Int64")
    unbracketed = []
    for identifier, (left, right) in enumerate(runs, start=1):
        hours = right - left + 1
        if left == 0 or right == len(calm_mask) - 1:
            method.iloc[left:right + 1] = "CALM_UNBRACKETED_KEEP_FILLED_DIRECTION"
            segment.iloc[left:right + 1] = identifier
            unbracketed.append({
                "start_utc": index[left],
                "end_utc_inclusive": index[right],
                "hours": hours,
                "missing_before_noncalm": left == 0,
                "missing_after_noncalm": right == len(calm_mask) - 1,
            })
            continue
        theta0 = float(direction_filled.iloc[left - 1]) % 360.0
        theta1 = float(direction_filled.iloc[right + 1]) % 360.0
        difference = (theta1 - theta0) % 360.0
        delta = difference - 360.0 if difference > 180.0 else difference
        for position, hour in enumerate(range(left, right + 1), start=1):
            statistic_direction.iloc[hour] = (theta0 + position / (hours + 1) * delta) % 360.0
            method.iloc[hour] = "ALL_CALM_SHORTEST_ARC_CLOCKWISE_EXACT_180"
            segment.iloc[hour] = identifier

    # 计算口径速度:静风小时统一 0.5 m/s(供 SMERGE/CALMET),其余为实际填充速度。
    speed_calculation = speed_filled.mask(pd.Series(calm_mask, index=index), CALM_LIMIT_M_S)

    if strict and (leading or unbracketed):
        if leading:
            raise WindPreparationError("LEADING_MISSING_NO_PREDECESSOR", leading)
        raise WindPreparationError("CALM_SEGMENT_MISSING_NONCALM_ENDPOINT", unbracketed)

    audit = pd.DataFrame({
        "wind_direction_raw_deg": direction,
        "wind_speed_raw_m_s": speed,
        "wind_direction_filled_deg": direction_filled,
        "wind_direction_was_filled": direction.isna() & direction_filled.notna(),
        "wind_direction_fill_source_utc": dir_src,
        "wind_speed_filled_m_s": speed_filled,
        "wind_speed_was_filled": speed.isna() & speed_filled.notna(),
        "wind_speed_fill_source_utc": spd_src,
        "is_calm": pd.Series(calm_mask, index=index),
        "wind_direction_statistics_deg": statistic_direction,
        "wind_speed_statistics_m_s": speed_filled,
        "wind_speed_calculation_m_s": speed_calculation,
        "direction_statistics_method": method,
        "calm_segment_id": segment,
    }, index=index)
    summary = {
        "calm_limit_m_s": CALM_LIMIT_M_S,
        "hour_count": int(len(index)),
        "calm_hours": int(calm_mask.sum()),
        "direction_forward_filled_hours": int((direction.isna() & direction_filled.notna()).sum()),
        "speed_forward_filled_hours": int((speed.isna() & speed_filled.notna()).sum()),
        "calm_segments": len(runs),
        "leading_missing": leading,
        "boundary_calm_segments": unbracketed,
        "statistics_speed_field": "wind_speed_filled_m_s",
        "calculation_speed_field": "wind_speed_calculation_m_s",
        "main_table_speed_field": "wind_speed_calculation_m_s (静风写 0.5 m/s 供 SMERGE/CALMET)",
    }

    # 主表:方向取统计口径(静风段最短弧);速度取计算口径——静风小时统一写 0.5 m/s,
    # 非静风小时写实际填充速度;缺失仍写 9999 哨兵。审计文件保留 filled/statistics 值。
    out = df.copy()
    out[spd_col] = speed_calculation.round(3).fillna(9999)
    out[dir_col] = statistic_direction.round(0).fillna(9999).astype(int)
    return out, audit, summary


def write_wind_audit(file_path, audit, summary):
    """在主表旁写审计文件:逐时填充来源/静风/统计风向 + 网关汇总。"""
    base, ext = os.path.splitext(file_path)
    audit_path = f"{base}_wind_audit{ext}"
    out = audit.copy()
    for column in ("wind_direction_fill_source_utc", "wind_speed_fill_source_utc"):
        out[column] = out[column].dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    out.insert(0, "at_utc", out.index.strftime("%Y-%m-%dT%H:%M:%SZ"))
    out.to_csv(audit_path, index=False)

    payload = dict(summary)
    payload["station_file"] = os.path.basename(file_path)
    for key in ("leading_missing", "boundary_calm_segments"):
        payload[key] = [
            {
                name: (value.strftime("%Y-%m-%dT%H:%M:%SZ") if hasattr(value, "strftime") else value)
                for name, value in item.items()
            }
            for item in payload[key]
        ]
    summary_path = f"{base}_wind_audit.json"
    with open(summary_path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
    return audit_path, summary_path


def process_one_station(file_path, strict=False):
    header_lines, columns, df_raw = read_station_csv(file_path)
    df = build_hourly_index(df_raw)

    # 重建基础时间列
    df["Year"] = df.index.year
    df["Month"] = df.index.month
    df["Day"] = df.index.day
    df["Hour"] = df.index.hour * 100

    # 列映射（兼容你当前文件和可能的别名）
    precip_col = "mm" if "mm" in df.columns else ("Precip" if "Precip" in df.columns else None)
    pressure_col = "mb" if "mb" in df.columns else ("Pressure" if "Pressure" in df.columns else None)
    ccover_col = "tenths" if "tenths" in df.columns else ("Ccover" if "Ccover" in df.columns else None)
    cheight_col = "hundreds_of_feet" if "hundreds_of_feet" in df.columns else ("Cheight" if "Cheight" in df.columns else None)
    temp_col = "DegC" if "DegC" in df.columns else ("Temp" if "Temp" in df.columns else None)
    rh_col = "%" if "%" in df.columns else ("RH" if "RH" in df.columns else None)
    wdir_col = "deg" if "deg" in df.columns else ("Wdir10m" if "Wdir10m" in df.columns else None)
    wspd_col = "ms-1" if "ms-1" in df.columns else ("Wspeed10m" if "Wspeed10m" in df.columns else None)

    # 连续变量补值规则
    for col in [temp_col, rh_col, pressure_col]:
        if col and col in df.columns:
            df[col] = fill_continuous_by_gap_rule(df[col])

    # 风场：逐字段前向保持 + 静风最短弧（Atmos ISD_FORWARD_FILL_CALM_ARC_V1）
    audit = summary = None
    if wdir_col and wspd_col and wdir_col in df.columns and wspd_col in df.columns:
        df, audit, summary = fill_wind_forward_calm(df, wdir_col, wspd_col, strict=strict)

    # 指定列缺失值固定填充
    if precip_col and precip_col in df.columns:
        df[precip_col] = pd.to_numeric(df[precip_col], errors="coerce").replace(-9999, np.nan).fillna(9999)
    if pressure_col and pressure_col in df.columns:
        df[pressure_col] = pd.to_numeric(df[pressure_col], errors="coerce").replace(-9999, np.nan).fillna(9999)
    if ccover_col and ccover_col in df.columns:
        df[ccover_col] = pd.to_numeric(df[ccover_col], errors="coerce").replace(-9999, np.nan).fillna(9999)
    if cheight_col and cheight_col in df.columns:
        df[cheight_col] = (
            pd.to_numeric(df[cheight_col], errors="coerce")
            .replace(-9999, np.nan)
            .fillna(722)
            .astype(int)
        )

    # 按原始第三行列顺序输出
    out_cols = [c for c in columns if c in df.columns]
    df_out = df[out_cols].copy()

    # 整数列格式化
    for int_col in ["Year", "Month", "Day", "Hour"]:
        if int_col in df_out.columns:
            df_out[int_col] = df_out[int_col].astype(int)

    return header_lines, df_out, audit, summary


def save_station_csv(file_path, header_lines, df_out):
    base, ext = os.path.splitext(file_path)
    output_path = f"{base}_filled{ext}"
    with open(output_path, "w", encoding="utf-8", newline="") as f:
        for line in header_lines:
            f.write(line + "\n")
        df_out.to_csv(f, index=False, header=False)
    return output_path


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="ISD 风场逐字段前向保持 + 静风最短弧补值")
    parser.add_argument("--strict", action="store_true",
                        help="前置缺失/贴边界静风段按 Atmos 语义报错退出(默认保留并在审计中标出)")
    args = parser.parse_args()

    workdir = "."
    pattern = re.compile(r"^[0-9A-Za-z]{6}-[0-9A-Za-z]{5}-\d{4}\.csv$")
    candidates = []
    for x in os.listdir(workdir):
        _, ext = os.path.splitext(x)
        # 仅识别CSV后缀文件
        if ext.lower() == ".csv" and pattern.match(x):
            candidates.append(x)

    if not candidates:
        print("未找到符合命名规则的站点CSV(如 583380-99999-2023.csv)")
        raise SystemExit(1)

    candidates = sorted(candidates)

    for input_file in candidates:
        try:
            headers, df_result, audit, summary = process_one_station(input_file, strict=args.strict)
        except WindPreparationError as error:
            print(f"[{input_file}] {error.code}: 前置缺失/贴边界静风段,未生成派生结果")
            for item in error.station_less_ranges:
                print(f"    {item}")
            raise SystemExit(1)
        _out = save_station_csv(input_file, headers, df_result)
        if audit is not None:
            audit_path, summary_path = write_wind_audit(_out, audit, summary)
            print(f"[{input_file}] 审计: {os.path.basename(audit_path)} / {os.path.basename(summary_path)}")
