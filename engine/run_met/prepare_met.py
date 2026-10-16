#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import os
import re
from pathlib import Path
from typing import Any

from engine.core.runtime_names import MET_DAT, MET_INP, MET_LST

from .common import (
    TEMPLATE_INP,
    case_paths,
    find_upperair_files,
    load_case_config_with_name,
    lon_lat_to_utm_km,
    parse_grid_cmn,
    parse_research_time,
    short_station_name,
)


def _replace_bang_var(text: str, var: str, value: str) -> str:
    pat = re.compile(rf"!\s*{re.escape(var)}\s*=\s*.*?!")
    return pat.sub(f"! {var} = {value} !", text)


def _rel_to(base_dir: Path, target: Path) -> str:
    return os.path.relpath(target.resolve(), start=base_dir.resolve())


def _station_mode_to_index(mode: str | None, station_id: str | None, station_ids: list[str]) -> int:
    normalized = (mode or "spatial").strip().lower()
    if normalized == "spatial":
        return -1
    if normalized == "station":
        if not station_id:
            raise ValueError("station mode requires station_id")
        try:
            return station_ids.index(str(station_id)) + 1
        except ValueError as exc:
            raise ValueError(f"station_id {station_id} not found in available stations: {station_ids}") from exc
    raise ValueError(f"Unsupported station selection mode: {mode}")


def _render_upperair_subgroup(text: str, upperair_files: list[Path], work_dir: Path) -> str:
    lines = text.splitlines()
    start = None
    subgroup_c = None
    header_idx = None
    separator_idx = None
    for i, line in enumerate(lines):
        if "Subgroup (b)" in line:
            start = i
        elif start is not None and header_idx is None and "------------  ----       ---------" in line:
            header_idx = i
        elif start is not None and header_idx is not None and separator_idx is None and line.strip().startswith("--------------------------------------------------------------------------------"):
            separator_idx = i
        elif start is not None and "Subgroup (c)" in line:
            subgroup_c = i
            break
    if start is None or header_idx is None or separator_idx is None or subgroup_c is None:
        raise RuntimeError("Cannot locate CALMET Subgroup (b) data boundaries")

    injected = []
    for idx, path in enumerate(upperair_files, start=1):
        injected.append(f"UP{idx}.DAT       input     {idx}  ! UPDAT={_rel_to(work_dir, path)} !    !END!")
    lines = lines[: header_idx + 1] + injected + lines[separator_idx:]
    return "\n".join(lines) + "\n"


def _replace_section(text: str, start_marker: str, end_marker: str, replacement: str) -> str:
    start = text.find(start_marker)
    if start == -1:
        raise RuntimeError(f"Cannot locate section start: {start_marker}")
    end = text.find(end_marker, start)
    if end == -1:
        raise RuntimeError(f"Cannot locate section end after: {start_marker}")
    return text[:start] + replacement.rstrip() + "\n\n" + text[end:]


def _station_coords_km(row: dict[str, str], grid: Any) -> tuple[float, float]:
    station_id = str(row.get("station_id", "?")).strip() or "?"
    if not str(row.get("lon", "")).strip() or not str(row.get("lat", "")).strip():
        raise ValueError(
            f"站点 {station_id} 缺少经纬度(lat/lon);stations.csv 元数据不完整。"
            "请确认下载步骤已生成 met/surface/isd_raw/surf_station_list_*.txt,且其中包含该站。"
        )
    try:
        lon = float(row["lon"])
        lat = float(row["lat"])
    except ValueError as error:
        raise ValueError(
            f"站点 {station_id} 的经纬度不是数值: lon={row['lon']!r}, lat={row['lat']!r}"
        ) from error
    return lon_lat_to_utm_km(lon, lat, grid.iutmzn, grid.lsohem == "N")


def _render_surface_group(surface_rows: list[dict[str, str]], grid: Any) -> str:
    data_lines = []
    for idx, row in enumerate(surface_rows, start=1):
        x_km, y_km = _station_coords_km(row, grid)
        name = short_station_name(row.get("station_name"), row["station_id"])
        tz_hour = int(float(row.get("tz_hour", "0") or "0"))
        anem_m = float(row.get("anem_m", "10.0") or "10.0")
        data_lines.append(
            f"! SS{idx:<2d} ='{name}'    {int(row['station_id']):6d}    {x_km:10.3f}    {y_km:10.3f}   {tz_hour:2d}   {anem_m:4.1f} !"
        )

    section = f"""INPUT GROUP: 7 -- Surface meteorological station parameters
--------------

     SURFACE STATION VARIABLES
     (One record per station -- {len(surface_rows):2d} records in all)


             1     2
         Name   ID            X coord.   Y coord.   Time   Anem.
                               (km)       (km)      zone   Ht.(m)
       ----------------------------------------------------------
{chr(10).join(data_lines)}
-------------------
      1
        Four character string for station name
        (MUST START IN COLUMN 9)

      2
        Six digit integer for station ID

!END!


-------------------------------------------------------------------------------"""
    return section


def _render_upperair_group(upperair_rows: list[dict[str, str]], grid: Any) -> str:
    data_lines = []
    for idx, row in enumerate(upperair_rows, start=1):
        x_km, y_km = _station_coords_km(row, grid)
        name = short_station_name(row.get("station_name"), row["station_id"])
        tz_hour = int(float(row.get("tz_hour", "0") or "0"))
        data_lines.append(
            f"! US{idx:<2d} ='{name}'   {int(row['station_id']):5d}    {x_km:10.3f}   {y_km:10.3f}   {tz_hour:2d} !"
        )

    section = f"""INPUT GROUP: 8 -- Upper air meteorological station parameters
--------------

     UPPER AIR STATION VARIABLES
     (One record per station -- {len(upperair_rows):2d} records in all)

             1     2
         Name    ID      X coord.   Y coord.  Time zone
                           (km)       (km)    
        -----------------------------------------------
{chr(10).join(data_lines)}
-------------------
      1
        Four character string for station name
        (MUST START IN COLUMN 9)

      2
        Five digit integer for station ID

!END!


-------------------------------------------------------------------------------"""
    return section


def render_met_inp(case_name: str, config: dict[str, Any], work_dir: Path) -> tuple[str, dict[str, Any]]:
    paths = case_paths(
        config,
        case_name,
        required=["geo_makegeo_dir", "met_surface_dir", "met_upperair_dir", "run_met_dir"],
    )
    grid = parse_grid_cmn(case_name)
    begin_dt, end_dt = parse_research_time(case_name)

    geo_dat = paths["geo_makegeo_dir"] / "geo.dat"
    surf_dat = paths["met_surface_dir"] / "final" / "surf.dat"
    surface_stations_csv = paths["met_surface_dir"] / "final" / "stations.csv"
    upperair_final_dir = paths["met_upperair_dir"] / "final"
    upperair_stations_csv = upperair_final_dir / "stations.csv"
    upperair_files = find_upperair_files(upperair_final_dir)

    required_files = [geo_dat, surf_dat, surface_stations_csv, upperair_stations_csv]
    missing = [str(path) for path in required_files if not path.exists()]
    if missing:
        raise FileNotFoundError(f"Required CALMET inputs missing: {', '.join(missing)}")

    with surface_stations_csv.open("r", encoding="utf-8", newline="") as f:
        surface_rows = list(csv.DictReader(f))
    with upperair_stations_csv.open("r", encoding="utf-8", newline="") as f:
        upperair_rows = list(csv.DictReader(f))

    met_cfg = config.get("met", {})
    station_cfg = met_cfg.get("station_selection", {})
    options = met_cfg.get("options", {})

    if not surface_rows:
        raise ValueError(f"No surface stations found in: {surface_stations_csv}")
    if not upperair_files:
        raise ValueError(f"No upperair files found in: {upperair_final_dir}")
    if not upperair_rows:
        raise ValueError(f"No upperair station metadata found in: {upperair_stations_csv}")

    surface_ids = [row["station_id"] for row in surface_rows]
    upperair_ids = [row["station_id"] for row in upperair_rows]

    file_station_ids = [path.stem.split("_", 1)[1] for path in upperair_files]
    if upperair_ids != file_station_ids:
        raise ValueError(
            "Upperair station metadata order does not match final up_*.dat files: "
            f"{upperair_ids} vs {file_station_ids}"
        )

    isurft = _station_mode_to_index(station_cfg.get("isurft_mode"), station_cfg.get("isurft_station_id"), surface_ids)
    iupt = _station_mode_to_index(station_cfg.get("iupt_mode"), station_cfg.get("iupt_station_id"), upperair_ids)
    iupwnd = -1 if (station_cfg.get("iupwnd_mode") or "spatial").strip().lower() == "spatial" else _station_mode_to_index(
        "station", station_cfg.get("iupwnd_station_id"), upperair_ids
    )

    values = {
        "GEODAT": _rel_to(work_dir, geo_dat),
        "SRFDAT": _rel_to(work_dir, surf_dat),
        "METLST": MET_LST,
        "METDAT": MET_DAT,
        "LCFILES": "T" if options.get("lcfiles", True) else "F",
        "NUSTA": str(len(upperair_files)),
        "NOWSTA": "0",
        "NM3D": "0",
        "NIGF": "0",
        "IBYR": str(begin_dt.year),
        "IBMO": str(begin_dt.month),
        "IBDY": str(begin_dt.day),
        "IBHR": str(begin_dt.hour),
        "IBSEC": str(begin_dt.second),
        "IEYR": str(end_dt.year),
        "IEMO": str(end_dt.month),
        "IEDY": str(end_dt.day),
        "IEHR": str(end_dt.hour),
        "IESEC": str(end_dt.second),
        "ABTZ": config.get("settings", {}).get("timezone", "UTC+0000"),
        "IRTYPE": str(options.get("irtype", 1)),
        "LCALGRD": "T" if options.get("lcalgrd", True) else "F",
        "PMAP": grid.imap,
        "IUTMZN": str(grid.iutmzn),
        "UTMHEM": grid.lsohem,
        "DATUM": grid.datum,
        "NX": str(grid.nx),
        "NY": str(grid.ny),
        "DGRIDKM": f"{grid.dgridkm:g}",
        "XORIGKM": f"{grid.xrefkm:.3f}",
        "YORIGKM": f"{grid.yrefkm:.3f}",
        "NZ": str(grid.nz),
        "ZFACE": ",".join(f"{z:g}" for z in grid.zfaces),
        "LSAVE": "T" if options.get("lsave", True) else "F",
        "LPRINT": "T" if options.get("lprint", False) else "F",
        "NOOBS": str(options.get("noobs", 0)),
        "NSSTA": str(len(surface_rows)),
        "NPSTA": str(options.get("npsta", 0)),
        "ICLOUD": str(options.get("icloud", 0)),
        "IFORMS": str(options.get("iforms", 2)),
        "IFORMP": str(options.get("iformp", 2)),
        "IFORMC": str(options.get("iformc", 2)),
        "IWFCOD": str(options.get("iwfcod", 1)),
        "IFRADJ": str(options.get("ifradj", 1)),
        "IKINE": str(options.get("ikine", 0)),
        "IOBR": str(options.get("iobr", 0)),
        "IDIOPT1": "0",
        "ISURFT": str(isurft),
        "IDIOPT2": "0",
        "IUPT": str(iupt),
        "IDIOPT3": "0",
        "IUPWND": str(iupwnd),
    }

    rendered = TEMPLATE_INP.read_text(encoding="utf-8", errors="ignore")
    for key, value in values.items():
        rendered = _replace_bang_var(rendered, key, value)
    rendered = _render_upperair_subgroup(rendered, upperair_files, work_dir)
    rendered = _replace_section(
        rendered,
        "INPUT GROUP: 7 -- Surface meteorological station parameters",
        "INPUT GROUP: 8 -- Upper air meteorological station parameters",
        _render_surface_group(surface_rows, grid),
    )
    rendered = _replace_section(
        rendered,
        "INPUT GROUP: 8 -- Upper air meteorological station parameters",
        "INPUT GROUP: 9 -- Precipitation station parameters",
        _render_upperair_group(upperair_rows, grid),
    )
    return rendered, {
        "geo_dat": geo_dat,
        "surf_dat": surf_dat,
        "surface_stations_csv": surface_stations_csv,
        "upperair_stations_csv": upperair_stations_csv,
        "upperair_files": upperair_files,
        "nssta": len(surface_rows),
        "nusta": len(upperair_files),
        "isurft": isurft,
        "iupt": iupt,
        "iupwnd": iupwnd,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Render CALMET input file from current case metadata")
    ap.add_argument("--case", help="Case name under project/cases; defaults to project/current")
    ap.add_argument("--output", help="Override output path; default project/current/run/met/met.inp")
    args = ap.parse_args()

    case_name, config = load_case_config_with_name(args.case)
    work_dir = case_paths(config, case_name, required=["run_met_dir"])["run_met_dir"]
    work_dir.mkdir(parents=True, exist_ok=True)
    output = Path(args.output).resolve() if args.output else (work_dir / MET_INP)

    rendered, summary = render_met_inp(case_name, config, work_dir)
    output.write_text(rendered, encoding="utf-8")

    print(f"Rendered CALMET input: {output}")
    print(f"Surface stations: {summary['nssta']}, upperair files: {summary['nusta']}")
    print(f"ISURFT={summary['isurft']} IUPT={summary['iupt']} IUPWND={summary['iupwnd']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
