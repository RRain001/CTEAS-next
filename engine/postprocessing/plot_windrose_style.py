from __future__ import annotations

import argparse
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.patches import Rectangle

from engine.core.paths import current_project_path, tutorial_path

CSV_PATH = current_project_path("met", "surface", "final", "surface_wind.csv")
SURF_DAT_PATH = current_project_path("met", "surface", "final", "surf.dat")
OUT_PATH = current_project_path("run", "puff", "postprocessing", "windrose.png")
LOCAL_TIMES_TTF = tutorial_path("Times New Roman.ttf")

COL_MONTH = 'Month'
COL_DIR = 'deg'
COL_SPEED = 'ms-1'

# 与示例图一致的风速分级与配色（低风速在底层）
SPEED_BINS = [0.5, 2.5, 4.5, 6.5, 8.5, 10.5, np.inf]
SPEED_LABELS = ['0.5-2.5', '2.5-4.5', '4.5-6.5', '6.5-8.5', '8.5-10.5', '>=10.5']
SPEED_COLORS = ['#f86a6d', '#f2c16d', '#ece99a', '#8dcd8d', '#98d9de', '#8fa8dd']

SECTORS = 16
SECTOR_WIDTH = 360.0 / SECTORS
THETA = np.deg2rad(np.arange(0, 360, SECTOR_WIDTH))
BAR_WIDTH = np.deg2rad(SECTOR_WIDTH * 0.82)


def configure_local_fonts() -> None:
    if LOCAL_TIMES_TTF.exists():
        font_manager.fontManager.addfont(str(LOCAL_TIMES_TTF))


def load_data(path: Path, month_column: str, direction_column: str, speed_column: str) -> pd.DataFrame:
    df = pd.read_csv(path, encoding='utf-8-sig')
    if month_column not in df.columns and len(df.columns) > 0 and str(df.columns[0]).strip() == "GENERIC":
        df = pd.read_csv(path, encoding='utf-8-sig', skiprows=2)
    return normalize_wind_dataframe(df, month_column, direction_column, speed_column)


def normalize_wind_dataframe(
    df: pd.DataFrame,
    month_column: str,
    direction_column: str,
    speed_column: str,
) -> pd.DataFrame:
    for col in [month_column, direction_column, speed_column]:
        if col not in df.columns:
            raise ValueError(f"Missing column '{col}' in wind data")
    df = df[[month_column, direction_column, speed_column]].rename(
        columns={
            month_column: COL_MONTH,
            direction_column: COL_DIR,
            speed_column: COL_SPEED,
        }
    )
    df[COL_MONTH] = pd.to_numeric(df[COL_MONTH], errors='coerce')
    df[COL_DIR] = pd.to_numeric(df[COL_DIR], errors='coerce')
    df[COL_SPEED] = pd.to_numeric(df[COL_SPEED], errors='coerce')

    # 清理异常值与缺测
    df = df.dropna(subset=[COL_MONTH, COL_DIR, COL_SPEED])
    df = df[(df[COL_SPEED] >= 0) & (df[COL_SPEED] < 100)]
    df = df[(df[COL_DIR] >= 0) & (df[COL_DIR] <= 360)]

    # 将 360 度并入 0 度
    df.loc[df[COL_DIR] == 360, COL_DIR] = 0
    return df


def _is_time_line(parts: list[str]) -> bool:
    if len(parts) != 8:
        return False
    try:
        vals = [int(float(x)) for x in parts]
    except ValueError:
        return False
    return 1900 <= vals[0] <= 2200 and 1 <= vals[1] <= 366 and 0 <= vals[2] <= 24


def load_surf_dat(path: Path, station_index: int = 1) -> pd.DataFrame:
    lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    if len(lines) < 7:
        raise ValueError(f"Invalid SURF.DAT file: {path}")
    try:
        station_count = int(lines[1].strip())
    except ValueError as exc:
        raise ValueError(f"Cannot read station count from SURF.DAT: {path}") from exc
    if station_index < 1 or station_index > station_count:
        raise ValueError(f"station_index must be 1..{station_count}, got {station_index}")

    rows: list[dict[str, float]] = []
    i = 6
    while i < len(lines):
        parts = lines[i].split()
        if not _is_time_line(parts):
            i += 1
            continue
        year = int(float(parts[0]))
        day_of_year = int(float(parts[1]))
        month = (datetime(year, 1, 1) + timedelta(days=max(1, day_of_year) - 1)).month
        first_station_line = i + station_index
        if first_station_line >= len(lines):
            break
        vals = lines[first_station_line].split()
        if len(vals) >= 2:
            try:
                speed = float(vals[0])
                direction = float(vals[1])
            except ValueError:
                i += station_count + 1
                continue
            rows.append({COL_MONTH: month, COL_DIR: direction, COL_SPEED: speed})
        i += station_count + 1
    if not rows:
        raise ValueError(f"No wind rows parsed from SURF.DAT: {path}")
    return normalize_wind_dataframe(pd.DataFrame(rows), COL_MONTH, COL_DIR, COL_SPEED)


def frequency_matrix(direction: np.ndarray, speed: np.ndarray) -> np.ndarray:
    # 按 16 方位统计，角度边界采用四舍五入到扇区中心
    sector_idx = ((direction + SECTOR_WIDTH / 2) // SECTOR_WIDTH).astype(int) % SECTORS

    mat = np.zeros((SECTORS, len(SPEED_LABELS)), dtype=float)
    total = len(direction)
    for i in range(len(SPEED_LABELS)):
        low = SPEED_BINS[i]
        high = SPEED_BINS[i + 1]
        if np.isinf(high):
            mask = speed >= low
        else:
            mask = (speed >= low) & (speed < high)

        if np.any(mask):
            counts = np.bincount(sector_idx[mask], minlength=SECTORS)
            mat[:, i] = counts / total * 100.0

    return mat


def draw_one_windrose(
    ax,
    mat_pct: np.ndarray,
    title: str,
    r_ticks: list[float],
    inner: float,
    is_main: bool = False,
) -> None:
    ax.set_theta_zero_location('N')
    ax.set_theta_direction(-1)
    ax.set_facecolor('white')
    ax.set_axisbelow(True)

    bottom = np.full(SECTORS, inner, dtype=float)
    for i in range(len(SPEED_LABELS)):
        vals = mat_pct[:, i]
        ax.bar(
            THETA,
            vals,
            width=BAR_WIDTH,
            bottom=bottom,
            color=SPEED_COLORS[i],
            edgecolor='#b7b7b7',
            linewidth=0.7,
            align='center',
            zorder=3,
        )
        bottom += vals

    # 主方向标签与网格
    ax.set_thetagrids(np.arange(0, 360, 45), labels=['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW'])
    theta_fontsize = 14 if is_main else 11
    r_fontsize = 14 if is_main else 10
    title_fontsize = 24 if is_main else 11

    max_r = inner + max(r_ticks)
    ax.set_ylim(0, max_r)
    ax.set_yticks([inner + r for r in r_ticks])
    ax.set_yticklabels([])
    ax.set_rlabel_position(240)
    for r in r_ticks:
        ax.text(
            np.deg2rad(240),
            inner + r - 0.15,
            f'{int(r)}%',
            fontsize=r_fontsize,
            fontweight='bold',
            ha='center',
            va='center',
            zorder=40,
            clip_on=False,
        )

    ax.grid(color='#a9a9a9', alpha=0.75, linewidth=0.8, zorder=0)
    ax.spines['polar'].set_color('#b2b2b2')
    ax.spines['polar'].set_linewidth(1.0)

    for tick in ax.get_xticklabels() + ax.get_yticklabels():
        tick.set_fontweight('bold')
    for tick in ax.get_xticklabels():
        tick.set_fontsize(theta_fontsize)

    # 中心留白，模拟示例中的空心风玫瑰
    ax.bar([0], [inner], width=2 * np.pi, bottom=0, color='white', edgecolor='none', zorder=10)
    title_y = -0.20 if is_main else -0.16
    ax.set_title(title, y=title_y, fontsize=title_fontsize, fontweight='bold')


def add_legend(fig) -> None:
    handles = [
        Rectangle((0, 0), 1, 1, facecolor=c, edgecolor='#b7b7b7', linewidth=0.8)
        for c in SPEED_COLORS[::-1]
    ]
    labels = SPEED_LABELS[::-1]

    leg = fig.legend(
        handles,
        labels,
        title='Wind Speed (m/s)',
        loc='center left',
        bbox_to_anchor=(0.91, 0.5),
        frameon=False,
        fontsize=11,
        title_fontsize=13,
        handlelength=2.6,
        handleheight=1.6,
        labelspacing=1.0,
    )
    leg.get_title().set_fontweight('bold')
    for t in leg.get_texts():
        t.set_fontweight('bold')


def render_windrose(df: pd.DataFrame, output_path: Path) -> None:
    configure_local_fonts()
    plt.rcParams['font.family'] = ['Times New Roman', 'SimSun', 'DejaVu Serif']
    plt.rcParams['font.weight'] = 'bold'
    plt.rcParams['axes.labelweight'] = 'bold'
    plt.rcParams['axes.unicode_minus'] = False

    annual = df
    spring = df[df[COL_MONTH].isin([3, 4, 5])]
    summer = df[df[COL_MONTH].isin([6, 7, 8])]
    autumn = df[df[COL_MONTH].isin([9, 10, 11])]
    winter = df[df[COL_MONTH].isin([12, 1, 2])]

    datasets = [
        (annual, '2023 Annual', [4, 8, 12, 16], 2.0),
        (spring, 'Spring (3, 4, 5)', [4, 8, 12, 16], 1.2),
        (summer, 'Summer (6, 7, 8)', [4, 8, 12, 16], 1.2),
        (autumn, 'Autumn (9, 10, 11)', [4, 8, 12, 16], 1.2),
        (winter, 'Winter (12, 1, 2)', [4, 8, 12, 16], 1.2),
    ]

    fig = plt.figure(figsize=(16.5, 8.5), facecolor='white')
    gs = fig.add_gridspec(2, 3, width_ratios=[1.6, 1.0, 1.0], wspace=0.20, hspace=0.28)

    axes = [
        fig.add_subplot(gs[:, 0], projection='polar'),
        fig.add_subplot(gs[0, 1], projection='polar'),
        fig.add_subplot(gs[0, 2], projection='polar'),
        fig.add_subplot(gs[1, 1], projection='polar'),
        fig.add_subplot(gs[1, 2], projection='polar'),
    ]

    for idx, (ax, (sub_df, title, r_ticks, inner)) in enumerate(zip(axes, datasets)):
        mat = frequency_matrix(sub_df[COL_DIR].to_numpy(), sub_df[COL_SPEED].to_numpy())
        draw_one_windrose(ax, mat, title, r_ticks, inner, is_main=(idx == 0))

    add_legend(fig)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=300, bbox_inches='tight', facecolor=fig.get_facecolor())
    plt.close(fig)
    print(f'Saved figure: {output_path}')


def main() -> None:
    parser = argparse.ArgumentParser(description="Plot wind rose from surface meteorology CSV or SURF.DAT.")
    parser.add_argument("--csv", type=Path, default=None, help="Optional wind CSV. If omitted, --surf-dat is used.")
    parser.add_argument("--surf-dat", type=Path, default=SURF_DAT_PATH, help="SMERGE SURF.DAT input")
    parser.add_argument("--station-index", type=int, default=1, help="1-based station index for SURF.DAT")
    parser.add_argument("--output", type=Path, default=OUT_PATH)
    parser.add_argument("--month-column", default=COL_MONTH)
    parser.add_argument("--direction-column", default=COL_DIR)
    parser.add_argument("--speed-column", default=COL_SPEED)
    args = parser.parse_args()

    if args.csv:
        df = load_data(args.csv, args.month_column, args.direction_column, args.speed_column)
    else:
        df = load_surf_dat(args.surf_dat, args.station_index)
    render_windrose(df, args.output)


if __name__ == '__main__':
    main()
