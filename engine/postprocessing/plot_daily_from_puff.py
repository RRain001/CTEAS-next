from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path

from .extract_point_data import DEFAULT_CONC_FILE, DEFAULT_MET_INP, DEFAULT_OUTPUT_CSV, extract_point_time_series
from .plot_daily_concentration_fangda import DEFAULT_OUTPUT, plot_reference_style


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract a PUFF point time series and plot daily mean concentration.")
    parser.add_argument("--conc-file", type=Path, default=DEFAULT_CONC_FILE)
    parser.add_argument("--met-inp", "--calmet-inp", dest="met_inp", type=Path, default=DEFAULT_MET_INP)
    parser.add_argument("--x", type=float, required=True)
    parser.add_argument("--y", type=float, required=True)
    parser.add_argument("--csv-output", type=Path, default=DEFAULT_OUTPUT_CSV)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--no-interpolation", action="store_true")
    parser.add_argument("--start-time", type=str)
    parser.add_argument("--end-time", type=str)
    parser.add_argument("--normalize", action="store_true")
    args = parser.parse_args()

    start_time = datetime.strptime(args.start_time, "%Y-%m-%d %H:%M") if args.start_time else None
    end_time = datetime.strptime(args.end_time, "%Y-%m-%d %H:%M") if args.end_time else None
    extract_point_time_series(
        conc_file=args.conc_file,
        calmet_inp=args.met_inp,
        point_x_km=args.x,
        point_y_km=args.y,
        output_csv=args.csv_output,
        use_interpolation=not args.no_interpolation,
        start_time=start_time,
        end_time=end_time,
    )
    plot_reference_style(args.csv_output, args.output, value_column="concentration", normalize_to_mean=args.normalize)


if __name__ == "__main__":
    main()
