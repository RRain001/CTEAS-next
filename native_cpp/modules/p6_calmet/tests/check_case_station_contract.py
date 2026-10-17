#!/usr/bin/env python3
"""P3/P4/P5 -> P6 met.inp station/geometry contract, real Hefei frozen case.

Only the final met.inp is authoritative to CALMET. The upstream station CSVs
are checked against their effective coordinates and identities, never used
to replace SS1/US1 during the P6 computation.
"""
from __future__ import annotations

import csv
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from engine.run_met.common import lon_lat_to_utm_km
from native_cpp.modules.p5_smerge.data_prep.download_isd_by_grid import (
    Station, load_utm_grid, station_in_utm_grid,
)


def annotated(text: str, key: str) -> str:
    matches = re.findall(
        rf"!\s*{re.escape(key)}\s*=\s*([^!]*)!", text
    )
    if len(matches) != 1:
        raise AssertionError(f"{key}: expected exactly one control, found {len(matches)}")
    return matches[0].strip()


def single_csv(path: Path) -> dict[str, str]:
    with path.open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    if len(rows) != 1:
        raise AssertionError(f"{path}: expected one frozen study station, got {len(rows)}")
    return rows[0]


def station(text: str, name: str) -> tuple[str, float, float]:
    s = annotated(text, name)
    fields = s.split("'")[-1].split()
    if len(fields) < 4:
        raise AssertionError(f"{name} incomplete")
    return fields[0], float(fields[1]), float(fields[2])


def main(case: Path) -> None:
    inp = (case / "run/met/met.inp").read_text(encoding="utf-8")
    grid = (case / "grid/grid.cmn").read_text(encoding="utf-8")
    geo = (case / "geo/makegeo/geo.dat").read_text(encoding="utf-8")
    zone = int(annotated(inp, "IUTMZN"))
    assert zone == int(annotated(grid, "IUTMZN"))
    northern = annotated(grid, "LSOHEM").strip().upper() == "N"
    assert northern
    dx = float(annotated(inp, "DGRIDKM"))
    xorig = float(annotated(inp, "XORIGKM"))
    yorig = float(annotated(inp, "YORIGKM"))
    assert abs(dx - float(annotated(grid, "DGRIDKM"))) < 1e-9
    assert abs(xorig - float(annotated(grid, "XREFKM"))) < 1e-9
    assert abs(yorig - float(annotated(grid, "YREFKM"))) < 1e-9
    assert int(annotated(inp, "NX")) == int(annotated(grid, "NX")) == 50
    assert int(annotated(inp, "NY")) == int(annotated(grid, "NY")) == 50
    assert int(annotated(inp, "NSSTA")) == int(annotated(inp, "NUSTA")) == 1

    # GEO.DAT 2.1: projection metadata and grid dimensions share P6 origin.
    g = geo.splitlines()
    assert g[0].startswith("GEO.DAT")
    assert g[4].strip() == "UTM"
    assert g[5].strip() == f"{zone}N"
    dims = g[7].split()
    assert (int(dims[0]), int(dims[1])) == (50, 50)
    for val, exp in zip(map(float, dims[2:6]), (xorig, yorig, dx, dx)):
        assert abs(val - exp) < 1e-6, (val, exp)

    pairs = (
        ("SS1", case / "met/surface/final/stations.csv"),
        ("US1", case / "met/upperair/final/stations.csv"),
    )
    for key, path in pairs:
        sid, x, y = station(inp, key)
        row = single_csv(path)
        assert sid == row["station_id"], (key, sid, row["station_id"])
        easting, northing = lon_lat_to_utm_km(
            float(row["lon"]), float(row["lat"]), zone, northern
        )
        # prepare_met publishes UTM kilometres with THREE decimal places.
        assert f"{x:.3f}" == f"{easting:.3f}", (key, x, easting)
        assert f"{y:.3f}" == f"{northing:.3f}", (key, y, northing)

    # Source-effective provenance is the contract, not the site name alone.
    # P4 may use one virtual station relocated to the release location.
    with (case / "met/upperair/2022/upperair_station_used_list.txt").open(
            encoding="utf-8", newline="") as f:
        p4_rows = list(csv.DictReader(f))
    p4_final = single_csv(case / "met/upperair/final/stations.csv")
    p4_matches = [row for row in p4_rows
                  if row["id"].endswith(p4_final["station_id"])]
    assert len(p4_matches) == 1, "P4 annual effective-station metadata mismatch"
    for axis in ("lat", "lon"):
        assert abs(float(p4_matches[0][axis]) - float(p4_final[axis])) < 1e-9, (
            "P4 effective position lost before US1", axis)

    # P5's original NOAA source location must be classified against the
    # published UTM grid, while SS1 uses the effective (possibly relocated)
    # coordinates written by P5. This detects legacy lon/lat-bbox leakage.
    p5 = json.loads((case / "met/surface/isd_raw/station_selection_2022.json").read_text())
    p5_final = single_csv(case / "met/surface/final/stations.csv")
    assert len(p5["stations"]) == 1, "frozen P5 study has one effective station"
    p5_row = p5["stations"][0]
    assert p5_row["ifstn"] == p5_final["station_id"]
    assert p5_row["sid"] == p5["primary_sid"]
    for axis in ("lat", "lon"):
        assert abs(float(p5_row[axis]) - float(p5_final[axis])) < 1e-9, (
            "P5 effective position lost before SS1", axis)
    p5_source = Station(
        p5_row["sid"], float(p5_row["source_lat"]), float(p5_row["source_lon"]),
        float(p5_row["source_elev"]), p5_row["name"], p5_row["country"],
        p5_row["begin"], p5_row["end"])
    strict_inside = station_in_utm_grid(p5_source, load_utm_grid(case / "grid/grid.cmn"))
    assert strict_inside != bool(p5_row["relocated"]), (
        "P5 strict UTM inside/outside classification contradicts frozen provenance")
    if p5_row["relocated"]:
        assert p5["mode"] == "VIRTUAL_RELOCATED"
    else:
        assert p5["mode"] == "OBSERVED"

    # SURF.DAT formatted station ID record, independent of CSV identity.
    with (case / "met/surface/final/surf.dat").open(encoding="utf-8") as f:
        head = [next(f) for _ in range(7)]
    assert head[6].split() == [station(inp, "SS1")[0]]
    upper = single_csv(case / "met/upperair/final/stations.csv")
    assert (case / f"met/upperair/final/up_{upper['station_id']}.dat").is_file()

    print("PASS_P3_P4_P5_TO_P6_STATION_GRID_CONTRACT")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: check_case_station_contract.py CASE_DIRECTORY")
    main(Path(sys.argv[1]).resolve())
