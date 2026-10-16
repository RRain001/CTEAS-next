#!/usr/bin/env python3
"""P7 original-CTEAS grid provenance contract (selected frozen 2022 case).

grid.cmn/center_location are PREPROCESSING artifacts, not additional CALPUFF
runtime inputs. Deriving coordinates here is a provenance check only.
Never replace frozen puff.inp or original CALMET.DAT values with recomputed UTM.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Callable


def active_values(text: str, name: str) -> list[str]:
    # Match exactly the active ! NAME = VALUE ! fields of the CTEAS
    # common and CALPUFF control files; disabled * ... * keys are ignored.
    expr = re.compile(r"![ \t]*" + re.escape(name) + r"[ \t]*=[ \t]*([^!\r\n]*)!", re.I)
    return [m.group(1).strip() for m in expr.finditer(text)]


def one(text: str, name: str) -> str:
    values = active_values(text, name)
    if len(values) != 1 or not values[0]:
        raise ValueError(f"expected exactly one active {name}, got {len(values)}")
    return values[0]


def scalar(text: str, name: str) -> float:
    value = one(text, name).replace("D", "E").replace("d", "e")
    try:
        result = float(value)
    except ValueError as exc:
        raise ValueError(f"bad numeric {name}={value}") from exc
    if not __import__("math").isfinite(result):
        raise ValueError(f"nonfinite {name}")
    return result


def values(text: str, name: str) -> list[float]:
    active = active_values(text, name)
    if not active:
        raise ValueError(f"missing active {name}")
    return [float(word.strip().replace("D", "E")) for v in active
            for word in v.split(",")]


def selected_case_contract(grid: str, puff: str, center: str,
                           converter: Callable[[float, float], dict]) -> dict:
    checks = (
        ("IMAP", "PMAP"), ("IUTMZN", "IUTMZN"), ("LSOHEM", "UTMHEM"),
        ("DATUM", "DATUM"), ("NX", "NX"), ("NY", "NY"), ("NZ", "NZ"),
    )
    for grid_key, puff_key in checks:
        g = one(grid, grid_key).upper()
        p = one(puff, puff_key).upper()
        if g != p:
            raise ValueError(f"grid.cmn {grid_key}={g} != puff.inp {puff_key}={p}")

    if one(grid, "IMAP").upper() != "UTM" or one(puff, "PMAP").upper() != "UTM":
        raise ValueError("selected frozen 2022 scope requires UTM")
    if one(grid, "DATUM").upper() != "WGS-84":
        raise ValueError("selected frozen 2022 datum must be WGS-84")
    if int(scalar(grid, "IUTMZN")) != 50 or one(grid, "LSOHEM").upper() != "N":
        raise ValueError("selected frozen 2022 projection must be UTM zone 50N")

    for grid_key, puff_key in (
        ("XREFKM", "XORIGKM"), ("YREFKM", "YORIGKM"),
        ("DGRIDKM", "DGRIDKM"),
    ):
        g = scalar(grid, grid_key)
        p = scalar(puff, puff_key)
        if g != p:
            raise ValueError(f"grid/puff {grid_key}/{puff_key} mismatch: {g} vs {p}")
    if values(grid, "ZFACE") != values(puff, "ZFACE"):
        raise ValueError("P7 grid.cmn/puff.inp ZFACE mismatch")

    nx = int(scalar(grid, "NX"))
    ny = int(scalar(grid, "NY"))
    nz = int(scalar(grid, "NZ"))
    dx = scalar(grid, "DGRIDKM")
    if (nx, ny, nz, dx) != (50, 50, 9, 0.1):
        raise ValueError("selected frozen 2022 grid must be 50x50x9, 100m")
    if one(puff, "METFM") != "1":
        raise ValueError("selected frozen 2022 P7 must use CALMET binary METFM=1")
    if one(puff, "METDAT").strip() == "":
        raise ValueError("METDAT filename missing")
    if int(scalar(puff, "NPT1")) != 1:
        raise ValueError("selected frozen 2022 requires one source")

    xy = values(puff, "X")
    if len(xy) != 10:
        raise ValueError("selected frozen 2022 source must have 10 values")
    if xy[0:2] != [513.385, 3533.769]:
        raise ValueError("2022 puff.inp source coordinates changed from frozen values")

    matches = dict(re.findall(r"(?im)^\s*(longitude|latitude)\s*:\s*([^\s]+)\s*$", center))
    if set(matches) != {"longitude", "latitude"}:
        raise ValueError("center_location requires longitude and latitude exactly once")
    lon, lat = float(matches["longitude"]), float(matches["latitude"])
    conv = converter(lon, lat)
    if int(conv["zone"]) != 50 or str(conv["hemisphere"]).upper() != "N":
        raise ValueError("center_location projection differs from original grid.cmn")

    # Original preprocessing rounds origin and source XY to THREE decimals.
    # This must be a validation only: never pass projected x/y into CALPUFF.
    x0 = float(f'{float(conv["x_km"]) - nx * dx / 2.0:.3f}')
    y0 = float(f'{float(conv["y_km"]) - ny * dx / 2.0:.3f}')
    projected_x = float(f'{float(conv["x_km"]):.3f}')
    projected_y = float(f'{float(conv["y_km"]):.3f}')
    if (x0, y0) != (scalar(grid, "XREFKM"), scalar(grid, "YREFKM")):
        raise ValueError("grid.cmn origin not reproduced by original preprocess/grid")
    if (projected_x, projected_y) != (xy[0], xy[1]):
        raise ValueError("frozen point source not reproduced by original prepare_puff 3dp")

    return {"zone": 50, "nx": nx, "ny": ny, "nz": nz, "dx_km": dx,
            "source_x_control_km": xy[0], "source_y_control_km": xy[1],
            "source_x_raw_utm_km": float(conv["x_km"]),
            "source_y_raw_utm_km": float(conv["y_km"])}


def negative_cases(grid: str, puff: str, center: str,
                   converter: Callable[[float, float], dict]) -> None:
    def should_fail(g: str, p: str, c: str, name: str) -> None:
        try:
            selected_case_contract(g, p, c, converter)
        except ValueError:
            return
        raise AssertionError(f"fail-closed regression did NOT reject {name}")

    edits = (
        (grid.replace("! NX =  50", "! NX =  51"), puff, center, "grid NX"),
        (grid.replace("! IUTMZN =  50", "! IUTMZN =  49"), puff, center, "UTM zone"),
        (grid.replace("! XREFKM =  510.885", "! XREFKM =  510.886"),
         puff, center, "rounded origin"),
        (grid.replace("! DATUM = WGS-84", "! DATUM = ESR-S"),
         puff, center, "datum"),
        (grid, puff.replace("! PMAP =UTM !", "! PMAP =LCC !"), center, "projection"),
        (grid, puff.replace("513.385, 3533.769", "513.3846439571, 3533.7689269678"),
         center, "unrounded GIS source override"),
        (grid, puff, center.replace("longitude:117.141610855",
                                    "longitude:118.141610855"), "center location drift"),
    )
    for changed_grid, changed_puff, changed_center, label in edits:
        if (changed_grid, changed_puff, changed_center) == (grid, puff, center):
            raise AssertionError(f"unapplied mutation fixture: {label}")
        should_fail(changed_grid, changed_puff, changed_center, label)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--grid", type=Path, required=True)
    parser.add_argument("--puff", type=Path, required=True)
    parser.add_argument("--center", type=Path, required=True)
    parser.add_argument("--negative", action="store_true")
    args = parser.parse_args()
    repo_root = Path(__file__).resolve().parents[4]
    sys.path.insert(0, str(repo_root))
    from engine.preprocess.grid.center_location_to_utm import convert_lon_lat

    grid = args.grid.read_text(encoding="utf-8")
    puff = args.puff.read_text(encoding="utf-8")
    center = args.center.read_text(encoding="utf-8")
    result = selected_case_contract(grid, puff, center, convert_lon_lat)
    if args.negative:
        negative_cases(grid, puff, center, convert_lon_lat)
    print("P7_ORIGINAL_GRID_PREPROCESS=PASS"
          f" NX={result['nx']} NY={result['ny']} NZ={result['nz']}"
          f" UTM_ZONE={result['zone']} SOURCE_KM="
          f"{result['source_x_control_km']},{result['source_y_control_km']}"
          " PREPROCESS_PROVENANCE_ONLY=true NO_RUNTIME_LONLAT_REPROJECTION=true"
          f" NEGATIVE_TESTS={'PASS' if args.negative else 'NOT_RUN'}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, OSError, AssertionError) as exc:
        print(f"P7_ORIGINAL_GRID_PREPROCESS=FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1)
