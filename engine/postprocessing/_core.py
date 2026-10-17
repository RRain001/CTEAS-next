from __future__ import annotations

import argparse
import struct
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterable

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LinearSegmentedColormap, LogNorm, Normalize, TwoSlopeNorm
from matplotlib import font_manager
from mpl_toolkits.axes_grid1 import make_axes_locatable

from engine.core.paths import current_project_path, tutorial_path
from engine.core.runtime_names import MET_INP, PUFF_CON


DEFAULT_CONC_FILE = current_project_path("run", "puff", PUFF_CON)
DEFAULT_MET_INP = current_project_path("run", "met", MET_INP)
DEFAULT_POSTPROCESS_DIR = current_project_path("run", "puff", "postprocessing")
DEFAULT_TERRAIN_FILE = current_project_path("run", "puff", "qaterr.grd")

UNIFIED_DEFAULTS = {
    "scale": "linear",
    "vmin": 5e-4,
    "vmax": 5e-2,
    "threshold": 1.2e-3,
    "cmap": "hadcrut",
}
SNAPSHOT_DEFAULTS = UNIFIED_DEFAULTS.copy()
MEAN_DEFAULTS = UNIFIED_DEFAULTS.copy()
SEASON_ORDER = ["Spring", "Summer", "Autumn", "Winter"]
SEASON_MONTHS = {
    "Winter": {12, 1, 2},
    "Spring": {3, 4, 5},
    "Summer": {6, 7, 8},
    "Autumn": {9, 10, 11},
}
HADCRUT_COLORS = [
    "#E0F3F8",
    "#313695",
    "#6BFF00",
    "#FEE090",
    "#F46D43",
    "#D73027",
]
TERRAIN_POSITIVE_COLORS = [
    "#d8e9c2",
    "#a8d08d",
    "#d7c58a",
    "#c6ab73",
    "#b18f61",
    "#d9c7a7",
    "#f3efe4",
]
TERRAIN_OCEAN_COLORS = [
    "#08306b",
    "#2171b5",
    "#6baed6",
    "#c6dbef",
]

plt.rcParams.update(
    {
        "font.family": "serif",
        "font.serif": ["Times New Roman", "DejaVu Serif"],
        "font.weight": "bold",
        "font.size": 16,
        "axes.labelweight": "bold",
        "axes.titleweight": "bold",
        "axes.unicode_minus": False,
    }
)

# Load local Times New Roman font file if present.
LOCAL_TIMES_TTF = tutorial_path("Times New Roman.ttf")
if LOCAL_TIMES_TTF.exists():
    font_manager.fontManager.addfont(str(LOCAL_TIMES_TTF))
    plt.rcParams["font.family"] = "Times New Roman"


@dataclass
class GridSpec:
    nx: int
    ny: int
    dgrid_km: float
    xorig_km: float
    yorig_km: float


@dataclass
class RunWindow:
    start: datetime
    end: datetime


@dataclass
class TimeRecord:
    start: datetime
    end: datetime
    data_offset: int


@dataclass
class SeasonalField:
    field: np.ndarray | None
    count: int
    start: datetime | None
    end: datetime | None
    periods: list[tuple[datetime, datetime]] | None = None


def _extract_calmet_key(text: str, key: str, cast):
    marker = f"! {key}"
    for line in text.splitlines():
        if marker in line and "=" in line:
            val = line.split("=", 1)[1].split("!", 1)[0].strip()
            return cast(val)
    raise ValueError(f"Cannot find {key} in CALMET.INP")


def parse_calmet_grid(calmet_inp: Path) -> GridSpec:
    text = calmet_inp.read_text(encoding="utf-8", errors="ignore")
    return GridSpec(
        nx=_extract_calmet_key(text, "NX", int),
        ny=_extract_calmet_key(text, "NY", int),
        dgrid_km=_extract_calmet_key(text, "DGRIDKM", float),
        xorig_km=_extract_calmet_key(text, "XORIGKM", float),
        yorig_km=_extract_calmet_key(text, "YORIGKM", float),
    )


def parse_calmet_run_window(calmet_inp: Path) -> RunWindow:
    text = calmet_inp.read_text(encoding="utf-8", errors="ignore")
    return RunWindow(
        start=datetime(
            _extract_calmet_key(text, "IBYR", int),
            _extract_calmet_key(text, "IBMO", int),
            _extract_calmet_key(text, "IBDY", int),
            _extract_calmet_key(text, "IBHR", int),
            0,
            _extract_calmet_key(text, "IBSEC", int),
        ),
        end=datetime(
            _extract_calmet_key(text, "IEYR", int),
            _extract_calmet_key(text, "IEMO", int),
            _extract_calmet_key(text, "IEDY", int),
            _extract_calmet_key(text, "IEHR", int),
            0,
            _extract_calmet_key(text, "IESEC", int),
        ),
    )


def _read_fortran_record(f) -> tuple[int, int]:
    head = f.read(4)
    if len(head) == 0:
        return -1, -1
    if len(head) < 4:
        raise EOFError("Unexpected EOF while reading Fortran record header")
    (nbytes,) = struct.unpack("<i", head)
    if nbytes < 0:
        raise ValueError(f"Invalid record length: {nbytes}")
    return f.tell(), nbytes


def _finish_fortran_record(f, payload_offset: int, nbytes: int) -> None:
    f.seek(payload_offset + nbytes)
    tail = f.read(4)
    if len(tail) < 4:
        raise EOFError("Unexpected EOF while reading Fortran record tail")
    (end_nbytes,) = struct.unpack("<i", tail)
    if end_nbytes != nbytes:
        raise ValueError(f"Fortran record marker mismatch: {nbytes} != {end_nbytes}")


def _decode_time_record(payload: bytes) -> tuple[datetime, datetime] | None:
    if len(payload) != 32:
        return None
    y1, d1, h1, s1, y2, d2, h2, s2 = struct.unpack("<8i", payload)
    if not (1900 <= y1 <= 2200 and 1900 <= y2 <= 2200):
        return None
    if not (1 <= d1 <= 366 and 1 <= d2 <= 366):
        return None
    if not (0 <= h1 <= 23 and 0 <= h2 <= 24):
        return None
    if not (0 <= s1 < 3600 and 0 <= s2 < 3600):
        return None
    start = datetime(y1, 1, 1) + timedelta(days=d1 - 1, hours=h1, seconds=s1)
    end = datetime(y2, 1, 1) + timedelta(days=d2 - 1, hours=h2, seconds=s2)
    return start, end


def index_time_records(conc_file: Path, nx: int, ny: int) -> list[TimeRecord]:
    expected_data_len = 15 + nx * ny * 4
    records: list[TimeRecord] = []
    pending_time: tuple[datetime, datetime] | None = None
    saw_meta_after_time = False

    with conc_file.open("rb") as f:
        while True:
            payload_offset, nbytes = _read_fortran_record(f)
            if nbytes < 0:
                break
            if nbytes == 32:
                payload = f.read(32)
                _finish_fortran_record(f, payload_offset, nbytes)
                decoded = _decode_time_record(payload)
                if decoded is not None:
                    pending_time = decoded
                    saw_meta_after_time = False
                elif pending_time is not None:
                    saw_meta_after_time = True
                continue
            if nbytes == expected_data_len and pending_time is not None and saw_meta_after_time:
                records.append(TimeRecord(start=pending_time[0], end=pending_time[1], data_offset=payload_offset))
                _finish_fortran_record(f, payload_offset, nbytes)
                pending_time = None
                saw_meta_after_time = False
                continue
            _finish_fortran_record(f, payload_offset, nbytes)

    if not records:
        raise RuntimeError("No timestep data records found. Please verify puff.con and grid size.")
    return records


def load_concentration_at_offset(conc_file: Path, offset: int, nx: int, ny: int) -> np.ndarray:
    nbytes = 15 + nx * ny * 4
    with conc_file.open("rb") as f:
        f.seek(offset)
        payload = f.read(nbytes)
    if len(payload) != nbytes:
        raise RuntimeError("Cannot read full concentration payload")
    arr = np.frombuffer(payload[15:], dtype="<f4")
    if arr.size != nx * ny:
        raise RuntimeError(f"Unexpected concentration array size: {arr.size}")
    return arr.reshape(ny, nx)


def pick_timestep(records: list[TimeRecord], when: str | None, step: int | None) -> tuple[int, TimeRecord]:
    if when is None and step is None:
        idx = len(records) - 1
        return idx, records[idx]
    if step is not None:
        if step < 0:
            step = len(records) + step
        if step < 0 or step >= len(records):
            raise IndexError(f"step out of range: {step}, total={len(records)}")
        return step, records[step]
    dt = datetime.strptime(when, "%Y-%m-%d %H:%M")
    diffs = [abs((r.start - dt).total_seconds()) for r in records]
    idx = int(np.argmin(diffs))
    return idx, records[idx]


def print_time_summary(records: Iterable[TimeRecord]) -> None:
    seq = list(records)
    print(f"Detected timesteps: {len(seq)}")
    print(f"First: {seq[0].start:%Y-%m-%d %H:%M} -> {seq[0].end:%Y-%m-%d %H:%M}")
    print(f"Last : {seq[-1].start:%Y-%m-%d %H:%M} -> {seq[-1].end:%Y-%m-%d %H:%M}")


def resolve_cmap(name: str):
    if name == "hadcrut":
        return LinearSegmentedColormap.from_list("hadcrut", HADCRUT_COLORS, N=256)
    if name == "terrain_positive":
        return LinearSegmentedColormap.from_list("terrain_positive", TERRAIN_POSITIVE_COLORS, N=256)
    if name == "terrain_negative":
        return LinearSegmentedColormap.from_list("terrain_negative", TERRAIN_OCEAN_COLORS, N=256)
    if name == "terrain_adaptive":
        return LinearSegmentedColormap.from_list(
            "terrain_adaptive",
            TERRAIN_OCEAN_COLORS + ["#f7f7f7"] + TERRAIN_POSITIVE_COLORS,
            N=256,
        )
    return plt.get_cmap(name)


def build_levels(scale: str, vmin: float, vmax: float, count: int = 100) -> np.ndarray:
    if scale == "log":
        return np.geomspace(vmin, vmax, count)
    return np.linspace(vmin, vmax, count + 1)


def build_colorbar_ticks(scale: str, vmin: float, vmax: float) -> list[float]:
    if scale == "log":
        ticks = [vmin, 1e-3, 3e-3, 1e-2, 3e-2, vmax]
        deduped: list[float] = []
        for tick in ticks:
            if vmin <= tick <= vmax and tick not in deduped:
                deduped.append(tick)
        return deduped
    return list(np.linspace(vmin, vmax, 6))


def style_colorbar(cbar, scale: str, vmin: float, vmax: float) -> None:
    cbar.set_ticks(build_colorbar_ticks(scale, vmin, vmax))
    # Flip colorbar orientation (compared with previous setting).
    # Keep higher values at the top by default.


def style_terrain_colorbar(cbar) -> None:
    cbar.set_label("Elevation (m)", fontsize=16, fontweight="bold")
    if getattr(cbar, "orientation", None) == "horizontal":
        cbar.ax.xaxis.set_label_position("bottom")


def resolve_terrain_style(terrain_data: np.ndarray) -> tuple[LinearSegmentedColormap, Normalize]:
    zmin = float(np.nanmin(terrain_data))
    zmax = float(np.nanmax(terrain_data))
    if zmin >= 0:
        return resolve_cmap("terrain_positive"), Normalize(vmin=zmin, vmax=zmax)
    if zmax <= 0:
        return resolve_cmap("terrain_negative"), Normalize(vmin=zmin, vmax=zmax)
    return resolve_cmap("terrain_adaptive"), TwoSlopeNorm(vmin=zmin, vcenter=0.0, vmax=zmax)


def _plot_edges(grid: GridSpec) -> tuple[np.ndarray, np.ndarray]:
    x_edges = grid.xorig_km + np.arange(grid.nx + 1) * grid.dgrid_km
    y_edges = grid.yorig_km + np.arange(grid.ny + 1) * grid.dgrid_km
    return x_edges, y_edges


def _plot_centers(grid: GridSpec) -> tuple[np.ndarray, np.ndarray]:
    x_centers = grid.xorig_km + (np.arange(grid.nx) + 0.5) * grid.dgrid_km
    y_centers = grid.yorig_km + (np.arange(grid.ny) + 0.5) * grid.dgrid_km
    return x_centers, y_centers


def validate_scale_args(scale: str, vmin: float, vmax: float) -> None:
    if vmin >= vmax:
        raise ValueError(f"Require vmin < vmax, got vmin={vmin}, vmax={vmax}")
    if scale == "log" and vmin <= 0:
        raise ValueError(f"Log scale requires vmin > 0, got vmin={vmin}")


def validate_cli_args(mode: str, when: str | None, step: int | None, scale: str, vmin: float, vmax: float) -> None:
    if when is not None and step is not None:
        raise ValueError("--time and --step cannot be used together")
    if mode != "snapshot" and (when is not None or step is not None):
        raise ValueError(f"--time/--step are only valid for snapshot mode, got mode={mode}")
    validate_scale_args(scale, vmin, vmax)


def ensure_output_path(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def load_surfer_ascii_grid(grd_file: Path) -> tuple[np.ndarray, tuple[float, float, float, float]]:
    with grd_file.open("r", encoding="utf-8", errors="ignore") as f:
        magic = f.readline().strip()
        if magic != "DSAA":
            raise ValueError(f"Unsupported GRD format in {grd_file}: {magic}")
        dims = np.fromstring(f.readline(), sep=" ")
        x_range = np.fromstring(f.readline(), sep=" ")
        y_range = np.fromstring(f.readline(), sep=" ")
        _ = f.readline()  # z range, not needed for plotting
        values = np.fromstring(f.read(), sep=" ")

    if dims.size != 2:
        raise ValueError(f"Invalid GRD dimensions in {grd_file}")
    nx, ny = int(dims[0]), int(dims[1])
    if values.size != nx * ny:
        raise ValueError(f"Unexpected GRD data size in {grd_file}: {values.size} vs {nx * ny}")
    return values.reshape(ny, nx), (float(x_range[0]), float(x_range[1]), float(y_range[0]), float(y_range[1]))


def resolve_terrain_file(conc_file: Path, terrain_file: Path | None = None) -> Path | None:
    candidates = []
    if terrain_file is not None:
        candidates.append(terrain_file)
    candidates.append(conc_file.parent / "qaterr.grd")
    candidates.append(conc_file.parents[2] / "geo" / "makegeo" / "qaterr.grd")
    candidates.append(DEFAULT_TERRAIN_FILE)
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def load_default_terrain(grid: GridSpec, conc_file: Path | None = None, terrain_file: Path | None = None) -> np.ndarray | None:
    terrain_path = resolve_terrain_file(conc_file or DEFAULT_CONC_FILE, terrain_file)
    if terrain_path is None:
        print("Warning: terrain background not found; plotting without terrain overlay.")
        return None
    terrain, (xmin, xmax, ymin, ymax) = load_surfer_ascii_grid(terrain_path)
    if terrain.shape != (grid.ny, grid.nx):
        print(
            f"Warning: terrain grid shape {terrain.shape} does not match concentration grid "
            f"({grid.ny}, {grid.nx}); terrain overlay skipped."
        )
        return None

    x_center_min = grid.xorig_km + 0.5 * grid.dgrid_km
    x_center_max = grid.xorig_km + (grid.nx - 0.5) * grid.dgrid_km
    y_center_min = grid.yorig_km + 0.5 * grid.dgrid_km
    y_center_max = grid.yorig_km + (grid.ny - 0.5) * grid.dgrid_km
    tol = max(1e-6, 0.51 * grid.dgrid_km)
    if (
        abs(xmin - x_center_min) > tol
        or abs(xmax - x_center_max) > tol
        or abs(ymin - y_center_min) > tol
        or abs(ymax - y_center_max) > tol
    ):
        print(
            "Warning: terrain grid extent does not match CALMET grid centers; "
            "terrain overlay will still be attempted."
        )

    print(
        f"Terrain background: {terrain_path.name} "
        f"(min={np.nanmin(terrain):.1f} m, max={np.nanmax(terrain):.1f} m)"
    )
    return terrain


def overlay_terrain(
    ax,
    grid: GridSpec,
    terrain_data: np.ndarray | None,
    coordinate_mode: str = "edges",
    mask: np.ndarray | None = None,
):
    if terrain_data is None:
        return None
    if coordinate_mode not in {"edges", "centers"}:
        raise ValueError(f"Unsupported coordinate_mode: {coordinate_mode}")

    plot_terrain = np.asarray(terrain_data, dtype=float)
    if mask is not None:
        plot_terrain = np.ma.masked_where(mask, plot_terrain)
    terrain_cmap, terrain_norm = resolve_terrain_style(terrain_data)

    x0 = grid.xorig_km
    x1 = grid.xorig_km + grid.nx * grid.dgrid_km
    y0 = grid.yorig_km
    y1 = grid.yorig_km + grid.ny * grid.dgrid_km
    terrain_mesh = ax.imshow(
        plot_terrain,
        origin="lower",
        extent=(x0, x1, y0, y1),
        interpolation="bilinear",
        cmap=terrain_cmap,
        norm=terrain_norm,
        alpha=0.8,
        zorder=0,
    )
    return terrain_mesh


def season_for_datetime(dt: datetime) -> str:
    for season, months in SEASON_MONTHS.items():
        if dt.month in months:
            return season
    raise ValueError(f"Unexpected month: {dt.month}")


def accumulate_mean(conc_file: Path, records: list[TimeRecord], nx: int, ny: int, label: str = "Accumulating") -> np.ndarray:
    total = np.zeros((ny, nx), dtype=np.float64)
    nrec = len(records)
    for idx, rec in enumerate(records, start=1):
        total += load_concentration_at_offset(conc_file, rec.data_offset, nx, ny)
        if idx % 500 == 0 or idx == nrec:
            print(f"{label}: {idx}/{nrec}")
    return total / nrec


def accumulate_seasonal_means(conc_file: Path, records: list[TimeRecord], nx: int, ny: int) -> dict[str, SeasonalField]:
    raw = {
        season: {
            "total": np.zeros((ny, nx), dtype=np.float64),
            "count": 0,
            "start": None,
            "end": None,
            "periods": [],
            "current_start": None,
            "current_end": None,
        }
        for season in SEASON_ORDER + ["Winter"]
    }
    nrec = len(records)
    for idx, rec in enumerate(records, start=1):
        season = season_for_datetime(rec.start + (rec.end - rec.start) / 2)
        raw[season]["total"] += load_concentration_at_offset(conc_file, rec.data_offset, nx, ny)
        raw[season]["count"] += 1
        if raw[season]["start"] is None or rec.start < raw[season]["start"]:
            raw[season]["start"] = rec.start
        if raw[season]["end"] is None or rec.end > raw[season]["end"]:
            raw[season]["end"] = rec.end
        if raw[season]["current_start"] is None:
            raw[season]["current_start"] = rec.start
            raw[season]["current_end"] = rec.end
        elif rec.start == raw[season]["current_end"]:
            raw[season]["current_end"] = rec.end
        else:
            raw[season]["periods"].append((raw[season]["current_start"], raw[season]["current_end"]))
            raw[season]["current_start"] = rec.start
            raw[season]["current_end"] = rec.end
        if idx % 500 == 0 or idx == nrec:
            print(f"Accumulating by season: {idx}/{nrec}")

    result: dict[str, SeasonalField] = {}
    for season in ["Winter", "Spring", "Summer", "Autumn"]:
        count = raw[season]["count"]
        if count == 0:
            result[season] = SeasonalField(field=None, count=0, start=None, end=None)
            continue
        if raw[season]["current_start"] is not None:
            raw[season]["periods"].append((raw[season]["current_start"], raw[season]["current_end"]))
        result[season] = SeasonalField(
            field=raw[season]["total"] / count,
            count=count,
            start=raw[season]["start"],
            end=raw[season]["end"],
            periods=raw[season]["periods"],
        )
    return result


def format_season_periods(periods: list[tuple[datetime, datetime]] | None) -> str:
    if not periods:
        return ""
    if len(periods) == 1:
        s, e = periods[0]
        return f"{s:%Y-%m-%d} to {e:%Y-%m-%d}"
    labels = [f"{s:%Y-%m-%d} to {e:%Y-%m-%d}" for s, e in periods]
    return "\n".join(labels)


def render_snapshot_plot(
    conc2d: np.ndarray,
    rec: TimeRecord,
    grid: GridSpec,
    terrain_data: np.ndarray | None,
    out_png: Path,
    scale: str,
    vmin: float,
    vmax: float,
    threshold: float | None,
    cmap_name: str,
) -> Path:
    validate_scale_args(scale, vmin, vmax)
    x_edges, y_edges = _plot_edges(grid)
    fig, ax = plt.subplots(figsize=(8.5, 7.8), constrained_layout=False)
    conc_plot = np.asarray(conc2d, dtype=float)
    conc_plot = np.where(np.isfinite(conc_plot), conc_plot, vmin)
    if threshold is not None:
        conc_plot = np.ma.masked_where(conc_plot < threshold, conc_plot)
    terrain_mesh = overlay_terrain(ax, grid, terrain_data, coordinate_mode="edges", mask=None)
    if scale == "log":
        conc_plot = np.clip(conc_plot, vmin, vmax)
        norm = LogNorm(vmin=vmin, vmax=vmax)
    else:
        norm = Normalize(vmin=vmin, vmax=vmax)
    pcm = ax.pcolormesh(
        x_edges,
        y_edges,
        conc_plot,
        shading="auto",
        cmap=resolve_cmap(cmap_name),
        norm=norm,
        alpha=0.9,
    )
    divider = make_axes_locatable(ax)
    conc_cax = divider.append_axes("right", size="2.8%", pad=0.12)
    terrain_cax = divider.append_axes("bottom", size="2.8%", pad=0.32)
    cbar = fig.colorbar(pcm, cax=conc_cax, extend="both")
    style_colorbar(cbar, scale, vmin, vmax)
    cbar.set_label("Concentration of tritium (Bq/m³)", fontsize=16, fontweight="bold")
    if terrain_mesh is not None:
        terrain_cbar = fig.colorbar(terrain_mesh, cax=terrain_cax, orientation="horizontal", extend="both")
        style_terrain_colorbar(terrain_cbar)
    ax.set_xlabel("")
    ax.set_ylabel("Y (km)")
    ax.set_aspect("equal")
    ax.grid(False)
    ax.set_title(f"Concentration Snapshot\n{rec.start:%Y-%m-%d %H:%M} to {rec.end:%Y-%m-%d %H:%M}")
    out_png = ensure_output_path(out_png)
    fig.subplots_adjust(left=0.09, right=0.90, top=0.91, bottom=0.11)
    fig.savefig(out_png, dpi=300, bbox_inches="tight", pad_inches=0.03)
    plt.close(fig)
    return out_png


def render_mean_plot(
    conc2d: np.ndarray,
    first_rec: TimeRecord,
    last_rec: TimeRecord,
    grid: GridSpec,
    terrain_data: np.ndarray | None,
    out_png: Path,
    scale: str,
    vmin: float,
    vmax: float,
    threshold: float | None,
    cmap_name: str,
    title: str,
    cbar_label: str,
) -> Path:
    validate_scale_args(scale, vmin, vmax)
    x_centers, y_centers = _plot_centers(grid)
    conc_plot = np.asarray(conc2d, dtype=float)
    conc_plot = np.where(np.isfinite(conc_plot), conc_plot, vmin if scale == "log" else np.nan)
    if threshold is not None:
        conc_plot = np.ma.masked_where(conc_plot < threshold, conc_plot)
    fig, ax = plt.subplots(figsize=(8.5, 7.8), constrained_layout=False)
    norm = LogNorm(vmin=vmin, vmax=vmax) if scale == "log" else Normalize(vmin=vmin, vmax=vmax)
    levels = build_levels(scale, vmin, vmax)
    terrain_mesh = overlay_terrain(ax, grid, terrain_data, coordinate_mode="centers", mask=None)
    pcm = ax.contourf(
        x_centers,
        y_centers,
        conc_plot,
        levels=levels,
        cmap=resolve_cmap(cmap_name),
        norm=norm,
        extend="both",
        alpha=0.9,
    )
    divider = make_axes_locatable(ax)
    conc_cax = divider.append_axes("right", size="2.8%", pad=0.12)
    terrain_cax = divider.append_axes("bottom", size="2.8%", pad=0.32)
    cbar = fig.colorbar(pcm, cax=conc_cax)
    style_colorbar(cbar, scale, vmin, vmax)
    cbar.set_label("Concentration of tritium (Bq/m³)", fontsize=16, fontweight="bold")
    if terrain_mesh is not None:
        terrain_cbar = fig.colorbar(terrain_mesh, cax=terrain_cax, orientation="horizontal", extend="both")
        style_terrain_colorbar(terrain_cbar)
    ax.set_xlabel("")
    ax.set_ylabel("Y (km)")
    ax.set_aspect("equal")
    ax.grid(False)
    ax.set_title(f"{title}\n{first_rec.start:%Y-%m-%d} to {last_rec.end:%Y-%m-%d}")
    out_png = ensure_output_path(out_png)
    fig.subplots_adjust(left=0.09, right=0.90, top=0.91, bottom=0.11)
    fig.savefig(out_png, dpi=300, bbox_inches="tight", pad_inches=0.03)
    plt.close(fig)
    return out_png


def render_seasonal_plot(
    seasonal_data: dict[str, SeasonalField],
    grid: GridSpec,
    terrain_data: np.ndarray | None,
    out_png: Path,
    scale: str,
    vmin: float,
    vmax: float,
    threshold: float | None,
    cmap_name: str,
) -> Path:
    validate_scale_args(scale, vmin, vmax)
    x_centers, y_centers = _plot_centers(grid)
    fig, axes = plt.subplots(2, 2, figsize=(14, 12), constrained_layout=False)
    axes = axes.flatten()
    fig.subplots_adjust(left=0.08, right=0.88, top=0.92, bottom=0.15, wspace=-0.08, hspace=0.22)
    levels = build_levels(scale, vmin, vmax)
    norm = LogNorm(vmin=vmin, vmax=vmax) if scale == "log" else Normalize(vmin=vmin, vmax=vmax)
    last_pcm = None
    terrain_mesh = None

    for idx, season in enumerate(SEASON_ORDER):
        ax = axes[idx]
        data = seasonal_data[season]
        if data.field is None or data.count == 0:
            current_terrain_mesh = overlay_terrain(ax, grid, terrain_data, coordinate_mode="centers", mask=None)
            if terrain_mesh is None:
                terrain_mesh = current_terrain_mesh
            ax.text(0.5, 0.5, f"No data for {season}", ha="center", va="center", transform=ax.transAxes)
            ax.set_title(season)
        else:
            conc_plot = np.asarray(data.field, dtype=float)
            fill_value = vmin if scale == "log" else np.nan
            conc_plot = np.where(np.isfinite(conc_plot), conc_plot, fill_value)
            if threshold is not None:
                conc_plot = np.ma.masked_where(conc_plot < threshold, conc_plot)
            current_terrain_mesh = overlay_terrain(
                ax,
                grid,
                terrain_data,
                coordinate_mode="centers",
                mask=None,
            )
            if terrain_mesh is None:
                terrain_mesh = current_terrain_mesh
            last_pcm = ax.contourf(
                x_centers,
                y_centers,
                conc_plot,
                levels=levels,
                cmap=resolve_cmap(cmap_name),
                norm=norm,
                extend="both",
                alpha=0.9,
            )
            ax.set_title(season)
        ax.set_xlabel("")
        ax.set_ylabel("Y (km)")
        ax.set_aspect("equal")
        ax.grid(False)

    if last_pcm is not None:
        positions = [ax.get_position() for ax in axes]
        left = min(p.x0 for p in positions)
        right = max(p.x1 for p in positions)
        bottom = min(p.y0 for p in positions)
        top = max(p.y1 for p in positions)
        conc_cax = fig.add_axes([right + 0.012, bottom, 0.013, top - bottom])
        cbar = fig.colorbar(last_pcm, cax=conc_cax, orientation="vertical")
        style_colorbar(cbar, scale, vmin, vmax)
        cbar.set_label("Concentration of tritium (Bq/m³)", fontsize=16, fontweight="bold")
    if terrain_mesh is not None:
        positions = [ax.get_position() for ax in axes]
        left = min(p.x0 for p in positions)
        right = max(p.x1 for p in positions)
        bottom = min(p.y0 for p in positions)
        terrain_cax = fig.add_axes([left, bottom - 0.060, right - left, 0.013])
        terrain_cbar = fig.colorbar(terrain_mesh, cax=terrain_cax, orientation="horizontal", extend="both")
        style_terrain_colorbar(terrain_cbar)
    out_png = ensure_output_path(out_png)
    fig.savefig(out_png, dpi=300, bbox_inches="tight", pad_inches=0.03)
    plt.close(fig)
    return out_png


def resolve_mode_defaults(mode: str) -> dict[str, object]:
    if mode == "snapshot":
        return SNAPSHOT_DEFAULTS.copy()
    return MEAN_DEFAULTS.copy()


def resolve_output_path(mode: str, out: Path | None, out_dir: Path | None) -> Path:
    if out is not None:
        return out
    base_dir = out_dir or DEFAULT_POSTPROCESS_DIR
    filename = {
        "snapshot": "conc_snapshot.png",
        "annual": "conc_annual.png",
        "seasonal": "conc_seasonal.png",
    }[mode]
    return base_dir / filename


def common_parser(description: str) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("--conc-file", type=Path, default=DEFAULT_CONC_FILE, help="Path to PUFF puff.con")
    parser.add_argument("--met-inp", "--calmet-inp", dest="met_inp", type=Path, default=DEFAULT_MET_INP, help="Path to MET input file")
    parser.add_argument("--terrain-file", type=Path, default=None, help="Optional Surfer ASCII terrain grid")
    parser.add_argument("--out", type=Path, default=None, help="Output file path")
    parser.add_argument("--out-dir", type=Path, default=None, help="Output directory")
    parser.add_argument("--scale", choices=["linear", "log"], default=None, help="Color scale type")
    parser.add_argument("--vmin", type=float, default=None, help="Color scale minimum")
    parser.add_argument("--vmax", type=float, default=None, help="Color scale maximum")
    parser.add_argument("--threshold", type=float, default=None, help="Mask values below this threshold")
    parser.add_argument("--cmap", type=str, default=None, help="Matplotlib colormap name or 'hadcrut'")
    return parser


def print_case_summary(grid: GridSpec, window: RunWindow) -> None:
    print(f"Grid: nx={grid.nx}, ny={grid.ny}, dgrid={grid.dgrid_km} km")
    print(f"MET window: {window.start:%Y-%m-%d %H:%M:%S} -> {window.end:%Y-%m-%d %H:%M:%S}")


def run_snapshot(
    conc_file: Path,
    calmet_inp: Path,
    out_png: Path,
    scale: str,
    vmin: float,
    vmax: float,
    threshold: float | None,
    cmap_name: str,
    terrain_file: Path | None = None,
    when: str | None = None,
    step: int | None = None,
) -> Path:
    grid = parse_calmet_grid(calmet_inp)
    window = parse_calmet_run_window(calmet_inp)
    terrain_data = load_default_terrain(grid, conc_file, terrain_file)
    print_case_summary(grid, window)
    if when is not None:
        req = datetime.strptime(when, "%Y-%m-%d %H:%M")
        if req < window.start or req > window.end:
            print("Warning: requested time is outside CALMET window; nearest available record will be used.")
    records = index_time_records(conc_file, grid.nx, grid.ny)
    print_time_summary(records)
    idx, rec = pick_timestep(records, when, step)
    print(f"Selected step index: {idx}")
    print(f"Selected time: {rec.start:%Y-%m-%d %H:%M} -> {rec.end:%Y-%m-%d %H:%M}")
    conc2d = load_concentration_at_offset(conc_file, rec.data_offset, grid.nx, grid.ny)
    return render_snapshot_plot(conc2d, rec, grid, terrain_data, out_png, scale, vmin, vmax, threshold, cmap_name)


def run_annual(
    conc_file: Path,
    calmet_inp: Path,
    out_png: Path,
    scale: str,
    vmin: float,
    vmax: float,
    threshold: float | None,
    cmap_name: str,
    terrain_file: Path | None = None,
) -> Path:
    grid = parse_calmet_grid(calmet_inp)
    window = parse_calmet_run_window(calmet_inp)
    terrain_data = load_default_terrain(grid, conc_file, terrain_file)
    print_case_summary(grid, window)
    records = index_time_records(conc_file, grid.nx, grid.ny)
    print_time_summary(records)
    annual_mean = accumulate_mean(conc_file, records, grid.nx, grid.ny)
    print(f"Annual mean stats: min={np.nanmin(annual_mean):.3e}, max={np.nanmax(annual_mean):.3e}")
    return render_mean_plot(
        annual_mean,
        records[0],
        records[-1],
        grid,
        terrain_data,
        out_png,
        scale,
        vmin,
        vmax,
        threshold,
        cmap_name,
        title="Annual Mean Concentration",
        cbar_label=f"Concentration (annual mean, {scale} scale)",
    )


def run_seasonal(
    conc_file: Path,
    calmet_inp: Path,
    out_png: Path,
    scale: str,
    vmin: float,
    vmax: float,
    threshold: float | None,
    cmap_name: str,
    terrain_file: Path | None = None,
) -> Path:
    grid = parse_calmet_grid(calmet_inp)
    window = parse_calmet_run_window(calmet_inp)
    terrain_data = load_default_terrain(grid, conc_file, terrain_file)
    print_case_summary(grid, window)
    records = index_time_records(conc_file, grid.nx, grid.ny)
    print_time_summary(records)
    seasonal_data = accumulate_seasonal_means(conc_file, records, grid.nx, grid.ny)
    print("\nSeasonal statistics:")
    for season in ["Winter", "Spring", "Summer", "Autumn"]:
        data = seasonal_data[season]
        if data.count > 0 and data.field is not None:
            print(
                f"  {season}: {data.count} timesteps, {data.start:%Y-%m-%d} -> {data.end:%Y-%m-%d}, "
                f"mean min={np.nanmin(data.field):.3e}, mean max={np.nanmax(data.field):.3e}"
            )
        else:
            print(f"  {season}: No data")
    return render_seasonal_plot(seasonal_data, grid, terrain_data, out_png, scale, vmin, vmax, threshold, cmap_name)
