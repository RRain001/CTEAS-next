#!/usr/bin/env python3
"""Scoped P4 data preparation. Never executes the legacy READ62 binary."""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
MODULE = "native_cpp.modules.p4_read62.data_prep"


def commands(year: int, pstop: float, station_id: str | None, skip_download: bool) -> list[list[str]]:
    if not 1900 <= year <= 2100:
        raise ValueError("year outside supported input interval")
    if not (0.0 < pstop <= 1500.0):
        raise ValueError("PSTOP must be within (0,1500] hPa")
    if station_id is not None and not station_id.strip():
        raise ValueError("empty station ID")
    steps: list[list[str]] = []
    if not skip_download:
        selection = ["--station-id", station_id] if station_id else ["--auto-select-all"]
        steps.append([sys.executable, "-m", MODULE + ".download_igra",
                      "--year", str(year), "--pstop", str(pstop), *selection, "--yes"])
    steps.append([sys.executable, "-m", MODULE + ".parse_igra_to_csv",
                  "--year", str(year), "--pstop", str(pstop), "--yes"])
    steps.append([sys.executable, "-m", MODULE + ".read", "--year", str(year)])
    return steps


def selected_years(year):
    """Select per YEAR, never persist the first selected station across years."""
    if year is not None:
        return [year]
    from engine.core.paths import current_project_path
    research = current_project_path("grid", "research_time").read_text(encoding="utf-8")
    a = re.search(r"BEGIN\s*:\s*(\d{8})-\d{6}", research)
    b = re.search(r"END\s*:\s*(\d{8})-\d{6}", research)
    if not (a and b):
        raise ValueError("research_time BEGIN/END missing")
    first, last = int(a.group(1)[:4]), int(b.group(1)[:4])
    if first > last or first < 1900 or last > 2100:
        raise ValueError("invalid research_time years")
    return list(range(first, last + 1))


def main() -> int:
    parser = argparse.ArgumentParser(description="Year-by-year IGRA -> CSV -> FSL (no Fortran)")
    parser.add_argument("--year", type=int, help="Single year; default: research_time year span")
    parser.add_argument("--pstop", type=float, default=500.0)
    parser.add_argument("--station-id", help="Manually pick ONE station; quality rule still applies")
    parser.add_argument("--skip-download", action="store_true")
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    try:
        years = selected_years(args.year)
        all_steps = [cmd for year in years
                     for cmd in commands(year, args.pstop, args.station_id, args.skip_download)]
    except (ValueError, FileNotFoundError) as exc:
        parser.error(str(exc))
    if args.execute:
        from engine.core.paths import current_project_path, engine_path
        root = current_project_path()
        required = [root / "grid" / "center_location", root / "grid" / "grid.cmn",
                    engine_path("resources", "igra", "igra2-station-list.txt")]
        if args.year is None:
            required.append(root / "grid" / "research_time")
        if args.skip_download:
            required += [root / "met" / "upperair" / str(year)
                         / "upperair_station_used_list.txt" for year in years]
        missing = [str(p) for p in required if not p.is_file()]
        if missing:
            raise SystemExit("P4 missing case inputs:\n" + "\n".join(missing))
    for cmd in all_steps:
        print(" ".join(cmd), flush=True)
        if args.execute:
            subprocess.run(cmd, cwd=REPO_ROOT, check=True)
    print("P4_DRY_RUN_NO_WRITES" if not args.execute else
          f"P4_FSL_PREP_COMPLETE years={years}; no READ62 Fortran or UP.DAT")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
