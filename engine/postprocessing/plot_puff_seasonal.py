from __future__ import annotations

import sys
from pathlib import Path

try:
    from ._core import (
        DEFAULT_CONC_FILE,
        DEFAULT_MET_INP,
        DEFAULT_POSTPROCESS_DIR,
        MEAN_DEFAULTS,
        common_parser,
        resolve_output_path,
        run_seasonal,
        validate_scale_args,
    )
except ImportError:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from _core import (
        DEFAULT_CONC_FILE,
        DEFAULT_MET_INP,
        DEFAULT_POSTPROCESS_DIR,
        MEAN_DEFAULTS,
        common_parser,
        resolve_output_path,
        run_seasonal,
        validate_scale_args,
    )


def main() -> None:
    parser = common_parser("Plot seasonal mean concentration from PUFF puff.con")
    args = parser.parse_args()

    scale = args.scale or MEAN_DEFAULTS["scale"]
    vmin = args.vmin if args.vmin is not None else MEAN_DEFAULTS["vmin"]
    vmax = args.vmax if args.vmax is not None else MEAN_DEFAULTS["vmax"]
    threshold = args.threshold if args.threshold is not None else MEAN_DEFAULTS["threshold"]
    cmap_name = args.cmap or MEAN_DEFAULTS["cmap"]
    try:
        validate_scale_args(scale, vmin, vmax)
    except ValueError as exc:
        parser.error(str(exc))

    saved = run_seasonal(
        conc_file=args.conc_file or DEFAULT_CONC_FILE,
        calmet_inp=args.met_inp or DEFAULT_MET_INP,
        out_png=resolve_output_path("seasonal", args.out, args.out_dir or DEFAULT_POSTPROCESS_DIR),
        scale=scale,
        vmin=vmin,
        vmax=vmax,
        threshold=threshold,
        cmap_name=cmap_name,
    )
    print(f"Saved: {saved}")


if __name__ == "__main__":
    main()
