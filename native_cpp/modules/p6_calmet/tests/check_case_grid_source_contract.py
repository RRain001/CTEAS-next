#!/usr/bin/env python3
"""Original CTEAS grid-generator -> grid.cmn -> GEO.DAT/met.inp Mode A contract.

This is READ-ONLY: never regenerate or overwrite a frozen reference case.
Proves the original engine/preprocess/grid source of the numerical grid
origin, including its 0.001-km publication rounding. The geographical
centre is NOT used to reconstruct CALMET stations within P6.
"""
from __future__ import annotations

import math
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

import yaml
from engine.preprocess.grid.configure_grid_cmn import convert_lon_lat
from engine.run_met.common import parse_grid_cmn


def control(text: str, key: str) -> str:
    matches = re.findall(rf"!\s*{re.escape(key)}\s*=\s*([^!]*)!", text)
    if len(matches) != 1:
        raise AssertionError(f"ambiguous or absent input control {key}: {matches}")
    return matches[0].strip()


def equal_float(name: str, actual: float, expected: float, tol: float=1e-10) -> None:
    if not (math.isfinite(actual) and math.isfinite(expected) and
            abs(actual-expected) <= tol):
        raise AssertionError(f"{name}: expected {expected}, observed {actual}")


def parse_center_location(path: Path) -> dict[str, float]:
    lines = path.read_text(encoding="utf-8").splitlines()
    out: dict[str, float] = {}
    for line in lines:
        name,sep,value=line.partition(":")
        if not sep or name.strip() not in ("longitude","latitude"):
            raise AssertionError(f"unrecognized center_location record: {line!r}")
        if name.strip() in out:
            raise AssertionError(f"duplicate center_location entry: {name!r}")
        out[name.strip()]=float(value)
    if set(out) != {"longitude","latitude"}:
        raise AssertionError(f"center_location incomplete: {out}")
    return out


def main(case: Path) -> None:
    cfg=yaml.safe_load((case/"case.yaml").read_text(encoding="utf-8"))
    user=cfg["preprocess"]["grid"]
    center=user["center"]
    lon=float(center["longitude"])
    lat=float(center["latitude"])
    length=float(user["domain"]["length_km"])
    width=float(user["domain"]["width_km"])
    spacing=float(user["resolution_km"])
    nz=int(user["nz"])
    if length<=0 or width<=0 or spacing<=0:
        raise AssertionError("nonpositive grid extent/resolution")
    station_center=parse_center_location(case/"grid/center_location")
    equal_float("center_location longitude",station_center["longitude"],lon)
    equal_float("center_location latitude",station_center["latitude"],lat)

    # Independently recalculate upstream *generator* output (not P6 physics).
    # Original configure_grid_cmn publishes XREFKM/YREFKM to 0.001 km.
    projected=convert_lon_lat(lon,lat)
    xref=float(f"{float(projected['x_km'])-length/2.0:.3f}")
    yref=float(f"{float(projected['y_km'])-width/2.0:.3f}")
    nx=math.ceil(length/spacing)
    ny=math.ceil(width/spacing)
    grid=parse_grid_cmn("case",path=case/"grid/grid.cmn")
    assert grid.imap=="UTM"
    assert grid.datum=="WGS-84"
    assert grid.lsohem==projected["hemisphere"]
    assert grid.iutmzn==projected["zone"]
    assert (grid.nx,grid.ny,grid.nz)==(nx,ny,nz)
    equal_float("grid spacing",grid.dgridkm,spacing)
    equal_float("generated XREFKM",grid.xrefkm,xref)
    equal_float("generated YREFKM",grid.yrefkm,yref)

    # Crucially distinguish the projected ideal centre from the centre of the
    # millikilometre-quantized model grid. They need not coincide exactly.
    x_grid_center=grid.xrefkm+grid.nx*grid.dgridkm/2.0
    y_grid_center=grid.yrefkm+grid.ny*grid.dgridkm/2.0
    delta_x_m=(x_grid_center-float(projected["x_km"]))*1000.0
    delta_y_m=(y_grid_center-float(projected["y_km"]))*1000.0
    if max(abs(delta_x_m),abs(delta_y_m))>0.501:
        raise AssertionError(
            f"grid centre differs from projected centre by >0.5m: {delta_x_m}, {delta_y_m}")

    # Verify original P1/P2/P3 control files actually consumed the frozen
    # grid.cmn geometry. TERREL's IGRID=1 means southwest cell (1,1) CORNER;
    # interpreting it as cell-centre would shift every generated field by 50m.
    for module in ("terrel","ctgproc","makegeo"):
        deck_path=case/f"geo/{module}/{module}.inp"
        original_deck=deck_path.read_text(encoding="utf-8")
        for key,value in (
            ("IUTMZN",grid.iutmzn),("NX",nx),("NY",ny),
            ("DGRIDKM",spacing),("XREFKM",xref),("YREFKM",yref)
        ):
            equal_float(f"{module} {key}",float(control(original_deck,key)),float(value),1e-6)
        if control(original_deck,"PMAP").upper()!="UTM":
            raise AssertionError(f"{module}: PMAP not UTM")
        if control(original_deck,"UTMHEM").upper()!=grid.lsohem:
            raise AssertionError(f"{module}: UTM hemisphere disagrees with grid")
        if control(original_deck,"DATUM").upper()!=grid.datum:
            raise AssertionError(f"{module}: datum disagrees with grid")
        if module=="terrel" and int(control(original_deck,"IGRID"))!=1:
            raise AssertionError("TERREL IGRID must mean SW corner, not cell centre")

    inp=(case/"run/met/met.inp").read_text(encoding="utf-8")
    for key,expected in (
        ("IUTMZN",grid.iutmzn),("NX",grid.nx),("NY",grid.ny),
        ("NZ",grid.nz),("DGRIDKM",grid.dgridkm),
        ("XORIGKM",grid.xrefkm),("YORIGKM",grid.yrefkm)
    ):
        equal_float(f"grid.cmn -> met.inp {key}",float(control(inp,key)),float(expected))
    assert control(inp,"PMAP").upper()=="UTM"
    assert control(inp,"UTMHEM").upper()==grid.lsohem
    assert control(inp,"DATUM").upper()==grid.datum

    met_zfaces=[float(x) for x in control(inp,"ZFACE").split(",")]
    if len(met_zfaces)!=nz+1:
        raise AssertionError("CALMET ZFACE layer count mismatch")
    if len(grid.zfaces)!=len(met_zfaces):
        raise AssertionError("grid.cmn ZFACE layer count mismatch")
    for n,(actual,expected) in enumerate(zip(met_zfaces,grid.zfaces)):
        equal_float(f"ZFACE layer {n}",actual,expected)

    geo=(case/"geo/makegeo/geo.dat").read_text(encoding="utf-8")
    lines=geo.splitlines()
    if lines[4].strip()!="UTM" or lines[5].strip()!=f"{grid.iutmzn}{grid.lsohem}":
        raise AssertionError("GEO.DAT projection disagrees with grid generator")
    gd=lines[7].split()
    if [int(v) for v in gd[:2]]!=[nx,ny]:
        raise AssertionError("GEO.DAT NX/NY differ from grid generator")
    for key,actual,expected in zip(
        ("GEO XREFKM","GEO YREFKM","GEO DXKM","GEO DYKM"),
        map(float,gd[2:6]),(xref,yref,spacing,spacing)
    ):
        equal_float(key,actual,expected,1e-6)

    print("PASS_ORIGINAL_GRID_GENERATOR_P1_P3_P6_INPUT_CONTRACT")
    print(f"projected_ideal_center_utm_km=({projected['x_km']:.9f}, {projected['y_km']:.9f})")
    print(f"published_grid_centre_utm_km=({x_grid_center:.9f}, {y_grid_center:.9f})")
    print(f"quantization_displacement_m=({delta_x_m:.6f}, {delta_y_m:.6f})")


if __name__=="__main__":
    if len(sys.argv)!=2:
        raise SystemExit("usage: check_case_grid_source_contract.py CASE_DIR")
    main(Path(sys.argv[1]).resolve())
