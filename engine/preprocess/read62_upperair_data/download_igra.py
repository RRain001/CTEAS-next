import argparse
import csv
import math
import re
import urllib.request
import zipfile
from pathlib import Path

from engine.core.paths import current_project_path, engine_path

DATA_ROOT = current_project_path("met", "upperair")


def parse_center(center_path: Path):
    text = center_path.read_text(encoding='utf-8', errors='ignore')
    lon_m = re.search(r'longitude\s*:\s*([-+]?\d+(?:\.\d+)?)', text)
    lat_m = re.search(r'latitude\s*:\s*([-+]?\d+(?:\.\d+)?)', text)
    if not lon_m or not lat_m:
        raise ValueError('center_location 格式无法解析 longitude/latitude')
    return float(lat_m.group(1)), float(lon_m.group(1))


def parse_grid(grid_path: Path):
    text = grid_path.read_text(encoding='utf-8', errors='ignore')

    def pick(name):
        m = re.search(rf'!\s*{name}\s*=\s*([-+]?\d+(?:\.\d+)?)', text)
        if not m:
            raise ValueError(f'grid.cmn 缺少 {name}')
        return float(m.group(1))

    return pick('DGRIDKM'), int(pick('NX')), int(pick('NY'))


def haversine_km(lat1, lon1, lat2, lon2):
    r = 6371.0
    p1 = math.radians(lat1)
    p2 = math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def signed_offsets_km(lat0, lon0, lat, lon):
    km_per_deg_lat = 111.32
    km_per_deg_lon = 111.32 * math.cos(math.radians(lat0))
    return (lon - lon0) * km_per_deg_lon, (lat - lat0) * km_per_deg_lat


def load_station_list(station_list_path: Path):
    stations = []
    with station_list_path.open('r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            if not line.strip():
                continue
            try:
                stn_id = line[0:11].strip()
                lat = float(line[12:20].strip())
                lon = float(line[21:30].strip())
                elev = float(line[31:37].strip())
                name = line[41:71].strip()
                fst = int(line[72:76].strip())
                lst = int(line[77:81].strip())
            except ValueError:
                continue
            stations.append({'id': stn_id, 'name': name, 'lat': lat, 'lon': lon, 'elev_m': elev, 'first_year': fst, 'last_year': lst})
    return stations


def choose_station(stations, center_lat, center_lon, dgrid_km, nx, ny):
    half_x = dgrid_km * nx / 2.0
    half_y = dgrid_km * ny / 2.0
    inside = []
    for s in stations:
        dx, dy = signed_offsets_km(center_lat, center_lon, s['lat'], s['lon'])
        dist = haversine_km(center_lat, center_lon, s['lat'], s['lon'])
        row = dict(s)
        row['dist_km'] = dist
        if abs(dx) <= half_x and abs(dy) <= half_y:
            inside.append(row)
    if inside:
        inside.sort(key=lambda x: x['dist_km'])
        return True, inside
    rows = []
    for s in stations:
        x = dict(s)
        x['dist_km'] = haversine_km(center_lat, center_lon, s['lat'], s['lon'])
        rows.append(x)
    rows.sort(key=lambda x: x['dist_km'])
    return False, rows[:3]


def filter_by_year(stations, year):
    return [s for s in stations if s['first_year'] <= year <= s['last_year']]


def print_station_list(title, rows):
    print(title)
    for i, s in enumerate(rows, 1):
        print(
            f"  [{i}] id={s['id']}, 站点名称={s['name']}, lat={s['lat']:.4f}, lon={s['lon']:.4f}, "
            f"数据可用范围={s['first_year']}-{s['last_year']}, 与中心点距离={s.get('dist_km',0):.1f}km"
        )


def choose_multi_from_list(rows):
    return rows[:]


def choose_one_from_list(rows):
    if not rows:
        raise ValueError("No candidate stations available")
    return rows[0]


def download_igra_data(station_id: str, out_dir: Path):
    out_dir.mkdir(parents=True, exist_ok=True)
    zip_name = f'{station_id}-data.txt.zip'
    txt_name = f'{station_id}-data.txt'
    zip_path = out_dir / zip_name
    txt_path = out_dir / txt_name
    if txt_path.exists() and txt_path.stat().st_size > 0:
        print(f'[已存在跳过下载] {txt_path.name}')
        return txt_path, True, None
    url = f'https://www.ncei.noaa.gov/data/integrated-global-radiosonde-archive/access/data-por/{zip_name}'
    print(f'开始下载: {station_id}', end=' ')

    last_err = None
    for i in range(1, 11):
        try:
            urllib.request.urlretrieve(url, zip_path)
            last_err = None
            break
        except Exception as e:
            last_err = str(e)
            print(f'[重试] {station_id} 第{i}次下载失败: {last_err}')
    if last_err is not None:
        print(f'[失败] {station_id} 连续10次下载失败')
        print(f'手动下载链接: {url}')
        print(f'手动保存路径: {txt_path}')
        return None, False, {'url': url, 'save_path': str(txt_path), 'error': last_err}

    with zipfile.ZipFile(zip_path, 'r') as zf:
        members = zf.namelist()
        target = txt_name if txt_name in members else members[0]
        zf.extract(target, path=out_dir)
        extracted = out_dir / target
    if extracted.name != txt_name:
        extracted.rename(txt_path)
    for member in members:
        p = out_dir / member
        if p.exists() and p.is_file() and p.name != txt_name:
            p.unlink()
    if zip_path.exists():
        zip_path.unlink()
    print('[完成下载]')
    return txt_path, False, None


def main():
    parser = argparse.ArgumentParser(description='步骤1a: 选站并下载IGRA原始文本')
    parser.add_argument('--year', type=int, help='研究年份，例如 2023')
    parser.add_argument('--station-id', type=str, help='手动指定站号；不传则按范围选站')
    parser.add_argument('--auto-select-all', action='store_true', help='自动选择候选列表全部站点')
    parser.add_argument('--yes', action='store_true', help='兼容参数，保留但不再触发交互')
    args = parser.parse_args()

    DATA_ROOT.mkdir(parents=True, exist_ok=True)

    center_path = current_project_path("grid", "center_location")
    grid_path = current_project_path("grid", "grid.cmn")
    station_list_path = engine_path("resources", "igra", "igra2-station-list.txt")

    center_lat, center_lon = parse_center(center_path)
    dgrid_km, nx, ny = parse_grid(grid_path)
    stations = load_station_list(station_list_path)

    year = args.year
    if year is None:
        raise SystemExit('year is required; pass --year YYYY')

    force_single_nearest = False
    if args.station_id:
        chosen = [s for s in stations if s['id'] == args.station_id]
        if not chosen:
            print(f'指定站号不在站点表中: {args.station_id}')
            return 1
        chosen_list = chosen
    else:
        in_domain, rows = choose_station(stations, center_lat, center_lon, dgrid_km, nx, ny)
        rows = filter_by_year(rows, year)
        if not rows:
            print('范围候选无该年份可用站点, 改为全站最近3个可用站点')
            rows = filter_by_year(stations, year)
            rows = sorted([{**s, 'dist_km': haversine_km(center_lat, center_lon, s['lat'], s['lon'])} for s in rows], key=lambda x: x['dist_km'])[:3]
            force_single_nearest = True
        print_station_list('候选站点: ', rows)
        if force_single_nearest:
            print("范围内无可用高空站点: 自动选择最近站点")
            chosen_list = [choose_one_from_list(rows)]
        elif args.auto_select_all:
            chosen_list = rows[:]
            print(f'自动选择全部候选站点, 共 {len(chosen_list)} 个')
        else:
            raise SystemExit('Non-interactive mode requires --station-id or --auto-select-all')

    year_dir = DATA_ROOT / str(year)
    year_dir.mkdir(parents=True, exist_ok=True)

    selected_file = year_dir / 'upperair_station_used_list.txt'
    failed_file = year_dir / f'download_failed_stations_{year}.csv'
    failed_rows = []
    with selected_file.open('w', encoding='utf-8', newline='') as sf:
        w = csv.writer(sf)
        w.writerow(['id', 'name', 'lat', 'lon', 'elev_m', 'year', 'raw_txt'])
        for s in chosen_list:
            lat_to_write = round(center_lat, 4)
            lon_to_write = round(center_lon, 4)
            txt, skipped, fail_info = download_igra_data(s['id'], year_dir)
            if txt is not None:
                w.writerow([s['id'], s['name'], lat_to_write, lon_to_write, s['elev_m'], year, str(txt)])
            else:
                failed_rows.append([s['id'], s['name'], fail_info['url'], fail_info['save_path'], fail_info['error']])

    print(f'已下载站点清单: {selected_file}')
    if failed_rows:
        with failed_file.open('w', encoding='utf-8', newline='') as ff:
            fw = csv.writer(ff)
            fw.writerow(['id', 'name', 'manual_url', 'save_path', 'error'])
            fw.writerows(failed_rows)
        print(f'失败站点清单已写入: {failed_file}')
    print(f'数据保存路径: {year_dir}/')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
