#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import re
from pathlib import Path
from typing import Any

from engine.core.runtime_names import MET_DAT, PUFF_CON, PUFF_DRY, PUFF_INP, PUFF_LST, PUFF_VIS, PUFF_WET

from engine.core.paths import case_dir
from engine.preprocess.grid.center_location_to_utm import convert_lon_lat

from .common import PUFF_TEMPLATE_FALLBACK, case_paths, load_case_config_with_name, parse_research_time


def _replace_bang_var(text: str, var: str, value: str) -> str:
    pat = re.compile(rf"!\s*{re.escape(var)}\s*=\s*.*?!")
    return pat.sub(f"! {var} ={value} !", text)


def _rel_to(base_dir: Path, target: Path) -> str:
    return os.path.relpath(target.resolve(), start=base_dir.resolve())


def _parse_grid_kv(path: Path) -> dict[str, Any]:
    kv: dict[str, Any] = {}
    zfaces: list[float] = []
    pattern = re.compile(r"^\s*[!*]\s*([A-Z0-9_]+)\s*=\s*(.*?)\s*[!*]\s*$")
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        m = pattern.match(line)
        if not m:
            continue
        key = m.group(1).strip().upper()
        value = m.group(2).strip()
        if key == "ZFACE":
            zfaces.append(float(value))
        else:
            kv[key] = value
    kv["ZFACE"] = zfaces
    return kv


def _xbtz_to_abtz(xbtz_str: str | None, default: str = "UTC+0000") -> str:
    if xbtz_str is None:
        return default
    hours = int(float(xbtz_str))
    sign = "+" if hours >= 0 else "-"
    return f"UTC{sign}{abs(hours):02d}00"


def _extract_bang_float(text: str, key: str) -> float | None:
    m = re.search(rf"!\s*{re.escape(key)}\s*=\s*([-+0-9.Ee]+)\s*!", text)
    return float(m.group(1)) if m else None


def _extract_cspec_names(text: str) -> list[str]:
    return re.findall(r"!\s*CSPEC\s*=\s*([A-Za-z0-9_.+\-]+)\s*!\s*!END!", text)


def _shift_point_source_xy(text: str, dx: float, dy: float) -> str:
    pattern = re.compile(r"(!\s*X\s*=\s*)([-+0-9.Ee]+)(\s*,\s*)([-+0-9.Ee]+)", flags=re.IGNORECASE)

    def repl(m: re.Match[str]) -> str:
        x_old = float(m.group(2))
        y_old = float(m.group(4))
        x_new = x_old + dx
        y_new = y_old + dy
        return f"{m.group(1)}{x_new:10.3f}{m.group(3)}{y_new:10.3f}"

    return pattern.sub(repl, text)


def _replace_section(text: str, start_marker: str, end_marker: str, replacement: str) -> str:
    start = text.find(start_marker)
    if start == -1:
        raise RuntimeError(f"Cannot locate section start: {start_marker}")
    end = text.find(end_marker, start)
    if end == -1:
        raise RuntimeError(f"Cannot locate section end after: {start_marker}")
    return text[:start] + replacement.rstrip() + "\n\n" + text[end:]


def _clear_decay_block_if_disabled(text: str, ndecay: int) -> str:
    if ndecay != 0:
        return text
    # In Subgroup (11b), when NDECAY=0 there must be no decay assignment blocks.
    # Remove sample parent/child assignment lines and their block terminator.
    start = text.find("Subgroup (11b)")
    if start == -1:
        return text
    end = text.find("INPUT GROUP: 12", start)
    if end == -1:
        return text
    section = text[start:end]
    section = re.sub(r"\s*!\s*[A-Za-z0-9_.+\-]+\s*=.*?(?:\n|$)", "\n", section)
    section = re.sub(r"\s*!\s*END\s*!\s*(?:\n|$)", "\n", section)
    return text[:start] + section + text[end:]


def _ensure_template_decay_block(text: str, ndecay: int, species: list[str]) -> str:
    start = text.find("Subgroup (11b)")
    if start == -1:
        return text
    end = text.find("INPUT GROUP: 12", start)
    if end == -1:
        return text
    section = text[start:end]
    # Normalize section by removing any existing decay assignment rows and block terminators.
    section = re.sub(r"\s*!\s*[A-Za-z0-9_.+\-]+\s*=.*?(?:\n|$)", "\n", section)
    section = re.sub(r"\s*!\s*END\s*!\s*(?:\n|$)", "\n", section)
    if ndecay <= 0:
        return text[:start] + section + text[end:]

    parent = species[0] if species else "H-3"
    child = species[1] if len(species) > 1 else "HE-3"
    block = (
        f"   !          {parent} = 388523520.0,   -1.0    !    (Parent)\n"
        f"   !         {child} =   -1.0, 1.0 !    (Child)\n"
        "   !END!\n"
    )
    m = re.search(r"\n--------\s*\n\s*a\s*\n", section)
    if m:
        pos = m.start() + 1
        section = section[:pos] + block + section[pos:]
    else:
        sep = section.find("-------------------------------------------------------------------------------")
        if sep == -1:
            return text
        section = section[:sep] + block + section[sep:]
    return text[:start] + section + text[end:]


def _read_center_lon_lat(path: Path) -> tuple[float, float]:
    lon = None
    lat = None
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if line.lower().startswith("longitude:"):
            lon = float(line.split(":", 1)[1].strip())
        elif line.lower().startswith("latitude:"):
            lat = float(line.split(":", 1)[1].strip())
    if lon is None or lat is None:
        raise ValueError(f"Invalid center_location file: {path}")
    return lon, lat


def _default_point_source(nspec: int) -> dict[str, Any]:
    emissions = [0.0] * nspec
    if nspec > 0:
        emissions[0] = 1.2345e05
    return {
        "name": "P1",
        "x_km": 123.456,
        "y_km": 1234.567,
        "stack_height_m": 50.0,
        "base_elev_m": 0.0,
        "stack_diameter_m": 2.0,
        "exit_velocity_mps": 11.11,
        "exit_temp_k": 293.0,
        "building_downwash_flag": 0.0,
        "zpltfm_m": 0.0,
        "fmfac": 1.0,
        "emissions": emissions,
    }


def _center_location_point_source(nspec: int, grid: dict[str, Any], grid_dir: Path) -> dict[str, Any]:
    lon, lat = _read_center_lon_lat(grid_dir / "center_location")
    conv = convert_lon_lat(lon, lat)
    expected_zone = int(float(grid.get("IUTMZN", 0)))
    expected_hem = str(grid.get("LSOHEM", "N")).upper()
    if int(conv["zone"]) != expected_zone or str(conv["hemisphere"]).upper() != expected_hem:
        raise ValueError(
            f"center_location UTM zone/hemisphere mismatch: "
            f"center={conv['zone']}{conv['hemisphere']} grid={expected_zone}{expected_hem}"
        )
    src = _default_point_source(nspec)
    src["x_km"] = float(conv["x_km"])
    src["y_km"] = float(conv["y_km"])
    return src


def _normalize_point_sources(puff_cfg: dict[str, Any], nspec: int, grid: dict[str, Any], grid_dir: Path) -> list[dict[str, Any]]:
    center_lon, center_lat = _read_center_lon_lat(grid_dir / "center_location")
    center_conv = convert_lon_lat(center_lon, center_lat)
    expected_zone = int(float(grid.get("IUTMZN", 0)))
    expected_hem = str(grid.get("LSOHEM", "N")).upper()

    raw_sources = puff_cfg.get("point_sources", [])
    if not raw_sources:
        return [_default_point_source(nspec)]

    out: list[dict[str, Any]] = []
    for i, src in enumerate(raw_sources, start=1):
        norm = dict(src)

        has_xy = ("x_km" in norm and "y_km" in norm)
        has_lonlat = ("longitude" in norm and "latitude" in norm)

        if has_lonlat:
            conv = convert_lon_lat(float(norm["longitude"]), float(norm["latitude"]))
            if int(conv["zone"]) != expected_zone or str(conv["hemisphere"]).upper() != expected_hem:
                raise ValueError(
                    f"Point source {norm.get('name', i)} UTM zone/hemisphere mismatch: "
                    f"source={conv['zone']}{conv['hemisphere']} grid={expected_zone}{expected_hem}"
                )
            norm["x_km"] = float(conv["x_km"])
            norm["y_km"] = float(conv["y_km"])
        elif not has_xy:
            norm["x_km"] = float(center_conv["x_km"])
            norm["y_km"] = float(center_conv["y_km"])

        norm.setdefault("name", f"STK{i}")
        norm.setdefault("stack_height_m", 40.0)
        norm.setdefault("base_elev_m", 0.0)
        norm.setdefault("stack_diameter_m", 3.0)
        norm.setdefault("exit_velocity_mps", 5.0)
        norm.setdefault("exit_temp_k", 355.0)
        norm.setdefault("building_downwash_flag", 0.0)
        norm.setdefault("zpltfm_m", 0.0)
        norm.setdefault("fmfac", 1.0)
        norm.setdefault("emissions", [0.0] * nspec)
        out.append(norm)
    return out


def _fmt_src_line(idx: int, src: dict[str, Any], nspec_emis: list[float], dx: float, dy: float) -> str:
    x = float(src["x_km"]) + dx
    y = float(src["y_km"]) + dy
    vals = [
        x,
        y,
        float(src["stack_height_m"]),
        float(src["base_elev_m"]),
        float(src["stack_diameter_m"]),
        float(src["exit_velocity_mps"]),
        float(src["exit_temp_k"]),
        float(src.get("building_downwash_flag", 0.0)),
    ] + [float(v) for v in nspec_emis]
    first8 = ", ".join(f"{v:.3f}" for v in vals[:8])
    emis = ",  ".join(f"{v:.3E}" for v in vals[8:])
    x_line = f"{first8}, {emis}" if emis else first8
    return (
        f"   {idx} ! SRCNAM = {src['name']} !\n"
        f"   {idx} ! X = {x_line} !\n"
        f"   {idx} ! ZPLTFM  = {float(src.get('zpltfm_m', 0.0)):.1f} !\n"
        f"   {idx} ! FMFAC  = {float(src.get('fmfac', 1.0)):.1f} !   !END!"
    )


def _render_point_sources(text: str, sources: list[dict[str, Any]], nspec: int, dx: float, dy: float) -> str:
    block_lines: list[str] = []
    for i, src in enumerate(sources, start=1):
        emis = src.get("emissions", [])
        if len(emis) != nspec:
            raise ValueError(f"Point source {src.get('name')} emissions length must be NSPEC={nspec}")
        block_lines.append(_fmt_src_line(i, src, emis, dx, dy))
        block_lines.append("")
    start_m = re.search(r"(?im)^Subgroup \(13b\)\s*$", text)
    if not start_m:
        raise RuntimeError("Cannot locate Subgroup (13b)")
    end_m = re.search(r"(?im)^Subgroup \(13c\)\s*$", text[start_m.end() :])
    if not end_m:
        raise RuntimeError("Cannot locate Subgroup (13c)")
    sec_start = start_m.end()
    sec_end = start_m.end() + end_m.start()
    section = text[sec_start:sec_end]

    data_start = re.search(r"(?im)^\s*\d+\s*!\s*SRCNAM\s*=", section)
    if not data_start:
        raise RuntimeError("Cannot locate point-source data rows in Subgroup (13b)")
    data_end = re.search(r"(?im)^\s*--------\s*$", section[data_start.start() :])
    if not data_end:
        raise RuntimeError("Cannot locate Subgroup (13b) notes separator")

    i0 = data_start.start()
    i1 = data_start.start() + data_end.start()
    new_data = "\n".join(block_lines).rstrip() + "\n\n"
    new_section = section[:i0] + new_data + section[i1:]
    return text[:sec_start] + new_section + text[sec_end:]


def render_puff_inp(case_name: str, config: dict[str, Any], work_dir: Path) -> tuple[str, dict[str, Any]]:
    paths = case_paths(config, case_name, required=["grid_dir", "run_met_dir", "run_puff_dir"])
    begin_dt, end_dt = parse_research_time(case_name)
    grid_dir = paths["grid_dir"]
    grid = _parse_grid_kv(grid_dir / "grid.cmn")

    template_candidates = [
        work_dir / "puff_7.0.inp",
        PUFF_TEMPLATE_FALLBACK,
        work_dir / PUFF_INP,
    ]
    template_path = next((p for p in template_candidates if p.exists()), None)
    if template_path is None:
        raise FileNotFoundError("No CALPUFF input template found")

    text = template_path.read_text(encoding="utf-8", errors="ignore")
    tpl_xorig = _extract_bang_float(text, "XORIGKM")
    tpl_yorig = _extract_bang_float(text, "YORIGKM")
    tpl_species = _extract_cspec_names(text)
    puff_cfg = config.get("puff", {})
    opts = puff_cfg.get("options", {})
    source_mode = str(opts.get("source_mode", "center_location")).strip().lower()
    nspec = int(opts.get("nspec", 7))
    mchem = int(opts.get("mchem", 0))
    idry = int(opts.get("idry", 0))
    iwet = int(opts.get("iwet", 0))
    ndecay = int(opts.get("ndecay", 1))
    metrun = int(opts.get("metrun", 0))
    nx = int(float(grid.get("NX", 1)))
    ny = int(float(grid.get("NY", 1)))
    if source_mode == "template_defaults":
        point_sources = [_default_point_source(nspec)]
    elif source_mode == "center_location":
        point_sources = [_center_location_point_source(nspec, grid, grid_dir)]
    elif source_mode == "case_yaml":
        point_sources = _normalize_point_sources(puff_cfg, nspec, grid, grid_dir)
    else:
        raise ValueError(f"Unsupported puff.options.source_mode: {source_mode}")

    if tpl_species and nspec != len(tpl_species):
        raise ValueError(
            f"Invalid PUFF config: NSPEC={nspec} but template has {len(tpl_species)} CSPEC entries {tpl_species}. "
            "Please keep NSPEC consistent with template species, or edit template species blocks first."
        )

    if nspec == 1 and ndecay > 0:
        raise ValueError(
            "Invalid PUFF config: NSPEC=1 with NDECAY>0. "
            "For H-3 decay, HE-3 must be included as child species, or set ndecay=0."
        )

    metdat = case_dir(case_name) / "deliverables" / "met" / MET_DAT
    values = {
        "METDAT": _rel_to(work_dir, metdat),
        "PUFLST": PUFF_LST,
        "CONDAT": PUFF_CON,
        "DFDAT": PUFF_DRY,
        "WFDAT": PUFF_WET,
        "VISDAT": PUFF_VIS,
        "LCFILES": "T" if opts.get("lcfiles", True) else "F",
        "MOZ": str(int(opts.get("moz", 0))),
        "ABTZ": _xbtz_to_abtz(grid.get("XBTZ"), config.get("settings", {}).get("timezone", "UTC+0000")),
        "PMAP": str(grid.get("IMAP", "UTM")).upper(),
        "IUTMZN": str(int(float(grid.get("IUTMZN", 0)))),
        "UTMHEM": str(grid.get("LSOHEM", "N")).upper(),
        "DATUM": str(grid.get("DATUM", "WGS-84")).upper(),
        "NX": str(nx),
        "NY": str(ny),
        "NZ": str(int(float(grid.get("NZ", 1)))),
        "DGRIDKM": f"{float(grid.get('DGRIDKM', 1.0)):g}",
        "XORIGKM": f"{float(grid.get('XREFKM', 0.0)):.3f}",
        "YORIGKM": f"{float(grid.get('YREFKM', 0.0)):.3f}",
        "NREC": str(int(opts.get("nrec", 0))),
        "NRGRP": str(int(opts.get("nrgrp", 0))),
        "NSPEC": str(nspec),
        "NSE": str(int(opts.get("nse", min(4, nspec)))),
        "METRUN": str(metrun),
        "MCHEM": str(mchem),
        "IDRY": str(idry),
        "IWET": str(iwet),
        "NDECAY": str(ndecay),
        "NPT1": str(len(point_sources)) if point_sources else str(int(opts.get("npt1", 0))),
        "NPT2": "0",
        "NSPT1": str(int(opts.get("nspt1", 0))),
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
        "IBCOMP": "1",
        "JBCOMP": "1",
        "IECOMP": str(nx),
        "JECOMP": str(ny),
        "IBSAMP": "1",
        "JBSAMP": "1",
        "IESAMP": str(nx),
        "JESAMP": str(ny),
    }
    for key, value in values.items():
        text = _replace_bang_var(text, key, value)
    text = _clear_decay_block_if_disabled(text, ndecay=ndecay)
    text = _ensure_template_decay_block(text, ndecay=ndecay, species=tpl_species)
    zfaces = grid.get("ZFACE", [])
    if zfaces:
        zface_str = ", ".join(f"{float(z):g}" for z in zfaces)
        text = re.sub(r"!\s*ZFACE\s*=\s*.*?!", f"! ZFACE = {zface_str} !", text)
    if tpl_xorig is not None and tpl_yorig is not None:
        dx = float(values["XORIGKM"]) - tpl_xorig
        dy = float(values["YORIGKM"]) - tpl_yorig
        if point_sources:
            # template_defaults: keep template-like source parameters, but shift with grid origin
            # so placeholders remain inside the current computational grid.
            render_dx = dx if source_mode == "template_defaults" else 0.0
            render_dy = dy if source_mode == "template_defaults" else 0.0
            # case_yaml: YAML coordinates are treated as final met-grid km coordinates.
            text = _render_point_sources(text, point_sources, nspec=nspec, dx=render_dx, dy=render_dy)
        else:
            text = _shift_point_source_xy(text, dx=dx, dy=dy)

    summary = {
        "template_path": str(template_path),
        "metdat": values["METDAT"],
        "puflst": values["PUFLST"],
        "condat": values["CONDAT"],
        "source_mode": source_mode,
        "period": f"{begin_dt} -> {end_dt}",
    }
    return text, summary


def main() -> int:
    ap = argparse.ArgumentParser(description="Render PUFF input for current case")
    ap.add_argument("--case", help="Case name under project/cases; defaults to project/current")
    args = ap.parse_args()

    case_name, config = load_case_config_with_name(args.case)
    work_dir = case_paths(config, case_name, required=["run_puff_dir"])["run_puff_dir"]
    work_dir.mkdir(parents=True, exist_ok=True)
    out_inp = work_dir / PUFF_INP

    rendered, summary = render_puff_inp(case_name, config, work_dir)
    out_inp.write_text(rendered, encoding="utf-8")

    print(f"[OK] Rendered: {out_inp}")
    for k, v in summary.items():
        print(f"[INFO] {k}: {v}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
