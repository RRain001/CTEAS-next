from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib import animation
from matplotlib.colors import LogNorm, Normalize
from mpl_toolkits.axes_grid1 import make_axes_locatable

try:
    from ._core import (
        DEFAULT_CONC_FILE,
        DEFAULT_MET_INP,
        DEFAULT_POSTPROCESS_DIR,
        build_colorbar_ticks,
        index_time_records,
        load_concentration_at_offset,
        load_default_terrain,
        overlay_terrain,
        parse_calmet_grid,
        parse_calmet_run_window,
        resolve_cmap,
        resolve_mode_defaults,
        style_colorbar,
        style_terrain_colorbar,
        validate_scale_args,
    )
except ImportError:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from _core import (
        DEFAULT_CONC_FILE,
        DEFAULT_MET_INP,
        DEFAULT_POSTPROCESS_DIR,
        build_colorbar_ticks,
        index_time_records,
        load_concentration_at_offset,
        load_default_terrain,
        overlay_terrain,
        parse_calmet_grid,
        parse_calmet_run_window,
        resolve_cmap,
        resolve_mode_defaults,
        style_colorbar,
        style_terrain_colorbar,
        validate_scale_args,
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Render yearly PUFF concentration animation")
    parser.add_argument("--conc-file", type=Path, default=DEFAULT_CONC_FILE, help="Path to PUFF puff.con")
    parser.add_argument("--met-inp", "--calmet-inp", dest="met_inp", type=Path, default=DEFAULT_MET_INP, help="Path to MET input file")
    parser.add_argument("--terrain-file", type=Path, default=None, help="Optional Surfer ASCII terrain grid")
    parser.add_argument(
        "--out",
        type=Path,
        default=DEFAULT_POSTPROCESS_DIR / "conc_yearly.mp4",
        help="Output animation path (.mp4 recommended, .gif supported)",
    )
    parser.add_argument("--fps", type=int, default=10, help="Frames per second")
    parser.add_argument("--start-step", type=int, default=0, help="Start timestep index (inclusive)")
    parser.add_argument("--end-step", type=int, default=None, help="End timestep index (exclusive), default all")
    parser.add_argument("--stride", type=int, default=1, help="Frame stride, e.g. 3 means every 3rd timestep")
    parser.add_argument("--max-frames", type=int, default=None, help="Hard cap on number of frames")
    parser.add_argument("--scale", choices=["linear", "log"], default=None, help="Color scale type")
    parser.add_argument("--vmin", type=float, default=None, help="Color scale minimum")
    parser.add_argument("--vmax", type=float, default=None, help="Color scale maximum")
    parser.add_argument("--threshold", type=float, default=None, help="Mask values below this threshold")
    parser.add_argument("--cmap", type=str, default=None, help="Matplotlib colormap name or 'hadcrut'")
    parser.add_argument("--dpi", type=int, default=180, help="Output DPI")
    return parser


def _prepare_frame(conc2d: np.ndarray, scale: str, vmin: float, vmax: float, threshold: float | None) -> np.ndarray:
    arr = np.asarray(conc2d, dtype=float)
    # Keep preprocessing consistent with snapshot/annual/seasonal static plots.
    arr = np.where(np.isfinite(arr), arr, vmin)
    if threshold is not None:
        arr = np.ma.masked_where(arr < threshold, arr)
    if scale == "log":
        arr = np.clip(arr, vmin, vmax)
    return arr


def _select_frame_indices(total: int, start: int, end: int | None, stride: int, max_frames: int | None) -> list[int]:
    end_idx = total if end is None else min(end, total)
    if not (0 <= start < end_idx):
        raise ValueError(f"Invalid frame window: start={start}, end={end_idx}, total={total}")
    if stride <= 0:
        raise ValueError(f"stride must be > 0, got {stride}")
    indices = list(range(start, end_idx, stride))
    if max_frames is not None and max_frames > 0:
        indices = indices[:max_frames]
    if not indices:
        raise ValueError("No frames selected with given start/end/stride/max-frames")
    return indices


def _build_gif_from_mp4(mp4_path: Path, gif_path: Path, fps: int) -> None:
    ffmpeg_bin = resolve_ffmpeg_bin()
    cmd = [
        ffmpeg_bin,
        "-y",
        "-i",
        str(mp4_path),
        "-vf",
        (
            f"fps={fps},scale=iw:-1:flags=lanczos,"
            "split[s0][s1];[s0]palettegen=max_colors=256[p];"
            "[s1][p]paletteuse=dither=bayer:bayer_scale=3"
        ),
        str(gif_path),
    ]
    subprocess.run(cmd, check=True)


def resolve_ffmpeg_bin() -> str | None:
    system_ffmpeg = shutil.which("ffmpeg")
    if system_ffmpeg:
        return system_ffmpeg
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return None


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    defaults = resolve_mode_defaults("seasonal")
    scale = args.scale or defaults["scale"]
    vmin = args.vmin if args.vmin is not None else defaults["vmin"]
    vmax = args.vmax if args.vmax is not None else defaults["vmax"]
    threshold = args.threshold if args.threshold is not None else vmin
    cmap_name = args.cmap or defaults["cmap"]
    validate_scale_args(scale, vmin, vmax)

    grid = parse_calmet_grid(args.met_inp)
    window = parse_calmet_run_window(args.met_inp)
    terrain_data = load_default_terrain(grid, args.conc_file, args.terrain_file)
    records = index_time_records(args.conc_file, grid.nx, grid.ny)
    frame_indices = _select_frame_indices(len(records), args.start_step, args.end_step, args.stride, args.max_frames)

    print(f"Grid: nx={grid.nx}, ny={grid.ny}, dgrid={grid.dgrid_km} km")
    print(f"MET window: {window.start:%Y-%m-%d %H:%M:%S} -> {window.end:%Y-%m-%d %H:%M:%S}")
    print(f"Detected timesteps: {len(records)}")
    print(
        f"Animation frames: {len(frame_indices)} "
        f"(start={frame_indices[0]}, end={frame_indices[-1]}, stride={args.stride})"
    )

    x_edges = grid.xorig_km + np.arange(grid.nx + 1) * grid.dgrid_km
    y_edges = grid.yorig_km + np.arange(grid.ny + 1) * grid.dgrid_km
    norm = LogNorm(vmin=vmin, vmax=vmax) if scale == "log" else Normalize(vmin=vmin, vmax=vmax)
    cmap = resolve_cmap(cmap_name)

    first_rec = records[frame_indices[0]]
    first_data = load_concentration_at_offset(args.conc_file, first_rec.data_offset, grid.nx, grid.ny)
    first_plot = _prepare_frame(first_data, scale, vmin, vmax, threshold)

    fig, ax = plt.subplots(figsize=(8.5, 7.8), constrained_layout=False)
    terrain_mesh = overlay_terrain(ax, grid, terrain_data)
    mesh = ax.pcolormesh(
        x_edges,
        y_edges,
        first_plot,
        shading="auto",
        cmap=cmap,
        norm=norm,
    )
    divider = make_axes_locatable(ax)
    conc_cax = divider.append_axes("right", size="2.8%", pad=0.12)
    terrain_cax = divider.append_axes("bottom", size="2.8%", pad=0.32)
    cbar = fig.colorbar(mesh, cax=conc_cax, extend="both", ticks=build_colorbar_ticks(scale, vmin, vmax))
    style_colorbar(cbar, scale, vmin, vmax)
    cbar.set_label("Concentration of tritium (Bq/m³)", fontsize=16, fontweight="bold")
    if terrain_mesh is not None:
        terrain_cbar = fig.colorbar(terrain_mesh, cax=terrain_cax, orientation="horizontal", extend="both")
        style_terrain_colorbar(terrain_cbar)

    ax.set_xlabel("")
    ax.set_ylabel("Y (km)")
    ax.set_aspect("equal")
    ax.grid(False)
    first_title = f"Concentration Animation\n{first_rec.start:%Y-%m-%d %H:%M} to {first_rec.end:%Y-%m-%d %H:%M}"
    ax.set_title(first_title)

    def update(frame_no: int):
        rec_idx = frame_indices[frame_no]
        rec = records[rec_idx]
        data = load_concentration_at_offset(args.conc_file, rec.data_offset, grid.nx, grid.ny)
        plot_data = _prepare_frame(data, scale, vmin, vmax, threshold)
        # Keep masked pixels masked, so animation uses the same threshold behavior as static plots.
        mesh.set_array(np.ma.asarray(plot_data).ravel())
        ax.set_title(f"Concentration Animation\n{rec.start:%Y-%m-%d %H:%M} to {rec.end:%Y-%m-%d %H:%M}")
        if frame_no % 100 == 0 or frame_no == len(frame_indices) - 1:
            print(f"Rendering frame: {frame_no + 1}/{len(frame_indices)}")
        return (mesh,)

    ani = animation.FuncAnimation(fig, update, frames=len(frame_indices), interval=max(1, int(1000 / args.fps)), blit=False)
    fig.subplots_adjust(left=0.09, right=0.90, top=0.91, bottom=0.11)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    suffix = args.out.suffix.lower()
    ffmpeg_bin = resolve_ffmpeg_bin()
    if ffmpeg_bin:
        plt.rcParams["animation.ffmpeg_path"] = ffmpeg_bin
    if suffix == ".gif":
        if ffmpeg_bin:
            tmp_mp4 = args.out.with_suffix(".tmp.mp4")
            mp4_writer = animation.FFMpegWriter(fps=args.fps, codec="h264", extra_args=["-pix_fmt", "yuv420p"])
            ani.save(tmp_mp4, writer=mp4_writer, dpi=args.dpi)
            _build_gif_from_mp4(tmp_mp4, args.out, args.fps)
            tmp_mp4.unlink(missing_ok=True)
        else:
            writer = animation.PillowWriter(fps=args.fps)
            ani.save(args.out, writer=writer, dpi=args.dpi)
    else:
        if not ffmpeg_bin:
            raise RuntimeError("ffmpeg not found; install ffmpeg/imageio-ffmpeg or choose GIF output.")
        writer = animation.FFMpegWriter(fps=args.fps, codec="h264", extra_args=["-pix_fmt", "yuv420p"])
        ani.save(args.out, writer=writer, dpi=args.dpi)
    plt.close(fig)
    print(f"Saved animation: {args.out}")


if __name__ == "__main__":
    main()
