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


def commands(year: int, pstop: float, station_id: str | None, skip_download: bool,
             case_root: Path | None = None, upperair_root: Path | None = None,
             offline_archive_root: Path | None = None) -> list[list[str]]:
    if not 1900 <= year <= 2100:
        raise ValueError("year outside supported input interval")
    if not (0.0 < pstop <= 1500.0):
        raise ValueError("PSTOP must be within (0,1500] hPa")
    if station_id is not None and not station_id.strip():
        raise ValueError("empty station ID")
    if any((case_root, upperair_root, offline_archive_root)) and not all((case_root, upperair_root, offline_archive_root)):
        raise ValueError("isolated P4 requires case, upperair, and offline archive paths")
    if case_root and skip_download:
        raise ValueError("isolated P4 cannot skip annual source selection and >80% QA")
    steps: list[list[str]] = []
    if not skip_download:
        selection = ["--station-id", station_id] if station_id else ["--auto-select-all"]
        selection_cmd = [sys.executable, "-m", MODULE + ".download_igra",
                         "--year", str(year), "--pstop", str(pstop), *selection, "--yes"]
        if case_root:
            selection_cmd += ["--case-root", str(case_root), "--upperair-root", str(upperair_root),
                              "--offline-archive-root", str(offline_archive_root)]
        steps.append(selection_cmd)
    parse_cmd = [sys.executable, "-m", MODULE + ".parse_igra_to_csv",
                 "--year", str(year), "--pstop", str(pstop), "--yes"]
    read_cmd = [sys.executable, "-m", MODULE + ".read", "--year", str(year)]
    if upperair_root:
        parse_cmd += ["--upperair-root", str(upperair_root)]
        read_cmd += ["--upperair-root", str(upperair_root)]
    steps.extend((parse_cmd, read_cmd))
    return steps


def selected_years(year, research_time_file: Path | None = None):
    """Select per YEAR, never persist the first selected station across years."""
    if year is not None:
        return [year]
    from engine.core.paths import current_project_path
    research = (research_time_file or current_project_path("grid", "research_time")).read_text(encoding="utf-8")
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
    parser.add_argument("--case-root", type=Path)
    parser.add_argument("--upperair-root", type=Path)
    parser.add_argument("--offline-archive-root", type=Path)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    try:
        years = selected_years(args.year, args.case_root / "grid" / "research_time" if args.case_root else None)
        all_steps = [cmd for year in years
                     for cmd in commands(year, args.pstop, args.station_id, args.skip_download,
                                         args.case_root, args.upperair_root, args.offline_archive_root)]
    except (ValueError, FileNotFoundError) as exc:
        parser.error(str(exc))
    if args.execute:
        from engine.core.paths import current_project_path, engine_path
        root = args.case_root if args.case_root else current_project_path()
        if args.case_root and args.pstop != 500.0:
            parser.error("isolated P4 only supports original-parity PSTOP=500 hPa")
        required = [root / "grid" / "center_location", root / "grid" / "grid.cmn",
                    engine_path("resources", "igra", "igra2-station-list.txt")]
        if args.year is None:
            required.append(root / "grid" / "research_time")
        if args.skip_download:
            required += [(args.upperair_root if args.upperair_root else root / "met" / "upperair") / str(year)
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
