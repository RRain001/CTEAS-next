from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib import font_manager
from matplotlib.font_manager import FontProperties

from engine.core.paths import current_project_path, tutorial_path

DEFAULT_CSV = current_project_path("run", "puff", "postprocessing", "point_timeseries.csv")
DEFAULT_OUTPUT = current_project_path("run", "puff", "postprocessing", "daily_concentration.png")
LOCAL_TIMES_TTF = tutorial_path("Times New Roman.ttf")


def configure_local_fonts() -> None:
    if LOCAL_TIMES_TTF.exists():
        font_manager.fontManager.addfont(str(LOCAL_TIMES_TTF))


def read_timeseries_csv(csv_path: Path, value_column: str) -> pd.DataFrame:
    try:
        df = pd.read_csv(csv_path, encoding="utf-8-sig")
    except UnicodeDecodeError:
        df = pd.read_csv(csv_path, encoding="gb18030")
    if "datetime" not in df.columns:
        raise ValueError(f"CSV missing datetime column: {csv_path}")
    if value_column not in df.columns:
        raise ValueError(f"CSV missing value column '{value_column}': {csv_path}")
    df = df[["datetime", value_column]].copy()
    df["datetime"] = pd.to_datetime(df["datetime"], errors="coerce")
    df[value_column] = pd.to_numeric(df[value_column], errors="coerce")
    df = df.dropna(subset=["datetime", value_column]).sort_values("datetime")
    if df.empty:
        raise ValueError(f"No valid concentration rows found in: {csv_path}")
    return df


def daily_mean_series(df: pd.DataFrame, value_column: str) -> pd.DataFrame:
    daily = (
        df.set_index("datetime")[value_column]
        .resample("D")
        .mean()
        .dropna()
        .rename("concentration")
        .reset_index()
    )
    if daily.empty:
        raise ValueError("No daily mean concentration values can be computed.")
    return daily


def plot_reference_style(
    csv_path: Path,
    output_path: Path,
    value_column: str = "concentration",
    normalize_to_mean: bool = False,
) -> None:
    configure_local_fonts()
    df = read_timeseries_csv(csv_path, value_column)
    daily = daily_mean_series(df, value_column)

    days = np.arange(1, len(daily) + 1)
    values = daily["concentration"].to_numpy(dtype=float)
    annual_mean = float(values.mean()) if len(values) else 0.0
    if normalize_to_mean and annual_mean > 0:
        values_to_plot = values / annual_mean
        mean_for_label = 1.0
        y_label_unit = "relative"
    else:
        values_to_plot = values
        mean_for_label = annual_mean
        y_label_unit = "Bq/m³"

    finite = values_to_plot[np.isfinite(values_to_plot)]
    y_min = 0.0
    y_max = float(np.nanmax(finite)) if finite.size else 1.0
    if y_max <= 0:
        y_max = 1.0
    y_max *= 1.12

    plt.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": ["Times New Roman", "DejaVu Sans"],
            "axes.unicode_minus": False,
            "font.size": 20,
            "font.weight": "bold",
            "axes.labelweight": "bold",
        }
    )

    times_bold = FontProperties(family=["Times New Roman", "DejaVu Serif"], weight="bold", size=20)

    fig = plt.figure(figsize=(13.92, 6.84), facecolor="white")
    ax = fig.add_axes([0.085, 0.16, 0.87, 0.73])
    ax.set_facecolor("white")
    ax.plot(days, values_to_plot, color="#4a4a4a", linewidth=1.4)
    ax.set_xlim(0, max(366, len(daily) + 1))
    ax.set_ylim(y_min, y_max)
    ax.set_autoscale_on(False)

    xticks = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335, 366]
    ax.set_xticks([x for x in xticks if x <= max(366, len(daily) + 1)])
    ax.set_yticks(np.linspace(y_min, y_max, 6))

    for lbl in ax.get_xticklabels() + ax.get_yticklabels():
        lbl.set_fontproperties(times_bold)
    ax.tick_params(axis="both", which="major", direction="in", length=9, width=1.8, labelsize=20, pad=10)
    ax.tick_params(axis="both", which="minor", direction="in", length=5, width=1.2)

    for spine in ax.spines.values():
        spine.set_linewidth(1.8)
        spine.set_color("black")

    ax.set_xlabel("")
    ax.set_ylabel("")
    ax.text(0.5, -0.115, "Day (days)", transform=ax.transAxes, ha="center", va="top", fontproperties=times_bold)
    ax.text(-0.095, 0.5, f"Tritium concentration ({y_label_unit})", transform=ax.transAxes, rotation=90, ha="center", va="center", fontproperties=times_bold)

    cn_text = ax.text(
        0.03,
        0.965,
        "Annual mean: ",
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontproperties=times_bold,
        color="black",
    )
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    cn_bbox = cn_text.get_window_extent(renderer=renderer)
    en_x = ax.transAxes.inverted().transform((cn_bbox.x1, cn_bbox.y1))[0] + 0.004
    ax.text(
        en_x,
        0.958,
        f"{mean_for_label:.6g} {y_label_unit}",
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontproperties=times_bold,
        color="black",
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=300, facecolor=fig.get_facecolor(), bbox_inches="tight")
    plt.close(fig)

    print(f"Saved figure: {output_path}")
    print("Daily concentration statistics:")
    print(f"  Daily records: {len(values)}")
    print(f"  Mean: {annual_mean:.6e} Bq/m³")
    print(f"  Max: {np.nanmax(values):.6e} Bq/m³")
    print(f"  Min: {np.nanmin(values):.6e} Bq/m³")


def main() -> None:
    parser = argparse.ArgumentParser(description="Plot daily mean concentration from a point time-series CSV.")
    parser.add_argument("--csv", type=Path, default=DEFAULT_CSV)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--value-column", default="concentration")
    parser.add_argument("--normalize", action="store_true", help="Normalize daily means to annual mean = 1.")
    args = parser.parse_args()

    plot_reference_style(args.csv, args.output, args.value_column, normalize_to_mean=args.normalize)


if __name__ == "__main__":
    main()
