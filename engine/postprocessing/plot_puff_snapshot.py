from __future__ import annotations

import argparse
import sys
from pathlib import Path

try:
    from ._core import (
        DEFAULT_CONC_FILE,
        DEFAULT_MET_INP,
        DEFAULT_POSTPROCESS_DIR,
        common_parser,
        resolve_mode_defaults,
        resolve_output_path,
        run_annual,
        run_seasonal,
        run_snapshot,
        validate_cli_args,
    )
except ImportError:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from _core import (
        DEFAULT_CONC_FILE,
        DEFAULT_MET_INP,
        DEFAULT_POSTPROCESS_DIR,
        common_parser,
        resolve_mode_defaults,
        resolve_output_path,
        run_annual,
        run_seasonal,
        run_snapshot,
        validate_cli_args,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = common_parser("Plot PUFF concentration in snapshot, annual, or seasonal mode")
    parser.add_argument("--mode", choices=["snapshot", "annual", "seasonal"], default="snapshot")
    parser.add_argument(
        "--time",
        type=str,
        default=None,
        help='Target start time for snapshot mode, format: "YYYY-MM-DD HH:MM"',
    )
    parser.add_argument(
        "--step",
        type=int,
        default=None,
        help="Timestep index for snapshot mode. Negative supports Python style, e.g. -1 for last step.",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    defaults = resolve_mode_defaults(args.mode)
    scale = args.scale or defaults["scale"]
    vmin = args.vmin if args.vmin is not None else defaults["vmin"]
    vmax = args.vmax if args.vmax is not None else defaults["vmax"]
    threshold = args.threshold if args.threshold is not None else defaults["threshold"]
    cmap_name = args.cmap or defaults["cmap"]
    conc_file = args.conc_file or DEFAULT_CONC_FILE
    met_inp = args.met_inp or DEFAULT_MET_INP
    out_dir = args.out_dir or DEFAULT_POSTPROCESS_DIR
    out_path = resolve_output_path(args.mode, args.out, out_dir)

    try:
        validate_cli_args(args.mode, args.time, args.step, scale, vmin, vmax)
    except ValueError as exc:
        parser.error(str(exc))

    if args.mode == "snapshot":
        saved = run_snapshot(
            conc_file=conc_file,
            calmet_inp=met_inp,
            out_png=out_path,
            scale=scale,
            vmin=vmin,
            vmax=vmax,
            threshold=threshold,
            cmap_name=cmap_name,
            terrain_file=args.terrain_file,
            when=args.time,
            step=args.step,
        )
    elif args.mode == "annual":
        saved = run_annual(
            conc_file=conc_file,
            calmet_inp=met_inp,
            out_png=out_path,
            scale=scale,
            vmin=vmin,
            vmax=vmax,
            threshold=threshold,
            cmap_name=cmap_name,
            terrain_file=args.terrain_file,
        )
    else:
        saved = run_seasonal(
            conc_file=conc_file,
            calmet_inp=met_inp,
            out_png=out_path,
            scale=scale,
            vmin=vmin,
            vmax=vmax,
            threshold=threshold,
            cmap_name=cmap_name,
            terrain_file=args.terrain_file,
        )

    print(f"Saved: {saved}")


if __name__ == "__main__":
    main()
