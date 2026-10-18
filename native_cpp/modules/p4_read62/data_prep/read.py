import argparse
import csv
from pathlib import Path

from engine.core.paths import current_project_path

DATA_ROOT = current_project_path("met", "upperair")
MAX_LEVELS = 200
MIN_VALID_LEVELS = 2
DEFAULT_PSTOP_HPA = 500.0
MAX_PRESSURE_HPA = 1040.0


def _resolve_station_raw_txt(raw_txt_value: str, year_dir: Path) -> Path:
    raw_txt = Path(raw_txt_value)
    if raw_txt.exists():
        return raw_txt
    candidate = year_dir / raw_txt.name
    if candidate.exists():
        return candidate
    return raw_txt


def get_first_value(row, keys):
    for key in keys:
        value = row.get(key)
        if value is not None:
            value = str(value).strip()
            if value != '':
                return value
    return ''


def parse_csv_datetime(csv_path: Path, station_id: str):
    stem = csv_path.stem
    prefix = f'{station_id}_'
    if not stem.startswith(prefix):
        return None
    ts = stem[len(prefix):]
    if len(ts) != 10 or not ts.isdigit():
        return None
    return ts[0:4], ts[4:6], ts[6:8], ts[8:10]


def fsl_temp_string(value_text):
    if not value_text:
        return '  32767'
    try:
        v = round(float(value_text), 1)
        s = f'{v:.1f}'.replace('.', '')
        return s.rjust(7)
    except (ValueError, TypeError):
        return '  32767'


def fsl_int_string(value_text):
    if not value_text:
        return '  32767'
    try:
        v = round(float(value_text))
        return f'{v:7d}'
    except (ValueError, TypeError):
        return '  32767'


def _parse_float(value_text):
    try:
        return float(value_text)
    except (ValueError, TypeError):
        return None


def _interp(a, b, frac):
    if a is None or b is None:
        return None
    return a + frac * (b - a)


def _interp_wind_direction(a, b, frac):
    """Shortest circular arc. Exact 180-degree tie is clockwise, as in P5."""
    if a is None or b is None:
        return None
    delta = (float(b) - float(a)) % 360.0
    if delta > 180.0:
        delta -= 360.0
    return (float(a) + frac * delta) % 360.0


def _ensure_target_pressure_level(cleaned, target_p):
    if not cleaned:
        return cleaned
    for lv in cleaned:
        if abs(lv['_pressure_num'] - target_p) < 1e-6:
            return cleaned

    for i in range(len(cleaned) - 1):
        a = cleaned[i]
        b = cleaned[i + 1]
        p1 = a['_pressure_num']
        p2 = b['_pressure_num']
        if p1 == p2:
            continue
        if (p1 - target_p) * (p2 - target_p) > 0:
            continue
        frac = (target_p - p1) / (p2 - p1)
        z = _interp(a['_height_num'], b['_height_num'], frac)
        if z is None:
            continue
        t = _interp(_parse_float(a.get('temp')), _parse_float(b.get('temp')), frac)
        d = _interp(_parse_float(a.get('dew')), _parse_float(b.get('dew')), frac)
        wd = _interp_wind_direction(_parse_float(a.get('wdir')), _parse_float(b.get('wdir')), frac)
        ws = _interp(_parse_float(a.get('wspd')), _parse_float(b.get('wspd')), frac)
        new_layer = {
            'pressure': f'{target_p:.1f}',
            'height': f'{z:.1f}',
            'temp': '' if t is None else f'{t:.1f}',
            'dew': '' if d is None else f'{d:.1f}',
            'wdir': '' if wd is None else f'{wd:.1f}',
            'wspd': '' if ws is None else f'{ws:.1f}',
            '_pressure_num': target_p,
            '_height_num': z,
        }
        out = cleaned[:]
        out.insert(i + 1, new_layer)
        out.sort(key=lambda x: x['_height_num'])
        return out
    return cleaned


def _hard_validate_layers(layers, station_elevation_m, min_pressure_hpa):
    cleaned = []
    pressure_clamped_count = 0
    for layer in layers:
        p = _parse_float(layer.get('pressure'))
        if p is None or p <= 0:
            continue
        if p > MAX_PRESSURE_HPA:
            p = MAX_PRESSURE_HPA
            layer = dict(layer)
            layer['pressure'] = f'{MAX_PRESSURE_HPA:.1f}'
            pressure_clamped_count += 1
        z = _parse_float(layer.get('height'))
        if z is None:
            continue
        wdir = _parse_float(layer.get('wdir'))
        wspd = _parse_float(layer.get('wspd'))
        if wdir is not None and (wdir < 0 or wdir > 360):
            layer = dict(layer)
            layer['wdir'] = ''
        if wspd is not None and wspd < 0:
            layer = dict(layer)
            layer['wspd'] = ''
        layer = dict(layer)
        layer['_pressure_num'] = p
        layer['_height_num'] = z
        cleaned.append(layer)

    cleaned.sort(key=lambda x: x['_height_num'])
    cleaned = _ensure_target_pressure_level(cleaned, min_pressure_hpa)
    cleaned = [x for x in cleaned if x['_pressure_num'] >= min_pressure_hpa]
    if len(cleaned) > MAX_LEVELS:
        cleaned = cleaned[:MAX_LEVELS]
    if len(cleaned) < MIN_VALID_LEVELS:
        return [], 0, 0, 1, pressure_clamped_count

    bottom_wind_filled = 0
    wd0 = _parse_float(cleaned[0].get('wdir'))
    ws0 = _parse_float(cleaned[0].get('wspd'))
    t0 = _parse_float(cleaned[0].get('temp'))
    if wd0 is None or ws0 is None:
        src_idx = None
        for i in range(1, len(cleaned)):
            wi = _parse_float(cleaned[i].get('wdir'))
            si = _parse_float(cleaned[i].get('wspd'))
            if wi is not None and si is not None:
                src_idx = i
                break
        if src_idx is None:
            return [], 0, 0, 1, pressure_clamped_count
        cleaned[0] = dict(cleaned[0])
        cleaned[0]['wdir'] = cleaned[src_idx]['wdir']
        cleaned[0]['wspd'] = cleaned[src_idx]['wspd']
        bottom_wind_filled = 1

    if t0 is None:
        src_t = None
        for i in range(1, len(cleaned)):
            ti = _parse_float(cleaned[i].get('temp'))
            if ti is not None:
                src_t = cleaned[i].get('temp')
                break
        if src_t is None:
            return [], 0, bottom_wind_filled, 1, pressure_clamped_count
        cleaned[0] = dict(cleaned[0])
        cleaned[0]['temp'] = src_t

    clamped = 0
    if cleaned[0]['_height_num'] > station_elevation_m:
        cleaned[0]['_height_num'] = station_elevation_m
        cleaned[0]['height'] = str(int(round(station_elevation_m)))
        clamped = 1
    cleaned.sort(key=lambda x: x['_height_num'])
    return cleaned, clamped, bottom_wind_filled, 0, pressure_clamped_count


def convert_csv_profiles_to_fsl(csv_dir: Path, output_path: Path, station_id: str, latitude: str, longitude: str, elevation: str, target_year: str, min_pressure_hpa: float, exact_lat: float | None = None, exact_lon: float | None = None, coord_digits: int = 6):
    month_cap = {
        '01': 'JAN', '02': 'FEB', '03': 'MAR', '04': 'APR',
        '05': 'MAY', '06': 'JUN', '07': 'JUL', '08': 'AUG',
        '09': 'SEP', '10': 'OCT', '11': 'NOV', '12': 'DEC',
    }

    csv_files = sorted(csv_dir.glob(f'{station_id}_*.csv'))
    processed = 0
    skipped = 0
    dropped_by_hard_check = 0
    surface_height_clamped = 0
    bottom_wind_filled = 0
    dropped_by_bottom_wind_missing = 0
    pressure_over_max_clamped = 0
    try:
        station_elevation_m = float(elevation)
    except (ValueError, TypeError):
        station_elevation_m = 0.0

    with output_path.open('w', encoding='utf-8') as fout:
        for csv_path in csv_files:
            dt = parse_csv_datetime(csv_path, station_id)
            if dt is None:
                skipped += 1
                continue
            year, month, day, hour = dt
            if year != target_year:
                skipped += 1
                continue

            layers = []
            with csv_path.open('r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    pressure_raw = get_first_value(row, ['pressure_hPa', 'pressure'])
                    layers.append(
                        {
                            'pressure': pressure_raw,
                            'height': get_first_value(row, ['geopotential height_m', 'height']),
                            'temp': get_first_value(row, ['temperature_C', 'temperature']),
                            'dew': get_first_value(row, ['dew point temperature_C', 'dewpoint']),
                            'wdir': get_first_value(row, ['wind direction_degree', 'direction']),
                            'wspd': get_first_value(row, ['wind speed_m/s', 'speed']),
                        }
                    )

            layers, clamped, filled, dropped_bottom, p_clamped = _hard_validate_layers(layers, station_elevation_m, min_pressure_hpa)
            surface_height_clamped += clamped
            bottom_wind_filled += filled
            dropped_by_bottom_wind_missing += dropped_bottom
            pressure_over_max_clamped += p_clamped
            if not layers:
                dropped_by_hard_check += 1
                skipped += 1
                continue

            total_layers = len(layers) + 4
            day_num = f'{int(day):2d}'
            hour_out = '0' if hour == '00' else hour

            head1 = f"    254{hour_out.rjust(7)}{day_num.rjust(7)}{month_cap[month].rjust(9)}{year.rjust(8)}"
            head2 = f"      1  99999{station_id.rjust(7)}{latitude.rjust(8)}{longitude.rjust(7)}{elevation.rjust(6)}  32767"
            # Legacy READ62.FOR reads only the fixed F7.2/F6.2 coordinate
            # fields. A trailing optional extension keeps 3-6 decimal digits
            # accessible to C++20 without shifting even one legacy column.
            if exact_lat is not None and exact_lon is not None:
                if not 3 <= coord_digits <= 6:
                    raise ValueError("FSL P4EXACT precision must be in [3,6]")
                head2 += (f" P4EXACT_LAT={exact_lat:.{coord_digits}f}"
                          f" P4EXACT_LON={exact_lon:.{coord_digits}f}")
            head3 = f"      2    100    100    194{total_layers:7d}  32767      3"
            head4 = '      3          9999                32767     ms'

            fout.write(head1 + '\n')
            fout.write(head2 + '\n')
            fout.write(head3 + '\n')
            fout.write(head4 + '\n')

            for i, layer in enumerate(layers):
                rec_type = '      9' if i == 0 else '      5'
                line = (
                    rec_type
                    + fsl_int_string(layer['pressure'])
                    + fsl_int_string(layer['height'])
                    + fsl_temp_string(layer['temp'])
                    + fsl_temp_string(layer['dew'])
                    + fsl_int_string(layer['wdir'])
                )
                try:
                    sped = float(layer['wspd'])
                    line += f'{round(sped * 10):7d}'
                except (ValueError, TypeError):
                    line += '  32767'
                fout.write(line + '\n')

            processed += 1

    return {
        'processed_profiles': processed,
        'skipped_profiles': skipped,
        'dropped_by_hard_check': dropped_by_hard_check,
        'surface_height_clamped': surface_height_clamped,
        'bottom_wind_filled': bottom_wind_filled,
        'dropped_by_bottom_wind_missing': dropped_by_bottom_wind_missing,
        'pressure_over_max_clamped': pressure_over_max_clamped,
        'total_csv': len(csv_files),
    }


def main():
    parser = argparse.ArgumentParser(description='步骤2: 将预处理CSV批量转换为FSL文本')
    parser.add_argument('--year', type=int, help='研究年份，例如 2023')
    parser.add_argument('--upperair-root', type=Path, help='Explicit isolated P4 output root')
    args = parser.parse_args()
    year = args.year
    if year is None:
        raise SystemExit('year is required; pass --year YYYY')

    year_dir = (args.upperair_root if args.upperair_root else DATA_ROOT) / str(year)
    year_dir.mkdir(parents=True, exist_ok=True)
    out_dir = year_dir / 'igra2fsl'
    out_dir.mkdir(parents=True, exist_ok=True)
    pstop_file = year_dir / 'pstop_hpa.txt'
    if pstop_file.exists():
        try:
            min_pressure_hpa = float(pstop_file.read_text(encoding='utf-8').strip())
        except ValueError:
            min_pressure_hpa = DEFAULT_PSTOP_HPA
    else:
        min_pressure_hpa = DEFAULT_PSTOP_HPA
    station_file = year_dir / 'upperair_station_used_list.txt'
    if not station_file.exists():
        print(f'未找到下载站点清单: {station_file}')
        print('请先执行 download_igra.py')
        return 1

    summary = []
    with station_file.open('r', encoding='utf-8', newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            stn_id = row['id']
            station_numeric = stn_id[-5:]
            lat = float(row['lat'])
            lon = float(row['lon'])
            elev = int(round(float(row['elev_m'])))
            raw_txt = _resolve_station_raw_txt(row['raw_txt'], year_dir)
            source_tag = raw_txt.name.replace('-data.txt', '')
            csv_dir = year_dir / f'{source_tag}_igra_every_moment'
            output_path = out_dir / f'{station_numeric}.txt'

            stats = convert_csv_profiles_to_fsl(
                csv_dir=csv_dir,
                output_path=output_path,
                station_id=station_numeric,
                latitude=f"{abs(lat):.2f}{'N' if lat >= 0 else 'S'}",
                longitude=f"{abs(lon):.2f}{'E' if lon >= 0 else 'W'}",
                elevation=str(elev),
                target_year=str(year),
                min_pressure_hpa=min_pressure_hpa,
                exact_lat=lat, exact_lon=lon, coord_digits=6,
            )
            summary.append((stn_id, output_path, stats))

    for stn_id, out, stats in summary:
        _ = (out, stats)
        print(f'站点: {stn_id} 转换完成 ')
    print(f'输出路径: {out_dir}/')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
