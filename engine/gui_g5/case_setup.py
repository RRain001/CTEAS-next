"""G5 case setup independent of the legacy preprocessing runner.

Creates case metadata and a published WGS-84 UTM grid; does not run vendor
Fortran or claim native P1-P7 calculations.
"""
from __future__ import annotations

import argparse
import math
import re
from pathlib import Path

import yaml

from engine.core.paths import CASES_ROOT
from engine.preprocess.grid.configure_grid_cmn import lon_lat_to_utm
from engine.run_met.common import lon_lat_to_utm_km

DEFAULT_LON = 117.0
DEFAULT_LAT = 32.0
DEFAULT_NZ = 9
DEFAULT_FACES = (0, 20, 40, 80, 160, 320, 640, 1200, 2000, 3000)


def initial_config(case_name: str) -> dict:
    return {
        "schema_version": 1,
        "case_name": case_name,
        "paths": {
            "grid_dir": "project/current/grid",
            "met_surface_dir": "project/current/met/surface",
            "met_upperair_dir": "project/current/met/upperair",
            "geo_ctgproc_dir": "project/current/geo/ctgproc",
            "geo_terrel_dir": "project/current/geo/terrel",
            "geo_makegeo_dir": "project/current/geo/makegeo",
            "run_met_dir": "project/current/run/met",
            "run_puff_dir": "project/current/run/puff",
            "run_read62_dir": "project/current/run/read62",
            "run_smerge_dir": "project/current/run/smerge",
        },
        "settings": {"timezone": "UTC+0000", "pstop_hpa_default": 500},
        "preprocess": {
            "stack": {"longitude": DEFAULT_LON, "latitude": DEFAULT_LAT},
            "grid": {
                "center": {"longitude": DEFAULT_LON, "latitude": DEFAULT_LAT},
                "domain": {"length_km": 50, "width_km": 50},
                "resolution_km": 1, "nz": DEFAULT_NZ,
                "vertical_levels_m": list(DEFAULT_FACES[1:]),
            },
            "research_time": {"begin": "20230101-000000", "end": "20231231-230000"},
            "upperair": {"pstop_hpa": 500, "auto_select_all": True},
            "surface": {"skip_download": False},
        },
        "met": {"station_selection": {
            "isurft_mode": "spatial", "iupt_mode": "spatial", "iupwnd_mode": "spatial"
        }, "options": {"npsta": 0, "noobs": 0}},
        "puff": {"options": {"source_mode": "case_yaml", "nspec": 2, "nse": 1},
                 "point_sources": []},
    }



def projected_stack_utm_km(data: dict) -> tuple[float, float]:
    """Project the source with the EDITED grid-centre UTM zone, not stale grid.cmn."""
    pre = data["preprocess"]
    center = pre["grid"]["center"]
    source = pre["stack"]
    zone, _, _ = lon_lat_to_utm(
        float(center["longitude"]), float(center["latitude"]))
    return lon_lat_to_utm_km(
        float(source["longitude"]), float(source["latitude"]), zone,
        float(center["latitude"]) >= 0)


def write_case_grid(root: Path, data: dict) -> None:
    grid = data["preprocess"]["grid"]
    center = grid["center"]
    zone, x_m, y_m = lon_lat_to_utm(
        float(center["longitude"]), float(center["latitude"]))
    # This function returns zone and metric positions; keep 0.001 km published origin.
    length = float(grid["domain"]["length_km"])
    width = float(grid["domain"]["width_km"])
    spacing = float(grid["resolution_km"])
    nx, ny = math.ceil(length / spacing), math.ceil(width / spacing)
    xref = round(x_m / 1000 - length / 2, 3)
    yref = round(y_m / 1000 - width / 2, 3)
    hemi = "N" if float(center["latitude"]) >= 0 else "S"
    nz = int(grid["nz"])
    if nz <= 0:
        raise ValueError("G5 NZ must be positive")
    vertical = [float(v) for v in grid.get("vertical_levels_m", [])]
    if len(vertical) != nz:
        raise ValueError("G5 vertical_levels_m length must equal NZ")
    if any(not math.isfinite(z) or z <= 0 for z in vertical):
        raise ValueError("G5 model vertical faces must be finite and positive")
    if any(a >= b for a, b in zip(vertical, vertical[1:])):
        raise ValueError("G5 vertical faces must strictly increase")
    faces = (0.0, *vertical)
    lines = [
        "! IMAP = UTM !", f"! IUTMZN = {zone} !",
        f"! LSOHEM = {hemi} !", "! DATUM = WGS-84 !",
        f"! XREFKM = {xref:.3f} !", f"! YREFKM = {yref:.3f} !",
        f"! DGRIDKM = {spacing:g} !", f"! NX = {nx} !", f"! NY = {ny} !",
        f"! NZ = {nz} !",
        *(f"! ZFACE = {z:g} !" for z in faces),
    ]
    out = root / "grid"
    out.mkdir(parents=True, exist_ok=True)
    (out / "grid.cmn").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (out / "center_location").write_text(
        f"longitude:{center['longitude']}\nlatitude:{center['latitude']}\n", encoding="utf-8")
    (out / "stack_location").write_text(
        f"longitude:{data['preprocess']['stack']['longitude']}\n"
        f"latitude:{data['preprocess']['stack']['latitude']}\n", encoding="utf-8")
    t = data["preprocess"]["research_time"]
    (out / "research_time").write_text(
        f"BEGIN:{t['begin']}\nEND:{t['end']}\n", encoding="utf-8")


def create_case(case_name: str) -> Path:
    if not re.fullmatch(r"[A-Za-z0-9_-]+", case_name):
        raise ValueError("case_name must contain only letters, digits, underscore or hyphen")
    root = CASES_ROOT / case_name
    if root.exists():
        raise FileExistsError(f"Case already exists: {root}")
    root.mkdir(parents=True, exist_ok=False)
    config = initial_config(case_name)
    (root / "case.yaml").write_text(
        yaml.safe_dump(config, allow_unicode=True, sort_keys=False), encoding="utf-8")
    write_case_grid(root, config)
    for rel in ("met/upperair", "met/surface", "geo/terrel", "geo/ctgproc",
                "geo/makegeo", "run/met", "run/puff", "runs"):
        (root / rel).mkdir(parents=True, exist_ok=True)
    return root


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Create a G5 case with isolated native routing")
    ap.add_argument("case_name")
    args = ap.parse_args(argv)
    print(create_case(args.case_name))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
