import argparse
import calendar
import csv
import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from engine.core.paths import current_project_path

MISSING = {-9999, -8888}
DATA_ROOT = current_project_path("met", "upperair")
MAX_LEVELS = 200
MIN_VALID_LEVELS = 2
DEFAULT_PSTOP_HPA = 500.0
MAX_PRESSURE_HPA = 1040.0


@dataclass
class SoundingHeader:
    station_numeric: str
    dt: datetime


def _resolve_station_raw_txt(raw_txt_value: str, year_dir: Path) -> Path:
    raw_txt = Path(raw_txt_value)
    if raw_txt.exists():
        return raw_txt
    candidate = year_dir / raw_txt.name
    if candidate.exists():
        return candidate
    return raw_txt


def _safe_int(v: str) -> Optional[int]:
    try:
        return int(v)
    except Exception:
        return None


def _parse_header(line: str) -> Optional[SoundingHeader]:
    parts = line.strip().split()
    if len(parts) < 7:
        return None
    station_raw = parts[0].lstrip('#')
    station_numeric = station_raw[-5:]
    year = _safe_int(parts[1]); month = _safe_int(parts[2]); day = _safe_int(parts[3]); hour = _safe_int(parts[4]); minute = _safe_int(parts[5])
    if None in (year, month, day, hour, minute):
        return None
    if hour < 0 or hour > 23 or hour == 99:
        hour = 0
    if minute < 0 or minute > 59 or minute in (99, 9999):
        minute = 0
    try:
        dt = datetime(year, month, day, hour, minute)
    except ValueError:
        return None
    return SoundingHeader(station_numeric=station_numeric, dt=dt)


def _to_hpa(raw: int) -> Optional[float]:
    if raw in MISSING:
        return None
    if raw > 0:
        return raw / 100.0
    return None


def _to_tenth_c(raw: int) -> Optional[float]:
    return None if raw in MISSING else raw / 10.0


def _to_deg(raw: int) -> Optional[float]:
    if raw in MISSING or raw < 0 or raw > 360:
        return None
    return float(raw)


def _to_mps(raw: int) -> Optional[float]:
    return None if raw in MISSING else raw / 10.0


def _fmt(v: Optional[float]) -> str:
    return '' if v is None else f'{v:.1f}'


def _pressure_hpa(v) -> Optional[float]:
    try:
        return float(v)
    except (ValueError, TypeError):
        return None


def _interp(a: Optional[float], b: Optional[float], frac: float) -> Optional[float]:
    if a is None or b is None:
        return None
    return a + frac * (b - a)


def _ensure_target_pressure_level(levels, target_p: float):
    if not levels:
        return levels
    for lv in levels:
        p = lv.get('pressure_hPa')
        if p is not None and abs(p - target_p) < 1e-6:
            return levels

    for i in range(len(levels) - 1):
        a = levels[i]
        b = levels[i + 1]
        p1 = a.get('pressure_hPa')
        p2 = b.get('pressure_hPa')
        if p1 is None or p2 is None or p1 == p2:
            continue
        if (p1 - target_p) * (p2 - target_p) > 0:
            continue
        frac = (target_p - p1) / (p2 - p1)
        new_lv = {
            'pressure_hPa': target_p,
            'geopotential height_m': _interp(a.get('geopotential height_m'), b.get('geopotential height_m'), frac),
            'temperature_C': _interp(a.get('temperature_C'), b.get('temperature_C'), frac),
            'dew point temperature_C': _interp(a.get('dew point temperature_C'), b.get('dew point temperature_C'), frac),
            'wind direction_degree': _interp(a.get('wind direction_degree'), b.get('wind direction_degree'), frac),
            'wind speed_m/s': _interp(a.get('wind speed_m/s'), b.get('wind speed_m/s'), frac),
        }
        out = levels[:]
        out.insert(i + 1, new_lv)
        out.sort(key=lambda x: x.get('geopotential height_m') if x.get('geopotential height_m') is not None else 1e20)
        return out
    return levels


def _clean_levels_for_read62(levels, target_p_hpa):
    pressure_clamped_count = 0
    by_pressure = {}
    for lv in levels:
        p = lv.get('pressure_hPa')
        if p is None or p <= 0:
            continue
        if p > MAX_PRESSURE_HPA:
            lv = dict(lv)
            lv['pressure_hPa'] = MAX_PRESSURE_HPA
            p = MAX_PRESSURE_HPA
            pressure_clamped_count += 1
        key = round(p, 1)
        old = by_pressure.get(key)
        if old is None:
            by_pressure[key] = lv
            continue
        old_z = old.get('geopotential height_m')
        new_z = lv.get('geopotential height_m')
        if old_z is None and new_z is not None:
            by_pressure[key] = lv

    with_height = [x for x in by_pressure.values() if x.get('geopotential height_m') is not None]
    with_height.sort(key=lambda x: x['geopotential height_m'])
    cleaned = []
    last_height = None
    for lv in with_height:
        z = lv.get('geopotential height_m')
        if z is None:
            continue
        if last_height is not None and z < last_height:
            continue
        last_height = z
        cleaned.append(lv)

    cleaned = _ensure_target_pressure_level(cleaned, target_p_hpa)
    cleaned = [x for x in cleaned if (_pressure_hpa(x.get('pressure_hPa')) or 0.0) >= target_p_hpa]
    if len(cleaned) > MAX_LEVELS:
        cleaned = cleaned[:MAX_LEVELS]
    return cleaned, pressure_clamped_count


def _repair_bottom_wind_temp(cleaned):
    if not cleaned:
        return cleaned, False, False
    btm = cleaned[0]
    wd = btm.get('wind direction_degree')
    ws = btm.get('wind speed_m/s')
    tp = btm.get('temperature_C')
    repaired = False

    if wd is None or ws is None:
        src_idx = None
        for i in range(1, len(cleaned)):
            wi = cleaned[i].get('wind direction_degree')
            si = cleaned[i].get('wind speed_m/s')
            if wi is not None and si is not None:
                src_idx = i
                break
        if src_idx is None:
            return cleaned, False, True
        cleaned[0] = dict(cleaned[0])
        cleaned[0]['wind direction_degree'] = cleaned[src_idx]['wind direction_degree']
        cleaned[0]['wind speed_m/s'] = cleaned[src_idx]['wind speed_m/s']
        repaired = True

    if tp is None:
        src_t = None
        for i in range(1, len(cleaned)):
            ti = cleaned[i].get('temperature_C')
            if ti is not None:
                src_t = ti
                break
        if src_t is None:
            return cleaned, repaired, True
        cleaned[0] = dict(cleaned[0])
        cleaned[0]['temperature_C'] = src_t
        repaired = True

    cleaned.sort(key=lambda x: x['geopotential height_m'] if x.get('geopotential height_m') is not None else 1e20)
    return cleaned, repaired, False


def ensure_year_completeness(csv_dir: Path, station_numeric: str, year: int, dropped_slots=None):
    dropped_slots = set(dropped_slots or [])
    slots = {}
    for p in csv_dir.glob(f'{station_numeric}_*.csv'):
        ts = p.stem.split('_', 1)[-1]
        if len(ts) != 10 or not ts.isdigit():
            continue
        y, m, d, h = ts[0:4], ts[4:6], ts[6:8], ts[8:10]
        if y != str(year) or h not in ('00', '12'):
            continue
        day_key = f'{y}{m}{d}'
        slots.setdefault(day_key, {})[h] = p

    filled_same_day = 0
    filled_prev_day = 0
    unresolved_slots = 0
    dropped_filled_same_day = 0
    dropped_filled_prev_day = 0
    total_days = 366 if calendar.isleap(year) else 365
    start = datetime(year, 1, 1)

    for i in range(total_days):
        day = start + timedelta(days=i)
        day_key = day.strftime('%Y%m%d')
        prev_key = (day - timedelta(days=1)).strftime('%Y%m%d')
        day_slots = slots.get(day_key, {})
        p00 = day_slots.get('00')
        p12 = day_slots.get('12')

        if p00 is None and p12 is not None:
            target = csv_dir / f'{station_numeric}_{day_key}00.csv'
            target.write_text(p12.read_text(encoding='utf-8'), encoding='utf-8')
            slots.setdefault(day_key, {})['00'] = target
            filled_same_day += 1
            if f'{day_key}00' in dropped_slots:
                dropped_filled_same_day += 1
            p00 = target
        if p12 is None and p00 is not None:
            target = csv_dir / f'{station_numeric}_{day_key}12.csv'
            target.write_text(p00.read_text(encoding='utf-8'), encoding='utf-8')
            slots.setdefault(day_key, {})['12'] = target
            filled_same_day += 1
            if f'{day_key}12' in dropped_slots:
                dropped_filled_same_day += 1
            p12 = target

        if p00 is None and p12 is None:
            prev_slots = slots.get(prev_key, {})
            prev00 = prev_slots.get('00') or prev_slots.get('12')
            prev12 = prev_slots.get('12') or prev_slots.get('00')
            if prev00 is not None and prev12 is not None:
                t00 = csv_dir / f'{station_numeric}_{day_key}00.csv'
                t12 = csv_dir / f'{station_numeric}_{day_key}12.csv'
                t00.write_text(prev00.read_text(encoding='utf-8'), encoding='utf-8')
                t12.write_text(prev12.read_text(encoding='utf-8'), encoding='utf-8')
                slots[day_key] = {'00': t00, '12': t12}
                filled_prev_day += 2
                if f'{day_key}00' in dropped_slots:
                    dropped_filled_prev_day += 1
                if f'{day_key}12' in dropped_slots:
                    dropped_filled_prev_day += 1
            else:
                unresolved_slots += 2
    return {
        'filled_same_day': filled_same_day,
        'filled_prev_day': filled_prev_day,
        'unresolved_slots': unresolved_slots,
        'dropped_filled_same_day': dropped_filled_same_day,
        'dropped_filled_prev_day': dropped_filled_prev_day,
    }


def convert_igra_to_csv(igra_path: Path, out_dir: Path, station_filter: str, year: int, station_elevation_m: float, target_p_hpa: float):
    out_dir.mkdir(parents=True, exist_ok=True)
    stats = {
        'soundings_total': 0,
        'soundings_written': 0,
        'soundings_dropped_after_cleaning': 0,
        'soundings_dropped_bottom_wind_missing': 0,
        'soundings_bottom_wind_filled': 0,
        'surface_height_clamped': 0,
        'pressure_over_max_clamped': 0,
        'rows_written': 0,
        'rows_seen': 0,
        'dropped_slots': [],
    }
    current_header = None
    current_levels = []

    def flush():
        nonlocal current_header, current_levels
        if not current_header:
            return
        stats['soundings_total'] += 1
        if current_header.station_numeric != station_filter or current_header.dt.year != year:
            return
        slot_key = current_header.dt.strftime('%Y%m%d%H')
        cleaned, p_clamped = _clean_levels_for_read62(current_levels, target_p_hpa)
        stats['pressure_over_max_clamped'] += p_clamped
        if len(cleaned) < MIN_VALID_LEVELS:
            stats['soundings_dropped_after_cleaning'] += 1
            stats['dropped_slots'].append(slot_key)
            return
        cleaned, repaired, cannot_repair = _repair_bottom_wind_temp(cleaned)
        if cannot_repair:
            stats['soundings_dropped_bottom_wind_missing'] += 1
            stats['dropped_slots'].append(slot_key)
            return
        if repaired:
            stats['soundings_bottom_wind_filled'] += 1
        if cleaned[0]['geopotential height_m'] > station_elevation_m:
            cleaned[0]['geopotential height_m'] = station_elevation_m
            stats['surface_height_clamped'] += 1
        cleaned.sort(key=lambda x: x['geopotential height_m'])
        csv_name = f"{current_header.station_numeric}_{current_header.dt.strftime('%Y%m%d%H')}.csv"
        csv_path = out_dir / csv_name
        with csv_path.open('w', newline='', encoding='utf-8') as f:
            w = csv.DictWriter(
                f,
                fieldnames=['pressure_hPa', 'geopotential height_m', 'temperature_C', 'dew point temperature_C', 'wind direction_degree', 'wind speed_m/s'],
            )
            w.writeheader()
            for r in cleaned:
                w.writerow(
                    {
                        'pressure_hPa': _fmt(r.get('pressure_hPa')),
                        'geopotential height_m': _fmt(r.get('geopotential height_m')),
                        'temperature_C': _fmt(r.get('temperature_C')),
                        'dew point temperature_C': _fmt(r.get('dew point temperature_C')),
                        'wind direction_degree': _fmt(r.get('wind direction_degree')),
                        'wind speed_m/s': _fmt(r.get('wind speed_m/s')),
                    }
                )
        stats['soundings_written'] += 1
        stats['rows_written'] += len(cleaned)

    with igra_path.open('r', encoding='utf-8', errors='replace') as f:
        for line in f:
            if not line.strip():
                continue
            if line.startswith('#'):
                flush(); current_header = _parse_header(line); current_levels = []; continue
            if current_header is None:
                continue
            stats['rows_seen'] += 1
            nums = re.findall(r'[-+]?\d+', line)
            if len(nums) < 9:
                continue
            p_raw = _safe_int(nums[2]); z_raw = _safe_int(nums[3]); t_raw = _safe_int(nums[4]); dpd_raw = _safe_int(nums[6]); wd_raw = _safe_int(nums[7]); ws_raw = _safe_int(nums[8])
            p = _to_hpa(p_raw) if p_raw is not None else None
            z = None if z_raw is None or z_raw in MISSING else float(z_raw)
            t = _to_tenth_c(t_raw) if t_raw is not None else None
            dpd = _to_tenth_c(dpd_raw) if dpd_raw is not None else None
            dew = None if t is None or dpd is None else (t - dpd)
            wd = _to_deg(wd_raw) if wd_raw is not None else None
            ws = _to_mps(ws_raw) if ws_raw is not None else None
            current_levels.append(
                {
                    'pressure_hPa': p,
                    'geopotential height_m': z,
                    'temperature_C': t,
                    'dew point temperature_C': dew,
                    'wind direction_degree': wd,
                    'wind speed_m/s': ws,
                }
            )
    flush()
    return stats


def main():
    parser = argparse.ArgumentParser(description='步骤1b: 将IGRA原始文本解析为每时次CSV')
    parser.add_argument('--year', type=int, help='研究年份, 例如 2023')
    parser.add_argument('--pstop', type=float, help='PSTOP(hPa)，例如 500; 不传则读取既有文件或默认500')
    parser.add_argument('--yes', action='store_true', help='兼容参数，保留但不再触发交互')
    args = parser.parse_args()

    year = args.year
    if year is None:
        raise SystemExit('year is required; pass --year YYYY')

    year_dir = DATA_ROOT / str(year)
    year_dir.mkdir(parents=True, exist_ok=True)
    pstop_file = year_dir / 'pstop_hpa.txt'
    if args.pstop is not None:
        target_p_hpa = float(args.pstop)
    else:
        if pstop_file.exists():
            try:
                target_p_hpa = float(pstop_file.read_text(encoding='utf-8').strip())
            except ValueError:
                target_p_hpa = DEFAULT_PSTOP_HPA
        else:
            target_p_hpa = DEFAULT_PSTOP_HPA
    pstop_file.write_text(f'{target_p_hpa:.1f}\n', encoding='utf-8')
    print(f'已保存PSTOP: {target_p_hpa:.1f} hPa -> {pstop_file}')

    download_file = year_dir / 'upperair_station_used_list.txt'
    if not download_file.exists():
        print(f'未找到下载清单: {download_file}')
        print('请先执行 download_igra.py')
        return 1

    total_ok = 0
    total_fail = 0
    with download_file.open('r', encoding='utf-8', newline='') as rf:
        reader = csv.DictReader(rf)

        for row in reader:
            stn_id = row['id']
            raw_txt = _resolve_station_raw_txt(row['raw_txt'], year_dir)
            station_numeric = stn_id[-5:]
            source_tag = raw_txt.name.replace('-data.txt', '')
            out_dir = year_dir / f'{source_tag}_igra_every_moment'
            for old in out_dir.glob(f'{station_numeric}_*.csv'):
                old.unlink()

            elev = float(row['elev_m'])
            stats = convert_igra_to_csv(
                raw_txt,
                out_dir,
                station_filter=station_numeric,
                year=year,
                station_elevation_m=elev,
                target_p_hpa=target_p_hpa,
            )
            fill_stats = ensure_year_completeness(out_dir, station_numeric, year, dropped_slots=stats.get('dropped_slots'))
            print(f"[完成解析] 站点: {stn_id}")
            _ = (stats, fill_stats)
            print(f"  输出路径: {out_dir}")
            if stats['soundings_written'] > 0:
                total_ok += 1
                print(f"[{stn_id}] 清洗成功")
            else:
                total_fail += 1
                print(f"[{stn_id}] 清洗失败")

    _ = (total_ok, total_fail)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
